# Diagram recipes

Four worked recipes, each run end to end on `vectorcraft-cli 0.16.0` (headless) with empty
`warnings` on every export unless noted. Coordinates are points, y down, origin at artboard 0's
top-left. Step lists use the step-file shape `{"command"|"id": ..., "params": ...}`; the same
list goes into MCP `command_batch {atomic: true, label, steps}` unchanged, except that
`draw_path` / `draw_shape` steps work **only** inside `command_batch` (the CLI answers
`unknown command draw_path`).

Contents: 1 flowchart from data, 2 architecture diagram by hand over MCP, 3 technical drawing
with dimensions to DXF, 4 timeline plus chart, then notes for org charts, swimlanes, wireframes,
floor plans and icons.

---

## 1. Flowchart from data (generator)

Spec: `examples/order-flow.spec.json` (5 nodes: terminal, decision, process, io, terminal; 5
edges including a loop back and two labelled decision exits).

```sh
python3 scripts/flowchart_steps.py examples/order-flow.spec.json -o steps.json
#   flowchart_steps: 74 steps, drawing 430.0x492.0 pt
vectorcraft-cli run --commands steps.json \
  --export flow.svg --export flow.pdf --export flow.png --export flow.dxf --scale 2
```

What came out: 4 export lines, all `"warnings":[]`. The SVG has layers `Connectors`, `Nodes`,
`Labels`; groups `node:start` ... `node:done`; paths `edge:start->check` ...; every label as a
`<tspan>`. `vectorcraft-cli info flow.pdf` reports 5 groups, 9 type objects, font Source Sans 3.

Same chart over MCP as one undo step:

```sh
python3 scripts/flowchart_steps.py examples/order-flow.spec.json --mcp -o batch.json
```

then call `command_run {id: "file.new", params: {}}` (only if you want a fresh document), and
`command_batch` with the contents of `batch.json` as its arguments. Tested: `completed: 74`,
`history: ["Order handling"]`, and one `undo` returns the document to empty.

To restyle afterwards: `swatch.edit {name: "Flow Process Fill", color: "#fde68a"}` recolours every
process box (they link to the global swatch); `graphicStyle.redefine` or a new
`graphicStyle.apply` changes the connector look in one step.

---

## 2. Architecture diagram by hand (MCP)

Plan on paper first: one row of services at `cy = 90`, column centres 90 / 250 / 410 / 570
(box width 120, gap 40), a queue one row lower at `cy = 190`. Boxes are `x = cx - 60`,
`y = cy - 24`; label baselines `cy + 11/3`. Connectors run from a box's right edge (`cx + 60`) to
the next box's left edge. The database is a cylinder from two SVG arcs (`A` is supported in
`d`). Synchronous calls get a graphic style; the async event is dashed with an open arrowhead.

