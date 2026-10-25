---
name: vectorcraft-draw
description: >-
  Draw diagrams and structured drawings in VectorCraft (the open-source, pure-Rust vector app) through
  its MCP tools or the headless `vectorcraft-cli`: flowcharts, process maps, org charts, architecture
  and network diagrams, swimlanes, timelines, wireframes, floor-plan style layouts, icons, simple
  charts/graphs, and technical drawings with dimensions. Use it when the user says "draw a
  flowchart / diagram / org chart / wireframe / technical drawing", wants a diagram generated from
  data (nodes and edges, CSV, a list), needs connectors with arrowheads, aligned and distributed
  boxes, named layers or consistent styles, or wants diagrams exported to SVG, PDF (incl. PDF/X,
  PDF/A), PNG, DXF for CAD/laser, or EMF/WMF for Office. Also covers LibreOffice Draw interop:
  converting `.odg` files so VectorCraft can open them and turning VectorCraft output back into
  ODG with `soffice --headless --convert-to`. Not for Adobe Illustrator or LibreOffice itself.
---

# VectorCraft Draw: diagrams, charts and technical drawings

Checked on 2026-10-25 against `vectorcraft-cli 0.16.0` (`~/.local/bin/vectorcraft-cli`): the
command catalogue (`vectorcraft-cli commands`, 802 ids), the headless MCP server
(`vectorcraft-cli mcp --headless`, 32 tools) and real runs. Things marked **UNVERIFIED** could
not be run on the authoring machine.

Related skills, so this one stays short:
- **vectorcraft** (`../vectorcraft/SKILL.md`): what the app is, formats, launch flags, the MCP
  and control-channel surface, verification protocol. Read it first if VectorCraft is new to you.
- **vectorcraft-scripting**: deeper automation, porting scripts, long command pipelines.
- **svg-audit**: validate and optimise the SVG you export (`scripts/validate_svg.py`).

Clean-room rule: never use Adobe applications or their MCP tools to make or check anything here.

## Pick a route

| Situation | Route |
|---|---|
| A live VectorCraft window, or an MCP client already registered | MCP: `command_batch {atomic: true}` then `doc_inspect` + `render_preview` |
| No GUI, files in and out, CI, many diagrams | `vectorcraft-cli run --commands steps.json --export out.svg ...` |
| Boxes-and-arrows from data (nodes + edges) | `scripts/flowchart_steps.py spec.json` writes the step file for either route |
| Bar/line/pie chart | `create_graph` (MCP) or `graph.create` (9 types) |
| Part drawing with measurements | `dimension.create` + DXF/PDF export |
| An `.odg` from LibreOffice Draw | `soffice --headless --convert-to pdf` (or svg) first, then open it |

Register MCP once (from the vectorcraft skill): `claude mcp add vectorcraft -- vectorcraft-cli mcp`
(connects to an app started with `--control 7979`, else runs headless) or `... mcp --headless`.

## Ground rules (all verified at 0.16.0)

1. **Space**: points, y grows downward, origin at artboard 0's top-left. A new document is
   612 x 792. `file.new` takes `width`/`height` as numbers (pt) or strings like `"160 mm"`, plus
   `units`, `artboards`, `colorMode: "cmyk"`. Headless MCP starts with an empty Untitled-1.
2. **Paint is sticky.** `paint.setFill`/`paint.setStroke` change the selection *and* the default
   for the next object. Always give every object explicit paint: `draw_shape`/`draw_path` take
   `fill`, `stroke`, `strokeWidth`, `dash`, `cap`, `join`, `opacity`, `name`; use `"none"` to
   switch one off. `text.create` takes `color`; without it, type inherits the last fill.
3. **Type**: `text.create {x, y, text, size, justify, color, font?}` places *point type whose
   baseline is y*; `justify: "center"` centres each line on x. `\n` makes extra lines (leading
   about 1.2 x size). To centre n lines in a box with centre (cx, cy):
   `y = cy + size/3 - (n-1) * 1.2 * size / 2`. The default face is the bundled Source Sans 3; a
   named `font` must be installed (`text.fontList`). Area type: `area: {width, height, fit}`.
   MCP `add_text` is the same but cannot go inside `command_batch`; use `text.create` there.
