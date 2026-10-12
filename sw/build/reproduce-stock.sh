#!/usr/bin/env bash
# Reproduce the untouched stock alternate ROM twice in distinct clean trees.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
SW="$ROOT/sw"
OUT="$ROOT/.build/stock-rom-repro"
REF="$SW/Elf2K-alternate.hex"
FIRST="$OUT/first/work/Elf2K-alternate.hex"
SECOND="$OUT/second/work/Elf2K-alternate.hex"

EXPECTED_BLOB="e1a14af17671dae2b051b53a7ae186d639e7f5b9"
EXPECTED_HEX_SHA256="db8d5148b7cb507613a20b28dc31abfce1b1f500cb69a8c2e348cfaea2ab6a4b"
ACTUAL_BLOB="$(git -C "$ROOT" hash-object "$REF")"
ACTUAL_SHA256="$(sha256sum "$REF" | cut -d' ' -f1)"
if [[ "$ACTUAL_BLOB" != "$EXPECTED_BLOB" || "$ACTUAL_SHA256" != "$EXPECTED_HEX_SHA256" ]]; then
  echo "ERROR: tracked stock reference has changed; refusing to compare against it" >&2
  exit 1
fi

printf 'Reference blob: %s\nReference HEX SHA-256: %s\n' "$ACTUAL_BLOB" "$ACTUAL_SHA256"
printf 'Python: '; python3 --version
printf 'GCC: '; gcc --version | head -n 1
printf 'Make: '; make --version | head -n 1

for label in first second; do
  echo "======= CLEAN STOCK BUILD: $label ======="
  rm -rf "$OUT/$label"
  mkdir -p "$OUT/$label"
  ELF2K_COMPARE_REFERENCE=0 ELF2K_BUILD_DIR="$OUT/$label" "$SW/build/build-stock.sh"
done

echo "======= INDEPENDENT-BUILD REPRODUCIBILITY ======="
# Check the decoded 32 KiB binary; raw Intel HEX record layout may differ.
if python3 "$SW/build/verify-rom.py" "$FIRST" "$SECOND" >"$OUT/independent-build-compare.txt" 2>&1; then
  REPRODUCIBLE=1
else
  REPRODUCIBLE=0
fi
cat "$OUT/independent-build-compare.txt"

echo "======= BUILD 1 AGAINST UNMODIFIED REFERENCE ======="
if python3 "$SW/build/verify-rom.py" "$REF" "$FIRST" >"$OUT/reference-compare-first.txt" 2>&1; then
  MATCH_FIRST=1
else
  MATCH_FIRST=0
fi
cat "$OUT/reference-compare-first.txt"

echo "======= BUILD 2 AGAINST UNMODIFIED REFERENCE ======="
if python3 "$SW/build/verify-rom.py" "$REF" "$SECOND" >"$OUT/reference-compare-second.txt" 2>&1; then
  MATCH_SECOND=1
else
  MATCH_SECOND=0
fi
cat "$OUT/reference-compare-second.txt"

echo "======= LOCKED TOOL SOURCE REVISIONS ======="
DEPS="$ROOT/.build/deps"
for dep in stg-tools rcasm asm02 stgrom-archive rcforth edtasm visual02 elfops; do
  printf '%s %s\n' "$dep" "$(git -C "$DEPS/$dep" rev-parse HEAD)"
done

printf '\nHEX SHA-256 hashes:\n'
sha256sum "$REF" "$FIRST" "$SECOND"

if ((REPRODUCIBLE)); then
  echo "INDEPENDENT BUILD RESULT: MATCH"
else
  echo "INDEPENDENT BUILD RESULT: MISMATCH" >&2
fi
if ((MATCH_FIRST && MATCH_SECOND)); then
  echo "STOCK REFERENCE RESULT: BYTE-FOR-BYTE MATCH"
else
  echo "STOCK REFERENCE RESULT: MISMATCH; baseline NOT ACCEPTED" >&2
fi

if ((REPRODUCIBLE && MATCH_FIRST && MATCH_SECOND)); then
  exit 0
fi
exit 1
