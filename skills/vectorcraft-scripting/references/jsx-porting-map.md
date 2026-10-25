# Porting map: reference-app scripting DOM → VectorCraft

How to rewrite an ExtendScript (`.jsx`) automation for VectorCraft. The DOM names in the left column come
from the scripting model the original `adobe-illustrator-scripting` skill describes. VectorCraft runs
none of it: each row names the command id (engine command; run it with `vectorcraft-cli run`, MCP
`command_run`/`command_batch`, or control `engine.execute`), the MCP tool, or the control method that
does the same job, with its key params.

Status column: **Direct** (same job, one call), **Approx.** (close; read the note), **None** (nothing in
VectorCraft 0.16.0; do it in your client language or not at all). Every id below is in the
`vectorcraft-cli commands` catalogue of 0.16.0, except MCP tools (lower_snake_case) and control methods
(`ui.*`, `app.*`, `engine.*`) that the notes name as such.

Before porting, run `script.check` on the script (see SKILL.md › Porting workflow): its `dom.members`,
`menuCommands`, `features` and `outside` lists are the checklist for this table.

---

## 1. Coordinates, units and values

| Concept | Reference-app scripting (as the original skill documents it) | VectorCraft |
|---|---|---|
| Unit | points (72/in) | points (72/in); `file.new {width: "210 mm"}` and a few text/path lengths also take unit strings |
| Origin, y axis | bottom-left of the artboard, y grows **up** | first artboard's **top-left**, y grows **down** |
| `position` / `rectangle(top, left, w, h)` | top-left corner, top measured upward | `x`, `y` of the top-left corner, y measured downward |
| Bounds | `geometricBounds [left, top, right, bottom]` | `bounds {x, y, width, height}` in `document.inspect` / `document.node {summary: true}` (geometric; Use Preview Bounds pref for stroke-inclusive Align/Transform) |
| Opacity | 0–100 | 0–100 in commands; `document.inspect` reports 0–1 |
| RGB | 0–255 per channel | `"#rrggbb"` (preferred), or `[r, g, b]` |
| CMYK, Gray | 0–100 | `{"c","m","y","k"}`, `{"gray"}`: 0–100 and 0–1 are both read (0.16.0 observed: `{c: 100}` = `{c: 1}`); `{gray: 0}` is white, `{gray: 100}` black (ink amount) |
| Text indices | JS string indices (UTF-16) | `start`/`end` are **UTF-8 byte offsets**: `"© 2025"` has `2025` at bytes 3–7 |
| Angles | degrees | degrees; positive = counter-clockwise on screen (verified) |

**Converting y-up coordinates.** Let `H` be the first artboard's height (the original's `doc.height` for a
one-artboard document) and assume the script's origin is that artboard's bottom-left:

```
y_vc            = H - y_ai                          # a point
rectangle(top, left, w, h)  →  shape.rectangle {x: left, y: H - top, width: w, height: h}
artboardRect [l, t, r, b]   →  {x: l, y: H - t, width: r - l, height: t - b}
translate(dx, dy)           →  object.move {dx: dx, dy: -dy}
polygon/star (cx, cy, …)    →  {cx: cx, cy: H - cy, …}
matrix [a b c d tx ty] (page space)  →  object.transform {matrix: [a, -b, -c, d, tx + c*H, H*(1 - d) - ty]}
```

If the script moved its ruler origin, add that offset first; `document.rulerOrigin {artboard?}` reports
VectorCraft's (it changes what the UI shows, never command coordinates). Prefer `object.rotate`,
`object.scale`, `object.reflect`, `object.shear` with an explicit `origin: [x, y]` over hand-made
matrices.

---

## 2. Application, documents, files

