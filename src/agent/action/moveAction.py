from mapc2022 import Agent as MapcAgent, AgentActionError as MapcAgentActionError

from data.coreData import Direction
from agent.action.agentAction import AgentAction

class MoveAction(AgentAction):
    """
    Moves the `Agent` to the given `Directions`. Note that
    not every of them will succeed.\n
    """

    directions: list[Direction]

    def __init__(self, directions: list[Direction]) -> None:
        self.directions = directions
    
    def perform(self, agent: MapcAgent) -> str:
        """
        Sends the move action to the simulation server
        and returns the result of it.\n
        If succeeded, all of the moves were completed,
        if failed then none of them, partial means at least
        one of them succeeded. The later can make the `Agents`
        disorientated, since they don't know how much they moved.
        """

        try:
            agent.move([str(direction) for direction in self.directions])
            return "success"
        except MapcAgentActionError as e:
            return e.args[0]