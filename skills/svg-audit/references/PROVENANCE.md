# Provenance

This skill is vendored from [svg-forge](https://github.com/Sagargupta16/svg-forge) by Sagar Gupta, MIT licence, at commit `a441c12fc1e735b6469efb9c81d6292e945acdbf`.

| Here | Upstream path | Changes |
| --- | --- | --- |
| `SKILL.md` | `skills/svg-audit/SKILL.md` | paths rewritten to this folder; plugin-install note dropped; `forge.py --theme both` fix replaced with a generic one; frames.py browser requirement and Python 3.10+ note added; "Auditing VectorCraft exports" section added; description notes VectorCraft exports |
| `scripts/validate_svg.py` | `skills/animated-svg/scripts/validate_svg.py` | none (byte-identical) |
| `scripts/frames.py` | `skills/animated-svg/scripts/frames.py` | none (byte-identical) |
| `scripts/optimize_svg.py` | `skills/animated-svg/scripts/optimize_svg.py` | none (byte-identical) |
| `references/github-readme.md` | `skills/animated-svg/references/github-readme.md` | links to non-vendored `design.md`, `timing.md` removed or inlined; `forge.py` pair step made generic |
| `references/smil-and-css.md` | `skills/animated-svg/references/smil-and-css.md` | links to non-vendored `design.md`, `timing.md`, `gotchas.md`, `optimize.md` removed or inlined |
| `references/accessibility.md` | `skills/animated-svg/references/accessibility.md` | links to non-vendored `design.md`, `timing.md`, `optimize.md` and `forge.py` mentions replaced with inline guidance |
| `references/motion.md` | `skills/motion-scene/references/motion.md` | note that the svg-forge kit helpers are not vendored |
| `references/verify.md` | `skills/motion-scene/references/verify.md` | `composition.md` budget inlined; kit example marked as not vendored |

Inlined facts (colour contrast table values, element budgets, id prefixing, reduced-motion behaviour) come from upstream `skills/animated-svg/references/design.md`, `timing.md`, `optimize.md`, `gotchas.md` and `skills/motion-scene/references/composition.md` at the same commit.

## Licence

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
