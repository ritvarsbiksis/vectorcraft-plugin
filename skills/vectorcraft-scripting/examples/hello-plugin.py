#!/usr/bin/env python3
"""Write a minimal VectorCraft ABI v1 object-filter plug-in, without any compiler.

The module ignores its input and adds one orange triangle: enough to see the sandbox contract
(exports memory, vc_abi_version, vc_manifest, vc_alloc, vc_run; no imports) end to end. Real
plug-ins are written in Rust/C/Zig/AssemblyScript and parse the input JSON (see docs/plugins.md
and crates/plugins/example in the VectorCraft repository).

  python3 hello-plugin.py hello.wasm
  VECTORCRAFT_CONFIG_DIR=/tmp/vc-profile vectorcraft-cli run \
    --cmd plugin.install --params '{"path": "'"$PWD"'/hello.wasm"}' \
    --cmd plugin.run --params '{"id": "org.example.hello-triangle"}' --export hello.svg

plugin.install copies the module into the profile's Plug-ins folder, so it is there on the next
start: use a throwaway VECTORCRAFT_CONFIG_DIR while experimenting. Standard library only.
"""
import json
import sys

MANIFEST = {"id": "org.example.hello-triangle", "name": "Hello Triangle", "version": "1.0.0",
            "kind": "filter", "author": "example", "description": "Adds a triangle.", "params": {}}
# Output in the input's shape: an object without "id" is new. Points, y down.
OUTPUT = {"objects": [{"type": "path", "name": "hello triangle",
                       "path": {"subpaths": [{"closed": True, "anchors": [
                           {"p": [100, 300]}, {"p": [200, 120]}, {"p": [300, 300]}]}]},
                       "fills": [{"type": "solid", "color": {"model": "rgb", "r": 0.9, "g": 0.3, "b": 0.1}}]}]}


def uleb(n):
    out = bytearray()
    while True:
        b, n = n & 0x7F, n >> 7
        out.append(b | (0x80 if n else 0))
        if not n:
            return bytes(out)


def sleb(n):
    out = bytearray()
    while True:
        b, n = n & 0x7F, n >> 7
        if (n == 0 and not b & 0x40) or (n == -1 and b & 0x40):
            out.append(b)
            return bytes(out)
        out.append(b | 0x80)


def vec(items):
    return uleb(len(items)) + b"".join(items)


def section(sid, body):
    return bytes([sid]) + uleb(len(body)) + body


def name(s):
    return uleb(len(s.encode())) + s.encode()


def func_body(code):
    b = b"\x00" + code + b"\x0b"  # no locals; end
    return uleb(len(b)) + b


def build():
    i32, i64 = b"\x7f", b"\x7e"
    manifest, output = json.dumps(MANIFEST).encode(), json.dumps(OUTPUT).encode()
    man_at, out_at, heap_at = 1024, 8192, 65536  # data offsets; vc_alloc hands out from page 1 on

    def packed(ptr, length):  # i64.const ((len << 32) | ptr)
        return b"\x42" + sleb((length << 32) | ptr)

    types = vec([b"\x60" + vec([]) + vec([i32]),            # () -> i32
                 b"\x60" + vec([]) + vec([i64]),            # () -> i64
                 b"\x60" + vec([i32]) + vec([i32]),         # (size) -> ptr
                 b"\x60" + vec([i32] * 4) + vec([i64])])    # (in, in_len, params, params_len) -> i64
    funcs = vec([uleb(0), uleb(1), uleb(2), uleb(3)])
    memory = vec([b"\x00" + uleb(64)])                      # 64 pages (4 MiB), no maximum
    heap = vec([i32 + b"\x01\x41" + sleb(heap_at) + b"\x0b"])  # mutable i32 bump pointer
    exports = vec([name("memory") + b"\x02" + uleb(0),
                   name("vc_abi_version") + b"\x00" + uleb(0),
                   name("vc_manifest") + b"\x00" + uleb(1),
                   name("vc_alloc") + b"\x00" + uleb(2),
                   name("vc_run") + b"\x00" + uleb(3)])
    code = vec([func_body(b"\x41" + sleb(1)),                 # vc_abi_version: 1
                func_body(packed(man_at, len(manifest))),      # vc_manifest
                # vc_alloc: r = heap; heap += size; return r
                func_body(b"\x23\x00\x23\x00\x20\x00\x6a\x24\x00"),
                func_body(packed(out_at, len(output)))])       # vc_run: the constant output
    data = vec([b"\x00\x41" + sleb(man_at) + b"\x0b" + uleb(len(manifest)) + manifest,
                b"\x00\x41" + sleb(out_at) + b"\x0b" + uleb(len(output)) + output])
    return (b"\x00asm\x01\x00\x00\x00" + section(1, types) + section(3, funcs) + section(5, memory)
            + section(6, heap) + section(7, exports) + section(10, code) + section(11, data))


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("usage: hello-plugin.py OUT.wasm")
    wasm = build()
    with open(sys.argv[1], "wb") as f:
        f.write(wasm)
    print("%s: %d bytes" % (sys.argv[1], len(wasm)))
