#!/usr/bin/env python3
"""Compare a historical component's assembled Intel HEX to the untouched stock ROM.

ROM HEX records use EPROM offsets 0000-7FFF; the component assembler emits
logical 1802 addresses 8000-FFFF. Compare only the component's configured
address range and count all bytes, including absent/unprogrammed FF bytes.
"""
from __future__ import annotations

import pathlib
import sys

SIZE = 32768
BASE = 0x8000


def load_hex(path: pathlib.Path, bias: int) -> bytearray:
    image = bytearray([0xFF]) * SIZE
    upper = 0
    occupied: set[int] = set()
    for lineno, raw in enumerate(path.read_text(encoding="ascii").splitlines(), 1):
        if not raw.strip():
            continue
        if not raw.startswith(":"):
            raise ValueError(f"{path}:{lineno}: invalid Intel HEX record")
        rec = bytes.fromhex(raw.strip()[1:])
        if len(rec) < 5 or len(rec) != rec[0] + 5 or sum(rec) & 255:
            raise ValueError(f"{path}:{lineno}: incorrect record length/checksum")
        size, address, kind = rec[0], int.from_bytes(rec[1:3], "big"), rec[3]
        if kind == 1:
            break
        if kind == 4:
            if size != 2:
                raise ValueError(f"{path}:{lineno}: invalid extended address")
            upper = int.from_bytes(rec[4:6], "big") << 16
            continue
        if kind != 0:
            raise ValueError(f"{path}:{lineno}: unsupported record type {kind}")
        for offset, value in enumerate(rec[4:4 + size]):
            index = upper + address + offset - bias
            if not 0 <= index < SIZE:
                raise ValueError(f"{path}:{lineno}: address outside expected ROM")
            if index in occupied and image[index] != value:
                raise ValueError(f"{path}:{lineno}: conflicting duplicate address")
            image[index] = value
            occupied.add(index)
    if not occupied:
        raise ValueError(f"{path}: no data records")
    return image


def main() -> int:
    if len(sys.argv) != 5:
        print("usage: compare-component.py REFERENCE.hex COMPONENT.hex START END_EXCLUSIVE",
              file=sys.stderr)
        return 2
    reference, component = map(pathlib.Path, sys.argv[1:3])
    start, end = (int(value, 16) for value in sys.argv[3:5])
    if not BASE <= start < end <= 0x10000:
        raise ValueError("expected logical 1802 component range within 8000-FFFF")
    ref = load_hex(reference, 0)
    built = load_hex(component, BASE)
    lo, hi = start - BASE, end - BASE
    differences = [idx for idx in range(lo, hi) if ref[idx] != built[idx]]
    first = (f"${BASE + differences[0]:04X}" if differences else "none")
    print(f"range=${start:04X}-${end - 1:04X} diff_count={len(differences)} "
          f"reference_non_ff={sum(x != 255 for x in ref[lo:hi])} "
          f"candidate_non_ff={sum(x != 255 for x in built[lo:hi])} "
          f"first_mismatch={first}")
    for idx in differences[:8]:
        print(f"  ${BASE + idx:04X}: reference={ref[idx]:02X} candidate={built[idx]:02X}")
    return 0 if not differences else 1


if __name__ == "__main__":
    raise SystemExit(main())
