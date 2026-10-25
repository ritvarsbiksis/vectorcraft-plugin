#!/usr/bin/env python3
"""Turn a small flowchart spec (JSON) into a VectorCraft step file.

Stdlib only. The output is a JSON array of {"id": command, "params": {...}}
steps that both `vectorcraft-cli run --commands FILE` and the MCP tool
`command_batch` accept (`--mcp` wraps it as command_batch arguments).

Spec (JSON):
  {
    "title": "Optional title",           # also the document title (SVG <title>)
    "description": "Optional",           # SVG <desc>; default: the node labels
    "direction": "TB" | "LR",            # top-to-bottom (default) or left-to-right
    "nodes": [{"id": "a", "label": "Text", "shape": "process",
               "rank": 0, "col": 0}],     # shape: terminal|process|decision|io
                                          # rank/col: optional layout overrides
    "edges": [{"from": "a", "to": "b", "label": "yes"}],
    "style": {"fontSize": 11, "font": "Helvetica", ...}   # optional, see STYLE
  }

Layout: nodes are ranked by longest path from the sources (edges that close a
cycle are drawn as back edges in an outer lane), each rank is centred on the
flow axis, connectors are orthogonal elbows ending in a Triangle arrowhead.
Usage:
  flowchart_steps.py spec.json [-o steps.json] [--mcp] [--into-existing]
                     [--origin X,Y] [--base N]
"""
import argparse
import json
import sys
import textwrap

STYLE = {
    "nodeWidth": 140, "nodeHeight": 48,        # process / terminal / io
    "decisionWidth": 156, "decisionHeight": 76,
    "rankGap": 56, "colGap": 40, "margin": 36, "laneGap": 22,
    "fontSize": 11, "edgeFontSize": 9, "titleSize": 16, "font": None,
    "lineWeight": 1.25, "connectorWeight": 1.25,
    "ink": "#0f172a", "connector": "#334155",
    "fills": {"terminal": "#dcfce7", "process": "#e0f2fe",
              "decision": "#fef3c7", "io": "#ede9fe"},
    "lines": {"terminal": "#166534", "process": "#075985",
              "decision": "#92400e", "io": "#5b21b6"},
}
SHAPES = ("terminal", "process", "decision", "io")


class SpecError(ValueError):
    pass


def load_spec(spec):
    nodes = spec.get("nodes") or []
    if not nodes:
        raise SpecError("spec has no nodes")
    ids = [n.get("id") for n in nodes]
    if any(not isinstance(i, str) or not i for i in ids):
        raise SpecError("every node needs a non-empty string id")
    if len(set(ids)) != len(ids):
        raise SpecError("node ids must be unique")
    for n in nodes:
        n.setdefault("label", n["id"])
        n.setdefault("shape", "process")
        if n["shape"] not in SHAPES:
            raise SpecError("node %r: shape must be one of %s" % (n["id"], ", ".join(SHAPES)))
    for e in spec.get("edges") or []:
        for end in ("from", "to"):
            if e.get(end) not in ids:
                raise SpecError("edge %r: unknown node %r" % (e, e.get(end)))
    direction = spec.get("direction", "TB").upper()
    if direction not in ("TB", "LR"):
        raise SpecError("direction must be TB or LR")
    style = dict(STYLE)
    for k, v in (spec.get("style") or {}).items():
        if k not in STYLE:
            raise SpecError("unknown style key %r" % k)
        style[k] = dict(STYLE[k], **v) if isinstance(STYLE[k], dict) else v
    return nodes, list(spec.get("edges") or []), direction, style


def rank_nodes(nodes, edges):
    """Longest-path ranks over the forward edges; returns (ranks, back_edges)."""
    order = [n["id"] for n in nodes]
    out = {i: [] for i in order}
    for k, e in enumerate(edges):
        out[e["from"]].append((e["to"], k))
    state, back = {}, set()

    def dfs(u):                      # iterative DFS: classify cycle-closing edges
        stack = [(u, iter(out[u]))]
        state[u] = 1
        while stack:
            v, it = stack[-1]
            for w, k in it:
                if state.get(w) == 1:
                    back.add(k)
                elif w not in state:
                    state[w] = 1
                    stack.append((w, iter(out[w])))
                    break
            else:
                state[v] = 2
                stack.pop()

    for i in order:
        if i not in state:
            dfs(i)
    rank = {i: 0 for i in order}
    for _ in order:                  # Bellman-style relaxation on a DAG: |V| passes max
        changed = False
        for k, e in enumerate(edges):
            if k not in back and e["from"] != e["to"] and rank[e["to"]] < rank[e["from"]] + 1:
                rank[e["to"]] = rank[e["from"]] + 1
                changed = True
        if not changed:
            break
    fixed = {n["id"]: n["rank"] for n in nodes if "rank" in n}
    rank.update(fixed)
    return rank, back


