#!/usr/bin/env python3
"""Read-only, pinned historical Elf2K component comparison.

Never writes an EPROM image, canonical build source, or reference. All files
emitted here are reports in the caller-supplied disposable output directory.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import runpy
import subprocess

ROOT = Path(__file__).resolve().parents[2]
CMP = runpy.run_path(str(ROOT / "sw/build/compare-component.py"))["load_hex"]
BASE = 0x8000
REFERENCE_BLOB = "e1a14af17671dae2b051b53a7ae186d639e7f5b9"
REFERENCE_SHA = "db8d5148b7cb507613a20b28dc31abfce1b1f500cb69a8c2e348cfaea2ab6a4b"
ARCHIVE_COMMIT = "1d5f8b2bb4295d83a6ac35db06c43c7eb009ec34"
REGIONS = {
    "EDTASM": (0xA400, 0xB100, "edtasm"),
    "Visual/02": (0xB100, 0xC200, "visual02"),
    "Forth": (0xDC00, 0xF000, "forth"),
    "BIOS": (0xF300, 0x10000, "bios"),
}
ARCHIVED = {
    "EDTASM": "edtasm.hex",
    "Visual/02": "visual02.hex",
    "Forth": "forth.hex",
    "BIOS": "bios.hex",
}

def require_reference(path: Path) -> None:
    actual = hashlib.sha256(path.read_bytes()).hexdigest()
    if actual != REFERENCE_SHA:
        raise RuntimeError(f"Refusing changed ROM reference: {actual}")
    blob = subprocess.check_output(
        ["git", "-C", str(ROOT), "hash-object", str(path)], text=True
    ).strip()
    if blob != REFERENCE_BLOB:
        raise RuntimeError(f"Refusing changed ROM git blob: {blob}")

def version_banner(data: bytes, word: bytes = b"Rc/Forth ") -> list[dict]:
    found = []
    pos = 0
    while (pos := data.find(word, pos)) >= 0:
        end = pos
        while end < min(len(data), pos + 32) and 32 <= data[end] < 127:
            end += 1
        found.append({"cpu_address": f"${BASE + pos:04X}",
                      "text": data[pos:end].decode("ascii", errors="replace")})
        pos += len(word)
    return found

def resync(ref: bytes, other: bytes, first: int, limit: int = 2048) -> dict | None:
    """Nearest >=24-byte matching anchor after divergence, allowing displacement.
    Evidence of alignment only, not proof of branch semantics.
    """
    width = 24
    upper = min(len(ref), first + limit)
    choices = []
    for index in range(first, max(first, upper - width + 1)):
        needle = ref[index:index + width]
        if len(needle) != width or needle == b"\xff" * width:
            continue
        for shift in range(-32, 33):
            alt = index + shift
            if alt < 0 or alt + width > len(other):
                continue
            if other[alt:alt + width] == needle:
                choices.append((index, abs(shift), shift))
        if choices:
            address, _, delta = min(choices)
            return {"reference_address": f"${BASE+address:04X}",
                    "candidate_address": f"${BASE+address+delta:04X}",
                    "candidate_minus_reference": delta, "anchor_bytes": width}
    return None

def compare(name: str, ref: bytes, candidate: bytes,
            start: int, end: int, filename: str) -> dict:
    lo, hi = start - BASE, end - BASE
    difference = [p for p in range(lo, hi) if ref[p] != candidate[p]]
    result = {
        "name": name, "file": filename, "region": f"${start:04X}-${end-1:04X}",
        "difference_count": len(difference),
        "first_mismatch": f"${difference[0]+BASE:04X}" if difference else None,
        "reference_non_ff": sum(v != 255 for v in ref[lo:hi]),
        "candidate_non_ff": sum(v != 255 for v in candidate[lo:hi]),
        "first_eight": [
            {"address": f"${BASE+p:04X}", "original": f"{ref[p]:02X}",
             "candidate": f"{candidate[p]:02X}"} for p in difference[:8]
        ],
    }
    if difference:
        # Search only the component's own address span to avoid false
        # alignment with identical firmware in other components.
        anchor = resync(ref[lo:hi], candidate[lo:hi], difference[0]-lo)
        if anchor:
            for field in ("reference_address", "candidate_address"):
                anchor[field] = f"${int(anchor[field][1:],16)+lo:04X}"
        result["nearest_equal_24_byte_run"] = anchor
    return result

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--reference", type=Path, required=True)
    ap.add_argument("--stock-work", type=Path, required=True)
    ap.add_argument("--archive", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()
    require_reference(args.reference)
    archive_commit = subprocess.check_output(
        ["git", "-C", str(args.archive.parent), "rev-parse", "HEAD"], text=True
    ).strip()
    if archive_commit != ARCHIVE_COMMIT:
        raise RuntimeError(f"Archived source pin unexpectedly changed: {archive_commit}")

    original = bytes(CMP(args.reference, 0))
    official = bytes(CMP(args.stock_work / "Elf2K-alternate.hex", 0))
    baseline_diff = sum(a != b for a,b in zip(original,official))
    if baseline_diff != 10441:
        raise RuntimeError(f"Canonical historical baseline drift: expected 10441, got {baseline_diff}")
    checks = {
        "reference_git_blob": REFERENCE_BLOB,
        "reference_hex_sha256": REFERENCE_SHA,
        "reference_binary_sha256": hashlib.sha256(original).hexdigest(),
        "independent_build_binary_sha256": hashlib.sha256(official).hexdigest(),
        "canonical_reference_differences": baseline_diff,
        "archive_git_commit": archive_commit,
        "reference_forth_banners": version_banner(original),
        "canonical_forth_banners": version_banner(official),
    }
    rows = []
    for name,(start,end,stem) in REGIONS.items():
        built = args.stock_work / (stem+".hex")
        rows.append(compare(name+" / pinned source", original, bytes(CMP(built,BASE)),
                            start,end,str(built)))
        archived = args.archive / ARCHIVED[name]
        rows.append(compare(name+" / archived compiled output", original,
                            bytes(CMP(archived,BASE)),start,end,str(archived)))
    if not any(x["text"].startswith("Rc/Forth 0.3") for x in checks["reference_forth_banners"]):
        raise RuntimeError("Expected 0.3 banner missing from protected reference")
    if not any(x["text"].startswith("Rc/Forth 0.1") for x in checks["canonical_forth_banners"]):
        raise RuntimeError("Expected 0.1 banner missing from canonical candidate")
    checks["rows"] = rows
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "audit.json").write_text(json.dumps(checks, indent=2)+"\n")
    md = [
        "# Historical reconstruction audit (NOT a production ROM)",
        "", "All offsets refer to the original unmodified alternate ROM. Archival",
        "preassembled outputs are independent historical evidence, not selected",
        "source components. Exact ROM reference gate remains active.",
        "", f"Original HEX SHA-256: \`{REFERENCE_SHA}\`",
        f"Original git blob: \`{REFERENCE_BLOB}\`",
        f"Archive commit: \`{archive_commit}\`",
        f"Canonical build differences: **{baseline_diff:,}**", "",
        "| Evidence | Region | Differing bytes | First difference | 24-byte resynchronization |",
        "|---|---|---:|---|---|",
    ]
    for r in rows:
        anchor = r.get("nearest_equal_24_byte_run")
        sync = (f"{anchor['reference_address']} vs {anchor['candidate_address']} "
                f"(delta {anchor['candidate_minus_reference']:+d})" if anchor else "none located")
        md.append(f"| {r['name']} | {r['region']} | {r['difference_count']:,} "
                  f"| {r['first_mismatch'] or 'none'} | {sync} |")
    md += ["", "Reference banners: "+str(checks["reference_forth_banners"]),
           "Canonical banners: "+str(checks["canonical_forth_banners"]), "",
           "**Decision status:** diagnostic only. No historical component is promoted.",
           "No reference, configuration, source lock, inventory, or EEPROM is changed.", ""]
    (args.output / "audit.md").write_text("\n".join(md))
    print("\n".join(md))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
