#!/usr/bin/env bash
# Isolated ROM-forensic source semantics experiment. Does NOT approve changes.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
OUT="$ROOT/.build/historical-reconstruction"
BASE="$OUT/bios-lookahead"
TRIAL="$OUT/bios-semantic-register-transfer"
WORK="$ROOT/.build/stock-rom-repro/first/work"
DEPS="$ROOT/.build/deps"
REF="$ROOT/sw/Elf2K-alternate.hex"
mkdir -p "$TRIAL"
test -s "$BASE/bios-step-5.asm"
cp "$BASE/bios-step-5.asm" "$TRIAL/bios.asm"
cp "$WORK/config.inc" "$WORK/bios.inc" "$TRIAL/"
python3 - "$TRIAL/bios.asm" <<'PY'
from pathlib import Path
import re,sys
p=Path(sys.argv[1])
text=p.read_text()
# Two reference bytes after reading first two IDE size bytes match the
# two register-transfer opcodes PLO RF and PHI RF, respectively.
# Pin context and require a unique original snippet, never edit a second site.
pat=(r"(?im)^(\s*plo\s+r7\b[^\n]*\n)"
     r"(\s*inp\s+IDE_DATA\b[^\n]*\n)"
     r"(\s*phi\s+r7\b[^\n]*\n)"
     r"(\s*inp\s+IDE_DATA\b)")
def insert(m):
    return (m.group(1)+"        plo     rf ; EXPERIMENT: ref has AF\n"+
            m.group(2)+m.group(3)+
            "        phi     rf ; EXPERIMENT: ref has BF\n"+m.group(4))
updated,count=re.subn(pat,insert,text)
if count != 1: raise SystemExit(f"Expected exactly one historic IDE size sequence: got {count}")
p.write_text(updated)
print("TEST ONLY: add source opcodes matching original bytes AF/BF; semantic change NOT approved")
PY
cd "$TRIAL"
assemble() {
  RCASM_DIR="$DEPS/rcasm/" "$DEPS/rcasm/rcasm" -v -h -l -x -d1802 -DELF2K -DSTGROM bios.asm >bios.lst 2>&1
}
assemble
python3 "$ROOT/sw/build/compare-component.py" "$REF" bios.hex F300 10000 >comparison-0.txt || true
head -n 11 comparison-0.txt
cp bios.asm bios-step-0.asm
cp bios.hex bios-step-0.hex
cp bios.lst bios-step-0.lst
: >ledger.txt
for i in $(seq 1 15); do
  cp bios.asm bios-before-"$i".asm
  if ! python3 "$ROOT/sw/build/probe-bios-next-branch.py" "$REF" bios.hex bios.lst bios.asm >step-"$i".txt 2>&1; then
    cat step-"$i".txt | tee -a ledger.txt
    break
  fi
  if ! assemble; then
    echo "FAILED ASSEMBLY; keeping earlier diagnostic result"
    cp bios-before-"$i".asm bios.asm
    break
  fi
  python3 "$ROOT/sw/build/compare-component.py" "$REF" bios.hex F300 10000 >comparison-"$i".txt || true
  cp bios.asm bios-step-"$i".asm
  cp bios.hex bios-step-"$i".hex
  cp bios.lst bios-step-"$i".lst
  cat step-"$i".txt | tee -a ledger.txt
  head -n 2 comparison-"$i".txt | tee -a ledger.txt
  grep -q 'diff_count=0 ' comparison-"$i".txt && break
done
echo "Completed semantic hypothesis in disposable branch only." | tee -a ledger.txt
