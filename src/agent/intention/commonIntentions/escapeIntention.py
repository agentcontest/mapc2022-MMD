import asyncio
import functools

from data.coreData import MapValueEnum, Coordinate

from data.intention import Observation
from agent.intention.mainAgentIntention import MainAgentIntention
from agent.intention.commonIntentions.travelIntention import TravelIntention
from agent.intention.commonIntentions.detachBlocksIntention import DetachBlocksIntention

from agent.action import AgentAction
from agent.pathfinder import PathFinder, PathFinderData

class EscapeIntention(MainAgentIntention):
    """
    Intention to escape clear zones, the goal is to
    get out of the clear zone.\n
    Detaches every block and then escapes from the clear zone.
    """

    travelIntention: TravelIntention | None
    detachBlocksIntention: DetachBlocksIntention | None
    pathFinder: PathFinder

    def __init__(self) -> None:
        self.travelIntention = None
        self.pathFinder = PathFinder()
        self.detachBlocksIntention = None
        
    def getPriority(self) -> float:
        return 2.0

    async def planNextAction(self, observation: Observation) -> AgentAction:
        # If there is any attached entity then detach them
        if any(observation.agentData.attachedEntities):
            if self.detachBlocksIntention is None:
                self.detachBlocksIntention = DetachBlocksIntention()
            
            return await self.detachBlocksIntention.planNextAction(observation)

        # If the Agent is free then travel to the closest safe coordinate
        if self.travelIntention is None or observation.map.getMapValueEnum(self.travelIntention.coordinate) \
            in [MapValueEnum.MARKER, MapValueEnum.AGENT, MapValueEnum.BLOCK]:
            
            pathFinderParams = PathFinderData(observation.map, observation.agentCurrentCoordinate,
                observation.agentMapcRole.getSpeed(len(observation.agentData.attachedEntities)), observation.simDataServer.getClearEnergyCost(),
                observation.agentData.energy, observation.simDataServer.getAgentMaxEnergy(),
                observation.agentMapcRole.clearChance, observation.simDataServer.getClearConstantCost(),
                observation.simDataServer.pathFindingMaxIteration, observation.agentMapcRole.vision,
                [e.relCoord for e in observation.agentData.attachedEntities])

            escapeCoord = await asyncio.get_running_loop().run_in_executor(None,
                functools.partial(self.pathFinder.findClosestFreeCoordinate, pathFinderParams))

            self.travelIntention = TravelIntention(escapeCoord, True)
        
        return await self.travelIntention.planNextAction(observation)

    def checkFinished(self, observation: Observation) -> bool:
        return observation.map.getMapValueEnum(observation.agentCurrentCoordinate) != MapValueEnum.MARKER
    
    def updateCoordinatesByOffset(self, offsetCoordinate: Coordinate) -> None:
        if self.travelIntention is not None:
            self.travelIntention.updateCoordinatesByOffset(offsetCoordinate)
        
        if self.detachBlocksIntention is not None:
            self.detachBlocksIntention.updateCoordinatesByOffset(offsetCoordinate)
    
    def normalizeCoordinates(self) -> None:
        if self.travelIntention is not None:
            self.travelIntention.normalizeCoordinates()
        
        if self.detachBlocksIntention is not None:
            self.detachBlocksIntention.normalizeCoordinates()

    def explain(self) -> str:
        if self.travelIntention is not None:
            return "escaping to " + str(self.travelIntention.coordinate)
        else:
            return "escaping to unknown"