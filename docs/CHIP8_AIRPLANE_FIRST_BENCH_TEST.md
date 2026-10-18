# CHIP-8 Airplane on the AVI / Netronics ELF II — first bench experiment (2026-10-18)

**Status: prepared for owner hardware test. NOT hardware-verified.** This work does NOT modify the F30A/1C62 cassette firmware or main branch.

## Source-derived discovery
- Owner's supplied `Airplane.hex` is **356 bytes** of CHIP-8 program/data, at CPU/RAM **$0600–$0763**; Intel HEX checksums verify.
- At `$0624`: `6008` loads V0=8, followed by `E0A1` at `$0626`, testing CHIP-8 **key 8**.
- The original RCA VIP CHIP-8 interpreter normally begins user programs at $0200, not $0600. Do not execute the Airplane bytes as CDP1802 machine instructions.
- There is an existing machine-code **COSMAC ELF** CHIP-8 interpreter at [Emma 02 data/Elf/chip8.hex](https://github.com/etxmato/emma_02/blob/master/data/Elf/chip8.hex), with exactly **624 noncontiguous bytes**: **$0000–$01FF** and **$0E00–$0E6F**. Its $01FC–$01FF startup CHIP-8 instructions are `00 E0 00 49` (clear screen and call machine routine $0049 to enable display).
- The original ELF 1802 interpreter's display-on routine uses `INP 1`. The current AVI firmware's `PIXIE_ON` macro also uses `INP 1` (see `sw/hardware.inc`), making video activation **plausibly compatible**. Keyboard port/timing remain to be tested on real hardware.

## First real-hardware trial (no ROM reprogramming)
Create a single Intel HEX image joining the original COSMAC ELF interpreter, the **unaltered** owner `Airplane.hex` at $0600, and a two-byte CHIP-8 instruction **`16 00`** at $0200. With the interpreter's $01FC startup, the chain becomes clear display -> enable video -> `JP $0600`.

Mem map:
- $0000–$01FF  ELF native CHIP-8 interpreter
- $0200–$0201  CHIP-8 `JP $0600` trampoline
- $0600–$0763  Original game, unchanged
- $0E00–$0E6F  Interpreter support tables and video ISR

Send the combined Intel HEX file at the existing monitor prompt, with COM1 at 2400 8N1 and video currently off. Verify `EXAMINE 01FC 0201` yields `00 E0 00 49 16 00`, and `EXAMINE 0600 060F` starts `6A 00 6B 04 6C 01 6D 00 6E 02 27 26 27 20 60 30`. Run **`RUN 0000`** and watch the Sony CRT. Try physical hex keypad **8**; it is the only virtual key the game's main code explicitly polls.

**Important:** There is no automatic return to the monitor; use the normal hardware monitor restart/reset to exit. The interpreter overwrites low RAM/Tiny BASIC and may drive the same Q output used by COM1 when sound is active, causing apparent terminal garbage. No new jumper moves required merely for this software test, but keypad I/O and PIC timing may differ from the COSMAC ELF emulator environment. Treat blank picture or nonresponsive keys as an integration clue, not proof the game file is wrong.

## Alternative
A second test could move the Airplane program from $0600 to $0200 and rewrite CHIP-8 `1NNN`, `2NNN` and `ANNN` internal targets by -$400. Avoid this unless the unmodified $0600/trampoline technique fails.

## Next firmware stage
After keyboard and video work, integrate ROM-resident CHIP-8 bootstrap as an opt-in monitor command (e.g. `CHIP8 0600`). Preserve existing ROM diagnostics, cassette support and the Giant Monitor. Keep the archival interpreter, firmware adaptation and the owner's game input as distinct, clearly attributed components.

## First bench result and isolation test (2026-10-18)

- On the AVI ELF II, the first combined image (`Airplane-ELF-II-try1-combined.hex`) **did not render an identifiable game**. User's Panasonic monitor showed alternating blocks and a scrambled 64-pixel-wide video region. The CDP1861 is producing output but interpretation/video DMA coherence are not established. Original `TEST PIXIE` had worked previously on this hardware.
- Exact owner's `Airplane.hex` has a byte-for-byte matching copy in **Emma 02 `data/Chip-8/Chip-8 ETI660 Games/Airplane.hex`**. That identifies the game's original platform as the ETI-660, which uses 64x48 CHIP-8 graphics and games at $0600, rather than the ELF 64x32 or COSMAC VIP 64x32 environment. Source: https://github.com/etxmato/emma_02/blob/master/data/Chip-8/Chip-8%20ETI660%20Games/Airplane.hex . The game appears to use common CHIP-8 instructions; do not conclude platform incompatibility alone caused the image.
- Prepared **`CHIP8-ELF-II-PIXIE-sanity-test.hex`**, a separate diagnostic combining the unchanged ELF interpreter with simple test data: `$0200:` CHIP-8 CLEAR; four outlined 8x8 sprites at (8,8), (40,8), (8,24), (40,24); stable `JP $0218` idle loop; sprite bytes `FF 81 81 81 81 81 81 FF` at $0300. The graphics diagnostic deliberately avoids ETI-660 code and key input.
- The next test is to send this new HEX as an Intel HEX text file to the monitor (replaces prior interpreter/game in RAM), then `EXAMINE 0200 0219`, `EXAMINE 0300 0307`, `EXAMINE 0E00 0E0F`, and `RUN 0000`. Expected picture: **four hollow 8x8 squares**, no alternating garbage. If still garbage, prioritize ELF interpreter's display ISR, DMA pointer setup, memory load correctness and VIDEO ON/interrupt assumptions. If squares render, focus on game-specific ETI input/graphics and operation.
- No ROM changes or hardware re-jumpering until we understand this isolation test. Keep F30A cassette baseline.
