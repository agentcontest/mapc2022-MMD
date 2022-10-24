import math

from data.coreData.enums import Direction, RotateDirection

class Coordinate:
    """
    Coordinate which can be relative or absolute.
    Working with relative coordinates requires to set the `normalize` param False,
    which is True by default.
    """

    maxWidth: int | None = None         # Max map width
    maxHeight: int | None = None        # Map map height
    dimensionsCalculated: bool = False  # Represesents if both dimensions are calculated

    __match_args__ = ("x", "y")
    def __init__(self, x: float, y: float, normalize: bool = True) -> None:
        if x > 0:
            self.x = int(math.floor(x))
        else:
            self.x = int(math.ceil(x))

        if y > 0:
            self.y = int(math.floor(y))
        else:
            self.y = int(math.ceil(y))
        
        if normalize:
            self.normalize()
            
    def normalize(self) -> None:
        """
        Normalizes the coordinate based on the
        calculated dimensions.
        """
        
        if Coordinate.maxWidth is not None:
            self.x = self.x % Coordinate.maxWidth

        if Coordinate.maxHeight is not None:
            self.y = self.y % Coordinate.maxHeight

    def move(self, directions: list[Direction], normalize: bool = True) -> None:
        """
        Changes the coordinate's values based on the directions.
        """

        for direction in directions:
            match direction:
                case Direction.NORTH:
                    self.y -= 1
                case Direction.EAST:
                    self.x += 1
                case Direction.SOUTH:
                    self.y += 1
                case Direction.WEST:
                    self.x -= 1
        
        if normalize:
            self.normalize()

    def negate(self) -> 'Coordinate':
        """
        Returns the negated `Coordinate`
        """
        return Coordinate(-1 * self.x, -1 * self.y, False)

    def getMovedCoord(self, directions: list[Direction], noramlize: bool = True) -> 'Coordinate':
        """
        Returns a new moved `Coordinate`
        """

        coord = Coordinate(self.x, self.y, noramlize)
        coord.move(directions, noramlize)
        return coord
    
    def getRotateDirection(self, direction: Direction) -> RotateDirection:
        """
        Returns the `RotateDirection` to be in the given `Direction`
        Only usable for relative `Coordinates`.
        """

        match direction:
            case Direction.NORTH:
                return RotateDirection.CLOCKWISE if self.x > 0 else RotateDirection.COUNTERCLOCKWISE
            case Direction.EAST:
                return RotateDirection.CLOCKWISE if self.y > 0 else RotateDirection.COUNTERCLOCKWISE
            case Direction.SOUTH:
                return RotateDirection.COUNTERCLOCKWISE if self.x > 0 else RotateDirection.CLOCKWISE
            case Direction.WEST:
                return RotateDirection.COUNTERCLOCKWISE if self.y > 0 else RotateDirection.CLOCKWISE

    def neighbors(self, normalize: bool = True, searchRange: int = 1, distant: int = 0) -> list['Coordinate']:
        """
        Returns the `Coordinates's` neigbors. The `searchRange` param is used for max distance,
        `distance` param is used for min distance.
        """

        neighbors = []
        for i in range(self.x - searchRange, self.x + searchRange + 1):
            for j in range(self.y - searchRange, self.y + searchRange + 1):
                coord = Coordinate(i, j, normalize)
                if Coordinate.manhattanDistance(self, coord) <= searchRange and \
                    Coordinate.manhattanDistance(self, coord) >= distant:
                    neighbors.append(coord)
        
        if self in neighbors:
            neighbors.remove(self)
            
        return neighbors
    
    def getSurroundingNeighbors(self, normalize: bool = True) -> list['Coordinate']:
        """
        Returns the `Coordinate's` neighbors by one Manhattan-distance and the closest
        ones diagonally.
        """

        neighbors = self.neighbors(normalize)
        neighbors.append(self.getShiftedCoordinate(Coordinate(1, 1, normalize)))
        neighbors.append(self.getShiftedCoordinate(Coordinate(1, -1, normalize)))
        neighbors.append(self.getShiftedCoordinate(Coordinate(-1, 1, normalize)))
        neighbors.append(self.getShiftedCoordinate(Coordinate(-1, -1, normalize)))

        return neighbors

    def getVisionBorderCoordinates(self, vision: int) -> list['Coordinate']:
        """
        Returns the `Coordinates` which are `vision` Manhattan-distance away.
        """

        coords = []
        iteration = 0
        for i in range(self.x - vision - 1, self.x + vision + 2):
            coords.append(Coordinate(i, self.y + iteration))
            coords.append(Coordinate(i, self.y - iteration))

            if i < self.x:
                iteration += 1
            else:
                iteration -= 1

        return coords[1:-1]

    def getShiftedCoordinate(self, offsetCoordinate: 'Coordinate', normalize: bool = True) -> 'Coordinate':
        """
        Returns the sum of two `Coordinates`
        """

        return Coordinate(self.x + offsetCoordinate.x, self.y + offsetCoordinate.y, normalize)
    
    def updateByOffsetCoordinate(self, offstetCoordinate: 'Coordinate', normalize: bool = True) -> None:
        """
        Adds the given `Coordinate` to the current one.
        """

        self.x += offstetCoordinate.x
        self.y += offstetCoordinate.y

        if normalize:
            self.normalize()
    
    def rotateRelCoord(self, direction: RotateDirection) -> None:
        """
        Rotates the `Coordinate` to the given `RotateDirection`.
        """

        originalX = self.x
        originalY = self.y

        match direction:
            case RotateDirection.CLOCKWISE:
                self.x = originalY * (-1)
                self.y = originalX
            case RotateDirection.COUNTERCLOCKWISE:
                self.x = originalY
                self.y = originalX * (-1)

    def getRotatedRelCoord(self, direction: RotateDirection) -> 'Coordinate':
        """
        Returns the rotated relative `Coordinate`.
        """

        coord = Coordinate(self.x, self.y, False)
        coord.rotateRelCoord(direction)
        return coord
    
    def copy(self, normalize: bool = True) -> 'Coordinate':
        """
        Returns a copy of the current `Coordinate`.
        """

        return Coordinate(self.x, self.y, normalize)

    def __eq__(self, other: 'Coordinate') -> bool:
        return isinstance(other, self.__class__) and self.x == other.x and self.y == other.y
    
    def __neq__(self, other: 'Coordinate') -> bool:
        return not self.__eq__(other)
    
    def __hash__(self) -> int:
        return hash(tuple(sorted(self.__dict__.items())))
    
    def __str__(self) -> str:
        return "(" + str(self.x) + ", " + str(self.y) + ")"
    
    def __repr__(self) -> str:
        return self.__str__()
    
    @staticmethod
    def origo() -> 'Coordinate':
        """
        Returns a  `Coordinate` which represents (0, 0)
        """

        return Coordinate(0, 0)

    @staticmethod
    def getDirection(start: 'Coordinate', end: 'Coordinate') -> Direction:
        """
        Returns the `Direction` between the two given `Coordinates`
        calculated by the relative `Coordinate` between them.
        """

        relCoord = Coordinate.getRelativeCoordinate(start, end)

        if relCoord.x == 0 and relCoord.y > 0:
            return Direction.SOUTH
        elif relCoord.x > 0 and relCoord.y == 0:
            return Direction.EAST
        elif relCoord.x == 0 and relCoord.y < 0:
            return Direction.NORTH
        elif relCoord.x < 0 and relCoord.y == 0:
            return Direction.WEST
        elif abs(relCoord.x) >= abs(relCoord.y):
            if relCoord.x > 0:
                return Direction.EAST
            else:
                return Direction.WEST
        else:
            if relCoord.y > 0:
                return Direction.SOUTH
            else:
                return Direction.NORTH
    
    @staticmethod
    def getRelativeCoordinateByDirection(direction: Direction) -> 'Coordinate':
        """
        Returns a relative, one Manhattan-distance away `Coordinate` based
        on the given direction.
        """

        match direction:
            case Direction.NORTH:
                return Coordinate(0, -1, False)
            case Direction.EAST:
                return Coordinate(1, 0, False)
            case Direction.SOUTH:
                return Coordinate(0, 1, False)
            case Direction.WEST:
                return Coordinate(-1, 0, False)

    @staticmethod
    def getRelativeCoordinate(start: 'Coordinate', end: 'Coordinate') -> 'Coordinate':
        """
        Returns the relative `Coordinate` between two absolute ones.
        """

        xDifference = end.x - start.x
        yDifference = end.y - start.y

        if Coordinate.maxWidth is not None:
            xRealCoordPos = xDifference % Coordinate.maxWidth
            xRealCoordNeg = xDifference % ((-1) * Coordinate.maxWidth)
            xDifference = xRealCoordPos if abs(xRealCoordPos) < abs(xRealCoordNeg) else xRealCoordNeg

        if Coordinate.maxHeight is not None:
            yRealCoordPos = yDifference % Coordinate.maxHeight
            yRealCoordNeg = yDifference % ((-1) * Coordinate.maxHeight)
            yDifference = yRealCoordPos if abs(yRealCoordPos) < abs(yRealCoordNeg) else yRealCoordNeg

        return Coordinate(xDifference, yDifference, False)

    @staticmethod
    def manhattanDistance(start: 'Coordinate', end: 'Coordinate') -> float:
        """
        Returns the Manhatten-distance between two `Coordinates`
        """

        relCoord = Coordinate.getRelativeCoordinate(start, end)
        return abs(relCoord.x) + abs(relCoord.y)
    
    @staticmethod
    def distance(start: 'Coordinate', end: 'Coordinate') -> float:
        """
        Returns the Euclidean-distance between two `Coordinates`
        """

        relCoord = Coordinate.getRelativeCoordinate(start, end)
        return math.sqrt(pow(relCoord.x, 2) + pow(relCoord.y, 2))
    
    @staticmethod
    def getClosestCoordByDistanceByTwoCoordsLine(start: 'Coordinate', end: 'Coordinate', distance: int, multiplier : int = 1) -> 'Coordinate':
        """
        Returns the closest `Coordinate` by the given distance on a line
        created by the two `Coordinates`.
        """

        difference_vector = (start.x - end.x, start.y - end.y)
        norm_of_vector = math.sqrt(pow(difference_vector[0], 2) + pow(difference_vector[1], 2))

        return Coordinate(end.x - multiplier * distance * difference_vector[0] / norm_of_vector,
            end.y - multiplier * distance * difference_vector[1] / norm_of_vector)
    
    @staticmethod
    def isCloserNewCoordinate(fromCoord: 'Coordinate', currentCoord: 'Coordinate', newCoord: 'Coordinate') -> bool:
        """
        Returns if the current `Coordinate` is closer than the new one.
        """

        return (Coordinate.distance(fromCoord, newCoord)
            < Coordinate.distance(fromCoord, currentCoord))