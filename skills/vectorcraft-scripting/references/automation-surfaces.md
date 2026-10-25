# VectorCraft automation surfaces: reference

Checked against `vectorcraft-cli 0.16.0` (installed at `~/.local/bin/vectorcraft-cli`), its
`vectorcraft-cli commands` catalogue, its MCP server's `tools/list`, and the repository docs at tag
`v0.16.0`: `docs/mcp.md`, `docs/control-protocol.md`, `docs/plugins.md`, `AGENTS.md`. Statements marked
**(observed)** come from running the 0.16.0 CLI, not from the docs.

Contents: 1 command layer · 2 headless CLI · 3 MCP server · 4 control channel · 5 plug-ins ·
6 batches, actions and data · 7 `script.check`

---

## 1. The command layer (shared by every surface)

Everything the app does is a **command**: an id, a label, a menu path, a shortcut, a params description
and an enabled state. The CLI, MCP, the control channel, the browser API and the Actions panel all call
the same commands.

- `vectorcraft-cli commands` prints the catalogue as JSON. At 0.16.0 it lists **802 entries**: 796 engine
  commands plus 6 CLI host commands (`file.open`, `file.save`, `file.export`, `file.exportForScreens`,
  `tool.select`, `tool.setOption`; `"host": true`). Fields: `id`, `label`, `menu`, `shortcut`,
  `params`, `enabled`, `disabled_reason` (`"no document open"` when the catalogue is printed with no
  document).
- UI-only commands (`ui.*`, `view.zoomIn`, `window.*`, dialogs) exist only in the desktop app: list them
  there with control `engine.commands` / `ui.menu.list`, or MCP `command_list` while connected. Headless,
  `invoke_menu {command: "view.zoomIn"}` answers `unknown command` **(observed)**.
- Live lookups: MCP `command_list {filter, menu, enabled_only, brief}` (alias `list_commands`), resource
  `vectorcraft://command/{id}`, control `engine.commands`.

**Reading a params description.** `{x, y, width, height, radius?: pt, rotation?: deg (about centre)} → {id}`
names the keys (`?` = optional), their units and defaults, and after `→` the result. `ids?|id?` means
either key. A `…` entry (`…as document.save`, `…the PDF options of document.exportPdf`) means the
command takes more keys than it lists.

**Unknown keys.** `run --cmd/--commands`, MCP `command_run` / `command_batch` steps and control
`engine.execute` check the top-level `params` keys against that description before running:

```
vectorcraft-cli: step 0 (file.new): invalid parameters for `file.new`: unknown parameter `widht`; did you mean `width`?
```

An effect's own `params` are checked against `effect.list` the same way. **(observed)** The check only
works where the description can be parsed. At 0.16.0 these accepted a misspelt key and ran with their
defaults (exit 0): `layer.new`, `layer.setProps`, `object.setProps`, `stroke.set`,
`object.setLiveShape`, `document.save`, `file.saveAs`, `document.export`, `document.inspect`. And
`paint.setFill` / `paint.setStroke` reject a misspelt colour key with a generic
`give color, none, swatch or gradient`. So never take exit 0 as proof that an edit happened: read the
object back.

**Results.** Commands return JSON (`{id}` for new objects, `{ids}`, `{count}`, …) or `null` for plain
edits. Most edits act on explicit `ids` / `id` when given, else on the selection. New objects become the
selection. Edits that change nothing record no undo step.

**Model conventions.** Lengths are points, y points **down**, the origin is the first artboard's top-left,
a new document is 612 × 792 pt. Opacity params are 0–100, but `document.inspect` reports `opacity` as
0–1 **(observed)**. Text ranges (`start`, `end`) are **UTF-8 byte offsets** **(observed)**.

---

## 2. Headless CLI (`vectorcraft-cli`)

