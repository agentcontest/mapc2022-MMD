from enum import Enum
from typing import Tuple

class MapValueEnum(Enum):
    """
    Represents an entity type on the map.
    """

    EMPTY = 0
    OBSTACLE = 1
    AGENT = 2
    DISPENSER = 3
    BLOCK = 4
    MARKER = 5
    UNKNOWN = 6

class Direction(Enum):
    """
    Represents the 4 global directions:
    north, east, south, west.
    """

    NORTH = 0
    EAST = 1
    SOUTH = 2
    WEST = 3

    def __str__(self) -> str:
        match self.value:
            case 0:
                return "n"
            case 1:
                return "e"
            case 2:
                return "s"
            case 3:
                return "w"
    
    def opposite(self) -> 'Direction':
        """
        Returns the opposite direction
        """

        match self.value:
            case 0:
                return Direction.SOUTH
            case 1:
                return Direction.WEST
            case 2:
                return Direction.NORTH
            case 3:
                return Direction.EAST
    
    def isOppositeDirection(self, other: 'Direction') -> bool:
        """
        Returns if the other `Direction` is the opposite of the current one.
        """

        return (self.value + other.value) % 2 == 0
    
    def isSameDirection(self, other: 'Direction') -> bool:
        """
        Returns if the other `Direction` is the same as the current one.
        """

        return self.value == other.value
    
    def getAdjacentDirections(self) -> Tuple['Direction']:
        """
        Returns the not opposite and the not same `Directions`.
        """

        return (Direction((self.value + 1) % 4), Direction((self.value - 1) % 4))

class RotateDirection(Enum):
    """
    Represents a rotate direction, it can be either clockwise or counter-clockwise.
    """

    CLOCKWISE = 0
    COUNTERCLOCKWISE = 1

    def __str__(self) -> str:
        match self.value:
            case 0:
                return "cw"
            case 1:
                return "ccw"

class AgentActionEnum(Enum):
    """
    Represents an Agent Action in Enum.
    """

    SKIP = 0
    MOVE = 1
    ROTATE = 2
    ADOPT = 3
    CLEAR = 4
    ATTACH = 5
    DETACH = 6
    REQUEST = 7
    CONNECT = 8
    DISCONNECT = 9
    SUBMIT = 10
    SURVEY = 11

    def __str__(self) -> str:
        match self.value:
            case 0:
                return "SKIP"
            case 1:
                return "MOVE"
            case 2:
                return "ROTATE"
            case 3:
                return "ADOPT"
            case 4:
                return "CLEAR"
            case 5:
                return "ATTACH"
            case 6:
                return "DETACH"
            case 7:
                return "REQUEST"
            case 8:
                return "CONNECT"
            case 9:
                return "DISCONNECT"
            case 10:
                return "SUBMIT"
            case 11:
                return "SURVEY"

class AgentIntentionRole(Enum):
    """
    Represents an agent logical role, eg, what it's currently doing.
    """

    EXPLORER = 0
    COORDINATOR = 1
    BLOCKPROVIDER = 2
    SINGLEBLOCKPROVIDER = 3

    def __str__(self) -> str:
        match self.value:
            case 0:
                return "EXPLORER"
            case 1:
                return "COORDINATOR"
            case 2:
                return "BLOCKPROVIDER"
            case 3:
                return "SINGLEBLOCKPROVIDER"

class RegulationType(Enum):
    """
    Represents a type of a norm regulation.
    """

    BLOCK = 0
    ROLE = 1

    def __str__(self) -> str:
        match self.value:
            case 0:
                return "BLOCK"
            case 1:
                return "ROLE"