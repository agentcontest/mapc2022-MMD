from abc import abstractclassmethod
from agent.intention.agentIntention import AgentIntention

class MainAgentIntention(AgentIntention):
    """
    Standalone `AgentIntention` which can be handled by
    the `IntentionHandler`. The `IntentionHandler` priorizies these (lowest is the first)
    by a priority value (which can be retrieved using `getPriority`).\n
    Basically the same as `AgentIntention`, but it has a priority.
    """

    @abstractclassmethod
    def getPriority(self) -> float:
        """
        Returns the priority of `MainAgentIntention`.
        """

        pass