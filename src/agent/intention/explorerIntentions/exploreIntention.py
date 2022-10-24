from data.coreData import MapValueEnum, Coordinate, MapcRole

from data.intention import Observation
from agent.intention.mainAgentIntention import MainAgentIntention
from agent.intention.commonIntentions import TravelIntention, DetachBlocksIntention, AdoptRoleIntention

from agent.action import AgentAction

class ExploreIntention(MainAgentIntention):
    """
    Intention to explore the surrounding unknown environment:
    search unknown `Coordinates` in a spiral shape, starting
    from the starting `Coordinate`.\n
    It is finished when all `DynamicMaps` are merged
    and all the `Coordinates` are explored.
    """
    
    currentTravelIntention: TravelIntention | None
    detachBlocksIntention: DetachBlocksIntention | None
    adoptRoleIntention: AdoptRoleIntention | None
    relocation: bool                                        # Contains if the Agent not found a close unknown Coordinate so
                                                            # it will move to a random location

    def __init__(self) -> None:
        self.currentTravelIntention = None
        self.detachBlocksIntention = None
        self.adoptRoleIntention = None

        self.relocation = False
    
    def getPriority(self) -> float:
        return 7.0

    async def planNextAction(self, observation: Observation) -> AgentAction:
        # If carrying a block and it regulates a norm then drop it
        maxBlockCount = observation.simDataServer.getMaxBlockRegulation()
        if len(observation.agentData.attachedEntities) > 1 or (maxBlockCount is not None and maxBlockCount < len(observation.agentData.attachedEntities)):
            if self.detachBlocksIntention is None:
                self.detachBlocksIntention = DetachBlocksIntention()
            
            return await self.detachBlocksIntention.planNextAction(observation)

        # If there are reserved roles for the Agent and it is not already adopted
        # then adopt it. It is important because of the Norms
        agentRoles = observation.simDataServer.getReservedRolesForAgent(observation.agentData.id)
        if any(agentRoles) and observation.agentMapcRole != agentRoles[0]:
            return await self.planRoleAdoptPlan(observation, agentRoles[0])

        # If just initialized or reached target or target became known (and not relocating) then search for a new target
        if (self.currentTravelIntention is None or self.currentTravelIntention.checkFinished(observation)
            or (not self.relocation and observation.map.getMapValueEnum(self.currentTravelIntention.coordinate) != MapValueEnum.UNKNOWN)):

            # Try to search for a close unknown Coordinate
            self.relocation = False
            newDestination = observation.map.findClosestUnknownFromStartingLocation(
                    observation.agentStartingCoordinate, observation.agentCurrentCoordinate, observation.agentMapcRole.vision)

            # If not found a close unknown Coordinate then move to a 
            # random close Coordinate and try later there
            if newDestination is None:
                newDestination = observation.map.findRandomFarCoordinate(
                    observation.agentCurrentCoordinate, observation.agentMapcRole.vision)
                self.relocation = True
            
            self.currentTravelIntention = TravelIntention(newDestination)

        return await self.currentTravelIntention.planNextAction(observation)

    def checkFinished(self, observation: Observation) -> bool:
        return observation.simDataServer.getMapCount() == 1 and observation.map.isMapExplored()
        
    def updateCoordinatesByOffset(self, offsetCoordinate: Coordinate) -> None:
        if self.currentTravelIntention is not None:
            self.currentTravelIntention.updateCoordinatesByOffset(offsetCoordinate)
        
        if self.detachBlocksIntention is not None:
            self.detachBlocksIntention.updateCoordinatesByOffset(offsetCoordinate)
        
        if self.adoptRoleIntention is not None:
            self.adoptRoleIntention.updateCoordinatesByOffset(offsetCoordinate)
    
    def normalizeCoordinates(self) -> None:
        if self.currentTravelIntention is not None:
            self.currentTravelIntention.normalizeCoordinates()
        
        if self.detachBlocksIntention is not None:
            self.detachBlocksIntention.normalizeCoordinates()
        
        if self.adoptRoleIntention is not None:
            self.adoptRoleIntention.normalizeCoordinates()

    def explain(self) -> str:
        if self.currentTravelIntention is not None:
            return "exploring to " + str(self.currentTravelIntention.coordinate) + " " + self.currentTravelIntention.explain()
        else:
            return "exploring to unknown"
    
    async def planRoleAdoptPlan(self, observation: Observation, role: MapcRole) -> AgentAction:
        """
        Returns the required `AgentAction` to adopt
        the given `MapcRole`
        """

        if self.adoptRoleIntention is None:
            self.adoptRoleIntention = AdoptRoleIntention(role)
        
        return await self.adoptRoleIntention.planNextAction(observation)