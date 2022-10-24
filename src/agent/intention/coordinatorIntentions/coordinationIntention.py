from typing import Tuple

from data.coreData import Coordinate, Task, TaskRequirement, AgentActionEnum, MapValueEnum
from data.coreData import Coordinate, Task, TaskRequirement
from data.coreData.mapcRole import MapcRole

from data.intention import Observation
from agent.intention.mainAgentIntention import MainAgentIntention
from agent.intention.commonIntentions import ClearZoneIntention, WaitIntention, DetachBlocksIntention, SkipIntention, AdoptRoleIntention
from agent.intention.coordinatorIntentions.assembleIntention import AssembleIntention
from agent.intention.blockProviderIntentions import BlockProvidingIntention
from data.server import IntentionDataServer

from agent.action import AgentAction, SubmitAction

class CoordinationIntention(MainAgentIntention):
    """
    Intention that coordinates a `Task` completion:
    clears the reserved goal zone area, assembles the blocks
    given by the blockprodivers and then submits the `Task`.\n
    Controls the blockproviders when to hand over the given block
    and where to.\n
    If something goes wrong (task expiration, goal zone moved, marker) then
    it will drop the `Task`.
    """

    waitIntention: WaitIntention | None
    blockProviderIntentions: list[BlockProvidingIntention] | None   # Blockprovider intentions (so communication can be made in one way)
    currentAssembleIntention: AssembleIntention | None
    clearZoneIntention: ClearZoneIntention | None
    currentBlockProvidingIntention: BlockProvidingIntention | None
    detachBlockIntention: DetachBlocksIntention | None
    skipIntention: SkipIntention
    adoptRoleIntention: AdoptRoleIntention | None
    agentId: str                                                    # Coordinator Agent Id
    task: Task
    intentionDataServer: IntentionDataServer
    clearingGoalZone: bool                                          # Contains if still clearing the goal zone
    droppingIntention: bool                                         # Contains if it has to drop the current Task and has to release the blockproviders
    initialisation: bool                                            # Contains if it was just initialized
    goalZone: Coordinate                                            # Goalzone where the Agent will assemble the Blocks
    otherAgentBlockCount: int                                       # Blocking threshold: if it reaches a limit (meaning other Agents blocking the area) then it will drop the Task
    taskReadyForSubmission: bool                                    # Just for explanation

    def __init__(self, agentId: str, task: Task, goalZone: Coordinate,
        blockProviderIntentions: list[BlockProvidingIntention], intentionDataServer: IntentionDataServer) -> None:

        self.waitIntention = None
        self.blockProviderIntentions = blockProviderIntentions
        self.currentAssembleIntention = None
        self.clearZoneIntention = None
        self.currentBlockProvidingIntention = None
        self.detachBlockIntention = None
        self.skipIntention = SkipIntention(False)
        self.adoptRoleIntention = None

        self.agentId = agentId
        self.task = task
        self.taskReadyForSubmission = False
        
        self.intentionDataServer = intentionDataServer

        self.goalZone = goalZone
        self.clearingGoalZone = True

        self.droppingIntention = False
        self.initialisation = True
        self.otherAgentBlockCount = 0

    def getPriority(self) -> float:
        return 5.0

    async def planNextAction(self, observation: Observation) -> AgentAction:
        # If just initialized and has the wrong blocks, then just drop them
        if self.initialisation: 
            if self.hasWrongBlocks(observation):
                return await self.releaseBlocks(observation)
            else:
                self.initialisation = False

        # Check the other Agent blocking threshold, to drop the intention if it is reached
        if not self.clearingGoalZone:
            self.checkBlockingAgents(observation)

        maxBlockCount = observation.simDataServer.getMaxBlockRegulation()

        # If already dropping the intention or task expired or goal zone moved or
        # the Task block counts regulates a norm then drop the intention
        if self.droppingIntention or observation.simDataServer.hasTaskExpired(self.task) or self.goalZoneGone(observation) or \
            (maxBlockCount is not None and maxBlockCount < len(self.task.requirements)):
            self.droppingIntention = True
            self.releaseProviders()
            return await self.dropIntention(observation)
        
        # If there are reserved roles for the Agent and it is not already adopted
        # then adopt it. It is required so the Agent can submit, attach and connect Blocks
        agentRoles = observation.simDataServer.getReservedRolesForAgent(self.agentId)
        if any(agentRoles) and observation.agentMapcRole != agentRoles[0]:
            return await self.planRoleAdoptPlan(observation, agentRoles[0])

        # If a blockprovider is handing over a Block currenctly
        if self.currentAssembleIntention is not None:
            # If something goes wrong for the blockprovider (for example a marker), then stop it and search for an another
            if not self.currentBlockProvidingIntention.isReadyForConnection() and not self.currentBlockProvidingIntention.checkFinishedProviding():
                self.currentAssembleIntention = None
                self.currentBlockProvidingIntention = None
            
            # If the hand over was completed and the blockprovider disconnected then close the hand over
            elif self.currentAssembleIntention.checkFinished(observation) and self.currentBlockProvidingIntention.checkFinishedProviding():
                # Signal to the blockprovider that the hand over was succesfully completed, the blockprovider is released
                self.currentBlockProvidingIntention.finishProviding()

                self.currentAssembleIntention = None
                self.currentBlockProvidingIntention = None
            
            # If the assemble failed permanently then drop the intetnion
            else:
                if self.currentAssembleIntention.failed:
                    self.droppingIntention = True

                return await self.currentAssembleIntention.planNextAction(observation)

        # If all the required Blocks are attached then submit
        if len(observation.agentData.attachedEntities) == len(self.task.requirements):
            self.taskReadyForSubmission = True
            return SubmitAction(self.task.name)

        # Search for a block hand over
        startableTaskReqResult = self.getStartableTaskRequirement(observation)

        if startableTaskReqResult is not None:
            # Initialize waitIntention at the goal zone 
            # (if it is initialized already then it won't do anything)
            self.clearingGoalZone = False
            self.initializeWaitIntetionForGoalZone(observation)
                
            # If the Agent is not at the waiting Coordinate then travel there
            if self.waitIntention.travelIntention.coordinate != observation.agentCurrentCoordinate:
                return await self.waitIntention.planNextAction(observation)

            # Else initialize assembleIntention
            return await self.initializeAssembleIntention(observation, startableTaskReqResult)

        # If stopped clearing the goal zone (started the assembly) then just wait
        elif not self.clearingGoalZone:
            return await self.waitIntention.planNextAction(observation)
        
        # Else continue clearing the goal zone
        else:
            return await self.planClearAction(observation)

    def checkFinished(self, observation: Observation) -> bool:        
        return (observation.agentData.lastAction == AgentActionEnum.SUBMIT and observation.agentData.lastActionSucceeded) or \
            (self.droppingIntention and self.blockProviderIntentions is None and not any(observation.agentData.attachedEntities))

    def updateCoordinatesByOffset(self, offsetCoordinate: Coordinate) -> None:
        if self.clearZoneIntention is not None:
            self.clearZoneIntention.updateCoordinatesByOffset(offsetCoordinate)
        
        if self.waitIntention is not None:
            self.waitIntention.updateCoordinatesByOffset(offsetCoordinate)
        
        if self.currentAssembleIntention is not None:
            self.currentAssembleIntention.updateCoordinatesByOffset(offsetCoordinate)
        
        if self.detachBlockIntention is not None:
            self.detachBlockIntention.updateCoordinatesByOffset(offsetCoordinate)
        
        self.skipIntention.updateCoordinatesByOffset(offsetCoordinate)

        if self.adoptRoleIntention is not None:
            self.adoptRoleIntention.updateCoordinatesByOffset(offsetCoordinate)

        self.goalZone.updateByOffsetCoordinate(offsetCoordinate)
    
    def normalizeCoordinates(self) -> None:
        if self.clearZoneIntention is not None:
            self.clearZoneIntention.normalizeCoordinates()
        
        if self.waitIntention is not None:
            self.waitIntention.normalizeCoordinates()
        
        if self.currentAssembleIntention is not None:
            self.currentAssembleIntention.normalizeCoordinates()
        
        if self.detachBlockIntention is not None:
            self.detachBlockIntention.normalizeCoordinates()
        
        self.skipIntention.normalizeCoordinates()

        if self.adoptRoleIntention is not None:
            self.adoptRoleIntention.normalizeCoordinates()
        
        self.goalZone.normalize()
    
    def checkBlockingAgents(self, observation: Observation) -> None:
        """
        Checks the blocking threshold count, if it is reached
        then the intention will be dropped.
        """

        agentCurrentCoordinate = observation.agentCurrentCoordinate
        
        # Check if an other Agent blocks the Block assembly zone
        if any([observation.map.getMapValueEnum(agentCurrentCoordinate.getShiftedCoordinate(tr.coordinate)) == MapValueEnum.AGENT
            for tr in self.task.requirements]):

            self.otherAgentBlockCount += 1

            # Threshold reached, drop intention
            if self.otherAgentBlockCount == observation.simDataServer.maxAgentBlockingThresholdForAssemble:
                self.droppingIntention = True
        
        # Reset if no one is blocking       
        else:
            self.otherAgentBlockCount = 0

    def startableTaskRequirements(self, observation: Observation) -> list[TaskRequirement]:
        """
        Returns all the `TaskRequirements` which can be started at the current time:
        a `Block` hand over can be completed if there is an attached `Block` or the `Agent`
        to which can the `Block` be connected.
        """

        attachedCoords = [Coordinate.origo()]
        attachedCoords.extend([e.relCoord for e in observation.agentData.attachedEntities])

        attachedCoordsNeighbors = set()
        for coord in attachedCoords:
            for c in coord.neighbors(False):
                attachedCoordsNeighbors.add(c)

        # Filter the ones which are not already attached
        return list(filter(lambda req: 
            req.coordinate in attachedCoordsNeighbors and req.coordinate not in attachedCoords,
            self.task.requirements))

    def getStartableTaskRequirement(self, observation: Observation) -> Tuple[BlockProvidingIntention, TaskRequirement] | None:
        """
        Checks if the next valid block hand over can be completed to the `Task` assemble, by asking the
        blockproviders, who are carrying the right type of block, are ready.\n
        Returns the `BlockProvidingIntention` and the `TaskRequirement` if found one, else `None`.
        """

        blockProviderIntentions = [bpi for bpi in self.blockProviderIntentions if bpi.isReadyToStartConnection()]

        for taskReq in self.startableTaskRequirements(observation):
            for blockProviderIntention in blockProviderIntentions:
                if taskReq.type == blockProviderIntention.blockType:
                    return (blockProviderIntention, taskReq)

        return None
    
    async def planClearAction(self, observation: Observation) -> AgentAction:
        """
        Plans a clear action around the goal zone by initializing
        the `ClearZoneIntention` if not already initialized and
        performing a clear calculated by the intention. If clear everything
        then it just skips.\n
        During that tries to reserves a closer goal zone if one is found
        which is not already reserved.
        """

        # Search for a closer goal zone
        closestGoalZone = observation.map.tryReserveCloserGoalZoneForTask(self.agentId, self.goalZone,
            observation.agentCurrentCoordinate, [r.coordinate for r in self.task.requirements])

        # If found one reserve it
        if closestGoalZone is not None:
            self.goalZone = closestGoalZone

        # Initialize clearZoneIntention if it is not or a closer goal zone is found
        if self.clearZoneIntention is None or \
            Coordinate.isCloserNewCoordinate(observation.agentCurrentCoordinate,
                self.clearZoneIntention.baseCoordinate, self.goalZone):

            self.clearZoneIntention = ClearZoneIntention(self.goalZone)
        
        # If there are clearable Coordinates then clear them
        if not self.clearZoneIntention.checkFinished(observation):
            return await self.clearZoneIntention.planNextAction(observation)
        # Else just wait
        else:
            if self.waitIntention is None:
                self.waitIntention = WaitIntention(self.goalZone, False)

            return await self.waitIntention.planNextAction(observation)
    
    def initializeWaitIntetionForGoalZone(self, observation: Observation) -> None:
        """
        Initializes a wait point at a goal zone to assemble the `Blocks` there.
        Uses the already reserved goal zone or a new one, if it closer and not
        already reserved.
        """

        closestGoalZone = observation.map.tryReserveCloserGoalZoneForTask(self.agentId, self.goalZone,
            observation.agentCurrentCoordinate, [r.coordinate for r in self.task.requirements])

        if closestGoalZone is not None:
            self.goalZone = closestGoalZone
            self.waitIntention = WaitIntention(self.goalZone, False)

        if self.waitIntention is None:
            self.waitIntention = WaitIntention(self.goalZone, False)

    def startDroppingIntention(self) -> None:
        """
        Sets the `droppingIntention` False
        """

        self.droppingIntention = True

    def releaseProviders(self) -> None:
        """
        Release blockproviders by sending signal to them,
        if there are any
        """

        if self.blockProviderIntentions is not None:
            for providerIntentions in self.blockProviderIntentions: 
                providerIntentions.finishProviding()
            self.blockProviderIntentions = None

    async def dropIntention(self,observation: Observation) -> AgentAction:        
        """
        Drops the current intention: releases `Blocks` and
        returns the `AgentAction` to do that or skip if already
        finished it.
        """

        if any(observation.agentData.attachedEntities):
            return await self.releaseBlocks(observation)
        else:
            return await self.skipIntention.planNextAction(observation)

    def goalZoneGone(self, observation: Observation) -> bool:
        """
        Returns if the reserved goal zone is gone (moved). If it is,
        it tries to reserve an another if it not started assembling the `Blocks`
        and if it was successful then returns False, meaning the `Task` can be still
        completed.
        """

        # If submit was sent and it failed then it moved,
        # the Agent should notice this earlier, but it's buggy
        if observation.agentData.lastAction == AgentActionEnum.SUBMIT and \
            (observation.agentData.lastActionResult == "failed" or observation.agentData.lastActionResult == "failed_target"):
            return True

        # Check if the goal zone is in the map
        if self.goalZone in observation.map.goalZones:
            return False
        
        # If already starting assembling the Blocks then return False,
        # the Agent probably can not move with more than 1 Blocks (it is forbidden in the current implementation),
        # so it won't try to reserve an another goal zone.
        if not self.clearingGoalZone:
            return True

        newGoalZone = observation.map.tryReserveCloserGoalZoneForTask(self.agentId, None,
            observation.agentCurrentCoordinate, [r.coordinate for r in self.task.requirements])
        
        # If a new goal zone is found then it is fine
        if newGoalZone is not None:
            self.goalZone = newGoalZone
            return False
        else:
            return True

    def hasWrongBlocks(self, observation : Observation) -> bool:
        """
        Returns if currently has wrong attached `Blocks` for the `Task`.\n
        IT RETURNS TRUE IF THERE IS ANY ATTACHED ENTITY, TODO
        """

        return any(observation.agentData.attachedEntities)

    async def releaseBlocks(self, observation : Observation) -> AgentAction:
        """
        Returns an `AgentAction` to release any attached entity.
        """

        if self.detachBlockIntention is None:
            self.detachBlockIntention = DetachBlocksIntention()
        
        return await self.detachBlockIntention.planNextAction(observation)

    def explain(self) -> str:
        explanation = "coordinating " + self.task.name + " until " + str(self.task.deadline) + " "
        if self.waitIntention:
            explanation += self.waitIntention.explain()

        if self.clearZoneIntention is not None:
            explanation += self.clearZoneIntention.explain()

        if self.currentAssembleIntention is not None:
            explanation += self.currentAssembleIntention.explain()

        if self.taskReadyForSubmission:
            explanation += " task ready for submission "

        return explanation
    
    async def initializeAssembleIntention(self, observation: Observation, startableTaskReqResult: Tuple[BlockProvidingIntention, TaskRequirement]) -> AgentAction:
        """
        Initializes an `AssembleIntention` to get a `Block` from a blockprovider
        and returns the first `AgentAction` from it.
        """

        # Initialize
        blockProvidingIntention, taskReq = startableTaskReqResult
        self.currentAssembleIntention = AssembleIntention(taskReq.coordinate, taskReq.type,
            blockProvidingIntention, self.intentionDataServer)

        # Signal the blockprovider to start the connection / hand over
        blockProvidingIntention.startConnection(taskReq.coordinate)
        self.currentBlockProvidingIntention = blockProvidingIntention

        return await self.currentAssembleIntention.planNextAction(observation)
    
    async def planRoleAdoptPlan(self, observation: Observation, role: MapcRole) -> AgentAction:
        """
        Returns the required `AgentAction` to adopt
        the given `MapcRole`
        """

        if self.adoptRoleIntention is None:
            self.adoptRoleIntention = AdoptRoleIntention(role)
        
        return await self.adoptRoleIntention.planNextAction(observation)