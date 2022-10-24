import asyncio
import functools

from data.coreData import Coordinate
from data.intention import Observation

from agent.intention.agentIntention import AgentIntention
from agent.action import AgentAction
from agent.pathfinder import PathFinder, PathFinderData

class TravelIntention(AgentIntention):
    """
    Intention which can be used when traveling is needed.
    It uses the `PathFinder` and its goal is completed
    when it has reached its destination
    """

    coordinate: Coordinate  # Destination coordinate
    ignoreMarkers: bool     # Ignore clear events, used at escaping
    pathFinder: PathFinder

    def __init__(self, coordinate: Coordinate, ignoreMarkers: bool = False) -> None:
        self.coordinate = coordinate.copy()
        self.ignoreMarkers = ignoreMarkers
        self.pathFinder = PathFinder()
    
    async def planNextAction(self, observation: Observation) -> AgentAction:
        pathFinderParams = PathFinderData(observation.map, observation.agentCurrentCoordinate,
            observation.agentMapcRole.getSpeed(len(observation.agentData.attachedEntities)), observation.simDataServer.getClearEnergyCost(),
            observation.agentData.energy, observation.simDataServer.getAgentMaxEnergy(),
            observation.agentMapcRole.clearChance, observation.simDataServer.getClearConstantCost(),
            observation.simDataServer.pathFindingMaxIteration, observation.agentMapcRole.vision,
            [e.relCoord for e in observation.agentData.attachedEntities])

        return await asyncio.get_running_loop().run_in_executor(None,
            functools.partial(self.pathFinder.findNextAction, pathFinderParams, self.coordinate, self.ignoreMarkers))

    def checkFinished(self, observation: Observation) -> bool:
        return observation.agentCurrentCoordinate == self.coordinate
    
    def updateCoordinatesByOffset(self, offsetCoordinate: Coordinate) -> None:
        self.coordinate.updateByOffsetCoordinate(offsetCoordinate)
    
    def normalizeCoordinates(self) -> None:
        self.coordinate.normalize()

    def explain(self) -> str:
        explanation  = "path " + self.pathFinder.explanation
        return explanation
