from data.coreData import Coordinate, MapValue, MapValueEnum

class DispenserMap():
    """
    Stores a map of dispensers grouped by block types.
    """

    dispensers: dict[str, set[Coordinate]]

    def __init__(self) -> None:
        self.dispensers = dict()
    
    def addDispenser(self, type: str, coordinate: Coordinate) -> None:
        """
        Adds new dispenser to given type.
        """

        if type not in self.dispensers:
            self.dispensers[type] = set()
        
        self.dispensers[type].add(coordinate)

    def getDispenserCoordsByType(self, type: str) -> list[Coordinate]:
        """
        Returns dispenser `Coordinates` by the given type.
        """

        return list(self.dispensers[type])
    
    def getAllDispenserCoords(self) -> list[Coordinate]:
        """
        Returns all the dispender `Coordinates` regardless of type.
        """

        return list(c for ds in self.dispensers.values() for c in ds)
    
    def getDispenserMapValueByCoord(self, coordinate: Coordinate) -> MapValue:
        """
        Returns a dispenser `Coordinate` mapped into `MapValue`
        """

        return MapValue(MapValueEnum.DISPENSER, [type for type, ds in self.dispensers.items() if coordinate in ds][0], 0)