from data.coreData import Coordinate
from data.intention import Observation

from agent.intention.agentIntention import AgentIntention
from agent.intention.commonIntentions.agitatedTraveltIntention import AgitatedTravelIntention

from agent.action import AgentAction

class DistantAgitatedTravelIntention(AgentIntention):
    """
    `AgitatedTravelIntention`, but the goal is to be in the given range
    of the given `Coordinate`.\n
    Its goal is to be within the given range of the the given `Coordinate`.
    """

    agitatedTravelIntention: AgitatedTravelIntention
    centerCoordinate: Coordinate                        # Target area center
    range: int                                          # Maximum distance between the Agent and the centerCoordinate

    def __init__(self, centerCoordinate: Coordinate, range: int, distant: int, allowRotateDuringWait: bool) -> None:
        self.agitatedTravelIntention = AgitatedTravelIntention(set(centerCoordinate.neighbors(True, range, distant)), allowRotateDuringWait)

        self.centerCoordinate = centerCoordinate
        self.range = range
    
    async def planNextAction(self, observation : Observation) -> AgentAction:
        return await self.agitatedTravelIntention.planNextAction(observation)

    def checkFinished(self, observation: Observation) -> bool:
        return Coordinate.manhattanDistance(self.centerCoordinate, observation.agentCurrentCoordinate) <= self.range
    
    def checkReachedGoalCoords(self, observation: Observation) -> bool:
        """
        Returns if it reached the given target `Coordinates`,
        ignoring the given range.
        """

        return self.agitatedTravelIntention.checkFinished(observation)
    
    def updateCoordinatesByOffset(self, offsetCoordinate: Coordinate) -> None:
        self.centerCoordinate.updateByOffsetCoordinate(offsetCoordinate)
        self.agitatedTravelIntention.updateCoordinatesByOffset(offsetCoordinate)

    def normalizeCoordinates(self) -> None:
        self.centerCoordinate.normalize()
        self.agitatedTravelIntention.normalizeCoordinates()

    def explain(self) -> str:
        return "distant agitated traveling to " + str(self.centerCoordinate)
        