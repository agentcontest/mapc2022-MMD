from abc import ABC, abstractclassmethod

from data.coreData import Coordinate

from data.intention import Observation
from agent.action import AgentAction

class AgentIntention(ABC):
    """
    Abstract class which represents an `AgentIntention`.
    An `AgentIntention` is a task for an `Agent`, it can be a part of
    an other, or it can be standalone. `AgentIntentions` gets the required information
    through `Observations`.\n
    Every intention has a goal, which can be checked if it completed (`checkFinished`),
    they can plan next step get reach their goal (`planNextAction`).\n
    `AgentIntentions` store `Coordinates`, so when `DynamicMaps` are merged,
    their `Coordinates` must be shifted if needed (`updateCoordinatesByOffset`).
    The same rule applies when a map dimension is calculated (`normalizeCoordinates`).\n
    `AgentIntentions` can also tell what is going on inside of them (`explain`),
    which can be used for debugging.
    """

    @abstractclassmethod
    async def planNextAction(self, observation: Observation) -> AgentAction:
        """
        Plans and returns the next action to reach its goal.
        """
        pass

    @abstractclassmethod
    def checkFinished(self, observation: Observation) -> bool:
        """
        Returns if it has reached its goal.
        """

        pass

    @abstractclassmethod
    def updateCoordinatesByOffset(self, offsetCoordinate: Coordinate) -> None:
        """
        Shifts the `Coordinates` inside it by the given one.
        """

        pass
    
    @abstractclassmethod
    def normalizeCoordinates(self) -> None:
        """
        Normalized the `Coordinates` inside it.
        """

        pass

    @abstractclassmethod
    def explain(self) -> str:
        """
        Returns an explanation string used for debugging.
        """

        pass