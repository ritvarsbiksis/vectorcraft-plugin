---
name: vectorcraft-scripting
description: >-
  Write, port, run and debug automation for VectorCraft, the open-source Illustrator-style
  vector app: `vectorcraft-cli run` step files (JSON or JSON Lines with "$N.path" references), MCP
  `command_batch`/`command_run` calls, control-channel clients (`vectorcraft --control`, JSON lines),
  sandboxed `.wasm` plug-ins (filters, live effects, exporters), Actions and data-driven batches
  (`command.batch`, `action.batch`, `dataset.import`), and folder export/convert pipelines. Use it
  whenever someone wants a "script", macro, batch job or automation for VectorCraft; asks to port,
  translate or run an Illustrator ExtendScript (.jsx, .jsxinc, .jsxbin) in VectorCraft, which has no
  script engine (this skill maps that DOM to VectorCraft commands and uses `script.check`); or debugs
  a failing step, an unknown-parameter error, a "$N" reference, an atomic batch, a confinement refusal
  or a control request. For what the app is and does in general, use the `vectorcraft` skill. Not for
  scripting Adobe Illustrator itself.
---

# VectorCraft scripting and automation

> Adapted from [`adobe-illustrator-scripting`](https://github.com/mouadja02/skills/tree/7d3a544d78edc42d447567dc4c44a072199d3b53/skills/design-and-ui/adobe-illustrator-scripting)
> (mouadja02/skills, from [github/awesome-copilot](https://github.com/github/awesome-copilot), MIT; see
> [LICENSE](LICENSE)). The structure follows the original; every API and example is VectorCraft's.

Checked against `vectorcraft-cli 0.16.0` and the repository docs at tag `v0.16.0` (`docs/mcp.md`,
`docs/control-protocol.md`, `docs/plugins.md`, `AGENTS.md`). Every example here was run with that CLI
(the control-channel ones through a test bridge to its headless engine, not the desktop app).
For the app itself (formats, UI, limitations, launch flags, verification protocol), read the sibling
skill [`../vectorcraft/SKILL.md`](../vectorcraft/SKILL.md); for laying out diagrams and structured
drawings, [`../vectorcraft-draw/SKILL.md`](../vectorcraft-draw/SKILL.md). This skill is about the
automation machinery itself: writing, porting, running and debugging it.

## Bundled files

- [`references/automation-surfaces.md`](references/automation-surfaces.md): exact reference for
  `run`/`convert`, the 32 MCP tools, the control protocol, the plug-in ABI, batches and `script.check`,
  including behaviour observed in 0.16.0 that the docs don't spell out. Read it before writing a client.
- [`references/jsx-porting-map.md`](references/jsx-porting-map.md): the reference app's scripting DOM,
  object by object, mapped to command ids and params; y-up → y-down formulas; enum crosswalk. Read it
  when porting a `.jsx`.
- [`examples/`](examples/README.md): runnable ports of the original skill's three scripts
  (batch PNG export, colour grid, find and replace), a stdlib Python control-channel client, and a
  compiler-free `.wasm` plug-in. `examples/README.md` gives the command for each.

## There is no script engine

VectorCraft never runs ExtendScript, JavaScript, AppleScript or VBScript. A `.jsx` can only be
**statically analysed**, by `script.check` (in the app: File › Scripts › Check Script…). What replaces
a script:

1. **Commands.** Everything the app does is a command with an id, params and a result: 802 of them in
   `vectorcraft-cli commands` at 0.16.0. Never guess an id or a param name: look it up there, or with
   MCP `command_list {filter: "…"}`.
2. **Steps, not code.** An automation is a list of `{"command": ID, "params": {...}}` steps. Values flow
   between steps through `"$N.path"` references; there are no variables, loops or conditions.
3. **Logic in your own language.** Loops, maths, files and decisions live in a client (shell, Python,
   Node, an agent) that generates the steps or sends them one by one.
4. **Plug-ins for in-document logic.** Code that must run inside VectorCraft on every path of a
   selection, or redraw live, is a sandboxed WebAssembly plug-in.

## Choosing a surface

| You need | Use |
|---|---|
| A repeatable job on files, no GUI, exit status for CI | `vectorcraft-cli run [--in IN] --commands steps.json --export OUT` |
| Convert or export files one to one | `vectorcraft-cli convert IN OUT [--scale N]` (in a shell loop for folders) |
| The same steps over a folder in one process | `action.batch` (through `run`) |
| An agent drawing, inspecting and previewing | MCP: `vectorcraft-cli mcp --headless` |
| An agent working in the user's open app, visibly | MCP `--connect 127.0.0.1:7979` + app started with `--control 7979` |
| Your own program driving the open app | control channel: JSON lines on `127.0.0.1:<port>` ([`examples/vc_control.py`](examples/vc_control.py)) |
| Several edits as one undo step | MCP `command_batch {atomic: true}`; `edit.undoGroup.begin`/`end` |
| Several edits that must all happen or none | engine command `command.batch` (rolls back on the first error) |
| Per-path geometry/colour logic, a live effect, a new export format | `.wasm` plug-in (`plugin.install`, `plugin.run`, `effect.apply`) |
| Template + spreadsheet → many files | `variable.define` + `variable.bind` + `dataset.import` + `action.batch {source: "datasets"}` |
| Reusing an existing `.jsx` | `script.check` + the porting map → a step file |
| Menus, dialogs, tools, window screenshots | the live app only: control `ui.*`, MCP `invoke_menu`/`screenshot {window: true}` while connected |
| An agent kept to certain folders | MCP or the app with `--automation-read-root` / `--automation-write-root` (`run`/`convert` have no confinement) |

## The object model

```
session: one `run`, one MCP server, or the desktop app
└─ documents (tabs)                 document.activate {index}; file.new; document.open
   ├─ artboards                     document.inspect → artboards [{x, y, width, height, name}]; artboard.*
   ├─ layers and sublayers          layer.new / layer.setProps / layer.move / layer.setCurrent
   │  └─ objects (by numeric id)    kind: Path, Compound Path, Group, Clip Group, Type, Image, Symbol,
   │                                Rectangle, Ellipse, …; name, bounds, fill, stroke, opacity, children
   ├─ swatches, gradients, patterns swatch.*, paint.*, pattern.*, object.pattern.make
   ├─ symbols, brushes, graphic styles, character/paragraph styles
   ├─ variables and data sets       variable.*, dataset.*
   └─ selection, key object, current layer, undo history, new-art paint
```

Read it, cheapest first:

- `document.inspect {depth: 0}`: artboards, top layers with counts, selection, history, units.
- `document.inspect {kind: "Type"}` or `{ids: [7, 9]}` (+ `limit`/`offset`): just those nodes, each
  with `path` (its ancestors). MCP `doc_inspect` takes the same arguments.
- `document.find {name?, kind?, text?}` → `{matches: [{id, name, kind, path}], total}`.
- `document.node {id}`: one object's full model (geometry as `subpaths[].anchors[] {p, in?, out?}`,
  appearance); `{id, summary: true}` the inspect summary. MCP resource `vectorcraft://object/{id}`.
- `document.json`: the whole model; use it for fidelity, never to look around a big file.

**Ids** are numbers, stable in a session and across native `.vectorcraft` save/open (verified). They
are reassigned when SVG/PDF is re-imported, and some commands replace objects (`symbol.new`,
`object.compoundPath.make`): take ids from each result, and name objects you must find again
(`object.setProps {id, name}` + `document.find {name}`).

## Units and coordinates

- Lengths are **points** (72 per inch; mm × 2.834645). A new document is 612 × 792 pt.
- **y points down; the origin is the first artboard's top-left.** The reference app's scripting DOM
  is y-up from the bottom-left, so every ported y changes. With `H` the artboard height:
  `rectangle(top, left, w, h)` → `shape.rectangle {x: left, y: H - top, width: w, height: h}`;
  `translate(dx, dy)` → `object.move {dx, dy: -dy}`. Matrices and the rest: porting map §1.
- Angles: degrees, positive = counter-clockwise on screen.
- Opacity params are 0–100; `document.inspect` reports `opacity` 0–1.
- Colours: prefer `"#rrggbb"`; `{c, m, y, k}`, `{gray}` (0 white, 100 black), `{l, a, b}` also work.
- Text `start`/`end` offsets are **UTF-8 bytes**, not JavaScript string indices.

## Core patterns

### 1. A step file is the new `.jsx`

```json
[
 {"command": "file.new", "params": {"width": 320, "height": 160, "name": "Badge"}},
 {"command": "shape.rectangle", "params": {"x": 20, "y": 20, "width": 280, "height": 120, "radius": 16}},
 {"command": "paint.setFill", "params": {"id": "$1.id", "color": "#1e88e5"}},
 {"command": "paint.setStroke", "params": {"id": "$1.id", "none": true}},
 {"command": "text.create", "params": {"x": 160, "y": 94, "text": "HELLO", "size": 40, "color": "#ffffff", "justify": "center"}},
 {"command": "object.group", "params": {"ids": ["$1.id", "$4.id"]}},
 {"command": "object.setProps", "params": {"id": "$5.id", "name": "badge"}}
]
```

```sh
vectorcraft-cli run --commands badge.json --export badge.svg --export badge.png --scale 2
```

`run` prints one JSON line per step (`{"step": "cmd", "command": "shape.rectangle", "result": {"id": 2}}`)
and exits 1 at the first failure. Without `--in`, the document is created when first needed (a leading
`file.new` becomes document 0). Steps may use `"id"` instead of `"command"`, so the same file is valid
as the `steps` of MCP `command_batch`. JSON Lines (one step per line) works too; `--commands -` reads
standard input.

### 2. Passing results between steps

A param string that is **exactly** `$N`, `$N.path` or `$last.path` becomes a value from step N's result
(0-based, counting every `--cmd`, `--commands` step and `--export` in order; `--in` is not a step):
`"$1.id"`, `"$2.ids.0"`, `"$last.ids[0]"`, also inside arrays (`"ids": ["$1.id", "$4.id"]`). A reference
to nothing fails the step. `"$5 off"` stays text but `"$1.99"` is a reference: write `"$$1.99"`.
Only `run` and MCP `command_batch` resolve references; `engine.execute` and `command.batch` don't.

### 3. Logic in your language, steps to VectorCraft

Generate the steps, then hand them over. [`examples/create-color-grid.py`](examples/create-color-grid.py)
computes a 5 × 4 grid and knows each step's index, so it writes `"$N.id"` references itself:

```sh
python3 examples/create-color-grid.py --columns 8 --rows 6 --seed 42 | vectorcraft-cli run --commands - --export grid.svg
```

### 4. An agent over MCP: inspect, act in one batch, look

```json
{"name": "doc_inspect", "arguments": {"depth": 0}}
{"name": "command_batch", "arguments": {"atomic": true, "label": "Badge", "steps": [
  {"id": "draw_shape", "params": {"shape": "rectangle", "x": 72, "y": 72, "width": 200, "height": 80, "radius": 12, "fill": "#1e88e5", "stroke": "none"}},
  {"id": "text.create", "params": {"x": 90, "y": 120, "text": "HELLO", "size": 28, "color": "#ffffff"}},
  {"id": "object.group", "params": {"ids": ["$0.id", "$1.id"]}}]}}
{"name": "render_preview", "arguments": {"max_side": 512}}
{"name": "export", "arguments": {"path": "/work/out/badge.svg"}}
```

- `atomic: true` makes the batch **one undo step, not a transaction**: if step 3 fails, steps 1–2
  stay (as that undo step). Read `failed`/`results`, then `undo` once if you want them gone.
- The undo group belongs to the document active when the batch starts: run `file.new` or `open_file`
  in a call of its own, then the atomic batch.
- A headless server starts with one document already open (`Untitled-1`).
- `draw_shape`/`draw_path` steps style the object in the same step; their ids are in `created`.

### 5. Your own program and the live app

The control channel is plain TCP on loopback: one JSON object per line, one reply per line.

```python
import json, socket
s = socket.create_connection(("127.0.0.1", 7979)); f = s.makefile("rb")
def call(method, params=None, _id=[0]):
    _id[0] += 1
    s.sendall((json.dumps({"id": _id[0], "method": method, "params": params or {}}) + "\n").encode())
    r = json.loads(f.readline())
    if not r["ok"]: raise RuntimeError(r["error"])
    return r["result"]
rect = call("engine.execute", {"command": "shape.rectangle", "params": {"x": 72, "y": 72, "width": 100, "height": 50}})
call("engine.execute", {"command": "paint.setFill", "params": {"id": rect["id"], "color": "#e53935"}})
```

[`examples/vc_control.py`](examples/vc_control.py) adds error handling, `$N` resolution for replaying
step files (`play steps.json --atomic LABEL`, undone on failure) and `export-open` (every open document
to PNG). The port has no authentication: enable `--control` only while you use it.

### 6. Loops over objects (the `pageItems` loop)

Inside the engine, select by kind and act on the selection:

```json
[
 {"command": "select.object.textObjects", "params": {}},
 {"command": "text.setStyle", "params": {"size": 20, "fill": "#c62828"}},
 {"command": "select.none", "params": {}}
]
```

For anything conditional, query from the client (`document.inspect {kind: "Type"}`, `document.find`),
decide there, and send commands with explicit `ids`.

### 7. Data-driven graphics (variables and data sets)

```json
[
 {"command": "text.create", "params": {"x": 20, "y": 70, "text": "Name", "size": 36}},
 {"command": "variable.define", "params": {"name": "headline", "kind": "text"}},
 {"command": "variable.bind", "params": {"variable": "headline", "ids": ["$0.id"]}},
 {"command": "dataset.import", "params": {"csv": "name,headline\nAda,Ada Lovelace\nAlan,Alan Turing\n"}},
 {"command": "action.batch", "params": {"source": "datasets", "destinationFolder": "out",
   "commands": [{"command": "document.export", "params": {"format": "svg"}}]}}
]
```

This writes `out/Untitled_Ada.svg` and `out/Untitled_Alan.svg` (`{FileStem}_{DataSet}`; the folder must
exist). CSV headers: `name`, then variables; `#Name` defines a visibility variable, `@Name` an image one.

### 8. Folders of files

`action.batch {folder, includeSubdirs?, destinationFolder, commands}` opens each readable file, plays
`commands`, and points each `document.export` at `destinationFolder/{stem}.{ext}`. Leave `destination`
out to write only the exports (`"folder"` also saves a copy of every source file there). It caps at 500
files, and `run` exits 0 even when some failed: check `failed` and `processed[].error`. A shell loop over
`vectorcraft-cli convert` isolates each file and scales past 500. Both are in
[`examples/batch-export-png.sh`](examples/batch-export-png.sh).

### 9. Plug-ins

A plug-in is a `.wasm` module with no imports that exports `memory`, `vc_abi_version` (returns 1),
`vc_manifest`, `vc_alloc` and `vc_run`, and exchanges JSON: an object **filter** gets the selected paths
and returns their new state (one undo step), a live **effect** reshapes one object's geometry on every
redraw, an **exporter** turns the native document JSON into file bytes. Install with
`plugin.install {path}` (copied into the profile's Plug-ins folder; experiment with a throwaway
`VECTORCRAFT_CONFIG_DIR`), run with `plugin.run {id}` or `effect.apply {effect: "plugin.<id>"}`.
[`examples/hello-plugin.py`](examples/hello-plugin.py) writes a working filter without a compiler.
ABI details: automation-surfaces §5.

## Quick reference: common jobs

| Job | Command (params) |
|---|---|
| New document | `file.new {width, height, colorMode?: "cmyk", artboards?}` |
| Open | `document.open {path}` (MCP `open_file`, control `app.open`, CLI `--in`) |
| Layer | `layer.new {name}` → `{id}`; `layer.setProps {id, visible?, locked?}`; `layer.setCurrent {id}` |
| Shapes | `shape.rectangle {x, y, width, height, radius?}`, `shape.ellipse`, `shape.polygon {cx, cy, radius, sides}`, `shape.star {cx, cy, radius1, radius2, points}`, `shape.line {x1, y1, x2, y2}` |
| Free path | `path.create {anchors: [{x, y, in?, out?}], closed?}` or `{d: "M0 0 L10 10"}` |
| Fill / stroke | `paint.setFill {id, color}` / `{none: true}`; `paint.setStroke`; `stroke.set {weight, cap, join, dash}` |
| Gradient | `paint.setFill {id, gradient: {kind: "linear", angle, stops: [{offset, color}]}}` |
| Spot colour | `swatch.new {name, color, spot: true}` → `paint.setFill {swatch, tint?}` |
| Point / area / path type | `text.create {x, y, text, size?, font?}`; `text.create {…, area: {width, height}}`; `text.createInPath {path, mode: "area"\|"onPath"}` |
| Edit text | `text.setText {id, text}`; `edit.findReplace {find, replace}`; `text.setRangeStyle {id, start, end, …}` |
| Group, compound, clip | `object.group {ids}`, `object.compoundPath.make {ids}`, `object.clippingMask.make {ids}` |
| Symbols | `symbol.new {name, ids}`; `symbol.place {name, x, y}`; `symbol.breakLink {ids}` |
| Transform | `object.move {ids, dx, dy}`, `object.rotate {ids, angle, origin?}`, `object.scale {ids, sx, sy?}`, `object.transform {ids, matrix}` |
| Effects | `effect.list` (catalogue), `effect.apply {effect, params, ids?}` |
| Pathfinder | `object.pathfinder.unite {ids}` … (MCP `pathfinder {operation}`) |
| Artboards | `artboard.new {x, y, width, height, name}`; `artboard.setProps {index, …}` |
| Selection | `select.set {ids}`, `select.all`, `select.none`, `select.object.textObjects` |
| Save / export | `document.save {path}`; `document.export {path, …}`; `file.saveCopy {path}` |

The full table, with the DOM name each replaces: [jsx-porting-map.md](references/jsx-porting-map.md).

## Export workflows

`document.export {path?, format?, …}` is the one exporter behind CLI `--export`/`convert`, MCP `export`
and control `app.export`; the path's extension picks the format and `document.formats` lists every
format with its options. Without `path` it returns `dataBase64`.

```sh
vectorcraft-cli run --in art.vectorcraft --export art.svg --export art@2x.png --scale 2 --export art.pdf
vectorcraft-cli convert art.ai art.svg --outline-text --decimals 2
```

```json
{"command": "document.export", "params": {"path": "out/icon.png", "ppi": 144, "background": "transparent"}}
{"command": "document.export", "params": {"path": "out/sheet.png", "useArtboards": true, "range": "1-3"}}
{"command": "document.export", "params": {"path": "out/print.pdf", "range": "all"}}
{"command": "document.exportPdf", "params": {"path": "out/x1a.pdf", "standard": "pdfX1a"}}
{"command": "document.exportForScreens", "params": {"folder": "out/screens", "formats": [{"format": "png", "scale": "2x"}]}}
```

- Rasters: first artboard by default, transparent background, `scale` = pixels per point or `ppi`;
  `useArtboards: true` writes `<stem>-<artboard name>.<ext>` per artboard; `rect: [x, y, w, h]` renders a page area.
- PDF and `.ai`: one page per artboard. SVG: one file per artboard of a `range`; options under `svg`.
- Selected art only: `selectedOnly: true` (MCP `selection: true`); `document.exportSelection`.
- Every result carries `warnings`, the loss report: read them. `SOURCE_DATE_EPOCH` makes PNG/PDF/EPS
  bytes reproducible.

## Porting an ExtendScript script

1. **Check it, never run it.** `script.check` reads the script (and, with `includes: true`, the files its
   `#include` lines name inside its folder) without executing anything:
   ```sh
   vectorcraft-cli run --cmd script.check --params '{"path": "/abs/path/create-color-grid.jsx", "includes": true}'
   ```
2. **Read the report.** `needs` says which worlds it touches (`dom`, `files`, `menuCommands`,
   `dialogs`, `hostOnly`); `dom.members` lists every DOM chain it uses; `menuCommands.strings` the
   menu strings to find command ids for; `outside` what it does beyond the document (files written,
   network, other apps); `problems` syntax that wouldn't even load.
3. **Map** each chain with the porting map; convert every y coordinate; turn `prompt`/dialogs into
   params; move `File`/`Folder`/loops/maths into the client; replace `executeMenuCommand` strings with
   command ids found by `command_list {filter}`.
4. **Run headless on copies**, inspect the result, and export. Then follow the round-trip checks below.

What `script.check` reported for the original skill's three scripts (0.16.0), and what they became:

| Script | `needs` | Key `dom.members` / `features` | Port |
|---|---|---|---|
| `create-color-grid.jsx` (38 lines) | language, dom | `app.documents.add()`, `….layers.add().name`, `….pathItems.rectangle()`, `.fillColor`, `.stroked`, `app.redraw()`; type `RGBColor` | `create-color-grid.py` → `create-color-grid.json`: `file.new`, `layer.new`, per cell `shape.rectangle` + `paint.setFill` + `paint.setStroke {none}`; y = 72 + row × 82 instead of `doc.height - 72 - …`; seeded random |
| `find-replace-text.jsx` (32 lines) | language, dom | `app.activeDocument.textFrames[].contents` (+ `.indexOf()`, `.split().join()`); `notify` ×4 (the alerts and prompts) | `find-replace-text.json`: `document.find {kind: "Type", text}` (frames, like the original's count), `edit.findReplace {find, replace, matchCase}` → `{count}` of occurrences; prompts become params |
| `batch-export-png.jsx` (39 lines) | language, dom, files | `app.documents[].exportFile()`, `app.userInteractionLevel`; type `ExportOptionsPNG24`; `file.dialog` (`Folder.selectDialog`), `file.objects`, `notify` ×3 | `batch-export-png.sh`: `action.batch` + `document.export {format: "png"}` over a folder, or `convert` per file; `vc_control.py export-open` for the app's open documents |

All three report `targets: [{app: "illustrator"}]` from `#target illustrator`, no `problems` and no
`outside` entries. A script that also writes a log file and calls menu items shows them:
`menuCommands.strings: [{value: "group"}, {value: "outline"}]`, `outside: [{id: "filesWritten", modes:
["w"]}]`, and `let`/`=>` as `problems: [{code: "newerSyntax"}]`.

## Error handling

| Where | What you get | Do |
|---|---|---|
| Misspelt param | ``invalid parameters for `file.new`: unknown parameter `widht`; did you mean `width`?`` | fix the key. **But** at 0.16.0 `layer.new`, `layer.setProps`, `object.setProps`, `stroke.set`, `object.setLiveShape`, `document.save`, `file.saveAs`, `document.export`, `document.inspect` ignore unknown keys silently: read the object back after them |
| Bad value | ``invalid parameters for `paint.setFill`: give color, none, swatch or gradient``, `` `columns` must be a whole number `` | the message names the key |
| No document | ``command `document.inspect` is not available right now: no document open`` | `file.new` / open first |
| `$N` | `` `$5.id`: there is no step 5 before this one ``; `step 0's result has no such value` | count from 0; `$$` for a literal `$` |
| `run` | `vectorcraft-cli: step N (id): …` on stderr, exit 1, later steps skipped, nothing rolled back | re-run on the original input |
| `action.batch` | exit 0 with `{failed, stopped, processed[].error}` | check `failed`; `stopOnError: false` to keep going |
| MCP | `isError: true` + message; `-32602` unknown tool argument; `-32003` busy (not run) | retry after the running call |
| Control | `{"ok": false, "error"}`; a malformed line closes the connection; `timeout: … will not run` (safe to retry) vs `still running` (inspect first); `{"pending": "<dialog>"}`; `"cancelled"` for a native file dialog | pass `path`s; finish dialogs with `ui.dialog.*`; reconnect after a close |
| Opening/exporting | `warnings` (on open also `missingLinks`; `convert` adds `importWarnings`) | treat them as the loss report |

Undo-safe edits: `command.batch {commands}` (engine) is all or nothing; `edit.undoGroup.begin {label}` +
`edit.undoGroup.end {cancel: true}` undoes a partial group; MCP `command_batch {atomic}` only groups.

## File confinement

- `vectorcraft-cli mcp --automation-read-root DIR --automation-write-root DIR` (each repeatable; implies
  `--headless`; refused with `--connect`): every read (open, place, `script.check` and its includes,
  plug-ins, libraries) must be under a read root, every write (save, export, screenshots) under a write
  root. A kind left out grants nothing (exports then only return bytes).
- The desktop app confines itself: `vectorcraft --control 7979 --automation-read-root DIR
  --automation-write-root DIR`; connect MCP or your client as usual.
- Refusals are ordinary errors: `automation path rejected: outside the write root /work/out: /etc/x.png`.
- `run` and `convert` have **no** confinement (they refuse the flags): run them only on paths you chose.
- Isolate the profile for agent runs: `VECTORCRAFT_CONFIG_DIR=/tmp/vc-agent` (or `VECTORCRAFT_NO_PREFS=1`).

## Verify by round-trip

1. After each edit you depend on, read it back: `document.inspect {ids: [id]}` or `document.node {id,
   summary: true}`; essential after the commands that don't check param names.
2. Look: MCP `render_preview`, control `ui.render`, or `--export check.png`.
3. Reopen what you wrote: `vectorcraft-cli info out.svg` (kinds, fonts, artboards, warnings) and
   `vectorcraft-cli run --in out.svg --cmd document.inspect --params '{"depth": 1}'`.
4. Keep the master as `.vectorcraft`: ids, live shapes (`Rectangle`) and spot-swatch links survive it;
   an SVG round trip turns them into plain `Path`s with new ids and hex colours (observed).
5. For byte-level comparisons set `SOURCE_DATE_EPOCH`.

## Best practices

- Look up every id and param in `vectorcraft-cli commands` (or `command_list`) for the installed
  version; the catalogue is the contract, not memory or older docs.
- Address objects by `ids`/`id` from results instead of relying on the selection; set fills and strokes
  explicitly (new art inherits the last paint used, and `path.create` fills open paths white).
- Keep step files declarative and generate them; keep one job per file; name objects you need later.
- Use JSON tools (Python `json.dumps`, `jq`) to build params: shell quoting breaks on quotes and `$`.
- Batch for one undo step, but create or open the document before an atomic batch.
- Run long or risky jobs headless on copies; point the live app at the result only when it is right.
- Prefer `--commands FILE` over long `--cmd` lines (command lines have length limits).
- Turn the control port off when done; it has no authentication.

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| Shapes appear upside down or off the page | y-up coordinates from a ported script | `y = H - y`; porting map §1 |
| Command "succeeded" but nothing changed | misspelt key on a command that doesn't check keys, or no selection | read back; pass `ids` |
| Black outline on every new shape | new art takes the default stroke | `paint.setStroke {id, none: true}` or `draw_shape {stroke: "none"}` |
| `"$1.99"` fails as a reference | it is one | write `"$$1.99"` |
| Atomic MCP batch left half the edits | atomic = one undo step, not rollback | `undo` once, or use engine `command.batch` |
| Edits of an atomic batch undo one by one | `file.new` inside the batch | create the document in a separate call |
| `unknown command view.zoomIn` / `inspect_ui needs the desktop app` | UI-only command headless | connect to the app (`--control` + `mcp --connect`) |
| Control call returns `cancelled` or `{"pending": …}` | a file dialog or a dialog opened | pass `path`; `ui.dialog.set`/`confirm`/`cancel` |
| Control connection drops | malformed line, 17th connection, 5 min idle | reconnect; one JSON object per line |
| `automation path rejected` | outside the roots | widen the root or write inside it |
| Text styling lands on the wrong letters | UTF-16 indices from JavaScript | convert to UTF-8 byte offsets |
| PNG has a white background | the export asked for it | `background: "transparent"` (the default) |
| `.jsx` "doesn't run" | there is no script engine | `script.check` and port it |

## Examples

| File | Ports | Run |
|---|---|---|
| [`examples/create-color-grid.json`](examples/create-color-grid.json) + [`.py`](examples/create-color-grid.py) | `create-color-grid.jsx` | `vectorcraft-cli run --commands examples/create-color-grid.json --export grid.svg` |
| [`examples/find-replace-text.json`](examples/find-replace-text.json) + [`sample-text.svg`](examples/sample-text.svg) | `find-replace-text.jsx` | `vectorcraft-cli run --in examples/sample-text.svg --commands examples/find-replace-text.json --export replaced.svg` |
| [`examples/batch-export-png.sh`](examples/batch-export-png.sh) | `batch-export-png.jsx` | `examples/batch-export-png.sh IN_DIR OUT_DIR [SCALE] [--per-file]` |
| [`examples/vc_control.py`](examples/vc_control.py) | control-channel client | `python3 examples/vc_control.py play examples/create-color-grid.json --atomic "Color Grid"` |
| [`examples/hello-plugin.py`](examples/hello-plugin.py) | plug-in ABI v1 | `python3 examples/hello-plugin.py hello.wasm` |

Details and expected output: [`examples/README.md`](examples/README.md).

## Sources

- VectorCraft repository: https://github.com/storytold/vectorcraft at tag `v0.16.0`:
  `docs/mcp.md` (tools, `run`, parameter keys, `script.check`), `docs/control-protocol.md`,
  `docs/plugins.md`, `AGENTS.md`.
- Ground truth: `vectorcraft-cli 0.16.0` (`vectorcraft-cli commands`, MCP `tools/list`), with every
  example above executed headlessly on 2026-10-25. The control-channel client was exercised through a
  test bridge to a headless engine, not against the desktop app.
- Original skill: `adobe-illustrator-scripting` in mouadja02/skills at commit
  `7d3a544d78edc42d447567dc4c44a072199d3b53` (from github/awesome-copilot), MIT, Copyright GitHub, Inc.
  No Adobe software was used to write or test this port.