| Reference DOM | VectorCraft | Status | Notes |
|---|---|---|---|
| `app` | the session: MCP server, control connection or one `run` | Approx. | there is no global object; state lives in the engine |
| `app.documents.add()`, `DocumentPreset` | `file.new {width, height, units, colorMode: "rgb"\|"cmyk", artboards, artboardLayout, bleed, preset}` | Direct | returns `{index}`; presets: `file.newPresets` |
| `app.documents.addDocument(preset)` | `file.new {preset: "<name>"}` | Direct | |
| `app.open(file)` | `document.open {path, pages?, cropTo?, password?, textAs?, layers?, colorMode?}`; MCP `open_file {path}`; control `app.open {path}`; CLI `run --in` | Direct | read `warnings`: they list what didn't come in as it was |
| `app.documents.length`, `documents[i]` | `document.activate {index}` (fails with `no such document` past the end); `ui.inspect` (app) | Approx. | headless MCP starts with one document; `run` creates one on demand |
| `app.activeDocument` | the active document; `document.activate {index}` switches | Direct | every command acts on the active document |
| `doc.name`, `doc.fullName` | `document.inspect` → `title`, `path` | Direct | |
| `doc.width`, `doc.height` | `document.inspect` → `artboards[0].width/height` | Direct | |
| `doc.documentColorSpace` | `document.inspect` → `colorMode`; change with `file.documentColorMode {mode, convert?}` | Direct | |
| `doc.rulerOrigin` | `document.rulerOrigin` / `document.setRulerOrigin {x, y}` | Direct | |
| `doc.save()`, `doc.saveAs(file, IllustratorSaveOptions)` | `document.save {path?, format?: vectorcraft\|template\|pdf\|svg\|svgz\|ai, options?}`; `file.saveAs`; `file.saveCopy`; MCP `save_file` | Approx. | `.ai` is PDF-compatible (carries the native document); `options: {aiVersion: "7"}` writes legacy v7; private editing data is never written |
| `Compatibility.ILLUSTRATOR*` | `aiVersion: "7"` or the default PDF-compatible `.ai` | Approx. | no per-version targets |
| `doc.close(SaveOptions.DONOTSAVECHANGES)` | `file.close {index?}`; `file.closeAll` | Approx. | headless closes without asking; the app opens a `saveChanges` dialog for modified documents: `ui.dialog.set {field: "discard", value: true}` + `ui.dialog.confirm` |
| `doc.print(PrintOptions)` | `file.print {preset?, settings?, path?, format?: pdf\|postscript}`; `print.setup`, `print.presets.list` | Approx. | prints through the shared spooler or to a file |
| `File`, `Folder`, `Folder.selectDialog`, `getFiles` | your client language; `file.list {path}` lists a folder (held to the read roots) | Approx. | no dialogs in automation: pass paths |
| `app.textFonts`, `textFonts.getByName` | `text.fontList {family?, style?}`; `text.fonts` (used in the document); `text.missingFonts` | Direct | fonts are named by family + style, not PostScript name |
| `app.preferences` | `prefs.list`, `prefs.get`, `prefs.set {key, value}`, `prefs.reset` | Direct | |
| `app.userInteractionLevel = DONTDISPLAYALERTS` | not needed | None | headless never shows dialogs; in the app, give commands their params (a missing `path` opens a dialog and answers `{"pending": …}`) |
| `app.redraw()` | not needed; look with `render_preview`, `screenshot`, control `ui.render` | None | |
| `app.executeMenuCommand("…")` | `engine.execute {command: "<id>"}`, control `ui.menu.invoke {command}`, MCP `invoke_menu {command}` | Approx. | menu items are command ids, not the reference app's strings: find them with `command_list {filter}` / `{menu: "Object > Path"}`; `script.check` lists the strings a script uses |
| `app.doScript(action, set)` | `command.batch {commands}` (what the Actions panel plays); `action.batch` over files/data sets | Approx. | actions are command lists, not `.aia` files |
| `#include`, `$.evalFile`, `#targetengine` | your client language's modules | None | VectorCraft loads no script code |
| `alert`, `confirm`, `prompt`, `$.writeln` | stdout of your client; command results | None | |
| `BridgeTalk`, ScriptUI palettes/dialogs, XMP, E4X, sockets | none | None | `script.check` reports them under `needs: hostOnly` |
| Startup Scripts folder | none | None | start a client from the OS instead |

---

## 3. Artboards

| Reference DOM | VectorCraft | Status | Notes |
|---|---|---|---|
| `doc.artboards[i].artboardRect` | `document.inspect` → `artboards[i]` `{x, y, width, height, name}` | Direct | convert y (§1) |
| `artboards.add(rect)` | `artboard.new {x?, y?, width?, height?, name?}` | Direct | default place: right of the last |
| `ab.name`, resize | `artboard.setProps {index, name?, x?, y?, width?, height?}` (or `artboards: [{index, …}]`) | Direct | |
| `artboards.remove(i)` | `artboard.delete {index \| indices}` | Direct | one is always left |
| `setActiveArtboardIndex(i)` | pass `artboard: i` to the command | Approx. | no engine command sets the active artboard; exports, `document.rulerOrigin`, `command.batch` take an index |
| `doc.fitArtboardToSelectedArt(i)` | `artboard.fitToSelection {index?}`, `artboard.fitToArt` | Direct | |
| rearrange | `artboard.rearrange`, `artboard.move {index, dx, dy, moveArt?}`, `artboard.duplicate` | Direct | |

