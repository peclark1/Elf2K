#!/usr/bin/env python3
"""Emit reversible, provenance-labelled One ROM experiment derived from CI AVI HEX.

DO NOT FLASH AS AN AUTOMATED STEP. Verified $875B baseline remains immutable.
"""
from __future__ import annotations
import argparse
import hashlib
from pathlib import Path

SIZE = 32768

def from_hex(p: Path) -> bytes:
    out = bytearray([255] * SIZE)
    seen = set()
    eof = False
    for line in p.read_text("ascii").splitlines():
        if not line.strip():
            continue
        if eof or not line.startswith(":"):
            raise ValueError("Unexpected Intel HEX line")
        b = bytes.fromhex(line[1:])
        if len(b) != b[0] + 5 or sum(b) % 256:
            raise ValueError("Bad Intel HEX checksum or record")
        count, addr, kind = b[0], int.from_bytes(b[1:3], "big"), b[3]
        if kind == 0:
            if addr + count > SIZE:
                raise ValueError("ROM data out of range")
            for i, value in enumerate(b[4:4+count]):
                if addr+i in seen:
                    raise ValueError("Duplicate ROM address")
                out[addr+i] = value
                seen.add(addr+i)
        elif kind == 1 and addr == 0 and count == 0:
            eof = True
        else:
            raise ValueError("Unsupported Intel HEX record")
    if not eof or len(seen) != SIZE:
        raise ValueError("Incomplete 32768-byte ROM")
    return bytes(out)

def to_hex(data: bytes, path: Path) -> None:
    with path.open("w", encoding="ascii", newline="\n") as f:
        for addr in range(0, SIZE, 16):
            chunk = data[addr:addr+16]
            record = bytes([len(chunk), addr >> 8, addr & 255, 0]) + chunk
            f.write(":" + record.hex().upper() + format((-sum(record)) & 255, "02X") + "\n")
        f.write(":00000001FF\n")

def stamp(rom: bytearray) -> None:
    total = sum(rom[:-4]) & 65535
    lo = total & 255
    if total == 0xFE01:
        raise ValueError("Unrepresentable STG checksum")
    if 0xFE01 < total < 0xFF01:
        hi, correction = 0, bytes([255, (-lo+1) & 255])
    else:
        hi = ((total >> 8) + 1 + int(lo != 0)) & 255
        correction = bytes([(-hi) & 255, (-lo) & 255])
    rom[-4:] = correction + bytes([hi, lo])
    if sum(rom) & 65535 != (hi << 8) + lo:
        raise ValueError("Checksum stamp failed")

def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("input_hex", type=Path)
    p.add_argument("output_dir", type=Path)
    a = p.parse_args()
    assembled = from_hex(a.input_hex)
    # ROM title length changes shift labels in BOOTS. Locate both POST
    # signatures in the emitted machine code; never use a stale $809B/$80C9.
    def unique_signature(pattern: bytes, label: str) -> int:
        window = assembled[:0x1000]
        position = window.find(pattern)
        if position < 0 or window.find(pattern, position + 1) >= 0:
            raise SystemExit(f"{label} machine-code signature absent/ambiguous")
        return position
    romchk = unique_signature(bytes.fromhex("E0 64 98 F8 80"),
                              "ROMCHK POST 98 / RLDI P1 BOOTS") + 1
    sizmem = unique_signature(bytes.fromhex("E0 64 89"),
                              "SIZMEM POST 89")
    target = 0x8000 + sizmem
    if not (0x8000 <= target < 0x8800):
        raise SystemExit("SIZMEM is outside expected early ROM region")
    old_instruction = assembled[romchk:romchk + 3]
    if old_instruction != bytes.fromhex("64 98 F8"):
        raise SystemExit("ROMCHK patch does not match validated instruction bytes")
    replacement = bytes([0xC0, target >> 8, target & 0xFF])
    patched = bytearray(assembled)
    patched[romchk:romchk + 3] = replacement
    stamp(patched)
    diff = [i for i, (old, new) in enumerate(zip(assembled, patched)) if old != new]
    allowed = set(range(romchk, romchk+3)) | {0x7FFC,0x7FFD,0x7FFE,0x7FFF}
    if not set(diff) <= allowed:
        raise SystemExit("Unexpected patch outside approved bytes")
    a.output_dir.mkdir(parents=True, exist_ok=True)
    prefix = "AVIElf2-Netronics-OneROM-EXPERIMENTAL"
    (a.output_dir / (prefix + ".bin")).write_bytes(patched)
    to_hex(patched, a.output_dir / (prefix + ".hex"))
    (a.output_dir / "AVIElf2-Netronics-assembled.bin").write_bytes(assembled)
    report = (
        "AVI COM2-FIRST 38400 CHIP8 ROM — NEW BOOT PATH NOT BENCH TESTED\n"
        "Preserve the previously verified 1C62 / F30A OneROM backup for rollback.\n"
        "COM2 38400 8N1 boots directly; J15 COM1-to-EF4 jumper may be removed at power-off.\n"
        "Ensure existing Hyperboard COM2 x16 clock is 614400 Hz and Tera Term 38400 8N1.\n"
        "COM2 9600/19200/38400 owner tested with matching external UART clocks.\n"
        "One ROM test image bypasses the unresolved startup ROM checksum scan.\n"
        f"Patch at CPU ${0x8000+romchk:04X}-${0x8000+romchk+2:04X}: "
        + old_instruction.hex().upper() + " -> " + replacement.hex().upper() + "\n"
        "Physical byte diff: " + ", ".join(f"{i:04X}" for i in diff) + "\n"
        "New checksum " + bytes(patched[-2:]).hex().upper() + "\n"
        "Assembled SHA256 " + hashlib.sha256(assembled).hexdigest() + "\n"
        "One ROM SHA256 " + hashlib.sha256(patched).hexdigest() + "\n"
    )
    (a.output_dir / "README-Netronics-OneROM-EXPERIMENTAL.txt").write_text(report)
    print(report)

if __name__ == "__main__":
    main()
