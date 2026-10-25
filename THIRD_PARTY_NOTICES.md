# Third-party notices

## vectorcraft skill

`skills/vectorcraft/` (`SKILL.md`, `evidence.md`, `agents/openai.yaml`) is copied unchanged from:

- Repository: https://github.com/midasmatterhorn/artcraft-skills
- Path: `vectorcraft/`
- Commit: `8287b5eb6641c6376cde2c1ad7480648f34349ac`
- Author: midasmatterhorn (https://github.com/midasmatterhorn)
- Found via: https://www.skillsdirectory.com/skills/midasmatterhorn-vectorcraft
- License: MIT

The skill was audited against VectorCraft v0.15.0. This plugin was built and tested against v0.16.0; where the
two differ, the live command catalogue (`vectorcraft-cli commands`) is authoritative.

```
MIT License

Copyright (c) 2026 midasmatterhorn

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

## vectorcraft-scripting skill

`skills/vectorcraft-scripting/` is a port of the `adobe-illustrator-scripting` skill to VectorCraft's automation
surfaces (MCP, CLI step files, control channel, plug-ins). It was rewritten and renamed; no ExtendScript API survives.

- Repository: https://github.com/mouadja02/skills
- Path: `skills/design-and-ui/adobe-illustrator-scripting/`
- Commit: `7d3a544d78edc42d447567dc4c44a072199d3b53`
- Upstream origin: https://github.com/github/awesome-copilot (GitHub Community), modified by mouadja02
- Found via: https://www.skillsdirectory.com/skills/mouadja02-adobe-illustrator-scripting
- License: MIT

```
MIT License

Copyright GitHub, Inc.

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

## svg-audit skill

`skills/svg-audit/SKILL.md` is adapted (paths rewired to this plugin's layout, generator-specific advice
replaced) from `skills/svg-audit/SKILL.md`. The scripts in `skills/svg-audit/scripts/` and the files in
`skills/svg-audit/references/` are copied from the sibling `animated-svg` and `motion-scene` skills of the same
repository. `skills/svg-audit/references/PROVENANCE.md` lists each file's original path.

- Repository: https://github.com/Sagargupta16/svg-forge
- Commit: `a441c12fc1e735b6469efb9c81d6292e945acdbf`
- Author: Sagar Gupta (https://github.com/Sagargupta16)
- Found via: https://www.skillsdirectory.com/skills/sagargupta16-svg-audit
- License: MIT

```
MIT License

Copyright (c) 2026 Sagar Gupta

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

## vectorcraft-draw skill

`skills/vectorcraft-draw/` is original work, licensed with the rest of this plugin. Its scope (diagrams,
flowcharts, technical drawings and format conversion) was inspired by the LibreOffice Draw skill
https://github.com/mayurrathi/awesome-agent-skills/blob/main/skills/draw/SKILL.md
(found via https://www.skillsdirectory.com/skills/mayurrathi-draw). That file carries no license, so none of its
text is included here.

## VectorCraft

The plugin drives VectorCraft (https://github.com/storytold/vectorcraft, Apache-2.0) through its own
`vectorcraft-cli mcp` server. No VectorCraft code is bundled; `scripts/install-cli.sh` downloads the official
release asset and verifies it against the release's `SHA256SUMS.txt`.
