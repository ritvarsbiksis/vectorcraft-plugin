# vectorcraft-plugin

A Claude Code plugin that lets Claude draw, edit, automate and export vector art in
[**VectorCraft**](https://github.com/storytold/vectorcraft), the open-source, pure-Rust vector illustration app
(alpha). Built and tested on macOS with VectorCraft 0.16.0. It bundles:

- **`vectorcraft` MCP server**: VectorCraft's own `vectorcraft-cli mcp` (32 tools: draw, paint, text, effects,
  Pathfinder, transforms, inspect, render previews, open/save/export, any engine command, atomic batches),
  started by `scripts/start-mcp.sh`. It drives a running app live, or a headless engine when no app is running.
- **`vectorcraft` skill**: what the app can and can't do, formats, CLI flags, MCP and control tools, and a
  verification protocol.
- **`vectorcraft-scripting` skill**: VectorCraft automation through MCP batches, `vectorcraft-cli run` step
  files, the control channel and `.wasm` plug-ins, plus porting Illustrator ExtendScript (`.jsx`) to them.
- **`vectorcraft-draw` skill**: flowcharts, org charts, architecture diagrams, timelines, charts and dimensioned
  technical drawings, with a stdlib flowchart generator, exports to SVG/PDF/PNG/DXF/EMF, and LibreOffice ODG
  interop.
- **`svg-audit` skill**: ranked findings for an SVG (render targets, GitHub dark/light contrast, accessibility,
  motion, file size) from a bundled validator, including SVGs exported from VectorCraft.

```
Claude ─stdio─▶ scripts/start-mcp.sh ─exec─▶ vectorcraft-cli mcp ─tcp 127.0.0.1:7979─▶ VectorCraft app (--control 7979)
                                                    └─ or --headless: in-process engine, no app
```

## Install

Requirements: VectorCraft (desktop app optional for headless work), `vectorcraft-cli`, Claude Code.
Python 3.10+ for the `svg-audit` scripts (the flowchart generator also runs on 3.9). Chrome, Chromium or Edge
is optional, for `svg-audit`'s frame previews.

1. Add the marketplace and install the plugin (in Claude Code):
   ```
   /plugin marketplace add ritvarsbiksis/vectorcraft-plugin
   /plugin install vectorcraft-plugin@vectorcraft
   ```
2. Install `vectorcraft-cli`. On macOS it is **not** inside `VectorCraft.app`; it ships as a separate release
   asset. The script downloads it from the official GitHub release, verifies it against `SHA256SUMS.txt` and
   links it as `~/.local/bin/vectorcraft-cli`:
   ```bash
   bash ~/.claude/plugins/marketplaces/vectorcraft/scripts/install-cli.sh
   ```
   (that is where Claude Code keeps a GitHub marketplace; from a clone run `bash scripts/install-cli.sh`, or ask
   Claude to "install the VectorCraft CLI". The server's startup error also prints the exact command;
   `--version latest` installs the newest release). Linux `.deb`/`.rpm`
   packages already put it at `/usr/bin/vectorcraft-cli`. On Windows, set the plugin's `cli_path` option to
   `C:\Program Files\VectorCraft\vectorcraft-cli.exe`.
3. For live editing, start the app with its control port:
   ```bash
   open -a VectorCraft --args --control 7979
   ```
   The control port has no authentication and listens on loopback only; leave it closed when you're not using it.
4. Start a new Claude Code session (or `/reload-plugins`) and ask, for example: *"Draw a flowchart of our
   signup flow in VectorCraft and export it as SVG and PDF"*.

## Options

Set at install or later in `/plugin` › vectorcraft-plugin › configure:

