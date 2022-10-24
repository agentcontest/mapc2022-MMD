from typing import Tuple
from random import choice

from data.coreData import Task, AgentIntentionRole, Coordinate, NormRegulation, RegulationType, MapcRole
from data.map import DynamicMap
from data.server import IntentionDataServer, SimulationDataServer, MapServer

from agent.intention import CoordinationIntention, BlockProvidingIntention, SingleBlockProvidingIntention, EscapeIntention, ResetIntention
from agent.agent.agent import Agent

class IntentionGenerator():
    """
    Responsible for generating and filtering global options
    (`MainAgentIntention`) for `Agents`, mainly `Task` and `Norm` options.\n
    Manages also `Agent` identifications.
    """

    simDataServer: SimulationDataServer
    mapServer: MapServer
    intentionDataServer: IntentionDataServer
    options: dict[int, list[Task]]
    taskTeams: dict[str, list[str]]

    def __init__(self, simDataServer: SimulationDataServer, mapServer: MapServer, intentionDataServer: IntentionDataServer) -> None:
        self.simDataServer = simDataServer
        self.mapServer = mapServer
        self.intentionDataServer = intentionDataServer

        self.options = None
        self.taskTeams = dict()

    def generateOptions(self, maps: list[DynamicMap], agents: list[Agent], tasks: list[Task], needReset: bool) -> None:
        """
        Generates Task options for `Agents` and makes them generate their own
        local options.\n
        If reconnected, then generates also reset tasks too.
        """

        if needReset:
            self.generateResetTasksForAgents(agents)

        self.generateTaskOptions(maps, tasks, self.simDataServer.getMaxBlockRegulation())
        self.generateAgentOptions(agents)
    
    def generateResetTasksForAgents(self, agents: list[Agent]) -> None:
        """
        Inserts every `Agent` a `ResetIntention` if they have any attached entity.
        The intention will make them detached every attached entity.
        """

        for agent in agents:
            if any([Coordinate.manhattanDistance(Coordinate.origo(), c) == 1 for c in agent.observation.agentData.perceptAttachedRelCoords]):
                agent.insertIntention(ResetIntention())

    def generateTaskOptions(self, maps: list[DynamicMap], tasks: list[Task], taskMaxBlockCount: int | None) -> None:
        """
        Generates global `Task` options for the given `DynamicMaps`.
        """

        # Only consider Tasks for which there is enough time
        self.options = dict()
        tasksForFilter = list(filter(self.enoughTimeForTask, tasks))

        # Generate Task options for every map
        for map in maps:
            # If there's no goal zone or role zone, then no Task can be started
            if not map.hasAnyGoalZone() or not map.isAnyRoleZone():
                continue 

            # Filter startable tasks and store them
            taskCanditates = []
            for task in tasksForFilter:
                if self.isTaskStartableForMap(map, task, taskMaxBlockCount):
                    taskCanditates.append(task)
            
            if any(taskCanditates):
                self.options[map.id] = list(taskCanditates)
    
    def generateAgentOptions(self, agents: list[Agent]) -> None:
        """
        Makes the `Agents` generate local options.
        If an `EscapeIntention` was generated and the given
        `Agent` is coordinator then make them abandon its current `Task`.
        """

        for agent in agents:
            agent.generateOptions()

            if agent.hasGivenTypeOfIntention(EscapeIntention) and agent.hasGivenTypeOfIntention(CoordinationIntention):
                self.mapServer.getMap(agent.id).freeCoordinatesFromTask(agent.id)
                agent.abandonCurrentTask()

    def filterOptions(self, maps: list[DynamicMap], agents: list[Agent]) -> None:
        """
        Filters the generated options and makes the `Agents` do the same locally.
        """

        self.filterRegulations(agents)
        self.filterTasks(maps, agents)
        
        for agent in agents:
            agent.filterOptions()

            if self.mapServer.getMap(agent.id).isAnyRoleZone() and not agent.doesTaskCurrently() and not agent.hasGivenTypeOfIntention(EscapeIntention):
                allowedRoles = self.simDataServer.getAllowedRoles()

                agentCurrentRole = self.simDataServer.getAgentCurrentRole(agent.id)
                if agentCurrentRole in allowedRoles:
                    continue

                agentRoleReservations = self.simDataServer.getReservedRolesForAgent(agent.id)
                if any(agentRoleReservations) and all(rr in allowedRoles for rr in agentRoleReservations):
                    continue

                newRole = self.simDataServer.getInterTaskRole()
                if newRole is not None:
                    self.simDataServer.reserveRoleForAgent(agent.id, newRole, True)

    def filterRegulations(self, agents: list[Agent]) -> None:
        """
        Filters `Norm` regulations, selects the ones that need to be ignored
        and handles the rest of team.
        """

        if not any(self.simDataServer.getNorms(False)) or not any(self.taskTeams):
            return

        self.filterIgnorableRegulations()
        self.filterRegulationsForConsideration(agents)
        self.handleRoleRegulations(agents)

    def filterIgnorableRegulations(self) -> None:
        """
        Searches unhandled `Norms` which can be ignored
        for some reason (default role regulation or 2 block regulation)
        """

        for unhandledNorm in self.simDataServer.getNorms(False):
            if all(nr.regType == RegulationType.BLOCK and nr.regQuantity == 2 for nr in unhandledNorm.regulations):
                self.simDataServer.setNormHandled(unhandledNorm.name)
            elif all(nr.regType == RegulationType.ROLE and nr.regParam == "default" for nr in unhandledNorm.regulations):
                self.simDataServer.setNormHandled(unhandledNorm.name)

    def filterRegulationsForConsideration(self, agents: list[Agent]) -> None:
        """
        Searches unhandled `Norms` and filters them for consideration.\n
        If the `Agents` do not lose much energy for not considering a `Norm`,
        then they will skip it (previous unconsidered `Norms` are considered too)
        """

        # Get current avearge Agent energy
        agentAvgEnergy = self.getAgentsAvgEnergy(agents)
        
        # Check every upcoming unhandled Norm
        for unhandledNorm in self.simDataServer.getNorms(False):
            currentAgentAvgEnergy = agentAvgEnergy

            # Get all the previous unconsidered Norms and add the current one to them
            unconsideredNorms = self.simDataServer.getNorms(True, False)
            unconsideredNorms.append(unhandledNorm)
            
            # Calculate the energy loss from the unconsidered ones
            for unconsideredNorm in unconsideredNorms:
                normDuration = unconsideredNorm.untilStep - max(unconsideredNorm.startStep, self.simDataServer.getSimulationStep())
                currentAgentAvgEnergy -= normDuration * unconsideredNorm.punishment
                
            # Calculate the energy gain from the time period
            earliestNormBegin = max(min(n.startStep for n in unconsideredNorms), self.simDataServer.getSimulationStep())
            latestNormUntil = min(max(n.untilStep for n in unconsideredNorms), self.simDataServer.lastStep())
            currentAgentAvgEnergy += (latestNormUntil - earliestNormBegin) * \
                self.simDataServer.getAgentEnergyRecharge()

            # If the average energy does not reach the treshold than it can be skipped
            if currentAgentAvgEnergy > self.simDataServer.agentMaxEnergy * self.simDataServer.agentEnergyMinPercentageThreshold:
                print("skipped norm: " + unhandledNorm.name)
                self.simDataServer.setNormUnconsidered(unhandledNorm.name)

    def handleRoleRegulations(self, agents: list[Agent]) -> None:
        """
        Handles the unhandled role `Norm` regulations.\n
        If the `Norm` is violated, then makes the `Agents` drop their `Tasks`,
        so they can select an another role.
        """

        # Get unhandled Norms
        for norm in self.simDataServer.getNorms(False):
            # Mark it handled
            self.simDataServer.setNormHandled(norm.name)

            # Handle every role regulation in Norm.
            for regulation in norm.regulations:
                if regulation.regType == RegulationType.ROLE:
                    self.handleRoleRegulation(agents, regulation)
    
    def handleRoleRegulation(self, agents: list[Agent], regulation: NormRegulation) -> None:
        """
        Handles role regulations by making the `Agents` drop their `Tasks`,
        so they select an another role.\n
        Until the `Norm` is violated, the `Agent` team with the most roles
        must drop their task. Firstly, the role reservations count, it that is not
        enought, then the current roles are measured.
        """

        # Get how many roles are need to be dropped
        violationQuantity = self.simDataServer.getRoleRegulationViolationQuantity(regulation)
        needReserved = True

        while violationQuantity > 0:
            # Select team with most roles
            teamIdToDismiss, roleCount = self.getTeamLeaderWithMostRole(regulation.regParam, needReserved)
            
            # Handle if not found any team
            if teamIdToDismiss is None:
                # Switch to current roles for counting
                if needReserved:
                    needReserved = False
                    continue
                # Else no team was found, no need to continue, because the rest of the Agents
                # will automatically search for an another Role and the violation will end
                else:
                    break

            # Abandon the Task
            teamCoordinator = next(filter(lambda a: a.id == teamIdToDismiss, agents))
            self.mapServer.getMap(teamCoordinator.id).freeCoordinatesFromTask(teamCoordinator.id)
            teamCoordinator.abandonCurrentTask()

            violationQuantity -= roleCount

    def getTeamLeaderWithMostRole(self, roleName: str, needReserved: bool) -> Tuple[str | None, int]:
        """
        Returns an `Agent` team which are working on a `Task`
        which has the most given role. Also returns the role count.\n
        The `needReserved` params sets if the reservations or the current
        roles are counted.
        """

        maxCoordinatorId = None
        maxRoleCount = 0

        for coordinatorId, agentIdList in self.taskTeams.items():
            roleCount = 0
            for agentId in agentIdList:
                agentRoles = self.simDataServer.getReservedRolesForAgent(agentId) if needReserved else [self.simDataServer.getAgentCurrentRole(agentId)]
                roleCount += len([r for r in agentRoles if r.name == roleName])
            
            if roleCount > maxRoleCount:
                maxRoleCount = roleCount
                maxCoordinatorId = coordinatorId

        return (maxCoordinatorId, maxRoleCount)

    def filterTasks(self, maps: list[DynamicMap], agents: list[Agent]) -> None:
        """
        Filters the generated `Task` options that can be started with
        the given `Agents`.
        For every map it starts every possible startable `Task`.
        """

        for map in maps:
            if map.id not in self.options:
                continue

            goalZonesCount = len(map.goalZones)

            # Start as much Task per map as possible
            while True:
                # Get the free Agents which are not doing a Task already
                freeAgents = list(filter(lambda a: a.id in map.agentCoordinates and not a.doesTaskCurrently(), agents))

                # Filter the Tasks which can be started with the free Agents
                self.options[map.id] = list(filter(
                    lambda t: self.isTaskStartableForAgents(map, freeAgents, t),
                    self.options[map.id]))
                
                availableTasks = self.options[map.id]
                
                # Continue to next map if no Task is startable
                if not any(availableTasks):
                    break

                # Start the task which has the most benefit
                busyAgentsCount = len(list(filter(lambda a: a.id in map.agentCoordinates, agents))) - len(freeAgents)
                self.startTask(map, freeAgents, max([task for task in availableTasks], key = lambda task: self.taskValue(task,busyAgentsCount,goalZonesCount)))

    def checkFinishedCurrentIntentionForAgents(self, agents: list[Agent]) -> None:
        """
        Make the `Agents` check if their `MainAgentIntention` has been finished.\n
        Reset their intentionrole to Explorer, and free reserved goal zones.
        """

        for agent in agents:
            if agent.checkFinishedCurrentIntention():
                if agent.isCurrentIntentionRelatedToTask():
                    if agent.getIntentionRole() in [AgentIntentionRole.COORDINATOR, AgentIntentionRole.SINGLEBLOCKPROVIDER]:
                        self.mapServer.getMap(agent.id).freeCoordinatesFromTask(agent.id)
                        del self.taskTeams[agent.id]

                    agent.setIntentionRole(AgentIntentionRole.EXPLORER)

                agent.finishCurrentIntention()

    def checkAgentIdentifications(self, agents: list[Agent]) -> None:
        """
        Checks the `DynamicMaps` for possible `Agent` identifications for
        merging or calculating map dimensions.\n
        If one of them is completed, then handles possible goal zone reservation
        conflicts and sends the `Coordinate` shift values or dimensions to the `Agents`,
        so they can update the `Coordinates` in ther intentions.
        """

        offsets, mapBoundaryReached = self.mapServer.checkAgentIdentifications()

        # Send the Coordinate shift values for the Agents who are involved in the merge
        # (the ones whose map were merged into an another)
        for agentId, offsetCoord in offsets.items():
            agent = next((a for a in agents if a.id == agentId))
            agent.updateCoordinatesByOffset(offsetCoord)

        # Same when map dimensions are calculated, do that also
        # at DynamicMaps
        if mapBoundaryReached:
            Coordinate.maxHeight = self.mapServer.gridHeight
            Coordinate.maxWidth = self.mapServer.gridWidth
            Coordinate.dimensionsCalculated = Coordinate.maxHeight is not None and Coordinate.maxWidth is not None

            for map in self.mapServer.maps.values():
                map.updateCoordinatesByBoundary()
            
            for agent in agents:
                agent.normalizeCoordinates()
        
        # If one of them happened, then need to resolve the conflicts (if there is any)
        if mapBoundaryReached or any(offsets):
            self.handleReservationConflicts(
                [map for map in self.mapServer.maps.values() if mapBoundaryReached
                    or any(set(map.agentCoordinates.keys()).intersection(offsets.keys()))],
                agents)

        # Set map count
        self.simDataServer.setMapCount(self.mapServer.getMapCount())

    def enoughTimeForTask(self, task: Task) -> bool:
        """
        Returns is there is enough time to start the given `Task`.
        """

        return (task.deadline - self.simDataServer.getSimulationStep()) > (3 + 4 * len(task.requirements))

    def taskValue(self, task: Task, busyAgentsCount: int, goalZonesCount: int) -> float:
        """
        Returns a value which represents the benefit of the given `Task`.\n
        Takes consideration the remaining time, the required `Block` count
        and goal zone crowdedness
        """

        requirementsLength = len(task.requirements)
        if requirementsLength == 1:
            value = task.reward
        else:
            value = (task.reward / (requirementsLength + 1))
        
        crowd = busyAgentsCount + 2 * requirementsLength - goalZonesCount * 3 / 4
        value = value * (task.deadline - self.simDataServer.getSimulationStep()) / 100
        
        if crowd < 0:
            return value 
        else:
            return value / (1 + crowd)

    def startTask(self, map: DynamicMap, freeAgents: list[Agent], task: Task) -> None:
        """
        Assigns `Agent(s)` to the given `Task`, based on the required `Block` count.
        """

        if len(task.requirements) == 1:
            self.startSoloTask(map, freeAgents, task)
        else:
            self.startCoopTask(map, freeAgents, task)

    def startSoloTask(self, map: DynamicMap, freeAgents: list[Agent], task: Task) -> None:
        """
        Assigns a single `Agent` to the given `Task` that requires only one `Block`.
        Reserves `MapcRole(s)` for the selected `Agent`
        """

        # Select single block provider Agent
        soloTaskAgent = min([agent for agent in freeAgents],
            key = lambda agent: agent.bidSingleBlock(task.requirements[0].type, [r.coordinate for r in task.requirements]))

        freeAgentIds = set([a.id for a in freeAgents])
        singleBlockProviderRoles = self.simDataServer.getSingleBlockProviderRoles(freeAgentIds)
        
        # If there is a role for block collecting and submission then choose that
        if any(singleBlockProviderRoles):
            self.handleNextRoleReservationForAgent(soloTaskAgent.id, singleBlockProviderRoles)
        
        # Else get block provider and coordinator role
        else:
            blockProviderRoles = self.simDataServer.getBlockProviderRoles(freeAgentIds)
            coordinatorRoles = self.simDataServer.getCoordinatorRoles(freeAgentIds)

            self.handleNextRoleReservationForAgent(soloTaskAgent.id, blockProviderRoles)
            self.simDataServer.reserveRoleForAgent(soloTaskAgent.id, choice(coordinatorRoles), False)
        
        # Get free goal zone, but there's no need to reserve it at the moment, because it will reserve the goal zone which will be the closest at that time
        initialGoalZone = map.getClosestFreeGoalZoneForTask(map.getAgentCoordinate(soloTaskAgent.id), [r.coordinate for r in task.requirements])

        # Set intention role and insert intention
        soloTaskAgent.setIntentionRole(AgentIntentionRole.SINGLEBLOCKPROVIDER)
        soloTaskAgent.insertIntention(SingleBlockProvidingIntention(soloTaskAgent.id, task,initialGoalZone, self.intentionDataServer))

        freeAgents.remove(soloTaskAgent)
        self.taskTeams[soloTaskAgent.id] = [soloTaskAgent.id]

    def startCoopTask(self, map: DynamicMap, freeAgents: list[Agent], task: Task) -> None:
        """
        Assigns an `Agent` team to the given `Task`, by selecting the coordinator
        and block providers. Reserves `MapcRoles` for them and a goal zone too.
        """

        teamAgentIds = []
        freeAgentIds = set([a.id for a in freeAgents])

        # Select coordinator
        coordinator = min([agent for agent in freeAgents], key = lambda agent: agent.bidGoalZone([r.coordinate for r in task.requirements]))

        coordinatorRoles = self.simDataServer.getCoordinatorRoles(freeAgentIds)
        self.handleNextRoleReservationForAgent(coordinator.id, coordinatorRoles)

        freeAgents.remove(coordinator)
        freeAgentIds.remove(coordinator.id)
        teamAgentIds.append(coordinator.id)

        # Get free goal zone
        reservedGoalZone = map.getClosestFreeGoalZoneForTask(map.getAgentCoordinate(coordinator.id), [r.coordinate for r in task.requirements])

        blockProviderIdentions = []

        # Select block providers for each block
        for i in range(0, len(task.requirements)):
            blockProvider = min([agent for agent in freeAgents], key = lambda agent: agent.bidDispenser(task.requirements[i].type, reservedGoalZone))

            currentBlockProvidingRoles = self.simDataServer.getBlockProviderRoles(freeAgentIds)
            self.handleNextRoleReservationForAgent(blockProvider.id, currentBlockProvidingRoles)

            teamAgentIds.append(blockProvider.id)
            freeAgents.remove(blockProvider)
            freeAgentIds.remove(blockProvider.id)

            # Set block provider role and insert intention
            providingIntention = BlockProvidingIntention(blockProvider.id, coordinator.id, task.requirements[i].type,
                self.intentionDataServer)

            blockProvider.insertIntention(providingIntention)
            blockProvider.setIntentionRole(AgentIntentionRole.BLOCKPROVIDER)

            blockProviderIdentions.append(providingIntention)
        
        # Reserve the goal zone
        map.reserveCoordinatesForTask(coordinator.id, reservedGoalZone, [r.coordinate for r in task.requirements])

        # Set coordinator role and insert intetion
        coordinator.setIntentionRole(AgentIntentionRole.COORDINATOR)
        coordinator.insertIntention(CoordinationIntention(coordinator.id, task, reservedGoalZone, blockProviderIdentions,
            self.intentionDataServer))

        self.taskTeams[coordinator.id] = teamAgentIds

    def handleNextRoleReservationForAgent(self, agentId: str, roles: set[MapcRole]) -> None:
        """
        Reserves one of the given `MapcRoles` if the `Agent` does not have
        one of them.
        """

        if self.simDataServer.getAgentCurrentRole(agentId) not in roles:
            self.simDataServer.reserveRoleForAgent(agentId, choice(list(roles)), True)
        else:
            self.simDataServer.clearRoleReservationsForAgent(agentId)

    def isTaskStartableForMap(self, map: DynamicMap, task: Task, maxBlockCount: int | None) -> bool:
        """
        Returns if the given `Task` can be started at the given `DynamicMap`.
        Takes dispensers and max block count `Norm` regulation in consideration.
        """

        if maxBlockCount is not None and len(task.requirements) > maxBlockCount:
            return False

        if any(req.type not in map.dispenserMap.dispensers for req in task.requirements):
            return False

        return True
    
    def isTaskStartableForAgents(self, map: DynamicMap, agents: list[Agent], task: Task) -> bool:
        """
        Returns if the given `Task` can be started by the given `Agents`.
        Takes roles and goal zone reservations in consideration.
        """

        freeAgentIds = set([a.id for a in agents])
        
        # If only one block is required, then a single block provider role
        # is enough
        if len(task.requirements) == 1:
            if not any(agents):
                return False
            
            if not any(self.simDataServer.getSingleBlockProviderRoles(freeAgentIds)) and \
                (not any(self.simDataServer.getBlockProviderRoles(freeAgentIds)) or not any(self.simDataServer.getCoordinatorRoles(freeAgentIds))):
                return False
        
        # Else a coordinator and for every block a block provider role is needed
        else:
            if len(task.requirements) + 1 > len(agents):
                return False
            
            if not any(self.simDataServer.getCoordinatorRoles(freeAgentIds)):
                return False
            
            if not self.simDataServer.isThereGivenAmountOfBlockProviderRole(len(task.requirements), freeAgentIds):
                return False

        # Check reservable goal zones too
        if not map.isAnyFreeGoalZoneForTask([req.coordinate for req in task.requirements]):
            return False

        return True

    def handleReservationConflicts(self, maps: list[DynamicMap], agents: list[Agent]) -> None:
        """
        Handles gole zone reservation conflicts after `DynamicMaps` have been shifted
        or map dimensions are calculated.\n
        Resolves the conflicts by making the selected teams abandon their current `Task`.
        """

        # Resolve conflict for every map
        for map in maps:
            conflicts = map.getConflictingCoordinateReservations()
            
            # Continue until there aren't any unresolved conflict
            while any(conflicts) and all(any(cs) for cs in conflicts.values()):
                
                # Select the one with the most conflict
                mostConflictCount = max([len(c) for c in conflicts.values()])
                mostConflictingAgentIds = [id for id, _ in list(filter(lambda c: len(c[1]) == mostConflictCount, conflicts.items()))]

                # Remove it from the conflicts
                removeableAgentId = max(mostConflictingAgentIds, key = lambda a: Coordinate.distance(map.getAgentCoordinate(a), map.agentCoordReservations[a][0]))

                del conflicts[removeableAgentId]
                for conflictList in conflicts.values():
                    if removeableAgentId in conflictList:
                        conflictList.remove(removeableAgentId)
                
                # Abandon its current Task
                agent : Agent = [a for a in agents if a.id == removeableAgentId][0]
                agent.abandonCurrentTask()
    
    def getAgentsAvgEnergy(self, agents: list[Agent]) -> float:
        """
        Returns the average `Agent` current energy.
        """

        return sum([a.dynamicPerceptWrapper.energy for a in agents]) / len(agents)