```
vectorcraft-cli run [--in FILE] [--cmd ID [--params JSON] | --commands FILE|-]... [--export FILE]... [--scale N]
vectorcraft-cli convert IN OUT [--scale N] [--artboard I | --range R] [--outline-text] [--decimals N]
                               [--replace-lossy] [--editing-data] [--ai-version 7|pdf] [--hidden-objects layer|omit|visible]
                               [--transparent-images flatten|omit]
vectorcraft-cli info FILE        # JSON: warnings (what didn't import as it was), info, artboards, kinds (counts), fonts
vectorcraft-cli commands         # the catalogue
vectorcraft-cli bench FILE | perf
```

### `run`

- `--in FILE` opens any readable format (the open is not a numbered step). Without it, a 612 × 792
  document with "Layer 1" is created the first time a step needs one; if the first step is `file.new`,
  that becomes document 0 **(observed)**.
- `--cmd ID --params JSON`: `--params` belongs to the `--cmd` before it.
- `--commands FILE` (or `-` for standard input, once): a JSON array of steps, or JSON Lines (one step per
  line, blank lines skipped). A step is `{"command": ID, "params": {...}}`; `"id"` may replace
  `"command"` (so the same file can be the `steps` of MCP `command_batch`); any other key is refused.
  UTF-8 (a BOM is skipped), at most 64 MiB and 100,000 steps; a malformed step stops the run before
  anything runs, naming `entry N` / `line N`. Steps run where the option stands among `--cmd` and
  `--export`, and count with them for `$N`.
- `--export FILE` (repeatable): the extension picks the format; `--scale` sizes rasters (pixels per
  point, default 1). A `.ait` is written as `file.saveAsTemplate` writes it.
- Output: one JSON line per step, `{"step": "open"|"cmd"|"export", "command"?, "result"}`. The first
  failure prints `vectorcraft-cli: step N (id): message` on stderr and exits 1; later steps don't run;
  nothing is rolled back (but nothing is on disk unless an earlier step wrote it).
- Also accepts the host commands `file.open`, `file.save`, `file.export`, `file.exportForScreens`,
  `tool.select`.
- **No file confinement**: `run` refuses `--automation-read-root` (`unknown run option`) **(observed)**.
  It reads and writes whatever paths it is given.

### Step references: `$N.path`

A param **string that is exactly** `$N`, `$N.path` or `$last.path` is replaced by a value from step N's
result (0-based, in run order, counting `--cmd`, `--commands` and `--export` steps; `$last` = the step
before). Paths go through objects by key and arrays by index: `"$1.id"`, `"$2.ids.0"`, `"$last.ids[0]"`.
A reference that names nothing fails the step (`step 0's result has no such value`). `"$$"` writes a
literal `$`.

**(observed)** References are resolved anywhere in `params`, nested arrays included (`"ids": ["$0.id"]`).
Strings that are not exactly a reference stay text (`"$5 off"`, `"$foo"`), but `"$1.99"` *is* one: write
`"$$1.99"`. `run` also resolves references inside the `commands` of a nested `command.batch`, against the
run's steps. The engine itself never resolves them: through `engine.execute` the command fails with
`` `id` is the step reference "$0.id", which only `run` and `command_batch` resolve ``.

### `convert` and `info`

`convert IN OUT` = open + export, with the warnings of both (`warnings`, plus `importWarnings` when reading
IN lost something). Rasters get the first artboard; PDF every artboard unless `--artboard`/`--range`.
It refuses to overwrite IN when reading it lost something, unless `--replace-lossy`. Exit 1 with
`can't open …: not a format VectorCraft reads` for unknown inputs **(observed)**.

### Environment

`VECTORCRAFT_NO_PREFS=1` (no preference reads/writes), `VECTORCRAFT_CONFIG_DIR=DIR` (isolated profile:
the CLI and headless MCP remember PDF presets, ICC profiles and installed plug-ins there),
`SOURCE_DATE_EPOCH=<seconds>` (byte-reproducible PNG/PDF/EPS/.ai/zip/native output; encrypted PDFs still
differ).

---

## 3. MCP server (`vectorcraft-cli mcp`)

