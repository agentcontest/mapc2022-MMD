from data.coreData import Coordinate, AgentActionEnum, AttachedEntity
from data.wrapper import DynamicPerceptWrapper

class AgentData():
    """
    Contains data about a given agent which are required for intentions.
    """

    id: str
    energy: int
    deactivated: bool
    lastAction: AgentActionEnum
    lastActionResult: str
    attachedEntities: list[AttachedEntity]
    perceptAttachedRelCoords: list[Coordinate]
    dynamicPerceptWrapper: DynamicPerceptWrapper

    def __init__(self, id: str, energy: int, deactivated: bool,
        lastAction : AgentActionEnum, lastActionResult: str,
        attachedEntities: list[AttachedEntity], perceptAttachedRelCoords: list[Coordinate],
        dynamicPerceptWrapper: DynamicPerceptWrapper) -> None:

        self.id = id
        self.energy = energy
        self.deactivated = deactivated
        self.lastAction = lastAction
        self.lastActionResult = lastActionResult
        self.attachedEntities = attachedEntities
        self.perceptAttachedRelCoords = perceptAttachedRelCoords
        self.dynamicPerceptWrapper = dynamicPerceptWrapper
    
    @property
    def lastActionSucceeded(self) -> bool:
        """
        Returns if the last agent action has succeeded.
        """

        return self.lastActionResult == "success"
