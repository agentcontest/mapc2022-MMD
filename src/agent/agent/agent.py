from typing import Type
import mapc2022 as mapc2022

from data.coreData import Coordinate, AgentActionEnum, AttachedEntity, MapcRole, MapValueEnum, AgentIntentionRole
from data.map import MapUpdateData
from data.server import SimulationDataServer, MapServer
from data.wrapper import DynamicPerceptWrapper
from data.intention import Observation

from agent.action import *
from agent.intention.mainAgentIntention import MainAgentIntention
from agent.agent.intentionHandler import IntentionHandler

class Agent:
    """
    Represents a single agent in the simulation.\n
    Maintains communication between the simulation server,
    manages its intentions through the `IntentionHandler` and
    sends informations to the local servers.
    """

    id: str
    mapServer: MapServer
    simDataServer: SimulationDataServer
    dynamicPerceptWrapper: DynamicPerceptWrapper | None
    observation: Observation | None
    attachedEntities: list[AttachedEntity]
    mapcAgent: mapc2022.Agent | None                        # Proxy to the simulation server
    mapcRole: MapcRole | None
    intentionHandler: IntentionHandler
    action: AgentAction | None

    def __init__(self, id : str, mapServer: MapServer, simDataServer: SimulationDataServer) -> None:
        self.id = id
        self.mapServer = mapServer
        self.simDataServer = simDataServer

        self.dynamicPerceptWrapper = None
        self.observation = None
        self.attachedEntities = []

        self.mapcAgent = None
        self.mapcRole = None
        
        self.intentionHandler = IntentionHandler(self.id)
        self.action = None
    
    def connect(self, host: str, port: int, password: str) -> None:
        """
        Connects to the simulation server.
        """

        self.mapcAgent = mapc2022.Agent.open(user = self.id, pw = password,
            host = host, port = port)
    
    def registerToMapServer(self) -> None:
        """
        Registers to the `MapServer` with a dynamic percept.
        Also sends basic information to the `SimulationDataServer`.
        """

        self.dynamicPerceptWrapper = DynamicPerceptWrapper(self.mapcAgent.dynamic["percept"],
                            self.simDataServer.staticPercept.roles, self.mapcAgent.dynamic["step"])
        self.mapcRole = self.simDataServer.staticPercept.roles[self.dynamicPerceptWrapper.role]

        updateData = MapUpdateData(
            self.dynamicPerceptWrapper.things,
            self.dynamicPerceptWrapper.markers,
            self.dynamicPerceptWrapper.dispensers,
            self.dynamicPerceptWrapper.goalZones,
            self.dynamicPerceptWrapper.roleZones
        )
        self.mapServer.registerNewMap(self.id, self.simDataServer.markerPurgeInterval, self.mapcAgent.dynamic["step"],
            updateData)
        self.simDataServer.setAgentMaxEnegy(self.dynamicPerceptWrapper.energy)
        self.simDataServer.setSimulationStep(self.mapcAgent.dynamic["step"])
        self.simDataServer.updateTasks(self.dynamicPerceptWrapper.tasks)
        self.setObservation()

    def insertIntention(self, intention: MainAgentIntention) -> None:
        """
        Inserts the given `MainAgentIntention` to the `IntentionHandler`.
        """

        self.intentionHandler.insertIntention(intention)

    def generateOptions(self) -> None:
        """
        Generates local intention options for the `Agent`.
        """

        self.intentionHandler.generateOptions(self.observation)
    
    def filterOptions(self) -> None:
        """
        Filters intention options for the `Agent`.
        """

        self.intentionHandler.filterOptions()

    async def planNextAction(self) -> None:
        self.setObservation()

        if not self.observation.agentData.deactivated:
            currentIntention = self.intentionHandler.getCurrentIntention()
            self.action = await currentIntention.planNextAction(self.observation)
        else:
            self.action = SkipAction()
    
    def checkFinishedCurrentIntention(self) -> bool:
        """
        Returns if the current `MainAgentIntention` has been finished.
        """

        currentIntention = self.intentionHandler.getCurrentIntention()
        return currentIntention is not None and currentIntention.checkFinished(self.observation)
    
    def isCurrentIntentionRelatedToTask(self) -> bool:
        """
        Returns if its current intention is related to a `Task`:
        providing block, coordinating or single block providing
        """

        return self.intentionHandler.isCurrentIntentionRelatedToTask()

    def finishCurrentIntention(self) -> None:
        """
        Finished the current intention in the `IntentionHandler`.
        """

        self.intentionHandler.finishCurrentIntention()

    def updateCoordinatesByOffset(self, offsetCoordinate: Coordinate) -> None:
        """
        Shifts the all the `Coordinates` in the `Observation` and
        in the `IntentionHandler`.
        """

        self.setObservation()
        self.intentionHandler.updateIntentionCoordinatesByOffset(offsetCoordinate)
    
    def normalizeCoordinates(self) -> None:
        """
        Normalizes all the `Coordinates` in the `Observation` and in
        the `IntentionHandler`.
        """

        self.setObservation()
        self.intentionHandler.normalizeIntentionCoordinates()
    
    def setIntentionRole(self, role: AgentIntentionRole) -> None:
        """
        Sets the `AgentIntentionRole`.
        """

        self.intentionHandler.setIntentionRole(role)
    
    def getIntentionRole(self) -> AgentIntentionRole:
        """
        Returns the current `AgentIntentionRole`.
        """

        return self.intentionHandler.getIntentionRole()
    
    def doesTaskCurrently(self) -> bool:
        """
        Returns if has the given type of `MainAgentIntention`.
        """

        return self.intentionHandler.doesTaskCurrently()
    
    def hasGivenTypeOfIntention(self, type: Type) -> bool:
        return self.intentionHandler.hasGivenTypeOfIntention(type)

    def abandonCurrentTask(self) -> None:
        """
        Drops the current `Task`: sends this information
        to the `IntentionHandler`.
        """

        self.intentionHandler.abandonCurrentTask()

    def setDynamicPercept(self) -> None:
        """
        Stores the retrieved dynamic percept and sends
        it to its `DynamicMap` and other informations to the
        `SimulationDataServer`.
        """

        self.dynamicPerceptWrapper = DynamicPerceptWrapper(self.mapcAgent.dynamic["percept"],
                            self.simDataServer.staticPercept.roles, self.mapcAgent.dynamic["step"])
        self.mapcRole = self.simDataServer.staticPercept.roles[self.dynamicPerceptWrapper.role]
        mapUpdateData = MapUpdateData(
            self.dynamicPerceptWrapper.things,
            self.dynamicPerceptWrapper.markers,
            self.dynamicPerceptWrapper.dispensers,
            self.dynamicPerceptWrapper.goalZones,
            self.dynamicPerceptWrapper.roleZones
        )
        self.mapServer.updateMap(self.id, self.mapcAgent.dynamic["step"], mapUpdateData)
        self.simDataServer.setSimulationStep(self.mapcAgent.dynamic["step"])
        self.simDataServer.setAgentMaxEnegy(self.dynamicPerceptWrapper.energy)

        # Maintain attached entity list
        for attachedEntity in list(self.attachedEntities):
            if attachedEntity.relCoord not in self.dynamicPerceptWrapper.attached:
                self.removeNotConnectedEntities(attachedEntity)

        self.simDataServer.updateTasks(self.dynamicPerceptWrapper.tasks)
        self.simDataServer.updateNorms(self.dynamicPerceptWrapper.norms)
        self.setObservation()

    def executeAction(self) -> str:
        """
        Executes the planned `AgentAction`
        and returns the response of it.
        """

        return self.action.perform(self.mapcAgent)

    def processActionResult(self, actionResult: str) -> None:
        """
        Processes the result of the executed `AgentAction`.
        """

        if isinstance(self.action, MoveAction):
            map = self.mapServer.getMap(self.id)
            currentCoord = map.getAgentCoordinate(self.id)
            
            # Move all the Coordinates
            if actionResult == "success":
                currentCoord.move(self.action.directions)
                map.setAgentCoordinate(self.id, currentCoord)
            
            # Else just the first one, because max is 2, failed is 0, then partial is 1
            elif actionResult == "partial_success":
                currentCoord.move([(self.action.directions[0])])
                map.setAgentCoordinate(self.id, currentCoord)

        elif isinstance(self.action, RotateAction) and actionResult == "success":
            # Rotate all attached entities in the list
            for attachedEntity in self.attachedEntities:
                attachedEntity.relCoord.rotateRelCoord(self.action.rotateDirection)

        elif isinstance(self.action, AttachAction) and actionResult == "success":
            # Update the attached entity list
            self.attachedEntities.append(AttachedEntity(
                Coordinate.getRelativeCoordinateByDirection(self.action.direction),
                self.action.entityType,
                self.action.details))

        elif isinstance(self.action, DetachAction) and actionResult == "success":
            # Update the attached entity list
            detachedRelCoord = Coordinate.origo().getMovedCoord([self.action.direction], False)
            detachedAttachedEntity = next(filter(lambda e: e.relCoord == detachedRelCoord, self.attachedEntities), None)

            if detachedAttachedEntity is not None:
                self.removeNotConnectedEntities(detachedAttachedEntity)

        elif isinstance(self.action, AdoptAction) and actionResult == "success":
            # Send the role change information to the SimulationDataServer
            self.simDataServer.switchRoleForAgent(self.id, self.action.roleName)

        elif isinstance(self.action, ConnectAction) and actionResult == "success":
            # Update the attached entity list, BUT with only one element
            # the rest of them is not calculated, because it will detach instantly after
            # this action. TODO: calculate the rest, because this can cause bugs
            if self.action.toAttachedEntity is not None:
                self.attachedEntities.append(self.action.toAttachedEntity)
                self.connectAttachedEntities(self.action.relCoord, self.action.toAttachedEntity)

        elif isinstance(self.action, DisconnectAction) and actionResult == "success":
            raise NotImplementedError("Disconnect handle") # TODO: Handle this action if needed

        elif isinstance(self.action, SubmitAction) and actionResult == "success":
            # Clear the attached list, only valid if
            # the submittor has only Task related attached entities
            self.attachedEntities.clear()
    
    def setDynamicPerceptAfterAction(self, actionResult: str) -> None:
        """
        Sets the retrieved dynamic percept
        and calculates the clear cost if it made a clear or
        the energy recharge value.
        """

        agentPrevEnergy = self.dynamicPerceptWrapper.energy
        deactivatedPrev = self.dynamicPerceptWrapper.deactivated
        self.setDynamicPercept()

        # Calculate clear enegy cost if just cleared
        if isinstance(self.action, ClearAction) and actionResult == "success":
            self.simDataServer.setClearEnergyCost(agentPrevEnergy - self.dynamicPerceptWrapper.energy)
        
        # Calculate energy regain if it is not deactivated
        elif not deactivatedPrev and agentPrevEnergy != self.simDataServer.agentMaxEnergy:
            self.simDataServer.setAgentEnergyRecharge(self.dynamicPerceptWrapper.energy - agentPrevEnergy)
        
        if isinstance(self.action, SubmitAction) and actionResult == "success":
            print(f"score: {self.dynamicPerceptWrapper.score}")

    def isDeactivated(self) -> bool:
        """
        Returns if the `Agent` is deactivated.
        """

        return self.dynamicPerceptWrapper is not None and self.dynamicPerceptWrapper.deactivated

    def setObservation(self) -> None:
        """
        Initializes the `Observation` object.
        """

        dynamicMap = self.mapServer.getMap(self.id)
        self.observation = Observation(self.id, self.simDataServer, dynamicMap, self.mapcRole,
            self.dynamicPerceptWrapper.energy, self.dynamicPerceptWrapper.deactivated,
            AgentActionEnum[self.dynamicPerceptWrapper.lastAction.upper()] \
                if self.dynamicPerceptWrapper.lastAction.upper() in [str(a) for a in AgentActionEnum] else AgentActionEnum.SKIP,
            self.dynamicPerceptWrapper.lastActionResult,
            self.attachedEntities, self.dynamicPerceptWrapper.attached,
            self.dynamicPerceptWrapper)

    def bidGoalZone(self, blockRelCoords: list[Coordinate]) -> float:
        """
        Returns an estimation how much step is needed
        to get to a goal zone. Includes if
        the `Agent` has the right or wrong role.
        """

        currentMap = self.mapServer.getMap(self.id)
        agentCurrentCoordinate = currentMap.getAgentCoordinate(self.id)

        # If the agent has a coordinator role then no need to get a new role
        if self.mapcRole in self.simDataServer.getCoordinatorRoles():
            return Coordinate.distance(agentCurrentCoordinate, currentMap.getClosestFreeGoalZoneForTask(agentCurrentCoordinate, blockRelCoords)) + \
                len(blockRelCoords) * self.mapcRole.getFreeSpeed()
        
        # Else it has to travel to a role zone
        else:
            roleZoneCoord = currentMap.getClosestRoleZone(agentCurrentCoordinate)
            return 1 + Coordinate.distance(agentCurrentCoordinate, roleZoneCoord) + \
                Coordinate.distance(roleZoneCoord, currentMap.getClosestFreeGoalZoneForTask(roleZoneCoord, blockRelCoords)) + \
                    len(blockRelCoords) * self.mapcRole.getFreeSpeed()

    def bidDispenser(self, type: str, goalZoneCoord: Coordinate) -> float:
        """
        Returns an estimation how much step is needed
        to get to the given type of `Dispenser`. Includes if
        the `Agent` has the right or wrong role.
        """

        currentMap = self.mapServer.getMap(self.id)
        agentCurrentCoordinate = currentMap.getAgentCoordinate(self.id)

        # If the agent has a block provider role then no need to get a new role
        if self.mapcRole in self.simDataServer.getBlockProviderRoles():
            if len(self.attachedEntities) == 1:
                attachedEntity = self.attachedEntities[0]
                
                # If has the right block then travelling to the Dispenser is not required
                if attachedEntity.entityType == MapValueEnum.BLOCK and attachedEntity.details == type:
                   return Coordinate.manhattanDistance(agentCurrentCoordinate, goalZoneCoord) / self.mapcRole.getSpeed(1)
            
            dispenserCoord = currentMap.getClosestDispenser(type, agentCurrentCoordinate)
            return 2 + Coordinate.manhattanDistance(agentCurrentCoordinate, dispenserCoord) / self.mapcRole.getFreeSpeed() + \
                 Coordinate.manhattanDistance(dispenserCoord, goalZoneCoord) / self.mapcRole.getSpeed(1)
        
        # Else it has to travel to a role zone
        else:
            roleZoneCoord = currentMap.getClosestRoleZone(agentCurrentCoordinate)
            roleZoneCoordDistance = Coordinate.manhattanDistance(agentCurrentCoordinate, roleZoneCoord)

            if len(self.attachedEntities) == 1:
                attachedEntity = self.attachedEntities[0]

                # If has the right block then travelling to the Dispenser is not required
                if attachedEntity.entityType == MapValueEnum.BLOCK and attachedEntity.details == type:
                   return 1 + roleZoneCoordDistance / self.mapcRole.getSpeed(1) + Coordinate.manhattanDistance(roleZoneCoord,goalZoneCoord) / self.mapcRole.getSpeed(1)

            # Else need to travel to the right Dispenser too
            dispenserCoord = currentMap.getClosestDispenser(type, roleZoneCoord)

            return 2 + roleZoneCoordDistance / self.mapcRole.getFreeSpeed() + Coordinate.manhattanDistance(roleZoneCoord, dispenserCoord) / self.mapcRole.getFreeSpeed() + \
                Coordinate.manhattanDistance(dispenserCoord, goalZoneCoord) / self.mapcRole.getSpeed(1)

    def bidSingleBlock(self, type: str, blockRelCoords: list[Coordinate]) -> float:
        """
        Returns an estimation how much step is needed
        to get a single `Block` `Task` done. Includes if
        the `Agent` has the right or wrong role.
        """

        currentMap = self.mapServer.getMap(self.id)
        agentCurrentCoordinate = currentMap.getAgentCoordinate(self.id)

        singleBlockProviderRoles = self.simDataServer.getSingleBlockProviderRoles()
        blockProviderRoles = self.simDataServer.getBlockProviderRoles()
        coordinatorRoles = self.simDataServer.getCoordinatorRoles()

        # Check if the only attached Block is the right type
        if len(self.attachedEntities) == 1:
            attachedEntity = self.attachedEntities[0]
            if attachedEntity.entityType == MapValueEnum.BLOCK and attachedEntity.details == type:
                # The right Block is already attached

                # If current role is fine then calculate the cost
                if self.mapcRole in singleBlockProviderRoles or self.mapcRole in blockProviderRoles:
                    return Coordinate.manhattanDistance(agentCurrentCoordinate, currentMap.getClosestFreeGoalZoneForTask(agentCurrentCoordinate, blockRelCoords)) / self.mapcRole.getSpeed(1)
                
                # Else have to search a role zone too
                else:
                    roleZoneCoord = currentMap.getClosestRoleZone(agentCurrentCoordinate)
                    return 2 + Coordinate.manhattanDistance(agentCurrentCoordinate, roleZoneCoord) / self.mapcRole.getSpeed(1) + \
                        Coordinate.manhattanDistance(roleZoneCoord, currentMap.getClosestDispenser(type, roleZoneCoord)) / self.mapcRole.getSpeed(1) 
            
            # Else have to find the right type of Dispenser
            else:
                # If current role is fine then calculate the cost
                if self.mapcRole in singleBlockProviderRoles or self.mapcRole in blockProviderRoles:
                    dispenserCoord = currentMap.getClosestDispenser(type, agentCurrentCoordinate)
                    return 2 + Coordinate.manhattanDistance(agentCurrentCoordinate, dispenserCoord) / self.mapcRole.getFreeSpeed() + \
                        Coordinate.manhattanDistance(dispenserCoord, currentMap.getClosestFreeGoalZoneForTask(dispenserCoord, blockRelCoords)) / self.mapcRole.getSpeed(1)
                
                # Else have to search a role zone too
                else:
                    roleZoneCoord = currentMap.getClosestRoleZone(agentCurrentCoordinate)
                    dispenserCoord = currentMap.getClosestDispenser(type, roleZoneCoord)
                    return 3 + Coordinate.manhattanDistance(agentCurrentCoordinate, roleZoneCoord) / self.mapcRole.getFreeSpeed() + \
                        Coordinate.manhattanDistance(roleZoneCoord, dispenserCoord) / self.mapcRole.getFreeSpeed() + \
                        Coordinate.manhattanDistance(dispenserCoord, currentMap.getClosestFreeGoalZoneForTask(dispenserCoord, blockRelCoords)) / self.mapcRole.getSpeed(1) 

        # Else have the wrong Blocks
        else:
            # If current role is fine then calculate the cost
            if self.mapcRole in singleBlockProviderRoles or self.mapcRole in coordinatorRoles:
                dispenserCoord = currentMap.getClosestDispenser(type, agentCurrentCoordinate)
                return 1 + Coordinate.manhattanDistance(agentCurrentCoordinate, dispenserCoord) / self.mapcRole.getFreeSpeed() + \
                    Coordinate.manhattanDistance(dispenserCoord, currentMap.getClosestFreeGoalZoneForTask(dispenserCoord, blockRelCoords)) / self.mapcRole.getSpeed(1)
            
            # Else have to search a role zone too
            else:
                roleZoneCoord = currentMap.getClosestRoleZone(agentCurrentCoordinate)
                dispenserCoord = currentMap.getClosestDispenser(type, roleZoneCoord)
                return 2 + Coordinate.manhattanDistance(agentCurrentCoordinate, roleZoneCoord) / self.mapcRole.getFreeSpeed() + \
                    Coordinate.manhattanDistance(roleZoneCoord, dispenserCoord) / self.mapcRole.getFreeSpeed() + \
                    Coordinate.manhattanDistance(dispenserCoord, currentMap.getClosestFreeGoalZoneForTask(dispenserCoord, blockRelCoords)) / self.mapcRole.getSpeed(1)

    def explain(self) -> str:
        """
        Returns the current intention explanation string.
        """

        explanation = ""
        for task in self.simDataServer.getTasks():
            explanation = explanation + task.name + "," + str(task.deadline) + " "

        explanation = explanation + "role " + str(self.intentionHandler.intentionRole) + " "

        if self.intentionHandler.getCurrentIntention():
            return explanation + self.intentionHandler.getCurrentIntention().explain()
        else:
            return explanation + "no intention"
    
    def removeNotConnectedEntities(self, removedAttachedEntity: AttachedEntity) -> None:
        """
        Removes the given `AttachedEntity` and removes the ones
        that are attached to the removed one.
        """

        for furtherAttachedEntity in removedAttachedEntity.attachedEntities:
            self.removeNotConnectedEntities(furtherAttachedEntity)
        
        if removedAttachedEntity in self.attachedEntities:
            self.attachedEntities.remove(removedAttachedEntity)
    
    def connectAttachedEntities(self, fromRelCoord: Coordinate, attachedEntity: AttachedEntity) -> None:
        """
        Adds an `AttachedEntity` to an another `AttachedEntity`, selected
        by the given `Coordinate`
        """

        fromAttachedEntity = next(filter(lambda e: e.relCoord == fromRelCoord, self.attachedEntities))
        fromAttachedEntity.addAttachEntity(attachedEntity)