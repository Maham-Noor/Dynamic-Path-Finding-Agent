# Dynamic Pathfinding Agent

> A real-time grid navigation agent built with Python + Pygame.
> Implements **Greedy Best-First Search** and **A\*** with live visualization,
> interactive map editing, and a dynamic obstacle mode with automatic re-planning.

---

## Table of Contents

- [Features](#features)
- [Installation](#installation)
- [Running the App](#running-the-app)
- [Project Structure](#project-structure)
- [How to Use](#how-to-use)
- [Algorithms](#algorithms)
- [Heuristics](#heuristics)
- [Dynamic Mode](#dynamic-mode)
- [Visual Legend](#visual-legend)
- [Keyboard Shortcuts](#keyboard-shortcuts)
- [Configuration](#configuration)
- [License](#license)

---

## Features

| Feature | Details |
|---|---|
| **Two Search Algorithms** | Greedy Best-First Search (GBFS) and A* Search |
| **Two Heuristics** | Manhattan Distance and Euclidean Distance, switchable at runtime |
| **Step-by-step Visualization** | Watch the frontier expand and path form in real time |
| **Dynamic Obstacle Mode** | Obstacles spawn mid-transit; agent detects and re-plans instantly |
| **Interactive Map Editor** | Click or drag on the grid to paint and erase walls |
| **Random Maze Generation** | Configurable obstacle density (5% to 65%) |
| **Live Metrics Dashboard** | Nodes visited, path cost, execution time, re-plan count, steps taken |
| **Adjustable Speed** | Independent sliders for visualization speed and agent movement speed |
| **Resizable Grid** | From 5x5 up to 40x60, configured via sliders |

---

## Installation

**Requirements:** Python 3.9 or higher

### 1. Clone the repository

```bash
git clone https://github.com/YOUR_USERNAME/Dynamic-Path-Finding-Agent.git
cd Dynamic-Path-Finding-Agent
```

### 2. Install dependencies

A `requirements.txt` file is included. Install everything with a single command:

```bash
pip install -r requirements.txt
```

> This installs `pygame`, the only external dependency the project needs.

---

## Running the App

```bash
python main.py
```

The application window will open immediately at **1280 x 820** pixels with a default 20x20 grid.

---

## Project Structure

```
Dynamic-Path-Finding-Agent/
│
├── main.py                    # Entry point — initializes Pygame and launches the app
│
├── requirements.txt           # Python dependencies (pip install -r requirements.txt)
│
├── core/                      # Pure logic — no GUI dependency
│   ├── __init__.py
│   ├── grid.py                # Grid model, cell states, maze generation, neighbor queries
│   ├── heuristics.py          # Manhattan & Euclidean distance functions
│   ├── algorithms.py          # GBFS and A* as Python generators + instant-solve variant
│   ├── agent.py               # Moving agent: path following, trail tracking, re-planning
│   └── search_result.py       # SearchResult dataclass (path, metrics, visited nodes)
│
├── gui/                       # Presentation layer — rendering and controls only
│   ├── __init__.py
│   ├── app.py                 # Main app: state machine, event loop, sidebar layout
│   ├── renderer.py            # Grid drawing, agent glow, obstacle flash, replan overlay
│   ├── controls.py            # Reusable widgets: Button, ToggleGroup, Slider, MetricCard
│   └── theme.py               # Design tokens: all colors, sizes, animation constants
│
└── README.md                  # This file
```

---

## How to Use

### Static Search Mode

1. Set your **grid size** using the Rows and Cols sliders
2. Select an **algorithm** — GBFS or A*
3. Select a **heuristic** — Manhattan or Euclidean
4. Optionally click **Generate Maze** to fill the grid with random obstacles,
   or click and drag directly on the grid to paint walls manually
5. Adjust **Viz Speed** to control how fast the animation plays
6. Click **Run Search** or press `R` — watch the frontier expand in amber,
   visited cells fill in indigo-blue, and the final path light up in mint green

### Dynamic Mode

1. Configure the grid and algorithm as above
2. Set **Spawn %** to control how often new obstacles appear per step
3. Set **Agent Spd** to control how fast the agent moves
4. Click **Dynamic Mode** or press `D`
5. The agent computes an initial path and begins moving
6. When a new obstacle spawns on the agent's route, re-planning fires automatically —
   you will see a cyan sweep for the re-search expansion and a gold flash for the new path
7. The trail of already-walked cells turns violet with a depth-fade effect

### Editing the Map

- **Left-click** on any empty cell to place a wall
- **Left-click** on any wall to remove it
- **Click and drag** to paint or erase multiple cells in one stroke
- The start and goal nodes cannot be overwritten

---

## Algorithms

### Greedy Best-First Search (GBFS)

```
f(n) = h(n)
```

GBFS expands whichever node appears closest to the goal according to the heuristic alone.
It ignores how expensive the path to the current node already is.

- **Fast** — reaches the goal with few expansions in open environments
- **Not optimal** — may return a longer-than-necessary path
- **Susceptible to heuristic traps** — can get stuck chasing dead ends in dense mazes

### A* Search

```
f(n) = g(n) + h(n)
```

A* balances the actual cost from the start `g(n)` with the estimated cost to the goal `h(n)`.

- **Optimal** — guaranteed to find the shortest path with an admissible heuristic
- **Complete** — will always find a path if one exists
- **Slower than GBFS** on trivial instances, but far more reliable on complex maps

---

## Heuristics

| Heuristic | Formula | Notes |
|---|---|---|
| **Manhattan** | `\|r1-r2\| + \|c1-c2\|` | Ideal for 4-directional grids — tight lower bound, always admissible |
| **Euclidean** | `sqrt((r1-r2)^2 + (c1-c2)^2)` | Straight-line distance — admissible but weaker bound, explores more nodes |

Manhattan is the recommended choice for this grid environment.
Euclidean is provided for comparison and experimentation.

---

## Dynamic Mode

When **Dynamic Mode** is active, the following happens each agent step:

1. With probability **Spawn %**, a new wall is placed on a random empty cell
2. The agent checks whether the new wall intersects its **remaining planned path**
   - If **no intersection** — agent continues without any re-planning (O(1) check)
   - If **intersection detected** — full re-plan is triggered instantly from the agent's current position
3. The agent moves one step forward along its current path
4. Visual overlays show:
   - **Orange-red flash** on the new wall (fades over 0.55 s)
   - **Cyan sweep** of nodes explored during re-planning
   - **Gold flash** on the newly computed path (fades over 1.2 s)
   - **Violet trail** of cells the agent has already walked through

The re-plan counter, obstacle-hit count, and step count are all tracked in the metrics sidebar.

---

## Visual Legend

| Color | Element | Meaning |
|---|---|---|
| Teal | Start node | Fixed starting position |
| Rose / Pink | Goal node | Pulsing destination — fixed target |
| Amber / Yellow | Frontier | Nodes currently in the open list (priority queue) |
| Indigo Blue | Visited | Nodes that have been fully expanded (closed list) |
| Mint Green | Path | The computed solution path |
| Violet | Trail | Cells the agent has already walked through (dynamic mode) |
| Bright Yellow | Agent | Current agent position — pulsing glow dot |
| Bright Cyan | Replan visited | Nodes explored during a re-planning event |
| Gold | Replan path | The newly computed path after an obstacle blocks the route |
| Dark | Wall | Impassable obstacle cell |

---

## Keyboard Shortcuts

| Key | Action |
|---|---|
| `R` | Run Search |
| `D` | Start Dynamic Mode |
| `G` | Generate random maze |
| `C` | Clear grid |
| `ESC` | Stop current run |
| Left-click on grid | Place or remove a wall |
| Left-click and drag | Paint or erase walls continuously |

---

## Configuration

All settings are adjustable via the sidebar sliders at runtime — no config files needed.

| Setting | Range | Description |
|---|---|---|
| Rows | 5 – 40 | Grid height in cells |
| Cols | 5 – 60 | Grid width in cells |
| Density | 5% – 65% | Obstacle coverage for random maze generation |
| Viz Speed | 1x – 10x | How fast the search animation plays |
| Spawn % | 1% – 40% | Probability of a new obstacle spawning each agent step |
| Agent Spd | 1x – 8x | How fast the agent moves along its path |

---

## License

MIT — free to use, modify, and distribute.