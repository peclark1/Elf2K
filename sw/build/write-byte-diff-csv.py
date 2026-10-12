#!/usr/bin/env python3
"""Write every decoded 27C256 ROM byte difference to a deterministic CSV."""
from __future__ import annotations

import csv
import pathlib
import runpy
import sys


def main() -> int:
    if len(sys.argv) != 4:
        print("usage: write-byte-diff-csv.py REFERENCE.hex GENERATED.hex OUTPUT.csv", file=sys.stderr)
        return 2
    ref, built, destination = map(pathlib.Path, sys.argv[1:])
    read_hex = runpy.run_path(str(pathlib.Path(__file__).with_name("verify-rom.py")))["load_hex"]
    reference = read_hex(ref)
    generated = read_hex(built)
    differences = 0
    with destination.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream)
        writer.writerow(["cpu_address", "eprom_offset", "reference_byte", "generated_byte"])
        for offset, (expected, actual) in enumerate(zip(reference, generated)):
            if expected != actual:
                writer.writerow((
                    f"0x{0x8000 + offset:04X}", f"0x{offset:04X}",
                    f"{expected:02X}", f"{actual:02X}"
                ))
                differences += 1
    print(f"Written {differences} complete byte differences to {destination}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
