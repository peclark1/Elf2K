#!/usr/bin/env bash
# Diagnostic only: build historical revisions of the SAME stock ROM components
# in separate disposable directories. Never change tracked source, source pins,
# reference image, or the selected ROM composition.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
DEPS="$ROOT/.build/deps"
WORK="$ROOT/.build/stock-rom/work"
OUT="$ROOT/.build/stock-source-probes"
REF="$ROOT/sw/Elf2K-alternate.hex"
if [[ ! -f "$WORK/config.inc" || ! -f "$WORK/bios.inc" ]]; then
  echo "Stock build artifacts not available; skipping historical source probes."
  exit 0
fi
mkdir -p "$OUT"
export RCASM_DIR="$DEPS/rcasm/"

probe() {
  local dep="$1" component="$2" commit="$3" start="$4" end="$5" assembler="$6"
  local prefix trial result
  prefix="$(printf '%s' "$commit" | cut -c1-8)"
  trial="$OUT/$component-$prefix"
  mkdir -p "$trial"
  cp "$WORK/config.inc" "$WORK/bios.inc" "$trial/"
  cp "$WORK/ops.inc" "$trial/" 2>/dev/null || true
  printf '\n===== %s at %s (%s) =====\n' "$component" "$prefix" "$dep"

  if ! git -C "$DEPS/$dep" fetch --quiet --depth 1 origin "$commit" >"$trial/fetch.log" 2>&1; then
    printf 'FETCH FAILED: %s\n' "$trial/fetch.log"
    cat "$trial/fetch.log"
    return 0
  fi
  if ! git -C "$DEPS/$dep" show "FETCH_HEAD:$component.asm" >"$trial/$component.asm"; then
    echo "MISSING HISTORICAL SOURCE: $component.asm"
    return 0
  fi

  if [[ "$assembler" == "asm02" ]]; then
    if ! python3 "$ROOT/sw/build/prepare-asm02-source.py" "$trial/$component.asm" >"$trial/prepare.log" 2>&1; then
      echo "SOURCE PREPARATION FAILED"; cat "$trial/prepare.log"; return 0
    fi
    if (cd "$trial" && "$DEPS/asm02/asm02" -i -L -s -DELF2K -DSTGROM "$component.asm" >"$component.lst" 2>&1); then
      result=assembled
    else
      result=assembler-failed
    fi
  else
    if ! python3 "$ROOT/sw/build/normalize-rcasm.py" "$trial/$component.asm" >"$trial/prepare.log" 2>&1; then
      echo "SOURCE PREPARATION FAILED"; cat "$trial/prepare.log"; return 0
    fi
    if [[ "$component" == "forth" ]]; then
      if (cd "$trial" && "$DEPS/rcasm/rcasm" -v -h -l -x -d1802 -DELF2K -DSTGROM -DNO_BLOAD "$component.asm" >"$component.lst" 2>&1); then
        result=assembled
      else
        result=assembler-failed
      fi
    else
      if (cd "$trial" && "$DEPS/rcasm/rcasm" -v -h -l -x -d1802 -DELF2K -DSTGROM "$component.asm" >"$component.lst" 2>&1); then
        result=assembled
      else
        result=assembler-failed
      fi
    fi
  fi
  if [[ "$result" != assembled || ! -s "$trial/$component.hex" ]]; then
    echo "ASSEMBLER FAILED OR DID NOT EMIT HEX: $trial/$component.lst"
    tail -n 30 "$trial/$component.lst" || true
    return 0
  fi
  if python3 "$ROOT/sw/build/compare-component.py" "$REF" "$trial/$component.hex" "$start" "$end" >"$trial/comparison.txt" 2>&1; then
    echo "EXACT COMPONENT MATCH"
  else
    echo "COMPONENT DOES NOT MATCH REFERENCE"
  fi
  head -n 10 "$trial/comparison.txt"
}

# Original component identities and ROM map remain fixed. Dates/SHAs from
# the upstream commit history are tested, not adopted as new source locks.
probe edtasm edtasm 2fe52285245c206769ebe4e3d4707a3cced328c8 A400 B100 rcasm
probe edtasm edtasm e16c07110b0d89a43669af6c41f9d271932f536f A400 B100 rcasm
probe rcforth forth d9de6b36190d811b7d962d7c495b31c5ff23e2d5 DC00 F000 rcasm
probe rcforth forth 556a89b42bacd2d2ecd0f732972df0f4ed3ccf4e DC00 F000 rcasm
probe rcforth forth c5ca5fb70dbc0ccfd7cf07dfe25de64c7b88638a DC00 F000 rcasm
probe rcforth forth 9ecf9fdc2819f38f420abb172f7eb57645d2392e DC00 F000 rcasm
probe visual02 visual02 61f7c978d01509086195084155fbe3f5fc014fc9 B100 C200 asm02
probe visual02 visual02 f0f3cf915cce78d81e62dcd1d2b3f9ecd2ea1327 B100 C200 asm02
probe visual02 visual02 fe0ddc3ed975343077fb7d27a80f7af44a5ae77a B100 C200 asm02
echo "Historical revision probes complete; strict stock reference gate unchanged."
