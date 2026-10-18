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

**Current blocker:** accurately obtain/review listing scan pages with Tables 1–3 before compiling a purported historical interpreter.
