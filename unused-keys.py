#!/usr/bin/env python3
# SPDX-License-Identifier: Unlicense
"""Analyze unused keybindings in Helix editor.

Compares installed Helix defaults against user config and reports
which US keyboard keys are unbound/available in each mode.
"""

import json
import os
import re
import subprocess
import sys
import tomllib
import urllib.request
from pathlib import Path


FALLBACK_VERSION = "25.07.1"

TERMINAL_CONFLICTS = {
    "C-c": "SIGINT",
    "C-z": "SIGTSTP",
    "C-s": "XOFF flow control",
    "C-q": "XON flow control",
    "C-h": "backspace in some terminals",
    "C-j": "newline in some terminals",
    "C-m": "return in some terminals",
    "C-\\": "SIGQUIT",
}


# ---------------------------------------------------------------------------
# Version detection
# ---------------------------------------------------------------------------

def detect_version():
    try:
        out = subprocess.check_output(["hx", "--version"], text=True).strip()
        m = re.search(r"(\d+\.\d+(?:\.\d+)?)", out)
        return m.group(1) if m else None
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


# ---------------------------------------------------------------------------
# Default keymap: fetch, parse, cache
# ---------------------------------------------------------------------------

def _cache_path(version):
    base = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache"))
    return base / "helix" / f"default-keymap-{version}.json"


