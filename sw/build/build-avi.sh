#!/usr/bin/env bash
set -euo pipefail

# Reproducible, independent AVI ROM development build. NO EEPROM operations.
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SW="$ROOT/sw"
BUILD_ROOT="${ELF2K_BUILD_DIR:-$ROOT/.build/avi-rom}"
WORK="$BUILD_ROOT/work"
DEPS="${ELF2K_DEPS_DIR:-$ROOT/.build/deps}"

"$SW/build/prepare-deps.sh" >/dev/null
rm -rf "$WORK"
mkdir -p "$WORK"
cp "$SW/Makefile" "$WORK/"
cp "$SW"/boots.asm "$SW"/boots.inc "$SW"/hardware.inc "$WORK/"
cp "$SW"/config.AVIElf2 "$SW"/help.AVIElf2 "$SW"/giantboard.hex "$WORK/"
cp "$SW"/avi-cassette.asm "$SW"/avi-chip8.asm "$WORK/"

# Omitting SEDIT/Forth changes code placement. The original one-page BZ
# in SHOW CPU can then cross a page. Fix only the disposable AVI copy:
# use the 1802's three-byte long conditional branch; no stock file changes.
python3 - "$WORK/boots.asm" <<'PY'
from pathlib import Path
import sys
p = Path(sys.argv[1])
s = p.read_text()
patches = (
    ("\tBZ\tCPU02\t\t; branch if it's a 1802",
     "\tLBZ\tCPU02\t\t; branch if it's a 1802"),
    ("\tBZ\tTDEC1B\t\t;  ...",
     "\tLBZ\tTDEC1B\t\t;  ..."),
)
for before, after in patches:
    if s.count(before) != 1:
        raise SystemExit("Expected one AVI-only branch to patch: " + before)
    s = s.replace(before, after)
p.write_text(s)
PY

cp "$DEPS/stgrom-archive/bios"/bios.asm "$DEPS/stgrom-archive/bios"/bios.inc "$WORK/"
# Apply AVI-only hardware-port safety guards to disposable sources.
python3 "$SW/build/avi-port.py" "$WORK"
cp "$DEPS/edtasm"/edtasm.asm "$WORK/"

# EDTASM's optional 'V' command unconditionally references Visual/02.
# While Visual/02 is deferred, turn the command into a safe monitor return.
# Work on the disposable copy only; do NOT touch the pinned Riley source.
python3 - "$WORK/edtasm.asm" <<'PY'
from pathlib import Path
import sys
p = Path(sys.argv[1])
s = p.read_text()
changes = (("lbz     visual02", "lbz     exitaddr"),
           ("lbr     visual+3", "lbr     exitaddr"))
for before, after in changes:
    if s.count(before) != 1:
        raise SystemExit("Expected EDTASM Visual/02 hook: " + before)
    s = s.replace(before, after)
# The stock editor/assembler still has S/L commands backed by XMODEM.
# Keep the historical text editor but disable those two entry points instead
# of letting either jump into the new Giant Monitor or unpopulated F100.
import re
for label in ("save", "load"):
    pattern = re.compile(r"(?m)^" + label + r":")
    if len(pattern.findall(s)) != 1:
        raise SystemExit("Expected one EDTASM " + label + " entry")
    s = pattern.sub(label + ":\n        lbr     mainlp     ; disabled: XMODEM omitted in AVI", s)
# XMODEM symbols are still referenced by unreachable code. Bind them to an
# unused address only in this disposable editor copy, never in config.inc.
s = "#define XMODEM 0f100h\n" + s
p.write_text(s)
PY


for src in bios.asm edtasm.asm; do
  python3 "$SW/build/normalize-rcasm.py" "$WORK/$src"
done

cp "$DEPS/visual02/visual02.asm" "$WORK/visual02.asm"
cp "$DEPS/elfops/include/ops.inc" "$WORK/ops.inc"
sed -i -e 's|#include ../ops.inc|#include "ops.inc"|' \
       -e 's|include[[:space:]]*../bios.inc|include bios.inc|' \
       "$WORK/visual02.asm"

MAKE_ARGS=(
  PLATFORM=AVIElf2
  TASM="$DEPS/stg-tools/tasm35/tasm"
  TASMTABS="$DEPS/stg-tools/tasm35/tables"
  ASM02="$DEPS/asm02/asm02"
  RCASM="$DEPS/rcasm/rcasm"
  RCASM_DIR="$DEPS/rcasm/"
  ROMMERGE="$DEPS/stg-tools/rommerge/rommerge"
  ROMCKSUM="$DEPS/stg-tools/romcksum/romcksum"
  ROMTEXT="$DEPS/stg-tools/romtext/romtext"
)

# TASM needs original bios.inc; Rc/Asm uses normalized constants.
make -C "$WORK" "${MAKE_ARGS[@]}" boots.hex
python3 "$SW/build/normalize-rcasm-include.py" "$WORK/bios.inc"
touch "$WORK/boots.hex"
make -C "$WORK" "${MAKE_ARGS[@]}"
python3 "$SW/build/verify-avi.py" "$WORK/AVIElf2.hex"
printf '\nAVIElf2 development ROM: %s\n' "$WORK/AVIElf2.hex"
