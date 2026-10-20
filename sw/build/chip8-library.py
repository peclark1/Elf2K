#!/usr/bin/env python3
"""Offline audit and Intel HEX packager for historical 64x32 VIP CHIP-8 ROMs."""
import argparse
import csv
import hashlib
import json
import re
from collections import deque
from pathlib import Path
from urllib.parse import quote

BASE = 0x200
LIMIT = 0xA00
VINTAGE = ("weisbecker", "cortez", "tcnj", "ivie", "winsor")
ETI_KNOWN = {"Airplane.ch8"}
TESTED = {"Breakout [Carmelo Cortez, 1979].ch8"}


def opcode_type(op):
    hi, lo = op >> 12, op & 15
    if hi == 0:
        if op in (0x00E0, 0x00EE):
            return "vip"
        if op in (0x00FB, 0x00FC, 0x00FD, 0x00FE, 0x00FF) or 0x00C0 <= op <= 0x00CF:
            return "extended"
        return "sys"
    if hi in (1, 2, 3, 4, 6, 7, 0xA, 0xB, 0xC):
        return "vip"
    if hi in (5, 9):
        return "vip" if lo == 0 else "extended"
    if hi == 8:
        return "vip" if lo in (0, 1, 2, 3, 4, 5, 6, 7, 0xE) else "extended"
    if hi == 0xD:
        return "extended" if lo == 0 else "vip"
    if hi == 0xE:
        return "vip" if (op & 255) in (0x9E, 0xA1) else "extended"
    if hi == 0xF:
        return "vip" if (op & 255) in (0x07, 0x0A, 0x15, 0x18, 0x1E, 0x29, 0x33, 0x55, 0x65) else "extended"
    return "extended"


def audit_code(binary):
    """Explore both conditional paths; never mistake all sprite data for code.

    Computed BNNN jumps cannot be statically resolved without register tracking.
    Results are suggestive, never proof of execution compatibility.
    """
    work = deque([BASE])
    seen, unsupported, warnings = set(), set(), set()
    last = BASE + len(binary)
    while work:
        pc = work.popleft()
        if pc in seen:
            continue
        if not BASE <= pc or pc + 1 >= last:
            warnings.add("control-flow target outside supplied bytes")
            continue
        if pc & 1:
            warnings.add("odd address for instruction")
        seen.add(pc)
        op = (binary[pc-BASE] << 8) | binary[pc-BASE+1]
        kind = opcode_type(op)
        if kind == "extended":
            unsupported.add(f"{pc:04X}:{op:04X}")
        if kind == "sys":
            warnings.add(f"VIP-specific SYS {op:04X} at {pc:04X}")
        hi, target = op >> 12, op & 0xFFF
        if hi == 1:
            work.append(target)
        elif hi == 2:
            work.extend((target, pc + 2))
        elif hi == 0xB:
            warnings.add(f"computed BNNN jump at {pc:04X}")
        elif op in (0x00EE, 0x00FD):
            continue
        elif hi in (3, 4, 5, 9) or (hi == 0xE and (op & 255) in (0x9E, 0xA1)):
            work.extend((pc + 2, pc + 4))
        else:
            work.append(pc + 2)
    return {
        "reachable_instructions": len(seen),
        "unsupported_opcodes": sorted(unsupported),
        "flow_warnings": sorted(warnings),
    }


def year_of(name):
    x = re.search(r"\b(?:19[6-9][0-9]|20[0-3][0-9])\b", name)
    return int(x.group()) if x else None