---

## 4. Layers

| Reference DOM | VectorCraft | Status | Notes |
|---|---|---|---|
| `doc.layers.add()` | `layer.new {name?, top?, color?, locked?, visible?, printable?, template?}` → `{id}` | Direct | goes above the current layer; it **does not** check param spelling (0.16.0) |
| `layers.getByName(n)` | `document.find {name: n, kind: "Layer"}` → `matches[].id` | Direct | substring match: compare `name` exactly yourself |
| `layer.name/visible/locked/printable/color` | `layer.setProps {id, name?, visible?, locked?, printable?, template?, color?}` | Direct | spelling not checked: verify with `document.inspect {ids: [id]}` |
| `layer.opacity`, blend | `object.setProps {id: layerId, opacity: 0..100, blend?}` | Direct | verified on a layer |
| `doc.activeLayer = l` | `layer.setCurrent {id}` | Direct | new art goes there |
| `layer.zOrder(…)`, sublayers | `layer.move {ids, target, place: "above"\|"below"\|"inside", copy?}`; `layer.newSublayer` | Direct | |
| `item.move(layer, PLACEATBEGINNING)` | `layer.move {ids: [item], target: layerId, place: "inside"}` | Direct | inside = on top of its contents |
| `layer.remove()` | `layer.delete {ids}` | Direct | the last layer stays |
| `layer.pageItems` | `document.inspect {ids: [layerId]}` or `{kind: …}` (nodes carry `path`, their ancestors) | Direct | |

---

## 5. Page items in general

| Reference DOM | VectorCraft | Status | Notes |
|---|---|---|---|
| `doc.pageItems[i]` iteration | `document.inspect {kind?, ids?, limit?, offset?}`; `document.find {name?, kind?, text?}` | Direct | page with `limit`/`offset` on big files; `depth`/`childLimit` slice the tree |
| `item.typename` | node `kind`: `Layer`, `Group`, `Clip Group`, `Path`, `Compound Path`, `Type`, `Image`, `Rectangle`, `Rounded Rectangle`, `Ellipse`, `Symbol`, … | Direct | live shapes report their shape name, not `Path` |
| `item.uuid`, `getPageItemFromUuid` | numeric `id`; `document.node {id}` | Approx. | ids survive a native `.vectorcraft` round trip (verified) but not SVG/PDF re-import, and structural commands (`symbol.new`, `object.compoundPath.make`) give new ids: name objects and use `document.find {name}` across files |
| `item.name` | `object.setProps {id, name}` | Direct | |
| `item.hidden`, `item.locked` | `object.setProps {id, visible?, locked?}` | Direct | |
| `item.opacity`, `blendingMode` | `object.setProps {opacity?, blend?: "Multiply"…}` or `transparency.set` | Direct | |
| `item.tags` | `object.setProps {data: {key: "value"}}` (written as SVG `data-*`) | Approx. | |
| `item.duplicate()` | `edit.duplicate {ids?, dx?, dy?}`; `object.move {…, copy: true}` | Direct | |
| `item.remove()` | `edit.clear {ids?}` | Direct | |
| `item.zOrder(BRINGTOFRONT…)` | `object.arrange.bringToFront` / `bringForward` / `sendBackward` / `sendToBack` `{ids?}` | Direct | |
| `geometricBounds`/`visibleBounds`/`controlBounds` | `bounds` (geometric) | Approx. | visual bounds only through `usePreviewBounds` for Align/Transform; no control bounds |
| read geometry (`pathPoints`) | `document.node {id}` → full model: `kind.path.subpaths[].anchors[] {p, in?, out?}` | Direct | `vectorcraft://object/{id}` is the summary |

---

## 6. Paths and shapes

