from data.coreData import Coordinate, MapValueEnum, AgentActionEnum, AttachedEntity

from data.intention import Observation
from agent.intention.agentIntention import AgentIntention
from agent.intention.commonIntentions import SkipIntention
from agent.intention.blockProviderIntentions import BlockProvidingIntention

from agent.action import AgentAction, AttachAction, ConnectAction

from data.server.intentionDataServer import IntentionDataServer

class AssembleIntention(AgentIntention):
    """
    Sub-Intention for the `CoordinationIntention` which takes
    over a `Blockk` from an other `Agent`.
    It finishes if the given `Block` is handed over
    and the other `Agent` is disconnected.
    """

    blockProvidingIntention: BlockProvidingIntention    # BlockProvidingIntention of the Agent that is handing over the Block
    skipIntention: SkipIntention
    blockRelCoord: Coordinate
    blockType: str
    assembleCompleted: bool                             # Contains if the block handover was successful
    intentionDataServer: IntentionDataServer
    failed: bool                                        # Contains if the block handover is failed permanently

    def __init__(self, blockRelCoord: Coordinate, blockType: str, blockProvidingIntention: BlockProvidingIntention, intentionDataServer: IntentionDataServer) -> None:
        self.blockProvidingIntention = blockProvidingIntention
        self.skipIntention = SkipIntention(False)

        self.blockRelCoord = blockRelCoord
        self.blockType = blockType
        self.assembleCompleted = False
        self.intentionDataServer = intentionDataServer

        self.failed = False

    async def planNextAction(self, observation: Observation) -> AgentAction:
        # If assemble is completed then wait until the other Agent gets disconnected
        if self.assembleCompleted:
            return await self.skipIntention.planNextAction(observation)
        
        # If the other Agent is ready to hand over the Block then get it
        elif self.blockProvidingIntention.isReadyForBlockHandover(self.intentionDataServer.getAgentOservation(self.blockProvidingIntention.agentId)):
            return await self.getAttachedBlock(observation, observation.agentCurrentCoordinate.getShiftedCoordinate(self.blockRelCoord))

        # Else just wait for the other Agent to get to the hand over point
        else:
            return await self.skipIntention.planNextAction(observation)

    def checkFinished(self, observation: Observation) -> bool:
        if not self.assembleCompleted:
            self.assembleCompleted = observation.agentData.lastAction in \
                [AgentActionEnum.ATTACH, AgentActionEnum.CONNECT] and observation.agentData.lastActionSucceeded

        return self.assembleCompleted and self.blockProvidingIntention.checkFinishedProviding()

    def updateCoordinatesByOffset(self, offsetCoordinate: Coordinate) -> None:        
        self.skipIntention.updateCoordinatesByOffset(offsetCoordinate)
    
    def normalizeCoordinates(self) -> None:        
        self.skipIntention.normalizeCoordinates()

    def explain(self) -> str:
        return "assembling " + str(self.blockRelCoord) + ' with agent ' + \
            self.blockProvidingIntention.agentId
    
    async def getAttachedBlock(self, observation: Observation, blockCoord: Coordinate) -> AgentAction:
        """
        Returns the `AgentAction` to get the attached `Block` from the other `Agent`,
        which is already handing over it.
        """

        # If the block is adjacent then it just needs to be attached
        if blockCoord in observation.agentCurrentCoordinate.neighbors():
            return AttachAction(Coordinate.getDirection(observation.agentCurrentCoordinate, blockCoord),
                MapValueEnum.BLOCK,
                observation.map.getMapValue(blockCoord).details)
        # Else it has to be connected to a specific attached Block
        else:
            connectCoords = [coord for coord in self.blockRelCoord.neighbors(False) if coord in [e.relCoord for e in observation.agentData.attachedEntities]]
            
            # It should not happen, but sometimes blocks get lost because of a bug (probably by a clear event)
            if not any(connectCoords):
                self.failed = True
                return await self.skipIntention.planNextAction(observation)

            # Get an attached relative Coordinate that can be used to complete the connection
            connectCoord = [coord for coord in self.blockRelCoord.neighbors(False) if coord in [e.relCoord for e in observation.agentData.attachedEntities]][0]
            return ConnectAction(self.blockProvidingIntention.agentId, connectCoord,
                AttachedEntity(Coordinate.getRelativeCoordinate(observation.agentCurrentCoordinate, blockCoord), MapValueEnum.BLOCK, self.blockType))