4. **Arrowheads** live on the stroke: `stroke.set {ids, endArrow, startArrow, arrowAlign}`.
   Heads include `Triangle`, `Arrow`, `ArrowOpen`, `Barbed`, `Concave`, `Circle`, `Diamond`,
   `Square`, `Bar`, `Fork` and about 30 more (the `stroke.set` params text lists all 40). Use
   `arrowAlign: "tip"` so the tip lands on the end point instead of overshooting it, and
   `stroke.setAdvanced {ids, arrowScale: [start %, end %]}` to resize heads. Dashed lines:
   `stroke.set {dash: [4, 3]}`. SVG export writes arrowed strokes as filled outlines (no
   `<marker>`), so arrows look identical everywhere but are no longer editable strokes in SVG.
5. **Names and layers**: `object.setProps {id, name}` names an object (SVG keeps it as
   `data-name`, with a sanitised `id`). `layer.setProps {name}` renames the current layer;
   `layer.new {name}` adds a layer above the current one and makes it current, so new art goes
   there; `layer.setCurrent {id}` switches back. Find ids with
   `document.find {kind: "Layer", name: "Nodes"}` -> `matches[0].id`.
6. **Groups**: `object.group {ids}` returns the group's `id`; group each node's shape with its
   label so it moves as one, then name the group (`node:<id>`).
7. **Consistent styling**: global swatches (`swatch.new {name, color, global: true}` returns the
   real `name`; an existing name becomes "Name 2") linked with `paint.setFill {ids, swatch}`, so
   one `swatch.edit {name, color}` recolours the whole diagram. Graphic styles capture fill,
   stroke, weight and arrowheads: `graphicStyle.new {id, name}` from a styled object, then
   `graphicStyle.apply {name, ids}` on the rest in one step.
8. **Align and distribute** act on the selection: `select.set {ids}`, then
   `object.align {horizontal|vertical: "left"|"center"|..., to: "selection"|"artboard"|"key"}`,
   `object.distribute {horizontal: "center"}` (first and last stay put),
   `object.distributeSpacing {axis: "horizontal", spacing?}` (spacing needs a key object,
   `select.key {id}`).
9. **Artboard**: `artboard.fitToArt {index: 0}` hugs the art with no margin; for a margin, compute
   the bounds yourself and use `artboard.setProps {index: 0, x, y, width, height}`.
