#!/usr/bin/env python3
"""Extract real source snippets for a blueprint, and check that every
`path@line@token` reference still resolves.

The reference format is one string: `path@line@token`

  path   repository-relative file path
  line   1-based line number
  token  an exact substring of that line, distinctive enough to survive
         small edits. It must not contain `@`.

Resolution rules (deliberately strict):

  1. If `token` appears on the declared line, use it.
  2. Otherwise look within +/-3 lines. This absorbs small edits that shift
     line numbers without changing the cited code.
  3. Otherwise FAIL. There is no whole-file fallback: a short token such as
     `evidence_verifier` can match an unrelated signature thousands of lines
     away, and silently quoting the wrong code is worse than reporting a
     broken reference.

Exit code is 1 when any reference fails, so this can gate a build.

Usage:
    python extract.py --root <repo> --refs refs.json --out code.json [--span 12]
    python extract.py --root <repo> --refs refs.json --check
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

DEFAULT_SPAN = 12
DRIFT_LIMIT = 3


def read_lines(root: Path, rel_path: str) -> list[str] | None:
    p = root / rel_path
    if not p.is_file():
        return None
    try:
        return p.read_text(encoding="utf-8").split("\n")
    except UnicodeDecodeError:
        return p.read_text(encoding="utf-8", errors="replace").split("\n")


def resolve(root: Path, ref: str, span: int = DEFAULT_SPAN) -> dict:
    parts = ref.split("@", 2)
    if len(parts) != 3:
        return {"ref": ref, "ok": False, "error": "expected path@line@token"}

    rel_path, line_s, token = parts
    try:
        declared = int(line_s)
    except ValueError:
        return {"ref": ref, "ok": False, "error": f"line is not an integer: {line_s}"}

    lines = read_lines(root, rel_path)
    if lines is None:
        return {"ref": ref, "ok": False, "error": f"file not found: {rel_path}"}

    actual = None
    if 1 <= declared <= len(lines) and token in lines[declared - 1]:
        actual = declared
    else:
        for delta in range(1, DRIFT_LIMIT + 1):
            for cand in (declared + delta, declared - delta):
                if 1 <= cand <= len(lines) and token in lines[cand - 1]:
                    actual = cand
                    break
            if actual is not None:
                break

    if actual is None:
        return {
            "ref": ref,
            "ok": False,
            "error": (
                f"token not found within +/-{DRIFT_LIMIT} lines of {declared} "
                f"(file has {len(lines)} lines): {token[:50]}"
            ),
        }

    start = max(1, actual - 2)
    end = min(len(lines), actual + span - 1)
    snippet = [
        {"n": i, "text": lines[i - 1], "hit": i == actual}
        for i in range(start, end + 1)
    ]

    return {
        "ref": ref,
        "ok": True,
        "path": rel_path,
        "line": actual,
        "declared_line": declared,
        "drifted": actual != declared,
        "token": token,
        "snippet": snippet,
        "total_lines": len(lines),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True, help="repository root to read code from")
    ap.add_argument("--refs", required=True, help="refs.json produced by you")
    ap.add_argument("--out", default="code.json", help="where to write snippets")
    ap.add_argument("--span", type=int, default=DEFAULT_SPAN, help="lines per snippet")
    ap.add_argument("--check", action="store_true", help="validate only, write nothing")
    args = ap.parse_args()

    root = Path(args.root).resolve()
    refs_path = Path(args.refs)
    if not root.is_dir():
        print(f"root is not a directory: {root}", file=sys.stderr)
        return 2
    if not refs_path.is_file():
        print(f"refs file not found: {refs_path}", file=sys.stderr)
        return 2

    refs_data = json.loads(refs_path.read_text(encoding="utf-8"))
    results: dict[str, dict] = {}
    ok = bad = drifted = 0

    for node_id, spec in refs_data.items():
        span = spec.get("span", args.span)
        for key, ref in spec.get("refs", {}).items():
            r = resolve(root, ref, span)
            results.setdefault(node_id, {})[key] = r
            if r["ok"]:
                ok += 1
                if r.get("drifted"):
                    drifted += 1
                    print(f"  ~ {node_id}.{key}: line drifted {r['declared_line']} -> {r['line']}")
            else:
                bad += 1
                print(f"  X {node_id}.{key}: {r['error']}")
                print(f"      {ref}")

    print(f"\n{ok + bad} references: {ok} ok, {bad} failed, {drifted} drifted")

    if args.check:
        return 0 if bad == 0 else 1

    out = Path(args.out)
    out.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"wrote {out} ({out.stat().st_size // 1024} KB)")
    return 0 if bad == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
