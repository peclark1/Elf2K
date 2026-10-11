#!/usr/bin/env python3
"""Normalize historical Rc/Asm source without changing assembled semantics.

Some STG/Riley sources put a label and instruction on the same physical line.
Public Rc/Asm versions can mis-handle symbolic operands on those lines.  The
historical private build environment did not.  Splitting the label onto its own
line is byte-neutral and makes the source assemble with public Rc/Asm.
"""

from __future__ import annotations

import pathlib
import re
import sys

# Rc/Asm treats a trailing semicolon comment on INCLUDE as part of the
# filename. Keep the comment on its own line to preserve source history.
INCLUDE_WITH_COMMENT = re.compile(
    r"^(\\s*include\\s+\\S+?)\\s+(;.*)$", re.IGNORECASE
)

LABEL_AND_CODE = re.compile(
    r"^([A-Za-z_.$?][A-Za-z0-9_.$?]*:)([ \t]+)(?=\S)(.*)$"
)


def normalize(path: pathlib.Path) -> None:
    out: list[str] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        # Tabs are harmless in operands but expanding them avoids historical
        # Rc/Asm column/parser surprises.
        line = raw.expandtabs(8)
        include = INCLUDE_WITH_COMMENT.match(line)
        if include:
            out.append(include.group(1))
            out.append(include.group(2))
            continue
        match = LABEL_AND_CODE.match(line)
        if match and not match.group(3).lstrip().startswith(";"):
            rest = match.group(3)
            opcode = rest.lstrip().split(None, 1)[0].lower()
            # EQU needs the label on the same physical line because Rc/Asm
            # applies the directive to its current parsed label.
            if opcode not in {"equ", ".equ"}:
                out.append(match.group(1))
                out.append("        " + rest)
                continue
        out.append(line)
    path.write_text("\n".join(out) + "\n", encoding="utf-8")


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: normalize-rcasm.py SOURCE", file=sys.stderr)
        return 2
    normalize(pathlib.Path(sys.argv[1]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
