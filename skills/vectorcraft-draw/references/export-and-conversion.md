# Export and conversion for diagrams

Checked with `vectorcraft-cli 0.16.0`. Option names below come from the `document.export`,
`document.exportPdf` and `document.exportDxf` params in `vectorcraft-cli commands`; ask
`run_command document.formats` (or `vectorcraft-cli run --cmd document.formats --params '{}'`)
for every option with its default. The LibreOffice part is **UNVERIFIED** (no `soffice` on the
authoring machine).

## Three ways to export

| Where | Call |
|---|---|
| Step file / CLI | `--export out.svg` (format from the extension; `--scale N` for rasters), or a step `{"command": "document.export", "params": {"path": "out.svg", ...options}}` |
| MCP | `export {path, format?, scale?, artboard?, range?, selection?, outlineText?, options?}` |
| One file to another | `vectorcraft-cli convert IN OUT [--scale N] [--artboard I \| --range R] [--outline-text] [--decimals N]` |

Every result carries `warnings` (the loss report); `convert` also returns `importWarnings` for
what reading IN left out, and refuses to overwrite IN when reading it lost something unless
`--replace-lossy`. Treat a non-empty list as a failed check until you have read it. Without a
`path`, MCP/engine exports return `dataBase64` instead of writing a file.

Keep the master as native `.vectorcraft` (`--export diagram.vectorcraft`, `save_file`, or
`file.saveAs {path}`) and treat everything below as deliverables.

## Formats for diagrams

### SVG (web, docs, further editing)

- Layers become `<g id="LayerName">`; named objects get a sanitised `id` plus the original
  `data-name` (`node:start` -> `id="node_start" data-name="node:start"`). This is what you grep to
  prove nodes and edges exist.
- Type stays live `<text>/<tspan>` with `font-family="'Source Sans 3', sans-serif"` by default.
  Viewers without the font substitute it; for pixel-exact output use `--outline-text` /
  `outlineText: true` (tested: 0 `<text>` left, file about 12x larger) or `embedFonts: true`.
- Arrowed strokes are written as filled outline paths, not `<marker>`s.
- Options (flat or under `svg: {...}`): `decimals` (1-7, default 3), `minify`, `responsive`
  (drops width/height, keeps the viewBox), `styling` (`presentation`, `style`, `entities`,
  `css`), `objectIds` (`layerNames`, `minimal`, `unique`), `profile: "tiny12"`, `embedFonts`,
  `hiddenLayers`, `preserveEditing` (the SVG reopens as the full VectorCraft document).
- Multi-artboard: the first artboard by default; `range: "all"` writes one file per artboard,
  named `{stem}-{artboard name}.svg` (tested: `m-Artboard-1.svg` ... and the list in `files`).
- Audit the result with the **svg-audit** skill (`scripts/validate_svg.py out.svg`). Note: at
  the time of writing that validator needs Python 3.10+ (it uses `itertools.pairwise`).

### PDF (print, review, hand-off)

- One page per artboard (`artboard`, `artboards` or `range: "1-3, 5"` to choose). Text stays
  selectable text in embedded subset fonts (`advanced: {outlineText: true}` to outline).
- `document.exportPdf {path, standard}` with `pdfX4`, `pdfX1a`, `pdfX3` or `pdfA2b`. Tested:
  the files carry `%PDF-1.6` + `GTS_PDFXVersion(PDF/X-4)`, `%PDF-1.3` + `PDF/X-1:2001`, and
  `%PDF-1.7` + `pdfaid:part 2 / conformance B` respectively, with empty warnings. They were
  **not** run through an external preflight (veraPDF, Acrobat-free checkers); do that before
  promising compliance to a printer. PDF/X-1a converts colour to CMYK and flattens
  transparency; a file that would still break its standard is refused, not written.
- `createLayers: true` writes each layer as an optional content group (tested), handy for
  `Connectors` / `Nodes` / `Labels`.
- `marks: {trim: true, ...}`, `bleed: {...}`, `security: {...}` exist; see the params text.
- VectorCraft's default preset embeds the native document (`preserveEditing`), so a PDF it
  wrote reopens fully editable (`"restored": true` on open). A `standard` turns that off.

### PNG (slides, chat, previews)

- `--scale 2` (pixels per point) or `ppi: 144`; `background: "white"` (default transparent);
  `antiAlias: "type"` snaps text to pixels; `rect: [x, y, w, h]` exports an area of the page;
  `useArtboards: true` writes one PNG per artboard.
- `document.exportForOffice {path, ppi: 150, transparent?: false}` is the Save for Office PNG
  and returns its pixel `width`/`height`.

### DXF (CAD, laser and plotter)

