from data.coreData import Coordinate
from data.intention import Observation

from agent.intention.agentIntention import AgentIntention
from agent.intention.commonIntentions import DistantAgitatedTravelIntention, SkipIntention
from agent.intention.blockProviderIntentions.connectIntention import ConnectIntention

from agent.action import AgentAction

class BlockDeliveryIntention(AgentIntention):
    """
    Intention to deliver a collected `Block` to
    an another `Agent`.\n
    Finishes when the `Block` is delivered to the
    `Agent`: the `Block` is handed over and
    it is detached.
    """

    distantAgitatedTravelIntention: DistantAgitatedTravelIntention | None
    connectIntention: ConnectIntention | None
    skipIntention: SkipIntention
    toAgentId: str
    toAgentCurrentCoordinate: Coordinate | None
    startedConnection: bool
    readyForConnection: bool
    blockRelCoord: Coordinate | None

    def __init__(self, toAgentId: str) -> None:
        self.distantAgitatedTravelIntention = None
        self.connectIntention = None
        self.skipIntention = SkipIntention(True)

        self.toAgentId = toAgentId
        self.toAgentCurrentCoordinate = None

        self.startedConnection = False
        self.readyForConnection = False
        self.blockRelCoord = None
        
    async def planNextAction(self, observation: Observation) -> AgentAction:
        toAgentCoordinate = observation.map.getAgentCoordinate(self.toAgentId)
        
        # If just intialized or coordinater Agent position changed then intialize travel intention
        if self.distantAgitatedTravelIntention is None or self.toAgentCurrentCoordinate != toAgentCoordinate:
            # Goal is to be close to the Coordinator, but keep a distance to it,
            # so other Blocks can be handed over
            self.toAgentCurrentCoordinate = toAgentCoordinate
            self.distantAgitatedTravelIntention = DistantAgitatedTravelIntention(
                toAgentCoordinate, observation.agentMapcRole.vision, observation.agentMapcRole.vision - 1, True)

        # If already started connection or it is close enough to the coordinator
        if self.startedConnection or self.distantAgitatedTravelIntention.checkFinished(observation):            
            # If not started connection, set ready flag True,
            # then get closer to the coordinator
            if not self.startedConnection:
                self.readyForConnection = True

                if self.distantAgitatedTravelIntention.checkReachedGoalCoords(observation):
                    return await self.skipIntention.planNextAction(observation)
                else:
                    return await self.distantAgitatedTravelIntention.planNextAction(observation)
            
            # If started connection then continue it
            else:
                if self.connectIntention is None:
                    self.connectIntention = ConnectIntention(self.toAgentId, self.blockRelCoord)

                return await self.connectIntention.planNextAction(observation)

        # Else travel to the coordinator
        return await self.distantAgitatedTravelIntention.planNextAction(observation)

    def checkFinished(self, observation: Observation) -> bool:
        return self.connectIntention is not None and self.connectIntention.checkFinished(observation)
    
    def isReadyForBlockHandover(self, observation: Observation) -> bool:
        """
        Returns if it is ready for the `Block` hand over:
        the attached `Block` is at the given `Coordinate`.
        """

        return self.connectIntention is not None and self.connectIntention.isReadyForBlockHandover(observation)
    
    def updateCoordinatesByOffset(self, offsetCoordinate: Coordinate) -> None:
        if self.toAgentCurrentCoordinate is not None:
            self.toAgentCurrentCoordinate.updateByOffsetCoordinate(offsetCoordinate)
        
        if self.distantAgitatedTravelIntention is not None:
            self.distantAgitatedTravelIntention.updateCoordinatesByOffset(offsetCoordinate)
        
        if self.connectIntention is not None:
            self.connectIntention.updateCoordinatesByOffset(offsetCoordinate)
        
        self.skipIntention.updateCoordinatesByOffset(offsetCoordinate)
    
    def normalizeCoordinates(self) -> None:
        if self.toAgentCurrentCoordinate is not None:
            self.toAgentCurrentCoordinate.normalize()
        
        if self.distantAgitatedTravelIntention is not None:
            self.distantAgitatedTravelIntention.normalizeCoordinates()
        
        if self.connectIntention is not None:
            self.connectIntention.normalizeCoordinates()
        
        self.skipIntention.normalizeCoordinates()
    
    def startConnection(self, blockRelCoord: Coordinate) -> None:
        """
        Starts the connection (the upcoming `Block` hand over), by retrieving the `Block` destination.
        """

        self.startedConnection = True
        self.blockRelCoord = blockRelCoord
    
    def stopConnection(self) -> None:
        """
        Stops the connection (the upcoming `Block` hand over).
        """

        self.startedConnection = False
        self.blockRelCoord = None

        self.connectIntention = None
    
    def setEscapeFlags(self) -> None:
        """
        Stops the connection (the upcoming `Block` hand over) because of a clear event.
        """

        if self.startedConnection:
            self.stopConnection()

        self.readyForConnection = False
    
    def isReadyToStartConnection(self) -> bool:
        """
        Returns if it is ready for the connection (the upcoming `Block` hand over) and not started it already.
        """

        return not self.startedConnection and self.readyForConnection
    
    def isReadyForConnection(self) -> bool:
        """
        Returns if it is ready for the connection (the upcoming `Block` hand over).
        """

        return self.readyForConnection

    def explain(self) -> str:
        explanation = "blockdelivering to " + self.toAgentId + " at " + str(self.toAgentCurrentCoordinate)

        if self.distantAgitatedTravelIntention is not None:
            explanation += self.distantAgitatedTravelIntention.explain()
            
        if self.readyForConnection is not None:
            explanation += "ready to connect "

        if self.startedConnection is not None:
            explanation += "connecting to relative " + str(self.blockRelCoord)

        return explanation
