from data.coreData import Coordinate, MapValueEnum, MapcRole

from data.intention import Observation
from agent.intention.mainAgentIntention import MainAgentIntention
from agent.intention.commonIntentions import TravelIntention, DetachBlocksIntention, AdoptRoleIntention

from agent.action import AgentAction

class UpdateMapIntention(MainAgentIntention):
    """
    Intention to update the already explored `DynamicMap`.
    It has no goal, searches and travels to the
    earliest explored (updated) `Coordinate`.
    """

    currentTravelIntention: TravelIntention | None
    detachBlocksIntention: DetachBlocksIntention | None
    adoptRoleIntention: AdoptRoleIntention | None

    def __init__(self) -> None:
        self.currentTravelIntention = None
        self.detachBlocksIntention = None
        self.adoptRoleIntention = None

    def getPriority(self) -> float:
        return 8.0

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

        # If just initialized or reached target or target became occupied then search for a new target
        if (self.currentTravelIntention is None or self.currentTravelIntention.checkFinished(observation)
            or observation.map.getMapValueEnum(self.currentTravelIntention.coordinate) in [MapValueEnum.AGENT, MapValueEnum.BLOCK, MapValueEnum.MARKER]):
            
            newDestination = observation.map.findRandomOldestCoordinate(
                    observation.agentCurrentCoordinate, observation.agentMapcRole.vision)
            self.currentTravelIntention = TravelIntention(newDestination)

        return await self.currentTravelIntention.planNextAction(observation)

    def checkFinished(self, _: Observation) -> bool:
        return False
        
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
        if self.adoptRoleIntention is None:
            self.adoptRoleIntention = AdoptRoleIntention(role)
        
        return await self.adoptRoleIntention.planNextAction(observation)