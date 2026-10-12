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


# ARCHIVED STOCK-SOURCE TRIALS: one disposable component at a time.
# Use the already pinned archive, without changing configuration, tools,
# software selections, original ROM, or any production source pins.
ARCHIVE="$DEPS/stgrom-archive/bios"
ARCHIVE_SHA="1d5f8b2bb4295d83a6ac35db06c43c7eb009ec34"
[[ "$(git -C "$DEPS/stgrom-archive" rev-parse HEAD)" == "$ARCHIVE_SHA" ]] || {
    echo "Archive not at the pinned SHA; refusing trials" >&2
    exit 1
}

archive_trial() {
    local source="$1" component="$2" start="$3" end="$4" variant="$5"
    local trial="$OUT/archive-$variant"
    echo "======= ARCHIVED STOCK-SOURCE TRIAL: $variant ======="
    rm -rf "$trial"
    mkdir -p "$trial"
    cp "$WORK/config.inc" "$WORK/bios.inc" "$trial/"
    cp "$ARCHIVE/$source.asm" "$trial/$component.asm"
    if ! python3 "$ROOT/sw/build/normalize-rcasm.py" "$trial/$component.asm" >"$trial/prepare.log" 2>&1; then
        echo "SOURCE PREPARATION FAILED: $variant"
        cat "$trial/prepare.log"
        return 0
    fi
    local -a options=(-v -h -l -x -d1802 -DELF2K -DSTGROM)
    if [[ "$component" == forth ]]; then options+=(-DNO_BLOAD); fi
    if ! (cd "$trial" && "$DEPS/rcasm/rcasm" "${options[@]}" "$component.asm" >"$component.lst" 2>&1) || [[ ! -s "$trial/$component.hex" ]]; then
        echo "ASSEMBLER FAILED OR NO HEX: $variant"
        tail -n 16 "$trial/$component.lst" 2>/dev/null || true
        return 0
    fi
    if python3 "$ROOT/sw/build/compare-component.py" "$REF" "$trial/$component.hex" "$start" "$end" >"$trial/comparison.txt" 2>&1; then
        echo "EXACT COMPONENT MATCH: $variant"
    else
        echo "COMPONENT DIFFERENCES REMAIN: $variant"
    fi
    sed -n '1,9p' "$trial/comparison.txt"
}
archive_trial edtasm edtasm A400 B100 edtasm
archive_trial visual02 visual02 B100 C200 visual02
archive_trial forth0 forth DC00 F000 forth0
archive_trial forth1 forth DC00 F000 forth1
archive_trial bios bios F300 10000 bios
echo "Archived component trials complete; production pins and reference unchanged."


# ARCHIVE ASM/02 FORTH: the archive Makefile explicitly uses ASM02,
# not RcAsm, for its newer rc/Forth assembly. Re-check both 0.3 candidates
# with that original assembler family and no changes to their byte semantics.
archive_forth_asm02() {
    local source="$1" trial="$OUT/archive-$1-asm02"
    echo "======= ARCHIVE ASM/02 FORTH TRIAL: $source ======="
    rm -rf "$trial"
    mkdir -p "$trial"
    cp "$WORK/config.inc" "$WORK/bios.inc" "$trial/"
    cp "$ARCHIVE/$source.asm" "$trial/forth.asm"
    # Asm/02 requires preprocessor-form includes. Only two active
    # STGROM include directives are converted; no target addresses changed.
    python3 - "$trial/forth.asm" <<'PY'
from pathlib import Path
import re
import sys
p = Path(sys.argv[1])
s = p.read_text(encoding="utf-8")
for name in ("config.inc", "bios.inc"):
    s, n = re.subn(r"(?im)^(\s*)include\s+" + re.escape(name) + r"(\s*)$",
                   r"\1#include " + name + r"\2", s)
    if n != 1:
        raise SystemExit(f"expected exactly one {name} include, got {n}")
p.write_text(s, encoding="utf-8")
PY
    if ! (cd "$trial" && "$DEPS/asm02/asm02" -i -L -s -DELF2K -DSTGROM forth.asm >forth.lst 2>&1) || [[ ! -s "$trial/forth.hex" ]]; then
        echo "ASM/02 ASSEMBLY FAILED OR NO HEX: $source"
        grep -in -E 'error|undefined|invalid|not found' "$trial/forth.lst" | head -n 24 || true
        tail -n 8 "$trial/forth.lst" || true
        return 0
    fi
    if python3 "$ROOT/sw/build/compare-component.py" "$REF" "$trial/forth.hex" DC00 F000 >"$trial/comparison.txt" 2>&1; then
        echo "EXACT FORTH 0.3 MATCH: $source"
    else
        echo "FORTH 0.3 DIFFERENCES REMAIN: $source"
    fi
    sed -n '1,9p' "$trial/comparison.txt"
}
archive_forth_asm02 forth0
archive_forth_asm02 forth1
echo "Forth ASM/02 trials complete; reference and stock configuration unchanged."
