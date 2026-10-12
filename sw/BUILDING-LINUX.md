# Rebuilding the stock Elf2K alternate ROM on Linux

The original 2024 source distribution intentionally omitted several Michael Riley
components and hard-coded local tool paths. The helper scripts in `sw/build/`
turn that historical arrangement into a pinned, isolated Linux build.

## Host prerequisites

On Debian/Ubuntu:

```sh
sudo apt-get update
sudo apt-get install build-essential git python3
```

No DOS, Windows, MSVC, Wine, or `/usr/local/bin` installation is required.

## One-command build and verification

From the repository root:

```sh
./sw/build/build-stock.sh
```

The script fetches pinned public revisions of TASM 3.5, the STG ROM utilities,
Rc/Asm, Asm/02, and the omitted Riley sources. It builds
`PLATFORM=Elf2K ALTERNATE=-alternate` in `.build/stock-rom/work/`, then
compares the generated 32 KiB byte stream with the checked-in known-working
`sw/Elf2K-alternate.hex`.

## Independent clean-build reproduction and regression tests

Run from the repository root (these scripts may be invoked with Bash even
when their executable mode has not been preserved by GitHub's contents API):

```sh
python3 -m unittest discover -s sw/build/tests -v
bash sw/build/reproduce-stock.sh
```

The reproducer verifies the reference Git blob and SHA-256, then builds twice
in separate freshly cleared directories under `.build/stock-rom-repro/`.
Both builds share pinned toolchain sources but never generated objects or ROM
files. It compares the decoded 32 KiB images against each other and the stock
reference. Full comparison output is retained in `.build/stock-rom-repro/*.txt`.

**Current checkpoint (2026-10-12):** both independent builds assemble and
match each other exactly, but differ from the stock reference in **10,477**
bytes. The verifier exits nonzero intentionally: this is NOT an accepted
stock baseline. See `docs/STOCK_ELF2K_REPRODUCIBILITY_REPORT.md` for
SHA-256 hashes, component differences, pinned tools, and review questions.

## Modernization kept deliberately small

The stock configuration files and ROM memory map are unchanged. The Makefile
now permits tool paths and `PLATFORM`/`ALTERNATE` to be overridden from the
command line, and the old DOS rc/BASIC preprocessor include path is replaced
by a local include path.

## Locked external revisions

- SpareTimeGizmos/tools `bfb20d0af74adecd5363377a474c60460dacf860`
- wd5gnr/RcAsm `fd1ea3092da6904ae8ecf1b01f1dc6773c992ded` (2023 fork used with the STG-integrated sources)
- rileym65/Asm-02 `a99bbca5e2ae425adff216f7df72ffbe0ed68faf`
- wd5gnr/1802black `1d5f8b2bb4295d83a6ac35db06c43c7eb009ec34` (STG-integrated BIOS and application sources)
- rileym65/Elf-RcForth `d9de6b36190d811b7d962d7c495b31c5ff23e2d5`
- rileym65/Elf-EDTASM `2fe52285245c206769ebe4e3d4707a3cced328c8`
- rileym65/Elf-Visual02 `61f7c978d01509086195084155fbe3f5fc014fc9`
- fourstix/Elfos-Diskless-Rom `8262a74c822e7c8ca4371b078feb9cf39104e75f`

If byte-for-byte verification identifies a historical source mismatch, update
the explicit source lock rather than silently following an upstream branch.
