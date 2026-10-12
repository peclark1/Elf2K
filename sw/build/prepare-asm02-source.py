#!/usr/bin/env python3
"""Adapt pinned upstream Visual/02 sources to the pinned public Asm/02.

Operate ONLY on a disposable build copy.  The Visual/02 revision contains
mixed RcAsm/Asm02 include syntax and one unmatched '#endif' immediately after
the exit handler. Fail closed on any other malformed preprocessor nesting.
"""
from __future__ import annotations

import pathlib
import re
import sys

INCLUDE = re.compile(
    r"^(\s*)(#?include)([ \t]+)(\S+)([ \t]*(?:;.*)?)$",
    re.IGNORECASE,
)
IF_OPEN = re.compile(r"^#(?:if|ifdef|ifndef)\s+", re.IGNORECASE)
RELOCATED = {
    "../ops.inc": "ops.inc",
    "../bios.inc": "bios.inc",
}


def normalize(path: pathlib.Path) -> None:
    source = path.read_text(encoding="utf-8").splitlines()
    output: list[str] = []
    depth = 0
    for i, raw in enumerate(source):
        match = INCLUDE.match(raw)
        if match:
            indent, _directive, _space, filename, tail = match.groups()
            filename = RELOCATED.get(filename, filename)
            if filename.startswith(('"', "'")) or filename.endswith(('"', "'")):
                raise ValueError(f"Asm/02 include filenames must be unquoted: {filename}")
            line = f"{indent}#include {filename}{tail}"
        else:
            line = raw

        directive = line.strip()
        if IF_OPEN.match(directive):
            depth += 1
        elif directive.lower() == "#endif":
            if depth == 0:
                preceding = next((s.strip() for s in reversed(source[:i]) if s.strip()), "")
                following = next((s.strip() for s in source[i + 1:] if s.strip()), "")
                known_orphan = (
                    re.match(r"^sep\s+r0\b", preceding, re.IGNORECASE)
                    and following.upper() == "#IFDEF ANYROM"
                )
                if known_orphan:
                    # An unmatched upstream directive; no bytes or addresses
                    # are emitted by this line. Do not modify tracked source.
                    continue
                raise ValueError(f"unexpected unmatched #endif at line {i + 1}")
            depth -= 1
        output.append(line)
    if depth:
        raise ValueError(f"unclosed preprocessor conditional(s): {depth}")
    path.write_text("\n".join(output) + "\n", encoding="utf-8")


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: prepare-asm02-source.py FILE", file=sys.stderr)
        return 2
    normalize(pathlib.Path(sys.argv[1]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