def wrap_label(text, width, size):
    per_line = max(4, int((width - 16) / (0.55 * size)))
    lines = []
    for para in str(text).split("\n"):
        lines.extend(textwrap.wrap(para, per_line) or [""])
    return lines


def layout(nodes, edges, direction, style):
    rank, back = rank_nodes(nodes, edges)
    tb = direction == "TB"
    lead = style["fontSize"] * 1.2
    geo = {}
    for n in nodes:
        dec = n["shape"] == "decision"
        w = style["decisionWidth"] if dec else style["nodeWidth"]
        h = style["decisionHeight"] if dec else style["nodeHeight"]
        lines = wrap_label(n["label"], w * (0.7 if dec else 1), style["fontSize"])
        h = max(h, len(lines) * lead + (34 if dec else 16))
        # flow space: v runs along the flow, u across it
        geo[n["id"]] = {"w": w, "h": h, "lines": lines, "shape": n["shape"],
                        "fl": (h if tb else w) / 2, "cr": (w if tb else h) / 2}
    ranks = sorted(set(rank.values()))
    by_rank = {r: [n["id"] for n in nodes if rank[n["id"]] == r] for r in ranks}
    pitch = max(g["cr"] for g in geo.values()) * 2 + style["colGap"]
    v = 0.0
    for r in ranks:
        band = max(geo[i]["fl"] for i in by_rank[r]) * 2
        members = by_rank[r]
        for slot, i in enumerate(members):
            node = next(n for n in nodes if n["id"] == i)
            col = node.get("col", slot - (len(members) - 1) / 2.0)
            geo[i]["u"] = col * pitch
            geo[i]["v"] = v + band / 2
            geo[i]["rank"] = r
        v += band + style["rankGap"]

    def blocked(u, r0, r1, skip=()):
        lo, hi = min(r0, r1), max(r0, r1)
        return any(lo < g["rank"] < hi and abs(g["u"] - u) < g["cr"] + 6
                   for i, g in geo.items() if i not in skip)

    def row_blocked(r, u0, u1, skip):
        lo, hi = min(u0, u1), max(u0, u1)
        return any(g["rank"] == r and i not in skip and lo - g["cr"] < g["u"] < hi + g["cr"]
                   for i, g in geo.items())

    for g in geo.values():           # port offsets: io's slanted sides sit inside its box
        slant = 0.175 * g["h"] if g["shape"] == "io" else 0
        g["sd"] = g["cr"] - (slant if tb else 0)
        g["en"] = g["fl"] - (0 if tb else slant)
    outer = max(g["u"] + g["cr"] for g in geo.values())
    gap = style["rankGap"]
    state = {"lanes": 0}
    used = set()                     # (node, side) ports already taken by an exit

    def lane():
        state["lanes"] += 1
        return outer + style["laneGap"] * state["lanes"]

    def around(s, d):                # out of the end port, round the outer lane, into the start
        ln, a, b = lane(), s["v"] + s["en"] + gap / 2, d["v"] - d["en"] - gap / 2
        return [(s["u"], s["v"] + s["en"]), (s["u"], a), (ln, a), (ln, b), (d["u"], b),
                (d["u"], d["v"] - d["en"])]

    routes = {}
    is_back = [k in back or e["from"] == e["to"]
               or geo[e["to"]]["rank"] <= geo[e["from"]]["rank"] for k, e in enumerate(edges)]
    for k, e in enumerate(edges):    # forward edges first, so back edges see the used ports
        if is_back[k]:
            continue
        s, d = geo[e["from"]], geo[e["to"]]
        s_end, d_start = s["v"] + s["en"], d["v"] - d["en"]
        du = d["u"] - s["u"]
        if abs(du) < 0.5:
            pts = ([(s["u"], s_end), (d["u"], d_start)]
                   if not blocked(s["u"], s["rank"], d["rank"]) else around(s, d))
        elif (s["shape"] == "decision" and not blocked(d["u"], s["rank"], d["rank"])
              and not row_blocked(s["rank"], s["u"], d["u"], (e["from"],))):
            side = 1 if du > 0 else -1   # leave a decision from its side tip
            used.add((e["from"], side))
            pts = [(s["u"] + side * s["sd"], s["v"]), (d["u"], s["v"]), (d["u"], d_start)]
        elif not blocked(s["u"], s["rank"], d["rank"]):
            t = d_start - gap / 2
            pts = [(s["u"], s_end), (s["u"], t), (d["u"], t), (d["u"], d_start)]
        elif not blocked(d["u"], s["rank"], d["rank"]):
            t = s_end + gap / 2
            pts = [(s["u"], s_end), (s["u"], t), (d["u"], t), (d["u"], d_start)]
        else:
            pts = around(s, d)
        routes[k] = pts
    for k, e in enumerate(edges):    # back edges: out of the source's far side, up the lane
        if not is_back[k]:
            continue
        s, d = geo[e["from"]], geo[e["to"]]
        ln = lane()
        pts = [(s["u"] + s["sd"], s["v"]), (ln, s["v"])]
        if (e["to"], 1) not in used:
            pts += [(ln, d["v"]), (d["u"] + d["sd"], d["v"])]
            used.add((e["to"], 1))
        else:                        # side taken: join the line into the start port
            b = d["v"] - d["en"] - gap / 2
            pts += [(ln, b), (d["u"], b), (d["u"], d["v"] - d["en"])]
        routes[k] = pts
    routes = [(e, routes[k], is_back[k]) for k, e in enumerate(edges)]

    def to_xy(u, vv):
        return (u, vv) if tb else (vv, u)

    boxes = {}
    for i, g in geo.items():
        cx, cy = to_xy(g["u"], g["v"])
        boxes[i] = dict(g, cx=cx, cy=cy, x=cx - g["w"] / 2, y=cy - g["h"] / 2)
    paths = [(e, [to_xy(*p) for p in pts], bk) for e, pts, bk in routes]
    return boxes, paths