10. **References**: a param string `"$N.id"` (also `"$N.name"`, `"$N.matches.0.id"`, `"$last.id"`)
    takes a value from step N's result; step 0 is the first step. Write `$$` for a literal `$`.
    In `vectorcraft-cli run`, every `--cmd` before `--commands` counts as a step (shift N, or
    use the generator's `--base`); `--in` does not.
11. **One undo step**: MCP `command_batch {atomic: true, label}` records the whole batch as one
    undo step named `label`, at most 256 steps. Two traps found by testing:
    - Do **not** put `file.new` inside the atomic batch. The undo group stays on the document that
      was active when the batch began, so everything drawn in the new document becomes separate
      undo steps. Run `command_run {id: "file.new"}` first, then the batch.
    - A failing step stops the batch but **keeps** the steps that ran (as one undo step). Call
      `undo` once to drop the partial diagram, fix the step, rerun. (The engine command
      `command.batch` does roll back on failure, but it does not resolve `$N` references.)
12. **Unknown param keys are refused** with a did-you-mean before anything runs. Check ids and
    params with `vectorcraft-cli commands` or MCP `command_list {filter: "stroke"}`, never memory.

## Layout method

Diagrams come out clean when geometry is computed first and drawing is a dumb replay.

1. **Plan a grid.** Choose the flow direction (top-to-bottom or left-to-right), node sizes
   (e.g. 140 x 48 process boxes, 156 x 76 decisions), a rank gap (about 56) and a column gap
   (about 40). Put each node in a (rank, column) cell; centre every rank on the flow axis.
2. **Compute boxes**: `x = cx - w/2`, `y = cy - h/2`. Shapes: `shape.rectangle` (`radius` 6 for
   process, `radius = h/2` for a terminal pill), `path.create {d}` for a diamond
   (`M cx y L x+w cy L cx y+h L x cy Z`) or a parallelogram (slant about 0.35 h),
   `shape.ellipse` for states/nodes, `shape.polygon {cx, cy, radius, sides}` for hexagons.
3. **Route connectors orthogonally** from port to port (ports = middle of each side):
   - same column: one straight segment, bottom port to top port;
   - different column: elbow `src bottom -> (src.x, midY) -> (dst.x, midY) -> dst top`, where
     `midY` sits in the gap just above the target row;
   - a decision's second exit leaves from its side tip: `tip -> (dst.x, tip.y) -> dst top`;
   - a loop back to an earlier rank goes out the far side into an outer lane
     (`lane x = rightmost box edge + 22`, +22 per extra lane) and comes back in.
   Draw each as one `path.create {d: "M x0 y0 L x1 y1 ..."}` with fill none, `join: "round"` and
   `endArrow: "Triangle", arrowAlign: "tip"`. Check segments never cross a box; if one would, push
   it to a lane.
4. **Layers bottom to top**: `Connectors` (so lines tuck under boxes), `Nodes` (one named group per
   node), `Labels` (edge labels, title, notes).
5. **Style once**: swatches for the palette, one graphic style per node kind and one for
   connectors.
6. **Draw in one atomic batch**, then fix the artboard (rule 9).
7. **Verify** (below) and only then export.

`scripts/flowchart_steps.py` implements exactly this; read it when hand-building something
similar.

## Route A: MCP

```json
{"name": "command_run", "arguments": {"id": "file.new", "params": {"width": 480, "height": 320}}}
{"name": "command_batch", "arguments": {"atomic": true, "label": "Diagram", "steps": [
  {"id": "layer.setProps", "params": {"name": "Connectors"}},
  {"id": "draw_path", "params": {"d": "M120 64 L200 64 L200 150", "fill": "none",
     "stroke": "#334155", "strokeWidth": 1.25, "join": "round", "name": "edge:a->b"}},
  {"id": "stroke.set", "params": {"ids": ["$1.id"], "endArrow": "Triangle", "arrowAlign": "tip"}},
  {"id": "layer.new", "params": {"name": "Nodes"}},
  {"id": "draw_shape", "params": {"shape": "rectangle", "x": 20, "y": 40, "width": 100,
     "height": 48, "radius": 6, "fill": "#e0f2fe", "stroke": "#075985", "strokeWidth": 1.25}},
  {"id": "text.create", "params": {"x": 70, "y": 67.7, "text": "Start", "size": 11,
     "justify": "center", "color": "#0f172a"}},
  {"id": "object.group", "params": {"ids": ["$4.id", "$5.id"]}},
  {"id": "object.setProps", "params": {"id": "$6.id", "name": "node:a"}}
]}}
{"name": "doc_inspect", "arguments": {"depth": 2}}
{"name": "render_preview", "arguments": {"max_side": 1024}}
```

Inside `command_batch`, a step's `id` is any command id or the pseudo-tools `draw_path` /
`draw_shape` (with their tool arguments); the reply lists `results` and `created`. Look at the
preview, and use `doc_inspect {kind: "Group"}` or `document.find {name: "node:"}` to confirm
every node exists, is named and sits on the right layer. Then `export {path, format?, options?}`.

## Route B: headless step file

A step file is a JSON array of `{"command": id, "params": {...}}` (`"id"` is accepted for
`"command"`, so the same steps work for MCP) or JSON Lines. Without `--in`, `run` starts from a
new 612 x 792 document, so begin with `artboard.setProps` or `file.new`. `draw_path` and
`draw_shape` are MCP-only pseudo-steps; the CLI answers `unknown command`, so step files use
`shape.rectangle` / `shape.ellipse` / `path.create {d}` followed by `paint.setFill`,
`paint.setStroke` and `stroke.set` with `ids: ["$N.id"]`.

```sh
vectorcraft-cli run --commands steps.json \
  --export out.svg --export out.pdf --export out.png --export out.dxf --scale 2
vectorcraft-cli run --in base.vectorcraft --commands steps.json --export out.vectorcraft
```

`run` prints one JSON line per step and stops at the first failure, naming the step (`step 7
(object.group)`). Read every `"step":"export"` line's `warnings`. `--scale` sets pixels per point
for raster exports only. `SOURCE_DATE_EPOCH=<secs>` makes PNG/PDF bytes reproducible.

## Route C: generate from data

`scripts/flowchart_steps.py` (Python 3.8+, stdlib only) turns nodes and edges into a step file:
longest-path ranks, centred rows, orthogonal elbow connectors with Triangle heads, decision side
exits, loop-backs in an outer lane, edge labels, wrapped node labels, global swatches, one
graphic style per node kind, layers `Connectors` / `Nodes` / `Labels`, groups named `node:<id>`,
paths named `edge:<from>-><to>`, an artboard sized to fit with a 36 pt margin, and (with a
`title`) `file.info {title, description}`, which becomes the SVG `<title>` / `<desc>`.

```json
{"title": "Order handling", "direction": "TB",
 "nodes": [{"id": "start", "label": "Order received", "shape": "terminal"},
           {"id": "check", "label": "Item in stock?", "shape": "decision"}, ...],
 "edges": [{"from": "start", "to": "check"}, {"from": "check", "to": "ship", "label": "yes"}, ...],
 "style": {"nodeWidth": 120, "fills": {"process": "#f1f5f9"}}}
```

Shapes: `terminal`, `process`, `decision`, `io`. Optional per node: `rank` (force a row) and
`col` (cross-axis slot, 0 = centre, in units of the column pitch). `direction`: `TB` or `LR`.
`style` keys are listed in `STYLE` at the top of the script (sizes, gaps, font sizes, `font`,
colours per kind).

```sh
python3 scripts/flowchart_steps.py spec.json -o steps.json                 # for vectorcraft-cli run
python3 scripts/flowchart_steps.py spec.json --mcp -o batch.json           # command_batch arguments
python3 scripts/flowchart_steps.py spec.json --into-existing --origin 600,40 -o add.json
python3 -I scripts/test_flowchart_steps.py                                 # 9 tests; 1 needs the CLI
```

`--mcp` refuses more than 256 steps (roughly 40 nodes); use the CLI for bigger charts.
`--into-existing` leaves the artboard and the current layer alone and adds new layers.
Limits: one row per rank (no crossing minimisation), long edges that skip ranks detour through
the outer lane when a box is in the way, and several edges into one node share its top port.
For an org chart, use `process` nodes and the default `TB`; nudge children under their parent
with `col`. Worked example: `examples/order-flow.spec.json` -> `examples/order-flow.steps.json`.

## Charts

`create_graph {type, x, y, width, height, series, categories, rows}` (MCP) or `graph.create`
(same params) draws a live graph: `column`, `stackedColumn`, `bar`, `stackedBar`, `line`, `area`,
`scatter`, `pie`, `radar`. `rows` has one array per category with one value per series; `csv`
works too. Graphs start in black and greys: each series is a group named after the series, so
recolour with `document.find {name: "2026", kind: "Group"}` then
`paint.setFill {ids: ["$N.matches.0.id"], color, target: "contents"}`. The colour survives
`graph.setData {id, rows}`. Details in `references/diagram-recipes.md` (recipe 4).

## Technical drawings

`dimension.create {mode, a, b, offset, options}` draws a live dimension and returns its `label`
(for example `"100 mm"`). Modes: `linear`, `angular`, `radius`, `diameter`. Options include
`units` (`mm`, `in`, `pt`, `cm`...), `precision`, `scale` (drawing:real), `arrowStyle`
(`filled`, `open`, `tick`, `none`), `fontSize`, `textPosition`. A positive `offset` puts the
dimension on the right-hand side of the a-to-b direction (below a left-to-right one). Linked
dimensions follow edits: `source: {kind: "segment", edge: {node, subpath: 0, segment: 0}}` or
`{kind: "circle", node}`. Restyle with `dimension.update`. Export to DXF for CAD (recipe 3).

## Export and conversion

| Target | How | Notes (verified unless marked) |
|---|---|---|
| SVG | `--export out.svg`, `export {format: "svg", options}` | Live text, `data-name` per object, layers as `<g>`; `outlineText: true` for exact type without fonts; `decimals`, `minify`, `responsive` |
| PDF | `.pdf`, `document.exportPdf {standard}` | One page per artboard; `standard: "pdfX4"`, `"pdfX1a"`, `"pdfX3"`, `"pdfA2b"` write the right markers (not validated with an external preflight) |
| PNG | `.png` + `--scale 2` or `ppi` | `background: "white"` for no alpha; `document.exportForOffice {ppi}` for slides |
| DXF | `.dxf`, `document.exportDxf` | Default R2018, mm, layers kept as DXF layers; type outlined unless `preserve: "editability"` |
| EMF / WMF | `.emf` / `.wmf` | One artboard per file; EMF keeps curves, WMF flattens them |

`vectorcraft-cli convert IN OUT` converts in one go (`--scale`, `--artboard`, `--outline-text`,
`--decimals`). Every export result carries `warnings`, and `convert` adds `importWarnings`;
an empty list is the only all-clear. Full table, PDF/X steps and batch loops:
`references/export-and-conversion.md`.

## LibreOffice Draw (ODG) interop

VectorCraft does not read `.odg`; `vectorcraft-cli info x.odg` fails with "not a format
VectorCraft reads". Go through PDF or SVG with LibreOffice's `soffice`:

```sh
soffice --headless --convert-to pdf --outdir conv/ drawing.odg     # all pages -> artboards
vectorcraft-cli convert conv/drawing.pdf drawing.vectorcraft
soffice --headless --convert-to odg --outdir conv/ diagram.svg     # back to ODG
```

**UNVERIFIED**: `soffice` was not installed where this skill was written, so the soffice lines
(the reverse SVG/PDF/EMF -> ODG direction especially) are based on LibreOffice's documented
filters, not a test run. Install LibreOffice (`brew install --cask libreoffice` on macOS, where
the binary is `/Applications/LibreOffice.app/Contents/MacOS/soffice`; `sudo apt install
libreoffice-draw` on Debian/Ubuntu), try one file, and check the result before batching. See
`references/export-and-conversion.md` for the caveats.

## Verify before you deliver

1. `doc_inspect {depth: 1}` (or `document.inspect` in a step file): layers exist in the planned
   order, each node is a named group, `history` shows one entry per atomic batch.
2. `render_preview {max_side: 1024}` or a 2x PNG export: look at it. Check labels sit inside
   boxes, arrows touch their targets, nothing overlaps, the artboard has a margin.
3. Export and read every `warnings` array.
4. Inspect the SVG text: `grep -o 'data-name="[^"]*"' out.svg` lists nodes and edges, and
   `grep -o '<tspan[^>]*>[^<]*' out.svg` lists labels. Then run the **svg-audit** validator.
5. Reopen exports with `vectorcraft-cli info out.pdf` (object counts by kind, fonts, warnings).

## References

- `references/diagram-recipes.md`: four worked, tested recipes (flowchart from data,
  architecture diagram by hand over MCP, technical drawing with dimensions to DXF, timeline and
  chart), plus wireframe, floor-plan and icon notes.
- `references/export-and-conversion.md`: every format option used above, PDF/X, `convert`,
  batch conversion, LibreOffice round trips.
- `scripts/flowchart_steps.py`, `scripts/test_flowchart_steps.py`: the generator and its tests.
- `examples/order-flow.spec.json`, `examples/order-flow.steps.json`: a 5-node flowchart and its
  generated step file (74 steps).
