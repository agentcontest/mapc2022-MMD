from data.coreData.taskRequirement import TaskRequirement

class Task():
    """
    Represents an agent task defined by the simulation.
    """

    name: str
    deadline: int
    reward: int
    requirements: list[TaskRequirement]

    def __init__(self, name: str, deadline: int, reward: int,
        requirements: list[TaskRequirement]) -> None:
        
        self.name = name
        self.deadline = deadline
        self.reward = reward
        self.requirements = requirements
    
    def __eq__(self, other) -> bool:
        return isinstance(other, self.__class__) and self.name == other.name
    
    def __neq__(self, other) -> bool:
        return not self.__eq__(other)
    
    def __hash__(self) -> int:
        return hash(self.name)