import random
import threading

from data.coreData import Coordinate, MapValue, MapValueEnum
from data.map.mapUpdateData import MapUpdateData
from data.map.dispenserMap import DispenserMap

class DynamicMap():
    """
    Represents the simulation map and stores information about it, like `Agent` `Coordinates`
    and entities. At first every `DynamicMap` belongs to an `Agent`, which will update the map with new values.\n
    These maps can be merged together, one of its data is merged to the other. This can invoked by `Agents`, 
    therefore the map will contain data about all the agents who participated in the merge.\n
    In the begining it's an infite map, however, when the map size is calculated by the `Agent`, all `Coordinates` in it
    will be normalized.
    """

    id: int                                                 # Map identifier
    agentId: str                                            # Agent identifier, in the beginning the map belongs to this Agent
    markerPurgeInterval: int                                # Step count which tells when to delete marker Coordinates (based on when the marker was noted)
    unknownCoordSearchMaxIter: int                          # Iteration upper bound at exploring new unknown map parts
    agentCoordinates: dict[str, Coordinate]                 # Current Coordinates for Agents
    agentStartingCoordinates: dict[str, Coordinate]         # Starting Coordinates for Agents
    agentCoordReservations: dict[str, list[Coordinate]]     # Coordinate reservation for Tasks
    store: dict[Coordinate, MapValue]                       # Entity container, does not stores markers and dispensers
    markers: dict[Coordinate, MapValue]                     # Marker container
    dispenserMap: DispenserMap
    roleZones: set[Coordinate]                              # Coordinates, where Role can be changed
    goalZones: set[Coordinate]                              # Coordinates, where Tasks can be submitted

    def __init__(self, id: int, agentId: str, markerPurgeInterval: int, simulationStep: int, unknownCoordSearchMaxIter : int,
        updateData: MapUpdateData = None) -> None:

        self.id = id
        self.markerPurgeInterval = markerPurgeInterval
        self.unknownCoordSearchMaxIter = unknownCoordSearchMaxIter

        self.agentCoordinates = dict([(agentId, Coordinate.origo())])
        self.agentStartingCoordinates = dict([(agentId, Coordinate.origo())])
        self.agentCoordReservations = dict()

        self.store = dict()
        self.markers = dict()
        self.dispenserMap = DispenserMap()

        self.roleZones = set()
        self.goalZones = set()

        self.reserveGoalZoneSemaphore = threading.Semaphore()

        if updateData is not None:
            self.addRange(simulationStep, updateData)
    
    def getMapValue(self, key: Coordinate, needMarker: bool = True, needDispenser: bool = False) -> MapValue:
        """
        Returns detailed information about an entity located at the given `Coordinate` in the map.\n
        Since markers and dispensers can be at a same `Coordinate` as an entity, the
        `needMarker` and the `needDispenser` params can be toggled to get these values.\n
        The return order is: `Marker` (if enabled) > `Agent` | `Block` | > `Dispenser` (if enabled) > `Obstacle` | `Empty` | `Unknown`,
        """

        if needMarker and key in self.markers:
            return self.markers[key]
        
        if key in self.store:
            isDispenser = key in self.dispenserMap.getAllDispenserCoords()
            if needDispenser and isDispenser:
                return self.dispenserMap.getDispenserMapValueByCoord(key)

            value = self.store[key]
            if isDispenser and value.value not in [MapValueEnum.AGENT, MapValueEnum.BLOCK]:
                return self.dispenserMap.getDispenserMapValueByCoord(key)
            else:
                return value
        else:
            return MapValue(MapValueEnum.UNKNOWN, "", 0)
    
    def getMapValueEnum(self, key: Coordinate, needMarker: bool = True, needDispenser: bool = False) -> MapValueEnum:
        """
        Returns the type of an entity located at the given `Coordinate` in the map.\n
        Since markers and dispensers can be at a same `Coordinate` as an entity, the
        `needMarker` and the `needDispenser` params can be toggled to get these values.\n
        The return order is: `Marker` (if enabled) > `Agent` | `Block` | > `Dispenser` (if enabled) > `Obstacle` | `Empty` | `Unknown`,
        """

        return self.getMapValue(key, needMarker, needDispenser).value

    def isCoordinateReservedForTask(self, coordinate: Coordinate) -> bool:
        """
        Returns if the given `Coordinate` is reserved for a task by any agent.
        """

        return coordinate in set([c for rs in self.agentCoordReservations.values() for c in rs])

    def findClosestUnknownFromStartingLocation(self, startCoordinate: Coordinate, currentCoordinate: Coordinate,
        vision: int) -> Coordinate | None:
        """
        Returns an unknown value `Coordinate` from the map, which is closest from the `Agent` starting position.
        """
        
        rangeIncrement = 0
        iterCount = 0
        unknownCoordinates = list(filter(lambda coord: self.getMapValueEnum(coord, False) == MapValueEnum.UNKNOWN,
            currentCoordinate.getVisionBorderCoordinates(vision)))

        # Search until one is found or max search iteration count is not completed
        while not any(unknownCoordinates) and iterCount <= self.unknownCoordSearchMaxIter:
            iterCount += 1
            rangeIncrement += 3     # For optimalization purposes, the closest property is that important here ()
            unknownCoordinates = list(filter(lambda coord: self.getMapValueEnum(coord, False) == MapValueEnum.UNKNOWN,
                currentCoordinate.getVisionBorderCoordinates(vision + rangeIncrement)))
        
        # For optimalization if maximum iter count is reached and found nothing then return None
        if iterCount > self.unknownCoordSearchMaxIter:
            return None

        # Randomize the order of the elements so the closestCoord's direction will always be different,
        # causing that every agent will start exploring to a different direction
        random.shuffle(unknownCoordinates)

        # Get the closest unknown coord from the starting position
        minDistanceFromStart = min([Coordinate.distance(startCoordinate, coord) for coord in unknownCoordinates])
        closestCoord = min(list(filter(lambda coord: abs(Coordinate.distance(startCoordinate, coord) - minDistanceFromStart) < 0.1,
            unknownCoordinates)), key = lambda coord: Coordinate.distance(currentCoordinate, coord))

        offsetCoordinate = Coordinate.getClosestCoordByDistanceByTwoCoordsLine(
            currentCoordinate, closestCoord, vision, 2)
        
        if self.getMapValueEnum(offsetCoordinate, False) == MapValueEnum.UNKNOWN:
            return offsetCoordinate
        else:
            return closestCoord
    
    def findRandomFarCoordinate(self, currentCoordinate: Coordinate, vision: int) -> Coordinate:
        """
        Returns a random passable (not `Block`, `Marker` or `Agent`) `Coordinate` for the `Agent` by 4 * vision distance away.
        """

        coordinates = self.getPassableCoordinates(currentCoordinate, 4 * vision)
        return random.choice(coordinates)
    
    def findRandomOldestCoordinate(self, currentCoordinate : Coordinate, vision: int) -> Coordinate:
        """
        Returns the earliest noted, passable (not `Block`, `Marker` or `Agent`) `Coordinate` which is 4 * vision distance away.
        """

        coordinates = self.getPassableCoordinates(currentCoordinate, 4 * vision)
        return min(coordinates, key = lambda coord: self.getMapValue(coord, False).simulationStep)
    
    def getPassableCoordinates(self, currentCoordinate: Coordinate, searchRange: int) -> list[Coordinate]:
        """
        Returns list of `Coordinates` which are passable (not `Block`, `Marker` or `Agent`) and at least `searchRange` distance away.
        """

        coordinates = list(filter(lambda coord: self.getMapValueEnum(coord) not in [MapValueEnum.AGENT, MapValueEnum.BLOCK, MapValueEnum.MARKER],
            currentCoordinate.getVisionBorderCoordinates(searchRange)))
        
        # If not found any then search in wider range
        while not any(coordinates):
            searchRange += 1
            coordinates = list(filter(lambda coord: self.getMapValueEnum(coord) not in [MapValueEnum.AGENT, MapValueEnum.BLOCK, MapValueEnum.MARKER],
                currentCoordinate.getVisionBorderCoordinates(searchRange)))
        
        return coordinates
        
    def getAgentCoordinate(self, agentId: str) -> Coordinate:
        """
        Returns an `Agent's` current `Coordinate's` copy.
        """

        return self.agentCoordinates[agentId].copy()
    
    def setAgentCoordinate(self, agentId: str, coordinate: Coordinate) -> None:
        """
        Sets an `Agent's` current `Coordinate`.
        """

        self.agentCoordinates[agentId] = coordinate.copy()
    
    def getAgentStartingCoordinate(self, agentId: str) -> Coordinate:
        """
        Returns an `Agent's` starting `Coordinate`.
        """

        return self.agentStartingCoordinates[agentId]
    
    def getDispenserCoordsByType(self, type: str) -> list[Coordinate]:
        """
        Returns `Dispenser` `Coordinates` by the given type.
        """

        return self.dispenserMap.getDispenserCoordsByType(type)
    
    def getClosestDispenser(self, type: str, coordinate: Coordinate) -> Coordinate:
        """
        Returns the closest given type `Dispenser` to the given `Coordinate`.
        Prioritizes the ones which are not surrounded by `Agents`, `Blocks` or `Markers`.
        """

        dispensers = self.dispenserMap.getDispenserCoordsByType(type)
        
        # Dispensers with no marker or agent on it and at least 2 neighbors of it is not occupied by agent, block or marker
        freeDispensers = list(filter(lambda c: self.getMapValueEnum(c) not in [MapValueEnum.MARKER, MapValueEnum.AGENT] and \
            (coordinate in c.neighbors() or len([n for n in c.neighbors() if self.getMapValueEnum(n) not in [MapValueEnum.AGENT, MapValueEnum.BLOCK, MapValueEnum.MARKER]]) >= 2),
            dispensers))

        return min(freeDispensers if any(freeDispensers) else dispensers, key = lambda c: Coordinate.distance(c, coordinate)).copy()

    def addRange(self, simulationStep: int, updateData: MapUpdateData) -> None:
        """
        Updates the map with information coming from an `Agent's` dynamic percept.\n
        Updates the map values, markers, goal zones, role zones.
        """

        deletableGoalZones = []
        for coord, mapValue in updateData.things.items():
            if coord not in self.store:
                self.store[coord] = mapValue
            elif mapValue.simulationStep > self.store[coord].simulationStep:
                self.store[coord].update(mapValue)
            
            # If there was previously a marker, but now it is not, then it disappeared.
            if coord in self.markers and coord not in updateData.markers:
                del self.markers[coord]
            
            # If there was previously a goal zone,but now it is not, then it disappeared.
            if coord in self.goalZones and coord not in updateData.goalZones:
                deletableGoalZones.append(coord)
        
        for coord, mapValue in updateData.markers.items():
            self.markers[coord] = mapValue

        for markerCoords in list(self.markers.keys()):
            # Remove old marker zones from map.
            if simulationStep - self.markers[markerCoords].simulationStep >= self.markerPurgeInterval:
                del self.markers[markerCoords]
        
        for coord, mapValue in updateData.dispensers.items():
            self.dispenserMap.addDispenser(mapValue.details, coord)

        self.roleZones.update(updateData.roleZones)

        self.deleteGoalZones(deletableGoalZones)
        self.goalZones.update(updateData.goalZones) 

    def merge(self, otherMap: 'DynamicMap', othersCoordinateInMyMap: Coordinate, othersCoordinateInOthersMap: Coordinate) -> Coordinate:
        """
        Merges the other map into the current one, by calculating the difference between the 'same' `Coordinates`.
        Returns the difference as a `Coordinate`.
        """

        # Calculate difference
        xDifference = othersCoordinateInMyMap.x - othersCoordinateInOthersMap.x
        yDifference = othersCoordinateInMyMap.y - othersCoordinateInOthersMap.y

        # Merge the others coordinates
        for coordinate, value in otherMap.store.items():
            shiftedCoordinate = Coordinate(coordinate.x + xDifference, coordinate.y + yDifference)

            if shiftedCoordinate not in self.store:
                self.store[shiftedCoordinate] = value
            elif self.store[shiftedCoordinate].simulationStep < value.simulationStep:
                self.store[shiftedCoordinate].update(value)
        
        # Merge the others markers
        for coordinate, value in otherMap.markers.items():
            shiftedCoordinate = Coordinate(coordinate.x + xDifference, coordinate.y + yDifference)

            if shiftedCoordinate not in self.markers or self.markers[shiftedCoordinate].simulationStep < value.simulationStep:
                self.markers[shiftedCoordinate] = value
        
        # Merge the agent current coordinates
        for agentId, coord in otherMap.agentCoordinates.items():
            self.agentCoordinates[agentId] = Coordinate(coord.x + xDifference, coord.y + yDifference)
        
        # Merge the agent starting coordinates
        for agentId, coord in otherMap.agentStartingCoordinates.items():
            self.agentStartingCoordinates[agentId] = Coordinate(coord.x + xDifference, coord.y + yDifference)
        
        # Merge the reserved coordinates, it can lead to conflict
        for agentId, reservedCoords in otherMap.agentCoordReservations.items():
            self.agentCoordReservations[agentId] = [Coordinate(c.x + xDifference, c.y + yDifference) for c in reservedCoords]
        
        # Merge dispenser coordinates
        for type, coordList in otherMap.dispenserMap.dispensers.items():
            for coord in coordList:
                self.dispenserMap.addDispenser(type, Coordinate(coord.x + xDifference, coord.y + yDifference))
        
        # Update role zones
        self.roleZones.update([Coordinate(coord.x + xDifference, coord.y + yDifference) for coord in otherMap.roleZones])

        # Update goal zones
        self.goalZones.update([Coordinate(coord.x + xDifference, coord.y + yDifference) for coord in otherMap.goalZones])
        
        return Coordinate(xDifference, yDifference, False)
    
    def updateCoordinatesByBoundary(self) -> None:
        """
        Recalculates the `Coordinates` located in the map when at least
        one of the map dimensions are calculated.\n
        Because of the 'infinite' map, the same map value can occur twice,
        that's why every 'normalized' `Coordinate` must be merged into the map.
        """

        newStore : dict[Coordinate, MapValue] = dict()
        newMarkers : dict[Coordinate, MapValue] = dict()
        newDispenserMap = DispenserMap()

        # Update agent current coordinates
        for agentCoord in self.agentCoordinates.values():
            agentCoord.normalize()

        # Update agent starting coordinates
        for agentStartCoord in self.agentStartingCoordinates.values():
            agentStartCoord.normalize()
        
        # Update reserved coordinates, it can lead to conflict
        for reservedCoords in self.agentCoordReservations.values():
            for reservedCoord in reservedCoords:
                reservedCoord.normalize()
        
        # Update dispensers
        for type, coordList in self.dispenserMap.dispensers.items():
            for coord in coordList:
                newDispenserMap.addDispenser(type, coord.copy())

        # Update the map values
        for coord, mapValue in self.store.items():
            newCoord = coord.copy()
            if newCoord not in newStore or newStore[newCoord].simulationStep < mapValue.simulationStep:
                newStore[newCoord] = mapValue

        # Update the markers
        for coord, marker in self.markers.items():
            newCoord = coord.copy()
            if newCoord not in newMarkers or newMarkers[newCoord].simulationStep < marker.simulationStep:
                newMarkers[newCoord] = marker
        
        self.store = newStore
        self.markers = newMarkers
        self.dispenserMap = newDispenserMap

        # Update role zones
        self.roleZones = set([coord.copy() for coord in self.roleZones])

        # Update goal zones
        self.goalZones = set([coord.copy() for coord in self.goalZones])
    
    def hasAnyGoalZone(self) -> bool:
        """
        Returns if there is any goal zone at which there is no `Dispender`, `Agent` or `Block`.
        """

        return any(self.getMapValueEnum(g) not in [MapValueEnum.DISPENSER, MapValueEnum.AGENT, MapValueEnum.BLOCK] for g in self.goalZones)

    def reserveCoordinatesForTask(self, agentId: str, goalZone: Coordinate, blockRelCoords: list[Coordinate]) -> None:
        """
        Reserves `Coordinates` for an `Agent` to task submission.
        The neigboring `Coordinates` are also reserved for better movablity for the `Agents`.
        """

        reservedCoords = [goalZone]
        reservedCoords.extend([goalZone.getShiftedCoordinate(bc) for bc in blockRelCoords])

        reservedCoords = [cn for c in reservedCoords for cn in c.getSurroundingNeighbors()]

        if agentId not in self.agentCoordReservations:
            self.agentCoordReservations[agentId] = []
        
        self.agentCoordReservations[agentId].extend(reservedCoords)
    
    def freeCoordinatesFromTask(self, agentId: str) -> None:
        """
        Frees the reserved `Coordinates` for an `Agent`.
        """

        self.agentCoordReservations[agentId] = []

    def isAnyFreeGoalZoneForTask(self, blockRelCoords: list[Coordinate]) -> bool:
        """
        Returns if a `Coordinate` set can be reserved for task completion. The submittor,
        the block and the surrounding `Coordinates` are checked.
        """

        return self.getFirstFreeGoalZoneForTask(
            list(filter(lambda c: self.getMapValueEnum(c) not in [MapValueEnum.DISPENSER, MapValueEnum.AGENT, MapValueEnum.BLOCK], self.goalZones)), blockRelCoords) is not None

    def getClosestFreeGoalZoneForTask(self, currentCoordinate: Coordinate, blockRelCoords: list[Coordinate]) -> Coordinate | None:
        """
        Returns the closest free (not occupied by an `Agent`, `Block` or `Dispenser`) `Coordinate`,
        where the given `Task` shape can be submitted.
        """

        goalZones = sorted(
            list(filter(lambda c: c == currentCoordinate or self.getMapValueEnum(c) not in [MapValueEnum.DISPENSER, MapValueEnum.AGENT, MapValueEnum.BLOCK], self.goalZones)),
            key = lambda c : Coordinate.distance(c, currentCoordinate))

        return self.getFirstFreeGoalZoneForTask(goalZones, blockRelCoords)
    
    def getFirstFreeGoalZoneForTask(self, goalZones: list[Coordinate], blockRelCoords: list[Coordinate]) -> Coordinate | None:
        """
        Returns the first `Coordinate`, where the given `Task` shape can be submitted
        and there is no `Dispenser` at the area.
        """

        reservedCoords = set([c for cs in self.agentCoordReservations.values() for c in cs])
        for goalZone in goalZones:
            blockGobalCoords = [goalZone.getShiftedCoordinate(bc) for bc in blockRelCoords]
            reserveableCoords = set([cn for c in blockGobalCoords for cn in c.getSurroundingNeighbors()])

            # If the coordinate is reserved or there is a dispenser on it then continue searching for an another
            # Dispenser could be a valid location, however it means that other agents going to travel here,
            # preventing the task assemble and submission
            if all(rc not in reservedCoords and self.getMapValueEnum(rc, False, True) != MapValueEnum.DISPENSER for rc in reserveableCoords):
                return goalZone

        return None
    
    def tryReserveCloserGoalZoneForTask(self, agentId: str, currentGoalZone: Coordinate | None, currentCoordinate: Coordinate,
        blockRelCoords: list[Coordinate]) -> Coordinate | None:
        """
        Tries to reserve a closer goal zone for an `Agent` if there is available.
        Returns the result of it which can be None (it failed) or a `Coordinate`
        (it succeeded, that's where the `Agent` has to submit the `Task`).
        """


        # Acquire semaphore
        self.reserveGoalZoneSemaphore.acquire()

        # Search for a closer available goal zone sorted by the distance
        goalZones = sorted(
            list(filter(lambda c: c == currentCoordinate or self.getMapValueEnum(c) not in [MapValueEnum.DISPENSER, MapValueEnum.AGENT, MapValueEnum.BLOCK, MapValueEnum.MARKER]
                and (currentGoalZone is None or Coordinate.distance(currentCoordinate, c) < Coordinate.distance(currentCoordinate, currentGoalZone)), self.goalZones)),
            key = lambda c : Coordinate.distance(c, currentCoordinate))

        result = self.getFirstFreeGoalZoneForTask(goalZones, blockRelCoords)

        if result is not None:
            self.freeCoordinatesFromTask(agentId)
            self.reserveCoordinatesForTask(agentId, result, blockRelCoords)

        # Release semaphore
        self.reserveGoalZoneSemaphore.release()
        return result

    def getConflictingCoordinateReservations(self) -> dict[str, list[str]]:
        """
        Returns a dictionary, which contains that which agent's reservation
        conflicts with other agents'\n.
        It's like a directed graph,
        if there are two opposite direction edges between two nodes, it means
        one of them has to be handled.
        """

        conflictingAgentIds : dict[str, list[str]] = dict()

        for agentId, reservedCoords in self.agentCoordReservations.items():
            for otherAgentId, otherAgentReservedCoordSet in self.agentCoordReservations.items():
                if agentId == otherAgentId:
                    continue
                
                # If there is at least one conflicting rserved coordinates, then it must be handled
                if any(set(reservedCoords).intersection(otherAgentReservedCoordSet)):
                    if agentId not in conflictingAgentIds:
                        conflictingAgentIds[agentId] = [otherAgentId]
                    else:
                        conflictingAgentIds[agentId].append(otherAgentId)

        return conflictingAgentIds

    def isMapExplored(self) -> bool:
        """
        Returns if the map dimensions are calculated
        and all the `Coordinates` are explored.
        """

        return Coordinate.dimensionsCalculated and \
            len(self.store.keys()) == Coordinate.maxWidth * Coordinate.maxHeight
    
    def deleteGoalZones(self, goalZones: list[Coordinate]) -> None:
        """
        Removes the given goal zone `Coordinates` from the map.
        """

        while any(goalZones):
            current = goalZones[0]
            goalZones.remove(current)
            self.goalZones.remove(current)

    def isAnyRoleZone(self) -> bool:
        """
        Returns if is there any not occupied (by `Agent` or `Block`) role zone in the map.
        """

        return any(self.getMapValueEnum(c, False) not in [MapValueEnum.AGENT, MapValueEnum.BLOCK] for c in self.roleZones)

    def getClosestRoleZone(self, currentCoordinate: Coordinate) -> Coordinate:
        """
        Returns the closest role zone to the given `Coordinate`.
        Prioritizes the ones which are not occupied (by `Agent`, `Block` or `Marker`).
        """

        roleZones = list(filter(lambda c: c == currentCoordinate or
            self.getMapValueEnum(c) not in [MapValueEnum.AGENT, MapValueEnum.BLOCK, MapValueEnum.MARKER],
            self.roleZones))
        
        if not any(roleZones):
            roleZones = self.roleZones

        return min(roleZones, key = lambda c : Coordinate.distance(c, currentCoordinate))