> **2026-10-18 CRITICAL CORRECTION AFTER BENCH FAILURE:** The first 1979 reconstructed test displayed repeating garbage. Comparison to the *original printed Table 2* exposed a transcription mistake **$0100 recorded as $0010** (the source table says `0100 00 00 00 00 F8 01 B5 F8`). The faulty image overwrote the interpreter initialization and could not constitute a valid Netronics compatibility test. Fixed the authoritative `sw/chip8-historical/patches.txt`, corrected both RAM Intel HEX test images, and added regression assertions to `rebuild_from_hex_sources.py` checking `$0010–$0017=B4 F8 1B A4 F8 01 B5 F8` and `$0100–$0107=00 00 00 00 F8 01 B5 F8`. Rebuilt independently from the base source and patch tables; corrected 16-bit byte sums: **Four-Squares 0D74**, **Maze 07F7**. SHA256 **Four-Squares** `1f4ab52bb8dfe726ca77b1b3d12a0707bc44b57d676244473c2c99f5545d6737`; **Maze** `d7fec6517a7f063b3b455f4761c2eaa96e518d9fcd98c642fb08b317d1318587`. Difference from failed images is exactly **8 bytes**. Earlier images are **superseded**. Next bench test: load corrected Four-Squares HEX, verify both corrected regions with `EXAMINE`, then `RUN 0000`; Maze only after success. No firmware or hardware change. The early ELF-only interpreter test failures are a separate investigation; this correction accounts specifically for the Netronics 1979 tests.

---

> **2026-10-18 UPDATE — source-level milestone complete:** Both originally scanned *Ipso Facto* #11 and #12 were uploaded by the owner and inspected page-by-page. The Tables 1/2 changes have been **transcribed directly from the page images** and applied to verified RCA VIP base images in the independent `sw/chip8-historical/` directory. Two complete 3584-byte Intel HEX **RAM** images (Four-Squares and Maze) have passed structural/checksum tests and are ready for a **first owner hardware test**. This is not yet a ROM-resident interpreter and has not yet produced a proven display on ELF II hardware. The AVI firmware and cassette baseline have NOT changed.

# Netronics ELF II CHIP-8 ROM Integration — historical-source reconstruction

Status: **research and architecture approved; NO CHIP-8 ROM firmware released**.
Project base: `feature/avi-netronics-compatible-rom`, separately continued on branch `feature/netronics-chip8-1979`.
Preserve known-good cassette firmware and Giant Monitor bytes.

## Historical foundation — primary sources

- M. E. Franklin and Lynn Clock, **“To VIP an ELF, Games and Video Manipulation from RCA,”** *Ipso Facto* #11, April 1979, pp. 35–38: https://www.cosmacelf.com/publications/newsletters/ipso-facto/ipso-facto-11.pdf
  - Netronics ELF II-compatible changes to RCA VIP operating-system and CHIP-8 interpreter (Tables 1–3).
  - Franklin expressly states that he applied the changes to his Netronics ELF II successfully.
  - Video ON: **INP 1** ($69); video OFF: **OUT 1** ($61).
  - Hex input: **INP 4** ($6C), with physical INPUT-switch status **EF4**.
  - On original hardware, CHIP-8 game key commands require the INPUT switch, sometimes continuously.
  - Original scheme: a 4 KiB memory system; software arrangements at low RAM, including OS routines in the $0Cxx–$0Dxx region; CHIP-8 starts around $0000 and games ordinarily at $0200.
  - Article gives monitor choice: M($0002) = $00 for VIP OS or $10 for CHIP-8 in its particular arrangement.
  - Original VIP cassette I/O removed/replaced by existing machine facilities.
- M. E. Franklin, **“To VIP an ELF, Part II,”** *Ipso Facto* #12, June 1979, p. 55: https://www.cosmacelf.com/publications/newsletters/ipso-facto/ipso-facto-12.pdf
  - **Erratum:** byte M($01FA) is **$9B**, not **$93**. This applies to reconstructed Netronics CHIP-8 version.
  - Separate TEC video-on table correction (not Netronics).
  - Different keyboard arrangements explain controls differences between VIP, Netronics, TEC, Quest.
- Dave Taylor, **“More on How to VIP an ELF,”** *Ipso Facto* #17, p. 40: https://www.cosmacelf.com/publications/newsletters/ipso-facto/ipso-facto-17.pdf
  - Reports additional real-ELF graphics/game experiments; supports that multiple port variants existed.
- Dave Taylor, **“To 'VIP' an ELF,”** *Ipso Facto* #18, p. 27: https://www.cosmacelf.com/publications/newsletters/ipso-facto/ipso-facto-18.pdf
  - Alternative relocated VIP system and port-1/keyboard integration. Treat as separate variant, not an erratum to Franklin.

**Source-quality caveat:** Searchable copies of #11/12 include OCR ambiguities in original hex listing (e.g., character O/0, B/8, and underlined page bytes). We must compare EVERY table byte against the page images before treating the listing as authentic. At this milestone, Tables 1–3 have **not** been byte-for-byte verified from the scans; do not generate ROM or claim a restored binary yet.

## What is already proven on the target hardware

