#!/usr/bin/env bash
# Separate historical reconstruction continuation. Every patch is in .build.
# This is NOT the official stock image build and does not edit its inputs.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
DEPS="$ROOT/.build/deps"
WORK="$ROOT/.build/stock-rom-repro/first/work"
OUT="$ROOT/.build/historical-reconstruction"
REF="$ROOT/sw/Elf2K-alternate.hex"
BASE="$ROOT/.build/stock-compat-probes/bios-three-short-branches"
mkdir -p "$OUT"
test -s "$WORK/config.inc"
test -s "$BASE/bios.hex"
test -s "$BASE/bios.lst"
test -s "$BASE/bios.asm"

# Historical EDTASM: original archive has DATA 1000h, modern source 4000h.
# Verify whether swapping ONLY the archived STGROM workspace explains other
# differences. This is a diagnostic, never a production decision.
EDI="$OUT/edtasm-archive-workspace-4000"
mkdir -p "$EDI"
cp "$DEPS/stgrom-archive/bios/edtasm.asm" "$EDI/edtasm.asm"
cp "$WORK/config.inc" "$WORK/bios.inc" "$EDI/"
python3 - "$EDI/edtasm.asm" <<'PY'
from pathlib import Path
import re, sys
path=Path(sys.argv[1])
s=path.read_text()
head,marker,tail=s.partition("#ifdef STGROM")
if not marker: raise SystemExit("STGROM section absent")
tail,count=re.subn(r"(?m)^(#define[ \t]+DATA[ \t]+)01000h\b",
                   r"\g<1>04000h",tail,count=1)
if count!=1: raise SystemExit(f"Archive STG workspace match count {count} !=1")
path.write_text(head+marker+tail)
PY
python3 "$ROOT/sw/build/normalize-rcasm.py" "$EDI/edtasm.asm"
if (cd "$EDI" && RCASM_DIR="$DEPS/rcasm/" "$DEPS/rcasm/rcasm" -v -h -l -x -d1802 -DELF2K -DSTGROM edtasm.asm >edtasm.lst 2>&1); then
  python3 "$ROOT/sw/build/compare-component.py" "$REF" "$EDI/edtasm.hex" A400 B100 >"$EDI/comparison.txt" || true
else
  printf '%s\n' 'Archived EDTASM 4000h assembly failed' >"$EDI/comparison.txt"
fi
cat "$EDI/comparison.txt"

# Previous depth-one BIOS greedy trial stopped as soon as an individual
# branch contraction worsened the total. This deliberately continues after
# that reversal, with one exact-address-identified edit at a time. Every
# prefix is independently kept, so a temporary regression is inspectable.
BIOS="$OUT/bios-lookahead"
mkdir -p "$BIOS"
cp "$BASE/bios.asm" "$BASE/bios.hex" "$BASE/bios.lst" "$BIOS/"
cp "$WORK/config.inc" "$WORK/bios.inc" "$BIOS/"
: > "$BIOS/ledger.txt"
for step in $(seq 1 12); do
  cp "$BIOS/bios.asm" "$BIOS/bios-before-$step.asm"
  if ! python3 "$ROOT/sw/build/probe-bios-next-branch.py" "$REF" "$BIOS/bios.hex" "$BIOS/bios.lst" "$BIOS/bios.asm" >"$BIOS/step-$step.txt" 2>&1; then
    cat "$BIOS/step-$step.txt" | tee -a "$BIOS/ledger.txt"
    break
  fi
  if ! (cd "$BIOS" && RCASM_DIR="$DEPS/rcasm/" "$DEPS/rcasm/rcasm" -v -h -l -x -d1802 -DELF2K -DSTGROM bios.asm >bios.lst 2>&1); then
    echo "Step $step assembler rejected candidate" | tee -a "$BIOS/ledger.txt"
    cp "$BIOS/bios-before-$step.asm" "$BIOS/bios.asm"
    break
  fi
  python3 "$ROOT/sw/build/compare-component.py" "$REF" "$BIOS/bios.hex" F300 10000 >"$BIOS/comparison-$step.txt" || true
  cp "$BIOS/bios.asm" "$BIOS/bios-step-$step.asm"
  cp "$BIOS/bios.hex" "$BIOS/bios-step-$step.hex"
  cp "$BIOS/bios.lst" "$BIOS/bios-step-$step.lst"
  cat "$BIOS/step-$step.txt" "$BIOS/comparison-$step.txt" | head -n 13 | tee -a "$BIOS/ledger.txt"
  if grep -q 'diff_count=0 ' "$BIOS/comparison-$step.txt"; then break; fi
done
echo "All BIOS lookahead candidates remain isolated; no reference data was altered." | tee -a "$BIOS/ledger.txt"

# The archive's Forth 0.3 forth1.asm provides an alternative display routine
# with a #if 0 block around the ONLY 'disp:' label. Yet 38 historical
# DW disp sites refer to it. Test inserting that existing symbolic entry name
# before the historical replacement routine in a disposable copy ONLY.
FORTH="$OUT/forth1-disposable-disp-label"
mkdir -p "$FORTH"
cp "$ROOT/.build/stock-compat-probes/archive-forth1-asm02/forth.asm" "$FORTH/forth.asm"
cp "$ROOT/.build/stock-compat-probes/archive-forth1-asm02/config.inc" "$FORTH/"
cp "$ROOT/.build/stock-compat-probes/archive-forth1-asm02/bios.inc" "$FORTH/"
cp "$ROOT/.build/stock-compat-probes/archive-forth1-asm02/ops.inc" "$FORTH/"
python3 - "$FORTH/forth.asm" <<'PY'
from pathlib import Path
import re,sys
path=Path(sys.argv[1])
text=path.read_text()
pattern=r"(?s)(#if 0[ \t]*\ndisp:[^\n]*\n.*?\n#else[ \t]*\n)(#ifdef ELFOS)"
patched,n=re.subn(pattern,r"\1disp:\n\2",text,count=1)
if n!=1:
    raise SystemExit(f"Historical forth1 display label anchor count {n} != 1")
path.write_text(patched)
PY
echo "======= ARCHIVED FORTH 0.3: DISPOSABLE FORWARD-LABEL TRIAL ======="
if (cd "$FORTH" && "$DEPS/asm02/asm02" -i -L -s -DELF2K -DSTGROM forth.asm >forth.lst 2>&1); then
  echo "Historical 0.3 source assembles after restoring missing DISP entry label"
  grep -E '^(Code Generated|Errors|Lines Assembled)' "$FORTH/forth.lst" || true
  python3 "$ROOT/sw/build/compare-component.py" "$REF" "$FORTH/forth.hex" DC00 F000 >"$FORTH/comparison.txt" || true
  head -n 11 "$FORTH/comparison.txt"
  python3 - "$FORTH/forth.hex" <<'PY'
import sys
from pathlib import Path
end=0
for line in Path(sys.argv[1]).read_text().splitlines():
    if not line.startswith(':'): continue
    raw=bytes.fromhex(line[1:])
    if raw[3]==0:
        end=max(end,(raw[1]<<8)+raw[2]+raw[0])
print(f"Historical forth1 emitted end address (exclusive): ${end:04X}; stock slot ends at ${0xF000:04X}")
if end > 0xF000:
    print("OVERLAP: candidate cannot replace the stock Forth component unchanged")
PY
else
  echo "Forth1 label correction was insufficient; see assembler diagnostic"
  grep -n 'ERROR' "$FORTH/forth.lst" | head -n 16 || true
fi
echo "Forth1 trial retained only under disposable reconstruction artifacts."
