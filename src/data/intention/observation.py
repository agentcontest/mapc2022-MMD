from data.coreData import Coordinate, MapcRole, AgentActionEnum, AttachedEntity
from data.wrapper import DynamicPerceptWrapper
from data.map import DynamicMap
from data.server import SimulationDataServer

from data.intention.agentData import AgentData

class Observation():
    """
    Contains data about the simulation, from an agent perspective,
    which are required for intentions.
    """

    agentData: AgentData
    simDataServer: SimulationDataServer
    map: DynamicMap
    agentMapcRole : MapcRole

    def __init__(self, agentId: str, simDataServer: SimulationDataServer, map: DynamicMap,
        agentMapcRole: MapcRole, agentEnergy: int, deactivated: bool,
        lastAction: AgentActionEnum, lastActionResult: str,
        attachedEntities: list[AttachedEntity], perceptAttachedRelCoords: list[Coordinate],
        dynamicPerceptWrapper: DynamicPerceptWrapper) -> None:
        
        self.agentData = AgentData(agentId, agentEnergy, deactivated, lastAction, lastActionResult,
            attachedEntities, perceptAttachedRelCoords, dynamicPerceptWrapper)
        self.simDataServer = simDataServer
        self.map = map
        self.agentMapcRole = agentMapcRole
    
    @property
    def agentCurrentCoordinate(self) -> Coordinate:
        """
        Returns the agent's (the one to the `Observation` belongs) current coordinate in the map.
        """

        return self.map.getAgentCoordinate(self.agentData.id)
    
    @property
    def agentStartingCoordinate(self) -> Coordinate:
        """
        Returns the agent's (the one to the `Observation` belongs) starting coordinate in the map.
        """

        return self.map.getAgentStartingCoordinate(self.agentData.id)