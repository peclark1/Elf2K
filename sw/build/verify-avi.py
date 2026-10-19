#!/usr/bin/env python3
"""Check complete AVI 27C256 Intel HEX, layout and STG ROM checksum."""
from __future__ import annotations
import hashlib
from pathlib import Path
import sys

SIZE = 32768
BASE = 0x8000
RESERVED = ((0xA100, 0xA400, "SEDIT"), (0xB100, 0xC200, "Visual/02 deferred"), (0xDD00, 0xF000, "reserved above CHIP-8 archive"), (0xF100, 0xF300, "reserved after Giant Monitor"))
ACTIVE = (
    (0x8000, 0x9800, "monitor"), (0x9800, 0xA100, "AVI help"),
    (0xA400, 0xB100, "EDTASM"),
    (0xC200, 0xD000, "AVI cassette monitor service"),
    (0xD000, 0xDD00, "1979 Netronics CHIP-8 launcher and archive"),
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

def validate_chip8_payload(rom: bytes) -> None:
    """Verify ROM-resident Netronics code against two REAL-HARDWARE-PROVEN
    period image files, rather than trusting the hand-written .DB listing.
    """
    fixture_dir = Path(__file__).resolve().parent.parent / "chip8-netronics"

    def read_1802_hex(filename: str) -> dict[int, int]:
        memory: dict[int, int] = {}
        seen_eof = False
        for line in (fixture_dir / filename).read_text("ascii").splitlines():
            record = bytes.fromhex(line[1:])
            if not line.startswith(":") or len(record) != 5 + record[0] or sum(record) % 256:
                raise ValueError(f"Invalid CHIP-8 golden Intel HEX record: {filename}")
            address = int.from_bytes(record[1:3], "big")
            if record[3] == 1:
                if record[0] != 0 or seen_eof:
                    raise ValueError("Invalid CHIP-8 golden EOF")
                seen_eof = True
            elif record[3] == 0 and not seen_eof:
                for i, b in enumerate(record[4:-1]):
                    if address + i in memory:
                        raise ValueError("CHIP-8 golden duplicate address")
                    memory[address + i] = b
            else:
                raise ValueError("Unsupported CHIP-8 golden record")
        if not seen_eof:
            raise ValueError("Missing CHIP-8 golden EOF")
        return memory

    four = read_1802_hex("Netronics-1979-CHIP8-Four-Squares-INTERRUPTS-ON.hex")
    maze = read_1802_hex("Netronics-1979-CHIP8-Maze-INTERRUPTS-ON.hex")
    for low, high in ((0x0000, 0x0200), (0x0C00, 0x0E00)):
        if any(four[a] != maze[a] for a in range(low, high)):
            raise ValueError("Proven CHIP-8 images disagree in core or OS")
    # Preserve the independent 1979 game/OS reference files byte-for-byte.
    # The owner's AVI ELF II hardware conclusively confirmed that the 1979
    # published interpreter broke the original RCA VIP F-group dispatcher.
    # Only this exact five-byte repair is authorized in the ROM archive.
    broken_fx = bytes.fromhex("01 B5 F8 56 D4")
    repaired_fx = bytes.fromhex("45 A3 98 56 D4")
    if bytes(four[0x0105+i] for i in range(5)) != broken_fx:
        raise ValueError("Historical reference FX dispatcher unexpectedly changed")
    if bytes(maze[0x0105+i] for i in range(5)) != broken_fx:
        raise ValueError("Maze historical reference FX dispatcher unexpectedly changed")
    blocks = (
        ("interpreter", four, 0x0000, 0x0200),
        ("period OS", four, 0x0C00, 0x0200),
        ("four-square game", four, 0x0200, 0x001A),
        ("four-square sprite", four, 0x0300, 0x0008),
        ("maze game", maze, 0x0200, 0x0022),
        ("interrupt-enable stub", four, 0x0E80, 0x0006),
    )
    physical = 0xD800 - BASE
    for name, expected, address, size in blocks:
        data = bytes(expected[address+i] for i in range(size))
        if name == "interpreter":
            data = data[:0x0105] + repaired_fx + data[0x010A:]
            if data[0x0105:0x010A] != repaired_fx:
                raise ValueError("CHIP-8 FX dispatch repair failed construction")
        if rom[physical:physical+size] != data:
            raise ValueError(f"ROM CHIP8 payload differs from bench-proven {name} at ${BASE+physical:04X}")
        physical += size
    if physical != 0xDC4A - BASE:
        raise ValueError("Incorrect CHIP-8 ROM payload size")
    print("PASS: Netronics CHIP-8 interpreter/OS, FOUR, MAZE and IE=1 bootstrap")
    print("      1093 original period payload bytes unchanged; exactly five")
    print("      FX dispatcher bytes patched to RCA VIP, hardware-verified")


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
    if b"Pete\'s ELF II Monitor" not in monitor:
        raise ValueError("AVI startup banner not assembled into monitor")
    if bytes([4]) + b"CASSAVE\x00" not in monitor:
        raise ValueError("CASSAVE command not linked into monitor")
    if bytes([4]) + b"CASLOAD\x00" not in monitor:
        raise ValueError("CASLOAD command not linked into monitor")
    if bytes([3]) + b"UART\x00" not in monitor:
        raise ValueError("UART monitor command dispatch not present")
    if rom[0x7000:0x7008] != bytes.fromhex("90A1B3B4B5B6B7F8"):
        raise ValueError("Original Giant Monitor signature missing at CPU F000")
    if bytes([5]) + b"CHIP8\x00" not in monitor:
        raise ValueError("CHIP8 monitor command dispatch not present")
    if rom[0x5800:0x5810] != bytes.fromhex("C00C1000000000000000000000000000"):
        raise ValueError("Historic CHIP-8 kernel bytes missing at CPU D800")
    if rom[0x5A00:0x5A10] != bytes.fromhex("F80CB2F806A2E2D2F8FFA1F80BB13028"):
        raise ValueError("Netronics VIP OS bytes missing at CPU DA00")
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
    validate_chip8_payload(rom)
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
