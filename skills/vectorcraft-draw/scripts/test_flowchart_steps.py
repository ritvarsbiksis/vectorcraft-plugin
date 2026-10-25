#!/usr/bin/env python3
"""Tests for flowchart_steps.py (stdlib unittest).

  python3 -I scripts/test_flowchart_steps.py      # from the skill folder

The last test runs the steps through vectorcraft-cli when it is found
($VECTORCRAFT_CLI, PATH or ~/.local/bin) and is skipped otherwise.
"""
import copy
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import flowchart_steps as fs  # noqa: E402

EXAMPLE = os.path.join(HERE, "..", "examples", "order-flow.spec.json")
RETURNS = {"id": {"shape.rectangle", "path.create", "text.create", "object.group", "layer.new"},
           "name": {"swatch.new", "graphicStyle.new"}}


def load_example():
    with open(EXAMPLE, encoding="utf-8") as fh:
        return json.load(fh)


def find_cli():
    for c in (os.environ.get("VECTORCRAFT_CLI"), shutil.which("vectorcraft-cli"),
              os.path.expanduser("~/.local/bin/vectorcraft-cli")):
        if c and os.path.isfile(c) and os.access(c, os.X_OK):
            return c
    return None


class Refs(unittest.TestCase):
    def check_refs(self, steps, base=0):
        for i, st in enumerate(steps):
            for ref in re.findall(r'"\$(\d+)\.(\w+)"', json.dumps(st["params"])):
                n, key = int(ref[0]) - base, ref[1]
                self.assertTrue(0 <= n < i, "step %d refers forward to $%s" % (i, ref[0]))
                self.assertIn(steps[n]["id"], RETURNS[key], "step %d: $%d has no .%s" % (i, n, key))

    def test_example_refs_point_back(self):
        steps, _ = fs.build_steps(load_example())
        self.check_refs(steps)
        self.assertTrue(all(set(s) == {"id", "params"} for s in steps))

    def test_base_offsets_refs(self):
        steps, _ = fs.build_steps(load_example(), base=3)
        self.check_refs(steps, base=3)


class Layout(unittest.TestCase):
    def test_ranks_and_back_edge(self):
        nodes, edges, _, _ = fs.load_spec(load_example())
        rank, back = fs.rank_nodes(nodes, edges)
        self.assertEqual(rank, {"start": 0, "check": 1, "ship": 2, "reorder": 2, "done": 3})
        self.assertEqual([edges[k]["from"] + ">" + edges[k]["to"] for k in back], ["reorder>check"])

    def geometry(self, spec):
        _, info = fs.build_steps(spec)
        return info["boxes"], info["paths"]

    def assert_clean(self, spec):
        boxes, paths = self.geometry(spec)
        bl = list(boxes.values())
        for i, a in enumerate(bl):                       # no two nodes overlap
            for b in bl[i + 1:]:
                self.assertFalse(a["x"] < b["x"] + b["w"] and b["x"] < a["x"] + a["w"]
                                 and a["y"] < b["y"] + b["h"] and b["y"] < a["y"] + a["h"])
        for e, pts, _ in paths:
            for (x0, y0), (x1, y1) in zip(pts, pts[1:]):  # orthogonal elbows only
                self.assertTrue(abs(x0 - x1) < 1e-6 or abs(y0 - y1) < 1e-6, (e, pts))
            for end, node in ((pts[0], e["from"]), (pts[-1], e["to"])):
                b = boxes[node]                          # ends touch their node's box
                self.assertTrue(b["x"] - 0.5 <= end[0] <= b["x"] + b["w"] + 0.5
                                and b["y"] - 0.5 <= end[1] <= b["y"] + b["h"] + 0.5, (e, end))

    def test_tb_clean(self):
        self.assert_clean(load_example())

    def test_lr_clean(self):
        spec = load_example()
        spec["direction"] = "LR"
        self.assert_clean(spec)

    def test_skip_rank_edge_avoids_nodes(self):
        spec = {"nodes": [{"id": "a"}, {"id": "b"}, {"id": "c"}],
                "edges": [{"from": "a", "to": "b"}, {"from": "b", "to": "c"},
                          {"from": "a", "to": "c"}]}
        boxes, paths = self.geometry(spec)
        _, pts, _ = paths[2]
        b = boxes["b"]
        for (x0, y0), (x1, y1) in zip(pts, pts[1:]):     # a->c must not run through b
            inside_x = b["x"] < max(x0, x1) and min(x0, x1) < b["x"] + b["w"]
            inside_y = b["y"] < max(y0, y1) and min(y0, y1) < b["y"] + b["h"]
            self.assertFalse(inside_x and inside_y, pts)
        self.assert_clean(spec)


class Errors(unittest.TestCase):
    def test_bad_specs(self):
        good = load_example()
        for mutate in (lambda s: s["edges"].append({"from": "start", "to": "nowhere"}),
                       lambda s: s["nodes"].append({"id": "start"}),
                       lambda s: s["nodes"][0].update(shape="cloud"),
                       lambda s: s.update(direction="RL"),
                       lambda s: s.update(style={"colour": "red"}),
                       lambda s: s.update(nodes=[])):
            spec = copy.deepcopy(good)
            mutate(spec)
            with self.assertRaises(fs.SpecError):
                fs.build_steps(spec)

    def test_mcp_refuses_over_256_steps(self):
        spec = {"nodes": [{"id": "n%d" % i} for i in range(60)],
                "edges": [{"from": "n%d" % i, "to": "n%d" % (i + 1)} for i in range(59)]}
        with tempfile.TemporaryDirectory() as tmp:
            p = os.path.join(tmp, "big.json")
            with open(p, "w") as fh:
                json.dump(spec, fh)
            self.assertEqual(fs.main([p, "--mcp", "-o", os.path.join(tmp, "o.json")]), 2)
            self.assertEqual(fs.main([p, "-o", os.path.join(tmp, "o.json")]), 0)


@unittest.skipUnless(find_cli(), "vectorcraft-cli not found")
class Headless(unittest.TestCase):
    def test_runs_and_exports(self):
        steps, _ = fs.build_steps(load_example())
        with tempfile.TemporaryDirectory() as tmp:
            sp, svg = os.path.join(tmp, "steps.json"), os.path.join(tmp, "out.svg")
            with open(sp, "w") as fh:
                json.dump(steps, fh)
            r = subprocess.run([find_cli(), "run", "--commands", sp, "--export", svg],
                               capture_output=True, text=True, timeout=120)
            self.assertEqual(r.returncode, 0, r.stderr)
            last = json.loads(r.stdout.strip().splitlines()[-1])
            self.assertEqual(last["result"]["warnings"], [])
            with open(svg, encoding="utf-8") as fh:
                text = fh.read()
            for n in ("start", "check", "ship", "reorder", "done"):
                self.assertIn('data-name="node:%s"' % n, text)
            self.assertEqual(text.count('data-name="edge:'), 5)
            for label in ("Item in stock?", "yes", "no", "restocked"):
                self.assertIn(">%s<" % label, text)


if __name__ == "__main__":
    unittest.main(verbosity=2)
