"""
core/search_result.py
---------------------
Data container for algorithm output and metrics.
"""

from dataclasses import dataclass, field
from typing import List, Set, Tuple, Optional


@dataclass
class SearchResult:
    path: List[Tuple[int, int]] = field(default_factory=list)
    visited: List[Tuple[int, int]] = field(default_factory=list)
    frontier_snapshots: List[Set[Tuple[int, int]]] = field(default_factory=list)
    nodes_visited: int = 0
    path_cost: float = 0.0
    execution_time_ms: float = 0.0
    success: bool = False

    def path_set(self) -> Set[Tuple[int, int]]:
        return set(self.path)