def classify(path, payload, instructions, code):
    title, year = path.stem.lower(), year_of(path.stem)
    reasons = []
    if len(payload) > LIMIT - BASE:
        reasons.append("too large for preserved RAM ($0200-$09FF)")
    if path.name in ETI_KNOWN or re.search(r"\beti[\s-]*660\b", instructions.lower()):
        reasons.append("ETI-660 program, incompatible display/hardware")
    if code["unsupported_opcodes"]:
        reasons.append("unsupported or extended instruction at reachable address")
    if reasons:
        return "incompatible", reasons
    reasons.extend(code["flow_warnings"])
    if year and year >= 1982:
        reasons.append("later CHIP-8 dialect/quirks not verified")
    if not ((year and year <= 1981) or any(a in title for a in VINTAGE)):
        reasons.append("original VIP provenance unconfirmed")
    return ("likely" if not reasons else "review"), reasons


def make_hex(payload):
    records = []
    for offset in range(0, len(payload), 16):
        data = payload[offset:offset+16]
        address = BASE + offset
        rec = bytes((len(data), address >> 8, address & 255, 0)) + data
        records.append(":" + rec.hex().upper() + f"{-sum(rec) & 255:02X}")
    return "\n".join(records + [":00000001FF"]) + "\n"


def verify_hex(text, payload):
    memory = {}
    eof = False
    for line in text.strip().splitlines():
        if not line.startswith(":"):
            raise ValueError("bad HEX prefix")
        rec = bytes.fromhex(line[1:])
        if len(rec) != rec[0] + 5 or sum(rec) % 256:
            raise ValueError("bad HEX record checksum/length")
        address = rec[1] * 256 + rec[2]
        if rec[3] == 1:
            if rec[0] or eof:
                raise ValueError("bad EOF")
            eof = True
        elif rec[3] == 0 and not eof:
            for n, value in enumerate(rec[4:-1]):
                if address + n in memory:
                    raise ValueError("overlap")
                memory[address + n] = value
        else:
            raise ValueError("unexpected record")
    if not eof or len(memory) != len(payload):
        raise ValueError("missing data/EOF")
    if bytes(memory[BASE + i] for i in range(len(payload))) != payload:
        raise ValueError("binary mismatch")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--revision", required=True)
    parser.add_argument("--max-games", type=int, default=30)
    args = parser.parse_args()
    if not args.source.is_dir():
        parser.error("source game directory not found")
    if not re.fullmatch("[a-f0-9]{40}", args.revision):
        parser.error("--revision requires full upstream commit SHA")
    if not 1 <= args.max_games <= 172:
        parser.error("--max-games must be 1 to 172")
    args.output.mkdir(parents=True, exist_ok=True)
    dest = args.output / "loadable-hex"
    dest.mkdir(exist_ok=True)
    games = []
    for p in sorted(args.source.glob("*.ch8"), key=lambda q: q.name.casefold()):
        data = p.read_bytes()
        txt = p.with_suffix(".txt")
        instructions = txt.read_text(encoding="utf-8", errors="replace") if txt.exists() else ""
        code = audit_code(data)
        status, reasons = classify(p, data, instructions, code)
        source_url = ("https://github.com/etxmato/emma_02/blob/" + args.revision
                      + "/data/Chip-8/Chip-8%20Games/" + quote(p.name))
        games.append({
            "title": p.stem, "source_filename": p.name, "source_url": source_url,
            "source_bytes": len(data), "source_sha256": hashlib.sha256(data).hexdigest(),
            "last_byte": "$" + f"{BASE + len(data) - 1:04X}",
            "has_upstream_hex": p.with_suffix(".hex").exists(),
            "has_instructions": txt.exists(), "year": year_of(p.stem),
            "classification": status, "reasons": reasons,
            "hardware_status": "Breakout proven on AVI ELF II" if p.name in TESTED else "untested",
            **code,
        })
    likely = [g for g in games if g["classification"] == "likely"]
    likely.sort(key=lambda r: (
        0 if r["year"] in (1978, 1979) else 1,
        not r["has_instructions"],
        r["source_bytes"],
        r["title"].casefold(),
    ))
    selected = likely[:args.max_games]
    for i, game in enumerate(selected, 1):
        name = re.sub(r"[^A-Za-z0-9_-]+", "-", game["title"]).strip("-")[:65]
        filename = f"{i:02d}-{name}.hex"
        payload = (args.source / game["source_filename"]).read_bytes()
        result = make_hex(payload)
        verify_hex(result, payload)
        if BASE + len(payload) > LIMIT:
            raise AssertionError("unsafe address")
        (dest / filename).write_text(result, encoding="ascii")
        game["loadable_hex"] = "loadable-hex/" + filename
        # Preserve available historical instructions in their own UTF-8 files.
        # The game metadata contains the exact upstream source attribution.
        original_instructions = (args.source / game["source_filename"]).with_suffix(".txt")
        if original_instructions.exists():
            instructions_dir = args.output / "instructions"
            instructions_dir.mkdir(exist_ok=True)
            txt_filename = f"{i:02d}-{name}.txt"
            text = original_instructions.read_text(encoding="utf-8", errors="replace")
            (instructions_dir / txt_filename).write_text(text, encoding="utf-8")
            game["instructions_file"] = "instructions/" + txt_filename
    report = {
        "source": "etxmato/emma_02",
        "revision": args.revision,
        "total_games": len(games),
        "selected": len(selected),
        "games": games,
    }
    (args.output / "catalog.json").write_text(json.dumps(report, indent=2) + "\n")
    with (args.output / "catalog.csv").open("w", newline="", encoding="utf-8") as f:
        keys = ("title", "classification", "source_bytes", "last_byte", "year",
                "has_instructions", "hardware_status", "loadable_hex", "reasons", "source_url")
        w = csv.DictWriter(f, fieldnames=keys, extrasaction="ignore")
        w.writeheader()
        for game in games:
            item = dict(game)
            item["reasons"] = "; ".join(game["reasons"])
            w.writerow(item)
    counts = {s: sum(g["classification"] == s for g in games)
              for s in ("likely", "review", "incompatible")}
    readme = [
        "# ELF II historical CHIP-8 library", "",
        "Source: Emma 02 at commit " + args.revision + ".",
        f"Inspected {len(games)} programs: {counts['likely']} likely, "
        + f"{counts['review']} review, {counts['incompatible']} incompatible.",
        f"Packaged {len(selected)} candidates as verified-checksum Intel HEX at $0200.",
        "",
        "LIKELY IS NOT HARDWARE-VERIFIED. This approximate code-path analysis",
        "does not prove keypad, original interpreter quirks, delays, sound,",
        "DMA/video execution speed, self-modifying code, or computed branches.",
        "See catalog.csv and catalog.json for reasons and historical attribution.",
        "",
        "## Loading on AVI ELF II", "",
        "Send one file from loadable-hex using Pete's Monitor Intel HEX loader.",
        "Then enter CHIP8 (not CHIP8 FOUR or CHIP8 MAZE).",
        "With autoboot enabled, RESET exits to monitor; CHIP8 restarts.",
        "With autoboot disabled, RUN OFF/ON restarts Breakout on verified hardware.",
        "For Breakout, hold 4+INPUT to move left, 6+INPUT to move right.",
        "",
        "No ROM firmware or historical interpreter code is modified.", "",
        "Original instruction text is copied to instructions/ when provided",
        "by the upstream archive. These are historical notes, not rewritten",
        "controls for the Netronics keypad + INPUT arrangement.", "",
        "## Selected candidates", "",
        "| Game | Size | Intel HEX | Original instructions |",
        "|---|---:|---|---|",
    ]
    for game in selected:
        readme.append(f"| {game['title'].replace('|','/')} | {game['source_bytes']} | "
                      + game["loadable_hex"] + " | " + game.get("instructions_file", "not provided") + " |")
    (args.output / "README.md").write_text("\n".join(readme) + "\n")
    print(f"AUDIT: {len(games)} files {counts}; {len(selected)} packaged", flush=True)
    for game in selected[:25]:
        print(f"  {game['source_bytes']:4} B {game['title']}", flush=True)


if __name__ == "__main__":
    main()
