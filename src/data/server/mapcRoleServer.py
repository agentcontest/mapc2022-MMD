import random

from data.coreData import MapcRole, AgentActionEnum, NormRegulation

class MapcRoleServer:
    """
    A repository which contains the current and the future `MapcRoles`
    for `Agents`.\n
    It helps finding the right `MapcRole` for the given `Agent` intention
    considering the complied `MapcRole` `NormRegulations`.
    """

    mapcRoles: list[MapcRole]
    agentRoleReservations: dict[str, list[MapcRole]]
    agentCurrentRoles: dict[str, MapcRole]

    def __init__(self, mapcRoles: list[MapcRole]) -> None:
        self.mapcRoles = mapcRoles
        self.agentRoleReservations = dict()
        self.agentCurrentRoles = dict()

    def registerInitialRoleForAgent(self, agentId: str, role: MapcRole) -> None:
        """
        Registers the initial `MapcRole` for the `Agent`. This is not equivivalent to
        role switching.
        """

        self.agentCurrentRoles[agentId] = role
        self.agentRoleReservations[agentId] = []
    
    def getAgentCurrentRole(self, agentId: str) -> MapcRole:
        """
        Returns the `Agent's` current `MapcRole`, the one that it has at this time.
        """

        return self.agentCurrentRoles[agentId]

    def getReservedRolesForAgent(self, agentId: str) -> list[MapcRole]:
        """
        Returns the `Agent's` reserved `MapcRoles`, the current one is not included.
        """

        return self.agentRoleReservations[agentId]
    
    def getRoleRegulationViolationQuantity(self, roleRegulation: NormRegulation) -> int:
        """
        Returns how much `Agent` violates the given `MapcRole` `NormRegulation`
        by their current or reserved `MapcRoles`.
        """

        return self.getAgentCountForRole(self.getRoleByName(roleRegulation.regParam)) - \
            roleRegulation.regQuantity

    def clearRoleReservationsForAgent(self, agentId: str) -> None:
        """
        Deletes the `MapcRole` reservations for the given `Agent`.
        """

        self.agentRoleReservations[agentId] = []

    def reserveRoleForAgent(self, agentId: str, role: MapcRole, removeNextRoles: bool) -> None:
        """
        Reserves the given `MapcRole` for the given `Agent`.
        The `removeNextRoles` param is usable for clearing previous reservations.
        """

        if removeNextRoles:
            self.clearRoleReservationsForAgent(agentId)

        self.agentRoleReservations[agentId].append(role)
    
    def switchRoleForAgent(self, agentId: str, nextRoleName: str) -> None:
        """
        Sets the new `MapcRole` for the `Agent`. The new one if from the reservation list,
        if it is not empty. If it is, then the given one will be next.\n
        The `nextRoleName` param is used when no reservations were made (for example when an `Agent` is explorer).
        """

        newRole = self.agentRoleReservations[agentId].pop() if agentId in self.agentRoleReservations and any(self.agentRoleReservations[agentId]) else \
            self.getRoleByName(nextRoleName)
        self.agentCurrentRoles[agentId] = newRole

    def isThereGivenAmountOfBlockProviderRole(self, roleRegulations: list[NormRegulation], quantity: int, agentIdIgnoreSet: set[str]) -> bool:
        """
        Returns if there is enough block provider role
        considering the complied `MapcRole` `NormRegulations`.
        """

        availableRoleCount = 0
        for role in [r for r in self.mapcRoles if self.isBlockProviderRole(r)]:
            maxRegulation = max(
                filter(lambda rr: rr.regParam == role.name, roleRegulations),
                key = lambda rr: rr.regQuantity,
                default = None)
            
            # If there is no regulation for a block providing role, then as much as possible
            # reservations can be made
            if maxRegulation is None:
                return True

            # Else get how much can be reserved considering the regulatinons
            availableRoleCount += min(maxRegulation.regQuantity - self.getAgentCountForRole(role, agentIdIgnoreSet), 0)

            # If reached the given quantity, then no need to look further
            if availableRoleCount >= quantity:
                return True
        
        return False

    def getCoordinatorRoles(self, roleRegulations: list[NormRegulation], agentIdIgnoreSet: set[str] | None = None) -> set[MapcRole]:
        """
        Returns the coordinator `MapcRoles`:
        those that can attach and connect `Blocks`, and also submit a `Task`.
        """

        return set(filter(
            lambda r: self.isCoordinatorRole(r),
            self.getAllowedRoles(roleRegulations, agentIdIgnoreSet)))
    
    def isCoordinatorRole(self, role: MapcRole) -> bool:
        """
        Returns if the the given `MapcRole` is capable of coordinating:
        it can attach and connect `Blocks`, and also submit a `Task`.
        """

        return AgentActionEnum.SUBMIT in role.actions and AgentActionEnum.ATTACH in role.actions and AgentActionEnum.CONNECT in role.actions

    def getBlockProviderRoles(self, roleRegulations: list[NormRegulation], agentIdIgnoreSet: set[str] | None = None) -> set[MapcRole]:
        """
        Returns the block provider `MapcRoles`:
        those that can attach, request and connect `Blocks`.
        """

        return set(filter(
            lambda r: self.isBlockProviderRole(r),
            self.getAllowedRoles(roleRegulations, agentIdIgnoreSet)))

    def isBlockProviderRole(self, role: MapcRole) -> bool:
        """
        Returns if the the given `MapcRole` is capable of block providing:
        it can attach, request and connect a `Block`.
        """

        return AgentActionEnum.REQUEST in role.actions and AgentActionEnum.ATTACH in role.actions and AgentActionEnum.CONNECT in role.actions and \
            role.getSpeed(1) > 0

    def getSingleBlockProviderRoles(self, roleRegulations: list[NormRegulation], agentIdIgnoreSet: set[str] | None = None) -> set[MapcRole]:
        """
        Returns the single block provider `MapcRoles`:
        those that can attach, request `Blocks`, and also submit a `Task`.
        """

        return set(filter(
            lambda r: self.isSingleBlockProviderRole(r),
            self.getAllowedRoles(roleRegulations, agentIdIgnoreSet)))
    
    def isSingleBlockProviderRole(self, role: MapcRole) -> bool:
        """
        Returns if the the given `MapcRole` is capable of single block providing:
        it can attach and request `Block`, and also submit a `Task`.
        """

        return AgentActionEnum.REQUEST in role.actions and AgentActionEnum.ATTACH in role.actions and AgentActionEnum.SUBMIT in role.actions and \
            role.getSpeed(1) > 0

    def getAllowedRoles(self, roleRegulations: list[NormRegulation], agentIdIgnoreSet: set[str] | None = None) -> list[MapcRole]:
        """
        Returns the `MapcRoles` which are allowed for reservations
        (considering the complied `MapcRole` `NormRegulations`).
        """

        return list(filter(
            lambda r: all(rr.regParam != r.name or self.getAgentCountForRole(r, agentIdIgnoreSet) < rr.regQuantity for rr in roleRegulations),
            self.mapcRoles))

    def getInterTaskRole(self, roleRegulations: list[NormRegulation]) -> MapcRole | None:
        """
        Returns a `MapcRole` which is either usable for single block providing, block providing or coordinating
        and also available. If not, choses a random allowed `MapcRole`.
        """

        # Try to search a useful role
        possibleRoles = list(filter(
            lambda r: (self.isBlockProviderRole(r) or self.isSingleBlockProviderRole(r) or self.isCoordinatorRole(r)) and \
                r.getSpeed(1) > 0,
            self.getAllowedRoles(roleRegulations)))
        
        # If not found one then try to search for anything else
        if not any(possibleRoles):
            possibleRoles = list(filter(
                lambda r: r.getSpeed(1) > 0,
                self.getAllowedRoles(roleRegulations)))

        if any(possibleRoles):
            return random.choice(possibleRoles)
        else:
            return None

    def getAgentCountForRole(self, role: MapcRole, agentIdIgnoreSet: set[str] | None = None) -> int:
        """
        Returns the number of `Agents` that currently have got or reserved the given `MapcRole`.\n
        If the `agentIdIgnoreSet` param is given, then those `Agents` are not included in the count.
        """

        return len([r for agentId, rs in self.agentRoleReservations.items() for r in rs if r == role
                and (agentIdIgnoreSet is None or agentId not in agentIdIgnoreSet)]) + \
            len([r for agentId, r in self.agentCurrentRoles.items() if r == role and \
                (agentIdIgnoreSet is None or agentId not in agentIdIgnoreSet)])

    def getRoleByName(self, roleName: str) -> MapcRole:
        """
        Returns a `MapcRole` by its name.
        """

        return next(filter(lambda r: r.name == roleName, self.mapcRoles)) 

    def getDefaultRole(self) -> MapcRole:
        """
        Returns the default `MapcRole`.
        """

        return self.getRoleByName("default")