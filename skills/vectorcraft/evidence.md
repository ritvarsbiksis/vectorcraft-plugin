# evidence.md — VectorCraft skill claim map (for orchestrator review)

Repo: `storytold/vectorcraft` · tag **v0.15.0** · commit `705eda5dc8cb06fb665a7d6e3d32176c25f8742a`
("Release 0.15.0", 2026-10-22) · inspected 2026-10-23 · installed `/Applications/VectorCraft.app`
reports `0.15.0` and its binary prints `vectorcraft 0.15.0`.

Tiers: **implemented** (code path exists and is wired into UI/CLI) · **partial** (code exists but visibly
incomplete — the missing part is named) · **not implemented** (repo-admitted absent) · **claimed**
(self-report, not measured).

| # | Claim in SKILL.md | Evidence (repo-relative) | Tier |
|---|---|---|---|
| 1 | Clean-room pure-Rust Illustrator reimplementation; macOS/Windows/Linux/FreeBSD + WASM web; alpha at ~88% breadth (353/375 menu items, 89/92 tools, 57/57 Photoshop effects, 4/4 3D), ~75% depth, ~62% ready (57–67%) | `README.md` L14–26; `apps/vectorcraft-web/`; `xtask/src/main.rs` (`wasm`); `docs/target-app-parity.md` L39; `ROADMAP.md` L32 | implemented; parity numbers claimed/self-assessed |
| 2 | Native `.vectorcraft`/`.drawcraft`, JSON `VERSION = 4`, down-save to v1/v2 as `drawcraft`, gzip, PNG preview, compact mode, atomic saves, unknown newer keys preserved | `crates/format/src/lib.rs` L13–14, L52–65, L215–299; `crates/format/src/atomic.rs`; `docs/mcp.md` L551 | implemented |
| 3 | Multi-document tabs, artboards, layers/sublayers, 42 panel modules, dock/float panels, workspaces persist, dock groups collapse (`window.panel.collapse`), drag artwork between document tabs (400 ms) | `crates/ui-egui/src/state.rs`; `crates/ui-egui/src/workspaces.rs`; `crates/ui-egui/src/panels/` (42 panel files + `mod.rs`); `crates/ui-egui/src/menus.rs` (`window.panel.collapse`); `docs/ui-parity.md` revisions 2026-10-21; `docs/development.md` › Drag artwork between document tabs | implemented (UI.6–UI.8 and tab drag new at this tag) |
| 4 | 92 tool ids, 89 wired; tools emit commands; 780 `cmd!` engine specs + 325 UI commands; unknown params rejected | `crates/tools/src/catalog.rs` (92 `t(...)` ids); `crates/tools/src/lib.rs`; `crates/engine/src/cmd/mod.rs` (`command_specs()`); `crates/ui-egui/src/menus.rs` (`UI_COMMANDS`); `crates/ui-egui/src/menus.rs::check_params` | implemented (3 tools not wired per target-app-parity) |
| 5 | Exact curve Pathfinder, Shape Builder regions + Gap Detection, Live Paint, offset/outline/simplify, brushes (5 kinds), appearance stacks, gradients with Method Classic/Perceptual and Dither, meshes/patterns/recolor, symbols/blends/envelopes/repeats/Intertwine/Objects on Path | `crates/pathops/src/lib.rs`; `crates/engine/src/cmd/buildcmds.rs`; `crates/engine/src/cmd/gradient.rs` L23–24, L108–112; `crates/brush/src/lib.rs` L49–53; `crates/engine/src/cmd/{appearance,paint,patterncmds,recolor,opacitymask,objects_on_path,intertwine,perspgrid}.rs`; `docs/gaps.md` G11 | implemented (Shape Builder planar regions #937 still missing) |
| 6 | Type: point/area/path, threading, styles, OpenType, vertical/CJK, bidi, SEA scripts, Touch Type, hyphenation/justification, No Break, System Layout, Fractional Widths, Snap to Glyph, manual tate-chu-yoko; **Ruby** `type.ruby`; colour emoji `sbix`/`CBDT` | `docs/type-parity.md`; `crates/engine/src/cmd/typecmd.rs` L119; `crates/text/src/bitmap.rs`; `crates/ui-egui/src/panels/character.rs` L790–840; `docs/development.md` 2026-10-21/22 | implemented; Ruby is engine/render/export only (no UI panel, no type-on-path); advanced type partial |
| 7 | All 57 Photoshop-style filters, live; **Effect Gallery dialog** with 6 raster categories, stack, params, preview, one undo step; SVG Filters submenu and Pathfinder Trap still missing; Hard Mix/Soft Mix exist | `crates/effects/src/pixel/` (56 pixel ids + `blur.gaussian`); `crates/ui-egui/src/dialogs/effect_gallery.rs` (CATEGORIES, `stack_batch_params`, tests `stack_preview_is_one_interaction`, `stack_ok_is_one_undo_step`); `crates/ui-egui/src/menus.rs` (`Effect Gallery…`, `todo("Apply SVG Filter…")`); `crates/effects/src/group.rs` `PATHFINDER_EFFECTS` (12 entries incl. hardMix/softMix); `crates/pathops/src/pathfinder.rs` (no Trap); `docs/effects-parity.md` | implemented; gallery partial coverage (Blur/Pixelate/Sharpen/Video absent from it); docs say gallery missing — stale |
| 8 | 3D Revolve/Extrude & Bevel/Inflate/Rotate, 1–10 coloured lights (`MAX_LIGHTS = 10`), four lighting presets via `effect.lightingPreset`, vector face export; no materials/shadows | `crates/three-d/src/{lib.rs,lights.rs}` L4; `crates/effects/src/lighting_presets.rs` L18; `crates/engine/src/cmd/effectcmd.rs` L59–65; `docs/three-d.md`; `docs/gaps.md` G3 | partial (~25% depth; painter's algorithm) |
| 9 | Image Trace with presets, Shapes/Auto-Grouping/Gradients, measured quality | `crates/trace/src/lib.rs`; `docs/image-trace-quality.md` | implemented |
| 10 | Open/place: 31 extensions in `OPEN_EXTS`; Place adds `.txt/.rtf/.docx`; SVG strongest; PDF/.ai own reader + editing data; EPS/PS own PostScript; Affinity read-only; PSD/PSB merged only; DXF/EMF/WMF | `crates/engine/src/cmd/fileio/mod.rs` L673–710 (OPEN_EXTS), L728–736 (TEXT/RTF/DOCX), L738+ (PLACE_EXTS); `crates/eps/`; `crates/affinity/README.md`; `docs/file-format-parity.md` | implemented (with the stated per-format losses) |
| 11 | Save: `SAVE_FORMATS` = vectorcraft/template/pdf/svg/svgz/ai; `.ai` PDF-compatible by default or legacy v7 (`aiVersion: "7"`), one artboard per legacy file; no Illustrator editing data written; `.ait` template | `crates/engine/src/cmd/fileio/save.rs` L23–27; `crates/engine/src/cmd/fileio/native.rs` L77–107 (`AI_OPTIONS`); `docs/file-format-parity.md` › The main format | implemented |
| 12 | Export: 20 write formats / 19 extensions + `plugin.<id>`; PDF presets/PDF-A-2b/PDF-X-1a/3/4/layers/marks/ICC/security/DisplayDocTitle; layered PSD; WebP lossless-only with warning; Export for Screens/Selection/Office/CSS; Print+Package | `crates/engine/src/cmd/fileio/mod.rs` L524–670 (FORMATS), L716–724 (`export_extensions`); `crates/engine/src/cmd/fileio/encode.rs` L563–564; `crates/engine/src/cmd/fileio/pdf.rs`; `crates/pdf/src/output.rs` L395; `crates/engine/src/cmd/{print,css,package}.rs`; `crates/engine/src/cmd/fileio/screens.rs` | implemented |
| 13 | Affinity `.af`/`.afdesign`/`.afpub` (+ `.afphoto` by content) read-only; AF.5 master pages, tables, paragraph formats, effects, overlays, embedded docs, CMYK pixels; 51 pinned corpus, 33 current `.af` | `crates/affinity/README.md` (import table, no write); `docs/affinity-validation.md` L32/L133; `.github/workflows/affinity-corpus.yml` | implemented (read-only; no write) |
| 14 | MCP: stdio JSON-RPC 2.0, 32 tools, 5 prompts, 3 fixed resources + 4 templates, caps (16 MiB line, 64 messages, 256 steps, 8 MiB kept results, 256 MiB replies), 2 s busy guard, protocol 2025-06-18 + 2026-07-28 cache hints, stdio-only limits | `crates/mcp/src/tools.rs` (`tool_definitions`, `MAX_COMMAND_BATCH_*`); `crates/mcp/src/server.rs` L21–44; `crates/mcp/src/{prompts.rs,resources.rs}`; `docs/mcp.md` L132–200, L289–305 | implemented (stdio only) |
| 15 | Control channel: loopback JSON-lines, 28 canonical methods (29 with `command` alias), no auth, 4 MiB line, 16 connections, 60 s reply wait, 300 s idle | `apps/vectorcraft/src/control_server.rs` L26–35, L62; `crates/ui-egui/src/control.rs::handle`; `docs/control-protocol.md` L91–127 | implemented |
| 16 | CLI: 7 subcommands; `run` gains `--commands FILE` or `-` (JSON array/JSON Lines, 64 MiB/100,000 steps, `$N.path`); `convert` flags incl. `--ai-version 7`/`pdf`, `--replace-lossy`, `importWarnings`; repeatable automation roots; `commands/info/bench/perf` | `apps/vectorcraft-cli/src/main.rs` L3–10, L67–135, `read_commands`/`parse_commands`, `convert`; `apps/vectorcraft/src/automation_args.rs` (repeatable roots) | implemented |
| 17 | Plug-ins: WebAssembly ABI v1 (wasmi, no imports, fuel/memory caps), kinds filter/effect/exporter, 256 typed params, Additional Plug-ins Folder | `docs/plugins.md`; `crates/plugins/src/{lib.rs,runtime.rs,manifest.rs}` (`ABI_VERSION = 1`, `MAX_PARAMS = 256`); `crates/engine/src/cmd/prefscmds.rs` (`pluginsFolder`); `crates/engine/src/cmd/plugin.rs` | implemented |
| 18 | Actions record/play via Actions panel and `command.batch`; Batch… dialog (`action.batch`); `dataset.import` CSV/TSV with header-defined text/visibility/image/graph variables; `script.check` statically checks `.jsx/.jsxinc/.js/.jsxbin` (never runs) | `crates/ui-egui/src/panels/actions.rs`; `crates/engine/src/cmd/fileio/{action_batch.rs,batch.rs}`; `crates/engine/src/cmd/variablecmds.rs` L548 (`datasets_csv_bytes`), L779 (`dataset_import`), L1354 (spec); `crates/doc/src/variables.rs` L14–25; `crates/scriptcheck/src/lib.rs`; `crates/engine/src/cmd/scripts.rs` | implemented (reference-app scripts still cannot run) |
| 19 | 25 interface languages (24 `.tsv` + English), Turkish new, 12-key score ~82% measured, only Georgian native-reviewed, no Hindi/Arabic | `crates/ui-egui/src/i18n/*.tsv` (24 files); `crates/ui-egui/src/i18n/mod.rs` L266 (Turkish); `crates/ui-egui/src/i18n/tests.rs` L1196; `docs/localization-parity.md` L20–67 | implemented (review gaps; ROADMAP's 74% is stale) |
| 20 | Never-crash discipline (clippy denies unwrap/expect/panic/todo/unimplemented/unreachable, engine `guard`), reproducible bytes via `SOURCE_DATE_EPOCH` | root `Cargo.toml` `[workspace.lints.clippy]`; `crates/engine/src/guard.rs`; `crates/doc/src/metadata.rs` L88–108 | implemented |

## Notes for the orchestrator

- **Method**: direct `git show`/grep/read against the v0.15.0 checkout (detached, clean). No codegraph
  index exists in this repo, so no codegraph call was made. No build, no GUI launch, no app scripting was
  performed; the installed bundle was checked with its `--version` only. `git diff v0.14.0..v0.15.0`
  identified what changed (release tags are squashed, so the range is large; the tree diff is what was
  used); every carried-forward claim was re-checked at the new tag.
- **Counts vs the v0.14.0 skill**: MCP tools 32 (unchanged), prompts 5 (unchanged), resources 3+4
  (unchanged), CLI subcommands 7 (unchanged), control methods unchanged, open extensions 31 (unchanged),
  save formats 6 (unchanged), export 20/19 (unchanged). Changed/new: Photoshop filters 46/57 → **57/57**;
  interface languages 24 → **25** (Turkish); **Effect Gallery now ships** (the previous skill repeated the
  docs and called it missing); CLI `run --commands`, repeatable automation roots, MCP 2026-07-28 cache
  hints, atomic draw styling, ruby, colour emoji, 3D lighting presets, gradient Method/Dither, Japanese
  print papers, PDF `DisplayDocTitle`, Affinity AF.5, No Break/System Layout/Fractional Widths/Snap to
  Glyph/manual tate-chu-yoko, panel docking/collapse and tab artwork drag are new at this tag.
- **Biggest correction**: `crates/ui-egui/src/dialogs/effect_gallery.rs` (absent at v0.14.0, present and
  tested at v0.15.0) implements Effect → Effect Gallery… with six raster categories, Add to Stack,
  reorder/remove, params, visibility, live preview and one-undo-step application. `docs/gaps.md` G2,
  `docs/effects-parity.md` and `README.md` still say it is missing. The skill states the code truth and
  names the real remaining gap (Blur/Pixelate/Sharpen/Video groups; 47 of 57 filters are browsable).
- **Other doc contradictions found** (code treated as authoritative): `docs/gaps.md` G4 still lists Touch
  Type and Snap to Glyph as missing, but `text.touchType` and `view.snapToGlyph` exist (the latter gained
  real snapping at this tag); `docs/type-parity.md` has a duplicate stale "CJK: ruby | missing" row beside
  its "partial" row while `type.ruby` exists; `docs/file-format-parity.md` lists PS as missing while
  `FORMATS`/`OPEN_EXTS` read `.ps`; `docs/effects-parity.md` lists Pathfinder Hard Mix as missing while
  `crates/effects/src/group.rs` implements `pathfinder.hardMix` (Trap is genuinely missing); `README.md`
  "What's missing" is stale on 3D types, the Effect Gallery and Variables; `ROADMAP.md` prints 348/375,
  46/50 and 74% where `docs/target-app-parity.md` says 353/375, 44/50 and
  `docs/localization-parity.md` says ~82%. The skill flags these rather than repeating them.
- **Tier honesty**: parity percentages, checklist "done" rows and hour estimates are self-assessments
  from code against public documentation, never side-by-side with Illustrator (the repo's clean-room rule
  forbids it); the skill carries that caveat. The `vectorcraft-cli` is **not installed** on this Mac and
  the `.app` bundle holds only the desktop binary (checked), so CLI behaviour is documented from
  `apps/vectorcraft-cli/src/main.rs` and `docs/mcp.md`, not executed.
- **Uncertain items**: the exact runtime command count (780 `cmd!` source entries is a grep count; some
  specs are built in tables, so query `engine.commands` for the live number); the three unwired tools
  (docs say 89/92 without naming them); whether the Effect Gallery is exposed on the web build (the
  dialog is UI code, not checked in WASM); per-filter visual fidelity of the 57 approximate raster
  filters (docs call them approximations); the `44/50` vector-effect count (target-app table) conflicts
  with `docs/effects-parity.md`'s `46/50` and with the code (Hard Mix/Soft Mix exist, Trap does not), so
  the skill names the concrete holes instead of trusting either percentage.
