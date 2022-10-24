from mapc2022 import Agent as MapcAgent, AgentActionError as MapcAgentActionError

from agent.action.agentAction import AgentAction

class SkipAction(AgentAction):
    """
    The `Agent` skips this step, it won't do anything.\n
    """

    def perform(self, agent: MapcAgent) -> str:
        """
        Returns the skip action, always succeeds.
        """

        try:
            agent.skip()
        except MapcAgentActionError:
            pass
        return "success"