"""Square maze generator — DFS carving with a clean PyQt6 UI.

Setup and run:
    pip install PyQt6
    python maze_app.py

How it works:
    * Enter a node count. It must be a perfect square; the app shows the
      derived k x k grid (e.g. 25 -> 5 x 5) and only enables Generate when valid.
    * Optionally tick "Use seed" and pick a number for a reproducible maze.
      Leave it unticked to get a fresh maze (and a fresh printed seed) each time.
    * Choose endpoints: a random pair, or the furthest-apart pair (the maze
      diameter, found with two breadth-first sweeps).
"""

import math
import random
import sys
from collections import deque

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QPainter, QPen
from PyQt6.QtWidgets import (
    QApplication,
    QButtonGroup,
    QCheckBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QRadioButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

# Wall/direction order: 0 = North, 1 = East, 2 = South, 3 = West.
DR = (-1, 0, 1, 0)
DC = (0, 1, 0, -1)


def carve_maze(rows, cols, rng):
    """Carve a perfect maze with iterative DFS (the recursive backtracker).

    Returns a list of 4-element wall lists, one per cell. True means the wall
    on that side is still standing.
    """
    n = rows * cols
    walls = [[True, True, True, True] for _ in range(n)]
    visited = [False] * n
    visited[0] = True
    stack = [0]
    while stack:
        cur = stack[-1]
        r, c = divmod(cur, cols)
        nbrs = []
        for d in range(4):
            nr, nc = r + DR[d], c + DC[d]
            if 0 <= nr < rows and 0 <= nc < cols:
                ni = nr * cols + nc
                if not visited[ni]:
                    nbrs.append((ni, d))
        if nbrs:
            ni, d = rng.choice(nbrs)
            walls[cur][d] = False
            walls[ni][(d + 2) % 4] = False
            visited[ni] = True
            stack.append(ni)
        else:
            stack.pop()
    return walls


def open_neighbors(i, walls, rows, cols):
    """Cells reachable from cell i (i.e. where the shared wall was removed)."""
    r, c = divmod(i, cols)
    out = []
    for d in range(4):
        if not walls[i][d]:
            nr, nc = r + DR[d], c + DC[d]
            if 0 <= nr < rows and 0 <= nc < cols:
                out.append(nr * cols + nc)
    return out


def bfs_distances(src, walls, rows, cols):
    """Breadth-first distance from src to every reachable cell."""
    n = rows * cols
    dist = [-1] * n
    dist[src] = 0
    q = deque([src])
    while q:
        u = q.popleft()
        for v in open_neighbors(u, walls, rows, cols):
            if dist[v] < 0:
                dist[v] = dist[u] + 1
                q.append(v)
    return dist


def furthest_pair(walls, rows, cols):
    """Two cells that are maximally far apart (the tree diameter), via two BFS sweeps."""
    dist = bfs_distances(0, walls, rows, cols)
    a = max(range(len(dist)), key=lambda i: dist[i])
    dist = bfs_distances(a, walls, rows, cols)
    b = max(range(len(dist)), key=lambda i: dist[i])
    return a, b


class MazeView(QWidget):
    """Paints the maze, scaling the grid to fill the available area."""

    def __init__(self):
        super().__init__()
        self.walls = None
        self.rows = 0
        self.cols = 0
        self.start = -1
        self.end = -1
        self.allow_pick = False      # manual endpoint selection on/off
        self.on_pick = None          # callback(cell_index)
        self._ox = self._oy = 0      # last-painted grid geometry, for hit-testing
        self._cell = 1
        self.setMinimumSize(420, 420)

    def set_maze(self, walls, rows, cols, start, end):
        self.walls = walls
        self.rows, self.cols = rows, cols
        self.start, self.end = start, end
        self.update()

    def mousePressEvent(self, event):
        if not self.walls or not self.allow_pick or self._cell <= 0:
            return
        x = event.position().x() - self._ox
        y = event.position().y() - self._oy
        c = int(x // self._cell)
        r = int(y // self._cell)
        if 0 <= r < self.rows and 0 <= c < self.cols and self.on_pick:
            self.on_pick(r * self.cols + c)

    def paintEvent(self, _event):
        if not self.walls:
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        margin = 18
        avail_w = self.width() - 2 * margin
        avail_h = self.height() - 2 * margin
        cell = max(1, min(avail_w // self.cols, avail_h // self.rows))
        gw, gh = cell * self.cols, cell * self.rows
        ox = (self.width() - gw) // 2
        oy = (self.height() - gh) // 2
        self._ox, self._oy, self._cell = ox, oy, cell

        p.fillRect(ox, oy, gw, gh, QColor("#F4F2EC"))

        def marker(idx, color):
            r, c = divmod(idx, self.cols)
            x = ox + c * cell
            y = oy + r * cell
            inset = cell * 0.24
            p.setBrush(QColor(color))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawEllipse(
                int(x + inset),
                int(y + inset),
                int(cell - 2 * inset),
                int(cell - 2 * inset),
            )

        if self.start >= 0:
            marker(self.start, "#4C9A2A")  # entrance
        if self.end >= 0:
            marker(self.end, "#1E6FB8")    # exit

        # Standing walls: dark, thick. Knocked-down walls (passages): light, thin.
        wall_pen = QPen(QColor("#26241F"))
        wall_pen.setWidth(max(2, cell // 12))
        wall_pen.setCapStyle(Qt.PenCapStyle.SquareCap)

        passage_pen = QPen(QColor("#D8D4CA"))
        passage_pen.setWidth(max(1, cell // 28))
        passage_pen.setCapStyle(Qt.PenCapStyle.FlatCap)

        # Endpoints of each side: (x1, y1, x2, y2).
        def side(x, y, d):
            return (
                (x, y, x + cell, y),                      # 0 N
                (x + cell, y, x + cell, y + cell),        # 1 E
                (x, y + cell, x + cell, y + cell),        # 2 S
                (x, y, x, y + cell),                      # 3 W
            )[d]

        # Light passages first, so dark walls paint on top at shared corners.
        p.setPen(passage_pen)
        for i in range(self.rows * self.cols):
            r, c = divmod(i, self.cols)
            x, y = ox + c * cell, oy + r * cell
            for d in range(4):
                if not self.walls[i][d]:
                    p.drawLine(*side(x, y, d))

        p.setPen(wall_pen)
        for i in range(self.rows * self.cols):
            r, c = divmod(i, self.cols)
            x, y = ox + c * cell, oy + r * cell
            for d in range(4):
                if self.walls[i][d]:
                    p.drawLine(*side(x, y, d))
        p.end()


class MazeApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Square Maze Generator")
        self.resize(640, 780)

        self.view = MazeView()

        self.nodes = QSpinBox()
        self.nodes.setRange(4, 10000)
        self.nodes.setValue(25)
        self.nodes.valueChanged.connect(self.generate)
        self.grid_label = QLabel()

        self.use_seed = QCheckBox("Use seed")
        self.seed = QSpinBox()
        self.seed.setRange(0, 999999)
        self.seed.setValue(12345)
        self.seed.setEnabled(False)
        self.use_seed.toggled.connect(self.seed.setEnabled)

        self.rb_random = QRadioButton("Random")
        self.rb_far = QRadioButton("Furthest apart")
        self.rb_manual = QRadioButton("Manual")
        self.rb_random.setChecked(True)
        group = QButtonGroup(self)
        group.addButton(self.rb_random)
        group.addButton(self.rb_far)
        group.addButton(self.rb_manual)
        self.rb_manual.toggled.connect(self._mode_changed)

        self._pick_target = "start"  # which endpoint the next click sets
        self.view.on_pick = self._on_pick

        self.generate_btn = QPushButton("Generate")
        self.generate_btn.clicked.connect(self.generate)

        self.seed_used = QLabel("")
        self.seed_used.setStyleSheet("color:#666;")

        self.hint = QLabel("")
        self.hint.setStyleSheet("color:#4C9A2A;")

        row1 = QHBoxLayout()
        row1.addWidget(QLabel("Nodes:"))
        row1.addWidget(self.nodes)
        row1.addWidget(self.grid_label)
        row1.addStretch(1)

        row2 = QHBoxLayout()
        row2.addWidget(self.use_seed)
        row2.addWidget(self.seed)
        row2.addStretch(1)
        row2.addWidget(QLabel("Endpoints:"))
        row2.addWidget(self.rb_random)
        row2.addWidget(self.rb_far)
        row2.addWidget(self.rb_manual)

        row3 = QHBoxLayout()
        row3.addWidget(self.generate_btn)
        row3.addWidget(self.seed_used)
        row3.addWidget(self.hint)
        row3.addStretch(1)

        layout = QVBoxLayout(self)
        layout.addLayout(row1)
        layout.addLayout(row2)
        layout.addLayout(row3)
        layout.addWidget(self.view, 1)

        self._validate()
        self.generate()

    def _validate(self):
        n = self.nodes.value()
        k = int(round(math.sqrt(n)))
        ok = k * k == n
        if ok:
            self.grid_label.setText(f"\u2192 {k} \u00d7 {k} grid")
            self.grid_label.setStyleSheet("color:#4C9A2A;")
        else:
            self.grid_label.setText("\u2192 not a perfect square")
            self.grid_label.setStyleSheet("color:#C0392B;")
        self.generate_btn.setEnabled(ok)
        return ok

    def _mode_changed(self):
        manual = self.rb_manual.isChecked()
        self.view.allow_pick = manual
        if manual:
            self._pick_target = "start"
            self.hint.setText("click a cell to set the green entrance")
        else:
            self.hint.setText("")

    def _on_pick(self, idx):
        """Manual endpoint selection: alternate start/end on each click."""
        if self._pick_target == "start":
            if idx == self.view.end:          # avoid overlapping the exit
                return
            self.view.start = idx
            self._pick_target = "end"
            self.hint.setText("click a cell to set the blue exit")
        else:
            if idx == self.view.start:        # avoid overlapping the entrance
                return
            self.view.end = idx
            self._pick_target = "start"
            self.hint.setText("click a cell to set the green entrance")
        self.view.update()

    def generate(self):
        if not self._validate():
            return
        k = int(round(math.sqrt(self.nodes.value())))
        seed = self.seed.value() if self.use_seed.isChecked() else random.randrange(1_000_000)
        rng = random.Random(seed)

        walls = carve_maze(k, k, rng)
        if self.rb_far.isChecked():
            start, end = furthest_pair(walls, k, k)
        elif self.rb_manual.isChecked():
            start, end = 0, k * k - 1     # sensible defaults; user clicks to adjust
            self._pick_target = "start"
            self.hint.setText("click a cell to set the green entrance")
        else:
            start, end = rng.sample(range(k * k), 2)

        self.view.set_maze(walls, k, k, start, end)
        self.seed_used.setText(f"seed: {seed}")


def main():
    app = QApplication(sys.argv)
    window = MazeApp()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()