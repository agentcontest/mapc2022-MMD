import math
import random
from typing import Tuple

from data.coreData import *
from data.map import DynamicMap
from data.dataStructure import PriorityQueue, PriorityQueueNode

from agent.action import AgentAction, MoveAction, SkipAction, ClearAction, RotateAction

from agent.pathfinder.pathFinderData import PathFinderData

class PathFinder:
    """
    Wrapper class for customized A* path finding algorithm,
    which can find path for an `Agent` which carries maximum
    one `Block`.\n
    The main idea is that the `Agent` must pull the `Block` behind it all the times,
    so when an `Agent` does not go straight then it must rotate. However, due to optimalizations,
    it only rotates if it must (the move can be completed without cleaning).
    """

    explanation: str
    blockClearValue: float  # Only clear block if necessary

    def __init__(self) -> None:
        self.explanation = ""
        self.blockClearValue = 100

    def findNextAction(self, pathfinderData: PathFinderData, end: Coordinate, ignoreMarker: bool = False) -> AgentAction:
        """
        Returns the first `AgentAction` which is needed to get to the given end `Coordinate`.
        It searches a path, using the customized A* algorithm, then returns the first step of it.
        """

        agentTravelTime = 1 / pathfinderData.agentSpeed
        clearCost = pathfinderData.clearConstantCost / (max(pathfinderData.agentEnergy - pathfinderData.clearEnergyCost, 0.1)
            / pathfinderData.agentMaxEnergy)
        clearSuccessTime = math.ceil(1 / pathfinderData.clearChance)

        agentTravelTime, clearCost, clearSuccessTime = self.calculateTravelConstantCosts(
            pathfinderData.agentSpeed, pathfinderData.clearEnergyCost,
            pathfinderData.agentEnergy, pathfinderData.agentMaxEnergy,
            pathfinderData.clearChance, pathfinderData.clearConstantCost)
        
        _, cameFrom, endCoordinate, rotateDict = self.AStarBody(pathfinderData.map, pathfinderData.start, end, agentTravelTime, clearCost,
            clearSuccessTime, pathfinderData.maxIteration, pathfinderData.agentVision,
            ignoreMarker, pathfinderData.attachedCoordinates)
        
        # If found path then recreate the route to it
        if endCoordinate is not None:
            return self.getAction(pathfinderData.map, cameFrom, endCoordinate, pathfinderData.agentSpeed,
                pathfinderData.attachedCoordinates, rotateDict)
        # If not found path then just skip, it could raise an Error
        else:
            return SkipAction()

    def findClosestFreeCoordinate(self, pathfinderData: PathFinderData) -> Coordinate:
        """
        Returns the closest free `Coordinate` using path finding.\n
        Used for escaping clear events, some distance cost could be used instead,
        but it calculates if clear or rotation is needed.
        """

        visionRange = 1
        closestFreeCoords = list(filter(lambda coord: pathfinderData.map.getMapValueEnum(coord) in
            [MapValueEnum.EMPTY, MapValueEnum.UNKNOWN], Coordinate.getVisionBorderCoordinates(pathfinderData.start, visionRange)))

        while not closestFreeCoords:
            visionRange += 1
            closestFreeCoords = list(filter(lambda coord: pathfinderData.map.getMapValueEnum(coord) in
                [MapValueEnum.EMPTY, MapValueEnum.UNKNOWN], Coordinate.getVisionBorderCoordinates(pathfinderData.start, visionRange)))
        
        agentTravelTime, clearCost, clearSuccessTime = self.calculateTravelConstantCosts(
            pathfinderData.agentSpeed, pathfinderData.clearEnergyCost,
            pathfinderData.agentEnergy, pathfinderData.agentMaxEnergy,
            pathfinderData.clearChance, pathfinderData.clearConstantCost) 

        return min(closestFreeCoords,
            key = lambda coord: self.AStarBody(pathfinderData.map, pathfinderData.start, coord, agentTravelTime, clearCost,
                clearSuccessTime, pathfinderData.maxIteration, pathfinderData.agentVision, True, pathfinderData.attachedCoordinates)[0])

    def AStarBody(self, map: DynamicMap, start: Coordinate, end: Coordinate, agentTravelTime: float, clearCost: float,
        clearSuccessTime: int, maxIteration: int, agentVision: int, ignoreMarker: bool,
        attachedCoordinates: list [Coordinate]) -> Tuple[float, dict[Coordinate, Coordinate], Coordinate, dict[Coordinate, Direction]]:
        """
        A* algorithm body, which returns a tuple:
        distance cost, cameFrom dictionary, the end `Coordinate` and a 
        rotation directory, which tells if an `Agent` has to rotate at a 
        given `Coordinate` then which `Direction` should be used to rotate
        (it's not `RotateDirection`, but it can be mapped to it).
        """    
        if start == end:
            return (math.inf, dict(), None, dict())

        iterationCount = 0
        cameFrom = dict()

        gScore = dict()
        gScore[start] = 0

        fScore = dict()
        fScore[start] = self.heuristicCost(start, end)

        openSet = PriorityQueue()
        openSet.insert(PriorityQueueNode(start, fScore[start]))

        attachedSet = dict()
        attachedSet[start] = attachedCoordinates

        rotations = dict()
        current = None

        while iterationCount <= maxIteration and not openSet.isEmpty():
            current = openSet.pop().value
            if current == end:
                return (gScore[current], cameFrom, current, rotations)
            
            # AttachedList contains the relative Coordinates of the Agent, after it got to the neighbor Coordinate,
            # it may have rotated, that's why it needs to be tracked
            # RotateDict contains the rotation data if rotation is needed to get to the neighbor Coordinate
            for neighbor, attachedList, rotateDict in self.getNeighbors(map, start, current, agentVision, ignoreMarker, attachedSet[current]):
                distanceCost, rotateDirection = self.distanceCost(map, current, neighbor, agentTravelTime, clearSuccessTime, clearCost, attachedSet[current], rotateDict)
                tentativeGScore = gScore[current] + distanceCost

                if tentativeGScore < (gScore[neighbor] if neighbor in gScore else math.inf):
                    cameFrom[neighbor] = current
                    attachedSet[neighbor] = attachedList
                    rotations[neighbor] = rotateDirection
                    gScore[neighbor] = tentativeGScore
                    fScore[neighbor] = tentativeGScore + self.heuristicCost(neighbor, end)

                    openSet.insert(PriorityQueueNode(neighbor, fScore[neighbor]))
            
            iterationCount += 1
        
        # If the max iteration count was reached, but not found the end Coordinate,
        # then the closest to it is fine (based on heuristics)
        if not openSet.isEmpty():
            closestCoord = min((coord for coord in fScore.keys() if coord in cameFrom), key = lambda coord: self.heuristicCost(coord, end))
            return (gScore[closestCoord], cameFrom, closestCoord, rotations)

        # If no path founded then return None
        return (math.inf, cameFrom, None, rotations)

    def getAction(self, map: DynamicMap, cameFrom: dict[Coordinate, Coordinate], current: Coordinate,
        maxSteps: int, attachedCoordinates: list[Coordinate],
        rotateDict: dict[Coordinate, Direction]) -> AgentAction:

        actions = []
        prev = cameFrom[current]

        self.explanation = str(current)

        # Recreate the route and store the required actions
        # between the nodes.
        while current in cameFrom:
            mapValue = map.getMapValueEnum(current, False)
            relCoord = Coordinate.getRelativeCoordinate(prev, current)
            if mapValue == MapValueEnum.OBSTACLE or (mapValue == MapValueEnum.BLOCK and relCoord not in attachedCoordinates):
                actions.insert(0, (AgentActionEnum.CLEAR, relCoord))
            else: 
                actions.insert(0, (AgentActionEnum.MOVE, Coordinate.getDirection(prev, current)))

            current = prev
            if prev in cameFrom:
                prev = cameFrom[prev]
                self.explanation += str(current)

        # If first a clear is needed then just do it
        if actions[0][0] == AgentActionEnum.CLEAR:
            return ClearAction(actions[0][1]) 

        # Else get all the move actions as possible
        #(it stops when max steps are reached or if a clear is needed)
        index = 0
        directions = []
        while index < len(actions) and index < maxSteps and actions[index][0] != AgentActionEnum.CLEAR:
            directions.append(actions[index][1])
            index += 1
        
        # If no block is carried then just move
        if len(attachedCoordinates) != 1:
            return MoveAction(directions)

        attachedCoord = attachedCoordinates[0]
        faceDirection = Coordinate.getDirection(attachedCoord, Coordinate.origo())

        # If no rotation is needed at least for the first step,
        # because the Agent goes straight then just move
        if faceDirection.isSameDirection(directions[0]):
            if (len(directions) == 1 or faceDirection.isSameDirection(directions[1])):
                return MoveAction(directions)
            else:
                return MoveAction([directions[0]])
        # If an opposite rotation is needed
        elif faceDirection.isOppositeDirection(directions[0]):
            return self.getActionAtOppositeRotating(map, current, attachedCoord, rotateDict, directions)
        # If just a simple rotation is needed
        else:
            return self.getActionAtSimpleRotating(map, current, attachedCoord, directions)

    def getActionAtSimpleRotating(self, map: DynamicMap, current: Coordinate,
        attachedCoord: Coordinate, directions: list[Direction]) -> AgentAction:
        """
        Returns an `AgentAction` which is required to get to the `Coordinate` which
        is next to the `Agent` (not in front of and not behind of it). It returns a `RotateAction` if a rotation is required,
        if not, then it returns as many `MoveActions` as possible.
        """

        # If a rotation can be avoided (no clear action is required) then just move
        attachedShifted = current.getShiftedCoordinate(attachedCoord).getMovedCoord([directions[0]])
        if map.getMapValueEnum(attachedShifted) in [MapValueEnum.EMPTY, MapValueEnum.UNKNOWN]:
            if len(directions) == 2 and map.getMapValueEnum(attachedShifted.getMovedCoord([directions[1]])) in [MapValueEnum.EMPTY, MapValueEnum.UNKNOWN]:
                return MoveAction(directions)
            else:
                return MoveAction([directions[0]])

        # If a rotation can not be avoided, then rotate to the given direction
        # and clear before it, if needed
        blockingAdjacentCoord = current.getMovedCoord([directions[0].opposite()])

        if map.getMapValueEnum(blockingAdjacentCoord, False) in [MapValueEnum.OBSTACLE, MapValueEnum.BLOCK]:
            return ClearAction(Coordinate.getRelativeCoordinate(current, blockingAdjacentCoord))
        else:
            return RotateAction(attachedCoord.getRotateDirection(directions[0]))

    def getActionAtOppositeRotating(self, map: DynamicMap, current: Coordinate,
        attachedCoord: Coordinate, rotateDict: dict[Coordinate, Direction],
        directions: list[Direction]) -> AgentAction:
        """
        Returns an `AgentAction` which is required to get to the `Coordinate` which
        is behind to the `Agent` (where the attached `Block` is). It returns a `RotateAction` if a rotation is required,
        if not, then it returns as many `MoveActions` as possible.
        """

        # If a rotation can be avoided (no clear action is required) then just move
        attachedShifted = current.getShiftedCoordinate(attachedCoord).getMovedCoord([directions[0]])
        if map.getMapValueEnum(attachedShifted) in [MapValueEnum.EMPTY, MapValueEnum.UNKNOWN]:
            if len(directions) == 2 and map.getMapValueEnum(attachedShifted.getMovedCoord([directions[1]])) in [MapValueEnum.EMPTY, MapValueEnum.UNKNOWN]:
                return MoveAction(directions)
            else:
                return MoveAction([directions[0]])

        # If a rotation can not be avoided, then rotate to the given direction
        # and clear before it, if needed
        directionToRotate = rotateDict[current.getMovedCoord([directions[0]])]
        blockingAdjacentCoord = current.getMovedCoord([directionToRotate.opposite()])

        if map.getMapValueEnum(blockingAdjacentCoord, False) in [MapValueEnum.OBSTACLE, MapValueEnum.BLOCK]:
            return ClearAction(Coordinate.getRelativeCoordinate(current, blockingAdjacentCoord))
        else:
            return RotateAction(attachedCoord.getRotateDirection(directionToRotate))

    def getNeighbors(self, map: DynamicMap, startCoordinate: Coordinate, currentCoordinate: Coordinate, vision: int,
        ignoreMarker: bool, attachedCoords: list[Coordinate]) -> list[Tuple[Coordinate, list[Coordinate], dict[Direction, bool]]]:
        """
        Returns the passable adjacent `Coordinates` and the belonging
        rotate dictionary and attached relative `Coordinates` if an `Agent`
        steps to the given `Coordinate`.
        """

        passableNeighbors = []
        for nextCoordinate in currentCoordinate.neighbors():
            passable, attacheds, rotateDict = self.isCoordinatePassable(map, startCoordinate, currentCoordinate, nextCoordinate, vision, ignoreMarker, attachedCoords)
            if passable:
                passableNeighbors.append((nextCoordinate, attacheds, rotateDict))

        random.shuffle(passableNeighbors)
        return passableNeighbors

    def distanceCost(self, map: DynamicMap, currentCoordinate: Coordinate, nextCoordinate: Coordinate, agentTravelTime: float, clearSuccessTime: int,
        clearCost: float, attachedCoordList: Coordinate, rotateDict: dict[Direction, bool]) -> Tuple[float, Direction]:
        """
        Returns the distance cost between two `Coordinates`, including
        clear and rotation cost if needed.
        """

        # If there is no attached entity just calculate the regular distance cost
        if len(attachedCoordList) != 1 or rotateDict is None:
            return (self.distanceCostWithoutRotating(map.getMapValueEnum(nextCoordinate, False), agentTravelTime, clearSuccessTime, clearCost), None)
        # If there is an attached entity then calculate the sum of the regular distance cost
        # and the rotation costs
        else:
            attachedCoord = attachedCoordList[0]
            moveDirection = Coordinate.getDirection(currentCoordinate, nextCoordinate)
            faceDirection = Coordinate.getDirection(attachedCoord, Coordinate.origo())

            # If rotation is not needed then calculate the regular distance cost
            if moveDirection.isSameDirection(faceDirection):
                return (self.distanceCostWithoutRotating(map.getMapValueEnum(nextCoordinate, False), agentTravelTime, clearSuccessTime, clearCost), None)
            # If 180 rotation is needed
            elif moveDirection.isOppositeDirection(faceDirection):
                return self.distanceCostWithOppositeRotating(map, currentCoordinate, nextCoordinate, clearSuccessTime, clearCost, rotateDict) 
            # If 90 rotation is needed
            else:
                return (self.distanceCostWithRotating(map, currentCoordinate, nextCoordinate, clearSuccessTime,
                    clearCost, attachedCoord), list(rotateDict.keys())[0])

    def distanceCostWithoutRotating(self, endValue: MapValueEnum, agentTravelTime: float, clearSuccessTime: int, clearCost: float) -> float:
        """
        Returns a distance cost between two `Coordinates` without rotating,
        includes the clear cost if it is needed.
        """

        if endValue == MapValueEnum.OBSTACLE:
            return 1 + self.clearCost(clearSuccessTime, clearCost)
        elif endValue == MapValueEnum.BLOCK:
            return self.blockClearValue + self.clearCost(clearSuccessTime, clearCost)
        else:
            return agentTravelTime

    def distanceCostWithRotating(self, map: DynamicMap, currentCoordinate: Coordinate, nextCoordinate: Coordinate, clearSuccessTime: int,
        clearCost: float, attachedCoord: Coordinate) -> float:
        """
        Returns the distance cost between two `Coordinates` with a simple 90 rotating,
        includes the clear cost if it is needed.
        """

        # Calculate the cost of the next Block coord, where the Block will be after the rotation
        nextCoordValue = map.getMapValueEnum(nextCoordinate, False)
        cost = 3
        if nextCoordValue == MapValueEnum.OBSTACLE:
            cost += self.clearCost(clearSuccessTime, clearCost)
        elif nextCoordValue == MapValueEnum.BLOCK:
            cost += self.blockClearValue + self.clearCost(clearSuccessTime, clearCost)

        # Calculate the cost of the next coord, where the Agent will be
        adjacentCoordValue = map.getMapValueEnum(currentCoordinate.getMovedCoord([Coordinate.getDirection(nextCoordinate, currentCoordinate)]), False)
        if adjacentCoordValue == MapValueEnum.OBSTACLE:
            cost += self.clearCost(clearSuccessTime, clearCost)
        elif adjacentCoordValue == MapValueEnum.BLOCK and Coordinate.getRelativeCoordinate(currentCoordinate, nextCoordinate) != attachedCoord:
            cost += self.blockClearValue + self.clearCost(clearSuccessTime, clearCost)

        return cost
    
    def distanceCostWithOppositeRotating(self, map: DynamicMap, currentCoordinate: Coordinate, nextCoordinate: Coordinate, clearSuccessTime: int,
        clearCost: float, rotateDict: dict[Direction, bool]) -> Tuple[float, Direction]:
        """
        Returns the distance cost between two `Coordinates` with a 180 rotating,
        includes the clear cost if it is needed.
        """

        cost = 6.0
        faceDirection = Coordinate.getDirection(nextCoordinate, currentCoordinate)
        frontCoord = currentCoordinate.getMovedCoord([faceDirection])
        leftDirection, rightDirection = faceDirection.getAdjacentDirections()

        # Calculate the both rotation cost
        leftCheckableCoords = [
            currentCoordinate.getMovedCoord([leftDirection]),
            frontCoord]
        rightCheckableCoords = [
            currentCoordinate.getMovedCoord([rightDirection]),
            frontCoord]
        
        leftRotateCost = cost
        for coord in leftCheckableCoords:
            coordValue = map.getMapValueEnum(coord, False)
            if coordValue == MapValueEnum.OBSTACLE:
                leftRotateCost += self.clearCost(clearSuccessTime, clearCost)
            elif coordValue == MapValueEnum.BLOCK:
                leftRotateCost += self.blockClearValue + self.clearCost(clearSuccessTime, clearCost)

        rightRotateCost = cost
        for coord in rightCheckableCoords:
            coordValue = map.getMapValueEnum(coord, False)
            if coordValue == MapValueEnum.OBSTACLE:
                rightRotateCost += self.clearCost(clearSuccessTime, clearCost)
            elif coordValue == MapValueEnum.BLOCK:
                rightRotateCost += self.blockClearValue + self.clearCost(clearSuccessTime, clearCost)

        # Then adjust to which rotation is allowed
        # and select the cheaper one if both is available
        # (at least one of them is available)
        if not rotateDict[leftDirection]:
            return (rightRotateCost, rightDirection)
        elif not rotateDict[rightDirection]:
            return (leftRotateCost, leftDirection)
        else:
            if leftRotateCost <= rightRotateCost:
                return (leftRotateCost, leftDirection)
            else:
                return (rightRotateCost, rightDirection)

    def heuristicCost(self, start: Coordinate, end: Coordinate) -> float:
        """
        Returns the Euclidean-distance.
        """

        return Coordinate.distance(start, end)
    
    def clearCost(self, clearSuccessTime: int, clearEnergyCost: float) -> float:
        """
        Returns the clear cost used at calculating the distance cost.
        """

        return clearSuccessTime + clearEnergyCost

    def isCoordinatePassable(self, map: DynamicMap, startCoordinate: Coordinate, currentCoordinate: Coordinate,
        nextCoordinate: Coordinate, vision: int, ignoreMarker: bool, attachedCoords: list [Coordinate]) -> Tuple[bool, list[Coordinate], dict[Direction, bool]]:
        """
        Returns if the given `Coordinate` is passable from the current one
        and the belonging rotate dictionary and attachment list if the `Agent`
        gets to this given `Coordinate`
        """

        coordValue = map.getMapValueEnum(nextCoordinate)

        # Marker or agent is passable if it is far from the agent,
        # because they will likely change position
        passableForAgent = (coordValue in [MapValueEnum.EMPTY, MapValueEnum.OBSTACLE, 
            MapValueEnum.UNKNOWN, MapValueEnum.BLOCK] or (
                coordValue == MapValueEnum.MARKER and (ignoreMarker 
                    or Coordinate.manhattanDistance(startCoordinate, nextCoordinate) > vision))
            or (coordValue == MapValueEnum.AGENT and Coordinate.manhattanDistance(startCoordinate, nextCoordinate) > vision))

        if not passableForAgent:
            return (False, attachedCoords, None)

        # If it is passable and there is no attached entities then ok
        if not any(attachedCoords):
            return (True, attachedCoords, None)

        if len(attachedCoords) == 1:
            attachment = attachedCoords[0].copy(False)

            # Gets if the coordinate is passable for the attached entities too
            passable, rotateDict = self.isCoordinatePassableForSingleAttachment(map, startCoordinate, currentCoordinate, nextCoordinate, ignoreMarker, attachment, vision)

            # Calculate the attached entities relative positions after the rotation (if needed)
            if passable and rotateDict is not None:
                moveDirection = Coordinate.getDirection(currentCoordinate, nextCoordinate)
                faceDirection = Coordinate.getDirection(attachment, Coordinate.origo())

                if moveDirection.isOppositeDirection(faceDirection):
                    attachment = attachment.getRotatedRelCoord(RotateDirection.CLOCKWISE).getRotatedRelCoord(RotateDirection.CLOCKWISE)
                else:
                    rotateDirection = attachment.getRotateDirection(moveDirection)
                    attachment = attachment.getRotatedRelCoord(rotateDirection)

            return (passable, [attachment], rotateDict)
        # Legacy check for multiple attached block, should not be used.
        else:
            return (self.isCoordinatePassableForMultipleAttachements(map, currentCoordinate, nextCoordinate,
                ignoreMarker, attachedCoords), attachedCoords, None)
    
    def isCoordinatePassableForSingleAttachment(self, map: DynamicMap, startCoordinate: Coordinate, currentCoordinate: Coordinate, nextCoordinate: Coordinate,
        ignoreMarker: bool, attachedCoord: Coordinate, vision: int) -> Tuple[bool, dict[Direction, bool]]:
        """
        Returns if the given `Coordinate` is passable from the current one for the single
        attached entity and returns also the rotation dictionary.
        """
        moveDirection = Coordinate.getDirection(currentCoordinate, nextCoordinate)
        faceDirection = Coordinate.getDirection(attachedCoord, Coordinate.origo())

        # If the Agent goes straight then it is passable for the attached entity too
        if moveDirection.isSameDirection(faceDirection):
            return (True, None)

        # If the Agent goes backwards
        elif moveDirection.isOppositeDirection(faceDirection):
            frontCoord = currentCoordinate.getMovedCoord([faceDirection])
            leftDirection, rightDirection = moveDirection.getAdjacentDirections()

            # A 180 rotation is needed, so at least one way
            # must be passable
            leftCheckableCoords = [
                currentCoordinate.getMovedCoord([leftDirection]),
                frontCoord]
            rightCheckableCoords = [
                currentCoordinate.getMovedCoord([rightDirection]),
                frontCoord]

            # Same rules apply: marker and agent is ok, if it is far, the rest is ok
            canRotateToLeftDirection = all(map.getMapValueEnum(c, ignoreMarker) in [MapValueEnum.EMPTY, MapValueEnum.UNKNOWN, MapValueEnum.BLOCK, MapValueEnum.OBSTACLE]
                    or (map.getMapValueEnum(c, ignoreMarker) in [MapValueEnum.AGENT, MapValueEnum.MARKER] and Coordinate.manhattanDistance(startCoordinate, c) > vision)
                for c in leftCheckableCoords)
            canRotateToRightDirection = all(map.getMapValueEnum(c, ignoreMarker) in [MapValueEnum.EMPTY, MapValueEnum.UNKNOWN, MapValueEnum.BLOCK, MapValueEnum.OBSTACLE]
                    or (map.getMapValueEnum(c, ignoreMarker) in [MapValueEnum.AGENT, MapValueEnum.MARKER] and Coordinate.manhattanDistance(startCoordinate, c) > vision)
                for c in rightCheckableCoords)

            return (canRotateToLeftDirection or canRotateToRightDirection,
                dict([(leftDirection, canRotateToLeftDirection), (rightDirection, canRotateToRightDirection)]))

        # If the Agent goes beside
        else:
            rotateToCoordinate = currentCoordinate.getMovedCoord([Coordinate.getDirection(nextCoordinate, currentCoordinate)])
            rotateToCoordinateValue = map.getMapValueEnum(rotateToCoordinate, ignoreMarker)
            canRotate = rotateToCoordinateValue in \
                [MapValueEnum.EMPTY, MapValueEnum.UNKNOWN, MapValueEnum.BLOCK, MapValueEnum.OBSTACLE] or \
                    (rotateToCoordinateValue in [MapValueEnum.AGENT, MapValueEnum.MARKER] and Coordinate.manhattanDistance(startCoordinate, rotateToCoordinate) > vision)

            return (canRotate, dict([(moveDirection, canRotate)]))

    def isCoordinatePassableForMultipleAttachements(self, map: DynamicMap, currentCoordinate: Coordinate, nextCoordinate: Coordinate,
        ignoreMarker: bool, attachedCoords: list[Coordinate]) -> bool:
        """
        Returns if the given `Coordinate` is passable from the current one for the `Agent`,
        if there are multiple attached entities.\n
        IT IS OBSOLATE, IT IS NOT USED, NOT SURE IF WORKS THE RIGHT WAY.
        """

        passableCoordsForAttacheds = [currentCoordinate.getShiftedCoordinate(coord) for coord in attachedCoords]
        passableCoordsForAttacheds.append(currentCoordinate)
        return all((nextCoordinate.getShiftedCoordinate(coord) in passableCoordsForAttacheds)
            or (map.getMapValueEnum(nextCoordinate.getShiftedCoordinate(coord), ignoreMarker) in
            [MapValueEnum.EMPTY, MapValueEnum.UNKNOWN]) for coord in attachedCoords)

    def calculateTravelConstantCosts(self, agentSpeed: int, clearEnergyCost: int,
        agentEnergy: int, agentMaxEnergy: int, clearChance: float,
        clearConstantConst: float) -> Tuple[float, float, float]:
        """
        Calculates the constant costs used at pathfinding.
        """

        agentTravelTime = 1 / agentSpeed
        clearCost = clearConstantConst / (max(agentEnergy - clearEnergyCost, 0.1) / agentMaxEnergy)
        clearSuccessTime = math.ceil(1 / clearChance)

        return (agentTravelTime, clearCost, clearSuccessTime)