from data.coreData.normRegulation import NormRegulation

class Norm:
    """
    Represents a norm which is defined by the simulation.
    Holds a collection of `NormRegulations`
    """

    name: str                           # Identifier
    startStep: int
    untilStep: int
    punishment: int
    regulations: list[NormRegulation]
    handled: bool                       # Contains whether the norm should be handled (ignorable or must complied)
    considered: bool                    # Contains whether the norm will be ignored

    def __init__(self, name: str, startStep: int, untilStep: int, punishment: int, regulations: list[NormRegulation]) -> None:
        self.name = name
        self.startStep = startStep
        self.untilStep = untilStep
        self.regulations = regulations
        self.punishment = punishment
        self.handled = False
        self.considered = True
    
    def __eq__(self, other) -> bool:
        return isinstance(other, self.__class__) and self.name == other.name
    
    def __neq__(self, other) -> bool:
        return not self.__eq__(other)
    
    def __hash__(self) -> int:
        return hash(self.name)