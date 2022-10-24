from data.coreData.enums import RegulationType

class NormRegulation:
    """
    Represents a role or block holding regulaton
    """

    regType: RegulationType # Type of the regulation
    regParam: str           # The role name or unused if block regulation
    regQuantity: int        # Quantity of the regulation (max block or role count)

    def __init__(self, regType: RegulationType, regParam: str, regQuantity: int) -> None:
        self.regType = regType
        self.regParam = regParam
        self.regQuantity = regQuantity