from mapc2022 import Agent as MapcAgent, AgentActionError as MapcAgentActionError

from data.coreData import RotateDirection
from agent.action.agentAction import AgentAction

class RotateAction(AgentAction):
    """
    Rotates the `Agent` (and its attached entities)
    to the given `Direction`.
    """

    rotateDirection: RotateDirection

    def __init__(self, rotateDirection: RotateDirection) -> None:
        self.rotateDirection = rotateDirection

    def perform(self, agent: MapcAgent) -> str:
        """
        Sends the rotate action to the simulation server
        and returns the result of it.
        """

        try:
            agent.rotate(str(self.rotateDirection))
            return "success"
        except MapcAgentActionError as e:
            return e.args[0]