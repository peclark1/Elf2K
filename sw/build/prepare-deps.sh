#!/usr/bin/env bash
set -euo pipefail

# Fetch/build the external tool and source revisions needed by the stock ROM.
# Every dependency is pinned so upstream changes cannot silently change output.
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
DEPS="${ELF2K_DEPS_DIR:-$ROOT/.build/deps}"
mkdir -p "$DEPS"

clone_at() {
    local name="$1" url="$2" sha="$3"
    local dir="$DEPS/$name"
    if [[ ! -d "$dir/.git" ]]; then
        rm -rf "$dir"
        git clone --quiet --no-checkout "$url" "$dir"
    fi
    git -C "$dir" fetch --quiet --depth 1 origin "$sha"
    git -C "$dir" checkout --quiet --detach FETCH_HEAD
}

clone_at stg-tools https://github.com/SpareTimeGizmos/tools.git bfb20d0af74adecd5363377a474c60460dacf860
clone_at rcasm https://github.com/wd5gnr/RcAsm.git fd1ea3092da6904ae8ecf1b01f1dc6773c992ded
clone_at asm02 https://github.com/rileym65/Asm-02.git a99bbca5e2ae425adff216f7df72ffbe0ed68faf
clone_at stgrom-archive https://github.com/wd5gnr/1802black.git 1d5f8b2bb4295d83a6ac35db06c43c7eb009ec34
clone_at rcforth https://github.com/rileym65/Elf-RcForth.git d9de6b36190d811b7d962d7c495b31c5ff23e2d5
clone_at edtasm https://github.com/rileym65/Elf-EDTASM.git 2fe52285245c206769ebe4e3d4707a3cced328c8
clone_at visual02 https://github.com/rileym65/Elf-Visual02.git 61f7c978d01509086195084155fbe3f5fc014fc9
clone_at elfops https://github.com/fourstix/Elfos-Diskless-Rom.git 8262a74c822e7c8ca4371b078feb9cf39104e75f

make -s -C "$DEPS/stg-tools/tasm35"
make -s -C "$DEPS/stg-tools/rommerge"
make -s -C "$DEPS/stg-tools/romcksum"
make -s -C "$DEPS/stg-tools/romtext"
make -s -C "$DEPS/rcasm"
make -s -C "$DEPS/asm02"

printf "%s\n" "$DEPS"
