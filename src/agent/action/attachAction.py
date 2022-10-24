from mapc2022 import Agent as MapcAgent, AgentActionError as MapcAgentActionError

from data.coreData import Direction, MapValueEnum
from agent.action.agentAction import AgentAction

class AttachAction(AgentAction):
    """
    Attaches an entity, which is adjacent
    to the `Agent` to the given `Direction`.
    Only performable if the current `Agent` role can perform this action.\n
    Contains information about the attached entity, which can be used for tracking
    the attached entities.
    """

    direction: Direction
    entityType: MapValueEnum
    details: str

    def __init__(self, direction: Direction, entityType: MapValueEnum, details: str) -> None:
        self.direction = direction
        self.entityType = entityType
        self.details = details
    
    def perform(self, agent: MapcAgent) -> str:
        """
        Sends the attach action to the simulation server
        and returns the result of it.
        The result does not contains information about the attached entity.
        """

        try:
            agent.attach(str(self.direction))
            return "success"
        except MapcAgentActionError as e:
            return e.args[0]