from data.coreData import Coordinate, Task, MapcRole
from data.intention import Observation
from data.server import IntentionDataServer

from agent.intention.mainAgentIntention import MainAgentIntention
from agent.intention.commonIntentions import AdoptRoleIntention, DetachBlocksIntention, SkipIntention
from agent.intention.blockProviderIntentions.blockCollectionIntention import BlockCollectionIntention
from agent.intention.blockProviderIntentions.singleBlockSubmissionIntention import SingleBlockSubmissionIntention

from agent.action import AgentAction

class SingleBlockProvidingIntention(MainAgentIntention):
    """
    Intention for providing and submitting a `Task` which
    required only one `Block`.
    Finishes when the `Task` is submitted successfully or
    if the `Task` is dropped due to failure.
    """

    agentId: str
    blockCollectionIntention: BlockCollectionIntention | None
    singleBlockSubmissionIntention: SingleBlockSubmissionIntention | None
    adoptRoleIntention: AdoptRoleIntention | None
    detachBlockIntention: DetachBlocksIntention | None
    skipIntention: SkipIntention
    task: Task
    blockType: str
    intentionDataServer: IntentionDataServer
    finished: bool
    goalZone: Coordinate

    def __init__(self, agentId: str, task: Task, goalZone: Coordinate, intentionDataServer: IntentionDataServer) -> None:
        self.agentId = agentId
        self.blockCollectionIntention = None
        self.singleBlockSubmissionIntention = None
        self.adoptRoleIntention = None
        self.detachBlockIntention = None
        self.skipIntention = SkipIntention(False)

        self.task = task
        self.blockType = task.requirements[0].type
        self.intentionDataServer = intentionDataServer

        self.finished = False
        self.goalZone = goalZone

    def getPriority(self) -> float:
        return 5.0

    async def planNextAction(self, observation: Observation) -> AgentAction:
        maxBlockCount = observation.simDataServer.getMaxBlockRegulation()

        # If Task has expired or submitted succesfully or goal zone gone
        # or max block count is violated then end the intention and skip
        if observation.simDataServer.hasTaskExpired(self.task) or \
            (self.singleBlockSubmissionIntention is not None and self.singleBlockSubmissionIntention.checkFinished(observation)) or \
            self.goalZone not in observation.map.goalZones or \
            (maxBlockCount is not None and maxBlockCount < len(self.task.requirements)):

            self.finished = True
            return await self.skipIntention.planNextAction(observation)

        # If just initialized and has the wrong Blocks then detach them.
        if self.blockCollectionIntention is None and self.singleBlockSubmissionIntention is None and \
            any(observation.agentData.attachedEntities) and not self.hasTheBlock(observation):

            return await self.releaseBlocks(observation)

        # Get the required AgentRole for the current state: block collection or submission
        agentRoles = observation.simDataServer.getReservedRolesForAgent(self.agentId)
        roleIndex = 0 if self.singleBlockSubmissionIntention is None or len(agentRoles) == 1 else 1
        
        # If has the wrong role then adopt it
        if any(agentRoles) and observation.agentMapcRole != agentRoles[roleIndex]:
            return await self.planRoleAdoptPlan(observation, agentRoles[roleIndex])

        # If just initialized and don't have any block, then initialize block collection intention
        if self.blockCollectionIntention is None and not any(observation.agentData.attachedEntities):
            self.blockCollectionIntention = BlockCollectionIntention(self.blockType,self.intentionDataServer)

            if self.singleBlockSubmissionIntention is not None:
                self.singleBlockSubmissionIntention = None
        
        # If just initialized and have the right Block, then initialize submission
        if self.blockCollectionIntention is None and self.singleBlockSubmissionIntention is None and self.hasTheBlock(observation):
            self.singleBlockSubmissionIntention = SingleBlockSubmissionIntention(self.task, self.goalZone.copy())
            return await self.singleBlockSubmissionIntention.planNextAction(observation)

        # Continue providing if not finished
        if self.blockCollectionIntention is not None:
            if self.blockCollectionIntention.checkFinished(observation):
                self.blockCollectionIntention = None
                self.singleBlockSubmissionIntention = SingleBlockSubmissionIntention(self.task, self.goalZone.copy())
                return await self.singleBlockSubmissionIntention.planNextAction(observation)
            else:
                return await self.blockCollectionIntention.planNextAction(observation)
        
        # Else continue block submission
        elif self.singleBlockSubmissionIntention is None:
            self.singleBlockSubmissionIntention = SingleBlockSubmissionIntention(self.task, self.goalZone.copy())
        
        return await self.singleBlockSubmissionIntention.planNextAction(observation)

    def checkFinished(self, _: Observation) -> bool:
        return self.finished
    
    def updateCoordinatesByOffset(self, offsetCoordinate: Coordinate) -> None:
        if self.blockCollectionIntention is not None:
            self.blockCollectionIntention.updateCoordinatesByOffset(offsetCoordinate)
        
        if self.singleBlockSubmissionIntention is not None:
            self.singleBlockSubmissionIntention.updateCoordinatesByOffset(offsetCoordinate)
        
        self.goalZone.updateByOffsetCoordinate(offsetCoordinate)

        if self.adoptRoleIntention is not None:
            self.adoptRoleIntention.updateCoordinatesByOffset(offsetCoordinate)
        
        if self.detachBlockIntention is not None:
            self.detachBlockIntention.updateCoordinatesByOffset(offsetCoordinate)
        
        self.skipIntention.updateCoordinatesByOffset(offsetCoordinate)
    
    def normalizeCoordinates(self) -> None:
        if self.blockCollectionIntention is not None:
            self.blockCollectionIntention.normalizeCoordinates()
        
        if self.singleBlockSubmissionIntention is not None:
            self.singleBlockSubmissionIntention.normalizeCoordinates()
        
        self.goalZone.normalize()

        if self.adoptRoleIntention is not None:
            self.adoptRoleIntention.normalizeCoordinates()
        
        if self.detachBlockIntention is not None:
            self.detachBlockIntention.normalizeCoordinates()
        
        self.skipIntention.normalizeCoordinates()
    
    def finishProviding(self) -> None:
        """
        Sets the finished whole providing task flag true
        (so the intention can be finished).
        """

        self.finished = True
    
    def startDroppingIntention(self) -> None:
        """
        Sets the `droppingIntention` False
        """

        self.droppingIntention = True

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

    def explain(self) -> str:
        explanation = "singleblockproviding " + self.blockType + " "

        if self.blockCollectionIntention is not None:
            explanation += self.blockCollectionIntention.explain()

        if self.singleBlockSubmissionIntention is not None:
            explanation += self.singleBlockSubmissionIntention.explain()

        return explanation
    
    async def planRoleAdoptPlan(self, observation: Observation, role: MapcRole) -> AgentAction:
        """
        Returns the required `AgentAction` to adopt
        the given `MapcRole`.
        """

        if self.adoptRoleIntention is None:
            self.adoptRoleIntention = AdoptRoleIntention(role)

        return await self.adoptRoleIntention.planNextAction(observation)