- CDP1861 video/interrupt operation: original 1977 Enterprise image works through the existing monitor `TEST PIXIE`.
- Netronics Giant Monitor and authentic Tiny BASIC cassette I/O: proven SAVE / LOAD / execute round-trip using the F30A cassette firmware.
- Low-RAM CHIP-8 ELF and Maze/VIP interpreter experiments: compiled/loaded but failed to produce stable displays; alternating scrambled/white blocks. Not a proof of CPU or CDP1861 failure.
- Maze combo image uses R1 = $8146 as a presumed VIP ROM video interrupt entry; this points into **our monitor**, which makes it incompatible as-is.
- Original ELF interpreter found in Emma 02 `data/Elf/chip8.hex` has its own RAM ISR at $0E46, but still did not display correctly on current Hyperboard.
- The owner's Airplane program is the ETI-660 CH8 variant loaded at $0600. **Do not make Airplane the initial acceptance gate**: ETI 660 video/layout may differ from classic VIP/ELF CHIP-8.

## Architecture decision

Use the **Netronics-specific historical adaptation** as the baseline behavior, not a generic VIP interpreter.

The first ROM integration can **store the interpreter/OS image in ROM and copy it into the historical RAM layout** before executing it. This avoids a risky initial relocation of 1802 code that uses absolute page addresses, RAM state and DMA; the executable is ROM-distributed even if runtime is in RAM. It leaves normal `$8000–$FFFF` ROM monitor code in place.

Proposed monitor entry (only after verified binaries and tests):
```
CHIP8          ; copy historical Netronics interpreter runtime to low RAM; start default game at 0200
CHIP8 0200     ; conventional CHIP-8 program
CHIP8 0600     ; alternate load address; conditional on interpreter compatibility
```
Exact syntax, graphics buffer placement and RAM footprint must be verified from the transcribed program before coding; default choice should not overwrite user programs silently.

Machine-level requirements:
1. Properly initialize 1802 registers including P/X, R0 DMA, R1 interrupt entry, and runtime stack; honor ELF II's original video ON/OFF I/O at port 1.
2. Keyboard driver accepts front-panel hex code on INP4 and detects INPUT via EF4; **COM1 is ALSO on EF4 in Pete's monitor**, so suspend COM1 reception while CHIP-8 is active. Do not assume a physical key press alone activates input without the INPUT switch.
3. Do not transmit COM1 text during CDP1861 video DMA; prior tests already revealed serial disruption during video.
4. Preserve original Giant Board $F000–$F0FF and separately hardware-verified cassette services.
5. Don't move physical jumpers under power; keep the normal monitor reset/recovery path.

## Build and hardware acceptance sequence

1. Recover **exact** 1979 Tables 1–3 into source with per-byte provenance and Issue 12 $01FA correction. Keep OCR-ambiguous bytes unresolved until verified against page images.
2. Generate a standalone reproducible low-RAM **historical Netronics test HEX** (no ROM modification), including a simple static CHIP-8 graphics test and the minimal interpreter/OS code.
3. Bench test with Sony CRT, actual ELF II keyboard/INPUT button; verify recognizable static image, DMA/interrupt stability, and keys.
4. Place authenticated interpreter image and ROM launcher into existing unused ROM region; validate ROM layout/checksum and preserve fallback cassette image.
5. Only then test Maze ($0200) and Airplane ($0600), with variant checks; document both on-hardware results.

**Current blocker resolved:** uploaded issue #11/#12 scans were inspected. **Next blocker:** actual hardware validation of the full source-reconstructed Netronics test images, including CDP1861 DMA/interrupt and EF4 keypad interaction. ROM integration remains pending.


## 2026-10-18 binary/source provenance and test artifacts

- Base RCA VIP ROM: Emma 02 `data/Vip/vip.rom`, 512 bytes, SHA256 `9df7ea9e055b5e4c5a1429bf24c1cb318ef4052977453285424e11ca76b40987`.
- Base RCA VIP CHIP-8: Emma 02 `data/Vip/chip8.ram`, 512 bytes, SHA256 `699ad707fd9756c10a31c7abbd03b95e28ae04112bd097ab72a62493d358271b`.
- Owner Maze original first $200 bytes match the archived VIP CHIP-8 image exactly; Maze program remains at $0200–$0221.
- `sw/chip8-historical/patches.txt` transcribes **232 OS bytes** (Table 1) and **112 CHIP-8 bytes** (Table 2), with `MODE=10` for CHIP-8 startup and Issue 12's $01FA = $9B correction applied; OS map $0C00–$0DFF.
- `Netronics-1979-CHIP8-Four-Squares.hex`: **3584 bytes $0000–$0DFF**, standalone RAM image, SHA256 of full image `fad5c4c94c5ab06729a4839fa3ec9c6bdee989e8a4cf3f6fd4b5886702b40c76`.
- `Netronics-1979-CHIP8-Maze.hex`: same range, standalone RAM image, SHA256 `64413915199de49f89d798a2aa6f0f1aa44945b315fe971f7f702643ba3d5c35`.
- Both images were independently generated twice with matching 16-bit byte sums `09E3` and `0466`; each Intel HEX record verified. Full Python reproducible build and user-supplied original Maze included in owner's test ZIP, whose link is present in the project conversation.
- Hardware acceptance: send Four-Squares HEX to 2400 8N1 monitor → `EXAMINE 0000 0002` expects `C0 0C 10` → `EXAMINE 01F8 01FF` expects `06 30 9B 00 00 E0 00 4B` → `RUN 0000`. Expect four outlined sprites on CDP1861. Only if stable, reset, load Maze HEX and `RUN 0000`. Do NOT program these RAM HEX files into a 32K ROM.