stdio, newline-delimited JSON-RPC 2.0, protocol `2025-06-18` (also accepts `2025-03-26`, `2024-11-05`).

| Mode | Command | Notes |
|---|---|---|
| default | `vectorcraft-cli mcp` | connect to `127.0.0.1:7979`, else fall back to headless |
| remote | `vectorcraft-cli mcp --connect 127.0.0.1:7979` | the app must run `vectorcraft --control 7979`; each tool call is one control request; UI tools work |
| headless | `vectorcraft-cli mcp --headless` | in-process engine, CPU renderer; no `inspect_ui`/`ui_inspect`, `type_text`, `open_panel`, `screenshot {window:true}`, `ui_screenshot` |
| confined | `… mcp --automation-read-root DIR --automation-write-root DIR` (each repeatable) | implies headless; refused with `--connect`; roots must exist |

Register: `claude mcp add vectorcraft -- vectorcraft-cli mcp` (or `--headless`, or `--connect …`).
**(observed)** A headless server starts with one open document (`Untitled-1`, index 0); `file.new`
opens a second one and makes it active.

### Tools (32)

| Group | Tools |
|---|---|
| Any command | `command_run {id, params?}` = `run_command {command, params?}`; `invoke_menu {command, params?}` (UI commands too when connected) |
| Batches | `command_batch {steps: [{id, params?}], atomic?, label?, stop_on_error? = true}` |
| Catalogue | `command_list {filter?, query?, menu?, enabled_only?, brief?}` (alias `list_commands`, which spells it `enabledOnly`) |
| Inspect | `doc_inspect` = `inspect_document {depth?, childLimit?, ids?, kind?, limit?, offset?}`; `ui_inspect` = `inspect_ui` (connected only) |
| Look | `render_preview {max_side?, artboard?}`; `screenshot {path?, scale?, artboard?, window?}`; `ui_screenshot` (connected) |
| Draw / edit | `draw_path {points \| d, closed?, fill?, stroke?, strokeWidth?, dash?, cap?, join?, opacity?, name?, effects?}`; `draw_shape {shape: rectangle\|ellipse\|polygon\|star\|line, …geometry, same styling}`; `set_paint {fill?, stroke?, strokeWidth?, ids?}`; `add_text {text, x?, y?, width?, height?, fit?, path?, mode?, size?, font?, color?, justify?, vertical?, …}`; `apply_effect {effect?, params?, ids?}` (no `effect`: the catalogue); `pathfinder {operation, ids?}`; `transform {ids?, dx?, dy?, rotate?, scale?, scaleX?, scaleY?, reflect?, shear?, origin?, copy?}`; `create_graph`; `text_wrap` |
| Files | `open_file {path}`; `save_file {path?}`; `export {path?, format?, scale?, artboard?, range?, selection?, outlineText?, options?}` (no `path`: `dataBase64`) |
| Input | `select_tool {tool}`; `pointer_gesture {events, tool?, mods?}`; `press_key {key, mods?}`; `type_text {text}` (connected); `open_panel {panel}` (connected) |
| History | `undo`, `redo` |

Paint values in the drawing tools: `"#rrggbb"`, `"none"`, `[r,g,b]` (0–1), `{"c","m","y","k"}`, `{"gray"}`
or a full `paint.setFill` params object. `draw_path`/`draw_shape` style the object in the same undo step;
a refused paint leaves nothing drawn.

### `command_batch` details

