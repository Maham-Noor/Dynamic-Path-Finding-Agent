"""
gui/renderer.py
---------------
Grid renderer with rich dynamic-mode visuals:

  Static search mode:
    - Frontier cells (amber), Visited cells (indigo), Final path (mint)

  Dynamic mode:
    - Trail    : cells the agent has already walked through (cool violet)
    - Remaining: the planned path ahead (mint green)
    - Agent dot: pulsing yellow circle with glow halo
    - New obstacle flash: newly spawned walls flash bright red briefly
    - Replan overlay: when a replan fires, briefly shows the re-search
                      expansion (visited nodes fade in indigo, new path flashes)
    - Path direction arrows: small chevrons on remaining path cells showing
                             which way the agent will turn
"""

import pygame
import math
from typing import Dict, List, Optional, Set, Tuple

from core.grid import CellState, Grid
from core.agent import Agent
from gui import theme


class ObstacleFlash:
    """Tracks a briefly-flashing newly-spawned obstacle."""
    DURATION = 0.55   # seconds

    def __init__(self, pos: Tuple[int, int]):
        self.pos = pos
        self.age = 0.0          # seconds elapsed

    def update(self, dt: float) -> bool:
        """Returns True while still alive."""
        self.age += dt
        return self.age < self.DURATION

    @property
    def alpha(self) -> int:
        t = 1.0 - (self.age / self.DURATION)
        # Sharp flash then fade
        return int(min(1.0, t * 2.5) * 200)

    @property
    def color(self) -> Tuple[int, int, int]:
        # Orange-red flash
        t = 1.0 - (self.age / self.DURATION)
        r = 255
        g = int(60 + t * 80)
        b = 60
        return (r, g, b)


class ReplanFlash:
    """Drives the brief replan-expansion visual overlay."""
    DURATION = 1.2    # total seconds for the overlay

    def __init__(self, visited: List[Tuple[int, int]], new_path: List[Tuple[int, int]]):
        self.visited  = visited
        self.new_path = set(new_path)
        self.age      = 0.0

    def update(self, dt: float) -> bool:
        self.age += dt
        return self.age < self.DURATION

    @property
    def progress(self) -> float:
        return min(1.0, self.age / self.DURATION)

    @property
    def visited_alpha(self) -> int:
        # Fade in then fade out
        t = self.progress
        if t < 0.3:
            return int((t / 0.3) * 160)
        else:
            return int(((1.0 - t) / 0.7) * 160)

    @property
    def path_alpha(self) -> int:
        t = self.progress
        if t < 0.4:
            return int((t / 0.4) * 220)
        else:
            return int(((1.0 - t) / 0.6) * 220)

    def visible_visited_count(self) -> int:
        """How many visited nodes to show (sweeps in over first half)."""
        t = min(1.0, self.progress * 2.5)
        return int(t * len(self.visited))