def label_spot(pts, label, size, back=False):
    """(x, y, justify) for an edge label: by the source port on the first segment,
    or, for a back edge, beside the middle of its longest segment (the lane)."""
    (x0, y0), (x1, y1) = pts[0], pts[1]
    if not back:
        if abs(x0 - x1) < 0.5:       # vertical: right of the line, just past the port
            return x0 + 5, (y0 + 4 + size if y1 > y0 else y0 - 6), "left"
        return (x0 + 5, y0 - 5, "left") if x1 > x0 else (x0 - 5, y0 - 5, "right")
    (x0, y0), (x1, y1) = max(zip(pts, pts[1:]),
                             key=lambda g: abs(g[1][0] - g[0][0]) + abs(g[1][1] - g[0][1]))
    if abs(x0 - x1) < 0.5:
        return x0 + 5, (y0 + y1) / 2 + size / 3, "left"
    return (x0 + x1) / 2, y0 + size + 3, "center"


def label_box(x, y, label, size, justify):
    """Rough bounds of a label (for sizing the artboard): x0, y0, x1, y1."""
    lines = label.split("\n")
    w = 0.55 * size * max(len(t) for t in lines)
    x0 = {"left": x, "right": x - w}.get(justify, x - w / 2)
    return x0, y - size, x0 + w, y + 1.2 * size * (len(lines) - 1) + size * 0.3


def r2(x):
    return round(x, 2)


def shape_step(b):
    x, y, w, h = b["x"], b["y"], b["w"], b["h"]
    if b["shape"] in ("process", "terminal"):
        radius = h / 2 if b["shape"] == "terminal" else 6
        return {"id": "shape.rectangle", "params": {"x": r2(x), "y": r2(y), "width": r2(w),
                                                    "height": r2(h), "radius": r2(radius)}}
    if b["shape"] == "decision":
        cx, cy = b["cx"], b["cy"]
        d = "M%s %s L%s %s L%s %s L%s %s Z" % (r2(cx), r2(y), r2(x + w), r2(cy),
                                               r2(cx), r2(y + h), r2(x), r2(cy))
    else:  # io: parallelogram
        s = h * 0.35
        d = "M%s %s L%s %s L%s %s L%s %s Z" % (r2(x + s), r2(y), r2(x + w), r2(y),
                                               r2(x + w - s), r2(y + h), r2(x), r2(y + h))
    return {"id": "path.create", "params": {"d": d}}