- A step `id` is a command id, or `draw_path` / `draw_shape` with that tool's arguments as `params`
  (its result is the tool's, so `"$N.id"` is the new object). The reply: `completed`, `failed`,
  `results: [{ok, result|error}]`, `created` (ids made by draw steps); `isError` when a step failed.
- At most 256 steps; kept results at most 8 MiB.
- `atomic: true` wraps the edits in `edit.undoGroup.begin/end`: **one undo step** named `label`.
  **(observed)** It is not a transaction: when a step fails, the steps before it stay, as that one undo
  step; call `undo` once to remove them (check `doc_inspect` → `history` first). For all-or-nothing use
  the engine command `command.batch` (§6), which rolls back.
- **(observed)** The undo group belongs to the document that is active when the batch starts. A
  `file.new` inside an atomic batch moves the later edits to the new document, where each keeps its own
  undo step. Create or open the document in a separate call first.

### Resources, prompts, protocol

- Fixed resources: `vectorcraft://document` (summary), `vectorcraft://document/json` (full model),
  `vectorcraft://commands`. Templates: `vectorcraft://object/{id}`, `vectorcraft://command/{id}`,
  `vectorcraft://effect/{id}`, `vectorcraft://swatch/{name}` (percent-encode spaces).
- Prompts: `poster`, `icon-set`, `recolor`, `trace-and-style`, `export-set`.
- Unknown top-level tool arguments → JSON-RPC `-32602`; command failures → `isError: true` with the
  message. A call arriving while another has run for 2 s gets `-32003` (busy; it was not run).
  `notifications/cancelled` stops exports and renders at their next checkpoint (nothing written).
  Lines ≤ 16 MiB; JSON-RPC batches ≤ 64 messages.

Raw session for debugging:

```sh
printf '%s\n' \
  '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"sh","version":"0"}}}' \
  '{"jsonrpc":"2.0","method":"notifications/initialized"}' \
  '{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"command_batch","arguments":{"atomic":true,"label":"Badge","steps":[{"id":"draw_shape","params":{"shape":"rectangle","x":72,"y":72,"width":200,"height":80,"radius":12,"fill":"#1e88e5","stroke":"none"}},{"id":"text.create","params":{"x":90,"y":120,"text":"HELLO","size":28,"color":"#ffffff"}},{"id":"object.group","params":{"ids":["$0.id","$1.id"]}}]}}}' \
  | vectorcraft-cli mcp --headless
```

---

## 4. Control channel (desktop app)

```sh
vectorcraft --control 7979 [--automation-read-root DIR]... [--automation-write-root DIR]...
open -a VectorCraft --args --control 7979          # macOS
```

Loopback only (`127.0.0.1`), **no authentication**: turn it on only while you use it. Sibling Craft apps
use the same default port; if binding fails, pick another.

**Framing.** One JSON object per line, `{"id": 1, "method": "…", "params": {…}}` → `{"id": 1, "ok": true,
"result": …}` or `{"id": 1, "ok": false, "error": "…"}`. A line that isn't a JSON object with a string
`method` (or longer than 4 MiB, or not UTF-8) gets one error and the connection is **closed**. At most
16 connections; idle ones close after 5 minutes; a started line must arrive within 30 s.

**Timeouts.** No reply within 60 s → `{"ok": false, "error": "timeout: …"}`: "will not run" means it
was withdrawn (safe to retry); "still running" means it may still complete (inspect before retrying).

| Method | Params | Use |
|---|---|---|
| `engine.execute` | `{command, params}` | run any engine or UI command (key check as §1) |
| `engine.commands` | | the catalogue including UI commands, with enablement |
| `document.inspect` | `{depth?, childLimit?, ids?, kind?, limit?, offset?}` | layer tree, selection, key object, history, paint defaults |
| `ui.inspect` | | tool, view, panels, window, background jobs, open file dialog |
| `ui.menu.list` / `ui.menu.invoke` | `{command, params}` | menu tree / invoke an item |
| `ui.contextMenu.list` | | the canvas context menu |
| `ui.tool.select` / `ui.tool.list` | `{tool}` | |
| `ui.pointer` | `{events: [{kind, x, y, space?, mods?}]}` | drive the active tool like the mouse |
| `ui.key` / `ui.text` / `ui.move` / `ui.click` / `ui.drag` / `ui.wheel` | | synthetic input (shared 1,024-event queue) |
| `ui.set` | `{rulers?, grid?, smartGuides?, …}` | view toggles |
| `ui.dialog.set` / `.confirm` / `.cancel` | `{field, value}` | fill and submit the open dialog |
| `ui.screenshot` | `{path?, data?}` | window capture (needs a presented frame; fails after ~8 s when locked/minimised) |
| `ui.render` | `{path?, scale?, artboard?, data?}` | headless render of an artboard |
| `ui.resize`, `ui.focus` | | |
| `app.open` / `app.save` / `app.export` / `app.quit` | `{path}` / `{path?}` / `{path?, format?, artboard?, range?, scale?, …}` | files through the host |

Behaviour to plan for:

- **Dialogs.** A command run without the params it needs may open a dialog and answer `{"pending":
  "<dialog>"}` (Save As without a path, `file.close`/`app.quit` on a modified document → `saveChanges`).
  Finish with `ui.dialog.set` + `ui.dialog.confirm`, or `ui.dialog.cancel`. Pass `path` to skip native
  file dialogs: on macOS/Linux they return `"cancelled"` at once and wait for the person at the screen.
- **Background save/export** (default on): `app.save`/`app.export {path}` return `{path, background:
  true, status}` before the file is written; `ui.inspect` lists running jobs.
- **No `$N` resolution**: a client that replays step files resolves references itself (as
  `examples/vc_control.py play` does), or uses `vectorcraft-cli mcp --connect` + `command_batch`.
- **Confinement** is the app's own: start it with the root flags; then requests, the input they inject
  and the background jobs they start are confined; the person at the keyboard is not.

In the web build the same requests go through promises on `window.vectorcraft` (`request`, `execute`,
`commands`, `inspect`, `screenshot`, `openFile`, `captureDownloads`, `files`, `readFile`).

---

## 5. Plug-ins: sandboxed WebAssembly (ABI v1)

No native plug-ins and no scripts: per-object logic that must live *inside* VectorCraft is a `.wasm`
module run by the `wasmi` interpreter, with **no host imports** (no files, network, clock or randomness),
a fresh instance per run, fuel and memory caps (32 MiB module, 512 MiB memory, 50 M instructions per
filter call plus 4,000 per input byte, 60 s per filter run / 5 s per live-effect run / 300 s per export).

| Kind | Gets | Returns | Invoked by |
|---|---|---|---|
| `filter` | selected paths/compound paths as JSON | the new state of those objects (+ new ones); one undo step | `plugin.run {id, params?, ids?}`, Object › Plug-ins |
| `effect` | one object's geometry and paints | replacement geometry, recomputed on change (cached) | `effect.apply {effect: "plugin.<id>", params}` |
| `exporter` | the whole document as native JSON | `{dataBase64, warnings?}` | `document.export {format: "plugin.<id>"}` or its extension |

Exports: `memory`, `vc_abi_version() -> 1`, `vc_manifest() -> i64` (`(len << 32) | ptr` of the
manifest JSON), `vc_alloc(size) -> ptr`, `vc_run(input, input_len, params, params_len) -> i64`.
Manifest: `id` (reverse-DNS), `name`, `version`, `kind`, `author`, `description`, `params` (typed:
`number`, `int`, `bool`, `choice`, `string`, `numberList`, with `min`/`max`/`default`, `label`, `unit`,
`group`, `help`, `visibleWhen`; at most 256), and `extensions` for exporters. Params arrive validated
with a `_context` (`mode`, `bounds`, `artboard`, `documentData`). Output `{"error": "…"}` declines with a
message. Geometry uses points, y down; colours `{"model": "rgb"|"cmyk"|"gray"|"lab", …}` with 0–1
components.

Management: `plugin.list`, `plugin.info {id}` (with `lastError`), `plugin.install {path | dataBase64,
name?, replace?}`, `plugin.remove {id}`, `plugin.reload {path?}`. Installing copies the module into the
profile's `Plug-ins` folder, so it is back after a restart **(observed with `VECTORCRAFT_CONFIG_DIR`)**.
Not in v1: tool or panel plug-ins, host callbacks, importers, paint-changing live effects, filters on
type, images or symbols.

`examples/hello-plugin.py` writes a working 602-byte filter without a compiler (verified: install, run,
one undo step named after the plug-in). Real plug-ins: `crates/plugins/example` (Rust, `serde_json`,
`wasm32-unknown-unknown`).

---

## 6. Batches, actions and data

| Command | Params | Behaviour |
|---|---|---|
| `command.batch` | `{label?, commands: [{command, params}], artboard?}` | ONE undo step; stops at the first error and **rolls everything back** (verified). What the Actions panel plays. No `$N` resolution of its own. |
| `edit.undoGroup.begin` / `.end` | `{label?}` / `{cancel?}` | edits between them are one undo step; `cancel: true` undoes them (verified) |
| `action.batch` | `{commands, source?: folder\|datasets, folder?, includeSubdirs?, destination?: none\|saveAndClose\|folder, destinationFolder?, overrideOpen?, overrideSave?, overrideExport?, stopOnError?, label?}` | plays `commands` on every readable file of `folder`, or on every data set → `{processed: [{path\|dataset, result\|error}], count, failed, stopped}`; caps 500 items, 8 folder levels, 256 steps; no nesting |
| `variable.define` / `variable.bind` | `{name, kind: text\|visibility\|image\|graph}` / `{variable, ids?}` | Variables panel |
| `dataset.import` | `{path? \| data? \| dataBase64? \| csv?}` | CSV/TSV: first column `name`, then variable names (`#Name` visibility, `@Name` image) |
| `dataset.select` / `dataset.capture` / `dataset.list` / `dataset.export` | `{name}` / `{name?}` / `{}` / `{path?}` | |

**(observed)** `action.batch`:
- `destination: "folder"` saves a copy of every source file into `destinationFolder` *as well as* running
  the exports. To write only exports, leave `destination` out and give `destinationFolder`: with
  `overrideExport` (default true) each `document.export` goes to `destinationFolder/{stem}.{ext}`.
- Unreadable files in the folder are skipped; ones that fail to open are listed with an `error`.
- `destinationFolder` may be relative (to the working directory) but must exist.
- With `source: "datasets"`, exports are named `{FileStem}_{DataSetName}.{ext}` (an unsaved document's
  stem is `Untitled`).
- `run` exits 0 when `action.batch` ran, even with `failed > 0`: check the result.

---

## 7. `script.check`: static analysis of reference-app scripts

`script.check {path? | data? | dataBase64?, name?, includes?}` reads `.jsx`, `.jsxinc`, `.js` or `.jsxbin`
and reports what the script uses. It never runs any of it and changes nothing. With `path` +
`includes: true` it also reads `#include`d files inside the script's folder (and inside the automation
read root). In the app: File › Scripts › Check Script… (and File › Open of a `.jsx`); over the control
channel `ui.checkScript {path? | data? | dataBase64?, name?}` shows the same report (docs/mcp.md).

Reply: `name`, `kind` (`script`, `compiled`, `module`, `notText`, `tooLarge`), `lines`, `needs`
(`language`, `dom`, `files`, `menuCommands`, `dialogs`, `hostOnly`), `targets`, `directives`, `includes`
(`status`: `checked`, `missing`, `notFollowed`, `cycle`, `notRead`, `limit`, `unreadable`), `features`
(`{id, count, lines}`), `dom.members` (member chains as written, `[]` index, `()` call; variables replaced
by the chain they hold), `dom.types`, `menuCommands.strings` / `.dynamic`, `outside` (`filesWritten`,
`filesOpened`, `network`, `nativeCode`, `otherApps`, `environment`, `unseenCode`, `preferences`),
`problems` (unclosed strings/brackets, syntax newer than ES3, unknown directives…), `truncated`.

```sh
vectorcraft-cli run --cmd script.check --params '{"path": "/abs/path/Tidy Layers.jsx", "includes": true}'
```
