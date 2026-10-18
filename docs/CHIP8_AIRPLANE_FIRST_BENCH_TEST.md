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


## 2026-10-18: Owner-supplied Chip8_Maze (1).hex review

The owner supplied a separate Intel HEX image named `Chip8_Maze (1).hex` for comparison. Verified all Intel HEX checksums; **546 data bytes** occupy exactly `$0000-$0221`:

- `$0000-$01FF`: an embedded **RCA COSMAC VIP-style CHIP-8 interpreter** (native 1802 machine code and CHIP-8 startup bytes).
- `$01FC-$01FF`: CHIP-8 startup `00 E0 00 4B` (clear screen, machine-specific SYS call).
- `$0200-$0221`: 34-byte Maze demonstration program and sprite bytes.
- **No memory records at $0E00 or above**, unlike Emma 02's `data/Elf/chip8.hex`, which includes its own $0E00-$0E6F video/ISR support.

**Critical machine dependency:** the Maze interpreter's bytes `F8 81 B1 F8 46 A1` at `$0009-$000E` load **R1=$8146** (1802 interrupt PC), expecting COSMAC VIP ROM interrupt code at that address. On our AVI ELF II, ROM `$8000-$FFFF` instead contains **Pete's ELF II Monitor**, not the RCA VIP ROM, so $8146 is an invalid video-ISR target. Do not try `RUN 0000` on this image as if it were hardware-independent.

For comparison, the ELF-specific CHIP-8 interpreter in Emma 02 `data/Elf/chip8.hex` begins `F8 0E B1 F8 46 A1`, loading **R1=$0E46**, and includes support code in RAM $0E00-$0E6F. This is why the earlier ELF interpreter was chosen; however, the owner has reported the same alternating garbled display even with a trivial PIXIE graphics test, so that version's **video/DMA setup still requires investigation on physical Hyperboard hardware**. The Maze image is valuable as a comparison and diagnostic, **not** evidence that the original interpreter can simply be loaded intact.

Next work: examine the ELF-specific ISR at $0E46 and initialization details against the proven monitor `TEST PIXIE` CDP1861 video paths. Keep cassette and ROM unchanged until an isolated 1802 DMA/framebuffer test establishes correct video setup.


## Historical Netronics ELF II CHIP-8 port identified (1979)

**Critical discovery:** *Ipso Facto*, Issue 11 (April 1979), “To VIP an ELF” (M. E. Franklin) documents a **Netronics ELF II-specific adaptation** of RCA's VIP operating system and CHIP-8 interpreter. Its tables 1 and 2 provide the Netronics changes; the author reports successful operation on a physical Netronics ELF II. Issue 12 (June 1979), “To VIP an ELF, Part II,” corrects two errata and discusses keypad differences. These are **period hobbyist adaptations**, not evidence that Netronics officially shipped a CHIP-8 ROM.

- Primary scans: https://www.cosmacelf.com/publications/newsletters/ipso-facto/ipso-facto-11.pdf and https://www.cosmacelf.com/publications/newsletters/ipso-facto/ipso-facto-12.pdf . Contents index: https://www.cosmacelf.com/publications/newsletters/ipso-facto/1979---ipso-facto-10-to-14.html .
- Specific interface table in Issue 11: Netronics 1861 VIDEO ON uses **INP1 ($69)**, VIDEO OFF uses **OUT1 ($61)**; hex keypad uses **INP4 ($6C)** and INPUT switch status **EF4**. Original VIP used a scanned keypad, so its keyboard routines required adaptation. On the period ELF II implementation, the IN button must be used for game key commands. **Our COM1 currently uses EF4**, which must be reconciled for games; avoid claiming real-time keyboard is already solved.
- Its period program occupies **4 KiB RAM** and the article describes a possible compact 2 KiB relocation. A ROM port should not assume the original code is position-independent or that buffer/stack/variables can live in ROM. The ROM must provide a stable display interrupt ISR and keyboard interface, with writable CHIP-8 state and framebuffer in RAM.
- Independent contemporary corroboration: the later ELF II owner report “To 'VIP' an ELF” in *Ipso Facto* Issue 18, accessible via https://manualzilla.com/doc/5798792/ipso-facto-issue-18 , notes relocating the operating system and adapting CHIP-8 for the Giant Board's I/O.
- Alternate ELF port: Paul C. Moews, *Programs for the COSMAC ELF: Interpreters* (1979), covered full CHIP-8 interpreter versions for the basic/expanded COSMAC ELF, including added instructions. See https://github.com/trapexit/chip-8_documentation and https://chip-8.github.io/extensions/ . The preexisting ELF interpreter we loaded at $0000/$0E00 is NOT the same as a verified Netronics ELF II implementation.

### Planned ROM integration architecture (not yet assembled)

1. Reconstruct and verify the **period Netronics-specific** CHIP-8 patches from Issue 11 (and Issue 12 corrections); compare against the currently available ELF interpreter binaries. Preserve source provenance and identify undocumented/ambiguous bytes instead of inferring them.
2. Use an opt-in **`CHIP8 [addr]`** monitor launcher: start normal monitor first, copy/initialize the appropriate interpreter state in RAM, install the interpreter's own 1861 ISR, and disable monitor serial during video. Provide reset-to-COM1 recovery.
3. Use ROM expansion area after our cassette module (latest image nominal **$C5E8-$EFFF**) for executable interpreter code and fonts/diagnostics, but keep framebuffer, CHIP-8 registers, call stack and dynamically generated state in RAM; be mindful of direct jumps and ROM PC register semantics.
4. Hardware-validate fixed graphics and original **64×32** CHIP-8 first, including the physical HEX keypad and EF4/COM1 conflict. Only then test the ETI-660 Airplane game at **$0600**, which originated on a **64×48** ETI-660 platform and may require distinct video compatibility work.
5. No ROM firmware modification until the historical tables have been transcribed and ROM/RAM mapping, ISR and keyboard semantics are defined. Continue to preserve the proven cassette baseline.