- `.dxf` or `document.exportDxf {path, version, unit, scale, colors, preserve, outlineText,
  useArtboards}`. Default: version 2018, unit mm, true colour, `preserve: "appearance"` (type as
  outlines; strokes a CAD line cannot draw become filled outlines), origin at the artboard's
  bottom-left corner. Layers become DXF layers (hidden: off; non-printing: not plotted).
- Circles and arcs come out as native `CIRCLE`/`ARC` entities; paths as polylines and splines;
  fills as outlines and solid hatches.
- `preserve: "editability"` keeps type as `TEXT` and every stroke as a line with lineweight and
  dashes, but drops arrowheads and width profiles (with warnings). With `version: "R12"` colours
  fall back to the 256 indexed colours (warning).
- DWG is not supported (no open writer); `document.formats` says so and suggests DXF.

### EMF / WMF (Microsoft Office)

- `.emf` keeps curves, clipping, transparent images, and gradients as images clipped to their
  shape; `.wmf` flattens curves into polygons behind a placeable header. One picture of one
  artboard (`useArtboards: true` for one file per artboard). Both tested with empty warnings on
  diagrams. Prefer EMF; prefer SVG for current Office versions that accept it.

### Others

`.eps` (one file per artboard with `useArtboards`), `.ai` (PDF-compatible, carries the native
document), `.jpg`, `.webp` (lossless only), `.tif`, `.psd` (layered), `.txt` (the text only).

## Batch conversion

```sh
mkdir -p out
for f in diagrams/*.vectorcraft; do
  b=$(basename "$f" .vectorcraft)
  vectorcraft-cli convert "$f" "out/$b.pdf" || echo "FAILED $f"
  vectorcraft-cli convert "$f" "out/$b.png" --scale 2
done
```

`convert` prints one JSON object; to fail a pipeline on warnings:

```sh
vectorcraft-cli convert in.svg out.pdf | python3 -c 'import sys, json; r = json.load(sys.stdin); \
  w = r.get("warnings", []) + r.get("importWarnings", []); print(*w, sep="\n"); sys.exit(1 if w else 0)'
```

Several formats from one source in one process: `vectorcraft-cli run --in diagram.vectorcraft
--export d.svg --export d.pdf --export d.png --export d.dxf --scale 2` (`--scale` applies to the
raster outputs only).

## LibreOffice Draw interop (UNVERIFIED)

VectorCraft cannot open `.odg` (`not a format VectorCraft reads`) and cannot write it. LibreOffice
is the bridge. None of the `soffice` lines below were run while writing this skill; they follow
LibreOffice's documented command line and filter names. Test one file first and inspect it.

Install:
- macOS: `brew install --cask libreoffice`; the binary is
  `/Applications/LibreOffice.app/Contents/MacOS/soffice` (not on PATH by default).
- Debian/Ubuntu: `sudo apt install libreoffice-draw`; Fedora: `sudo dnf install libreoffice-draw`.
- Windows: `winget install TheDocumentFoundation.LibreOffice`; then `soffice.exe` in
  `C:\Program Files\LibreOffice\program\`.

ODG into VectorCraft:

```sh
soffice --headless --convert-to pdf --outdir conv/ drawing.odg   # every page; best fidelity
vectorcraft-cli info conv/drawing.pdf                            # one artboard per page, warnings
vectorcraft-cli convert conv/drawing.pdf drawing.vectorcraft
# or, for a single page:
soffice --headless --convert-to svg --outdir conv/ drawing.odg   # expect the first page only
```

Prefer PDF: it carries every page, and VectorCraft opens PDFs with layers and editable text
(`document.open {path, pages?, textAs?: "text"|"outlines"}`). Check `importWarnings` /
`warnings` for missing fonts.

VectorCraft output into ODG:

```sh
vectorcraft-cli convert diagram.vectorcraft diagram.svg
soffice --headless --convert-to odg --outdir conv/ diagram.svg                     # SVG import
soffice --headless --infilter="draw_pdf_import" --convert-to odg --outdir conv/ diagram.pdf
soffice --headless --convert-to odg --outdir conv/ diagram.emf
```

Expectations to check, not facts: SVG and PDF should arrive as editable Draw shapes; an EMF/WMF
usually arrives as one metafile picture that needs Shape > Break in Draw to become shapes; text
may be split per line. Use `--outline-text` on the SVG if fonts differ between machines.

Practical notes:
- Several files in one call: `soffice --headless --convert-to pdf --outdir conv/ *.odg`.
- A running LibreOffice window can block headless runs; give the batch its own profile:
  `soffice -env:UserInstallation=file:///tmp/lo-batch --headless --convert-to ...`.
- After conversion always reopen the result (`vectorcraft-cli info`, or open the ODG in
  LibreOffice) before deleting the source.
