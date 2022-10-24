from data.coreData import Task, MapcRole, Norm, NormRegulation, RegulationType
from data.wrapper import StaticPerceptWrapper

from data.server.mapcRoleServer import MapcRoleServer

class SimulationDataServer:
    """
    A repository which contains global values for `Agents`
    and also wraps the `MapcRoleServer`.
    """

    teamName: str
    mapcRoleServer: MapcRoleServer | None
    staticPercept: StaticPerceptWrapper | None
    clearConstantCost: float
    agentMaxEnergy: int
    clearEnergyCost: float | None
    energyRecharge: float | None
    simulationStep: int
    mapCount: int | None
    tasks: set[Task]
    norms: dict[str, Norm]

    def __init__(self, teamName: str) -> None:
        self.teamName = teamName
        self.mapcRoleServer = None
        self.staticPercept = None
        self.tasks = set()
        self.norms = dict()

        self.clearConstantCost = 2.5
        self.agentMaxEnergy = 0
        self.clearEnergyCost = None
        self.energyRecharge = None
        self.simulationStep = 0
        self.mapCount = None
    
    @property
    def pathFindingMaxIteration(self) -> int:
        """
        Constant A-Star maximum iteration count.
        """

        return 500
    
    @property
    def markerPurgeInterval(self) -> int:
        """
        Constant simulation step value used for removing old marker values
        from `DynamicMaps`.
        """

        return 10
    
    @property
    def unknownCoordSearchMaxIter(self) -> int:
        """
        Constant maximum iteration count used for searching a new unknown `Coordinate`˛
        for an `Agent` during exploration.
        """
        
        return 60
    
    @property
    def normHandleInterval(self) -> int:
        """
        Constant simulation step interval in which a `Norm` must be handled.
        """
        
        return 20
    
    @property
    def agentEnergyMinPercentageThreshold(self) -> float:
        """
        Constant percentage used at deciding if a `Norm` should be considered or ignored.\n
        The average agent energy percentage should be minimum this value after the norm if ignored.
        """

        return 0.20

    @property
    def maxAgentBlockingThresholdForAssemble(self) -> int:
        """
        Maximum simulation step count at `Block` assemble:
        if an other `Agent` blocks continuously the area
        for the given value, then it will abaddon the `Task`.
        """

        return 10

    def isLastStep(self) -> bool:
        """
        Returns if the current step is the last one.
        """

        return self.staticPercept.steps == self.simulationStep + 1

    def lastStep(self) -> int:
        """
        Returns the simulation's last step | step count
        """

        return self.staticPercept.steps

    def setStaticPercept(self, wrapper: StaticPerceptWrapper) -> None:
        """
        Saves the static percept which is global for every `Agent`.
        """

        self.staticPercept = wrapper
        self.mapcRoleServer = MapcRoleServer(list(self.staticPercept.roles.values()))

    def getStaticPercept(self) -> StaticPerceptWrapper | None:
        """
        Returns the static percept which is global for every `Agent` if it has been set.
        """

        return self.staticPercept

    def setSimulationStep(self, value: int) -> None:
        """
        Sets the current simulation step.
        """

        self.simulationStep = value

    def getSimulationStep(self) -> int:
        """
        Returns the current simulation step.
        """

        return self.simulationStep
    
    def getClearConstantCost(self) -> float:
        """
        Constant value used for the clear cost calculation.
        """

        return self.clearConstantCost

    def setAgentMaxEnegy(self, value: int) -> None:
        """
        Sets the agent maximum energy. It can't be decreased by this method.
        """

        self.agentMaxEnergy = max(self.agentMaxEnergy, value)
    
    def getAgentMaxEnergy(self) -> int:
        """
        Returns the possible maximum energy for the `Agents`
        """

        return self.agentMaxEnergy
    
    def setAgentEnergyRecharge(self, value: float) -> None:
        """
        Sets the `Agent` energy recharge per step value. It can't be decreased.
        """

        self.energyRecharge = max(self.energyRecharge, value) if self.energyRecharge is not None else value
    
    def getAgentEnergyRecharge(self) -> float:
        """
        Returns the `Agent` energy recharge per step value.
        """

        return self.energyRecharge if self.energyRecharge is not None else 1.0

    def setClearEnergyCost(self, value: float) -> None:
        """
        Sets the clear energy cost for the `Agents` (which is global, `MapcRoles` do not affect it).
        This value can't be increased.
        """

        self.clearEnergyCost = min(self.clearEnergyCost, value) if self.clearEnergyCost is not None else value
    
    def getClearEnergyCost(self) -> float:
        """
        Returns the clear energy cost for the `Agents` (which is global, `MapcRoles` do not affect it).
        """

        return self.clearEnergyCost if self.clearEnergyCost is not None else 3.0
    
    def updateTasks(self, tasks: list[Task]) -> None:
        """
        Sets the available `Tasks` which are allowed to be submitted.
        """

        self.tasks = set([t for t in tasks if t.deadline > self.simulationStep])
    
    def getTasks(self) -> list[Task]:
        """
        Returns the `Tasks` which are submittable.
        """

        return list(self.tasks)
    
    def hasTaskExpired(self, task: Task) -> bool:
        """
        Returns if the given `Task` has expired, meaning it can't be submitted.
        """

        return task not in self.tasks
    
    def updateNorms(self, norms: list[Norm]) -> None:
        """
        Updates the `Norms` with new ones and deletes the expired ones
        """

        self.norms.update([(n.name, n) for n in norms if n.name not in self.norms])       
        for name, norm in [(k, v) for k, v in self.norms.items()]:
            if norm.untilStep < self.simulationStep:
                del self.norms[name]
                
    def getNorms(self, needHandled: bool, needConsidered: bool | None = None) -> list[Norm]:
        """
        Returns the upcoming `Norms` which is filterable by handling and considering status.
        """

        return list(filter(
            lambda n: n.startStep <= self.simulationStep + self.normHandleInterval and \
                (needHandled == n.handled) and \
                (needConsidered is None or needConsidered == n.considered),
            self.norms.values()))

    def getNormsRegulations(self, norms: list[Norm], regulationType: RegulationType | None = None) -> list[NormRegulation]:
        """
        Returns the `NormRegulations` belonging to the given `Norms`.
        """

        return list(filter(
            lambda nr: regulationType is None or nr.regType == regulationType,
            [nr for n in norms for nr in n.regulations]))
        
    def getRoleRegulationViolationQuantity(self, roleRegulation: NormRegulation) -> int:
        """
        Returns how much `Agent` violates the given `MapcRole` `NormRegulation`
        by their current or reserved `MapcRoles`.
        """

        return self.mapcRoleServer.getRoleRegulationViolationQuantity(roleRegulation)

    def getActiveRegulations(self, type: RegulationType) -> list[NormRegulation]:
        """
        Returns the upcoming `NormRegulatios`.
        """

        return self.getNormsRegulations(self.getNorms(True, True), type)

    def setNormHandled(self, normName: str) -> None:
        """
        Marks a `Norm` and its `NormRegulations` handled,
        meaning it will be considered.
        """

        self.norms[normName].handled = True
    
    def setNormUnconsidered(self, normName: str) -> None:
        """
        Marks a `Norm` and its `NormRegulations` ignoreable.
        """

        norm = self.norms[normName]
        norm.handled = True
        norm.considered = False

    def getMaxBlockRegulation(self) -> int | None:
        """
        Returns the maximum `Block` regulation count
        from the `Block` considered `NormRegulations` if there is any.
        """

        return min(
            [nr.regQuantity for nr in self.getActiveRegulations(RegulationType.BLOCK)
                if nr.regQuantity != 2],
            default = None)
    
    def setMapCount(self, value: int) -> None:
        """
        Sets the remaining `DynamicMap` count for the simulation. The value is between 1 and `Agent` count.
        """

        self.mapCount = value
    
    def getMapCount(self) -> int | None:
        """
        Returns the remaining `DynamicMap` count for the simulation. The value is between 1 and `Agent` count.
        """

        return self.mapCount
    
    def registerInitialRoleForAgent(self, agentId: str, role: MapcRole) -> None:
        """
        Registers the initial `MapcRole` for the `Agent`. This is not equivivalent to
        role switching.
        """

        self.mapcRoleServer.registerInitialRoleForAgent(agentId, role)
    
    def getAgentCurrentRole(self, agentId: str) -> MapcRole:
        """
        Returns the `Agent's` current `MapcRole`, the one that it has at this time.
        """

        return self.mapcRoleServer.getAgentCurrentRole(agentId)

    def getReservedRolesForAgent(self, agentId: str) -> list[MapcRole]:
        """
        Returns the `Agent's` reserved `MapcRoles`, the current one is not included.
        """

        return self.mapcRoleServer.getReservedRolesForAgent(agentId)
    
    def clearRoleReservationsForAgent(self, agentId: str) -> None:
        """
        Deletes the `MapcRole` reservations for the given `Agent`.
        """

        self.mapcRoleServer.clearRoleReservationsForAgent(agentId)

    def reserveRoleForAgent(self, agentId: str, role: MapcRole, removeNextRoles: bool) -> None:
        """
        Reserves the given `MapcRole` for the given `Agent`.
        The `removeNextRoles` param is usable for clearing previous reservations.
        """

        self.mapcRoleServer.reserveRoleForAgent(agentId, role, removeNextRoles)
    
    def switchRoleForAgent(self, agentId: str, nextRoleName: str) -> None:
        """
        Sets the new `MapcRole` for the `Agent`. The new one if from the reservation list,
        if it is not empty. If it is, then the given one will be next.\n
        The `nextRoleName` param is used when no reservations were made (for example when an `Agent` is explorer).
        """

        self.mapcRoleServer.switchRoleForAgent(agentId, nextRoleName)

    def getCoordinatorRoles(self, agentIdIgnoreSet: set[str] | None = None) -> set[MapcRole]:
        """
        Returns if the the given `MapcRole` is capable of coordinating:
        it can attach and connect `Blocks`, and also submit a `Task`.
        """

        return self.mapcRoleServer.getCoordinatorRoles(self.getActiveRegulations(RegulationType.ROLE), agentIdIgnoreSet)
    
    def isCoordinatorRole(self, role: MapcRole) -> bool:
        """
        Returns the block provider `MapcRoles`:
        those that can attach, request and connect `Blocks`.
        """

        return self.mapcRoleServer.isCoordinatorRole(role)

    def getBlockProviderRoles(self, agentIdIgnoreSet: set[str] | None = None) -> MapcRole | None:
        """
        Returns the block provider `MapcRoles`:
        those that can attach, request and connect `Blocks`.
        """

        return self.mapcRoleServer.getBlockProviderRoles(self.getActiveRegulations(RegulationType.ROLE), agentIdIgnoreSet)
    
    def isBlockProviderRole(self, role: MapcRole) -> bool:
        """
        Returns if the the given `MapcRole` is capable of block providing:
        it can attach, request and connect a `Block`.
        """

        return self.mapcRoleServer.isBlockProviderRole(role)

    def getSingleBlockProviderRoles(self, agentIdIgnoreSet: set[str] | None = None) -> MapcRole | None:
        """
        Returns the single block provider `MapcRoles`:
        those that can attach, request `Blocks`, and also submit a `Task`.
        """

        return self.mapcRoleServer.getSingleBlockProviderRoles(self.getActiveRegulations(RegulationType.ROLE), agentIdIgnoreSet)
    
    def isSingleBlockProviderRole(self, role: MapcRole) -> bool:
        """
        Returns if there is enough block provider role
        considering the complied `MapcRole` `NormRegulations`.
        """

        return self.mapcRoleServer.isSingleBlockProviderRole(role)
    
    def isThereGivenAmountOfBlockProviderRole(self, quantity: int, agentIdIgnoreSet: set[str]) -> bool:
        return self.mapcRoleServer.isThereGivenAmountOfBlockProviderRole(
            self.getActiveRegulations(RegulationType.ROLE), quantity, agentIdIgnoreSet)

    def getAllowedRoles(self, agentIdIgnoreSet: set[str] | None = None) -> list[MapcRole]:
        """
        Returns the `MapcRoles` which are allowed for reservations
        (considering the complied `MapcRole` `NormRegulations`).
        """

        return self.mapcRoleServer.getAllowedRoles(self.getActiveRegulations(RegulationType.ROLE), agentIdIgnoreSet)
    
    def getInterTaskRole(self) -> MapcRole | None:
        """
        Returns a `MapcRole` which is either usable for single block providing, block providing or coordinating
        and also available. If not, choses a random allowed `MapcRole`.
        """

        return self.mapcRoleServer.getInterTaskRole(self.getActiveRegulations(RegulationType.ROLE))