import random

from data.coreData import Coordinate, MapValueEnum

from data.intention import Observation
from agent.intention.agentIntention import AgentIntention

from agent.action import AgentAction, SkipAction, ClearAction, RotateAction

class SkipIntention(AgentIntention):    
    """
    Intention used for skipping, it has no goal.
    Can be toggled to allow rotates, so when it
    blocks a dispenser and it is on then it will rotate.
    """

    allowRotate: bool

    def __init__(self, allowRotate: bool) -> None:
        self.allowRotate = allowRotate

    async def planNextAction(self, observation: Observation) -> AgentAction:
        # Only rotate if it is allowed, only 1 entity is attached and the
        # entity blocks a dispenser
        if self.allowRotate and len(observation.agentData.attachedEntities) == 1 and \
            observation.map.getMapValueEnum(observation.agentCurrentCoordinate.getShiftedCoordinate(
                observation.agentData.attachedEntities[0].relCoord)) == MapValueEnum.DISPENSER:
                
            # Try to rotate to any available direction
            faceDirection = Coordinate.getDirection(observation.agentData.attachedEntities[0].relCoord, Coordinate.origo())

            leftCoordinate = observation.agentCurrentCoordinate.getMovedCoord([faceDirection.getAdjacentDirections()[0]])
            rightCoordinate = observation.agentCurrentCoordinate.getMovedCoord([faceDirection.getAdjacentDirections()[1]])
            canRotateToRightDirection = observation.map.getMapValueEnum(leftCoordinate) in [MapValueEnum.EMPTY, MapValueEnum.OBSTACLE]
            canRotateToLeftDirection = observation.map.getMapValueEnum(rightCoordinate) in [MapValueEnum.EMPTY, MapValueEnum.OBSTACLE]

            rotateData = [d[1] for d in [(canRotateToLeftDirection, rightCoordinate), (canRotateToRightDirection, leftCoordinate)] if d[0]]
            # If it can not rotate then just skip
            if not any(rotateData):
                return SkipAction()
            # Else rotate and clear before, if it is needed
            else:
                coordinate = random.choice(rotateData)
                    
                if observation.map.getMapValueEnum(coordinate) == MapValueEnum.OBSTACLE:
                    return ClearAction(Coordinate.getRelativeCoordinate(observation.agentCurrentCoordinate, coordinate))
                else:
                    return RotateAction(Coordinate.getRotateDirection(observation.agentCurrentCoordinate, Coordinate.getDirection(observation.agentCurrentCoordinate, coordinate)))
                
        else:
            return SkipAction()

    def checkFinished(self, _: Observation) -> bool:
        return False
    
    def updateCoordinatesByOffset(self, _: Coordinate) -> None:
        pass
    
    def normalizeCoordinates(self) -> None:
        pass

    def explain(self) -> str:
        return "skipping"