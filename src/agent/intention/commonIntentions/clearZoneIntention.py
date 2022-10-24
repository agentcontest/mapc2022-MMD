from random import random
from data.coreData import Coordinate, MapValueEnum

from data.intention import Observation
from agent.intention.agentIntention import AgentIntention
from agent.intention.commonIntentions.skipIntention import SkipIntention
from agent.intention.commonIntentions.clearTargetIntention import ClearTargetIntention

from agent.action import AgentAction, ClearAction

class ClearZoneIntention(AgentIntention):
    """
    Intention to clear the given `Coordinates`: clear `Block`,
    `Obstacle` or `Agent`. It's finished if all the target `Coordinates` are
    empty or there's `Dispenser` on them.\n
    Note that it does not use shooting range, only clears `Coordinates`
    which are adjacent to the `Agent`.
    """

    clearTargetIntention: ClearTargetIntention | None
    skipIntention: SkipIntention
    baseCoordinate: Coordinate

    def __init__(self, baseCoordinate: Coordinate) -> None:
        self.clearTargetIntention = None
        self.skipIntention = SkipIntention(True)

        self.baseCoordinate = baseCoordinate

    async def planNextAction(self, observation: Observation) -> AgentAction:
        # If there is nothing to clear, then try to shoot enemy Agents
        clearableCoords = self.getClearableCoords(observation)
        if not any(clearableCoords):
            if observation.agentMapcRole.clearMaxDistance > 1:
                enemyCoord = self.getClearableEnemy(observation)
                if enemyCoord is not None:
                    return ClearAction(Coordinate.getRelativeCoordinate(observation.agentCurrentCoordinate,enemyCoord))
            
            # If not one is available in shooting range then just skip
            return await self.skipIntention.planNextAction(observation)
        
        # Get closest clearable Coordinate
        closestClearableCoord = min(
            clearableCoords,
            key = lambda c: Coordinate.distance(observation.agentCurrentCoordinate, c))

        if self.clearTargetIntention is None or self.clearTargetIntention.targetCoordinate != closestClearableCoord:
            self.clearTargetIntention = ClearTargetIntention(closestClearableCoord)
        
        # Only clear if eneergy is not low
        lowEnergy = observation.simDataServer.getClearEnergyCost() * 2.4 > observation.agentData.energy
        if lowEnergy and self.clearTargetIntention.targetCoordinate in observation.agentCurrentCoordinate.neighbors():
            return await self.skipIntention.planNextAction(observation)
        
        # Some chance to shoot enemies instead
        if random() > 0.5:
            if observation.agentMapcRole.clearMaxDistance > 1:
                enemyCoord = self.getClearableEnemy(observation)
                if enemyCoord:
                    return ClearAction(Coordinate.getRelativeCoordinate(observation.agentCurrentCoordinate,enemyCoord))

        # Clear target area element
        return await self.clearTargetIntention.planNextAction(observation)

    def checkFinished(self, observation: Observation) -> bool:
        return not any(self.getClearableCoords(observation))

    def getClearableEnemy(self, observation: Observation) -> Coordinate:
        """
        Returns an enemy `Agent's` `Coordinate` within shooting range.
        """

        clearableCoords = list(
            filter(lambda coord: observation.map.getMapValueEnum(coord) == MapValueEnum.AGENT and  
                observation.map.getMapValue(coord).details != observation.simDataServer.teamName and
                coord not in observation.map.goalZones,
                observation.agentCurrentCoordinate.neighbors(True, observation.agentMapcRole.clearMaxDistance)))
        
        return min([coord for coord in clearableCoords],
            key = lambda coord: Coordinate.manhattanDistance(coord,observation.agentCurrentCoordinate),
            default = None)

    def getClearableCoords(self, observation: Observation) -> list[Coordinate]:
        """
        Returns the remaining clearable and unknown `Coordinates`.
        """

        return list(
            filter(lambda coord: observation.map.getMapValueEnum(coord)
                in [MapValueEnum.UNKNOWN, MapValueEnum.OBSTACLE, MapValueEnum.BLOCK] and \
                    coord not in [observation.agentCurrentCoordinate.getShiftedCoordinate(c)
                        for c in observation.agentData.perceptAttachedRelCoords],
                self.baseCoordinate.neighbors(True, observation.agentMapcRole.vision)))

    def updateCoordinatesByOffset(self, offsetCoordinate: Coordinate) -> None:
        if self.baseCoordinate is not None:
            self.baseCoordinate.updateByOffsetCoordinate(offsetCoordinate)

        if self.clearTargetIntention is not None:
            self.clearTargetIntention.updateCoordinatesByOffset(offsetCoordinate)
        
        self.skipIntention.updateCoordinatesByOffset(offsetCoordinate)
    
    def normalizeCoordinates(self) -> None:
        if self.baseCoordinate is not None:
            self.baseCoordinate.normalize()

        if self.clearTargetIntention is not None:
            self.clearTargetIntention.normalizeCoordinates()
        
        self.skipIntention.normalizeCoordinates()

    def explain(self) -> str:
        return "clearing zone " + str(self.baseCoordinate)