```json
{"atomic": true, "label": "Architecture", "steps": [
 {"id": "artboard.setProps", "params": {"index": 0, "x": 0, "y": 0, "width": 660, "height": 250}},
 {"id": "layer.setProps", "params": {"name": "Connectors"}},
 {"id": "draw_path", "params": {"d": "M150 90 L190 90", "fill": "none", "stroke": "#334155", "strokeWidth": 1.25, "name": "edge:browser->gateway"}},
 {"id": "stroke.set", "params": {"ids": ["$2.id"], "endArrow": "Triangle", "arrowAlign": "tip"}},
 {"id": "graphicStyle.new", "params": {"id": "$2.id", "name": "Sync call"}},
 {"id": "draw_path", "params": {"d": "M310 90 L350 90", "name": "edge:gateway->orders"}},
 {"id": "draw_path", "params": {"d": "M470 90 L520 90", "name": "edge:orders->db"}},
 {"id": "graphicStyle.apply", "params": {"name": "$4.name", "ids": ["$5.id", "$6.id"]}},
 {"id": "draw_path", "params": {"d": "M410 114 L410 166", "fill": "none", "stroke": "#334155", "strokeWidth": 1.25, "dash": [4, 3], "name": "edge:orders->queue"}},
 {"id": "stroke.set", "params": {"ids": ["$8.id"], "endArrow": "ArrowOpen", "arrowAlign": "tip"}},
 {"id": "layer.new", "params": {"name": "Nodes"}},
 {"id": "draw_shape", "params": {"shape": "rectangle", "x": 30, "y": 66, "width": 120, "height": 48, "radius": 6, "fill": "#f8fafc", "stroke": "#475569", "strokeWidth": 1.25}},
 {"id": "text.create", "params": {"x": 90, "y": 93.67, "text": "Browser", "size": 11, "justify": "center", "color": "#0f172a"}},
 {"id": "object.group", "params": {"ids": ["$11.id", "$12.id"]}},
 {"id": "object.setProps", "params": {"id": "$13.id", "name": "node:browser"}},
 {"id": "draw_shape", "params": {"shape": "rectangle", "x": 190, "y": 66, "width": 120, "height": 48, "radius": 6, "fill": "#e0f2fe", "stroke": "#075985", "strokeWidth": 1.25}},
 {"id": "text.create", "params": {"x": 250, "y": 93.67, "text": "API gateway", "size": 11, "justify": "center", "color": "#0f172a"}},
 {"id": "object.group", "params": {"ids": ["$15.id", "$16.id"]}},
 {"id": "object.setProps", "params": {"id": "$17.id", "name": "node:gateway"}},
 {"id": "draw_shape", "params": {"shape": "rectangle", "x": 350, "y": 66, "width": 120, "height": 48, "radius": 6, "fill": "#e0f2fe", "stroke": "#075985", "strokeWidth": 1.25}},
 {"id": "text.create", "params": {"x": 410, "y": 93.67, "text": "Orders service", "size": 11, "justify": "center", "color": "#0f172a"}},
 {"id": "object.group", "params": {"ids": ["$19.id", "$20.id"]}},
 {"id": "object.setProps", "params": {"id": "$21.id", "name": "node:orders"}},
 {"id": "draw_path", "params": {"d": "M520 66 A50 8 0 0 1 620 66 L620 114 A50 8 0 0 1 520 114 Z", "fill": "#fef3c7", "stroke": "#92400e", "strokeWidth": 1.25}},
 {"id": "draw_path", "params": {"d": "M520 66 A50 8 0 0 0 620 66", "fill": "none", "stroke": "#92400e", "strokeWidth": 1.25}},
 {"id": "text.create", "params": {"x": 570, "y": 97.67, "text": "Postgres", "size": 11, "justify": "center", "color": "#0f172a"}},
 {"id": "object.group", "params": {"ids": ["$23.id", "$24.id", "$25.id"]}},
 {"id": "object.setProps", "params": {"id": "$26.id", "name": "node:db"}},
 {"id": "draw_shape", "params": {"shape": "rectangle", "x": 350, "y": 166, "width": 120, "height": 48, "radius": 6, "fill": "#ede9fe", "stroke": "#5b21b6", "strokeWidth": 1.25, "dash": [4, 3]}},
 {"id": "text.create", "params": {"x": 410, "y": 193.67, "text": "Order events queue", "size": 11, "justify": "center", "color": "#0f172a"}},
 {"id": "object.group", "params": {"ids": ["$28.id", "$29.id"]}},
 {"id": "object.setProps", "params": {"id": "$30.id", "name": "node:queue"}},
 {"id": "select.set", "params": {"ids": ["$13.id", "$17.id", "$21.id", "$26.id"]}},
 {"id": "object.align", "params": {"vertical": "center", "to": "selection"}},
 {"id": "layer.new", "params": {"name": "Labels"}},
 {"id": "text.create", "params": {"x": 170, "y": 84, "text": "HTTPS", "size": 8, "justify": "center", "color": "#475569"}},
 {"id": "text.create", "params": {"x": 415, "y": 143, "text": "async", "size": 8, "justify": "left", "color": "#475569"}},
 {"id": "text.create", "params": {"x": 30, "y": 40, "text": "Checkout architecture", "size": 16, "color": "#0f172a"}},
 {"id": "select.none", "params": {}}
]}
```

Tested: `completed: 39, failed: 0`, then `export {path: ".../arch.png", scale: 2}` and an SVG
export, both with empty warnings. Notes:

- `$4.name` uses the name `graphicStyle.new` actually gave (it appends a number when the name is
  taken), and the style carries the arrowhead, so steps 5 and 6 needed no paint of their own.
- `object.align` here is a safety net (the row was computed aligned); it is the tool to use when
  boxes came from different sources. For even gaps use `object.distributeSpacing`.
