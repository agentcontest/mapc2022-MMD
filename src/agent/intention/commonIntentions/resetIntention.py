from data.coreData import Coordinate
from data.intention import Observation

from agent.intention.mainAgentIntention import MainAgentIntention
from agent.action import AgentAction, DetachAction

class ResetIntention(MainAgentIntention):    
    """
    Intention used when the `Agents` got disconnected,
    its goal is to detach every possible attached, adjacent
    entity.
    """

    def getPriority(self) -> float:
        return 2.5

    async def planNextAction(self, observation: Observation) -> AgentAction:
        return DetachAction(Coordinate.getDirection(Coordinate.origo(), self.getPossibleAttachedNeighbors(observation)[0]))

    def checkFinished(self, observation: Observation) -> bool:
        return not any(self.getPossibleAttachedNeighbors(observation))
    
    def updateCoordinatesByOffset(self, _: Coordinate) -> None:
        pass
    
    def normalizeCoordinates(self) -> None:
        pass

    def explain(self) -> str:
        return "resetting"
    
    def getPossibleAttachedNeighbors(self, observation: Observation) -> list[Coordinate]:
        return [c for c in observation.agentData.perceptAttachedRelCoords
            if Coordinate.manhattanDistance(Coordinate.origo(), c) == 1]