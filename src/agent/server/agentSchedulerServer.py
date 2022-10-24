import asyncio
import PySimpleGUI as sg

from data.coreData import Coordinate
from data.dataStructure import ThreadWithReturnValue
from data.server import MapServer, SimulationDataServer
from data.wrapper import StaticPerceptWrapper
from data.server.intentionDataServer import IntentionDataServer

from agent.agent.agent import Agent
from agent.server.intentionGenerator import IntentionGenerator


class AgentSchedulerServer():
    """
    The main `Agent` manager: responsible for
    initializations and action scheduling.\n
    Contains a `IntentionGenerator` object, which is responsible
    for generating global options for `Agents`.
    """

    host: str
    port: int
    teamName: str
    password: str
    initialization: bool                        # Used at reconnecting
    agents: list[Agent]
    simDataServer: SimulationDataServer
    mapServer: MapServer
    intentionDataServer: IntentionDataServer
    intentionGenerator: IntentionGenerator
    explainAgentIntentions: bool                # Explanation enable flag

    def __init__(self, host: str, port: int, teamName: str, password: str, explain: bool) -> None:
        self.host = host
        self.port = port
        self.teamName = teamName
        self.password = password

        self.initialization = True

        self.agents = []

        self.simDataServer = SimulationDataServer(teamName)
        self.mapServer = MapServer(self.simDataServer.unknownCoordSearchMaxIter)
        self.intentionDataServer = IntentionDataServer()

        self.intentionGenerator = IntentionGenerator(self.simDataServer, self.mapServer, self.intentionDataServer)

        self.explainAgentIntentions = explain
        if self.explainAgentIntentions:
            sg.theme('DarkAmber')
            self.layout = None
            self.window = None
    
    def populateAgents(self, capacity: int) -> None:
        """
        Adds the given amount of new `Agents` to
        the `Agent` container.
        """

        for _ in range(len(self.agents), capacity):
            self.addAgent()

    def addAgent(self) -> Agent:
        """
        Adds a new `Agent` to the `Agent` container.
        """

        newAgent = Agent(self.generateAgentId(), self.mapServer, self.simDataServer)
        self.agents.append(newAgent)
        return newAgent

    def initialiteStaticValues(self) -> None:
        """
        Resets `Coordinate` static values (map dimension values)
        """

        Coordinate.maxWidth = None
        Coordinate.maxHeight = None
        Coordinate.dimensionsCalculated = False

    async def connectAgents(self) -> None:
        """
        Connect `Agents` to the simulation server,
        first only one `Agent` is connected, then based
        on the team size, the rest of them will be connected.
        """

        # Connect the first one to the simulation server
        firstAgent = self.addAgent()
        firstAgent.connect(self.host, self.port, self.password)

        # Get team size from static percept
        staticPercept = StaticPerceptWrapper(firstAgent.mapcAgent.static["percept"])
        self.populateAgents(staticPercept.teamSize)
        self.simDataServer.setStaticPercept(staticPercept)

        # Connect the first one to the local servers
        firstAgent.registerToMapServer()
        self.simDataServer.registerInitialRoleForAgent(firstAgent.id, firstAgent.mapcRole)

        if self.explainAgentIntentions:
            self.initExplanation()
    
        # Connect the rest of the team
        threads = [ThreadWithReturnValue(target = agent.connect, args=(self.host, self.port, self.password)) for agent in self.agents[1:]]
        
        [t.start() for t in threads]
        [t.join() for t in threads]

    def registerAgentsToServers(self) -> None:
        """
        Registers the `Agents` (except the first one) to the `MapServer`
        and to the `MapcRoleServer.
        """

        for agent in self.agents[1:]:
            agent.registerToMapServer()
            self.simDataServer.registerInitialRoleForAgent(agent.id, agent.mapcRole)
    
    async def scheduleAgents(self) -> None:
        """
        Schedules the `Agent` actions for the next step.\n
        First checks identifications, then generates, filter options for `Agents`.
        After that makes the `Agents` plan their next move, which will be performed
        after. Lastly makes the `Agents` check if they finished their current `MainAgentIntention`.
        """

        self.checkAgentIdentifications()
        self.generateOptionsForAgents()
        self.filterOptionsForAgents()
        await self.planNextActionForAgents()
        self.executeActionForAgents()
        self.checkFinishedCurrentIntentionForAgents()
        
    def generateOptionsForAgents(self) -> None:
        """
        Makes the `IntentionGenerator` and the `Agents` generate global
        and local options.
        """

        # Check if a reconnect was performed and pass this value to the option generation
        needReset = self.initialization and self.simDataServer.getSimulationStep() > 1

        self.intentionGenerator.generateOptions(list(self.mapServer.maps.values()),
            self.getActiveAgents(), self.simDataServer.getTasks(), needReset)
        
        self.initialization = False
    
    def filterOptionsForAgents(self) -> None:
        """
        Makes the `IntentionGenerator` and the `Agents` filter the generated options.
        """

        self.intentionGenerator.filterOptions(list(self.mapServer.maps.values()), self.getActiveAgents())
    
    async def planNextActionForAgents(self) -> None:
        """
        Makes the active `Agents` plan their next move by their
        current `MainAgentIntention`.
        """

        coroutines = [agent.planNextAction() for agent in self.getActiveAgents()]
        await asyncio.gather(*coroutines)
    
    def executeActionForAgents(self) -> None:
        """
        Makes the active `Agents` execute their planned `AgentAction`
        and store the retrieved data from the incoming dynamic percept.
        """

        # Send the action
        activeAgents = self.getActiveAgents()
        threads = [ThreadWithReturnValue(target = agent.executeAction) for agent in activeAgents]
        [t.start() for t in threads]
        results = [t.join() for t in threads]

        # Result process, store the changes
        for i in range(0, len(activeAgents)):
            activeAgents[i].processActionResult(results[i])
        
        # Parse dynamic percept and set observation
        for i in range(0, len(activeAgents)):
            activeAgents[i].setDynamicPerceptAfterAction(results[i])
            self.intentionDataServer.addAgentObservation(activeAgents[i].id, activeAgents[i].observation)
            self.intentionDataServer.addAgentIntentionRole(activeAgents[i].id, activeAgents[i].intentionHandler.intentionRole)
            
    def checkFinishedCurrentIntentionForAgents(self) -> None:
        """
        Makes the active `Agents` to check if their current `MainAgentIntention`
        has been finished.
        """

        self.intentionGenerator.checkFinishedCurrentIntentionForAgents(self.getActiveAgents())
    
    def checkAgentIdentifications(self) -> None:
        """
        Checks the `Agent` identification globally:
        possible `DynamicMap` merges and map dimension calculations
        are checked.
        """

        self.intentionGenerator.checkAgentIdentifications(self.getActiveAgents())

    def getActiveAgents(self) -> list[Agent]:
        """
        Get a list of `Ągents` which are connected to the server.
        """

        return list(filter(lambda a: a.mapcAgent is not None, self.agents))

    def getAgentById(self, id: str) -> Agent:
        """
        Returns an `Agent` by the given id.
        """

        return next((a for a in self.agents if a.id == id), None)

    def generateAgentId(self) -> str:
        """
        Returns a new id for an `Agent`
        """

        return "agent" + self.teamName + str(len(self.agents) + 1)
    
    # region Explanation

    def initExplanation(self) -> None:
        """
        Explanation initialization if enabled.
        """

        self.layout = [[sg.T(agent.id), sg.T("--- no explanation ---", key = agent.id, size = (150, 1))]
            for agent in self.agents]
        self.window = sg.Window("Explanation window", self.layout, resizable = True, finalize = True,  location=(400,0))
        self.window.read(timeout = 10)

    def explain(self) -> None:
        """
        Update explain window.
        """

        self.window.read(timeout = 10)
        for agent in self.agents:
            self.window[agent.id].update(agent.explain())

    # endregion