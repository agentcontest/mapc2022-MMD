from data.coreData import Coordinate, MapcRole
from data.intention import Observation
from data.server import IntentionDataServer

from agent.intention.mainAgentIntention import MainAgentIntention
from agent.intention.commonIntentions import SkipIntention, AdoptRoleIntention, DetachBlocksIntention
from agent.intention.blockProviderIntentions.blockCollectionIntention import BlockCollectionIntention
from agent.intention.blockProviderIntentions.blockDeliveryIntenton import BlockDeliveryIntention

from agent.action import AgentAction

class BlockProvidingIntention(MainAgentIntention):
    """
    Intention to collect and to deliver a `Block` to an another Agent.
    Starts with `BlockCollectionIntention` and ends with `BlockDeliveryIntention`.
    """

    blockCollectionIntention: BlockCollectionIntention | None
    blockDeliveryIntention: BlockDeliveryIntention | None
    skipIntention: SkipIntention
    adoptRoleIntention: AdoptRoleIntention | None
    detachBlockIntention: DetachBlocksIntention | None
    agentId: str                                                # Own id
    toAgentId: str                                              # Destination agent id
    blockType: str                                              # Block type to deliver
    finishedCurrentProviding: bool                              # Contains if finished the current providing (delivered one block)
    finishedGlobalProviding: bool                               # Contains if finished the whole providing task (this is the same as `finishedCurrentProviding` at the current moment)
    intentionDataServer: IntentionDataServer

    def __init__(self, agentId: str, toAgentId: str, blockType: str, intentionDataServer: IntentionDataServer) -> None:
        self.blockCollectionIntention = None
        self.blockDeliveryIntention = None
        self.skipIntention = SkipIntention(False)
        self.adoptRoleIntention = None
        self.detachBlockIntention = None

        self.agentId = agentId
        self.toAgentId = toAgentId
        
        self.blockType = blockType

        self.finishedCurrentProviding = False
        self.finishedGlobalProviding = False

        self.intentionDataServer = intentionDataServer

    def getPriority(self) -> float:
        return 5.0

    async def planNextAction(self, observation: Observation) -> AgentAction:
        # Check finished the current providing
        if self.finishedCurrentProviding or \
            (self.blockDeliveryIntention is not None and self.blockDeliveryIntention.checkFinished(observation)):
            
            # Wait to be released (from the coordinator)
            self.finishedCurrentProviding = True    
            return await self.skipIntention.planNextAction(observation)

        # If just initialized check the currently attached entities
        if self.blockCollectionIntention is None and self.blockDeliveryIntention is None and \
            any(observation.agentData.attachedEntities) and not self.hasTheBlock(observation):
            
            # If has the wrong types of blocks then detach them
            return await self.releaseBlocks(observation)

        # If there are reserved roles for the Agent and it is not already adopted
        # then adopt it. It is required so the Agent can request, attach and connect Blocks
        agentRoles = observation.simDataServer.getReservedRolesForAgent(self.agentId)
        if any(agentRoles) and observation.agentMapcRole != agentRoles[0]:
            return await self.planRoleAdoptPlan(observation, agentRoles[0])

        # Initialize blockCollectionIntention if have to
        if self.blockCollectionIntention is None:
            # Has to collect the required Block
            if not observation.agentData.attachedEntities:
                self.blockCollectionIntention = BlockCollectionIntention(self.blockType, self.intentionDataServer)
                self.blockDeliveryIntention = None
            
            # If already has the right block then initialize the blockDeliveryIntention
            elif self.blockDeliveryIntention is None and self.hasTheBlock(observation):
                self.blockDeliveryIntention = BlockDeliveryIntention(self.toAgentId)
                return await self.blockDeliveryIntention.planNextAction(observation)

        # If it is collecting
        if self.blockCollectionIntention is not None:
            # If finished then switch to delivering
            if self.blockCollectionIntention.checkFinished(observation):
                self.blockCollectionIntention = None
                self.blockDeliveryIntention = BlockDeliveryIntention(self.toAgentId)

                return await self.blockDeliveryIntention.planNextAction(observation)
            
            # Else continue collecting
            else:
                return await self.blockCollectionIntention.planNextAction(observation)

        return await self.blockDeliveryIntention.planNextAction(observation)

    def checkFinished(self, observation: Observation) -> bool:
        if not self.finishedCurrentProviding:
            self.finishedCurrentProviding = self.blockDeliveryIntention is not None and self.blockDeliveryIntention.checkFinished(observation)

        return self.finishedGlobalProviding
    
    def checkFinishedProviding(self) -> bool:
        return self.finishedCurrentProviding
    
    def updateCoordinatesByOffset(self, offsetCoordinate: Coordinate) -> None:
        if self.blockCollectionIntention is not None:
            self.blockCollectionIntention.updateCoordinatesByOffset(offsetCoordinate)
        
        if self.blockDeliveryIntention is not None:
            self.blockDeliveryIntention.updateCoordinatesByOffset(offsetCoordinate)
        
        self.skipIntention.updateCoordinatesByOffset(offsetCoordinate)

        if self.adoptRoleIntention is not None:
            self.adoptRoleIntention.updateCoordinatesByOffset(offsetCoordinate)
        
        if self.detachBlockIntention is not None:
            self.detachBlockIntention.updateCoordinatesByOffset(offsetCoordinate)
    
    def normalizeCoordinates(self) -> None:
        if self.blockCollectionIntention is not None:
            self.blockCollectionIntention.normalizeCoordinates()
        
        if self.blockDeliveryIntention is not None:
            self.blockDeliveryIntention.normalizeCoordinates()
        
        self.skipIntention.normalizeCoordinates()

        if self.adoptRoleIntention is not None:
            self.adoptRoleIntention.normalizeCoordinates()
        
        if self.detachBlockIntention is not None:
            self.detachBlockIntention.normalizeCoordinates()
    
    def startConnection(self, blockRelCoord: Coordinate) -> None:
        """
        Starts the connection (the upcoming `Block` hand over), by retrieving the `Block` destination
        if already delivering the `Block`.
        """

        if self.blockDeliveryIntention is not None:
            self.blockDeliveryIntention.startConnection(blockRelCoord)
    
    def stopConnection(self) -> None:
        """
        Stops the connection (the upcoming `Block` hand over) if
        already delivering the `Block`.
        """

        if self.blockDeliveryIntention is not None:
            self.blockDeliveryIntention.stopConnection()
    
    def isReadyToStartConnection(self) -> bool:
        """
        Returns if it is ready for the connection (the upcoming `Block` hand over) and not started it already
        and if already delivering the `Block`.
        """

        return self.blockDeliveryIntention is not None and self.blockDeliveryIntention.isReadyToStartConnection()

    def isReadyForConnection(self) -> bool:
        """
        Returns if it is ready for the connection (the upcoming `Block` hand over) if already
        delivering the `Block`.
        """

        return self.blockDeliveryIntention is not None and self.blockDeliveryIntention.isReadyForConnection()
    
    def isReadyForBlockHandover(self, observation: Observation) -> bool:
        """
        Returns if it is ready for the `Block` hand over:
        delivering the `Block` and the attached `Block` is at the given `Coordinate`.
        """

        return self.blockDeliveryIntention is not None and self.blockDeliveryIntention.isReadyForBlockHandover(observation)

    def finishProviding(self) -> None:
        """
        Sets the finished whole providing task flag true
        (so the intention can be finished).
        """

        self.finishedGlobalProviding = True

    def hasTheBlock(self,observation:Observation) -> bool:
        """
        Returns if currently has the right type of `Block`
        and if it is the only attached entity.
        """

        return len(observation.agentData.attachedEntities) == 1 and \
            observation.agentData.attachedEntities[0].details == self.blockType

    async def releaseBlocks(self, observation : Observation) -> AgentAction:
        """
        Returns an `AgentAction` to release any attached entity.
        """

        if self.detachBlockIntention is None:
            self.detachBlockIntention = DetachBlocksIntention()
        
        return await self.detachBlockIntention.planNextAction(observation)

    def isDeliveringBlock(self) -> bool:
        """
        Returns if currently delivering a `Block`.
        """

        return self.blockDeliveryIntention is not None
    
    def setEscapeFlags(self) -> None:
        """
        Stops the connection (the upcoming `Block` hand over) because of a clear event
        if it is in the delivering status.
        """

        self.blockDeliveryIntention.setEscapeFlags()

    def explain(self) -> str:
        explanation = "blockproviding " + self.blockType + " to " + self.toAgentId + " "

        if self.blockCollectionIntention is not None:
            explanation += self.blockCollectionIntention.explain()

        if self.blockDeliveryIntention is not None:
            explanation += self.blockDeliveryIntention.explain()

        return explanation
    
    async def planRoleAdoptPlan(self, observation: Observation, role: MapcRole) -> AgentAction:
        """
        Returns the required `AgentAction` to adopt
        the given `MapcRole`.
        """

        if self.adoptRoleIntention is None:
            self.adoptRoleIntention = AdoptRoleIntention(role)
        
        return await self.adoptRoleIntention.planNextAction(observation)
