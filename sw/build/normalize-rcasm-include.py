#!/usr/bin/env python3
"""Convert the constants-only Riley BIOS include into Rc/Asm preprocessor form.

The stock bios.inc consists of conditional directives plus label/EQU constant
definitions. Public Rc/Asm is unreliable with those EQU definitions when the
file is included from another source, but its preprocessor accepts equivalent
#define expressions. This transformation is used only in the disposable Linux
verification build after TASM has assembled boots.hex.
"""

from __future__ import annotations

import pathlib
import re
import sys

EQU = re.compile(
    r"^\\s*([A-Za-z_.$?][A-Za-z0-9_.$?]*):\\s+equ\\s+(.+?)(\\s*;.*)?$",
    re.IGNORECASE,
)


def normalize(path: pathlib.Path) -> None:
    out: list[str] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        match = EQU.match(raw)
        if match:
            name, value, comment = match.groups()
            value = value.rstrip()
            out.append(f"#define {name} {value}")
            if comment:
                out.append(comment.lstrip())
        else:
            out.append(raw.expandtabs(8))
    path.write_text("\\n".join(out) + "\\n", encoding="utf-8")


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: normalize-rcasm-include.py INCLUDE", file=sys.stderr)
        return 2
    normalize(pathlib.Path(sys.argv[1]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
