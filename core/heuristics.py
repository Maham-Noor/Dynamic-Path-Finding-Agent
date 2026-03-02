"""
core/heuristics.py
------------------
Heuristic functions for informed search algorithms.
"""

import math
from enum import Enum, auto
from typing import Tuple


class HeuristicType(Enum):
    MANHATTAN = auto()
    EUCLIDEAN = auto()


def manhattan(a: Tuple[int, int], b: Tuple[int, int]) -> float:
    """Manhattan distance — optimal for 4-directional grids."""
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def euclidean(a: Tuple[int, int], b: Tuple[int, int]) -> float:
    """Euclidean distance — straight-line distance."""
    return math.sqrt((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2)


def get_heuristic(htype: HeuristicType):
    """Factory — returns the heuristic callable for a given type."""
    return manhattan if htype == HeuristicType.MANHATTAN else euclidean
