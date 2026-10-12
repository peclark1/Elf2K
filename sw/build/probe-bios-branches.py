#!/usr/bin/env python3
"""Advance one reference-backed short/long branch trial in a disposable BIOS copy."""
import re
import sys
from pathlib import Path

LONG_TO_SHORT = {0xC0: (0x30, "lbr", "br"),
                 0xC1: (0x31, "lbq", "bq"),
                 0xC2: (0x32, "lbz", "bz"),
                 0xC3: (0x33, "lbdf", "bdf"),
                 0xC9: (0x39, "lbnq", "bnq"),
                 0xCA: (0x3A, "lbnz", "bnz"),
                 0xCB: (0x3B, "lbnf", "bnf")}

def load(path, bias):
    image = bytearray(b"\xff" * 32768)
    for raw in Path(path).read_text(encoding="ascii").splitlines():
        if not raw:
            continue
        data = bytes.fromhex(raw[1:])
        count, addr, typ = data[0], int.from_bytes(data[1:3], "big"), data[3]
        if typ == 1:
            break
        if typ != 0:
            raise ValueError("unsupported Intel HEX record")
        if (sum(data) & 255) or len(data) != count + 5:
            raise ValueError("invalid Intel HEX record")
        for i, value in enumerate(data[4:4 + count]):
            offset = addr + i - bias
            if 0 <= offset < len(image):
                image[offset] = value
    return image

def main():
    if len(sys.argv) != 5:
        print("usage: probe-bios-branches.py REF.hex bios.hex bios.lst bios.asm", file=sys.stderr)
        return 2
    reference, compiled, listing, source = map(Path, sys.argv[1:])
    orig, curr = load(reference, 0), load(compiled, 0x8000)
    lo, hi = 0xF300 - 0x8000, 0x10000 - 0x8000
    mismatches = [i for i in range(lo, hi) if orig[i] != curr[i]]
    if not mismatches:
        print("BIOS EXACT MATCH: stop")
        return 1
    address = mismatches[0] + 0x8000
    expected, actual = orig[mismatches[0]], curr[mismatches[0]]
    print(f"before: {len(mismatches)} differences; first=0x{address:04X} ref={expected:02X} built={actual:02X}")
    choice = LONG_TO_SHORT.get(actual)
    if choice is None or choice[0] != expected:
        print("NOT a recognizable short/long branch pair; no edit")
        return 1
    _, oldop, newop = choice
    found = []
    for line in listing.read_text(errors="replace").splitlines():
        match = re.match(r"\s*\d+\s+([0-9a-fA-F]{4}):\s+([0-9a-fA-F]{2})\s+", line)
        if match and int(match[1], 16) == address and int(match[2], 16) == actual:
            code = re.search(r"\b" + oldop + r"\s+([\w.$?]+)\b", line, re.IGNORECASE)
            if code:
                found.append(code[1])
    if len(found) != 1:
        print(f"Unable to unambiguously locate {oldop} at 0x{address:04X}: {found}")
        return 1
    target = found[0]
    body = source.read_text()
    pattern = r"(?im)^(\s*)" + re.escape(oldop) + r"(\s+)" + re.escape(target) + r"\b"
    revised, count = re.subn(pattern, lambda m: m.group(1) + newop + m.group(2) + target, body)
    if count != 1:
        print(f"Source {oldop} {target} not unique ({count}); no edit")
        return 1
    source.write_text(revised)
    print(f"TRIAL PATCH 0x{address:04X} {oldop.upper()} {target} -> {newop.upper()} {target}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