def build_steps(spec, into_existing=False, origin=(0.0, 0.0), base=0):
    nodes, edges, direction, style = load_spec(spec)
    boxes, paths = layout(nodes, edges, direction, style)
    title = spec.get("title")
    m = style["margin"]
    labels = [(e,) + label_spot(pts, str(e["label"]), style["edgeFontSize"], bk)
              for e, pts, bk in paths if e.get("label")]
    lboxes = [label_box(x, y, str(e["label"]), style["edgeFontSize"], j) for e, x, y, j in labels]
    xs = ([b["x"] for b in boxes.values()] + [p[0] for _, pts, _ in paths for p in pts]
          + [lb[0] for lb in lboxes])
    ys = ([b["y"] for b in boxes.values()] + [p[1] for _, pts, _ in paths for p in pts]
          + [lb[1] for lb in lboxes])
    xe = [b["x"] + b["w"] for b in boxes.values()] + [lb[2] for lb in lboxes] + xs
    ye = [b["y"] + b["h"] for b in boxes.values()] + [lb[3] for lb in lboxes] + ys
    top = style["titleSize"] * 2 if title else 0
    dx = origin[0] + m - min(xs) if not into_existing else origin[0] - min(xs)
    dy = origin[1] + m + top - min(ys) if not into_existing else origin[1] + top - min(ys)
    width, height = max(xe) - min(xs) + 2 * m, max(ye) - min(ys) + 2 * m + top

    steps = []

    def add(cmd, params):
        steps.append({"id": cmd, "params": params})
        return "$%d" % (base + len(steps) - 1)

    def text(x, y, size, lines, justify="center"):
        p = {"x": r2(x), "y": r2(y), "text": "\n".join(lines), "size": size,
             "justify": justify, "color": style["ink"]}
        if style["font"]:
            p["font"] = style["font"]
        return add("text.create", p)

    if not into_existing:
        add("artboard.setProps", {"index": 0, "x": r2(origin[0]), "y": r2(origin[1]),
                                  "width": r2(width), "height": r2(height)})
        if title:                    # becomes the SVG <title>/<desc> and PDF metadata
            desc = spec.get("description") or "Flowchart: " + ", ".join(
                str(n["label"]).replace("\n", " ") for n in nodes)[:400]
            add("file.info", {"title": title, "description": desc})
        add("layer.setProps", {"name": "Connectors"})
    else:
        add("layer.new", {"name": "Connectors"})
    sw = {}
    sw["line"] = add("swatch.new", {"name": "Flow Connector", "color": style["connector"], "global": True})
    for kind in SHAPES:
        if any(n["shape"] == kind for n in nodes):
            sw[kind + "F"] = add("swatch.new", {"name": "Flow %s Fill" % kind.title(),
                                                "color": style["fills"][kind], "global": True})
            sw[kind + "L"] = add("swatch.new", {"name": "Flow %s Line" % kind.title(),
                                                "color": style["lines"][kind], "global": True})

    # connectors first, on the bottom layer
    edge_ids = []
    conn_style = None
    for e, pts, _ in paths:
        pts = [(x + dx, y + dy) for x, y in pts]
        d = "M" + " L".join("%s %s" % (r2(x), r2(y)) for x, y in pts)
        ref = add("path.create", {"d": d})
        add("object.setProps", {"id": ref + ".id", "name": "edge:%s->%s" % (e["from"], e["to"])})
        if conn_style is None:
            add("paint.setFill", {"ids": [ref + ".id"], "none": True})
            add("paint.setStroke", {"ids": [ref + ".id"], "swatch": sw["line"] + ".name"})
            add("stroke.set", {"ids": [ref + ".id"], "weight": style["connectorWeight"],
                               "join": "round", "endArrow": "Triangle", "arrowAlign": "tip"})
            conn_style = add("graphicStyle.new", {"id": ref + ".id", "name": "Flow Connector"})
        else:
            edge_ids.append(ref + ".id")
    if edge_ids:
        add("graphicStyle.apply", {"name": conn_style + ".name", "ids": edge_ids})

    add("layer.new", {"name": "Nodes"})
    lead = style["fontSize"] * 1.2
    first_of = {}
    styled = {k: [] for k in SHAPES}
    for n in nodes:
        b = boxes[n["id"]]
        b = dict(b, x=b["x"] + dx, y=b["y"] + dy, cx=b["cx"] + dx, cy=b["cy"] + dy)
        st = shape_step(b)
        shp = add(st["id"], st["params"])
        kind = n["shape"]
        if kind not in first_of:
            add("paint.setFill", {"ids": [shp + ".id"], "swatch": sw[kind + "F"] + ".name"})
            add("paint.setStroke", {"ids": [shp + ".id"], "swatch": sw[kind + "L"] + ".name"})
            add("stroke.set", {"ids": [shp + ".id"], "weight": style["lineWeight"], "join": "round"})
            first_of[kind] = add("graphicStyle.new", {"id": shp + ".id",
                                                      "name": "Flow %s" % kind.title()})
        else:
            styled[kind].append(shp + ".id")
        lines = b["lines"]
        base_y = b["cy"] + style["fontSize"] / 3 - (len(lines) - 1) * lead / 2
        txt = text(b["cx"], base_y, style["fontSize"], lines)
        grp = add("object.group", {"ids": [shp + ".id", txt + ".id"]})
        add("object.setProps", {"id": grp + ".id", "name": "node:%s" % n["id"]})
    for kind, ids in styled.items():
        if ids:
            add("graphicStyle.apply", {"name": first_of[kind] + ".name", "ids": ids})

    if labels or title:
        add("layer.new", {"name": "Labels"})
    for e, x, y, just in labels:
        lines = str(e["label"]).split("\n")
        t = text(x + dx, y + dy, style["edgeFontSize"], lines, just)
        add("object.setProps", {"id": t + ".id", "name": "label:%s->%s" % (e["from"], e["to"])})
    if title:
        x0 = origin[0] + (m if not into_existing else 0)
        t = text(x0, origin[1] + (m if not into_existing else 0) + style["titleSize"],
                 style["titleSize"], [title], "left")
        add("object.setProps", {"id": t + ".id", "name": "title"})
    return steps, {"width": r2(width), "height": r2(height), "boxes": boxes, "paths": paths,
                   "offset": (dx, dy)}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("spec", help="spec JSON file, or - for standard input")
    ap.add_argument("-o", "--out", help="write the steps here (default: standard output)")
    ap.add_argument("--mcp", action="store_true",
                    help="wrap as command_batch arguments {atomic, label, steps}")
    ap.add_argument("--into-existing", action="store_true",
                    help="draw into the open document: no artboard resize, new layers only")
    ap.add_argument("--origin", default="0,0", help="top-left of the drawing, X,Y in pt")
    ap.add_argument("--base", type=int, default=0,
                    help="index of the first step when other steps run before these ($N refs)")
    a = ap.parse_args(argv)
    try:
        if a.spec == "-":
            spec = json.load(sys.stdin)
        else:
            with open(a.spec, encoding="utf-8") as fh:
                spec = json.load(fh)
        ox, oy = (float(v) for v in a.origin.split(","))
        steps, info = build_steps(spec, a.into_existing, (ox, oy), a.base)
    except (SpecError, ValueError, OSError) as exc:
        print("flowchart_steps: %s" % exc, file=sys.stderr)
        return 2
    if a.mcp and len(steps) > 256:
        print("flowchart_steps: %d steps exceed command_batch's 256; use vectorcraft-cli run"
              % len(steps), file=sys.stderr)
        return 2
    doc = {"atomic": True, "label": spec.get("title") or "Flowchart", "steps": steps} if a.mcp else steps
    text = json.dumps(doc, indent=1, ensure_ascii=False) + "\n"
    if a.out:
        with open(a.out, "w", encoding="utf-8") as fh:
            fh.write(text)
    else:
        sys.stdout.write(text)
    print("flowchart_steps: %d steps, drawing %sx%s pt" % (len(steps), info["width"], info["height"]),
          file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
