#!/usr/bin/env python3
from __future__ import annotations

import math
import sys
from io import BytesIO
from typing import List, Tuple

import requests
import re
from PIL import Image, ImageDraw


def fetch_contributions_svg(username: str) -> str:
    url = f"https://github.com/users/{username}/contributions"
    r = requests.get(url, timeout=15)
    r.raise_for_status()
    return r.text


def parse_cells(svg_html: str) -> List[Tuple[int, int, str]]:
    # Extract SVG block
    m = re.search(r"(<svg[\s\S]*?</svg>)", svg_html, re.IGNORECASE)
    if not m:
        raise SystemExit("Could not find contributions SVG on the page")
    svg = m.group(1)
    rects = re.findall(r"<rect[^>]+>", svg)
    cells = []
    for r in rects:
        # extract x, y, fill
        mx = re.search(r"x=[\"']?([0-9.]+)[\"']?", r)
        my = re.search(r"y=[\"']?([0-9.]+)[\"']?", r)
        mf = re.search(r"fill=[\"']?(#[0-9a-fA-F]{3,6}|[a-zA-Z0-9()#,%]+)[\"']?", r)
        if not (mx and my and mf):
            continue
        try:
            x = int(float(mx.group(1)))
            y = int(float(my.group(1)))
            fill = mf.group(1)
            cells.append((x, y, fill))
        except Exception:
            continue
    if not cells:
        raise SystemExit("No rect cells parsed from SVG")
    xs = sorted(sorted({c[0] for c in cells}))
    ys = sorted(sorted({c[1] for c in cells}))
    grid = []
    for x in xs:
        col = [c for c in cells if c[0] == x]
        col_sorted = sorted(col, key=lambda t: t[1])
        for y, _, fill in col_sorted:
            grid.append((xs.index(x), ys.index(y), fill))
    return grid


def build_path(grid: List[Tuple[int, int, str]], cols: int, rows: int) -> List[Tuple[int, int, str]]:
    # Visit column by column, top-to-bottom (simple snake)
    path = []
    for cx in range(cols):
        for ry in range(rows):
            # find matching cell
            for g in grid:
                if g[0] == cx and g[1] == ry:
                    path.append((g[0], g[1], g[2]))
                    break
    return path


def render_snake(path: List[Tuple[int, int, str]], cols: int, rows: int, out_path: str, cell_size: int = 16, gap: int = 4, trail: int = 12, fps: int = 12, neon_color: str = '#7c3aed', bg_colors: List[str] = None):
    w = cols * (cell_size + gap) + gap
    h = rows * (cell_size + gap) + gap
    frames = []
    visited_colors: List[str] = []
    positions = [(p[0], p[1]) for p in path]
    colors = [p[2] for p in path]
    total = len(path)
    if bg_colors is None:
        bg_colors = ['#ebedf0', '#eeeeee', 'transparent']
    # snake_color holds the current drawing color; defaults to neon_color
    snake_color = neon_color
    for i in range(total + trail):
        im = Image.new("RGBA", (w, h), (10, 10, 10, 255))
        draw = ImageDraw.Draw(im)
        # draw base grid
        for idx, (cx, ry, fill) in enumerate(path):
            x = gap + cx * (cell_size + gap)
            y = gap + ry * (cell_size + gap)
            draw.rectangle([x, y, x + cell_size, y + cell_size], fill=fill)

        # draw snake trail
        head_idx = min(i, total - 1)
        visited_range = range(max(0, i - trail + 1), min(i + 1, total))
        for t_idx, step in enumerate(visited_range):
            idx0 = step
            cx, ry = positions[idx0]
            color = colors[idx0]
            # if the visited square has a non-background color, update snake_color
            if color.lower() not in [c.lower() for c in bg_colors]:
                snake_color = color
            else:
                # otherwise keep neon base
                snake_color = neon_color
            x = gap + cx * (cell_size + gap) + cell_size // 2
            y = gap + ry * (cell_size + gap) + cell_size // 2
            radius = int(cell_size * (1 - (t_idx / max(1, trail)) * 0.6))
            draw.ellipse([x - radius, y - radius, x + radius, y + radius], fill=snake_color)

        frames.append(im.convert("P", palette=Image.ADAPTIVE))

    # save as GIF
    frames[0].save(out_path, save_all=True, append_images=frames[1:], loop=0, duration=int(1000 / fps), optimize=True)


def main(username: str, out_path: str = "snake.gif"):
    html = fetch_contributions_svg(username)
    grid = parse_cells(html)
    if not grid:
        raise SystemExit("No contribution cells parsed")
    cols = max(c[0] for c in grid) + 1
    rows = max(c[1] for c in grid) + 1
    path = build_path(grid, cols, rows)
    render_snake(path, cols, rows, out_path)
    print("Wrote", out_path)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("username")
    parser.add_argument("out", nargs="?", default="snake.gif")
    parser.add_argument("--neon", default="#7c3aed", help="Fallback neon color")
    parser.add_argument("--bg", nargs="*", default=["#ebedf0", "#eeeeee", "transparent"], help="Background colors to ignore")
    parser.add_argument("--cell-size", type=int, default=14)
    parser.add_argument("--gap", type=int, default=4)
    parser.add_argument("--trail", type=int, default=12)
    parser.add_argument("--fps", type=int, default=12)
    args = parser.parse_args()
    html = fetch_contributions_svg(args.username)
    grid = parse_cells(html)
    if not grid:
        raise SystemExit("No contribution cells parsed")
    cols = max(c[0] for c in grid) + 1
    rows = max(c[1] for c in grid) + 1
    path = build_path(grid, cols, rows)
    render_snake(path, cols, rows, args.out, cell_size=args.cell_size, gap=args.gap, trail=args.trail, fps=args.fps, neon_color=args.neon, bg_colors=args.bg)
    print("Wrote", args.out)
