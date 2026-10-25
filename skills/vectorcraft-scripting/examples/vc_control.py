#!/usr/bin/env python3
"""Minimal client for VectorCraft's control channel (standard library only).

Start the desktop app with the channel on (loopback only, no authentication):

    vectorcraft --control 7979 [--automation-read-root DIR] [--automation-write-root DIR]
    # macOS: open -a VectorCraft --args --control 7979

Protocol: one JSON request per line, {"id", "method", "params"}; one reply per line,
{"id", "ok": true, "result"} or {"id", "ok": false, "error"}. See
docs/control-protocol.md in the VectorCraft repository.

Subcommands:
  call METHOD [PARAMS_JSON]        any control method, e.g. engine.commands, document.inspect
  run COMMAND [PARAMS_JSON]        engine.execute one command
  play STEPS.json [--atomic LABEL] replay a step file (the `vectorcraft-cli run --commands`
                                   format), resolving "$N.path" / "$last.path" here, since
                                   engine.execute does not; --atomic makes it one undo step
                                   and undoes everything if a step fails
  export-open OUT_DIR [--format png] [--scale 1]
                                   export every open document (port of batch-export-png.jsx)
"""
import argparse
import json
import os
import re
import socket
import sys


class ControlError(Exception):
    """The app answered ok: false (the message is the app's own)."""


class Control:
    def __init__(self, host="127.0.0.1", port=7979, timeout=70.0):
        # The app answers a request within 60 s or replies with a timeout error.
        self.addr = (host, port)
        self.timeout = timeout
        self.sock = None
        self.reader = None
        self.next_id = 1

    def connect(self):
        self.close()
        self.sock = socket.create_connection(self.addr, timeout=self.timeout)
        self.reader = self.sock.makefile("rb")

    def close(self):
        if self.reader:
            self.reader.close()
        if self.sock:
            self.sock.close()
        self.sock = self.reader = None

    def request(self, method, params=None):
        if self.sock is None:
            self.connect()
        rid = self.next_id
        self.next_id += 1
        line = json.dumps({"id": rid, "method": method, "params": params or {}}) + "\n"
        try:
            self.sock.sendall(line.encode("utf-8"))
            raw = self.reader.readline()
        except OSError:
            self.close()  # idle connections are closed after 5 minutes: retry once
            self.connect()
            self.sock.sendall(line.encode("utf-8"))
            raw = self.reader.readline()
        if not raw:
            self.close()
            raise ControlError("connection closed by the app before it replied")
        reply = json.loads(raw)
        if reply.get("id") != rid:
            # Refusals of a line (a 17th connection, an unreadable line) carry no id and the
            # app closes the connection: never pair a reply with the wrong request.
            self.close()
            raise ControlError(reply.get("error") or "reply id %r for request %r" % (reply.get("id"), rid))
        if not reply.get("ok"):
            raise ControlError(reply.get("error", "unknown error"))
        return reply.get("result")

    def execute(self, command, params=None):
        return self.request("engine.execute", {"command": command, "params": params or {}})


# --- step files -------------------------------------------------------------------------

REF = re.compile(r"^\$(\d+|last)((?:\.[^.\[\]]+|\[\d+\])*)$")


def resolve(value, results):
    """Resolve "$N.path" / "$last.path" the way `vectorcraft-cli run` does; "$$" is a literal $."""
    if isinstance(value, dict):
        return {k: resolve(v, results) for k, v in value.items()}
    if isinstance(value, list):
        return [resolve(v, results) for v in value]
    if not isinstance(value, str):
        return value
    if value.startswith("$$"):
        return value[1:]
    m = REF.match(value)
    if not m:
        return value  # "$5 off" and "$foo" stay text
    step = len(results) - 1 if m.group(1) == "last" else int(m.group(1))
    if not 0 <= step < len(results):
        raise ControlError("%s: there is no step %d before this one" % (value, step))
    cur = results[step]
    for key in re.findall(r"\.([^.\[\]]+)|\[(\d+)\]", m.group(2)):
        k = key[0] or key[1]
        if isinstance(cur, list) and k.isdigit() and int(k) < len(cur):
            cur = cur[int(k)]
        elif isinstance(cur, dict) and k in cur:
            cur = cur[k]
        else:
            raise ControlError("%s: step %d's result has no such value" % (value, step))
    return cur


