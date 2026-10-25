# Examples

VectorCraft ports of the three ExtendScript samples that shipped with the original
`adobe-illustrator-scripting` skill, plus a control-channel client and a minimal plug-in. Each was run
with `vectorcraft-cli 0.16.0` (headless); commands below assume `vectorcraft-cli` is on `PATH` and that
you run them from this folder. `VECTORCRAFT_NO_PREFS=1` keeps a run from touching your preferences.

| File | What it is |
|---|---|
| `create-color-grid.py` | generator for the colour-grid step list (stdlib Python) |
| `create-color-grid.json` | its output with the defaults (5 × 4, seed 7): 63 steps |
| `find-replace-text.json` | find and replace across every text object |
| `sample-text.svg` | input for the find-and-replace example (four point-type objects) |
| `batch-export-png.sh` | folder → PNG, through `action.batch` or a `convert` loop (POSIX sh) |
| `vc_control.py` | control-channel client for the desktop app (stdlib Python 3) |
| `hello-plugin.py` | writes a 602-byte ABI v1 filter plug-in without a compiler |

## create-color-grid (port of `create-color-grid.jsx`)

The original created a document, added a layer named "Color Grid" and drew 5 × 4 one-inch squares,
red rising with the column, green with the row, blue random, no stroke. The port keeps that, with two
changes: rows are placed from the top (`y = 72 + row × 82`, since VectorCraft's y points down) and the
random blue comes from a seeded generator, so the step file is reproducible.

```sh
vectorcraft-cli run --commands create-color-grid.json --export grid.svg --export grid.png
python3 create-color-grid.py --columns 8 --rows 6 --seed 42 | vectorcraft-cli run --commands - --export grid.svg
```

Expected: `grid.svg` has a `Color_Grid` group with 20 `<path>` squares from (72, 72) to (472, 390),
no strokes; the PNG is 612 × 792 with a transparent background. Each cell is three steps
(`shape.rectangle`, `paint.setFill {id: "$N.id"}`, `paint.setStroke {id: "$N.id", none: true}`).
The file uses `"id"` step keys, so the same array works as MCP `command_batch` `steps` (63 ≤ 256;
create the document in a separate call first if you pass `atomic: true`) and with
`vc_control.py play`.

## find-replace-text (port of `find-replace-text.jsx`)

The original prompted for two strings and replaced them in every text frame's contents. The port takes
them as params and uses `edit.findReplace`, which keeps each run's style:

```sh
vectorcraft-cli run --in sample-text.svg --commands find-replace-text.json --export replaced.svg
```

Expected output lines: `document.find` → `"total": 3` (objects containing `2025`), `edit.findReplace` →
`{"count": 4}` (occurrences), the second `document.find` → `"total": 0`; `replaced.svg` reads
"Spring Sale 2026", "Offer ends 31 May 2026", "© 2026 Example Shop. Sale items 2026 range.".

Other strings without editing the file (build the JSON with a JSON tool, not by hand):

```sh
vectorcraft-cli run --in poster.svg --cmd edit.findReplace \
  --params "$(python3 -c 'import json,sys; print(json.dumps({"find": sys.argv[1], "replace": sys.argv[2]}))' 'Old Co.' 'New Co.')" \
  --export poster-new.svg
```

`matchCase` (default false) and `wholeWord` are optional; `ids` limits it to some objects. A match
never spans two style runs.

## batch-export-png (port of `batch-export-png.jsx`)

The original exported every open document as a transparent PNG-24 of its artboard at 100 % into a
folder picked in a dialog. Headless there are no open documents and no dialogs, so the port takes an
input folder and an output folder:

```sh
./batch-export-png.sh ~/art/in ~/art/png          # action.batch, one process, subfolders included
./batch-export-png.sh ~/art/in ~/art/png 2        # @2x (2 pixels per point)
./batch-export-png.sh ~/art/in ~/art/png 1 --per-file   # one `convert` per file, top folder only
```

Set `VECTORCRAFT_CLI=/path/to/vectorcraft-cli` if it is not on `PATH`. It exits non-zero when any file
fails (an unreadable PDF is reported in `processed[].error`; files of other types are skipped). Files with
the same stem overwrite each other's PNG. For the documents open in the desktop app, which is what the
original meant, use the control client:

```sh
python3 vc_control.py export-open ~/art/png --format png --scale 1
```

## vc_control.py (control channel)

Needs the desktop app with `--control` (`open -a VectorCraft --args --control 7979` on macOS). No
dependencies beyond Python 3.

```sh
python3 vc_control.py call engine.commands | head
python3 vc_control.py call document.inspect '{"depth": 0}'
python3 vc_control.py run shape.star '{"cx": 300, "cy": 300, "radius1": 120, "radius2": 50}'
python3 vc_control.py play create-color-grid.json --atomic "Color Grid"
python3 vc_control.py --port 7980 export-open out/
```

`play` resolves `"$N.path"` references itself (the engine doesn't), starts the undo group after any
leading `file.new`/open step, and undoes the group if a step fails. `export-open` walks the tabs with
`document.activate {index}` until `no such document`, then `app.export`s each (with Background Export on,
the reply comes before the file is written). Tested through a bridge that forwards each request to a
headless `vectorcraft-cli mcp` engine; not yet against a running desktop app.

## hello-plugin.py (plug-in ABI v1)

```sh
python3 hello-plugin.py hello.wasm
VECTORCRAFT_CONFIG_DIR=/tmp/vc-profile vectorcraft-cli run \
  --cmd plugin.install --params '{"path": "'"$PWD"'/hello.wasm"}' \
  --cmd plugin.run --params '{"id": "org.example.hello-triangle"}' --export hello.svg
```

Expected: `hello.svg` holds `<path id="hello_triangle" … d="M100 300 L200 120 L300 300 Z" fill="#e64d1a"/>`.
The throwaway `VECTORCRAFT_CONFIG_DIR` matters: `plugin.install` copies the module into that profile's
`Plug-ins` folder, where every later run (and the app, for the default profile) installs it again.
