#!/usr/bin/env python3
"""Generate the VectorCraft step list for a grid of coloured squares.

Port of create-color-grid.jsx. VectorCraft runs no scripts, so the loop lives
here and VectorCraft receives a plain list of command steps. The output works
unchanged as:

  * a `vectorcraft-cli run --commands FILE` step file (a JSON array), and
  * the `steps` of the MCP `command_batch` tool (steps use the "id" key,
    which `run` also accepts).

Coordinates are VectorCraft's: points, y pointing down, origin at the first
artboard's top-left. The original measured y up from the bottom
(startY = doc.height - 72), which is y = 72 from the top here.

Usage:
  python3 create-color-grid.py > create-color-grid.json
  python3 create-color-grid.py --columns 8 --rows 6 --seed 42 > grid.json
  vectorcraft-cli run --commands grid.json --export grid.svg

Standard library only.
"""
import argparse
import json
import random


def build_steps(columns, rows, cell, gap, start_x, start_y, seed, new_document):
    rng = random.Random(seed)  # seeded: the same file every run
    steps = []
    if new_document:
        steps.append({"id": "file.new", "params": {}})  # 612 x 792 pt, like documents.add()
    steps.append({"id": "layer.new", "params": {"name": "Color Grid"}})
    for row in range(rows):
        for col in range(columns):
            x = start_x + col * (cell + gap)
            y = start_y + row * (cell + gap)  # y grows downwards
            red = round(col / max(columns - 1, 1) * 255)
            green = round(row / max(rows - 1, 1) * 255)
            blue = round(128 + rng.random() * 127)
            rect = len(steps)  # this step's index, for "$N.id" below
            steps.append({"id": "shape.rectangle",
                          "params": {"x": x, "y": y, "width": cell, "height": cell}})
            steps.append({"id": "paint.setFill",
                          "params": {"id": "$%d.id" % rect,
                                     "color": "#%02x%02x%02x" % (red, green, blue)}})
            steps.append({"id": "paint.setStroke",
                          "params": {"id": "$%d.id" % rect, "none": True}})
    steps.append({"id": "select.none", "params": {}})
    return steps


def main():
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--columns", type=int, default=5)
    p.add_argument("--rows", type=int, default=4)
    p.add_argument("--cell", type=float, default=72, help="square size in pt (72 = 1 in)")
    p.add_argument("--gap", type=float, default=10)
    p.add_argument("--start-x", type=float, default=72)
    p.add_argument("--start-y", type=float, default=72, help="top edge of row 0, from the top")
    p.add_argument("--seed", type=int, default=7)
    p.add_argument("--no-new-document", action="store_true",
                   help="draw into the current document instead of starting one")
    a = p.parse_args()
    if a.columns < 1 or a.rows < 1:
        p.error("--columns and --rows must be at least 1")
    steps = build_steps(a.columns, a.rows, a.cell, a.gap, a.start_x, a.start_y,
                        a.seed, not a.no_new_document)
    if len(steps) > 256:
        # Fine for `run` (100,000 steps); one MCP command_batch takes at most 256.
        import sys
        print("note: %d steps: split them for MCP command_batch (max 256)" % len(steps),
              file=sys.stderr)
    # One step per line: a JSON array that still diffs and reads well.
    print("[\n" + ",\n".join(" " + json.dumps(s) for s in steps) + "\n]")


if __name__ == "__main__":
    main()
