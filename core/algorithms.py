"""
core/algorithms.py
------------------
Greedy Best-First Search and A* Search implementations.

Both algorithms yield intermediate states for step-by-step visualization,
or can be called for an instant result via `solve()`.
"""

import heapq
import time
from typing import Callable, Dict, Generator, List, Optional, Set, Tuple

from core.grid import Cell, CellState, Grid
from core.heuristics import HeuristicType, get_heuristic
from core.search_result import SearchResult


# ──────────────────────────────────────────────────────────────
# Shared helpers
# ──────────────────────────────────────────────────────────────

def _reconstruct_path(
    came_from: Dict[Tuple[int, int], Optional[Tuple[int, int]]],
    current: Tuple[int, int]
) -> List[Tuple[int, int]]:
    path = []
    while current is not None:
        path.append(current)
        current = came_from.get(current)
    path.reverse()
    return path


def _path_cost(path: List[Tuple[int, int]]) -> float:
    """Unit step cost (each move costs 1)."""
    return float(len(path) - 1) if len(path) > 1 else 0.0


# ──────────────────────────────────────────────────────────────
# Step-generator (yields per-expansion for animation)
# ──────────────────────────────────────────────────────────────

class SearchStep:
    """
    A single step snapshot yielded by the step generators.
    Contains current frontier and just-visited node for rendering.
    """
    __slots__ = ("frontier", "visited_node", "done", "result")

    def __init__(
        self,
        frontier: Set[Tuple[int, int]],
        visited_node: Optional[Tuple[int, int]],
        done: bool = False,
        result: Optional[SearchResult] = None
    ):
        self.frontier = frontier
        self.visited_node = visited_node
        self.done = done
        self.result = result


# ──────────────────────────────────────────────────────────────
# Greedy Best-First Search
# ──────────────────────────────────────────────────────────────

def gbfs_steps(
    grid: Grid,
    htype: HeuristicType,
    start: Optional[Tuple[int, int]] = None,
    goal: Optional[Tuple[int, int]] = None
) -> Generator[SearchStep, None, None]:
    """
    Greedy Best-First Search — f(n) = h(n).
    Yields a SearchStep after every node expansion.
    Final step has done=True and a populated SearchResult.
    """
    h = get_heuristic(htype)
    s = start or grid.start.pos
    g = goal  or grid.goal.pos
    t0 = time.perf_counter()

    # (priority, tie-breaker, pos)
    open_heap: List[Tuple[float, int, Tuple[int, int]]] = []
    counter = 0
    heapq.heappush(open_heap, (h(s, g), counter, s))

    came_from: Dict[Tuple[int, int], Optional[Tuple[int, int]]] = {s: None}
    open_set: Set[Tuple[int, int]] = {s}
    closed: Set[Tuple[int, int]] = set()
    nodes_visited = 0

    while open_heap:
        _, _, current = heapq.heappop(open_heap)
        if current in closed:
            continue
        closed.add(current)
        open_set.discard(current)
        nodes_visited += 1

        if current == g:
            path = _reconstruct_path(came_from, current)
            elapsed = (time.perf_counter() - t0) * 1000
            result = SearchResult(
                path=path,
                visited=list(closed),
                nodes_visited=nodes_visited,
                path_cost=_path_cost(path),
                execution_time_ms=round(elapsed, 3),
                success=True
            )
            yield SearchStep(frozenset(open_set), current, done=True, result=result)
            return

        cell = grid.cell(*current)
        for nb in grid.neighbors(cell):
            np_ = nb.pos
            if np_ not in closed and np_ not in came_from:
                came_from[np_] = current
                counter += 1
                heapq.heappush(open_heap, (h(np_, g), counter, np_))
                open_set.add(np_)

        yield SearchStep(frozenset(open_set), current)

    elapsed = (time.perf_counter() - t0) * 1000
    result = SearchResult(
        visited=list(closed),
        nodes_visited=nodes_visited,
        execution_time_ms=round(elapsed, 3),
        success=False
    )
    yield SearchStep(frozenset(), None, done=True, result=result)


# ──────────────────────────────────────────────────────────────
# A* Search
# ──────────────────────────────────────────────────────────────

def astar_steps(
    grid: Grid,
    htype: HeuristicType,
    start: Optional[Tuple[int, int]] = None,
    goal: Optional[Tuple[int, int]] = None
) -> Generator[SearchStep, None, None]:
    """
    A* Search — f(n) = g(n) + h(n).
    Yields a SearchStep after every node expansion.
    """
    h = get_heuristic(htype)
    s = start or grid.start.pos
    g = goal  or grid.goal.pos
    t0 = time.perf_counter()

    counter = 0
    open_heap: List[Tuple[float, int, Tuple[int, int]]] = []
    heapq.heappush(open_heap, (0.0, counter, s))

    came_from: Dict[Tuple[int, int], Optional[Tuple[int, int]]] = {s: None}
    g_score: Dict[Tuple[int, int], float] = {s: 0.0}
    open_set: Set[Tuple[int, int]] = {s}
    closed: Set[Tuple[int, int]] = set()
    nodes_visited = 0

    while open_heap:
        f, _, current = heapq.heappop(open_heap)
        if current in closed:
            continue
        closed.add(current)
        open_set.discard(current)
        nodes_visited += 1

        if current == g:
            path = _reconstruct_path(came_from, current)
            elapsed = (time.perf_counter() - t0) * 1000
            result = SearchResult(
                path=path,
                visited=list(closed),
                nodes_visited=nodes_visited,
                path_cost=_path_cost(path),
                execution_time_ms=round(elapsed, 3),
                success=True
            )
            yield SearchStep(frozenset(open_set), current, done=True, result=result)
            return

        cell = grid.cell(*current)
        for nb in grid.neighbors(cell):
            np_ = nb.pos
            if np_ in closed:
                continue
            tentative_g = g_score[current] + 1.0
            if tentative_g < g_score.get(np_, float("inf")):
                came_from[np_] = current
                g_score[np_] = tentative_g
                f_score = tentative_g + h(np_, g)
                counter += 1
                heapq.heappush(open_heap, (f_score, counter, np_))
                open_set.add(np_)

        yield SearchStep(frozenset(open_set), current)

    elapsed = (time.perf_counter() - t0) * 1000
    result = SearchResult(
        visited=list(closed),
        nodes_visited=nodes_visited,
        execution_time_ms=round(elapsed, 3),
        success=False
    )
    yield SearchStep(frozenset(), None, done=True, result=result)


# ──────────────────────────────────────────────────────────────
# Instant solve (no animation) — used for re-planning
# ──────────────────────────────────────────────────────────────

def solve_instant(
    grid: Grid,
    algorithm: str,
    htype: HeuristicType,
    start: Optional[Tuple[int, int]] = None,
    goal: Optional[Tuple[int, int]] = None
) -> SearchResult:
    """
    Run the selected algorithm to completion without yielding steps.
    Used for immediate re-planning during dynamic mode.
    """
    gen = gbfs_steps(grid, htype, start, goal) if algorithm == "GBFS" else astar_steps(grid, htype, start, goal)
    result = None
    for step in gen:
        if step.done:
            result = step.result
    return result or SearchResult()
