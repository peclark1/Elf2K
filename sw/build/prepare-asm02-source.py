#!/usr/bin/env python3
"""Prepare disposable Visual/02 and BIOS includes for pinned public Asm/02.

The pinned upstream source has mixed include syntax, one known stray #endif,
missing STGROM BIOS aliases, and an EDTASM capitalization discrepancy.
Asm/02 substitutes macros only once and case-sensitively.  Resolve stock
constants from generated config.inc and bios.inc, not hard-coded ROM addresses.
Never change the tracked sources, configuration, or reference ROM.
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
# These are the same four BIOS service aliases defined for other Visual/02
# targets, but inadvertently absent under STGROM.
STGROM_SERVICES = {
    "FTYPE": "f_type",
    "FINMSG": "f_inmsg",
    "FMSG": "f_msg",
    "FINPUT": "f_input",
}


def read_defines(path: pathlib.Path) -> dict[str, str]:
    if not path.is_file():
        raise FileNotFoundError(f"required generated/build include missing: {path}")
    values: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        match = DEFINE.match(line)
        if match:
            _, name, _, value = match.groups()
            values[name] = value.strip()
    return values


def expand_known(value: str, definitions: dict[str, str]) -> str:
    # Preserve assembler expressions: only resolve symbolic references to
    # known generated stock constants. No eval(), address guesses, or retarget.
    return WORD.sub(lambda m: definitions.get(m.group(0), m.group(0)), value)


def normalize_bios(path: pathlib.Path, config: dict[str, str]) -> None:
    out: list[str] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        match = DEFINE.match(raw)
        if match:
            prefix, name, space, rhs = match.groups()
            raw = f"{prefix}{name}{space}{expand_known(rhs, config)}"
        out.append(raw)
    path.write_text("\n".join(out) + "\n", encoding="utf-8")


def service_aliases(bios_path: pathlib.Path, config: dict[str, str]) -> dict[str, str]:
    bios = read_defines(bios_path)
    resolved: dict[str, str] = {}
    for alias, target in STGROM_SERVICES.items():
        if target not in bios:
            raise ValueError(f"missing stock BIOS service: {target}")
        resolved[alias] = expand_known(bios[target], config)
        # A leftover BIOS/EBIOS name means we could emit a wrong ROM address.
        if re.search(r"\b(?:BIOS|EBIOS)\b", resolved[alias]):
            raise ValueError(f"unresolved BIOS service address for {alias}")
    return resolved


def normalize_visual(path: pathlib.Path, config: dict[str, str],
                     aliases: dict[str, str]) -> None:
    source = path.read_text(encoding="utf-8").splitlines()
    output: list[str] = []
    depth = 0
    in_stgrom = False
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
            prefix, name, space, rhs = definition.groups()
            line = f"{prefix}{name}{space}{expand_known(rhs, config)}"

        # The pinned assembler expands EDTASM uppercase from stock config,
        # but not the lower-case identifier used by the Visual/02 entry.
        if re.search(r"\bmov\s+r0,\s*edtasm\+3\b", line, re.IGNORECASE):
            line = re.sub(r"\bedtasm\+3\b", "EDTASM+3", line)

        directive = line.strip()
        if directive.upper() == "#IFDEF STGROM":
            in_stgrom = True
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
                    continue  # one upstream stray directive; emits no bytes
                raise ValueError(f"unexpected unmatched #endif at line {i + 1}")
            depth -= 1
            if in_stgrom and depth == 0:
                in_stgrom = False
        output.append(line)
        # Insert aliases alongside the *stock* STGROM DATA/CODE definitions.
        # Derive every value from BIOS and config; no hard-coded ROM map.
        if in_stgrom and re.match(r"^#define DATA\s+", directive):
            nearby = source[i + 1 : i + 5]
            already = any("#define FTYPE" in candidate for candidate in nearby)
            if not already:
                output.extend(f"#define {name} {rhs}" for name, rhs in aliases.items())
    if depth:
        raise ValueError(f"unclosed preprocessor conditional(s): {depth}")
    path.write_text("\n".join(output) + "\n", encoding="utf-8")


def normalize(path: pathlib.Path) -> None:
    config = read_defines(path.with_name("config.inc"))
    bios = path.with_name("bios.inc")
    aliases = service_aliases(bios, config)
    if path.name == "bios.inc":
        normalize_bios(path, config)
    else:
        normalize_visual(path, config, aliases)


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: prepare-asm02-source.py FILE", file=sys.stderr)
        return 2
    normalize(pathlib.Path(sys.argv[1]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
