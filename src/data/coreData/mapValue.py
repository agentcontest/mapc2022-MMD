from data.coreData.enums import MapValueEnum

class MapValue:
    """
    Represents a map value of the simulation map.
    It contains informations about the entity
    and the simulation step when was it noted.
    """

    value: MapValueEnum
    simulationStep: int
    details: str

    def __init__(self, value: MapValueEnum, details: str, simulationStep: int) -> None:
        self.value = value
        self.simulationStep = simulationStep
        self.details = details
    
    def update(self, mapValue: 'MapValue') -> None:
        """
        Updates the current `MapValue` values with the other ones.
        """

        self.value = mapValue.value
        self.simulationStep = mapValue.simulationStep
        self.details = mapValue.details
    
    def __eq__(self, other) -> bool:
        return (isinstance(other, self.__class__) and self.value == other.value and
            self.simulationStep == other.simulationStep and (self.details == other.details
                or (self.value == MapValueEnum.AGENT and self.simulationStep == 0)))