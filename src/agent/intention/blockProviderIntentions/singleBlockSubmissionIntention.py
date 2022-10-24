from data.coreData import Coordinate, MapValueEnum, RotateDirection, Task
from data.intention import Observation

from agent.intention import AgentIntention, TravelIntention

from agent.action import AgentAction, SkipAction, SubmitAction, RotateAction, ClearAction, MoveAction

class SingleBlockSubmissionIntention(AgentIntention):
    """
    Intention for submitting a `Task` which requires
    only one `Block`.\n
    Finishes when submitted the `Task` successfully,
    or if had to drop it.\n
    TODO: Draft solution, needs to be refactorized.
    """

    task: Task
    finished: bool
    travelIntention: TravelIntention
    goalZone: Coordinate

    def __init__(self, task : Task, goalZone: Coordinate) -> None:
        self.task = task
        self.finished = False
        self.travelIntention = TravelIntention(goalZone)
        self.goalZone = goalZone

    async def planNextAction(self, observation: Observation) -> AgentAction:
        if observation.simDataServer.hasTaskExpired(self.task) or \
            not observation.agentData.attachedEntities or \
            self.goalZone not in observation.map.goalZones:
            self.finished = True
            return SkipAction()

        # are we there yet ? if yes, then try to submit
        if observation.agentCurrentCoordinate in observation.map.goalZones:
            blockDirection = Coordinate.getDirection(Coordinate.origo(),observation.agentData.attachedEntities[0].relCoord)
            taskDirection = Coordinate.getDirection(Coordinate.origo(),self.task.requirements[0].coordinate)

            # is the block in the right direction ?
            if taskDirection.isSameDirection(blockDirection):
               return SubmitAction(self.task.name)

            # opposite direction is the target ?
            oppositeDirection = blockDirection.opposite()
            if taskDirection.isSameDirection(oppositeDirection):
                # where to turn ?
                clockDirection, counterClockDirection = blockDirection.getAdjacentDirections()
                clockCoord = observation.agentCurrentCoordinate.getMovedCoord([clockDirection])
                counterClockCoord = observation.agentCurrentCoordinate.getMovedCoord([counterClockDirection])
                clockValue = observation.map.getMapValueEnum(clockCoord)
                counterClockValue = observation.map.getMapValueEnum(counterClockCoord)
                # is there free direction ?
                if clockValue in [MapValueEnum.EMPTY, MapValueEnum.DISPENSER]:
                    return RotateAction(RotateDirection.CLOCKWISE)
                if counterClockValue in [MapValueEnum.EMPTY, MapValueEnum.DISPENSER]:
                    return RotateAction(RotateDirection.COUNTERCLOCKWISE)
                # is there clearable direction ?
                if clockValue in [MapValueEnum.OBSTACLE,MapValueEnum.BLOCK] and clockCoord not in observation.agentData.attachedEntities:
                    return ClearAction(Coordinate.getRelativeCoordinate(observation.agentCurrentCoordinate, clockCoord))
                if counterClockValue in [MapValueEnum.OBSTACLE,MapValueEnum.BLOCK] and counterClockCoord not in observation.agentData.attachedEntities:
                    return ClearAction(Coordinate.getRelativeCoordinate(observation.agentCurrentCoordinate, counterClockCoord))
                # else:
                #     return self.moveToAnotherGoalPosition(observation)

            # adjacent directions may be targets?
            clockDirection, counterClockDirection = blockDirection.getAdjacentDirections()

            # clock direction is the target ?
            targetCoord = observation.agentCurrentCoordinate.getMovedCoord([clockDirection])
            targetMapValue = observation.map.getMapValueEnum(targetCoord)
            if taskDirection.isSameDirection(clockDirection):
                if targetMapValue in [MapValueEnum.EMPTY, MapValueEnum.DISPENSER]:
                    return RotateAction(RotateDirection.CLOCKWISE)
                if targetMapValue in [MapValueEnum.OBSTACLE,MapValueEnum.BLOCK] and targetCoord not in observation.agentData.attachedEntities:
                    return ClearAction(Coordinate.getRelativeCoordinate(observation.agentCurrentCoordinate, targetCoord))
                # else:
                #     return self.moveToAnotherGoalPosition(observation)

            # counterclock direction is the target ?
            targetCoord = observation.agentCurrentCoordinate.getMovedCoord([counterClockDirection])
            targetMapValue = observation.map.getMapValueEnum(targetCoord)
            if taskDirection.isSameDirection(counterClockDirection):
                if targetMapValue in [MapValueEnum.EMPTY, MapValueEnum.DISPENSER]:
                    return RotateAction(RotateDirection.COUNTERCLOCKWISE)
                if targetMapValue in [MapValueEnum.OBSTACLE,MapValueEnum.BLOCK] and targetCoord not in observation.agentData.attachedEntities:
                   return ClearAction(Coordinate.getRelativeCoordinate(observation.agentCurrentCoordinate, targetCoord))
                # else:
                #     return self.moveToAnotherGoalPosition(observation)

        closestGoalZone = observation.map.tryReserveCloserGoalZoneForTask(observation.agentData.id, self.goalZone,
            observation.agentCurrentCoordinate, [r.coordinate for r in self.task.requirements])
        if closestGoalZone is not None:
            self.goalZone = closestGoalZone
            self.travelIntention = TravelIntention(self.goalZone)

        return await self.travelIntention.planNextAction(observation)

    def moveToAnotherGoalPosition(self, observation: Observation) -> AgentAction:
        # move in the opposite direction of the task requirement
        # TODO this is not a complete solution, but it may sometimes help
        return MoveAction([Coordinate.getDirection(observation.agentCurrentCoordinate,observation.agentCurrentCoordinate.getShiftedCoordinate(self.task.requirements[0].coordinate))])


    def checkFinished(self, _: Observation) -> bool:
        return self.finished
    
    def updateCoordinatesByOffset(self, offsetCoordinate: Coordinate) -> None:
        self.travelIntention.updateCoordinatesByOffset(offsetCoordinate)

        self.goalZone.updateByOffsetCoordinate(offsetCoordinate)
    
    def normalizeCoordinates(self) -> None:
        self.travelIntention.normalizeCoordinates()

        self.goalZone.normalize()
    
    def explain(self) -> str:
        explanation = "singleblocksubmitting " + self.task.name + " finished: " + str(self.finished)

        return explanation