class GridRenderer:
    # Trail fade: older cells are dimmer
    TRAIL_FADE_STEPS = 24

    def __init__(self, surface: pygame.Surface, grid: Grid):
        self.surface = surface
        self.grid    = grid
        self._compute_geometry()
        self._pulse_t = 0.0

        # Dynamic mode overlay state (managed by app via public methods)
        self._obstacle_flashes: List[ObstacleFlash] = []
        self._replan_flash: Optional[ReplanFlash]   = None
        # Ordered trail list for fade-depth rendering
        self._trail_order: List[Tuple[int, int]] = []

    # ── Geometry ──────────────────────────────────────────────────

    def _compute_geometry(self):
        gx = theme.SIDEBAR_W + theme.GRID_PADDING
        gy = theme.GRID_PADDING
        gw = theme.WINDOW_W - theme.SIDEBAR_W - theme.GRID_PADDING * 2
        gh = theme.WINDOW_H - theme.GRID_PADDING - theme.GRID_PAD_BOT
        self.cell_size = min(gw // self.grid.cols, gh // self.grid.rows)
        total_w = self.cell_size * self.grid.cols
        total_h = self.cell_size * self.grid.rows
        self.origin_x = gx + (gw - total_w) // 2
        self.origin_y = gy + (gh - total_h) // 2

    def on_grid_resize(self):
        self._compute_geometry()

    def cell_rect(self, row: int, col: int) -> pygame.Rect:
        x = self.origin_x + col * self.cell_size
        y = self.origin_y + row * self.cell_size
        return pygame.Rect(x, y, self.cell_size, self.cell_size)

    def pixel_to_cell(self, px: int, py: int) -> Optional[Tuple[int, int]]:
        col = (px - self.origin_x) // self.cell_size
        row = (py - self.origin_y) // self.cell_size
        if self.grid.is_valid(row, col):
            return (row, col)
        return None

    # ── Public overlay controls (called by app) ───────────────────

    def add_obstacle_flash(self, pos: Tuple[int, int]):
        self._obstacle_flashes.append(ObstacleFlash(pos))

    def trigger_replan_flash(self, visited: List[Tuple[int, int]],
                             new_path: List[Tuple[int, int]]):
        self._replan_flash = ReplanFlash(visited, new_path)

    def clear_dynamic_overlays(self):
        self._obstacle_flashes = []
        self._replan_flash     = None
        self._trail_order      = []

    def update_trail_order(self, trail_ordered: List[Tuple[int, int]]):
        """App passes the ordered history of agent steps for fade rendering."""
        self._trail_order = trail_ordered

    # ── Main draw ─────────────────────────────────────────────────

    def draw(
        self,
        dt: float = 0.0,
        # Static search overlays
        frontier: Optional[Set[Tuple[int, int]]] = None,
        visited:  Optional[Set[Tuple[int, int]]] = None,
        path:     Optional[Set[Tuple[int, int]]] = None,
        # Dynamic mode agent
        agent: Optional[Agent] = None,
    ):
        self._pulse_t += dt * 3.2

        # Update flash timers
        self._obstacle_flashes = [f for f in self._obstacle_flashes if f.update(dt)]
        if self._replan_flash and not self._replan_flash.update(dt):
            self._replan_flash = None

        frontier = frontier or set()
        visited  = visited  or set()
        path     = path     or set()

        cs  = self.cell_size
        pad = max(1, cs // 12)
        br  = max(2, cs // 8)   # border radius for inner cell

        # Build lookup sets from agent for this frame
        trail_set:     Set[Tuple[int, int]] = set()
        remaining_set: Set[Tuple[int, int]] = set()
        if agent:
            trail_set     = agent.trail
            remaining_set = agent.remaining_set()

        # ── Cell layer ────────────────────────────────────────────
        for cell in self.grid.all_cells():
            r, c  = cell.row, cell.col
            rect  = self.cell_rect(r, c)
            inner = pygame.Rect(rect.x + pad, rect.y + pad,
                                rect.w - pad * 2, rect.h - pad * 2)
            pos   = cell.pos

            pygame.draw.rect(self.surface, theme.BG_DEEP, rect)

            # ── Determine base color ──
            if cell.state == CellState.WALL:
                color = theme.COLOR_WALL
            elif cell.state == CellState.START:
                color = theme.COLOR_START
            elif cell.state == CellState.GOAL:
                color = theme.COLOR_GOAL
            elif agent:
                # Dynamic mode coloring
                if pos == agent.pos:
                    color = theme.COLOR_EMPTY   # agent drawn separately on top
                elif pos in remaining_set:
                    color = theme.COLOR_PATH    # ahead path: mint
                elif pos in trail_set:
                    color = theme.COLOR_TRAIL   # behind trail: violet
                else:
                    color = theme.COLOR_EMPTY
            else:
                # Static search coloring
                if pos in path:
                    color = theme.COLOR_PATH
                elif pos in frontier:
                    color = theme.COLOR_FRONTIER
                elif pos in visited:
                    color = theme.COLOR_VISITED
                else:
                    color = theme.COLOR_EMPTY

            pygame.draw.rect(self.surface, color, inner, border_radius=br)

            # ── Trail depth-fade overlay ──────────────────────────
            if agent and pos in trail_set and self._trail_order:
                depth = self._trail_depth(pos)
                if depth is not None:
                    fade_a = max(10, int(depth * 120))
                    self._alpha_rect(inner, (*theme.COLOR_TRAIL, fade_a), br)

            # ── START glow ────────────────────────────────────────
            if cell.state == CellState.START:
                self._alpha_rect(inner, (*theme.COLOR_START, 55), br)

            # ── GOAL pulse ────────────────────────────────────────
            if cell.state == CellState.GOAL:
                pulse_a = int(abs(math.sin(self._pulse_t)) * 60 + 15)
                self._alpha_rect(inner, (*theme.COLOR_GOAL, pulse_a), br)

            # ── Path direction arrows (remaining path) ────────────
            if agent and pos in remaining_set and cs >= 16:
                self._draw_arrow(pos, remaining_set, cs, rect)

        # ── Replan flash overlay ──────────────────────────────────
        if self._replan_flash:
            self._draw_replan_flash(pad, br)

        # ── Obstacle flash overlay ────────────────────────────────
        for flash in self._obstacle_flashes:
            if not self.grid.is_valid(*flash.pos):
                continue
            rect  = self.cell_rect(*flash.pos)
            inner = pygame.Rect(rect.x + pad, rect.y + pad,
                                rect.w - pad * 2, rect.h - pad * 2)
            self._alpha_rect(inner, (*flash.color, flash.alpha), br)
            # Extra bright ring
            ring_a = flash.alpha // 2
            ring_rect = inner.inflate(4, 4)
            self._alpha_ring(ring_rect, (*flash.color, ring_a), br + 2)

        # ── Agent dot ─────────────────────────────────────────────
        if agent:
            self._draw_agent(agent, cs)

        # ── Grid lines ────────────────────────────────────────────
        if cs >= 12:
            lc = (28, 28, 50)
            tw = cs * self.grid.cols
            th = cs * self.grid.rows
            for row in range(self.grid.rows + 1):
                y = self.origin_y + row * cs
                pygame.draw.line(self.surface, lc,
                                 (self.origin_x, y), (self.origin_x + tw, y))
            for col in range(self.grid.cols + 1):
                x = self.origin_x + col * cs
                pygame.draw.line(self.surface, lc,
                                 (x, self.origin_y), (x, self.origin_y + th))

        # ── Border frame ──────────────────────────────────────────
        tw = cs * self.grid.cols
        th = cs * self.grid.rows
        frame = pygame.Rect(self.origin_x - 1, self.origin_y - 1, tw + 2, th + 2)
        pygame.draw.rect(self.surface, theme.BORDER, frame, 1, border_radius=4)

    # ── Internal helpers ──────────────────────────────────────────

    def _alpha_rect(self, rect: pygame.Rect, color_a: Tuple, br: int):
        """Blit a rounded rect with alpha onto the surface."""
        s = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
        pygame.draw.rect(s, color_a, s.get_rect(), border_radius=br)
        self.surface.blit(s, rect.topleft)

    def _alpha_ring(self, rect: pygame.Rect, color_a: Tuple, br: int):
        """Blit an outlined (ring) rounded rect with alpha."""
        s = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
        pygame.draw.rect(s, color_a, s.get_rect(), width=2, border_radius=br)
        self.surface.blit(s, rect.topleft)

    def _trail_depth(self, pos: Tuple[int, int]) -> Optional[float]:
        """
        Returns 0.0 (oldest) to 1.0 (newest) based on position in trail_order.
        Used for fade rendering.
        """
        if not self._trail_order:
            return None
        n = len(self._trail_order)
        # Only care about the last TRAIL_FADE_STEPS cells for fade
        window = self._trail_order[-self.TRAIL_FADE_STEPS:]
        try:
            idx = window.index(pos)
            return (idx + 1) / len(window)
        except ValueError:
            return 0.1   # old enough to be at minimum brightness

    def _draw_arrow(self, pos: Tuple[int, int],
                    remaining: Set[Tuple[int, int]],
                    cs: int, rect: pygame.Rect):
        """Draw a small direction chevron pointing toward the next path cell."""
        r, c = pos
        # Find next cell in remaining that neighbors this one
        for dr, dc, angle in [(-1,0,90), (1,0,270), (0,-1,180), (0,1,0)]:
            nb = (r + dr, c + dc)
            if nb in remaining and nb != pos:
                cx = rect.centerx
                cy = rect.centery
                sz = max(2, cs // 7)
                rad = math.radians(angle)
                # Draw a tiny triangle pointing in direction
                tip   = (cx + int(math.cos(rad) * sz * 1.5),
                         cy - int(math.sin(rad) * sz * 1.5))
                left  = (cx + int(math.cos(rad + 2.3) * sz),
                         cy - int(math.sin(rad + 2.3) * sz))
                right = (cx + int(math.cos(rad - 2.3) * sz),
                         cy - int(math.sin(rad - 2.3) * sz))
                arrow_surf = pygame.Surface((cs, cs), pygame.SRCALPHA)
                ox, oy = rect.x, rect.y
                pts = [(tip[0]-ox, tip[1]-oy),
                       (left[0]-ox, left[1]-oy),
                       (right[0]-ox, right[1]-oy)]
                pygame.draw.polygon(arrow_surf, (*theme.BG_DEEP, 120), pts)
                self.surface.blit(arrow_surf, rect.topleft)
                break

    def _draw_replan_flash(self, pad: int, br: int):
        rf = self._replan_flash
        v_alpha = rf.visited_alpha
        p_alpha = rf.path_alpha
        n       = rf.visible_visited_count()

        # Show expanding visited nodes
        for pos in rf.visited[:n]:
            if not self.grid.is_valid(*pos):
                continue
            rect  = self.cell_rect(*pos)
            inner = pygame.Rect(rect.x + pad, rect.y + pad,
                                rect.w - pad * 2, rect.h - pad * 2)
            self._alpha_rect(inner, (*theme.COLOR_REPLAN_VISITED, v_alpha), br)

        # Show new path
        for pos in rf.new_path:
            if not self.grid.is_valid(*pos):
                continue
            rect  = self.cell_rect(*pos)
            inner = pygame.Rect(rect.x + pad, rect.y + pad,
                                rect.w - pad * 2, rect.h - pad * 2)
            self._alpha_rect(inner, (*theme.COLOR_REPLAN_PATH, p_alpha), br)

    def _draw_agent(self, agent: Agent, cs: int):
        """Draw the agent as a glowing pulsing dot."""
        ar, ac = agent.pos
        arect  = self.cell_rect(ar, ac)
        cx, cy = arect.centerx, arect.centery
        radius = max(3, cs // 3)

        # Glow halo
        pulse_r  = radius + int(abs(math.sin(self._pulse_t * 1.5)) * (cs // 5))
        glow_dim = pulse_r * 2 + 6
        glow     = pygame.Surface((glow_dim, glow_dim), pygame.SRCALPHA)
        g_alpha  = int(abs(math.sin(self._pulse_t * 1.5)) * 90 + 25)
        pygame.draw.circle(glow, (*theme.COLOR_AGENT, g_alpha),
                           (pulse_r + 3, pulse_r + 3), pulse_r)
        self.surface.blit(glow, (cx - pulse_r - 3, cy - pulse_r - 3))

        # Outer ring
        pygame.draw.circle(self.surface, theme.COLOR_AGENT, (cx, cy), radius)
        # Inner dark core
        pygame.draw.circle(self.surface, theme.BG_DEEP, (cx, cy), max(1, radius // 3))
        # Specular highlight dot
        hl_r = max(1, radius // 5)
        pygame.draw.circle(self.surface, (255, 255, 220),
                           (cx - radius // 4, cy - radius // 4), hl_r)
