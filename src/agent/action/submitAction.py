from mapc2022 import Agent as MapcAgent, AgentActionError as MapcAgentActionError

from agent.action.agentAction import AgentAction

class SubmitAction(AgentAction):
    """
    Submits a `Task`, turning in the given attached `Blocks`.
    Only performable if the current `Agent` role can perform this action.\n
    Note that if the `Blocks` types and relative positions not match the
    `Task` requirements or if it is expired (passed the deadline or
    removed from the active tasks) then it will fail.
    """

    taskName: str

    def __init__(self, taskName: str) -> None:
        self.taskName = taskName

    def perform(self, agent: MapcAgent) -> str:
        """
        Sends the submit action to the simulation server
        and returns the result of it.
        If succeeded the 'submitted' `Blocks` disappear from
        the simulation.
        """

        try:
            agent.submit(self.taskName)
            return "success"
        except MapcAgentActionError as e:
            return e.args[0]