| Reference DOM | VectorCraft | Status | Notes |
|---|---|---|---|
| `pathItems.rectangle(top, left, w, h)` | `shape.rectangle {x, y, width, height}` | Direct | y conversion (§1) |
| `pathItems.roundedRectangle(…, r, r)` | `shape.rectangle {…, radius}`; MCP `draw_shape {shape: "rectangle", radius}` | Direct | one radius |
| `pathItems.ellipse(top, left, w, h)` | `shape.ellipse {x, y, width, height}` | Direct | |
| `pathItems.polygon(cx, cy, r, sides)` | `shape.polygon {cx, cy, radius, sides}` | Direct | |
| `pathItems.star(cx, cy, r, inner, n)` | `shape.star {cx, cy, radius1, radius2, points}` | Direct | |
| line | `shape.line {x1, y1, x2, y2}` | Direct | no fill, default stroke |
| `pathItems.add()` + `setEntirePath(pts)` | `path.create {anchors: [{x, y}], closed?}` or `{d: "M… L…"}`; MCP `draw_path {points \| d}` | Direct | `path.create` takes the new-art fill (white by default) even when open: set `paint.setFill {none: true}` |
| `pathPoints.add()`, `anchor`, `leftDirection`, `rightDirection` | `path.create {anchors: [{x, y, in: [x, y], out: [x, y]}]}` | Direct | `in` = incoming handle, `out` = outgoing |
| `PointType.SMOOTH/CORNER` | `path.convertAnchors`; MCP `draw_path` points `{x, y, in, out, smooth}` | Approx. | |
| edit anchors | `path.setAnchors`, `path.moveAnchors`, `path.insertAnchor`, `path.deleteAnchors` | Direct | read their params first |
| `closed = true` | `path.close`; `path.create {closed: true}` | Direct | |
| `filled = false`, `stroked = false` | `paint.setFill {id, none: true}`, `paint.setStroke {id, none: true}` | Direct | |
| `strokeWidth`, `strokeCap`, `strokeJoin`, `strokeMiterLimit`, `strokeDashes` | `stroke.set {ids?, weight, cap: butt\|round\|square, join: miter\|round\|bevel, miterLimit, dash: [d, g, …]}` | Direct | spelling not checked (0.16.0) |
| `fillOverprint`, `strokeOverprint` | `object.setOverprint {fill?, stroke?, ids?}`; read back with `attributes.info {ids?}` | Direct | |
| Offset Path, Outline Stroke, Simplify | `object.path.offsetPath {offset}`, `object.path.outlineStroke`, `object.path.simplify` | Direct | |
| Pathfinder | `object.pathfinder.unite` / `minusFront` / `intersect` / `exclude` / `divide` / `trim` / `merge` / `crop` / `outline` / `minusBack`; MCP `pathfinder {operation}` | Direct | live versions: `effect.apply` with a `pathfinder.*` effect on a group |

## 7. Compound paths, groups, clipping

| Reference DOM | VectorCraft | Status |
|---|---|---|
| `compoundPathItems.add()` + move paths in | `object.compoundPath.make {ids}` (members get new ids) / `object.compoundPath.release` | Direct |
| `groupItems.add()` + move items in | `object.group {ids}` → `{id}`; `object.ungroup` | Direct |
| `group.clipped = true` | `object.clippingMask.make {ids}` (topmost clips) / `object.clippingMask.release` | Direct |
| fill rule | `path.setFillRule` | Direct |

---

## 8. Text

