#!/usr/bin/env python3
"""Compare two 27C256 Intel HEX images as 32 KiB ROM byte streams."""
from __future__ import annotations
import hashlib
import pathlib
import sys

ROM_SIZE = 32768
LOGICAL_BASE = 0x8000

def load_hex(path: pathlib.Path) -> bytearray:
    image = bytearray([0xFF]) * ROM_SIZE
    upper = 0
    seen = set()
    for lineno, raw in enumerate(path.read_text(encoding="ascii").splitlines(), 1):
        line = raw.strip()
        if not line:
            continue
        if not line.startswith(":"):
            raise ValueError(f"{path}:{lineno}: not Intel HEX")
        rec = bytes.fromhex(line[1:])
        count = rec[0]
        if len(rec) != count + 5 or (sum(rec) & 0xFF):
            raise ValueError(f"{path}:{lineno}: invalid Intel HEX record")
        addr = (rec[1] << 8) | rec[2]
        rtype = rec[3]
        data = rec[4:4 + count]
        if rtype == 0:
            absolute = upper + addr
            for offset, value in enumerate(data):
                target = absolute + offset
                if not 0 <= target < ROM_SIZE:
                    raise ValueError(f"{path}:{lineno}: address {target:#x} outside ROM")
                image[target] = value
                seen.add(target)
        elif rtype == 1:
            break
        elif rtype == 4:
            upper = int.from_bytes(data, "big") << 16
        else:
            raise ValueError(f"{path}:{lineno}: unsupported record type {rtype}")
    if not seen:
        raise ValueError(f"{path}: no data records")
    return image

def checksum16(data: bytes) -> int:
    return sum(data) & 0xFFFF

def main() -> int:
    if len(sys.argv) != 3:
        print("usage: verify-rom.py REFERENCE.hex GENERATED.hex", file=sys.stderr)
        return 2
    ref_path, got_path = map(pathlib.Path, sys.argv[1:])
    ref, got = load_hex(ref_path), load_hex(got_path)
    print(f"reference: {len(ref)} bytes, checksum16={checksum16(ref):04X}, stored={ref[-2]:02X}{ref[-1]:02X}")
    print(f"generated: {len(got)} bytes, checksum16={checksum16(got):04X}, stored={got[-2]:02X}{got[-1]:02X}")
    print(f"reference Intel HEX SHA-256: {hashlib.sha256(ref_path.read_bytes()).hexdigest()}")
    print(f"generated Intel HEX SHA-256: {hashlib.sha256(got_path.read_bytes()).hexdigest()}")
    print(f"reference binary SHA-256: {hashlib.sha256(ref).hexdigest()}")
    print(f"generated binary SHA-256: {hashlib.sha256(got).hexdigest()}")
    diffs = [i for i, (a, b) in enumerate(zip(ref, got)) if a != b]
    if not diffs:
        print("ROM verification: byte-for-byte MATCH")
        return 0
    print(f"ROM verification: MISMATCH ({len(diffs)} differing bytes)")
    print("first differences (logical CPU address: reference -> generated):")
    for i in diffs[:32]:
        print(f"  ${LOGICAL_BASE + i:04X}: {ref[i]:02X} -> {got[i]:02X}")
    print("differences by original stock ROM components:")
    regions = (
        ("Monitor", 0x8000, 0x97FF), ("HELP", 0x9800, 0xA0FF),
        ("SEDIT", 0xA100, 0xA3FF), ("EDTASM", 0xA400, 0xB0FF),
        ("Visual/02", 0xB100, 0xC1FF), ("rc/BASIC", 0xC200, 0xDBFF),
        ("rc/Forth", 0xDC00, 0xEFFF), ("XMODEM", 0xF000, 0xF2FF),
        ("BIOS", 0xF300, 0xFFFF),
    )
    for component, begin, end in regions:
        differences = sum(begin <= LOGICAL_BASE + i <= end for i in diffs)
        print(f"  {component:10s} {begin:04X}-{end:04X}: {differences} different bytes")
    print("differences by 256-byte logical ROM page:")
    pages = {}
    for i in diffs:
        pages[i // 256] = pages.get(i // 256, 0) + 1
    for page, count in sorted(pages.items()):
        start = LOGICAL_BASE + page * 256
        print(f"  ${start:04X}-${start + 0xFF:04X}: {count}")
    return 1

if __name__ == "__main__":
    raise SystemExit(main())
