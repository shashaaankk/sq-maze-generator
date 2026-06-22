# Square Maze Generator

A PyQt6 app that carves perfect mazes on a square grid using depth-first search.

## Theory

A maze is built by **carving passages**, not drawing walls. Start with a grid where every cell is sealed by four walls, then let DFS knock walls down as it explores.

- **DFS carve.** Begin at one cell, mark it visited, push it on a stack. Repeatedly look at the cell on top of the stack: if it has an unvisited neighbour, remove the wall between them, mark the neighbour visited, and push it (go deeper). If it has none, pop the stack (backtrack). Stop when the stack is empty.
- **Why it works.** Each cell is reached exactly once, so exactly `N - 1` walls are removed for `N` cells. The result is a *spanning tree*: fully connected, no loops. That makes it a **perfect maze** — exactly one path between any two cells.
- **Stack = depth-first.** Always expanding the newest cell is what produces long winding corridors. A queue (breadth-first) would instead spread outward in rings.

## Randomness

The only random choice is *which* unvisited neighbour to carve toward. A seeded PRNG makes this reproducible: the same seed always rebuilds the same maze, since the seed fully determines every carving decision. Leave the seed unset to get a fresh maze each run.

## Endpoints

Because any two cells have exactly one connecting path, the entrance and exit can be chosen freely:

- **Random** — any two distinct cells.
- **Furthest apart** — the two cells with the longest path between them (the maze diameter), found with two breadth-first sweeps: BFS from any cell to the most distant cell `A`, then BFS from `A` to the most distant cell `B`.

## Input

Node count must be a **perfect square** so the grid is `k × k` (e.g. `25 -> 5 × 5`). The app validates this and only enables generation for valid counts.

## Usage

```bash
pip install PyQt6
python maze_app.py
```

Controls:

- **Nodes** — node count; turns green with the derived `k × k` grid when valid, red otherwise.
- **Use seed** — tick and pick a number for a reproducible maze; the seed used is shown next to the button.
- **Endpoints** — `Random` or `Furthest apart`.
- **Generate** — carve and draw. Green dot = entrance, blue dot = exit.
