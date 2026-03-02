"""
gui/app.py
----------
Main application class. Manages:
  - Application state machine (IDLE → VISUALIZING → DYNAMIC → EDITING)
  - Pygame event loop
  - Sidebar UI with controls, toggles, sliders, metrics
  - Search visualization stepping
  - Dynamic mode agent movement + re-planning
"""

import pygame
import random
import time
from enum import Enum, auto
from typing import Optional, Set, Tuple, List

from core.grid import Grid, CellState
from core.algorithms import gbfs_steps, astar_steps, SearchStep
from core.agent import Agent
from core.heuristics import HeuristicType
from core.search_result import SearchResult
from gui import theme
from gui.renderer import GridRenderer
from gui.controls import (
    Button, ToggleGroup, Slider, MetricCard,
    draw_section_header, draw_rounded_rect
)


# ──────────────────────────────────────────────
# App States
# ──────────────────────────────────────────────

class AppState(Enum):
    IDLE        = auto()   # Waiting for user action
    VISUALIZING = auto()   # Running step-by-step search animation
    DYNAMIC     = auto()   # Agent moving with dynamic obstacles
    EDITING     = auto()   # User painting walls (implicit; handled by IDLE + drag)


# ──────────────────────────────────────────────
# PathfindingApp
# ──────────────────────────────────────────────

