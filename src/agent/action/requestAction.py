from mapc2022 import Agent as MapcAgent, AgentActionError as MapcAgentActionError

from data.coreData import Direction
from agent.action.agentAction import AgentAction

class RequestAction(AgentAction):
    """
    Requests a `Block` from a `Dispenser`, which is adjacent
    to the `Agent` to the given `Direction`.
    Only performable if the current `Agent` role can perform this action.
    """
    
    direction: Direction

    def __init__(self, direction: Direction) -> None:
        self.direction = direction
    
    def perform(self, agent: MapcAgent) -> str:
        """
        Sends the request action to the simulation server
        and returns the result of it.
        """

        try:
            agent.request(str(self.direction))
            return "success"
        except MapcAgentActionError as e:
            return e.args[0]