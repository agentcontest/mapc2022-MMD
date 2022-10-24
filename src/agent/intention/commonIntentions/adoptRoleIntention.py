from data.coreData import Coordinate, MapcRole

from data.intention import Observation
from agent.intention.agentIntention import AgentIntention
from agent.intention.commonIntentions.agitatedTraveltIntention import AgitatedTravelIntention

from agent.action import AgentAction, AdoptAction

class AdoptRoleIntention(AgentIntention):    
    """
    Intention to adopt the given `MapcRole` by
    travelling to the closest role zone and adopting
    the role.\n
    Finished when the given `MapcRole` is adopted.
    """

    agitatedTravelIntention: AgitatedTravelIntention | None
    mapcRole: MapcRole

    def __init__(self, mapcRole: MapcRole) -> None:
        self.agitatedTravelIntention = None
        self.mapcRole = mapcRole

    async def planNextAction(self, observation: Observation) -> AgentAction:
        # Get the closest free role zone
        closestRoleZone = observation.map.getClosestRoleZone(observation.agentCurrentCoordinate)
        if self.agitatedTravelIntention is None or \
            Coordinate.isCloserNewCoordinate(observation.agentCurrentCoordinate, next(iter(self.agitatedTravelIntention.coordinates)), closestRoleZone):

            self.agitatedTravelIntention = AgitatedTravelIntention(set([closestRoleZone]), True)
        
        # Travel there if the Agent is not already there
        if not self.agitatedTravelIntention.checkFinished(observation):
            return await self.agitatedTravelIntention.planNextAction(observation)
        # Adopt the Role
        else:
            return AdoptAction(self.mapcRole.name) 

    def checkFinished(self, observation: Observation) -> bool:
        return self.mapcRole == observation.agentMapcRole
    
    def updateCoordinatesByOffset(self, offsetCoordinate: Coordinate) -> None:
        if self.agitatedTravelIntention is not None:
            self.agitatedTravelIntention.updateCoordinatesByOffset(offsetCoordinate)
    
    def normalizeCoordinates(self) -> None:
        if self.agitatedTravelIntention is not None:
            self.agitatedTravelIntention.normalizeCoordinates()

    def explain(self) -> str:
        return "adopting role " + self.mapcRole.name
