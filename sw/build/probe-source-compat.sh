#!/usr/bin/env bash
# Strictly diagnostic, reference-backed source-compatibility experiments.
# Patches affect only fresh .build trial copies, never tracked stock sources.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
WORK="$ROOT/.build/stock-rom-repro/first/work"
OUT="$ROOT/.build/stock-compat-probes"
DEPS="$ROOT/.build/deps"
REF="$ROOT/sw/Elf2K-alternate.hex"
[[ -s "$WORK/config.inc" && -s "$WORK/bios.inc" ]] || {
    echo "Missing first independent stock build: $WORK" >&2; exit 1;
}
export RCASM_DIR="$DEPS/rcasm/"
mkdir -p "$OUT"

probe() {
    local component="$1" variant="$2" start="$3" end="$4" assembler="$5"
    local trial="$OUT/$variant"
    rm -rf "$trial"
    mkdir -p "$trial"
    cp "$WORK/$component.asm" "$WORK/config.inc" "$WORK/bios.inc" "$trial/"
    if [[ "$assembler" == asm02 ]]; then
        cp "$WORK/ops.inc" "$trial/"
    fi
    python3 - "$trial/$component.asm" "$variant" <<'PY'
from pathlib import Path
import re
import sys
p = Path(sys.argv[1])
variant = sys.argv[2]
s = p.read_text(encoding="utf-8")
if variant == "edtasm-stg-data-1000":
    before, marker, after = s.partition("#ifdef STGROM")
    if not marker:
        raise ValueError("STGROM section not found")
    after, count = re.subn(r"(?m)^#define DATA[ \t]+04000h[ \t]*$",
                           "#define DATA     01000h", after, count=1)
    if count != 1:
        raise ValueError(f"expected exactly one EDTASM STG data declaration: {count}")
    s = before + marker + after
elif variant == "bios-short-no-uart":
    s, count = re.subn(r"(?m)^([ \t]*)lbnz([ \t]+no_uart\b)",
                       r"\1bnz\2", s, flags=re.IGNORECASE)
    if count != 2:
        raise ValueError(f"expected two BIOS no_uart long-branches: {count}")
elif variant == "visual02-zero-traps":
    pattern = (
        r"(ldi[ \t]+ntraps\.0[^\n]*\n"
        r"[ \t]*plo[ \t]+r7[^\n]*\n"
        r"[ \t]*ldi[ \t]+0[^\n]*\n"
        r"[ \t]*)plo([ \t]+r7\b)"
    )
    s, count = re.subn(pattern, r"\1str\2", s, flags=re.IGNORECASE)
    if count != 1:
        raise ValueError(f"expected exactly one Visual/02 traps initialization: {count}")
else:
    raise ValueError(f"unknown forensic variant: {variant}")
p.write_text(s, encoding="utf-8")
PY
    echo "======= REFERENCE-BACKED TRIAL: $variant ======="
    if [[ "$assembler" == asm02 ]]; then
        ( cd "$trial" && "$DEPS/asm02/asm02" -i -L -s -DELF2K -DSTGROM "$component.asm" >"$component.lst" )
    elif [[ "$component" == forth ]]; then
        ( cd "$trial" && "$DEPS/rcasm/rcasm" -v -h -l -x -d1802 -DELF2K -DSTGROM -DNO_BLOAD "$component.asm" >"$component.lst" )
    else
        ( cd "$trial" && "$DEPS/rcasm/rcasm" -v -h -l -x -d1802 -DELF2K -DSTGROM "$component.asm" >"$component.lst" )
    fi
    [[ -s "$trial/$component.hex" ]] || {
        tail -n 50 "$trial/$component.lst" >&2; exit 1;
    }
    if python3 "$ROOT/sw/build/compare-component.py" "$REF" "$trial/$component.hex" "$start" "$end" >"$trial/comparison.txt"; then
        echo "REFERENCE-MATCHES in $variant"
    else
        echo "DIFFERENCES-REMAIN in $variant"
    fi
    sed -n '1,9p' "$trial/comparison.txt"
}
probe edtasm edtasm-stg-data-1000 A400 B100 rcasm
probe bios bios-short-no-uart F300 10000 rcasm
probe visual02 visual02-zero-traps B100 C200 asm02
echo "The official stock build and unchanged reference comparison remain authoritative."
