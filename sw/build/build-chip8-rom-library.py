#!/usr/bin/env python3
"""Deterministic 27-game VIP CHIP-8 ROM packer. Never changes original bytes."""
from __future__ import annotations
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PARTS = ("rom-library-01.json", "rom-library-02.json")
LIB = ROOT / "chip8-netronics/games"
BANKS = ((0xA100, 0xA400), (0xB100, 0xC200),
         (0xD200, 0xD800), (0xDD00, 0xF000))
DIRECTORY = 0xF100
ENTRYSIZE = 16
TOTAL = 27
UPSTREAM = "9bd1cdb1fd020081d6536a94d19351c94578acd0"


def load_games():
    games = []
    for name in PARTS:
        j = json.loads((LIB / name).read_text())
        if j["revision"] != UPSTREAM or j["upstream"] != "etxmato/emma_02":
            raise ValueError("unexpected source revision")
        games.extend(j["games"])
    if [g["id"] for g in games] != list(range(1, TOTAL + 1)):
        raise ValueError("expected 27 unique sequential game IDs")
    for g in games:
        if len(bytes.fromhex(g["bytes"])) != g["length"]:
            raise ValueError("Game size mismatch: " + g["title"])
        if not (1 <= g["length"] <= 0x800):
            raise ValueError("invalid RAM game length")
        if len(g["menu"]) > 11 or not g["menu"].isascii():
            raise ValueError("menu label exceeds 11 ASCII characters")
        if len(g["source_hex_sha"]) != 40:
            raise ValueError("missing original upstream file SHA")
    return games


def allocate(games):
    remaining = [end - start for start, end in BANKS]
    occupied = [0] * len(BANKS)
    for g in sorted(games, key=lambda x: (-x["length"], x["title"])):
        choices = [i for i, available in enumerate(remaining) if available >= g["length"]]
        if not choices:
            raise ValueError("No contiguous bank for " + g["title"])
        i = min(choices, key=lambda c: (remaining[c] - g["length"], c))
        g["rom_address"] = BANKS[i][0] + occupied[i]
        occupied[i] += g["length"]
        remaining[i] -= g["length"]
    assert DIRECTORY + len(games) * ENTRYSIZE <= 0xF300
    return games


def table(games):
    data = bytearray()
    for g in games:
        data.extend(g["rom_address"].to_bytes(2, "big"))
        data.extend(g["length"].to_bytes(2, "big"))
        data.extend(g["menu"].encode("ascii").ljust(12, b"\x00"))
    return bytes(data)


def db_lines(binary):
    for i in range(0, len(binary), 16):
        yield "        .DB " + ",".join("$" + f"{b:02X}" for b in binary[i:i+16])


def build(source, asm_path, layout_path):
    games = allocate(source)
    lines = ["; Generated from committed, attributed historical game bytes",
             "; Each F100 table record is 2-byte ROM pointer, 2-byte byte-count,",
             "; and 12-byte null-terminated/padded menu label."]
    for g in sorted(games, key=lambda x: x["rom_address"]):
        lines.extend(["", "; " + g["title"],
                      "        .ORG $" + f"{g['rom_address']:04X}"])
        lines.extend(db_lines(bytes.fromhex(g["bytes"])))
    lines += ["", "        .ORG $F100", "AVICH8LIBTABLE:"]
    directory = table(games)
    lines.extend(db_lines(directory))
    lines.append("        .END")
    asm_path.parent.mkdir(parents=True, exist_ok=True)
    asm_path.write_text("\n".join(lines) + "\n", encoding="ascii")
    report = {
        "count": len(games),
        "total_game_bytes": sum(x["length"] for x in games),
        "directory": DIRECTORY,
        "directory_hex": directory.hex(),
        "banks": [{"start": a, "end": b,
                   "used": sum(g["length"] for g in games if a <= g["rom_address"] < b)}
                  for a, b in BANKS],
        "games": [{"id": g["id"], "title": g["title"],
                   "menu": g["menu"], "length": g["length"],
                   "rom_address": g["rom_address"],
                   "sha256": hashlib.sha256(bytes.fromhex(g["bytes"])).hexdigest()}
                  for g in games],
    }
    layout_path.parent.mkdir(parents=True, exist_ok=True)
    layout_path.write_text(json.dumps(report, indent=2) + "\n")
    print(f"PACKED {len(games)} games, {report['total_game_bytes']} bytes")
    for bank in report["banks"]:
        print(f"  {bank['start']:04X}-{bank['end']-1:04X}: "
              f"{bank['used']} of {bank['end']-bank['start']} bytes")
    return report


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit("usage: build-chip8-rom-library.py OUT_ASM OUT_JSON")
    build(load_games(), Path(sys.argv[1]), Path(sys.argv[2]))
