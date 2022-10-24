from data.coreData import AgentIntentionRole
from data.intention import Observation

class IntentionDataServer():
    """
    Information repository about agent intentions,
    contains `Observations` and `AgentIntentionRoles`.
    """

    observations: dict[str, Observation]
    agentIntentionRoles: dict[str, AgentIntentionRole]

    def __init__(self) -> None:
        self.observations = dict()
        self.agentIntentionRoles = dict()
    
    def addAgentObservation(self, agentId: str, observation: Observation) -> None:
        """
        Stores an `Agent's` `Observation` for the current step.
        """

        self.observations[agentId] = observation
    
    def getAgentOservation(self, agentId: str) -> Observation:
        """
        Returns an `Agent's` `Observation` for the current step.
        """

        return self.observations[agentId]
    
    def addAgentIntentionRole(self, agentId: str, agentIntentionRole: AgentIntentionRole) -> None:
        """
        Stores an `Agent's` intention role.
        """

        self.agentIntentionRoles[agentId] = agentIntentionRole
    
    def getAgentIntentionRole(self, agentId: str) -> AgentIntentionRole:
        """
        Returns an `Agent's` intention role.
        """

        return self.agentIntentionRoles[agentId]