"""Physical and model constants used in the migrated EAF model."""

from dataclasses import dataclass


@dataclass(frozen=True)
class MolecularMass:
    FE: float = 0.055845
    C: float = 0.0120107
    O2: float = 0.032
    CO: float = 0.02801
    CO2: float = 0.04401
    FEO: float = 0.071844
    MNO: float = 0.0709374
    MN: float = 0.054938


@dataclass(frozen=True)
class Kinetics:
    KD_CL: float = 15.0
    KD_CD: float = 35.0
    KD_C_O2: float = 55.0
    KD_MNO_C: float = 20.0


MOLAR_MASS = MolecularMass()
KINETICS = Kinetics()
