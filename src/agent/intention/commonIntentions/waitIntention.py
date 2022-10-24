from data.coreData import Coordinate, MapValueEnum

from data.intention import Observation
from agent.intention.agentIntention import AgentIntention
from agent.intention.commonIntentions.travelIntention import TravelIntention
from agent.intention.commonIntentions.skipIntention import SkipIntention

from agent.action import AgentAction, ClearAction

class WaitIntention(AgentIntention):
    """
    Intention used for travelling to a given
    `Coordinate` and waiting there forever, it has no goal.
    If the destination is occupied then it will wait at its
    current position.\n
    While at waiting, it will shoot enemy `Agents`.
    """

    travelIntention: TravelIntention
    skipIntention: SkipIntention

    def __init__(self, coordinate: Coordinate, allowRotateDuringWait: bool) -> None:
        self.travelIntention = TravelIntention(coordinate)
        self.skipIntention = SkipIntention(allowRotateDuringWait)
    
    async def planNextAction(self, observation : Observation) -> AgentAction:
        # Check if it reached its destination or if it is occupied by an another agent or marker
        if self.travelIntention.checkFinished(observation) or \
            observation.map.getMapValueEnum(self.travelIntention.coordinate) in [MapValueEnum.AGENT, MapValueEnum.MARKER]:

            # If the Agent has high energy and there is enemy Agent is range, then shoot it.
            if observation.agentMapcRole.clearMaxDistance > 1:
                enemyCoord = self.getClearableEnemy(observation)
                if enemyCoord is not None:
                    lowEnergy = observation.simDataServer.getClearEnergyCost() * 2.4 > observation.agentData.energy
                    if not lowEnergy:
                        return ClearAction(Coordinate.getRelativeCoordinate(observation.agentCurrentCoordinate, enemyCoord))

            # If reached destination or it is occupied and can not shoot enemy Agents then just skip.
            return await self.skipIntention.planNextAction(observation)
        # If not reached its destination then travel to it
        else:
            return await self.travelIntention.planNextAction(observation)

    def checkFinished(self, _: Observation) -> bool:
        return False
    
    def updateCoordinatesByOffset(self, offsetCoordinate: Coordinate) -> None:
        self.travelIntention.updateCoordinatesByOffset(offsetCoordinate)
        self.skipIntention.updateCoordinatesByOffset(offsetCoordinate)

    def normalizeCoordinates(self) -> None:
        self.travelIntention.normalizeCoordinates()
        self.skipIntention.normalizeCoordinates()

    def getClearableEnemy(self, observation: Observation) -> Coordinate | None:
        """
        Returns an enemy `Agent` within shooting range if one found.
        """

        clearableCoords = list(
            filter(lambda coord: observation.map.getMapValueEnum(coord) == MapValueEnum.AGENT and  
                observation.map.getMapValue(coord).details != observation.simDataServer.teamName and
                coord not in observation.map.goalZones,
                observation.agentCurrentCoordinate.neighbors(True, observation.agentMapcRole.clearMaxDistance)))
        
        return min([coord for coord in clearableCoords],
            key = lambda coord: Coordinate.manhattanDistance(coord,observation.agentCurrentCoordinate),
            default = None)

    def explain(self) -> str:
        return "waitIntention at " + str(self.travelIntention.coordinate)
