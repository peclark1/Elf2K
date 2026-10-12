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
  if ! python3 "$ROOT/sw/build/probe-bios-branches.py" "$REF" "$BIOS/bios.hex" "$BIOS/bios.lst" "$BIOS/bios.asm" >"$BIOS/step-$step.txt" 2>&1; then
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
