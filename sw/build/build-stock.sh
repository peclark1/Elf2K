#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SW="$ROOT/sw"
BUILD_ROOT="${ELF2K_BUILD_DIR:-$ROOT/.build/stock-rom}"
WORK="$BUILD_ROOT/work"
DEPS="${ELF2K_DEPS_DIR:-$ROOT/.build/deps}"

"$SW/build/prepare-deps.sh" >/dev/null
rm -rf "$WORK"
mkdir -p "$WORK"

# Build in a disposable tree; never overwrite the checked-in reference ROM.
cp "$SW/Makefile" "$WORK/"
cp "$SW"/boots.asm "$SW"/boots.inc "$SW"/hardware.inc "$WORK/"
cp "$SW"/config.Elf2K-alternate "$SW"/help.Elf2K-alternate "$WORK/"

# Michael Riley components omitted from the STG source distribution.
cp "$DEPS/stgrom-archive/bios"/bios.asm "$DEPS/stgrom-archive/bios"/bios.inc "$WORK/"
cp "$DEPS/stgrom-archive/bios"/rcbasic.asm "$WORK/"
cp "$DEPS/stgrom-archive/bios"/sedit.asm "$WORK/"
cp "$DEPS/stgrom-archive/bios"/xmodem.asm "$WORK/"
cp "$DEPS/rcforth"/forth.asm "$WORK/"
cp "$DEPS/edtasm"/edtasm.asm "$WORK/"

# Public Rc/Asm has a long-standing parser bug when a source line both defines
# a label and uses another symbol in the instruction. The historical STG build
# used a locally modified assembler. Split those lines in the disposable tree;
# this is source-layout-only and cannot change emitted addresses or bytes.
for src in bios.asm xmodem.asm sedit.asm edtasm.asm forth.asm; do
  python3 "$SW/build/normalize-rcasm.py" "$WORK/$src"
done

MAKE_ARGS=(
  PLATFORM=Elf2K
  ALTERNATE=-alternate
  TASM="$DEPS/stg-tools/tasm35/tasm"
  TASMTABS="$DEPS/stg-tools/tasm35/tables"
  ASM02="$DEPS/asm02/asm02"
  RCASM="$DEPS/rcasm/rcasm"
  RCASM_DIR="$DEPS/rcasm/"
  ROMMERGE="$DEPS/stg-tools/rommerge/rommerge"
  ROMCKSUM="$DEPS/stg-tools/romcksum/romcksum"
  ROMTEXT="$DEPS/stg-tools/romtext/romtext"
)

# boots.asm is assembled by TASM and needs Riley's original bios.inc syntax.
# Build it first, while bios.inc is pristine.
make -C "$WORK" "${MAKE_ARGS[@]}" boots.hex

# Convert the historical label/EQU bios.inc into preprocessor defines only
# in the disposable tree. TASM has already assembled boots.hex from its original.
# Both public Rc/Asm and Asm/02 need this normalized include.
python3 "$SW/build/normalize-rcasm-include.py" "$WORK/bios.inc"

# config.inc now exists: expand only its constants in the Asm/02 copy.
# VISUAL/02 assumes Riley's old sibling-repository checkout layout
# and mixes RcAsm-style INCLUDE with Asm/02's #include form.
cp "$DEPS/visual02/visual02.asm" "$WORK/visual02.asm"
cp "$DEPS/elfops/include/ops.inc" "$WORK/ops.inc"
# The pinned public Asm/02 expands BIOS #defines only once. Resolve those
# constants from this stock config in the disposable include, after TASM boots.
python3 "$SW/build/prepare-asm02-source.py" "$WORK/bios.inc"
python3 "$SW/build/prepare-asm02-source.py" "$WORK/visual02.asm"
# Catch missing/malformed relocated includes before Asm/02 opens NULL handles.
grep -qF '#include ops.inc' "$WORK/visual02.asm"
grep -qF '#include bios.inc' "$WORK/visual02.asm"
grep -qF '#include config.inc' "$WORK/visual02.asm"
test -f "$WORK/ops.inc"

# bios.inc is now newer than boots.hex. Mark the already verified TASM output
# newer so GNU make does not rebuild it with the Rc/Asm-only include form.
touch "$WORK/boots.hex"

if ! make -C "$WORK" "${MAKE_ARGS[@]}"; then
  # Rc/Asm and Asm/02 redirect diagnostics to .lst; surface them in CI logs.
  for listing in "$WORK"/*.lst; do
    if grep -Eiq 'error|not found|undefined' "$listing"; then
      printf '\n== Diagnostics from %s ==\n' "$listing" >&2
      grep -Ei 'error|not found|undefined' "$listing" | tail -n 60 >&2 || true
    fi
  done
  exit 1
fi

if [[ "${ELF2K_COMPARE_REFERENCE:-1}" == "1" ]]; then
  python3 "$SW/build/verify-rom.py" "$SW/Elf2K-alternate.hex" "$WORK/Elf2K-alternate.hex"
fi
printf "\nBuilt ROM: %s\n" "$WORK/Elf2K-alternate.hex"
