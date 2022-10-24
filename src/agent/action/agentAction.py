from abc import ABC, abstractclassmethod
from mapc2022 import Agent as MapcAgent

class AgentAction(ABC):
    """
    Abstraction for `Agent` actions sent to the simulation server.\n
    Wraps all the required parameters for the given action, so it can
    be sent of its own.
    """

    @abstractclassmethod
    def perform(self, _: MapcAgent) -> str:
        """
        Sends the the action to the simulation the server
        and returns the result of it: succeeded or a fail code.
        """

        pass