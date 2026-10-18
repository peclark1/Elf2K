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