def _fetch_source(version):
    url = (
        f"https://raw.githubusercontent.com/helix-editor/helix/"
        f"{version}/helix-term/src/keymap/default.rs"
    )
    try:
        req = urllib.request.Request(
            url, headers={"User-Agent": "helix-unused-keys/1.0"}
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.read().decode()
    except Exception as e:
        print(f"Warning: fetch failed ({e})", file=sys.stderr)
        return None


# ---------------------------------------------------------------------------
# Rust keymap!() parser
# ---------------------------------------------------------------------------

def _strip_comments(source):
    lines = []
    for line in source.splitlines():
        out = []
        in_str = False
        i = 0
        while i < len(line):
            if in_str:
                if line[i] == "\\" and i + 1 < len(line):
                    out.append(line[i : i + 2])
                    i += 2
                    continue
                if line[i] == '"':
                    in_str = False
            else:
                if line[i] == '"':
                    in_str = True
                elif line[i : i + 2] == "//":
                    break
            out.append(line[i])
            i += 1
        lines.append("".join(out))
    return "\n".join(lines)


_TOKEN_RE = re.compile(
    r'"(?:[^"\\]|\\.)*"'
    r"|=>"
    r"|\|"
    r"|[{},=]"
    r"|[a-zA-Z_]\w*"
)


def _extract_blocks(source):
    blocks = []
    pat = "keymap!({"
    i = 0
    while True:
        idx = source.find(pat, i)
        if idx == -1:
            break
        start = idx + len(pat)
        depth = 1
        j = start
        in_str = False
        while j < len(source) and depth > 0:
            ch = source[j]
            if in_str:
                if ch == "\\" and j + 1 < len(source):
                    j += 2
                    continue
                if ch == '"':
                    in_str = False
            else:
                if ch == '"':
                    in_str = True
                elif ch == "{":
                    depth += 1
                elif ch == "}":
                    depth -= 1
                    if depth == 0:
                        break
            j += 1
        blocks.append(source[start:j])
        i = j + 1
    return blocks


def _unquote(tok):
    return tok[1:-1].replace('\\"', '"').replace("\\\\", "\\")


def _parse_bindings(tokens, pos):
    bindings = {}
    while pos < len(tokens):
        tok = tokens[pos]
        if tok == "}":
            return bindings, pos
        if not tok.startswith('"'):
            pos += 1
            continue

        keys = [_unquote(tok)]
        pos += 1
        while pos < len(tokens) and tokens[pos] == "|":
            pos += 1
            if pos < len(tokens) and tokens[pos].startswith('"'):
                keys.append(_unquote(tokens[pos]))
                pos += 1

        if pos >= len(tokens) or tokens[pos] != "=>":
            continue
        pos += 1

        if pos < len(tokens) and tokens[pos] == "{":
            pos += 1
            if pos < len(tokens) and tokens[pos].startswith('"'):
                pos += 1
            while (
                pos < len(tokens)
                and not tokens[pos].startswith('"')
                and tokens[pos] != "}"
            ):
                pos += 1
            sub, pos = _parse_bindings(tokens, pos)
            if pos < len(tokens) and tokens[pos] == "}":
                pos += 1
            for key in keys:
                bindings[key] = {"_sub": True, **sub}
        elif pos < len(tokens):
            cmd = tokens[pos]
            pos += 1
            for key in keys:
                bindings[key] = cmd

        if pos < len(tokens) and tokens[pos] == ",":
            pos += 1

    return bindings, pos


def _deep_copy(obj):
    if isinstance(obj, dict):
        return {k: _deep_copy(v) for k, v in obj.items()}
    return obj


def _deep_merge(base, over):
    for k, v in over.items():
        if k in base and isinstance(base[k], dict) and isinstance(v, dict):
            _deep_merge(base[k], v)
        else:
            base[k] = v


def parse_default_source(source):
    source = _strip_comments(source)
    blocks = _extract_blocks(source)
    if len(blocks) < 3:
        return None

    modes = {}
    for block, name in zip(blocks, ("normal", "select_over", "insert")):
        toks = _TOKEN_RE.findall(block)
        start = 1 if toks and toks[0].startswith('"') else 0
        bindings, _ = _parse_bindings(toks, start)
        modes[name] = bindings

    select = _deep_copy(modes["normal"])
    _deep_merge(select, modes["select_over"])

    return {
        "normal": modes["normal"],
        "select": select,
        "insert": modes["insert"],
    }


# ---------------------------------------------------------------------------
# Fallback for 25.07.1
# ---------------------------------------------------------------------------

def _build_fallback():
    S = {"_sub": True}
    n = {}
    for k in "h j k l t f T F r R v G : i I a A o O d c C s S ;".split():
        n[k] = "bound"
    for k in "n N u U y p P Q q > < = J K & _ ( ) % x X / ? *".split():
        n[k] = "bound"
    for k in "| ! $".split():
        n[k] = "bound"
    for k in ('~', '`', '"', ',', "esc", "tab", "home", "end",
              "left", "right", "up", "down", "pageup", "pagedown"):
        n[k] = "bound"
    for k in ("C-a", "C-b", "C-c", "C-d", "C-f", "C-i", "C-o",
              "C-s", "C-u", "C-x", "C-z"):
        n[k] = "bound"
    for k in ("A-.", "A-`", "A-d", "A-c", "A-C", "A-s", "A-minus",
              "A-_", "A-;", "A-o", "A-i", "A-I", "A-p", "A-n",
              "A-e", "A-b", "A-a", "A-x", "A-*", "A-u", "A-U",
              "A-J", "A-K", "A-,", "A-(", "A-)", "A-:", "A-|", "A-!"):
        n[k] = "bound"
    for k in ("g", "m", "[", "]", "space", "z", "Z", "C-w"):
        n[k] = dict(S)

    ins = {}
    for k in ("esc", "tab", "S-tab", "up", "down", "left", "right",
              "pageup", "pagedown", "home", "end",
              "backspace", "S-backspace", "del", "ret"):
        ins[k] = "bound"
    for k in ("C-s", "C-x", "C-r", "C-w", "C-u", "C-k",
              "C-h", "C-d", "C-j"):
        ins[k] = "bound"
    for k in ("A-backspace", "A-d", "A-del"):
        ins[k] = "bound"

    return {"normal": n, "select": _deep_copy(n), "insert": ins}


def get_default_keymap(version):
    cp = _cache_path(version)
    if cp.exists():
        try:
            with open(cp) as f:
                km = json.load(f)
            if km:
                print(f"Loaded cached defaults ({cp.name})", file=sys.stderr)
                return km
        except Exception:
            pass

    source = _fetch_source(version)
    if source:
        km = parse_default_source(source)
        if km:
            cp.parent.mkdir(parents=True, exist_ok=True)
            with open(cp, "w") as f:
                json.dump(km, f, separators=(",", ":"))
            print(f"Fetched and cached defaults for {version}", file=sys.stderr)
            return km

    print("Using built-in fallback keymap.", file=sys.stderr)
    return _build_fallback()


# ---------------------------------------------------------------------------
# US keyboard key set
# ---------------------------------------------------------------------------

def _us_keys():
    cats = {}
    cats["Lowercase letters"] = list("abcdefghijklmnopqrstuvwxyz")
    cats["Uppercase letters"] = list("ABCDEFGHIJKLMNOPQRSTUVWXYZ")
    cats["Digits"] = [str(d) for d in range(10)]
    cats["Symbols"] = sorted(
        set(list("`-=[]\\;',./") + list("~!@#$%^&*()_+{}|:<>?") + ['"']),
        key=ord,
    )
    cats["Ctrl"] = [f"C-{c}" for c in "abcdefghijklmnopqrstuvwxyz"]

    alt = set()
    for c in "abcdefghijklmnopqrstuvwxyz":
        alt.add(f"A-{c}")
    for c in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
        alt.add(f"A-{c}")
    for c in "`=[]\\;',./~!@#$%^&*()_+{}|:<>?":
        alt.add(f"A-{c}")
    alt.add('A-"')
    alt.add("A-minus")
    cats["Alt"] = sorted(alt)

    cats["Special"] = [
        "space", "ret", "tab", "backspace", "del", "esc",
        "home", "end", "pageup", "pagedown",
    ]
    return cats


# ---------------------------------------------------------------------------
# User config
# ---------------------------------------------------------------------------

def _load_user_config():
    p = Path.home() / ".config" / "helix" / "config.toml"
    if not p.exists():
        return {}
    with open(p, "rb") as f:
        return tomllib.load(f)


def _flatten_user(section):
    if not isinstance(section, dict):
        return {}
    result = {}
    for key, val in section.items():
        if isinstance(val, dict):
            inner = {"_sub": True}
            for k, v in val.items():
                if isinstance(v, dict):
                    inner[k] = {"_sub": True}
                elif isinstance(v, list):
                    inner[k] = "macro"
                else:
                    inner[k] = str(v)
            result[key] = inner
        elif isinstance(val, list):
            result[key] = "macro"
        elif isinstance(val, str):
            result[key] = val
        else:
            result[key] = str(val)
    return result


# ---------------------------------------------------------------------------
# Analysis
# ---------------------------------------------------------------------------

def _build_effective(defaults, user):
    eff = _deep_copy(defaults) if isinstance(defaults, dict) else {}
    if not isinstance(user, dict):
        return eff
    for k, v in user.items():
        if isinstance(v, dict) and k in eff and isinstance(eff[k], dict):
            _deep_merge(eff[k], v)
        else:
            eff[k] = v
    return eff


def _analyze(effective, key_cats):
    bound = set()
    freed = set()
    for k, v in effective.items():
        if k == "_sub":
            continue
        if isinstance(v, str) and v == "no_op":
            freed.add(k)
        else:
            bound.add(k)

    available = {}
    for cat, keys in key_cats.items():
        avail = [k for k in keys if k not in bound]
        if avail:
            available[cat] = avail

    return bound, available


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

def _fmt(k):
    if "`" in k:
        return f"`` {k} ``"
    return f"`{k}`"


def _print_report(version, analysis):
    print("# Helix Keybinding Analysis\n")
    print(f"**Version:** {version}  ")
    print(f"**Config:** `~/.config/helix/config.toml`\n")

    print("## Summary\n")
    rows = []
    for mode, (bound, avail) in analysis.items():
        n_avail = sum(len(v) for v in avail.values())
        rows.append((mode.title(), str(len(bound)), str(n_avail)))
    headers = ("Mode", "Bound", "Available")
    widths = [
        max(len(h), *(len(r[i]) for r in rows))
        for i, h in enumerate(headers)
    ]
    def row(cells, aligns):
        parts = []
        for c, w, a in zip(cells, widths, aligns):
            parts.append(c.rjust(w) if a == ">" else c.ljust(w))
        return "| " + " | ".join(parts) + " |"
    aligns = ("<", ">", ">")
    print(row(headers, aligns))
    seps = []
    for w, a in zip(widths, aligns):
        seps.append("-" * (w - 1) + ":" if a == ">" else "-" * w)
    print("| " + " | ".join(seps) + " |")
    for r in rows:
        print(row(r, aligns))
    print()

    for mode, (bound, avail) in analysis.items():
        print(f"## {mode.title()} Mode\n")

        if not avail:
            print("*All keys bound.*\n")
            continue

        skip_insert = {"Lowercase letters", "Uppercase letters", "Digits", "Symbols", "Special"}
        for cat, keys in avail.items():
            if mode == "insert" and cat in skip_insert:
                continue
            print(f"**{cat}:** {', '.join(_fmt(k) for k in keys)}\n")

        all_keys = {k for keys in avail.values() for k in keys}
        conflicts = [
            (k, r)
            for k, r in sorted(TERMINAL_CONFLICTS.items())
            if k in all_keys
        ]
        if conflicts:
            print(
                "> **Terminal conflicts:** "
                + ", ".join(f"`{k}` ({r})" for k, r in conflicts)
                + "\n"
            )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    include_alt = "--include-alt-key-combinations" in sys.argv

    version = detect_version()
    if not version:
        print("Error: `hx --version` failed. Is Helix installed?", file=sys.stderr)
        sys.exit(1)

    print(f"Helix {version}", file=sys.stderr)

    defaults = get_default_keymap(version)
    if not defaults:
        print("Error: could not load default keymap.", file=sys.stderr)
        sys.exit(1)

    config = _load_user_config()
    user_keys = config.get("keys", {})
    key_cats = _us_keys()
    if not include_alt:
        key_cats.pop("Alt", None)

    analysis = {}
    for mode in ("normal", "select", "insert"):
        user_mode = _flatten_user(user_keys.get(mode, {}))
        effective = _build_effective(defaults.get(mode, {}), user_mode)
        analysis[mode] = _analyze(effective, key_cats)

    _print_report(version, analysis)


if __name__ == "__main__":
    main()
