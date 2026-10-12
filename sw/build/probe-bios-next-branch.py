#!/usr/bin/env python3
"""Find the next historically plausible long->short branch beyond operand deltas.

Diagnostic only: changes a disposable BIOS source supplied by the caller.
Both bytes and the assembled listing MUST identify a long branch at the same
address, and the target must fit a CDP1802 short branch in that page.
"""
from __future__ import annotations
from pathlib import Path
import re
import runpy
import sys

TOOLS = runpy.run_path(str(Path(__file__).with_name("probe-bios-branches.py")))
load = TOOLS["load"]
LONG_TO_SHORT = TOOLS["LONG_TO_SHORT"]

def patch(reference: Path, compiled: Path, listing: Path, source: Path) -> tuple[int,str]:
    original = load(reference, 0)
    candidate = load(compiled, 0x8000)
    start, end = 0xF300 - 0x8000, 0x10000 - 0x8000
    diffs = [i for i in range(start,end) if original[i] != candidate[i]]
    if not diffs:
        return 1, "BIOS EXACT MATCH; no edit required"
    lines = listing.read_text(errors="replace").splitlines()
    code_at = {}
    for line in lines:
        m = re.match(r"\s*\d+\s+([0-9a-fA-F]{4}):\s+([0-9a-fA-F]{2})\s+",line)
        if m: code_at[int(m.group(1),16)] = line
    body = source.read_text()
    skipped = []
    for index in diffs:
        address = index + 0x8000
        expected,actual = original[index],candidate[index]
        choice = LONG_TO_SHORT.get(actual)
        if not choice or choice[0] != expected:
            if len(skipped) < 6: skipped.append(f"${address:04X}: {expected:02X}/{actual:02X} nonbranch")
            continue
        _, old, new = choice
        matchline = code_at.get(address)
        if not matchline or not re.search(r"\b"+re.escape(old)+r"\s+",matchline,re.I):
            continue
        matchtarget = re.search(r"\b"+re.escape(old)+r"\s+([\w.$?]+)\b",matchline,re.I)
        if not matchtarget: continue
        target = matchtarget.group(1)
        # Current long branch destination's high byte must equal the page
        # after the two-byte short branch. Enforce 1802 short-branch legality.
        if index+2 >= len(candidate) or candidate[index+1] != ((address+2)>>8)&255:
            continue
        pat = re.compile(r"(?im)^([ \t]*)"+re.escape(old)+r"([ \t]+)"+re.escape(target)+r"\b")
        hits = list(pat.finditer(body))
        if len(hits) > 1 and ";" in matchline:
            comment = matchline.split(";",1)[1].strip()
            hits = [h for h in hits if ";" in body[h.start():body.find("\n",h.end())] and
                    body[h.start():body.find("\n",h.end())].split(";",1)[1].strip()==comment]
        if len(hits) != 1: continue
        hit = hits[0]
        source.write_text(body[:hit.start()]+hit.group(1)+new+hit.group(2)+target+body[hit.end():])
        return 0,(f"First differing offset ${diffs[0]+0x8000:04X}; skipped operand/nonbranch bytes: "
                  +"; ".join(skipped)+"\n"
                  +f"REFERENCE-BACKED EXPERIMENT: ${address:04X} {old.upper()} {target} -> {new.upper()} {target}")
    return 1,("No unambiguous same-page short branch after first mismatch "
              +f"${diffs[0]+0x8000:04X}; skipped: "+"; ".join(skipped))

if __name__ == "__main__":
    if len(sys.argv)!=5:
        print("usage: probe-bios-next-branch.py REF.hex bios.hex bios.lst bios.asm",file=sys.stderr)
        raise SystemExit(2)
    code, message=patch(*map(Path,sys.argv[1:]))
    print(message)
    raise SystemExit(code)
