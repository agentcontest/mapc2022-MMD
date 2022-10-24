from data.coreData.coordinate import Coordinate
from data.coreData.enums import MapValueEnum

class AttachedEntity:
    """
    Represents an attached entity which is attached to an another entity. It can be either a block or an agent
    """

    relCoord: Coordinate
    entityType: MapValueEnum
    details: str
    attachedEntities: list['AttachedEntity']

    def __init__(self, relCoord: Coordinate, entityType: MapValueEnum, details: str) -> None:
        self.relCoord = relCoord
        self.entityType = entityType
        self.details = details
        self.attachedEntities = []
    
    def addAttachEntity(self, attachedEntity: 'AttachedEntity') -> None:
        self.attachedEntities.append(attachedEntity)

    def __eq__(self, other) -> bool:
        return isinstance(other, self.__class__) and self.relCoord == other.relCoord
    
    def __neq__(self, other) -> bool:
        return not self.__eq__(other)
    
    def __hash__(self) -> int:
        return self.relCoord.__hash__()