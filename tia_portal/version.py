""" TIA Portal version. This module only has the Enum class TIAVersion. The Enum class is used to store the TIA Portal version. The TIA Portal version is used to determine the correct TIA Portal API to use.
"""
from __future__ import annotations
from enum import Enum


class TiaVersion(Enum):
    """TIA Portal version. The TIA Portal version is used to determine the correct TIA Portal API to use.

    Attributes:
        V15 (str): TIA Portal V15.
        V15_1 (str): TIA Portal V15.1.
        V16 (str): TIA Portal V16.
        V17 (str): TIA Portal V17.
        V18 (str): TIA Portal V18.
        V19 (str): TIA Portal V19.
        V20 (str): TIA Portal V20.
        V21 (str): TIA Portal V21.
    """

    V15 = "15"
    V15_1 = "15_1"
    V16 = "16"
    V17 = "17"
    V18 = "18"
    V19 = "19"
    V20 = "20"
    V21 = "21"
