#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ЛР №4, «Системи штучного інтелекту».
Двонаправлений хвильовий пошук найкоротшого шляху на одиничному графі,
представленому у вигляді лабіринту (-1 — непрохідна клітинка, 0 — прохідна).
Для порівняння реалізовано також одно-направлений хвильовий пошук.

Запуск: python bidir_lab.py
"""

import time
import tkinter as tk
from tkinter import ttk

# ---------------------------------------------------------------------------
# Заданий лабіринт 15 × 15 (# — непрохідна клітинка, . — прохідна)
# ---------------------------------------------------------------------------
MAZE = [
    "...............",
    "..##.....####..",
    "...#..#.....#..",
    ".#....#..#..#..",
    ".#....#..#.....",
    ".####.####..##.",
    "......#........",
    "..##..#..####..",
    "...#.....#.....",
    ".#.#.###....#..",
    ".#......#...#..",
    ".####...#.###..",
    "....#.......#..",
    "..#.#..####.#..",
    "..#............",
]
START, GOAL = (0, 0), (14, 14)        # (рядок, стовпець), нумерація з 0
MIN_SIZE, MAX_SIZE = 10, 20

OPERATORS = {
    "cross": ("вверх-вниз-вправо-вліво", [(-1, 0), (1, 0), (0, 1), (0, -1)]),
    "diag": ("по діагоналях", [(-1, 1), (1, 1), (1, -1), (-1, -1)]),
    "all": ("комбінація (8 напрямків)",
            [(-1, 0), (1, 0), (0, 1), (0, -1), (-1, 1), (1, 1), (1, -1), (-1, -1)]),
}
METHODS = {"bi": "двонаправлений", "one": "одно-направлений"}


def default_grid():
    """Матриця лабіринту: -1 — непрохідна клітинка, 0 — прохідна."""
    return [[-1 if ch == "#" else 0 for ch in row] for row in MAZE]


# ---------------------------------------------------------------------------
# Хвильові алгоритми
# ---------------------------------------------------------------------------
class Wave:
    """Одна хвиля: власна матриця позначок і поточний фронт."""

    def __init__(self, grid, origin, moves):
        self.rows, self.cols = len(grid), len(grid[0])
        self.moves = moves
        self.mark = [row[:] for row in grid]       # -1 стіна, 0 вільна, k > 0 — номер хвилі
        self.mark[origin[0]][origin[1]] = 1
        self.front = [origin]
        self.stage = {origin: 0}                   # на якому циклі клітинку охоплено

    def expand(self, cycle):
        """Поширити хвилю на один крок: розкрити весь фронт, повернути новий фронт."""
        new = []
        for r, c in self.front:
            for dr, dc in self.moves:
                a, b = r + dr, c + dc
                if 0 <= a < self.rows and 0 <= b < self.cols and self.mark[a][b] == 0:
                    self.mark[a][b] = self.mark[r][c] + 1
                    self.stage[(a, b)] = cycle
                    new.append((a, b))
        expanded = len(self.front)
        self.front = new
        return new, expanded

    def back_to_origin(self, cell):
        """Зворотний хід: від клітинки до джерела хвилі за спаданням позначок."""
        seq = [cell]
        while self.mark[cell[0]][cell[1]] != 1:
            r, c = cell
            for dr, dc in self.moves:
                a, b = r - dr, c - dc
                if 0 <= a < self.rows and 0 <= b < self.cols and self.mark[a][b] == self.mark[r][c] - 1:
                    cell = (a, b)
                    break
            seq.append(cell)
        return seq


def check(grid, start, goal):
    if grid[start[0]][start[1]] == -1 or grid[goal[0]][goal[1]] == -1:
        raise ValueError("Старт або мета на непрохідній клітинці")


def one_way_search(grid, start, goal, op):
    """Одно-направлений хвильовий пошук: хвиля лише від старту."""
    check(grid, start, goal)
    ws = Wave(grid, start, OPERATORS[op][1])
    cycles = expanded = 0
    found = start == goal
    while ws.front and not found:
        cycles += 1
        new, e = ws.expand(cycles)
        expanded += e
        found = goal in ws.stage
    path = list(reversed(ws.back_to_origin(goal))) if found else []
    return {"path": path, "cycles": cycles, "expanded": expanded, "meet": None,
            "ws": ws, "wf": None}


def two_way_search(grid, start, goal, op):
    """
    Двонаправлений хвильовий пошук: дві зустрічні хвилі — від старту і від мети.
    На кожному циклі спочатку на один крок поширюється хвиля від старту, потім — від мети.
    Зустріч — клітинка нового фронту однієї хвилі, вже позначена іншою хвилею;
    серед таких клітинок вибирається та, що дає найкоротший сумарний шлях.
    """
    check(grid, start, goal)
    moves = OPERATORS[op][1]
    ws, wf = Wave(grid, start, moves), Wave(grid, goal, moves)
    cycles = expanded = 0
    meet = start if start == goal else None
    while ws.front and wf.front and meet is None:
        cycles += 1
        for wave, other in ((ws, wf), (wf, ws)):
            new, e = wave.expand(cycles)
            expanded += e
            hits = [c for c in new if other.mark[c[0]][c[1]] > 0]
            if hits:
                meet = min(hits, key=lambda c: ws.mark[c[0]][c[1]] + wf.mark[c[0]][c[1]])
                break
            if not wave.front:
                break
    path = []
    if meet is not None:
        to_start = ws.back_to_origin(meet)      # meet ... start
        to_goal = wf.back_to_origin(meet)       # meet ... goal
        path = list(reversed(to_start)) + to_goal[1:]
    return {"path": path, "cycles": cycles, "expanded": expanded, "meet": meet,
            "ws": ws, "wf": wf}


SEARCH = {"bi": two_way_search, "one": one_way_search}


def search_time_us(grid, start, goal, op, method):
    """Час одного пошуку, мкс (медіана 5 серій по 30 запусків)."""
    res = []
    for _ in range(5):
        t0 = time.perf_counter()
        for _ in range(30):
            SEARCH[method](grid, start, goal, op)
        res.append((time.perf_counter() - t0) / 30 * 1e6)
    return sorted(res)[2]


def cell_name(rc):
    return f"({rc[0] + 1},{rc[1] + 1})"


# ---------------------------------------------------------------------------
# Графічний інтерфейс
# ---------------------------------------------------------------------------
C = {"wall": "#495057", "free": "#ffffff", "ws": "#d0e4ff", "wf": "#d3f9d8",
     "fs": "#ffe066", "ff": "#ffc078", "meet": "#b197fc", "path": "#ff8787",
     "start": "#40c057", "goal": "#fa5252", "grid": "#adb5bd"}


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.apply_theme()
        self.title("ЛР №4. Двонаправлений хвильовий пошук")
        self.geometry("1320x840")
        self.grid_m = default_grid()
        self.start_c, self.goal_c = START, GOAL
        self.res = None
        self.shown = 0               # скільки циклів пошуку вже показано
        self.done = False
        self.job = None
        self.paint_value = None
        self.runs = []
        self.res_win = None
        self.build()
        self.redraw()

    def apply_theme(self):
        """На macOS — рідна тема; на Windows/Linux — Sun Valley (pip install sv-ttk), якщо є."""
        if self.tk.call("tk", "windowingsystem") == "aqua":
            return
        try:
            import sv_ttk
            sv_ttk.set_theme("light")
        except ImportError:
            ttk.Style(self).theme_use("clam")

    # ---------------- інтерфейс ----------------
    def build(self):
        p = ttk.Frame(self, padding=6)
        p.pack(side="left", fill="y")

        f = ttk.LabelFrame(p, text="Лабіринт (матриця суміжності)", padding=6)
        f.pack(fill="x", pady=3)
        r = ttk.Frame(f)
        r.pack(fill="x")
        ttk.Label(r, text="Рядків").pack(side="left")
        self.sp_r = ttk.Spinbox(r, from_=MIN_SIZE, to=MAX_SIZE, width=4)
        self.sp_r.pack(side="left", padx=3)
        ttk.Label(r, text="Стовпців").pack(side="left")
        self.sp_c = ttk.Spinbox(r, from_=MIN_SIZE, to=MAX_SIZE, width=4)
        self.sp_c.pack(side="left", padx=3)
        ttk.Button(f, text="Застосувати розмір", command=self.apply_size).pack(fill="x", pady=(4, 0))
        r = ttk.Frame(f)
        r.pack(fill="x", pady=(4, 0))
        ttk.Button(r, text="Очистити стіни", command=self.clear_walls).pack(side="left", fill="x", expand=True)
        ttk.Button(r, text="Відновити заданий", command=self.restore).pack(side="left", fill="x", expand=True)
        self.info = ttk.Label(f, justify="left")
        self.info.pack(anchor="w", pady=(4, 0))

        f = ttk.LabelFrame(p, text="Клік мишею по клітинці", padding=6)
        f.pack(fill="x", pady=3)
        self.mode = tk.StringVar(value="wall")
        for val, txt in (("wall", "Стіна (-1) ↔ прохід (0), можна вести мишею"),
                         ("start", "Початкова вершина"), ("goal", "Цільова вершина")):
            ttk.Radiobutton(f, text=txt, value=val, variable=self.mode).pack(anchor="w")

        f = ttk.LabelFrame(p, text="Пошук", padding=6)
        f.pack(fill="x", pady=3)
        ttk.Label(f, text="Метод:").pack(anchor="w")
        self.method = tk.StringVar(value="bi")
        for val, txt in (("bi", "двонаправлений (зустрічні хвилі)"),
                         ("one", "одно-направлений (для порівняння)")):
            ttk.Radiobutton(f, text=txt, value=val, variable=self.method, command=self.reset).pack(anchor="w")
        ttk.Label(f, text="Оператор переходу:").pack(anchor="w", pady=(4, 0))
        self.op = tk.StringVar(value="cross")
        for key, (name, _) in OPERATORS.items():
            ttk.Radiobutton(f, text=name, value=key, variable=self.op, command=self.reset).pack(anchor="w")
        r = ttk.Frame(f)
        r.pack(fill="x", pady=4)
        ttk.Label(r, text="Затримка, мс").pack(side="left")
        self.delay = tk.IntVar(value=300)
        ttk.Scale(r, from_=20, to=1500, variable=self.delay).pack(side="left", fill="x", expand=True)
        r = ttk.Frame(f)
        r.pack(fill="x")
        for txt, cmd in (("▶ Анімація", self.animate), ("Крок", self.step),
                         ("Миттєво", self.instant), ("Скинути", self.reset)):
            ttk.Button(r, text=txt, command=cmd).pack(side="left", fill="x", expand=True)

        ttk.Button(p, text="Вікно результатів", command=self.show_results).pack(fill="x", pady=6)

        f = ttk.LabelFrame(p, text="Позначення", padding=6)
        f.pack(fill="x", pady=3)
        lg = tk.Canvas(f, width=290, height=146, highlightthickness=0, bg=f.winfo_toplevel()["bg"])
        lg.pack(anchor="w")
        items = [("wall", "free", "непрохідна (-1) / прохідна (0)"),
                 ("ws", None, "хвиля від старту (номер хвилі)"),
                 ("wf", None, "хвиля від мети (номер хвилі)"),
                 ("fs", "ff", "фронт від старту / від мети"),
                 ("meet", None, "точка зустрічі хвиль"),
                 ("path", None, "знайдений шлях"),
                 ("start", "goal", "старт / мета")]
        for i, (k, k2, t) in enumerate(items):
            y = 4 + i * 20
            lg.create_rectangle(4, y, 18, y + 14, fill=C[k], outline=C["grid"])
            x = 26
            if k2:
                lg.create_rectangle(22, y, 36, y + 14, fill=C[k2], outline=C["grid"])
                x = 44
            lg.create_text(x, y + 7, text=t, anchor="w", fill="#212529")

        right = ttk.Frame(self)
        right.pack(side="left", fill="both", expand=True)
        self.cv = tk.Canvas(right, bg="#fbfbf8", highlightthickness=0)
        self.cv.pack(fill="both", expand=True)
        self.cv.bind("<Button-1>", self.press)
        self.cv.bind("<B1-Motion>", self.drag)
        self.cv.bind("<ButtonRelease-1>", lambda e: setattr(self, "paint_value", None))
        self.cv.bind("<Configure>", lambda e: self.redraw())
        self.status = tk.StringVar(value="Оберіть метод і оператор переходу та натисніть «Анімація», «Крок» або «Миттєво».")
        ttk.Label(right, textvariable=self.status, relief="sunken", padding=(6, 2)).pack(fill="x")

    # ---------------- лабіринт ----------------
    def size(self):
        return len(self.grid_m), len(self.grid_m[0])

    def apply_size(self):
        try:
            nr, nc = int(self.sp_r.get()), int(self.sp_c.get())
        except ValueError:
            return
        nr = max(MIN_SIZE, min(MAX_SIZE, nr))
        nc = max(MIN_SIZE, min(MAX_SIZE, nc))
        old = self.grid_m
        self.grid_m = [[old[r][c] if r < len(old) and c < len(old[0]) else 0 for c in range(nc)]
                       for r in range(nr)]
        clamp = lambda rc: (min(rc[0], nr - 1), min(rc[1], nc - 1))
        self.start_c, self.goal_c = clamp(self.start_c), clamp(self.goal_c)
        for r, c in (self.start_c, self.goal_c):
            self.grid_m[r][c] = 0
        self.status.set(f"Розмір лабіринту: {nr} × {nc}.")
        self.reset()

    def clear_walls(self):
        self.grid_m = [[0] * len(row) for row in self.grid_m]
        self.reset()

    def restore(self):
        self.grid_m = default_grid()
        self.start_c, self.goal_c = START, GOAL
        self.reset()

    def geometry_cells(self):
        rows, cols = self.size()
        w, h = max(self.cv.winfo_width(), 200), max(self.cv.winfo_height(), 200)
        s = int(min((w - 20) / cols, (h - 20) / rows, 44))
        ox, oy = (w - s * cols) // 2, (h - s * rows) // 2
        return s, ox, oy

    def cell_at(self, x, y):
        s, ox, oy = self.geometry_cells()
        rows, cols = self.size()
        c, r = (x - ox) // s, (y - oy) // s
        return (int(r), int(c)) if 0 <= r < rows and 0 <= c < cols else None

    def press(self, e):
        cell = self.cell_at(e.x, e.y)
        if cell is None:
            return
        r, c = cell
        m = self.mode.get()
        if m == "wall":
            if cell in (self.start_c, self.goal_c):
                return
            self.paint_value = 0 if self.grid_m[r][c] == -1 else -1
            self.grid_m[r][c] = self.paint_value
        else:
            if self.grid_m[r][c] == -1:
                self.status.set("Вершина має бути на прохідній клітинці (0).")
                return
            if m == "start":
                self.start_c = cell
            else:
                self.goal_c = cell
        self.reset()

    def drag(self, e):
        if self.mode.get() != "wall" or self.paint_value is None:
            return
        cell = self.cell_at(e.x, e.y)
        if cell and cell not in (self.start_c, self.goal_c) and self.grid_m[cell[0]][cell[1]] != self.paint_value:
            self.grid_m[cell[0]][cell[1]] = self.paint_value
            self.reset()

    # ---------------- пошук ----------------
    def prepare(self):
        self.stop()
        op, meth = self.op.get(), self.method.get()
        self.res = SEARCH[meth](self.grid_m, self.start_c, self.goal_c, op)
        rows, cols = self.size()
        walls = sum(row.count(-1) for row in self.grid_m)
        self.res.update(time=search_time_us(self.grid_m, self.start_c, self.goal_c, op, meth),
                        op=OPERATORS[op][0], method=METHODS[meth], start=self.start_c, goal=self.goal_c,
                        size=f"{rows}×{cols}", walls=walls, cells=rows * cols)
        self.shown = 0
        self.done = False

    def show_step(self):
        k = self.shown
        ns = sum(1 for v in self.res["ws"].stage.values() if v == k)
        if self.res["wf"] is None:
            self.status.set(f"Цикл {k}: фронт хвилі від старту — {ns} клітинок")
        else:
            nf = sum(1 for v in self.res["wf"].stage.values() if v == k)
            self.status.set(f"Цикл {k}: фронт від старту — {ns} клітинок, фронт від мети — {nf} клітинок")

    def animate(self):
        self.prepare()
        self.redraw()
        self.job = self.after(self.delay.get(), self.tick)

    def tick(self):
        if self.shown < self.res["cycles"]:
            self.shown += 1
            self.show_step()
            self.redraw()
            self.job = self.after(self.delay.get(), self.tick)
        else:
            self.job = None
            self.finish()

    def step(self):
        self.stop()
        if self.res is None or self.done:
            self.prepare()
            self.status.set("Покроковий режим: кожне натискання «Крок» — один цикл пошуку.")
            self.redraw()
            return
        if self.shown < self.res["cycles"]:
            self.shown += 1
            self.show_step()
            self.redraw()
        else:
            self.finish()

    def instant(self):
        self.prepare()
        self.shown = self.res["cycles"]
        self.finish()

    def finish(self):
        self.done = True
        r = self.res
        self.runs.append(r)
        self.print_run(r)
        if r["path"]:
            meet = f", зустріч у {cell_name(r['meet'])}" if r["meet"] is not None else ""
            self.status.set(f"Шлях знайдено: {len(r['path'])} вершин ({len(r['path']) - 1} кроків), "
                            f"циклів {r['cycles']}, розкрито {r['expanded']} клітинок{meet}.")
        else:
            self.status.set("Шлях не існує: хвиля згасла, не зустрівши іншу хвилю чи мету.")
        self.redraw()
        self.show_results()

    def stop(self):
        if self.job:
            self.after_cancel(self.job)
            self.job = None

    def reset(self):
        self.stop()
        self.res = None
        self.done = False
        self.redraw()

    def print_run(self, r):
        """Рядок результату в консоль (через табуляцію — для вставки в таблицю звіту)."""
        if len(self.runs) == 1:
            print("№\tМетод\tОператор\tРозмір\tСтін\tСтарт→мета\tВершин у шляху\tЦикли\tРозкриті\t"
                  "Час, мкс\tЗустріч\tШлях")
        path = "–".join(cell_name(p) for p in r["path"]) or "не знайдено"
        meet = cell_name(r["meet"]) if r["meet"] is not None else "—"
        print(f"{len(self.runs)}\t{r['method']}\t{r['op']}\t{r['size']}\t{r['walls']}\t"
              f"{cell_name(r['start'])}→{cell_name(r['goal'])}\t{len(r['path']) or '—'}\t{r['cycles']}\t"
              f"{r['expanded']}\t{r['time']:.1f}\t{meet}\t{path}", flush=True)

    # ---------------- малювання ----------------
    def redraw(self):
        rows, cols = self.size()
        walls = sum(row.count(-1) for row in self.grid_m)
        self.info.config(text=f"Розмір {rows} × {cols} = {rows * cols} клітинок\n"
                              f"непрохідних (-1): {walls} ({walls / (rows * cols):.0%})\n"
                              f"прохідних (0): {rows * cols - walls}")
        self.sp_r.set(rows)
        self.sp_c.set(cols)
        cv = self.cv
        cv.delete("all")
        s, ox, oy = self.geometry_cells()
        ws = wf = None
        path = set()
        if self.res:
            ws, wf = self.res["ws"], self.res["wf"]
            if self.done:
                path = set(self.res["path"])
        k = self.shown
        font = ("DejaVu Sans", max(7, s // 3))
        small = ("DejaVu Sans", max(6, s // 4))
        for r in range(rows):
            for c in range(cols):
                x, y = ox + c * s, oy + r * s
                v = self.grid_m[r][c]
                text, fill, tcol = str(v), C["free"], "#adb5bd"
                if v == -1:
                    fill, tcol = C["wall"], "#ced4da"
                else:
                    in_s = ws is not None and ws.stage.get((r, c), k + 1) <= k
                    in_f = wf is not None and wf.stage.get((r, c), k + 1) <= k
                    if in_s:
                        text, fill, tcol = str(ws.mark[r][c]), C["ws"], "#1c3d7a"
                        if ws.stage[(r, c)] == k and k > 0 and not self.done:
                            fill = C["fs"]
                    if in_f:
                        text, fill, tcol = str(wf.mark[r][c]), C["wf"], "#1b5e20"
                        if wf.stage[(r, c)] == k and k > 0 and not self.done:
                            fill = C["ff"]
                    if in_s and in_f:
                        text, fill, tcol = f"{ws.mark[r][c]}|{wf.mark[r][c]}", C["meet"], "#212529"
                    if (r, c) in path and (r, c) != self.res["meet"]:
                        fill, tcol = C["path"], "#212529"
                if (r, c) == self.start_c:
                    fill, tcol = C["start"], "#ffffff"
                if (r, c) == self.goal_c:
                    fill, tcol = C["goal"], "#ffffff"
                cv.create_rectangle(x, y, x + s, y + s, fill=fill, outline=C["grid"])
                cv.create_text(x + s / 2, y + s / 2, text=text, fill=tcol, font=small if "|" in text else font)
        if path and len(self.res["path"]) > 1:
            pts = []
            for r, c in self.res["path"]:
                pts += [ox + c * s + s / 2, oy + r * s + s / 2]
            cv.create_line(*pts, fill="#c92a2a", width=max(2, s // 10))
        for c in range(cols):
            cv.create_text(ox + c * s + s / 2, oy - 7, text=c + 1, fill="#868e96", font=("DejaVu Sans", 8))
        for r in range(rows):
            cv.create_text(ox - 9, oy + r * s + s / 2, text=r + 1, fill="#868e96", font=("DejaVu Sans", 8))

    # ---------------- вікно результатів ----------------
    def show_results(self):
        if not (self.res_win and self.res_win.winfo_exists()):
            w = self.res_win = tk.Toplevel(self)
            w.title("Результати пошуку")
            w.geometry("1300x460")
            self.txt = tk.Text(w, height=11, font=("DejaVu Sans Mono", 10), wrap="word")
            self.txt.pack(fill="x", padx=6, pady=6)
            cols = ("№", "Метод", "Оператор", "Розмір", "Стін", "Старт→мета", "Вершин", "Цикли",
                    "Розкриті", "Час, мкс", "Зустріч", "Шлях")
            widths = (35, 135, 190, 65, 50, 110, 65, 60, 75, 75, 70, 420)
            self.log = ttk.Treeview(w, columns=cols, show="headings")
            for c, wd in zip(cols, widths):
                self.log.heading(c, text=c)
                self.log.column(c, width=wd, anchor="w" if c in ("Шлях", "Оператор", "Метод") else "center")
            self.log.pack(fill="both", expand=True, padx=6, pady=(0, 6))
            self.shown_rows = 0
        for r in self.runs[self.shown_rows:]:
            self.shown_rows += 1
            self.log.insert("", "end", values=(
                self.shown_rows, r["method"], r["op"], r["size"], r["walls"],
                f"{cell_name(r['start'])}→{cell_name(r['goal'])}",
                len(r["path"]) or "—", r["cycles"], r["expanded"], f"{r['time']:.1f}",
                cell_name(r["meet"]) if r["meet"] is not None else "—",
                "–".join(cell_name(p) for p in r["path"]) or "не знайдено"))
        self.txt.delete("1.0", "end")
        r = self.res
        if r:
            self.txt.insert("end", "\n".join([
                f"Метод: {r['method']} хвильовий пошук;  оператор переходу: {r['op']}",
                f"Лабіринт: {r['size']}, непрохідних клітинок {r['walls']} з {r['cells']}",
                f"Старт: {cell_name(r['start'])}   Мета: {cell_name(r['goal'])}",
                "",
                f"Координати вершин шляху: {'–'.join(cell_name(p) for p in r['path']) or 'шлях не існує'}",
                f"Віддаль (кількість вершин шляху): {len(r['path']) or '—'}"
                f"   (кроків: {len(r['path']) - 1 if r['path'] else '—'})",
                f"Точка зустрічі хвиль: {cell_name(r['meet']) if r['meet'] is not None else '—'}",
                f"Кількість циклів: {r['cycles']}",
                f"Кількість розкритих вершин: {r['expanded']}",
                f"Час виконання пошуку: {r['time']:.1f} мкс",
            ]))


if __name__ == "__main__":
    App().mainloop()
