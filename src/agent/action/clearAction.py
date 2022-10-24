from mapc2022 import Agent as MapcAgent, AgentActionError as MapcAgentActionError

from data.coreData import Coordinate
from agent.action.agentAction import AgentAction

class ClearAction(AgentAction):
    """
    Clears a given `Coordinate`, which must be relative
    to the given `Agent`.\n
    Note that if the target is adjacent to the `Agent`, then
    it can not damage it (its energy won't be decreased).
    """

    relCoordinate: Coordinate

    def __init__(self, relCoordinate: Coordinate) -> None:
        self.relCoordinate = relCoordinate
    
    def perform(self, agent: MapcAgent) -> str:
        """
        Sends the clear action to the simulation server
        and returns the result of it.
        """

        try:
            agent.clear((self.relCoordinate.x, self.relCoordinate.y))
            return "success"
        except MapcAgentActionError as e:
            return e.args[0]