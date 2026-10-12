#!/usr/bin/env python3
"""Adapt relocated Visual/02 includes to the pinned Asm/02 preprocessor.

The STG-flavored Visual/02 source mixes RcAsm-style 'include' with Asm/02
'#include'.  This Asm/02 revision only opens files through '#include', and
expects unquoted filenames.  Operate on the *disposable copy* only.
"""
from __future__ import annotations

import pathlib
import re
import sys

INCLUDE = re.compile(
    r"^(\s*)(#?include)([ \t]+)(\S+)([ \t]*(?:;.*)?)$",
    re.IGNORECASE,
)
RELOCATED = {
    "../ops.inc": "ops.inc",
    "../bios.inc": "bios.inc",
}


def normalize(path: pathlib.Path) -> None:
    output: list[str] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        match = INCLUDE.match(raw)
        if not match:
            output.append(raw)
            continue
        indent, _directive, _space, filename, tail = match.groups()
        filename = RELOCATED.get(filename, filename)
        if filename.startswith(('"', "'")) or filename.endswith(('"', "'")):
            raise ValueError(f"Asm/02 include filenames must be unquoted: {filename}")
        output.append(f"{indent}#include {filename}{tail}")
    path.write_text("\n".join(output) + "\n", encoding="utf-8")


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: prepare-asm02-source.py FILE", file=sys.stderr)
        return 2
    normalize(pathlib.Path(sys.argv[1]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
