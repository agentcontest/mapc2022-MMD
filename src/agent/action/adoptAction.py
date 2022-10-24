from mapc2022 import Agent as MapcAgent, AgentActionError as MapcAgentActionError

from agent.action.agentAction import AgentAction

class AdoptAction(AgentAction):
    """
    Changes the `Agent's` current role to the given one.
    Note that it can only succeed if the `Agent` is in
    a goal zone.
    """

    def __init__(self, roleName: str) -> None:
        self.roleName = roleName
    
    def perform(self, agent: MapcAgent) -> str:
        """
        Sends the adopt action to the simulation server
        and returns the result of it.
        """

        try:
            agent.adopt(self.roleName)
            return "success"
        except MapcAgentActionError as e:
            return e.args[0]