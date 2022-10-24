from data.coreData.coordinate import Coordinate
from data.coreData.mapValue import MapValue

class MapUpdateData():
    """
    Collection of data to update the map.
    """

    things: dict[Coordinate, MapValue]
    markers: dict[Coordinate, MapValue]
    dispensers: dict[Coordinate, MapValue]
    goalZones: list[Coordinate]
    roleZones: list[Coordinate]

    def __init__(self, things: dict[Coordinate, MapValue], markers: dict[Coordinate, MapValue],
        dispensers: dict[Coordinate, MapValue], goalZones: list[Coordinate],
        roleZones: list[Coordinate]) -> None:

        self.things = things
        self.markers = markers
        self.dispensers = dispensers
        self.goalZones = goalZones
        self.roleZones = roleZones