class PathfindingApp:
    FPS = 60

    def __init__(self):
        self.screen = pygame.display.set_mode((theme.WINDOW_W, theme.WINDOW_H))
        self.clock = pygame.time.Clock()

        # Load fonts
        pygame.font.init()
        try:
            self.font_sm  = pygame.font.SysFont("Consolas",    theme.FONT_SM, bold=False)
            self.font_md  = pygame.font.SysFont("Consolas",    theme.FONT_MD, bold=False)
            self.font_lg  = pygame.font.SysFont("Consolas",    theme.FONT_LG, bold=True)
            self.font_xl  = pygame.font.SysFont("Consolas",    theme.FONT_XL, bold=True)
            self.font_xxl = pygame.font.SysFont("Consolas",    theme.FONT_XXL, bold=True)
        except Exception:
            self.font_sm  = pygame.font.SysFont(None, theme.FONT_SM + 4)
            self.font_md  = pygame.font.SysFont(None, theme.FONT_MD + 4)
            self.font_lg  = pygame.font.SysFont(None, theme.FONT_LG + 4)
            self.font_xl  = pygame.font.SysFont(None, theme.FONT_XL + 4)
            self.font_xxl = pygame.font.SysFont(None, theme.FONT_XXL + 4)

        # Simulation settings
        self._rows = 20
        self._cols = 20
        self._density = 0.30
        self._spawn_prob = theme.SPAWN_PROBABILITY
        self._viz_speed = 1          # 1=slow, 5=fast
        self._algorithm = "A*"
        self._heuristic = HeuristicType.MANHATTAN

        # Build initial grid
        self.grid = Grid(self._rows, self._cols)
        self.renderer = GridRenderer(self.screen, self.grid)

        # State
        self.state = AppState.IDLE
        self._search_gen = None
        self._viz_frontier: Set[Tuple[int, int]] = set()
        self._viz_visited:  Set[Tuple[int, int]] = set()
        self._viz_path:     Set[Tuple[int, int]] = set()
        self._last_result: Optional[SearchResult] = None
        self._step_accum = 0.0
        self._agent: Optional[Agent] = None
        self._agent_accum = 0.0
        self._dragging_wall = False
        self._drag_mode = None   # True = placing, False = removing
        self._status_msg = "Ready — configure and press Run Search"
        self._status_color = theme.TEXT_SECONDARY
        self._notification = ""
        self._notif_timer = 0.0
        self._trail_order: list = []   # ordered history of agent steps

        self._build_ui()

    # ──────────────────────────────────────────────
    # UI Construction
    # ──────────────────────────────────────────────

    def _build_ui(self):
        """
        Build all sidebar UI elements with a layout that fits exactly within
        WINDOW_H. Budget breakdown (px):
          Title block    : 46
          Algo section   : 14 + 28 = 42
          Heuristic      : 14 + 28 = 42
          Grid Size      : 14 + 22 + 6 + 22 = 64   (two sliders, compact)
          Map Gen        : 14 + 22 = 36
          Viz Speed      : 14 + 22 = 36
          Dynamic        : 14 + 22 = 36
          Controls       : 14 + 5*(28+5) = 189
          Metrics        : 14 + 2*(38+5) = 100
          Status bar     : 36
          Hints          : 18
          ─────────────────────────────
          Total          ≈ 659  (leaves ~160px slack in 820)
        """
        sx = 12                     # sidebar x origin
        sw = theme.SIDEBAR_W - 22   # usable width  (290 - 22 = 268)
        y  = 10

        # ── Title  ──────────────────────────────────
        self._title_y = y
        y += 46                     # title block height

        btn_w = (sw - 8) // 2
        GAP   = 8                   # gap between paired buttons

        # ── Algorithm  ──────────────────────────────
        self._section_y_algo = y
        # header ~14px, buttons 28px  → block = 14+6+28 = 48
        self._btn_gbfs  = Button((sx, y + 20, btn_w, 28), "GBFS",
                                 lambda: self._set_algorithm("GBFS"))
        self._btn_astar = Button((sx + btn_w + GAP, y + 20, btn_w, 28), "A*",
                                 lambda: self._set_algorithm("A*"), active=True)
        self._algo_group = ToggleGroup([self._btn_gbfs, self._btn_astar])
        self._algo_group.set_active(1)
        y += 54

        # ── Heuristic  ──────────────────────────────
        self._section_y_heuristic = y
        self._btn_manhattan = Button((sx, y + 20, btn_w, 28), "Manhattan",
                                     lambda: self._set_heuristic(HeuristicType.MANHATTAN), active=True)
        self._btn_euclidean = Button((sx + btn_w + GAP, y + 20, btn_w, 28), "Euclidean",
                                     lambda: self._set_heuristic(HeuristicType.EUCLIDEAN))
        self._heuristic_group = ToggleGroup([self._btn_manhattan, self._btn_euclidean])
        y += 54

        # ── Grid Size (two compact sliders)  ────────
        self._section_y_grid = y
        # header ~14, then 20px label+value + 14px track per slider, gap 10
        self._slider_rows = Slider((sx, y + 32, sw, 14), 5, 40, self._rows, "Rows", ".0f")
        self._slider_cols = Slider((sx, y + 62, sw, 14), 5, 60, self._cols, "Cols", ".0f")
        y += 82

        # ── Map Generation  ─────────────────────────
        self._section_y_map = y
        self._slider_density = Slider((sx, y + 32, sw, 14), 0.05, 0.65, self._density, "Density", ".0%")
        y += 52

        # ── Visualization Speed  ────────────────────
        self._section_y_viz = y
        self._slider_speed = Slider((sx, y + 32, sw, 14), 1, 10, self._viz_speed, "Speed", ".0f", "x")
        y += 52

        # ── Dynamic Spawn Probability + Agent Speed  ────────────────
        self._section_y_dyn = y
        self._slider_spawn = Slider((sx, y + 32, sw, 14), 0.01, 0.40, self._spawn_prob, "Spawn %", ".0%")
        self._slider_agent_speed = Slider((sx, y + 62, sw, 14), 1, 8, 3.0, "Agent Spd", ".0f", "x")
        y += 82

        # ── Controls (5 buttons)  ───────────────────
        self._section_y_actions = y
        bh = 28                     # button height
        bg = 5                      # gap between buttons
        by = y + 20
        self._btn_generate = Button((sx, by,               sw, bh), "Generate Maze",  self._generate_maze)
        self._btn_clear    = Button((sx, by + (bh+bg),     sw, bh), "Clear Grid",      self._clear_grid)
        self._btn_run      = Button((sx, by + (bh+bg)*2,   sw, bh), "Run Search",      self._run_search, accent=True)
        self._btn_dynamic  = Button((sx, by + (bh+bg)*3,   sw, bh), "Dynamic Mode",    self._run_dynamic)
        self._btn_stop     = Button((sx, by + (bh+bg)*4,   sw, bh), "Stop",            self._stop, enabled=False)
        y += 20 + (bh + bg) * 5 + 4

        # ── Metrics (2x3 grid)  ─────────────────────
        self._section_y_metrics = y
        mh  = 36
        mg  = 4
        mw2 = (sw - mg) // 2
        mx2 = sx + mw2 + mg
        my  = y + 18
        self._metric_nodes   = MetricCard((sx,  my,            mw2, mh), "NODES")
        self._metric_cost    = MetricCard((mx2, my,            mw2, mh), "PATH COST")
        self._metric_time    = MetricCard((sx,  my+mh+mg,      mw2, mh), "TIME (ms)")
        self._metric_replan  = MetricCard((mx2, my+mh+mg,      mw2, mh), "REPLANS")
        self._metric_steps   = MetricCard((sx,  my+(mh+mg)*2,  mw2, mh), "STEPS")
        self._metric_obs_hit = MetricCard((mx2, my+(mh+mg)*2,  mw2, mh), "OBS HIT")

    # ──────────────────────────────────────────────
    # Callbacks
    # ──────────────────────────────────────────────

    def _set_algorithm(self, name: str):
        self._algorithm = name
        self._algo_group.set_active(0 if name == "GBFS" else 1)
        self._notify(f"Algorithm → {name}")

    def _set_heuristic(self, h: HeuristicType):
        self._heuristic = h
        self._heuristic_group.set_active(0 if h == HeuristicType.MANHATTAN else 1)
        self._notify(f"Heuristic → {h.name.capitalize()}")

    def _generate_maze(self):
        if self.state not in (AppState.IDLE,):
            return
        self._apply_grid_settings()
        self.grid.generate_random_maze(self._slider_density.value)
        self._reset_viz()
        self._notify("Maze generated")

    def _clear_grid(self):
        if self.state not in (AppState.IDLE,):
            return
        self._apply_grid_settings()
        self.grid.clear_all()
        self._reset_viz()
        self._notify("Grid cleared")

    def _apply_grid_settings(self):
        rows = int(self._slider_rows.value)
        cols = int(self._slider_cols.value)
        if rows != self._rows or cols != self._cols:
            self._rows, self._cols = rows, cols
            self.grid = Grid(rows, cols)
            self.renderer = GridRenderer(self.screen, self.grid)

    def _run_search(self):
        if self.state == AppState.VISUALIZING:
            return
        self._apply_grid_settings()
        self._reset_viz()
        self.state = AppState.VISUALIZING
        gen_fn = gbfs_steps if self._algorithm == "GBFS" else astar_steps
        self._search_gen = gen_fn(self.grid, self._heuristic)
        self._btn_run.enabled = False
        self._btn_dynamic.enabled = False
        self._btn_stop.enabled = True
        self._status_msg = f"Running {self._algorithm} ({self._heuristic.name}) …"
        self._status_color = theme.ACCENT_CYAN

    def _run_dynamic(self):
        if self.state == AppState.DYNAMIC:
            return
        self._apply_grid_settings()
        self._reset_viz()
        self._trail_order = []
        self.renderer.clear_dynamic_overlays()

        # Build agent, compute initial path
        self._agent = Agent(self.grid, self._algorithm, self._heuristic)
        result = self._agent.compute_initial_path()
        if not result.success:
            self._notify("No path found! Adjust obstacles.")
            self._agent = None
            return

        self._last_result = result
        self._update_metrics_from_result(result)
        self.state = AppState.DYNAMIC
        self._btn_run.enabled = False
        self._btn_dynamic.enabled = False
        self._btn_stop.enabled = True
        self._status_msg = "Dynamic mode — agent navigating"
        self._status_color = theme.ACCENT_ROSE

    def _stop(self):
        self.state = AppState.IDLE
        self._search_gen = None
        self._agent = None
        self._btn_run.enabled = True
        self._btn_dynamic.enabled = True
        self._btn_stop.enabled = False
        self._status_msg = "Stopped. Grid editable."
        self._status_color = theme.TEXT_SECONDARY

    # ──────────────────────────────────────────────
    # Reset helpers
    # ──────────────────────────────────────────────

    def _reset_viz(self):
        self._viz_frontier = set()
        self._viz_visited  = set()
        self._viz_path     = set()
        self._last_result  = None
        self._trail_order  = []
        self.grid.reset_search_states()
        self.renderer.clear_dynamic_overlays()
        self._metric_nodes.update("--")
        self._metric_cost.update("--")
        self._metric_time.update("--")
        self._metric_replan.update("--")
        self._metric_steps.update("--")
        self._metric_obs_hit.update("--")

    def _update_metrics(self, result: SearchResult):
        self._metric_nodes.update(str(result.nodes_visited))
        self._metric_cost.update(f"{result.path_cost:.1f}")
        self._metric_time.update(f"{result.execution_time_ms:.1f}")

    def _update_metrics_from_result(self, result: SearchResult):
        """Alias used by dynamic mode initial path."""
        self._update_metrics(result)

    def _notify(self, msg: str):
        self._notification = msg
        self._notif_timer = 2.5

    # ──────────────────────────────────────────────
    # Main Loop
    # ──────────────────────────────────────────────

    def run(self):
        while True:
            dt = self.clock.tick(self.FPS) / 1000.0
            self._handle_events()
            self._update(dt)
            self._draw()

    # ──────────────────────────────────────────────
    # Event handling
    # ──────────────────────────────────────────────

    def _handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                import sys; sys.exit()

            # Sidebar controls
            self._algo_group.handle_event(event)
            self._heuristic_group.handle_event(event)
            self._slider_rows.handle_event(event)
            self._slider_cols.handle_event(event)
            self._slider_density.handle_event(event)
            self._slider_speed.handle_event(event)
            self._slider_spawn.handle_event(event)
            self._slider_agent_speed.handle_event(event)
            self._btn_generate.handle_event(event)
            self._btn_clear.handle_event(event)
            self._btn_run.handle_event(event)
            self._btn_dynamic.handle_event(event)
            self._btn_stop.handle_event(event)

            # Grid wall painting (only when IDLE)
            if self.state == AppState.IDLE:
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    cell_pos = self.renderer.pixel_to_cell(*event.pos)
                    if cell_pos:
                        r, c = cell_pos
                        cell = self.grid.cell(r, c)
                        self._drag_mode = cell.state != CellState.WALL
                        self._dragging_wall = True
                        self.grid.toggle_wall(r, c)
                if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                    self._dragging_wall = False
                if event.type == pygame.MOUSEMOTION and self._dragging_wall:
                    cell_pos = self.renderer.pixel_to_cell(*event.pos)
                    if cell_pos:
                        self.grid.set_wall(*cell_pos, is_wall=self._drag_mode)

            # Keyboard shortcuts
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_r:
                    self._run_search()
                elif event.key == pygame.K_d:
                    self._run_dynamic()
                elif event.key == pygame.K_c:
                    self._clear_grid()
                elif event.key == pygame.K_g:
                    self._generate_maze()
                elif event.key == pygame.K_ESCAPE:
                    self._stop()

    # ──────────────────────────────────────────────
    # Update
    # ──────────────────────────────────────────────

    def _update(self, dt: float):
        if self._notif_timer > 0:
            self._notif_timer -= dt

        if self.state == AppState.VISUALIZING:
            self._update_visualizing(dt)
        elif self.state == AppState.DYNAMIC:
            self._update_dynamic(dt)

    def _update_visualizing(self, dt: float):
        if self._search_gen is None:
            return

        speed = max(1, int(self._slider_speed.value))
        step_delay = theme.VIZ_STEP_DELAY_MS / 1000.0 / speed

        self._step_accum += dt
        steps_to_take = int(self._step_accum / step_delay)
        self._step_accum -= steps_to_take * step_delay

        for _ in range(max(1, steps_to_take)):
            try:
                step: SearchStep = next(self._search_gen)
                self._viz_frontier = set(step.frontier)
                if step.visited_node:
                    self._viz_visited.add(step.visited_node)
                if step.done:
                    if step.result:
                        self._last_result = step.result
                        if step.result.success:
                            self._viz_path = step.result.path_set()
                            self._status_msg = f"Path found! Length {step.result.path_cost:.0f}"
                            self._status_color = theme.COLOR_PATH
                        else:
                            self._status_msg = "No path exists"
                            self._status_color = theme.ACCENT_ROSE
                        self._update_metrics(step.result)
                    self._finalize_search()
                    break
            except StopIteration:
                self._finalize_search()
                break

    def _finalize_search(self):
        self._search_gen = None
        self.state = AppState.IDLE
        self._btn_run.enabled = True
        self._btn_dynamic.enabled = True
        self._btn_stop.enabled = False

    def _update_dynamic(self, dt: float):
        if self._agent is None:
            return

        agent_speed = max(1.0, self._slider_agent_speed.value)
        agent_delay = theme.AGENT_STEP_DELAY_MS / 1000.0 / agent_speed
        self._agent_accum += dt

        while self._agent_accum >= agent_delay:
            self._agent_accum -= agent_delay
            self._dynamic_tick()
            if self._agent is None:
                break

    def _dynamic_tick(self):
        """One discrete agent step: maybe spawn obstacle, then move."""
        agent = self._agent
        if agent is None:
            return

        spawn_prob = self._slider_spawn.value

        # ── Attempt obstacle spawn ─────────────────────────────
        if random.random() < spawn_prob:
            new_obs = self.grid.spawn_random_obstacle(
                current_path=agent.remaining_set(),
                agent_pos=agent.pos
            )
            if new_obs:
                agent.new_obstacles.append(new_obs)
                self.renderer.add_obstacle_flash(new_obs)

                # Check if it blocks the path
                event = agent.check_and_replan(new_obs)
                if event is not None:
                    # Trigger replan visualization overlay
                    self.renderer.trigger_replan_flash(
                        event.visited_nodes, event.new_path
                    )
                    self._metric_replan.update(str(agent.replanning_count))
                    self._metric_obs_hit.update(str(agent.obstacles_hit))

                    if agent.no_path:
                        self._status_msg = "No path after obstacle — stopped"
                        self._status_color = theme.ACCENT_ROSE
                        self._update_dynamic_metrics()
                        self._finalize_dynamic()
                        return

                    count = agent.replanning_count
                    self._notify(f"Replanned x{count} — new path: {len(event.new_path)} steps")
                    self._status_msg = f"Replanning... (x{count})"
                    self._status_color = theme.COLOR_REPLAN_PATH

        # ── Move agent one step ────────────────────────────────
        prev_pos = agent.pos
        moved = agent.step()

        if moved and agent.pos != prev_pos:
            # Extend ordered trail for depth-fade rendering
            self._trail_order.append(prev_pos)
            self.renderer.update_trail_order(self._trail_order)
            self._metric_steps.update(str(agent.steps_taken))
            self._status_msg = f"Moving... step {agent.steps_taken}"
            self._status_color = theme.ACCENT_CYAN

        # ── Check goal ─────────────────────────────────────────
        if agent.reached_goal:
            self._trail_order.append(agent.pos)
            self.renderer.update_trail_order(self._trail_order)
            self._status_msg = f"Goal reached in {agent.steps_taken} steps!"
            self._status_color = theme.COLOR_PATH
            self._update_dynamic_metrics()
            self._finalize_dynamic()

    def _update_dynamic_metrics(self):
        agent = self._agent
        if agent is None:
            return
        if agent.last_result:
            self._metric_nodes.update(str(agent.last_result.nodes_visited))
            self._metric_cost.update(f"{agent.last_result.path_cost:.1f}")
            self._metric_time.update(f"{agent.last_result.execution_time_ms:.1f}")
        self._metric_replan.update(str(agent.replanning_count))
        self._metric_steps.update(str(agent.steps_taken))
        self._metric_obs_hit.update(str(agent.obstacles_hit))

    def _finalize_dynamic(self):
        self._agent = None
        self._trail_order = []
        self.renderer.clear_dynamic_overlays()
        self.state = AppState.IDLE
        self._btn_run.enabled = True
        self._btn_dynamic.enabled = True
        self._btn_stop.enabled = False

    # ──────────────────────────────────────────────
    # Drawing
    # ──────────────────────────────────────────────

    def _draw(self):
        self.screen.fill(theme.BG_DEEP)
        self._draw_sidebar()

        dt_render = self.clock.get_time() / 1000.0
        agent = self._agent if self.state == AppState.DYNAMIC else None

        self.renderer.draw(
            dt       = dt_render,
            frontier = self._viz_frontier,
            visited  = self._viz_visited,
            path     = self._viz_path,
            agent    = agent,
        )

        pygame.display.flip()

    def _draw_sidebar(self):
        sw = theme.SIDEBAR_W
        lx = 12
        lw = sw - 22

        # ── Panel background + right border
        draw_rounded_rect(self.screen, theme.BG_PANEL, pygame.Rect(0, 0, sw, theme.WINDOW_H), 0)
        pygame.draw.line(self.screen, theme.BORDER, (sw, 0), (sw, theme.WINDOW_H), 1)

        # ── Title block  ────────────────────────────────
        # Two-line title using safe ASCII to avoid font glyph gaps
        t1 = self.font_xl.render("PATH", True, theme.ACCENT_ROSE)
        t2 = self.font_xl.render("FIND", True, theme.ACCENT_CYAN)
        dot = self.font_xl.render("*", True, theme.ACCENT_PINK)
        # row them: "PATH  *  FIND" on one line if it fits, else two lines
        title_line = self.font_xl.render("PATH  *  FIND", True, theme.ACCENT_ROSE)
        self.screen.blit(title_line, (lx, 10))
        sub = self.font_sm.render("dynamic pathfinding agent", True, theme.TEXT_MUTED)
        self.screen.blit(sub, (lx, 10 + title_line.get_height() + 2))

        # ── Sections (drawn at pre-calculated y positions from _build_ui)
        # Each draw_section_header call returns y after the underline — ignored here
        # because widget positions are baked in during _build_ui.

        draw_section_header(self.screen, self.font_sm, "ALGORITHM",
                            lx, self._section_y_algo, lw)
        self._algo_group.draw(self.screen, self.font_md)

        draw_section_header(self.screen, self.font_sm, "HEURISTIC",
                            lx, self._section_y_heuristic, lw)
        self._heuristic_group.draw(self.screen, self.font_md)

        draw_section_header(self.screen, self.font_sm, "GRID SIZE",
                            lx, self._section_y_grid, lw)
        self._slider_rows.draw(self.screen, self.font_sm, self.font_md)
        self._slider_cols.draw(self.screen, self.font_sm, self.font_md)

        draw_section_header(self.screen, self.font_sm, "MAP GENERATION",
                            lx, self._section_y_map, lw)
        self._slider_density.draw(self.screen, self.font_sm, self.font_md)

        draw_section_header(self.screen, self.font_sm, "VIZ SPEED",
                            lx, self._section_y_viz, lw)
        self._slider_speed.draw(self.screen, self.font_sm, self.font_md)

        draw_section_header(self.screen, self.font_sm, "DYNAMIC MODE",
                            lx, self._section_y_dyn, lw)
        self._slider_spawn.draw(self.screen, self.font_sm, self.font_md)
        self._slider_agent_speed.draw(self.screen, self.font_sm, self.font_md)

        draw_section_header(self.screen, self.font_sm, "CONTROLS",
                            lx, self._section_y_actions, lw)
        self._btn_generate.draw(self.screen, self.font_md)
        self._btn_clear.draw(self.screen, self.font_md)
        self._btn_run.draw(self.screen, self.font_md)
        self._btn_dynamic.draw(self.screen, self.font_md)
        self._btn_stop.draw(self.screen, self.font_md)

        draw_section_header(self.screen, self.font_sm, "METRICS",
                            lx, self._section_y_metrics, lw)
        self._metric_nodes.draw(self.screen, self.font_sm, self.font_md)
        self._metric_cost.draw(self.screen, self.font_sm, self.font_md)
        self._metric_time.draw(self.screen, self.font_sm, self.font_md)
        self._metric_replan.draw(self.screen, self.font_sm, self.font_md)
        self._metric_steps.draw(self.screen, self.font_sm, self.font_md)
        self._metric_obs_hit.draw(self.screen, self.font_sm, self.font_md)

        # ── Divider before footer
        footer_top = theme.WINDOW_H - 54
        pygame.draw.line(self.screen, theme.BORDER, (0, footer_top), (sw, footer_top), 1)

        # ── Status message
        status_surf = self.font_sm.render(self._status_msg, True, self._status_color)
        # Clip to sidebar width
        clip = pygame.Rect(lx, footer_top + 6, lw, 18)
        self.screen.set_clip(clip)
        self.screen.blit(status_surf, (lx, footer_top + 6))
        self.screen.set_clip(None)

        # ── Notification toast (floats above status)
        if self._notif_timer > 0 and self._notification:
            alpha = int(min(1.0, self._notif_timer) * 220)
            ns = pygame.Surface((lw, 20), pygame.SRCALPHA)
            ns.fill((22, 22, 38, alpha))
            nt = self.font_sm.render(self._notification, True, (*theme.ACCENT_CYAN, alpha))
            ns.blit(nt, (6, 2))
            self.screen.blit(ns, (lx, footer_top - 22))

        # ── Keyboard hints (compact, single row)
        hints = [("R","Run"), ("D","Dyn"), ("G","Gen"), ("C","Clr"), ("ESC","Stop")]
        hx = lx
        hy = theme.WINDOW_H - 26
        for key, desc in hints:
            ks = self.font_sm.render(f"[{key}]", True, theme.ACCENT_PINK)
            ds = self.font_sm.render(f"{desc} ", True, theme.TEXT_MUTED)
            if hx + ks.get_width() + ds.get_width() > sw - 4:
                break
            self.screen.blit(ks, (hx, hy))
            hx += ks.get_width()
            self.screen.blit(ds, (hx, hy))
            hx += ds.get_width() + 2

        # ── Legend in grid area bottom strip
        self._draw_legend()

    def _draw_legend(self):
        """Draw color legend in a strip at the very bottom of the grid area."""
        items = [
            (theme.COLOR_START,          "Start"),
            (theme.COLOR_GOAL,           "Goal"),
            (theme.COLOR_FRONTIER,       "Frontier"),
            (theme.COLOR_VISITED,        "Visited"),
            (theme.COLOR_PATH,           "Path"),
            (theme.COLOR_TRAIL,          "Trail"),
            (theme.COLOR_AGENT,          "Agent"),
            (theme.COLOR_REPLAN_VISITED, "Replan"),
            (theme.COLOR_WALL,           "Wall"),
        ]
        legend_h = 22
        lx = theme.SIDEBAR_W + theme.GRID_PADDING
        ly = theme.WINDOW_H - legend_h
        lw = theme.WINDOW_W - theme.SIDEBAR_W

        strip = pygame.Rect(theme.SIDEBAR_W, ly - 1, lw, legend_h + 1)
        pygame.draw.rect(self.screen, theme.BG_PANEL, strip)
        pygame.draw.line(self.screen, theme.BORDER,
                         (theme.SIDEBAR_W, ly - 1), (theme.WINDOW_W, ly - 1), 1)

        x = lx
        for color, label in items:
            pygame.draw.rect(self.screen, color, (x, ly + 6, 9, 9), border_radius=2)
            txt = self.font_sm.render(label, True, theme.TEXT_MUTED)
            self.screen.blit(txt, (x + 12, ly + 4))
            x += 12 + txt.get_width() + 10
            if x > theme.WINDOW_W - 10:
                break