| Reference DOM | VectorCraft | Status | Notes |
|---|---|---|---|
| `textFrames.add()` + `contents` + `position` | `text.create {x, y, text, size?, font?, style?, color?, justify?}` → `{id, bounds}`; MCP `add_text` | Direct | (x, y) is the first baseline's start |
| `textFrames.areaText(path)` | `text.createInPath {path: id, mode: "area", text}` or `text.create {…, area: {width, height, fit?}}` | Direct | `overflow` lists frames whose text doesn't fit |
| `textFrames.pathText(path)` | `text.createInPath {path: id, mode: "onPath", text, at?}` | Direct | |
| `tf.contents` (read) | `text.getRange {id}` → `{text, runs, length}`; `document.find {text}` | Direct | |
| `tf.contents = s` | `text.setText {id \| ids, text}` (keeps the first run's style) | Direct | |
| find and replace over all frames | `edit.findReplace {find, replace, matchCase?, wholeWord?, ids?}` → `{count}` (occurrences) | Direct | matches never span style runs |
| `characters[i]`, `words[]`, `textRange` | byte ranges: `text.getRange {id, start, end}`, `text.editRange {id, start, end, insert}` | Approx. | UTF-8 bytes, not words/lines |
| `characterAttributes.size/textFont/fillColor/tracking/horizontalScale/baselineShift` | `text.setRangeStyle {id, start?, end?, size, font, style, fill, tracking, hScale, vScale, baselineShift, kerning, …}`; whole object: `text.setStyle {ids, …}` | Direct | `tracking`/`kerning` in 1/1000 em |
| `paragraphAttributes.justification` | `text.setStyle {justify: left\|center\|right\|justifyAll\|auto}` | Direct | |
| indents, space before/after, hyphenation | `text.setFormat {leftIndent, rightIndent, firstLineIndent, spaceBefore, spaceAfter, hyphenate, …}` | Direct | |
| `characterStyles`, `paragraphStyles` | `charStyle.*`, `paraStyle.*` commands | Direct | list them with `command_list {filter: "charStyle"}` |
| `frame.nextFrame = other`, `stories` | `text.thread.create` (selected frames, stacking order), `text.thread.add {from, to? \| rect? \| at?}`; `text.thread.info` | Direct | |
| `tf.createOutline()` | `type.createOutlines` (on the selection: `select.set {ids}` first) | Direct | |
| legacy text items | none | None | |

---

## 9. Colour, swatches, gradients, patterns

| Reference DOM | VectorCraft | Status | Notes |
|---|---|---|---|
| `new RGBColor()` + `item.fillColor = c` | `paint.setFill {id, color: "#rrggbb"}` | Direct | `paint.setStroke` for strokes; both also set the default for new art |
| `CMYKColor`, `GrayColor`, `LabColor` | `color: {c, m, y, k}`, `{gray}`, `{l, a, b}` | Direct | in a CMYK document RGB input is stored as CMYK unless `keepModel: true` |
| `NoColor` | `{none: true}`; MCP paint `"none"` | Direct | |
| `doc.spots.add()` + `SpotColor` + `tint` | `swatch.new {name, color, spot: true}` then `paint.setFill {swatch: name, tint: 0..100}` | Direct | links stay live: `swatch.edit` recolours the art |
| `doc.swatches.getByName(n)` | `swatch.list {group?}`; resource `vectorcraft://swatch/{name}`; apply with `paint.setFill {swatch: n}` | Direct | |
| `swatchGroups` | `swatch.newGroup`, `swatch.move {names, group}` | Direct | |
| `doc.gradients.add()` + `GradientColor` | `paint.setFill {gradient: {kind: linear\|radial\|freeform, stops: [{offset 0..1, color, opacity?, midpoint?}], angle?, start?, end?}}`; save with `swatch.new {gradient}` | Direct | `paint.editGradient` edits the targeted one; `method: "perceptual"` and `dither` are VectorCraft extras |
| `PatternColor` | `object.pattern.make {ids, name}` then `paint.setFill {swatch: "<pattern>"}` (verified); `pattern.list` | Direct | |
| `doc.documentColorSpace` conversions | `file.documentColorMode {mode, convert?, grays?}`; `edit.colors.toCMYK` / `toRGB` / `toGrayscale` | Direct | |

---

## 10. Styles, brushes, symbols, effects

| Reference DOM | VectorCraft | Status | Notes |
|---|---|---|---|
| `graphicStyles[n].applyTo(item)` | `graphicStyle.apply {name, ids?, add?}`; `graphicStyle.list`, `graphicStyle.new` | Direct | |
| `brushes[n].applyTo(item)` | `brush.apply {name, ids?}`; `brush.list` | Direct | |
| `doc.symbols.getByName(n)` | `symbol.list`; `symbol.setCurrent` | Direct | |
| `symbolItems.add(sym)` + `position` | `symbol.place {name, x, y}` → `{id}` (registration point at x, y) | Direct | default: artboard centre |
| `symbols.add(item)` | `symbol.new {name, ids}` → the art becomes the symbol and is replaced by an instance (new id) | Direct | |
| `instance.breakLink()` | `symbol.breakLink {ids}` → `{ids}` | Direct | |
| `instance.symbol = other` | `symbol.replace` | Direct | read its params |
| live effects (menu items) | `effect.apply {effect, params, ids?, item?}`; `effect.list` (catalogue with defaults); `effect.setParams`, `effect.remove`; MCP `apply_effect` | Direct | effect ids look like `stylize.dropShadow`, `distort.roughen`, `blur.gaussian` |
| expand appearance | `effect.expandAppearance`, `object.expand` | Direct | |

---

## 11. Selection

| Reference DOM | VectorCraft | Status |
|---|---|---|
| `doc.selection` (read) | `document.inspect` → `selection` (ids), `selectionBounds` | Direct |
| `doc.selection = null` | `select.none` | Direct |
| `item.selected = true` | `select.set {ids}` / `select.add {ids}` / `select.toggle {ids}` | Direct |
| select all, inverse, same colour | `select.all`, `select.inverse`, `select.same.fillColor` …, `select.object.textObjects` … | Direct |
| iterate selection by type | `document.inspect {ids: selection}` and read each `kind` | Direct |

Prefer explicit `ids` over selection-driven commands in automation: results stay correct when a person
clicks in the app meanwhile, and the `$N.id` references make it cheap.

---

## 12. Transforms

| Reference DOM | VectorCraft | Status | Notes |
|---|---|---|---|
| `item.translate(dx, dy)` | `object.move {ids, dx, dy: -dy}` | Direct | y flips |
| `item.rotate(a)` | `object.rotate {ids, angle: a, origin?}` | Direct | counter-clockwise; default origin: bounding-box centre |
| `item.resize(sx, sy)` | `object.scale {ids, sx, sy, origin?, strokes?}` | Direct | percent; `strokes` = Scale Strokes & Effects |
| reflect, shear | `object.reflect {axis}`, `object.shear {angle, axis}` | Direct | |
| `item.transform(matrix)` | `object.transform {ids, matrix: [a, b, c, d, e, f]}` | Approx. | convert the matrix (§1) |
| `app.getIdentityMatrix`, `concatenate*Matrix` | compute in your client | None | |
| Transform Each | `object.transformEach` | Direct | |
| set position/size | `object.setBounds {x?, y?, width?, height?, reference?: 0..8}` | Direct | |
| align / distribute | `object.align {horizontal?, vertical?, to?}`, `object.distribute` | Direct | MCP `transform` runs move/rotate/scale/reflect/shear in one call |

---

## 13. Placed, raster and special items

| Reference DOM | VectorCraft | Status | Notes |
|---|---|---|---|
| `placedItems.add()` + `file` | `file.place {path, link?: true}` (raster stays linked; a PDF/`.ai`/native file becomes a linked placed document); `links.list`, `links.relink`, `links.embed` | Direct | |
| `rasterItems`, `rasterize()` | images (`kind: Image`); `object.rasterize {ppi?}` | Direct | |
| `TracingObject`, `TracingOptions` | `imageTrace.make {id, preset?, params?}`, `imageTrace.expand`, `imageTrace.presets` | Direct | |
| `meshItems` | `object.mesh.create {rows, cols, …}`, `object.mesh.setPointColor` | Direct | |
| `graphItems` | MCP `create_graph`; `graph.setData`, `graph.setType` | Direct | |
| `pluginItems` | none: VectorCraft plug-ins are `.wasm` filters, live effects and exporters | None | |
| `nonNativeItems` | `.ai` import draws them as a group named "Non-native art" | Approx. | read-only |
| `legacyTextItems` | none | None | |

---

## 14. Variables and data sets

| Reference DOM | VectorCraft | Status |
|---|---|---|
| `doc.variables.add()` + `kind` | `variable.define {name, kind: text\|visibility\|image\|graph}` | Direct |
| `tf.contentVariable = v`, `item.visibilityVariable = v` | `variable.bind {variable, ids}`; `variable.makeTextDynamic` etc. on the selection | Direct |
| `doc.dataSets.add()` (capture) | `dataset.capture {name?}` | Direct |
| load data | `dataset.import {csv \| path}` (header `name`, then variables; `#Name` visibility, `@Name` image) | Direct |
| `dataSet.display()` | `dataset.select {name}` | Direct |
| batch over data sets | `action.batch {source: "datasets", destinationFolder, commands: [document.export …]}` → `{FileStem}_{DataSet}.{ext}` | Direct |

---

## 15. Save and export options

All exports are `document.export {path?, format?, …options}` (MCP `export`, control `app.export`, CLI
`run --export FILE` / `convert`); the path's extension picks the format. `document.formats` lists every
format with its options and defaults.

| Reference options object | VectorCraft | Notes |
|---|---|---|
| `ExportOptionsPNG24 {transparency, artBoardClipping, horizontalScale}` | `{format: "png", scale \| ppi, background: "transparent"\|"white"\|"#rrggbb", antiAlias, artboard?, useArtboards?, rect?}` | transparent and first artboard are the defaults; `scale` = pixels per point (1 = 100 %) |
| `ExportOptionsPNG8`, `ExportOptionsGIF` | `{format: "png8"\|"gif", colors, reduction, dither, matte, transparency}` | |
| `ExportOptionsJPEG` | `{format: "jpg", quality: 0–100, colorModel, method, embedIcc}` | |
| `ExportOptionsSVG {fontType: OUTLINEFONT, …}` | `{format: "svg", outlineText: true, svg: {styling, images, objectIds, decimals, minify, responsive, preserveEditing, embedFonts, profile}}` | `convert --outline-text --decimals N` |
| `ExportOptionsTIFF` | `{format: "tiff", colorModel, lzw, byteOrder}` | |
| `ExportOptionsPhotoshop` | `{format: "psd", layers: true, maxEditability?, colorModel}` | layered PSD export; PSD *import* is the merged image only |
| `ExportOptionsAutoCAD` | `document.exportDxf` / `{format: "dxf"}` | DXF R12–2018; no DWG |
| `ExportOptionsFlash`, `FXGSaveOptions` | none | |
| `PDFSaveOptions {compatibility, preserveEditability}` | `document.exportPdf {path, preset?, standard?, compatibility: "1.3"…"2.0", range?, marks?, bleed?, security?}` or `{format: "pdf"}` | `preserveEditing` (on in the default preset) makes the PDF reopen as the native document |
| `EPSSaveOptions` | `document.exportEps` / `{format: "eps"}` | |
| `IllustratorSaveOptions` | `document.save {format: "ai"}`; `{aiVersion: "7"}` | see §2 |
| Export for Screens / Asset Export | `document.exportForScreens {folder?, artboards? \| range?, formats: [{format, scale, suffix}], …}`; `assets.*` | |
| Save for Web | `document.exportForWeb` | |
| one file per artboard | rasters: `useArtboards: true` (`<stem>-<artboard name>.<ext>`, e.g. `sheet-Artboard-1.png`); SVG: `range`; PDF/`.ai`: pages | |

---

## 16. Enumerations

| Reference enum | VectorCraft value |
|---|---|
| `DocumentColorSpace.RGB/CMYK` | `colorMode: "rgb"\|"cmyk"` |
| `StrokeCap.BUTTENDCAP/ROUNDENDCAP/PROJECTINGENDCAP` | `cap: "butt"\|"round"\|"square"` |
| `StrokeJoin.MITERENDJOIN/ROUNDENDJOIN/BEVELENDJOIN` | `join: "miter"\|"round"\|"bevel"` |
| `Justification.LEFT/CENTER/RIGHT/FULLJUSTIFY` | `justify: "left"\|"center"\|"right"\|"justifyAll"` |
| `BlendModes.MULTIPLY` … | `blend: "Multiply"`, `"Screen"`, `"Color Burn"` … (the Transparency panel labels) |
| `ElementPlacement.PLACEATBEGINNING/PLACEATEND/PLACEBEFORE/PLACEAFTER/INSIDE` | `layer.move {place: "inside"}` (top of the target), `"above"`, `"below"`; to the bottom use `object.arrange.sendToBack` after the move |
| `ZOrderMethod.*` | `object.arrange.bringToFront` / `bringForward` / `sendBackward` / `sendToBack` |
| `GradientType.LINEAR/RADIAL` | `gradient: {kind: "linear"\|"radial"}` (also `"freeform"`) |
| `TextType.POINTTEXT/AREATEXT/PATHTEXT` | `text.create` / `text.create {area}` or `text.createInPath {mode: "area"}` / `{mode: "onPath"}` |
| `VariableKind.TEXTUAL/IMAGE/VISIBILITY/GRAPH` | `kind: "text"\|"image"\|"visibility"\|"graph"` |
| `SaveOptions.DONOTSAVECHANGES` | headless `file.close`; app: `saveChanges` dialog with `discard` |
| `ExportType.*` | `format: "png"\|"png8"\|"jpg"\|"svg"\|"tiff"\|"psd"\|"dxf"\|"gif"\|…` |
| `UserInteractionLevel.*` | none (see §2) |
