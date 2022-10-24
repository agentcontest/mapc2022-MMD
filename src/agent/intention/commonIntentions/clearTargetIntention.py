from agent.intention.commonIntentions import skipIntention
from data.coreData import Coordinate, MapValueEnum

from data.intention import Observation
from agent.intention.agentIntention import AgentIntention
from agent.intention.commonIntentions.waitIntention import TravelIntention, SkipIntention

from agent.action import AgentAction, ClearAction

class ClearTargetIntention(AgentIntention):
    """
    Intention to clear the given `Coordinate`: clear `Block`,
    `Obstacle` or `Agent`. It's finished if the target `Coordinate` is
    empty or there's a `Dispenser` on it.\n
    Note that it does not use shooting range, only clears `Coordinates`
    which are adjacent to the `Agent`.
    """

    travelIntention: TravelIntention | None
    targetCoordinate: Coordinate

    def __init__(self, targetCoordinate: Coordinate) -> None:
        self.travelIntention = None
        self.finished = False
        self.skipIntention = SkipIntention(True)
        self.targetCoordinate = targetCoordinate
    
    async def planNextAction(self, observation: Observation) -> AgentAction:
        # If the given area is unknown then travel there to get information about it
        if observation.map.getMapValueEnum(self.targetCoordinate) == MapValueEnum.UNKNOWN:
            if self.travelIntention is None:
                self.travelIntention = TravelIntention(self.targetCoordinate)
            
            return await self.travelIntention.planNextAction(observation)
        
        # Get free neighbors
        freeNeighbors = list(filter(lambda c: c == observation.agentCurrentCoordinate or observation.map.getMapValueEnum(c) not in [MapValueEnum.AGENT, MapValueEnum.BLOCK],
            [n for n in self.targetCoordinate.neighbors()]))

        # If there are is no free coordinate then finish,
        # it's not this intention's responsibility to handle this case
        if not any(freeNeighbors):
            self.finished = True
            return await self.skipIntention.planNextAction(observation)

        # Get the closest free one from where the shot can be made
        closestFreeNeighbor = min(
            freeNeighbors,
            key = lambda c: Coordinate.distance(observation.agentCurrentCoordinate, c))
        
        if self.travelIntention is None or self.travelIntention.coordinate != closestFreeNeighbor:
            self.travelIntention = TravelIntention(closestFreeNeighbor)
        
        # Travel to the chosen closest free Coordinate if the Agent is not there already
        if not self.travelIntention.checkFinished(observation):
            return await self.travelIntention.planNextAction(observation)
        # If the Agent is there then shoot
        else:
            return ClearAction(Coordinate.getRelativeCoordinate(observation.agentCurrentCoordinate, self.targetCoordinate))

    def checkFinished(self, observation: Observation) -> bool:
        return self.finished or observation.map.getMapValueEnum(self.targetCoordinate) in [MapValueEnum.EMPTY, MapValueEnum.DISPENSER]
    
    def updateCoordinatesByOffset(self, offsetCoordinate: Coordinate) -> None:
        if self.travelIntention is not None:
            self.travelIntention.updateCoordinatesByOffset(offsetCoordinate)

        self.targetCoordinate.updateByOffsetCoordinate(offsetCoordinate)
    
    def normalizeCoordinates(self) -> None:
        if self.travelIntention is not None:
            self.travelIntention.normalizeCoordinates()

        self.targetCoordinate.normalize()

    def explain(self) -> str:
        return "clearing " + str(self.targetCoordinate)