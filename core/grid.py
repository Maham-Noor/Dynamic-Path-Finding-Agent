"""
core/grid.py
------------
Grid environment model. Handles cell states, obstacle management,
maze generation, and neighbor queries.
"""

import random
from enum import Enum, auto
from dataclasses import dataclass, field
from typing import List, Optional, Set, Tuple


class CellState(Enum):
    EMPTY    = auto()
    WALL     = auto()
    START    = auto()
    GOAL     = auto()
    FRONTIER = auto()   # In open list / priority queue
    VISITED  = auto()   # Expanded / closed
    PATH     = auto()   # Final solution path


@dataclass
class Cell:
    row: int
    col: int
    state: CellState = CellState.EMPTY

    @property
    def pos(self) -> Tuple[int, int]:
        return (self.row, self.col)

    def __hash__(self):
        return hash(self.pos)

    def __eq__(self, other):
        return isinstance(other, Cell) and self.pos == other.pos

    def __lt__(self, other):
        return self.pos < other.pos


class Grid:
    """
    Represents the navigable environment.
    Provides maze generation, manual editing, and neighbor queries.
    """

    def __init__(self, rows: int = 20, cols: int = 20):
        self.rows = rows
        self.cols = cols
        self._cells: List[List[Cell]] = []
        self.start: Optional[Cell] = None
        self.goal: Optional[Cell] = None
        self._build_empty()
        self._set_defaults()

    # ──────────────────────────────────────────────
    # Construction
    # ──────────────────────────────────────────────

    def _build_empty(self):
        self._cells = [
            [Cell(r, c) for c in range(self.cols)]
            for r in range(self.rows)
        ]

    def _set_defaults(self):
        """Place start (top-left area) and goal (bottom-right area)."""
        sr, sc = 1, 1
        gr, gc = self.rows - 2, self.cols - 2
        self.start = self._cells[sr][sc]
        self.goal  = self._cells[gr][gc]
        self.start.state = CellState.START
        self.goal.state  = CellState.GOAL

    # ──────────────────────────────────────────────
    # Public API
    # ──────────────────────────────────────────────

    def cell(self, row: int, col: int) -> Cell:
        return self._cells[row][col]

    def all_cells(self):
        for row in self._cells:
            for cell in row:
                yield cell

    def is_valid(self, row: int, col: int) -> bool:
        return 0 <= row < self.rows and 0 <= col < self.cols

    def is_passable(self, row: int, col: int) -> bool:
        return self.is_valid(row, col) and self._cells[row][col].state != CellState.WALL

    def neighbors(self, cell: Cell) -> List[Cell]:
        """4-directional neighbors that are passable."""
        directions = [(-1, 0), (1, 0), (0, -1), (0, 1)]
        result = []
        for dr, dc in directions:
            nr, nc = cell.row + dr, cell.col + dc
            if self.is_passable(nr, nc):
                result.append(self._cells[nr][nc])
        return result

    def toggle_wall(self, row: int, col: int):
        """Flip wall/empty for a cell (ignores start/goal)."""
        cell = self._cells[row][col]
        if cell.state in (CellState.START, CellState.GOAL):
            return
        if cell.state == CellState.WALL:
            cell.state = CellState.EMPTY
        else:
            cell.state = CellState.WALL

    def set_wall(self, row: int, col: int, is_wall: bool):
        cell = self._cells[row][col]
        if cell.state in (CellState.START, CellState.GOAL):
            return
        cell.state = CellState.WALL if is_wall else CellState.EMPTY

    def reset_search_states(self):
        """Clear FRONTIER / VISITED / PATH states, preserve walls."""
        for cell in self.all_cells():
            if cell.state in (CellState.FRONTIER, CellState.VISITED, CellState.PATH):
                cell.state = CellState.EMPTY

    def clear_all(self):
        """Remove all walls and reset search states."""
        for cell in self.all_cells():
            if cell.state not in (CellState.START, CellState.GOAL):
                cell.state = CellState.EMPTY

    # ──────────────────────────────────────────────
    # Maze / Random Map Generation
    # ──────────────────────────────────────────────

    def generate_random_maze(self, density: float = 0.30):
        """
        Scatter walls with the given density (0.0 – 1.0).
        Guarantees start and goal remain open.
        """
        self.clear_all()
        for cell in self.all_cells():
            if cell.state in (CellState.START, CellState.GOAL):
                continue
            if random.random() < density:
                cell.state = CellState.WALL

    def generate_recursive_maze(self):
        """
        Recursive division maze — produces more structured corridors.
        """
        self.clear_all()
        # Border walls
        for r in range(self.rows):
            for c in range(self.cols):
                if r == 0 or r == self.rows - 1 or c == 0 or c == self.cols - 1:
                    cell = self._cells[r][c]
                    if cell.state not in (CellState.START, CellState.GOAL):
                        cell.state = CellState.WALL
        self._divide(1, 1, self.rows - 2, self.cols - 2)

    def _divide(self, r1: int, c1: int, r2: int, c2: int):
        h = r2 - r1
        w = c2 - c1
        if h < 2 or w < 2:
            return
        horizontal = h > w if h != w else random.choice([True, False])
        if horizontal:
            row = random.randrange(r1 + 1, r2, 2) if (r2 - r1) > 1 else r1
            gap = random.randrange(c1, c2 + 1)
            for c in range(c1, c2 + 1):
                if c != gap:
                    cell = self._cells[row][c]
                    if cell.state not in (CellState.START, CellState.GOAL):
                        cell.state = CellState.WALL
            self._divide(r1, c1, row - 1, c2)
            self._divide(row + 1, c1, r2, c2)
        else:
            col = random.randrange(c1 + 1, c2, 2) if (c2 - c1) > 1 else c1
            gap = random.randrange(r1, r2 + 1)
            for r in range(r1, r2 + 1):
                if r != gap:
                    cell = self._cells[r][col]
                    if cell.state not in (CellState.START, CellState.GOAL):
                        cell.state = CellState.WALL
            self._divide(r1, c1, r2, col - 1)
            self._divide(r1, col + 1, r2, c2)

    # ──────────────────────────────────────────────
    # Dynamic obstacles
    # ──────────────────────────────────────────────

    def spawn_random_obstacle(
        self,
        current_path: Optional[Set[Tuple[int, int]]] = None,
        agent_pos: Optional[Tuple[int, int]] = None
    ) -> Optional[Tuple[int, int]]:
        """
        Randomly place one new wall on an empty cell.
        Returns the (row, col) of spawned obstacle or None.
        Avoids start, goal, and the agent's current position.
        """
        candidates = [
            cell for cell in self.all_cells()
            if cell.state == CellState.EMPTY
            and cell.pos != (self.start.row, self.start.col)
            and cell.pos != (self.goal.row, self.goal.col)
            and cell.pos != agent_pos
        ]
        if not candidates:
            return None
        chosen = random.choice(candidates)
        chosen.state = CellState.WALL
        return chosen.pos

    def resize(self, rows: int, cols: int):
        """Resize grid, resetting everything."""
        self.rows = rows
        self.cols = cols
        self._build_empty()
        self._set_defaults()
