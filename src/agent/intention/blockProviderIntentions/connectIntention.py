from data.coreData import Coordinate, AgentActionEnum, MapValueEnum

from data.intention import Observation
from agent.intention.agentIntention import AgentIntention
from agent.intention.commonIntentions import TravelIntention, SkipIntention

from agent.action import AgentAction, DetachAction, ConnectAction, RotateAction, ClearAction

class ConnectIntention(AgentIntention):
    """
    Intention to hand over a `Block` to an another
    `Agent`. It either connects the `Block` to the given
    destination or just drops the `Block` by detaching it.\n
    Finishes when the `Block` is handed over and it has been
    detached.
    """
    
    travelIntention: TravelIntention | None
    skipIntention: SkipIntention
    toAgentId: str
    toAgentCurrentCoord: Coordinate | None
    blockRelCoord: Coordinate
    blockGoalCoord: Coordinate | None
    attachedRelCoord: Coordinate | None
    connected: bool

    def __init__(self, toAgentId: str, blockRelCoord: Coordinate) -> None:
        self.travelIntention = None
        self.skipIntention = SkipIntention(True)

        self.toAgentId = toAgentId
        self.toAgentCurrentCoord = None

        self.blockRelCoord = blockRelCoord
        self.blockGoalCoord = None
        self.attachedRelCoord = None

        self.connected = False

    async def planNextAction(self, observation: Observation) -> AgentAction:        
        # Get the coordinator Agent's Coordinate
        toAgentCurrentCoord = observation.map.getAgentCoordinate(self.toAgentId)

        # If just initialized or coordinat Agent's Coordinated changed or the current
        # travel intention is occoupied
        if self.travelIntention is None or self.toAgentCurrentCoord != toAgentCurrentCoord or \
            observation.map.getMapValueEnum(self.travelIntention.coordinate) in [MapValueEnum.AGENT, MapValueEnum.BLOCK]:
            
            # Search for an another goal, from where the block hand over can be completed
            self.initializeTravelIntention(observation, toAgentCurrentCoord)
        
        # If not found a valid target hand over Coordinate, then just skip
        if self.travelIntention is None:
            return await self.skipIntention.planNextAction(observation)

        # If found a valid position and the Agent is there
        if self.travelIntention.checkFinished(observation):
            attachedBlockRelCoord = observation.agentData.attachedEntities[0].relCoord
            currentBlockCoord = observation.agentCurrentCoordinate.getShiftedCoordinate(attachedBlockRelCoord)
            self.blockGoalCoord = self.toAgentCurrentCoord.getShiftedCoordinate(self.blockRelCoord)

            # If the Block is not in the right position then rotate it
            if currentBlockCoord != self.blockGoalCoord:
                return await self.rotateAttachedBlockToGoal(observation, attachedBlockRelCoord)
            
            # Hand over the Block
            else:
                return self.handOverAttachedBlock(observation, attachedBlockRelCoord, currentBlockCoord)

        # Else travel to the target position
        else:
            return await self.travelIntention.planNextAction(observation)

    def checkFinished(self, observation: Observation) -> bool:
        return observation.agentData.lastAction == AgentActionEnum.DETACH and observation.agentData.lastActionSucceeded
    
    def isReadyForBlockHandover(self, observation: Observation) -> bool:
        """
        Returns if it is ready for the block hand over:
        the attached block is at the given `Coordinate`.
        """

        return self.blockGoalCoord is not None \
            and any(observation.agentData.attachedEntities) \
                and self.blockGoalCoord == observation.agentCurrentCoordinate.getShiftedCoordinate(observation.agentData.attachedEntities[0].relCoord)
    
    def updateCoordinatesByOffset(self, offsetCoordinate: Coordinate) -> None:
        self.skipIntention.updateCoordinatesByOffset(offsetCoordinate)

        if self.toAgentCurrentCoord is not None:
            self.toAgentCurrentCoord = self.toAgentCurrentCoord.getShiftedCoordinate(offsetCoordinate)
        
        if self.travelIntention is not None:
            self.travelIntention.updateCoordinatesByOffset(offsetCoordinate)
    
    def normalizeCoordinates(self) -> None:
        self.skipIntention.normalizeCoordinates()

        if self.toAgentCurrentCoord is not None:
            self.toAgentCurrentCoord.normalize()
        
        if self.travelIntention is not None:
            self.travelIntention.normalizeCoordinates()

    def explain(self) -> str:
        return "connecIntention"
    
    def initializeTravelIntention(self, observation: Observation, toAgentCurrentCoord: Coordinate) -> None:
        """
        Sets the travel intention target to a `Coordinate` from where the `Block` can be handed over to
        its destination.\n
        The target must be in one of the `Block` destinations neghbors.
        """

        self.toAgentCurrentCoord = toAgentCurrentCoord
        blockGoalCoord = self.toAgentCurrentCoord.getShiftedCoordinate(self.blockRelCoord)
        travelIntentionGoal = None

        # If the Agent is already in a valid position then no need to search further
        if observation.agentCurrentCoordinate in blockGoalCoord.neighbors():
            travelIntentionGoal = observation.agentCurrentCoordinate
        
        # Else search for a valid position
        else:
            # Get all the Block destinations neighbors which are not occupied
            # and its surroundings are free so the Agent can rotate the Block
            possibleTravelIntentionGoals = list(filter(lambda c: (c == observation.agentCurrentCoordinate
                    or observation.map.getMapValueEnum(c) not in [MapValueEnum.AGENT, MapValueEnum.BLOCK, MapValueEnum.MARKER])
                and any(observation.map.getMapValueEnum(n) not in [MapValueEnum.AGENT, MapValueEnum.BLOCK, MapValueEnum.MARKER] for n in c.neighbors()
                    if n != blockGoalCoord and Coordinate.getDirection(blockGoalCoord, c) != Coordinate.getDirection(c, n)),
                blockGoalCoord.neighbors()))
                    
            # If found any then the choose the closest
            if any(possibleTravelIntentionGoals):
                travelIntentionGoal = min(possibleTravelIntentionGoals, key = lambda c: Coordinate.distance(observation.agentCurrentCoordinate, c))

        if travelIntentionGoal is not None:
            self.travelIntention = TravelIntention(travelIntentionGoal)
        else:
            self.travelIntention = None
    
    async def rotateAttachedBlockToGoal(self, observation: Observation, attachedBlockRelCoord: Coordinate) -> AgentAction:
        """
        Returns the required `AgentAction` to get the attached `Block` to the given position,
        by rotating and clearing obstacles.
        """

        faceDirection = Coordinate.getDirection(attachedBlockRelCoord, Coordinate.origo())
        blockGoalDirection = Coordinate.getDirection(observation.agentCurrentCoordinate, self.blockGoalCoord)

        # If double rotation is needed
        if faceDirection.isSameDirection(blockGoalDirection):
            leftDirection, rightDirection = faceDirection.getAdjacentDirections()
            rotateGoalCoords = [observation.agentCurrentCoordinate.getMovedCoord([leftDirection]),
                observation.agentCurrentCoordinate.getMovedCoord([rightDirection])]

            # Need to decide which direction to rotate, try the one which requires to clear action
            freeCoord = next(filter(lambda c: observation.map.getMapValueEnum(c) in [MapValueEnum.EMPTY, MapValueEnum.DISPENSER], rotateGoalCoords), None)
            if freeCoord is not None:
                return RotateAction(attachedBlockRelCoord.getRotateDirection(Coordinate.getDirection(observation.agentCurrentCoordinate, freeCoord).opposite()))

            # If both ways need clearing then chose one which can be cleared
            blockedCoord = next(filter(lambda c: observation.map.getMapValueEnum(c) in [MapValueEnum.OBSTACLE, MapValueEnum.BLOCK] and \
                c not in observation.agentData.attachedEntities, rotateGoalCoords), None)
            
            # If it is clearable, then clear it
            if blockedCoord is not None:
                return ClearAction(Coordinate.getRelativeCoordinate(observation.agentCurrentCoordinate, blockedCoord))
            
            # If an another Agent is blocking, then just skip (TODO: maybe attach if it is enemy Agent?)
            else:
                return await self.skipIntention.planNextAction(observation)

        # If a simple rotation is enough
        else:
            blockGoalCoordValue = observation.map.getMapValueEnum(self.blockGoalCoord)
            
            # If target Coordinate is occupied then clear it
            if blockGoalCoordValue in [MapValueEnum.OBSTACLE, MapValueEnum.BLOCK] and self.blockGoalCoord not in observation.agentData.attachedEntities:
                return ClearAction(Coordinate.getRelativeCoordinate(observation.agentCurrentCoordinate, self.blockGoalCoord))
            
            # If an another Agent then skip (TODO: maybe attach if it is enemy Agent?)
            elif blockGoalCoordValue == MapValueEnum.AGENT:
                return await self.skipIntention.planNextAction(observation)
            
            # If free then just rotate
            else:
                return RotateAction(attachedBlockRelCoord.getRotateDirection(blockGoalDirection.opposite()))
    
    def handOverAttachedBlock(self, observation: Observation, attachedBlockRelCoord: Coordinate, currentBlockCoord: Coordinate) -> AgentAction:
        """
        Returns the `AgentAction` to hand over the `Block`.
        """

        # If connection is not required then just drop the Block
        if currentBlockCoord in self.toAgentCurrentCoord.neighbors():
            return DetachAction(Coordinate.getDirection(Coordinate.origo(), attachedBlockRelCoord))

        # Set connected flag if not set
        if not self.connected:
            self.connected = observation.agentData.lastAction == AgentActionEnum.CONNECT and observation.agentData.lastActionSucceeded
                
        # If connection is required and not connected then connect the Blocks
        if not self.connected:
            self.attachedRelCoord = attachedBlockRelCoord
            return ConnectAction(self.toAgentId, attachedBlockRelCoord)
        # If connected then just disconnect by detaching the Block
        else:
            return DetachAction(Coordinate.getDirection(Coordinate.origo(), self.attachedRelCoord))
