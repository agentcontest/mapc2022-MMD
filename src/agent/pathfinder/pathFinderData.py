from data.coreData import Coordinate
from data.map import DynamicMap

class PathFinderData():
    """
    Wrapper class storing data used at
    pathfinding.
    """

    map: DynamicMap
    start: Coordinate
    agentSpeed: int
    clearEnergyCost: int
    agentEnergy: int
    agentMaxEnergy: int
    clearChance: float
    clearConstantCost: float
    maxIteration: int
    agentVision: int
    attachedCoordinates: list[Coordinate]

    def __init__(self, map: DynamicMap, start: Coordinate, agentSpeed: int, clearEnergyCost: int,
        agentEnergy: int, agentMaxEnergy: int, clearChance: float, clearConstantCost: float, maxIteration: int,
        agentVision: int, attachedCoordinates: list[Coordinate]) -> None:

        self.map = map
        self.start = start
        self.agentSpeed = agentSpeed
        self.clearEnergyCost = clearEnergyCost
        self.agentEnergy = agentEnergy
        self.agentMaxEnergy = agentMaxEnergy
        self.clearChance = clearChance
        self.clearConstantCost = clearConstantCost
        self.maxIteration = maxIteration
        self.agentVision = agentVision
        self.attachedCoordinates = attachedCoordinates