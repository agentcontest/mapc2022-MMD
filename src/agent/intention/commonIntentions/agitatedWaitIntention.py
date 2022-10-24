from data.coreData import Coordinate

from data.intention import Observation
from agent.intention.agentIntention import AgentIntention
from agent.intention.commonIntentions.agitatedTraveltIntention import AgitatedTravelIntention
from agent.intention.commonIntentions.skipIntention import SkipIntention

from agent.action import AgentAction

class AgitatedWaitIntention(AgentIntention):
    """
    `AgitatedTravelIntention` which waits at one of the given target
    `Coordinates` forever after the `Agent` travelled there, has no goal.
    """
    
    agitatedTravelIntention: AgitatedTravelIntention
    skipIntention: SkipIntention

    def __init__(self, coordinates: set[Coordinate], allowRotateDuringWait: bool) -> None:
        self.agitatedTravelIntention = AgitatedTravelIntention(coordinates, allowRotateDuringWait)
        self.skipIntention = SkipIntention(allowRotateDuringWait)
    
    async def planNextAction(self, observation : Observation) -> AgentAction:
        # If not reached the given Coordinates then travel to them
        if not self.agitatedTravelIntention.checkFinished(observation):
            return await self.agitatedTravelIntention.planNextAction(observation)
        # Else wait
        else:
            return await self.skipIntention.planNextAction(observation)

    def checkFinished(self, _: Observation) -> bool:
        return False
    
    def updateCoordinatesByOffset(self, offsetCoordinate: Coordinate) -> None:
        self.agitatedTravelIntention.updateCoordinatesByOffset(offsetCoordinate)
        self.skipIntention.updateCoordinatesByOffset(offsetCoordinate)

    def normalizeCoordinates(self) -> None:
        self.agitatedTravelIntention.normalizeCoordinates()
        self.skipIntention.normalizeCoordinates()

    def explain(self) -> str:
        return "agitated waiting "
