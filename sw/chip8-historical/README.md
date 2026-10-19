# CRITICAL CORRECTION — 2026-10-18

The **first** Netronics 1979 RAM test image generated in this project was **invalid**: *Ipso Facto* #11 Table 2 row **$0100** was mistakenly transcribed as **$0010**. That overwrote the interpreter's critical initialization instructions at $0010–$0013 and failed to install the intended $0104–$0107 instructions. This is a **source transcription error**, not a Netronics ELF II hardware diagnosis.

**Use only the revised HEX files on this branch (commits after the correction).** The initial ZIP `Netronics-ELF-II-CHIP8-1979-First-Test.zip` and earlier downloaded standalone test HEX files are **superseded**.

Corrected checks: `$0010–$0017 = B4 F8 1B A4 F8 01 B5 F8` and `$0100–$0107 = 00 00 00 00 F8 01 B5 F8`.

New verified full-image SHA256: **Four-Squares** `1f4ab52bb8dfe726ca77b1b3d12a0707bc44b57d676244473c2c99f5545d6737`; **Maze** `d7fec6517a7f063b3b455f4761c2eaa96e518d9fcd98c642fb08b317d1318587`.

The fixed RAM HEX files are still **not hardware-verified**. No AVI ROM image has been changed.

---

# Netronics ELF II / 1979 CHIP-8 reconstruction (experimental)
Derived from M. E. Franklin/Lynn Clock, *Ipso Facto* Issue 11 (April 1979), printed pp. 35–38, with Issue 12 (June 1979), printed p. 55 erratum.
The tables in the article are **patches**, not complete code. This folder preserves two matching archived RCA VIP 512-byte base images (converted to Intel HEX with address $0000), exact patch rows as `patches.txt`, and reproducible RAM test images.

Base image source: [Emma 02 `data/Vip/vip.rom` and `chip8.ram`](https://github.com/etxmato/emma_02/tree/master/data/Vip). They match the interpreter originally included in the owner's Maze HEX at $0000–$01FF.
The Maze program itself ($0200–$0221) is taken from the owner's supplied file, not included in the upstream RCA base.

`Netronics-1979-CHIP8-Four-Squares.hex` and `Netronics-1979-CHIP8-Maze.hex` are full **3584-byte RAM images $0000–$0DFF**, containing relocated/patched VIP OS at $0C00–$0DFF and CHIP-8 at $0000–$01FF. Intel HEX lines checksum to zero. Do NOT flash them as a 32K ROM. They are **NOT hardware-tested**.

Each is rebuilt independently from the documented sources; recorded 16-bit byte sums: Four-Squares `09E3`, Maze `0466`. Note these sums are not ROM checksums; the source AVI ROM and cassette routines are untouched.

Hardware bench flow: normal terminal Intel HEX upload → optional `EXAMINE 0000 0002` = `C0 0C 10` → `EXAMINE 01F8 01FF` = `06 30 9B 00 00 E0 00 4B` → `RUN 0000`; video on the CDP1861, no expected COM1 terminal output. First test Four-Squares (four white outlined 8×8 sprites), then Maze (maze pattern) only if video stable. Reset to return to the monitor. This overwrites Tiny BASIC in low RAM; do not make hardware jumper changes based on this test.

The paired ZIP with a full Python rebuild and validity checks is provided in the project conversation. Next milestone is on-hardware validation, then an optional ROM-resident `CHIP8` launcher (not yet coded).