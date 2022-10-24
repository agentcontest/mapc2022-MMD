from mapc2022 import Agent as MapcAgent, AgentActionError as MapcAgentActionError

from data.coreData import Coordinate, AttachedEntity
from agent.action.agentAction import AgentAction

class ConnectAction(AgentAction):
    """
    Connects the given attached entity to the
    other `Agent's` given attached entity.
    Only performable if the current `Agent` role can perform this action.\n
    A connection is established between the two `Agents`, making them stuck to each other.
    """

    toAgentId: str
    relCoord: Coordinate
    toAttachedEntity: AttachedEntity | None

    def __init__(self, toAgentId: str, relCoord: Coordinate, toAttachedEntity: AttachedEntity = None) -> None:
        self.toAgentId = toAgentId
        self.relCoord = relCoord
        self.toAttachedEntity = toAttachedEntity
    
    def perform(self, agent: MapcAgent) -> str:
        """
        Sends the connect action to the simulation server
        and returns the result of it.
        Note that it does not contain information about the attached entities.
        """

        try:
            agent.connect(self.toAgentId, (self.relCoord.x, self.relCoord.y))
            return "success"
        except MapcAgentActionError as e:
            return e.args[0]