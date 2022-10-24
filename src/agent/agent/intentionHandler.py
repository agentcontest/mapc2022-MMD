from typing import Type

from data.coreData import Coordinate, AgentIntentionRole
from data.dataStructure import PriorityQueue, PriorityQueueNode
from data.intention import Observation

from agent.intention.mainAgentIntention import MainAgentIntention
from agent.intention.explorerIntentions import ExploreIntention, UpdateMapIntention
from agent.intention.commonIntentions import IdleIntention, EscapeIntention
from agent.intention.blockProviderIntentions import BlockProvidingIntention, SingleBlockProvidingIntention
from agent.intention.coordinatorIntentions import CoordinationIntention

class IntentionHandler():
    """
    Intention container which prioritizes `MainAgentIntentions`
    by their priority (min priority queue).\n
    Manages communication between the right intention (the first one)
    and drops it if it is finished.
    """

    agentId: str
    intentions: PriorityQueue
    currentIntention: MainAgentIntention | None
    intentionRole: AgentIntentionRole
    hasToDropCurrentTask: bool                      # Contains if has to drop its current Task 
                                                    # (used for coordinators and single block providers)

    def __init__(self, agentId: str) -> None:
        self.agentId = agentId

        self.intentions = PriorityQueue()
        self.initializeBaseIntention()
        self.currentIntention = None

        self.intentionRole = AgentIntentionRole.EXPLORER
        self.hasToDropCurrentTask = False
    
    def insertIntention(self, intention: MainAgentIntention) -> None:
        """
        Inserts a `MainAgentIntention` into the queue by its priority.
        """

        self.intentions.insert(PriorityQueueNode(intention, intention.getPriority()))
    
    def isCurrentIntentionRelatedToTask(self) -> bool:
        """
        Returns if its current intention is related to a `Task`:
        providing block, coordinating or single block providing
        """

        return isinstance(self.currentIntention, (BlockProvidingIntention, SingleBlockProvidingIntention, CoordinationIntention))
    
    def finishCurrentIntention(self) -> None:
        """
        Finishes its first intention, removes from the queue.
        """

        self.intentions.pop()
        self.currentIntention = None
    
    def getCurrentIntention(self) -> MainAgentIntention | None:
        """
        Returns the current `MainAgentIntention`.
        """

        return self.currentIntention
    
    def generateOptions(self, observation: Observation) -> None:
        """
        Generates local intentions: currently only
        generates `EscapeIntention` if it needs to escape.
        """

        if self.isAgentInMarkerCoords(observation) and not self.hasGivenTypeOfIntention(EscapeIntention):
            escapeInt = EscapeIntention()
            self.intentions.insert(PriorityQueueNode(escapeInt, escapeInt.getPriority()))

    def filterOptions(self) -> MainAgentIntention:
        """
        Filters the generated intention options:
        selects the current `MainAgentIntention` from the queue.
        """

        # If has to drop Task then drop it before choosing an another intention
        if self.hasToDropCurrentTask and self.currentIntention is not None and \
            isinstance(self.currentIntention, (CoordinationIntention, SingleBlockProvidingIntention)):

            self.currentIntention.startDroppingIntention()

        # Select the current intention
        currentIntention = self.intentions.head().value

        # If it is an escape (clear event) set the required flags
        if isinstance(currentIntention, EscapeIntention):
            # If coordinator then drop the Task and release the blockProviders
            if isinstance(self.currentIntention, CoordinationIntention):
                self.currentIntention.releaseProviders()
                self.currentIntention.startDroppingIntention()
            
            # If single block provider then just set own flags
            elif isinstance(self.currentIntention, BlockProvidingIntention) and self.currentIntention.isDeliveringBlock():
                self.currentIntention.setEscapeFlags()

        self.currentIntention = currentIntention
        return self.currentIntention
    
    def updateIntentionCoordinatesByOffset(self, offsetCoordinate: Coordinate) -> None:
        """
        Shifts the all the `Coordinates` in all intentions recursively.
        """

        for intention in self.intentions.getValues():
            intention.updateCoordinatesByOffset(offsetCoordinate)
    
    def normalizeIntentionCoordinates(self) -> None:
        """
        Normalizes all the `Coordinates` in all intentions recursively.
        """

        for intention in self.intentions.getValues():
            intention.normalizeCoordinates()
    
    def setIntentionRole(self, role: AgentIntentionRole) -> None:
        """
        Sets the `AgentIntentionRole`.
        """

        self.intentionRole = role
    
    def getIntentionRole(self) -> AgentIntentionRole:
        """
        Returns the current `AgentIntentionRole`.
        """

        return self.intentionRole

    def doesTaskCurrently(self) -> bool:
        """
        Returns if one of the `MainAgentIntentions` from the queue are
        related to a `Task` by the current `AgentIntentionRole`.
        """

        return self.intentionRole in [AgentIntentionRole.COORDINATOR, AgentIntentionRole.BLOCKPROVIDER, AgentIntentionRole.SINGLEBLOCKPROVIDER]
    
    def abandonCurrentTask(self) -> None:
        """
        Drops the current `Task`: sends this information
        to the right `MainAgentIntention`.
        """

        # If the current one is a Task related then send the signal
        if self.currentIntention is not None and isinstance(self.currentIntention, (CoordinationIntention, SingleBlockProvidingIntention)):
            self.currentIntention.startDroppingIntention()
        
        # Else set the flag, so later can be sent
        else:
            self.hasToDropCurrentTask = True
    
    def hasGivenTypeOfIntention(self, type: Type) -> bool:
        """
        Returns if has the given type of `MainAgentIntention`.
        """

        return any(isinstance(i, type) for i in self.intentions.getValues())
    
    def initializeBaseIntention(self) -> None:
        """
        Initializes the `ExploreIntention`, `UpdateMapIntention`
        and `IdleIntention` intentsions.
        """
        
        exploreInt = ExploreIntention()
        updateMapInt = UpdateMapIntention()
        idleInt = IdleIntention()

        self.intentions.insert(PriorityQueueNode(exploreInt, exploreInt.getPriority()))
        self.intentions.insert(PriorityQueueNode(updateMapInt, updateMapInt.getPriority()))
        self.intentions.insert(PriorityQueueNode(idleInt, idleInt.getPriority()))
    
    def isAgentInMarkerCoords(self, observation: Observation) -> bool:
        """
        Returns if the `Agent` or one of its attached entities
        are in a clear event.
        """

        agentCurrentCoord = observation.agentCurrentCoordinate
        involvedCoords = [agentCurrentCoord]
        involvedCoords.extend([agentCurrentCoord.getShiftedCoordinate(e.relCoord) for e in observation.agentData.attachedEntities])

        return any(c in observation.map.markers for c in involvedCoords)