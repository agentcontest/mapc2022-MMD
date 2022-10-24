from data.coreData.enums import AgentActionEnum

class MapcRole:
    """
    Represents an agent role defined by the simulation.
    """

    name: str                       # Identifier
    vision: int
    clearChance: float
    clearMaxDistance: int
    actions: list[AgentActionEnum]
    speed: list[int]

    def __init__(self, name: str, vision: int, clearChance: float, clearMaxDistance: int, actions: list[str], speed: list[int]) -> None:
        self.name = name
        self.vision = vision
        self.clearChance = clearChance
        self.clearMaxDistance = clearMaxDistance
        self.actions = [AgentActionEnum[action.upper()] for action in actions]
        self.speed = speed
    
    def canPerformAction(self, action: AgentActionEnum) -> bool:
        """
        Returns if it can perform the given action.
        """

        return action in self.actions
    
    def getSpeed(self, attachedCount: int) -> int:
        """
        Returns the speed with the given amount of attached entities. Its value is always maximum 2.
        """

        return min(self.speed[-1] if attachedCount >= len(self.speed) else self.speed[attachedCount], 2)

    def getFreeSpeed(self) -> int:
        """
        Returns the speed if nothing is attached to the agent. Its value is always maximum 2.
        """

        return min(self.speed[0], 2)
    
    def __eq__(self, other) -> bool:
        return isinstance(other, self.__class__) and self.name == other.name
    
    def __neq__(self, other) -> bool:
        return not self.__eq__(other)
    
    def __hash__(self) -> int:
        return hash(self.name)
    
    def __str__(self) -> str:
        return self.name
    
    def __repr__(self) -> str:
        return self.__str__()