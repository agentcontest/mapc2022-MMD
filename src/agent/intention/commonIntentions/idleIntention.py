from data.coreData import Coordinate

from data.intention import Observation
from agent.intention.mainAgentIntention import MainAgentIntention

from agent.action import AgentAction, SkipAction

class IdleIntention(MainAgentIntention):    
    """
    Intention which only skips forever, it has no goal.
    (placeholder intention if an agent gets no other intention for
    some reasons (it should not happen)).
    """

    def getPriority(self) -> float:
        return 10.0

    async def planNextAction(self, _: Observation) -> AgentAction:
        return SkipAction()

    def checkFinished(self, _: Observation) -> bool:
        return False
    
    def updateCoordinatesByOffset(self, _: Coordinate) -> None:
        pass
    
    def normalizeCoordinates(self) -> None:
        pass

    def explain(self) -> str:
        return "idling"