from typing import Tuple

from data.coreData import Coordinate, MapValue, MapValueEnum
from data.map import DynamicMap, MapUpdateData

class MapServer:
    """
    Repository which contains information about `DynamicMaps`
    for `Agents`. Supports algorithms for merging `DynamicMaps`
    and calculated the map dimensions.
    """
    
    aliasis: dict[str, int]
    maps: dict[int, DynamicMap]
    nextMapId: int
    gridWidth: int | None
    gridHeight: int | None
    mapUnknownCoordSearchMaxIter: int
    currentDynamicPerceptWrappers: dict[str, dict[Coordinate, MapValue]]

    def __init__(self, mapUnknownCoordSearchMaxIter: int) -> None:
        self.aliasis = dict()
        self.maps = dict()
        self.nextMapId = 0

        self.gridWidth = None
        self.gridHeight = None

        self.mapUnknownCoordSearchMaxIter = mapUnknownCoordSearchMaxIter
        self.currentDynamicPerceptWrappers = dict()
    
    def registerNewMap(self, agentId: str, markerPurgeInterval: int, simulationStep: int,
        updateData: MapUpdateData) -> None:
        """
        Registers a new `DynamicMap` belonging to the given `Agent` and
        fills it with initial data (dynamic percept).
        """

        newId = self.generateNewMapId()
        self.aliasis[agentId] = newId
        self.maps[newId] = DynamicMap(newId, agentId, markerPurgeInterval, simulationStep,
                            self.mapUnknownCoordSearchMaxIter, updateData)

    def updateMap(self, agentId: str, simulationStep: int, updateData: MapUpdateData) -> None:
        """
        Updates the `DynamicMap` belonging to the given `Agent` from
        its dynamic percept.
        """

        self.currentDynamicPerceptWrappers[agentId] = updateData.things

        adjustedUpdateData = self.adjustUpdateData(agentId, updateData)
        self.getMap(agentId).addRange(simulationStep, adjustedUpdateData)

    def checkAgentIdentifications(self) -> Tuple[dict[str, Coordinate], bool]:
        """
        Checks the `DynamicMaps` for possible `Agent` identifications for
        merging or calculating map dimensions.\n
        Returns a Tuple: if a merge happened, which `Agents` should update
        their `Coordinates` with the given relative `Coordinate` and
        if a map dimension has been calculated.
        """

        coordOffsetForMergedAgents : dict[str, Coordinate] = dict()
        mapBoundaryReached = False

        # Start identifying other agents using the dynamic percept
        for agentId, dynamicPercept in self.currentDynamicPerceptWrappers.items():
            canditates = []
            
            # Select other agents from the same team that are in the vision
            unknownOtherAgents = [coord for coord, mapValue in dynamicPercept.items() 
                            if mapValue.value == MapValueEnum.AGENT
                                and coord != Coordinate.origo()
                                and mapValue.details == dynamicPercept[Coordinate.origo()].details]
            
            for otherAgentCoord in unknownOtherAgents:
                for otherAgentId, otherDynamicPercept in self.currentDynamicPerceptWrappers.items():

                    # If the other agent sees the current agent from the negated perspective then it is
                    # a possible canditate
                    if (agentId != otherAgentId and otherAgentCoord.negate() in otherDynamicPercept and
                            otherDynamicPercept[otherAgentCoord.negate()].value == MapValueEnum.AGENT and
                            otherDynamicPercept[otherAgentCoord.negate()].details == dynamicPercept[Coordinate.origo()].details):

                        possible = True

                        # Check the surroundig coordinates, if it can be seen by both
                        # agents, but the entity on it differs, then they are not next to each-other
                        for otherCoord, otherMapValue in otherDynamicPercept.items():
                            coord = otherAgentCoord.getShiftedCoordinate(otherCoord, False)
                            if coord in dynamicPercept and dynamicPercept[coord] != otherMapValue:
                                possible = False
                                break
                    
                        # After all if every entity matched, then add it to the possible cantitates
                        if possible:
                            canditates.append((otherAgentId, otherAgentCoord.copy(False)))
                
                currentAgentMap = self.getMap(agentId)
                
                # Identifying must be 100% sure, if more than one canditates are possible, then abort
                if len(canditates) == 1:
                    canditateId = canditates[0][0]
                    canditateRelCoord = canditates[0][1]
                    currentAgentCoordinate = currentAgentMap.getAgentCoordinate(agentId)

                    # If the two agents are not in the same map, then these maps can be merged
                    if self.aliasis[agentId] != self.aliasis[canditateId]:
                        agentIdsToBeUpdated = self.maps[self.aliasis[canditateId]].agentCoordinates.keys()
                        offsetCoord = self.mergeMaps(agentId, canditateId,
                            currentAgentCoordinate.getShiftedCoordinate(canditateRelCoord))

                        for updateableAgentId in agentIdsToBeUpdated:
                            coordOffsetForMergedAgents[updateableAgentId] = offsetCoord      
                    
                    # If the two agents are in the same map, they see each-other, but the coordinates are not correct,
                    # it means one of them passed the map at least once, so at least one of the map dimensions can be calculated
                    elif (self.aliasis[agentId] == self.aliasis[canditateId]
                            and currentAgentMap.getAgentCoordinate(canditateId) !=
                            currentAgentCoordinate.getShiftedCoordinate(canditateRelCoord)):

                        self.calculateMapGridSize(currentAgentMap.getAgentCoordinate(agentId), currentAgentMap.getAgentCoordinate(canditateId),
                                canditateRelCoord, max(dynamicPercept.keys(), key = lambda coord: coord.x).x)
                        mapBoundaryReached = True

        return (coordOffsetForMergedAgents, mapBoundaryReached)

    def mergeMaps(self, firstAgentId: str, secondAgentId: str, othersCoordinateInMyMap: Coordinate) -> Coordinate:
        """
        Merges `DynamicMaps` by two identified `Agent's` location (`Coordinate) and the difference
        `Coordinate` between them. The second is merged into the first and after that it will be deleted.\n
        Returns the coordinate system difference in `Coordinate`.
        """

        firstMapId = self.aliasis[firstAgentId]
        secondMapId = self.aliasis[secondAgentId]

        offsetCoord = self.maps[firstMapId].merge(self.maps[secondMapId], othersCoordinateInMyMap,
                                self.maps[secondMapId].getAgentCoordinate(secondAgentId))

        for agentId, alias in self.aliasis.items():
            if alias == secondMapId:
                self.aliasis[agentId] = firstMapId

        del self.maps[secondMapId]
        print(str(self.getMapCount()) + " map remains")

        return offsetCoord
    
    def calculateMapGridSize(self, agentCoordinate1: Coordinate, agentCoordinate2: Coordinate,
        relCoordinate: Coordinate, agentVision: int) -> None:
        """
        Calculates the map dimension by two identified `Agent's` location (`Coordinate) and the difference
        `Coordinate` between them. The dimensions are set as the `Coordinate` class' static values.\n
        Note that these dimension can be calculated more than once, these values can not be decreased.
        (For example when an `Agent` passed the map more than once,
        meaning the calculated dimensions can be multiple of the real dimensions).
        """

        xDifference = abs(agentCoordinate1.x - agentCoordinate2.x)
        yDifference = abs(agentCoordinate1.y - agentCoordinate2.y)

        widthDifference = abs(agentCoordinate1.x - agentCoordinate2.x + relCoordinate.x)
        heightDifferece = abs(agentCoordinate1.y - agentCoordinate2.y + relCoordinate.y)

        if (self.gridWidth is None or widthDifference < self.gridWidth) and \
            xDifference > agentVision:

            self.gridWidth = widthDifference
            print("map width: " + str(self.gridWidth))
        
        if (self.gridHeight is None or heightDifferece < self.gridHeight) and \
            yDifference > agentVision: 

            self.gridHeight = heightDifferece
            print("map height: " + str(self.gridHeight))

    def getMap(self, agentId: str) -> DynamicMap:
        """
        Returns a `DynamicMap` that belongs to the given `Agent`.
        """

        return self.maps[self.aliasis[agentId]]
    
    def getMapCount(self) -> int:
        """
        Returns the remaining `DynamicMap` count for the simulation. The value is between 1 and `Agent` count.
        """

        return len(self.maps.keys())
    
    def adjustUpdateData(self, agentId: str, data: MapUpdateData) -> MapUpdateData:
        """
        Adjust update data by transforming the `Coordinates` from relative to absolute.
        """

        agentCoordinate = self.getMap(agentId).getAgentCoordinate(agentId)
        adjustedUpdateData = MapUpdateData(
            dict([(key.getShiftedCoordinate(agentCoordinate), value) for key, value in data.things.items()]),
            dict([(key.getShiftedCoordinate(agentCoordinate), value) for key, value in data.markers.items()]),
            dict([(key.getShiftedCoordinate(agentCoordinate), value) for key, value in data.dispensers.items()]),
            [value.getShiftedCoordinate(agentCoordinate) for value in data.goalZones],
            [value.getShiftedCoordinate(agentCoordinate) for value in data.roleZones])

        return adjustedUpdateData

    def generateNewMapId(self) -> int:
        """
        Returns a new unique `DynamicMap` identifier.
        """

        self.nextMapId += 1
        return self.nextMapId