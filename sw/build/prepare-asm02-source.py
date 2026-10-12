#!/usr/bin/env python3
"""Prepare disposable Visual/02 source for pinned public Asm/02 v1.1.

The pinned upstream source mixes 'include' and '#include', contains one
known orphan #endif, and uses nested #defines. Asm/02 expands the latter only
once, so resolve stock config.inc constants in #define RHS before assembly.
The checked-in sources and reference ROM are never modified.
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
DEFINE = re.compile(r"^(\s*#define[ \t]+)([A-Za-z_][A-Za-z0-9_]*)([ \t]+)(.*)$")
WORD = re.compile(r"\b[A-Za-z_][A-Za-z0-9_]*\b")
RELOCATED = {
    "../ops.inc": "ops.inc",
    "../bios.inc": "bios.inc",
}


def stock_defines(config_path: pathlib.Path) -> dict[str, str]:
    if not config_path.is_file():
        raise FileNotFoundError(f"stock config.inc was not generated: {config_path}")
    values: dict[str, str] = {}
    for line in config_path.read_text(encoding="utf-8").splitlines():
        match = DEFINE.match(line)
        if match:
            _prefix, name, _space, value = match.groups()
            values[name] = value.strip()
    return values


def expand_stock_constants(value: str, definitions: dict[str, str]) -> str:
    # Only literal constants from the generated stock config.inc are expanded.
    # Do not interpret assembler expressions, conditionals, or source strings.
    return WORD.sub(lambda m: definitions.get(m.group(0), m.group(0)), value)


def normalize(path: pathlib.Path) -> None:
    definitions = stock_defines(path.with_name("config.inc"))
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

        definition = DEFINE.match(line)
        if definition:
            prefix, name, space, value = definition.groups()
            line = f"{prefix}{name}{space}{expand_stock_constants(value, definitions)}"

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
                    continue  # Unmatched upstream directive, no emitted bytes.
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
