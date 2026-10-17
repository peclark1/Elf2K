#!/usr/bin/env python3
"""Check complete AVI 27C256 Intel HEX, layout and STG ROM checksum."""
from __future__ import annotations
import hashlib
from pathlib import Path
import sys

SIZE = 32768
BASE = 0x8000
RESERVED = ((0xA100, 0xA400, "SEDIT"), (0xB100, 0xC200, "Visual/02 deferred"), (0xC200, 0xF000, "future services / RAM-loaded Tiny BASIC"), (0xF100, 0xF300, "reserved after Giant Monitor"))
ACTIVE = (
    (0x8000, 0x9800, "monitor"), (0x9800, 0xA100, "AVI help"),
    (0xA400, 0xB100, "EDTASM"),
    (0xF000, 0xF100, "original Giant Monitor"),
    (0xF300, 0x10000, "BIOS"),
)

def image_from_hex(path: Path) -> bytes:
    data = bytearray([0xFF] * SIZE)
    visited: set[int] = set()
    upper = 0
    eof = False
    for line_number, line in enumerate(path.read_text(encoding="ascii").splitlines(), 1):
        line = line.strip()
        if not line:
            continue
        if eof or not line.startswith(":"):
            raise ValueError(f"Bad record after EOF or missing ':' at line {line_number}")
        record = bytes.fromhex(line[1:])
        if len(record) < 5 or len(record) != record[0] + 5 or sum(record) % 256:
            raise ValueError(f"Invalid Intel HEX checksum/record at line {line_number}")
        count = record[0]
        addr = int.from_bytes(record[1:3], "big")
        kind = record[3]
        if kind == 0:
            for offset, value in enumerate(record[4:4 + count]):
                position = upper + addr + offset
                if position >= SIZE or position in visited:
                    raise ValueError(f"Out-of-bounds/duplicate data: physical {position:04X}")
                data[position] = value
                visited.add(position)
        elif kind == 1 and addr == 0 and count == 0:
            eof = True
        elif kind == 4 and count == 2:
            upper = int.from_bytes(record[4:6], "big") << 16
        else:
            raise ValueError(f"Unsupported Intel HEX record type {kind}")
    if not eof or len(visited) != SIZE:
        raise ValueError(f"Incomplete ROM: EOF={eof}, coverage={len(visited)}/{SIZE}")
    return bytes(data)

def validate(path: Path) -> None:
    rom = image_from_hex(path)
    for start, stop, name in RESERVED:
        if rom[start-BASE:stop-BASE] != bytes([0xFF]) * (stop-start):
            raise ValueError(f"{name} reservation overwritten: {start:04X}-{stop-1:04X}")
    for start, stop, name in ACTIVE:
        if all(b == 0xFF for b in rom[start-BASE:stop-BASE]):
            raise ValueError(f"Expected populated {name}: {start:04X}-{stop-1:04X}")
    # Image-level smoke checks for the boot signature, dispatch table, and
    # distinct CDP1854 mode-1 9600 8N1 initialization sequence.
    monitor = rom[0x0000:0x1800]
    extended_bios = rom[0x7300:0x7800]
    if b"AVI ELF II " not in monitor:
        raise ValueError("AVI startup banner not assembled into monitor")
    if bytes([3]) + b"UART\x00" not in monitor:
        raise ValueError("UART monitor command dispatch not present")
    if rom[0x7000:0x7008] != bytes.fromhex("90A1B3B4B5B6B7F8"):
        raise ValueError("Original Giant Monitor signature missing at CPU F000")
    if bytes.fromhex("650063196399") not in extended_bios:
        raise ValueError("CDP1863/CDP1854 control sequence missing")
    # romcksum -c32764: physical 7FFC/7FFD correction, 7FFE/7FFF
    # checksum. Sum is calculated after clearing these four bytes.
    raw_sum = sum(rom[:-4]) & 0xFFFF
    lo = raw_sum & 0xFF
    if raw_sum == 0xFE01:
        raise ValueError("Unrepresentable STG ROM checksum FE01")
    if 0xFE01 < raw_sum < 0xFF01:
        hi = 0
        correction = bytes([0xFF, (-lo + 1) & 0xFF])
    else:
        hi = ((raw_sum >> 8) + 1 + int(lo != 0)) & 0xFF
        correction = bytes([(-hi) & 0xFF, (-lo) & 0xFF])
    expected = bytes([hi, lo])
    if rom[-4:] != correction + expected:
        raise ValueError(f"Checksum/correction mismatch: got {rom[-4:].hex()}, expected {(correction+expected).hex()}")
    if (sum(rom) & 0xFFFF) != int.from_bytes(expected, "big"):
        raise ValueError("Whole-ROM sum does not equal embedded checksum")
    print(f"PASS: {len(rom)} ROM bytes, STG checksum {expected.hex().upper()}")
    print("SHA256 (binary ROM): " + hashlib.sha256(rom).hexdigest())
    for start, stop, name in ACTIVE:
        print(f"  {start:04X}-{stop-1:04X} {stop-start:5}  {name}")
    for start, stop, name in RESERVED:
        print(f"  {start:04X}-{stop-1:04X} {stop-start:5}  {name}: all FF")
    print("BUILD VALIDATION ONLY - hardware and functional testing still required")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: verify-avi.py AVIElf2.hex")
    try:
        validate(Path(sys.argv[1]))
    except (ValueError, OSError) as exc:
        raise SystemExit(f"FAIL: {exc}")
