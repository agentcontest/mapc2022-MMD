from data.coreData.coordinate import Coordinate

class TaskRequirement():
    """
    Represent a task requirement, in which relative `Coordinate`
    must the the given type of block.
    Note: the details here is unused.
    """

    coordinate: Coordinate
    details: str
    type: str

    def __init__(self, x: int, y: int, details: str, type: str) -> None:
        self.coordinate = Coordinate(x, y, False)
        self.details = details
        self.type = type