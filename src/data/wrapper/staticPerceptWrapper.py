from data.coreData import MapcRole

class StaticPerceptWrapper:
    """
    Wrapper for the simulation static percept.
    """

    teamSize: int
    steps: int
    roles: dict[str, MapcRole]

    def __init__(self, perception : dict) -> None:
        self.teamSize = perception["teamSize"]
        self.steps = perception["steps"]
        self.roles = dict([(role["name"],
            MapcRole(role["name"], role["vision"], role["clear"]["chance"], role["clear"]["maxDistance"], role["actions"], role["speed"])) for role in perception["roles"]])