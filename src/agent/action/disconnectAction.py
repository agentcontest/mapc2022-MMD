from mapc2022 import Agent as MapcAgent, AgentActionError as MapcAgentActionError

from data.coreData import Coordinate
from agent.action.agentAction import AgentAction

class DisconnectAction(AgentAction):
    """
    Disconnects the given attached entity from the
    other `Agent's` given attached entity.\n
    A connection is removed from the two `Agents`, making them unstuck from each other,
    if there is no ther connections between them.
    """

    firstRelCoord: Coordinate
    secondRelCoord: Coordinate

    def __init__(self, firstRelCoord: Coordinate, secondRelCoord: Coordinate) -> None:
        self.firstRelCoord = firstRelCoord
        self.secondRelCoord = secondRelCoord
    
    def perform(self, agent: MapcAgent) -> str:
        """
        Sends the disconnect action to the simulation server
        and returns the result of it.
        Note that it does not contain information about the attached entities.
        """

        try:
            agent.disconnect((self.firstRelCoord.x, self.firstRelCoord.y),
                (self.secondRelCoord.x, self.secondRelCoord.y))
            return "success"
        except MapcAgentActionError as e:
            return e.args[0]