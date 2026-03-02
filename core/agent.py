"""
core/agent.py
-------------
Navigating agent with rich state for dynamic mode visualization.

Tracks:
  - Current position along a planned path
  - Trail of visited cells (breadcrumb history)
  - Remaining path ahead
  - Flash list of newly spawned obstacles
  - Last replan search result (frontier + visited snapshots for animation)
  - Statistics: steps taken, obstacles encountered, replanning count
"""

from dataclasses import dataclass, field
from typing import List, Optional, Set, Tuple

from core.algorithms import solve_instant
from core.grid import Grid
from core.heuristics import HeuristicType
from core.search_result import SearchResult


@dataclass
class ReplanEvent:
    """Carries data for animating a single re-planning event."""
    obstacle_pos: Tuple[int, int]
    from_pos: Tuple[int, int]
    old_remaining: List[Tuple[int, int]]
    new_path: List[Tuple[int, int]]
    visited_nodes: List[Tuple[int, int]]
    success: bool


class Agent:
    """
    Navigating agent for dynamic grid traversal.

    Public attributes used by the renderer / app:
      pos              - current (row, col)
      trail            - set of already-visited cells (breadcrumb)
      remaining_path   - path cells AHEAD of current position
      full_path        - entire current planned path
      new_obstacles    - list of recently spawned walls (for flash effect)
      replan_events    - list of ReplanEvent objects (most recent first)
      steps_taken      - total movement steps executed
      obstacles_hit    - total obstacles that blocked the path
      replanning_count - total re-plans performed
      reached_goal     - True when agent reaches goal cell
      no_path          - True when no path exists from current position
    """

    def __init__(self, grid: Grid, algorithm: str, htype: HeuristicType):
        self.grid      = grid
        self.algorithm = algorithm
        self.htype     = htype

        self.pos: Tuple[int, int]             = grid.start.pos
        self.full_path: List[Tuple[int, int]] = []
        self._path_index: int                 = 0

        self.trail:          Set[Tuple[int, int]] = set()
        self.remaining_path: List[Tuple[int, int]] = []
        self.new_obstacles:  List[Tuple[int, int]] = []
        self.replan_events:  List[ReplanEvent]      = []

        self.steps_taken:      int  = 0
        self.obstacles_hit:    int  = 0
        self.replanning_count: int  = 0
        self.reached_goal:     bool = False
        self.no_path:          bool = False
        self.last_result: Optional[SearchResult] = None

    # ── Path management ───────────────────────────

    def compute_initial_path(self) -> SearchResult:
        result = solve_instant(
            self.grid, self.algorithm, self.htype,
            self.pos, self.grid.goal.pos
        )
        self._apply_path(result)
        return result

    def _apply_path(self, result: SearchResult):
        self.last_result = result
        if result.success:
            self.full_path   = result.path
            self._path_index = 0
            self.no_path     = False
            self._sync_remaining()
        else:
            self.full_path      = []
            self.remaining_path = []
            self.no_path        = True

    def _sync_remaining(self):
        if self._path_index < len(self.full_path):
            self.remaining_path = self.full_path[self._path_index:]
        else:
            self.remaining_path = []

    def remaining_set(self) -> Set[Tuple[int, int]]:
        return set(self.remaining_path)

    # ── Movement ──────────────────────────────────

    def step(self) -> bool:
        """Advance one cell. Returns True if moved."""
        if self.reached_goal or self.no_path:
            return False
        if not self.full_path or self._path_index >= len(self.full_path) - 1:
            return False

        self.trail.add(self.pos)
        self._path_index += 1
        self.pos = self.full_path[self._path_index]
        self.steps_taken += 1
        self._sync_remaining()

        if self.pos == self.grid.goal.pos:
            self.reached_goal = True
            self.trail.add(self.pos)

        return True

    # ── Obstacle detection & re-planning ──────────

    def check_and_replan(self, new_obstacle: Tuple[int, int]):
        """
        If new_obstacle blocks remaining path, re-plan and return ReplanEvent.
        Returns None if obstacle is off-path (no replan needed).
        """
        if self.reached_goal or self.no_path:
            return None

        if new_obstacle not in self.remaining_set():
            return None   # efficiency: skip replan entirely

        old_remaining = list(self.remaining_path)
        self.obstacles_hit += 1

        result = solve_instant(
            self.grid, self.algorithm, self.htype,
            self.pos, self.grid.goal.pos
        )

        event = ReplanEvent(
            obstacle_pos  = new_obstacle,
            from_pos      = self.pos,
            old_remaining = old_remaining,
            new_path      = result.path if result.success else [],
            visited_nodes = result.visited,
            success       = result.success
        )

        self._apply_path(result)
        self.replanning_count += 1
        self.replan_events.insert(0, event)
        if len(self.replan_events) > 30:
            self.replan_events.pop()

        return event

    # ── Reset ─────────────────────────────────────

    def reset(self):
        self.pos              = self.grid.start.pos
        self.full_path        = []
        self._path_index      = 0
        self.trail            = set()
        self.remaining_path   = []
        self.new_obstacles    = []
        self.replan_events    = []
        self.steps_taken      = 0
        self.obstacles_hit    = 0
        self.replanning_count = 0
        self.reached_goal     = False
        self.no_path          = False
        self.last_result      = None