| Option | Default | Effect |
| --- | --- | --- |
| `mode` | `auto` | `auto`: the running app if one listens on the port, else headless. `connect`: the app only. `headless`: no app. |
| `control_port` | `7979` | Port the app was started with (`--control PORT`). |
| `cli_path` | empty | Absolute path to `vectorcraft-cli` (or its folder). Empty searches PATH, `~/.local/bin`, `~/.cargo/bin`, `/usr/bin`, `/usr/local/bin`, `/opt/homebrew/bin`. |
| `read_roots`, `write_roots` | empty | Existing folders the agent may read from / write to. Any root confines file access and **forces headless**; to confine a live app, start it with `--automation-read-root DIR --automation-write-root DIR`. |

`auto` decides when the server starts: if you launch the app afterwards, run `/reload-plugins`. Claude Code joins
list options with commas, so a root whose path contains a comma works only as the sole root.

## Skills

| Skill | Use it for |
| --- | --- |
| `/vectorcraft-plugin:vectorcraft` | Anything about the app: capabilities, formats, flags, shortcuts, troubleshooting |
| `/vectorcraft-plugin:vectorcraft-scripting` | Batch automation, step files, control-channel clients, plug-ins, porting `.jsx` scripts |
| `/vectorcraft-plugin:vectorcraft-draw` | Diagrams, charts, technical drawings, ODG conversion |
| `/vectorcraft-plugin:svg-audit` | Reviewing an SVG before it ships (README, web, VectorCraft export) |

Claude loads them automatically when a request matches; the slash commands force them. In Claude Code the MCP
tools appear as `mcp__plugin_vectorcraft-plugin_vectorcraft__<tool>`.

## Troubleshooting

- **The `vectorcraft` server fails to start**: `vectorcraft-cli` wasn't found. Run `install-cli.sh` (step 2) or
  set `cli_path`, then `/reload-plugins`. The launcher's stderr (`claude --debug` or `/mcp`) lists every place it
  looked.
- **Changes don't show in the app**: the server started headless. Start the app with `--control 7979`, then
  `/reload-plugins`; or set `mode` to `connect` to make a missing app an error instead.
- **"not available right now: no document open"**: a freshly started app has no document (headless sessions
  start with `Untitled-1`). Open a file or run `file.new` first; Claude does this when asked to draw.
- **Reads or writes refused**: the path is outside `read_roots` / `write_roots`.

## Repository layout

```
.claude-plugin/plugin.json        plugin manifest and userConfig options
.claude-plugin/marketplace.json   marketplace "vectorcraft" listing this repo root as the plugin
.mcp.json                         registers the vectorcraft MCP server (via scripts/start-mcp.sh)
scripts/start-mcp.sh              finds vectorcraft-cli, maps the options to flags, execs `vectorcraft-cli mcp`
scripts/install-cli.sh            installs vectorcraft-cli from the official release, SHA-256 verified
skills/vectorcraft/               app reference (vendored unchanged)
skills/vectorcraft-scripting/     automation and .jsx porting (+ references/, examples/)
skills/vectorcraft-draw/          diagrams and drawings (+ references/, scripts/, examples/)
skills/svg-audit/                 SVG review (+ scripts/, references/)
```

## Development

- Load the working copy as a plugin (the root `.mcp.json` only works as a plugin, where `${CLAUDE_PLUGIN_ROOT}`
  is set; decline it if Claude Code offers it as a project server):
  ```bash
  claude --plugin-dir .
  ```
- Validate and test the install locally:
  ```bash
  claude plugin validate .
  ```
  ```bash
  claude plugin marketplace add ./
  ```
  ```bash
  claude plugin install vectorcraft-plugin@vectorcraft
  ```
- Flowchart generator tests:
  ```bash
  python3 skills/vectorcraft-draw/scripts/test_flowchart_steps.py
  ```
- Bump `version` in `.claude-plugin/plugin.json` for every release; installed users only get updates when it
  changes.

## License

MIT, see [LICENSE](LICENSE). Vendored and adapted skills keep their own MIT notices:
[THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md). VectorCraft itself is Apache-2.0 and is not bundled.
