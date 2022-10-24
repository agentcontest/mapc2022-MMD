from mapc2022 import Agent as MapcAgent, AgentActionError as MapcAgentActionError

from data.coreData import Direction
from agent.action.agentAction import AgentAction

class DetachAction(AgentAction):
    """
    Detaches an entity, which is adjacent
    to the `Agent` to the given `Direction`.\n
    Note that it not detaches only one entity, it detaches also the ones, that
    are attached to the detached one and so on.
    """

    direction: Direction

    def __init__(self, direction: Direction) -> None:
        self.direction = direction
    
    def perform(self, agent: MapcAgent) -> str:
        """
        Sends the detach action to the simulation server
        and returns the result of it.
        The result does not contains information about which
        attached entities are detached.
        """

        try:
            agent.detach(str(self.direction))
            return "success"
        except MapcAgentActionError as e:
            return e.args[0]