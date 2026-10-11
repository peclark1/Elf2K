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
cp "$DEPS/elf-bios"/bios.asm "$DEPS/elf-bios"/bios.inc "$WORK/"
cp "$DEPS/stgrom-archive/bios"/rcbasic.asm "$WORK/"
cp "$DEPS/stgrom-archive/bios"/sedit.asm "$WORK/"
cp "$DEPS/stgrom-archive/bios"/xmodem.asm "$WORK/"
cp "$DEPS/rcforth"/forth.asm "$WORK/"
cp "$DEPS/edtasm"/edtasm.asm "$WORK/"

# VISUAL/02 assumes Riley's old sibling-repository checkout layout.
cp "$DEPS/visual02/visual02.asm" "$WORK/visual02.asm"
cp "$DEPS/elfops/include/ops.inc" "$WORK/ops.inc"
sed -i -e 's|#include ../ops.inc|#include "ops.inc"|' \
       -e 's|include[[:space:]]*../bios.inc|include bios.inc|' \
       "$WORK/visual02.asm"

make -C "$WORK" \
  PLATFORM=Elf2K ALTERNATE=-alternate \
  TASM="$DEPS/stg-tools/tasm35/tasm" \
  TASMTABS="$DEPS/stg-tools/tasm35/tables" \
  ASM02="$DEPS/asm02/asm02" \
  RCASM="$DEPS/rcasm/rcasm" \
  RCASM_DIR="$DEPS/rcasm/" \
  ROMMERGE="$DEPS/stg-tools/rommerge/rommerge" \
  ROMCKSUM="$DEPS/stg-tools/romcksum/romcksum" \
  ROMTEXT="$DEPS/stg-tools/romtext/romtext"

python3 "$SW/build/verify-rom.py" "$SW/Elf2K-alternate.hex" "$WORK/Elf2K-alternate.hex"
printf "\nBuilt ROM: %s\n" "$WORK/Elf2K-alternate.hex"
