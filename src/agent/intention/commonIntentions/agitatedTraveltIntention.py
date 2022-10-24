from data.coreData import Coordinate, MapValueEnum

from data.intention import Observation
from agent.intention.agentIntention import AgentIntention
from agent.intention.commonIntentions.waitIntention import WaitIntention

from agent.action import AgentAction

class AgitatedTravelIntention(AgentIntention):
    """
    Extended `TravelIntention`, which travels to the given goal `Coordinates`, but
    if all of them are occupied, then it won't just wait, it tries to get as close as possible.\n
    Its goal is to get to one of the given target `Coordinates`.
    """

    coordinates: set[Coordinate]
    allowRotateDuringWait: bool
    waitIntention: WaitIntention | None

    def __init__(self, coordinates: set[Coordinate], allowRotateDuringWait: bool) -> None:
        self.waitIntention = None

        self.coordinates = coordinates
        self.allowRotateDuringWait = allowRotateDuringWait
    
    async def planNextAction(self, observation : Observation) -> AgentAction:
        # It not initialized or chosen target is occupied or current target is not
        # in the target zones and there is a free target zone
        if self.waitIntention is None or \
            observation.map.getMapValueEnum(self.waitIntention.travelIntention.coordinate) not in [MapValueEnum.EMPTY, MapValueEnum.OBSTACLE, MapValueEnum.UNKNOWN] or \
            (self.waitIntention.travelIntention.coordinate not in self.coordinates and \
                any(observation.map.getMapValueEnum(coord) in [MapValueEnum.EMPTY, MapValueEnum.OBSTACLE, MapValueEnum.UNKNOWN] for coord in self.coordinates)):

            # Search for free target Coordinates, which is not reserved for a Task
            freeGoalCoordinates = list(filter(lambda coord: observation.map.getMapValueEnum(coord)
                in [MapValueEnum.EMPTY, MapValueEnum.OBSTACLE, MapValueEnum.UNKNOWN] and not observation.map.isCoordinateReservedForTask(coord),
                self.coordinates))

            # If there is a free target Coordinate then travel to it
            if any(freeGoalCoordinates):
                self.waitIntention = WaitIntention(min(freeGoalCoordinates,
                    key = lambda coord: Coordinate.distance(coord, observation.agentCurrentCoordinate)),
                    self.allowRotateDuringWait)
            # Else search the closest free Coordinate to the target Coordinates
            else:
                self.waitIntention = WaitIntention(self.findClosestFreeCoordFromDestinations(observation),
                    self.allowRotateDuringWait)

        return await self.waitIntention.planNextAction(observation)

    def checkFinished(self, observation: Observation) -> bool:
        return observation.agentCurrentCoordinate in self.coordinates
    
    def updateCoordinatesByOffset(self, offsetCoordinate: Coordinate) -> None:
        self.coordinates = set([coord.getShiftedCoordinate(offsetCoordinate) for coord in self.coordinates])
        
        if self.waitIntention is not None:
            self.waitIntention.updateCoordinatesByOffset(offsetCoordinate)

    def normalizeCoordinates(self) -> None:
        self.coordinates = set([coord.copy() for coord in self.coordinates])
        
        if self.waitIntention is not None:
            self.waitIntention.normalizeCoordinates()

    def explain(self) -> str:
        return "agitated travelling "
    
    def findClosestFreeCoordFromDestinations(self, observation: Observation) -> Coordinate:
        """
        Returns the closest free (not `Agent` or `Marker`) `Coordinate` to
        the target `Coordinates`.
        """

        # Get the closest target Coordinate
        nearestGoalCoordinate = min(self.coordinates,
            key = lambda coord: Coordinate.distance(coord, observation.agentCurrentCoordinate))

        # Search the closest Coordinate to the `nearestGoalCoordinate`
        searchRange = 1
        closestFreeCordinates = list(filter(
            lambda coord: observation.map.getMapValueEnum(coord) in [MapValueEnum.EMPTY, MapValueEnum.OBSTACLE, MapValueEnum.UNKNOWN]
                and not observation.map.isCoordinateReservedForTask(coord),
            nearestGoalCoordinate.getVisionBorderCoordinates(searchRange)))
                
        while not any(closestFreeCordinates):
            searchRange += 1
            closestFreeCordinates = list(filter(
                lambda coord: observation.map.getMapValueEnum(coord) in [MapValueEnum.EMPTY, MapValueEnum.OBSTACLE, MapValueEnum.UNKNOWN],
                nearestGoalCoordinate.getVisionBorderCoordinates(searchRange)))
        
        return min(closestFreeCordinates,
            key = lambda coord: Coordinate.distance(coord, observation.agentCurrentCoordinate))