- For network diagrams, swap boxes for `shape.ellipse` / `shape.polygon {sides: 6}` and keep the
  same port arithmetic (an ellipse's ports are the ends of its axes).

---

## 3. Technical drawing with dimensions, to DXF

A 100 x 60 mm plate with 7 mm corner radius and a 10 mm hole, on a 160 x 110 mm sheet. Convert
millimetres with `pt = mm * 72 / 25.4` (1 mm = 2.8346 pt). Part geometry and dimensions go on
separate layers so CAD users can switch them.

```json
[
 {"id": "file.new", "params": {"width": "160 mm", "height": "110 mm", "units": "Millimeters", "name": "Bracket plate"}},
 {"id": "layer.setProps", "params": {"name": "Part"}},
 {"id": "shape.rectangle", "params": {"x": 85.04, "y": 56.69, "width": 283.46, "height": 170.08, "radius": 14.17}},
 {"id": "paint.setFill", "params": {"ids": ["$2.id"], "none": true}},
 {"id": "stroke.set", "params": {"ids": ["$2.id"], "weight": 0.7}},
 {"id": "shape.ellipse", "params": {"x": 113.39, "y": 85.04, "width": 28.35, "height": 28.35}},
 {"id": "paint.setFill", "params": {"ids": ["$5.id"], "none": true}},
 {"id": "stroke.set", "params": {"ids": ["$5.id"], "weight": 0.7}},
 {"id": "layer.new", "params": {"name": "Dimensions"}},
 {"id": "dimension.create", "params": {"mode": "linear", "a": [85.04, 226.77], "b": [368.5, 226.77], "offset": 28, "options": {"units": "mm", "precision": 0, "arrowStyle": "filled", "fontSize": 8}}},
 {"id": "dimension.create", "params": {"mode": "linear", "a": [368.5, 56.69], "b": [368.5, 226.77], "offset": -28, "options": {"units": "mm", "precision": 0, "fontSize": 8}}},
 {"id": "dimension.create", "params": {"mode": "diameter", "source": {"kind": "circle", "node": "$5.id"}, "options": {"units": "mm", "precision": 1, "fontSize": 8}}}
]
```

```sh
vectorcraft-cli run --commands plate.json --export plate.pdf --export plate.dxf \
  --cmd document.exportDxf --params '{"path":"plate-r12.dxf","version":"R12","preserve":"editability"}'
```

Results: the three dimensions return labels `"100 mm"`, `"60 mm"`, `"10.0 mm"`. Offset sign: a
positive offset sits on the right-hand side of the a-to-b direction, so the left-to-right width
dimension with `+28` lands below the part and the top-to-bottom height dimension needs `-28` to
land on the right.

- **Linked dimensions** follow the geometry: give `source: {kind: "segment", edge: {node: id,
  subpath: 0, segment: 0}}` instead of `a`/`b`; after `path.moveAnchor` shortened the measured
  line from 100 mm, its dimension read `80.1 mm` with no further step.
- **Drawing scale**: `options.scale: "1:50"` makes 100 pt read `1.76 m` (with `units: "m"`), for
  floor plans and site plans.
- **DXF defaults** (`.dxf` / `document.exportDxf {}`): version 2018 (`AC1032`), unit mm, DXF layers
  `Part` and `Dimensions`, the hole as a native `CIRCLE`, type outlined, no warnings.
- **DXF R12 + `preserve: "editability"`**: type stays `TEXT`, but three warnings: indexed
  colours only before 2004, arrowheads/width profiles dropped ("Maximize Editability writes
  strokes as lines"), and fills on whole type objects left out. Choose by the consumer: laser and
  cutter software wants the default; a CAD user who edits text wants editability.
- Hidden lines, centre lines: `stroke.set {dash: [6, 2, 1, 2]}` on their own layer.

---

## 4. Timeline plus chart

A roadmap line with four milestones spaced evenly by `object.distribute`, labels above, and a
two-series column chart recoloured series by series.

```json
[
 {"command": "artboard.setProps", "params": {"index": 0, "x": 0, "y": 0, "width": 600, "height": 420}},
 {"command": "layer.setProps", "params": {"name": "Timeline"}},
 {"command": "shape.line", "params": {"x1": 40, "y1": 90, "x2": 560, "y2": 90}},
 {"command": "stroke.set", "params": {"ids": ["$2.id"], "weight": 2, "cap": "round", "endArrow": "Arrow", "arrowAlign": "tip"}},
 {"command": "paint.setStroke", "params": {"ids": ["$2.id"], "color": "#334155"}},
 {"command": "shape.ellipse", "params": {"x": 54, "y": 84, "width": 12, "height": 12}},
 {"command": "shape.ellipse", "params": {"x": 90, "y": 84, "width": 12, "height": 12}},
 {"command": "shape.ellipse", "params": {"x": 120, "y": 84, "width": 12, "height": 12}},
 {"command": "shape.ellipse", "params": {"x": 494, "y": 84, "width": 12, "height": 12}},
 {"command": "paint.setFill", "params": {"ids": ["$5.id", "$6.id", "$7.id", "$8.id"], "color": "#0ea5e9"}},
 {"command": "paint.setStroke", "params": {"ids": ["$5.id", "$6.id", "$7.id", "$8.id"], "color": "#ffffff"}},
 {"command": "select.set", "params": {"ids": ["$5.id", "$6.id", "$7.id", "$8.id"]}},
 {"command": "object.distribute", "params": {"horizontal": "center"}},
 {"command": "document.inspect", "params": {"ids": ["$5.id", "$6.id", "$7.id", "$8.id"]}},
 {"command": "text.create", "params": {"x": 60, "y": 72, "text": "Kick-off\nJan", "size": 9, "justify": "center", "color": "#0f172a"}},
 {"command": "text.create", "params": {"x": 206.67, "y": 72, "text": "Beta\nApr", "size": 9, "justify": "center", "color": "#0f172a"}},
 {"command": "text.create", "params": {"x": 353.33, "y": 72, "text": "GA\nJul", "size": 9, "justify": "center", "color": "#0f172a"}},
 {"command": "text.create", "params": {"x": 500, "y": 72, "text": "v2\nOct", "size": 9, "justify": "center", "color": "#0f172a"}},
 {"command": "layer.new", "params": {"name": "Chart"}},
 {"command": "graph.create", "params": {"type": "column", "x": 60, "y": 160, "width": 400, "height": 200,
   "categories": ["Q1", "Q2", "Q3", "Q4"], "series": ["Plan", "Actual"], "rows": [[10, 8], [20, 22], [30, 27], [40, 45]]}},
 {"command": "document.find", "params": {"name": "Actual", "kind": "Group"}},
 {"command": "paint.setFill", "params": {"ids": ["$20.matches.0.id"], "color": "#0ea5e9", "target": "contents"}},
 {"command": "document.find", "params": {"name": "Plan", "kind": "Group"}},
 {"command": "paint.setFill", "params": {"ids": ["$22.matches.0.id"], "color": "#cbd5e1", "target": "contents"}},
 {"command": "select.none", "params": {}}
]
```

- `object.distribute {horizontal: "center"}` kept the first and last dot and moved the middle
  two to centres 206.67 and 353.33; step 13 (`document.inspect {ids}`) reports the new bounds,
  which is where the label x values come from. Over MCP, read them from the batch `results`
  and place the labels in a second batch, or compute the spacing yourself and skip distribute.
- `graph.create` rows are one array per category, one value per series. Each series is a group
  named after its series (legend swatch included), which is what `document.find` hits; the
  colours survive `graph.setData`. `graph.setType {id, type: "line"}` switches the chart type.
- A graph is live data, not plain paths: for hand-styled bars, `object.ungroup` it after the
  data is final.

---

## More layouts, briefly

- **Org chart**: the generator with `process` nodes and `TB`; multi-line labels
  (`"CTO\nA. Rivera"`) grow the box. Rows are centred, so add `col` to children to sit them
  under their parent (`col` is in column-pitch units, 0 = centre).
- **Swimlanes**: draw lanes first on a `Lanes` layer as `shape.rectangle` bands (no stroke,
  alternating light fills) with a rotated or left-aligned lane title; then place nodes by
  (lane, step) instead of (rank, column). The generator's `rank` + `col` overrides with `LR`
  give lanes as rows.
- **Wireframes**: one artboard per screen (`file.new {artboards: 3, artboardLayout: {layout:
  "row", spacing: 40}}`), greys only, `shape.rectangle` for blocks, an image placeholder as a
  rectangle plus two diagonal `shape.line`s, `text.create {area: {width, height}}` for body copy.
  `shape.rectangularGrid {x, y, width, height, rows, columns}` gives a layout grid.
- **Floor-plan style layouts**: walls as thick strokes on open paths (`stroke.set {weight: 8,
  cap: "square", join: "miter"}`), then `object.path.outlineStroke` (acts on the selection) to
  turn them into filled shapes and `object.pathfinder.unite {ids}` to merge corners; doors as
  `shape.arc`; room labels on a `Labels` layer; dimensions with `options.scale: "1:50"`.
- **Icons**: a 24 x 24 artboard, 2 pt strokes with round caps and joins, shapes combined with
  `object.pathfinder.unite` / `minusFront`, then `object.path.outlineStroke` so the icon is
  pure fills; export SVG with `options: {decimals: 2, minify: true}` and audit it with
  **svg-audit**.
