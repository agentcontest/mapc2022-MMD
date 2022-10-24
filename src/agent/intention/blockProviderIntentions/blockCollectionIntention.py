from random import random

from data.coreData import Coordinate, MapValueEnum, AgentActionEnum, AgentIntentionRole
from data.intention import Observation
from data.server import IntentionDataServer

from agent.intention.agentIntention import AgentIntention
from agent.intention.commonIntentions import AgitatedTravelIntention, SkipIntention

from agent.action import AgentAction, RequestAction, AttachAction, DetachAction, ClearAction

class BlockCollectionIntention(AgentIntention):
    """
    Intention to collect the given `Block` type,
    from a `Dispenser` or from the abandoned `Blocks`
    from the map.\n
    Finishes when the given `Block` type is attached.
    """

    agitatedTravelIntention: AgitatedTravelIntention | None
    skipIntention: SkipIntention
    closestDispenserCoord: Coordinate | None
    blockType: str
    intentionDataServer: IntentionDataServer

    def __init__(self, blockType: str, intentionDataServer: IntentionDataServer) -> None:
        self.agitatedTravelIntention = None
        self.skipIntention = SkipIntention(True)

        self.closestDispenserCoord = None
        self.blockType = blockType
        self.intentionDataServer = intentionDataServer

    async def planNextAction(self, observation: Observation) -> AgentAction:
        # Check if Agents got stuck together by attaching a Block
        if self.closestDispenserCoord is not None and self.hasAttachedMultipleEntities(observation):
            return await self.handleMultipleAttachedStuck(observation)

        # Get closest dispenser Coordinate
        closestDispenserCoord = observation.map.getClosestDispenser(
            self.blockType, observation.agentCurrentCoordinate)

        # Get closest abandoned Block Coordinate
        freeBlockCoord = self.getFreeBlockCoord(observation)
        
        # If abandoned Block is closer than Dispenser then target that
        if freeBlockCoord is not None and \
            (Coordinate.manhattanDistance(observation.agentCurrentCoordinate, freeBlockCoord) < Coordinate.manhattanDistance(observation.agentCurrentCoordinate, closestDispenserCoord)):
            
            closestDispenserCoord = freeBlockCoord.copy()

        # Travel to the Dispenser / Block
        if (closestDispenserCoord not in observation.agentCurrentCoordinate.neighbors()):
            return await self.travelToClosestDispenser(observation, closestDispenserCoord)

        self.closestDispenserCoord = closestDispenserCoord
        
        # If the target area is occupied by an another Block, then clear it
        target = observation.map.getMapValue(self.closestDispenserCoord)
        if target.value == MapValueEnum.BLOCK and target.details != self.blockType:
            return ClearAction(Coordinate.getRelativeCoordinate(observation.agentCurrentCoordinate, self.closestDispenserCoord))

        # Else try to attach the Block
        if target.value == MapValueEnum.BLOCK and target.details == self.blockType:
            return await self.attemptAttachBlock(observation)
        # If the dispenser is empty, then request a Block from it
        else:
            return RequestAction(Coordinate.getDirection(observation.agentCurrentCoordinate, self.closestDispenserCoord))

    def checkFinished(self, observation: Observation) -> bool:
        return observation.agentData.lastAction == AgentActionEnum.ATTACH and observation.agentData.lastActionSucceeded and \
            not self.hasAttachedMultipleEntities(observation)
    
    def updateCoordinatesByOffset(self, offsetCoordinate: Coordinate) -> None:
        if self.closestDispenserCoord is not None:
            self.closestDispenserCoord.updateByOffsetCoordinate(offsetCoordinate)
        
        if self.agitatedTravelIntention is not None:
            self.agitatedTravelIntention.updateCoordinatesByOffset(offsetCoordinate)
        
        self.skipIntention.updateCoordinatesByOffset(offsetCoordinate)
    
    def normalizeCoordinates(self) -> None:
        if self.closestDispenserCoord is not None:
            self.closestDispenserCoord.normalize()
        
        if self.agitatedTravelIntention is not None:
            self.agitatedTravelIntention.normalizeCoordinates()
        
        self.skipIntention.normalizeCoordinates()

    def explain(self) -> str:
        explanation = "blockcollecting " + self.blockType + " from dispenser " + str(self.closestDispenserCoord)

        if self.agitatedTravelIntention is not None:
            explanation += self.agitatedTravelIntention.explain()

        return explanation
    
    def hasAttachedMultipleEntities(self, observation: Observation) -> bool:
        """
        Returns if multiple entities are attached, for example when multiple `Agents`
        are attaching the same `Block`, they will get stuck together.
        """
        
        # If the Agent isn't next to the Dispenser then skip
        if Coordinate.manhattanDistance(observation.agentCurrentCoordinate, self.closestDispenserCoord) != 1:
            return False

        # Else check for oher Agents
        dispenserRelCoord = Coordinate.getRelativeCoordinate(observation.agentCurrentCoordinate, self.closestDispenserCoord)
        return any(filter(lambda c: observation.map.getMapValueEnum(observation.agentCurrentCoordinate.getShiftedCoordinate(c)) == MapValueEnum.AGENT,
            set(dispenserRelCoord.neighbors(False)).intersection(observation.agentData.perceptAttachedRelCoords)))
    
    async def handleMultipleAttachedStuck(self, observation: Observation) -> AgentAction:
        """
        Returns the `AgentAction` required to get unstuck.
        There's 50% chance to detach the attached `Block`, at least
        one of the `Agents` will detach sooner or later, making them unstuck.
        """

        if random() < 0.5:
            return DetachAction(Coordinate.getDirection(observation.agentCurrentCoordinate, self.closestDispenserCoord))
        else:
            return await self.skipIntention.planNextAction(observation)
    
    async def travelToClosestDispenser(self, observation: Observation, closestDispenserCoord: Coordinate) -> AgentAction:
        if self.agitatedTravelIntention is None or self.closestDispenserCoord is None or self.closestDispenserCoord != closestDispenserCoord:
            self.closestDispenserCoord = closestDispenserCoord
            self.agitatedTravelIntention = AgitatedTravelIntention(self.closestDispenserCoord.neighbors(), True)

        return await self.agitatedTravelIntention.planNextAction(observation)
    
    async def attemptAttachBlock(self, observation: Observation) -> AgentAction:
        otherAgentIdsAtDispenser = [id for id, c in observation.map.agentCoordinates.items()
            if c in self.closestDispenserCoord.neighbors() and self.intentionDataServer.getAgentIntentionRole(id) in [AgentIntentionRole.BLOCKPROVIDER, AgentIntentionRole.SINGLEBLOCKPROVIDER]]
            
        if any([a for a in otherAgentIdsAtDispenser if any(self.intentionDataServer.getAgentOservation(a).agentData.attachedEntities)]) or \
            len(otherAgentIdsAtDispenser) > 0 and min(otherAgentIdsAtDispenser) != observation.agentData.id:
                
            return await self.skipIntention.planNextAction(observation)

        return AttachAction(Coordinate.getDirection(observation.agentCurrentCoordinate, self.closestDispenserCoord), MapValueEnum.BLOCK, self.blockType)

    def getFreeBlockCoord(self, observation: Observation) -> Coordinate | None:
        """
        Returns the `Coordinate` of an abandoned `Block` (which matches the requried type)
        if one is found.
        """

        blockCoords = []
        for possibleBlockCoord in observation.agentCurrentCoordinate.neighbors(searchRange = observation.agentMapcRole.vision):
            # If it's from a dispenser then skip, it's not abandoned
            if observation.map.getMapValueEnum(possibleBlockCoord, needDispenser = True) == MapValueEnum.DISPENSER:
                continue

            coordValue = observation.map.getMapValue(possibleBlockCoord)

           # If type does not match or it is attached then skip
            if coordValue.value != MapValueEnum.BLOCK or coordValue.details != self.blockType or \
                Coordinate.getRelativeCoordinate(observation.agentCurrentCoordinate, possibleBlockCoord) in observation.agentData.perceptAttachedRelCoords:
                continue

            # If probably attached (to an another block, or agent), or there's a marker around it then skip too
            if any(observation.map.getMapValueEnum(n) in [MapValueEnum.BLOCK, MapValueEnum.AGENT, MapValueEnum.MARKER] for n in possibleBlockCoord.neighbors()):
                continue

            blockCoords.append(possibleBlockCoord)
        
        return min(blockCoords, key = lambda coord: Coordinate.manhattanDistance(coord,observation.agentCurrentCoordinate), default = None) 