def load_steps(path):
    with open(path, encoding="utf-8-sig") as f:
        text = f.read()
    stripped = text.lstrip()
    if stripped.startswith("["):
        steps = json.loads(stripped)
    else:  # JSON Lines
        steps = [json.loads(l) for l in text.splitlines() if l.strip()]
    out = []
    for i, s in enumerate(steps):
        cmd = s.get("command", s.get("id"))
        if not isinstance(cmd, str) or set(s) - {"command", "id", "params"}:
            raise ControlError("entry %d: a step is {command|id, params?}" % i)
        out.append((cmd, s.get("params") or {}))
    return out


# An undo group belongs to the active document, so open or create the document first.
OPENS_DOCUMENT = {"file.new", "file.open", "document.open", "file.newFromTemplate"}


def play(ctl, steps, atomic_label=None):
    results = []
    grouping = False
    try:
        for i, (cmd, params) in enumerate(steps):
            if atomic_label and not grouping and cmd not in OPENS_DOCUMENT:
                ctl.execute("edit.undoGroup.begin", {"label": atomic_label})
                grouping = True
            try:
                result = ctl.execute(cmd, resolve(params, results))
            except ControlError as e:
                raise ControlError("step %d (%s): %s" % (i, cmd, e))
            results.append(result)
            print(json.dumps({"step": i, "command": cmd, "result": result}))
    except ControlError:
        if grouping:
            ctl.execute("edit.undoGroup.end", {"cancel": True})  # undo the partial batch
        raise
    if grouping:
        ctl.execute("edit.undoGroup.end", {})
    return results


# --- batch-export-png.jsx, ported ---------------------------------------------------------

def export_open_documents(ctl, out_dir, fmt="png", scale=1.0):
    """Export every open document's first artboard. Returns the paths the app reports."""
    out_dir = os.path.abspath(out_dir)
    written = []
    index = 0
    while True:
        try:
            ctl.execute("document.activate", {"index": index})
        except ControlError as e:
            if "no such document" in str(e):
                break  # past the last tab
            raise
        title = ctl.request("document.inspect", {"depth": 0}).get("title") or "Untitled-%d" % (index + 1)
        stem = os.path.splitext(title)[0]
        path = os.path.join(out_dir, "%s.%s" % (stem, fmt))
        # Transparent background and the first artboard are the raster defaults.
        result = ctl.request("app.export", {"path": path, "format": fmt, "scale": scale})
        # With Background Export on, the reply is {path, background: true, status} at once.
        written.append(result.get("path", path) if isinstance(result, dict) else path)
        for w in (result or {}).get("warnings", []) if isinstance(result, dict) else []:
            print("warning: %s: %s" % (title, w), file=sys.stderr)
        index += 1
    return written


def main(argv=None):
    p = argparse.ArgumentParser(description="VectorCraft control-channel client")
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=int(os.environ.get("VECTORCRAFT_CONTROL_PORT", 7979)))
    sub = p.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("call")
    c.add_argument("method")
    c.add_argument("params", nargs="?", default="{}")
    r = sub.add_parser("run")
    r.add_argument("command")
    r.add_argument("params", nargs="?", default="{}")
    pl = sub.add_parser("play")
    pl.add_argument("steps")
    pl.add_argument("--atomic", metavar="LABEL")
    ex = sub.add_parser("export-open")
    ex.add_argument("out_dir")
    ex.add_argument("--format", default="png")
    ex.add_argument("--scale", type=float, default=1.0)
    a = p.parse_args(argv)

    ctl = Control(a.host, a.port)
    try:
        if a.cmd == "call":
            print(json.dumps(ctl.request(a.method, json.loads(a.params)), indent=1))
        elif a.cmd == "run":
            print(json.dumps(ctl.execute(a.command, json.loads(a.params)), indent=1))
        elif a.cmd == "play":
            play(ctl, load_steps(a.steps), a.atomic)
        elif a.cmd == "export-open":
            os.makedirs(a.out_dir, exist_ok=True)
            paths = export_open_documents(ctl, a.out_dir, a.format, a.scale)
            print("exported %d document(s)" % len(paths))
            for path in paths:
                print(path)
    except ConnectionRefusedError:
        print("nothing listens on %s:%d: start VectorCraft with --control %d" % (a.host, a.port, a.port),
              file=sys.stderr)
        return 2
    except ControlError as e:
        print("error: %s" % e, file=sys.stderr)
        return 1
    finally:
        ctl.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
