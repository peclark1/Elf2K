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


## 2026-10-18: Video evidence of repeating garbage/white framebuffer

Owner provided 10.9-second mobile video `IMG_9979.MOV` of a CHIP-8 test on original Netronics ELF II and Panasonic CRT. Frame-by-frame inspection: image repeatedly cycles between **filled pale/white 64x32-looking display rectangle** (at times with a thin horizontal band of scrambled pixels) and a **dense patterned/noisy rectangle**. Position and overall scan geometry remain largely stable; this does **not** resemble a conventional rolling/unsynchronized TV picture. None of the expected four outlined sprites is recognizable. Exact pixel contents vary during the recording. Owner characterized it as “like it's in a loop.”

This **proves the visual output is unstable**, but does not by itself prove whether the source is a bad IRQ entry R1, failure to reinitialize R0 DMA each frame, erroneous video framebuffer memory writes, another assembly/image problem, or the actual deployed HEX file. Prior `TEST PIXIE` runs on this hardware were successful; do not revert to hardware/clock troubleshooting without isolating software behavior.

**Next targeted distinction:** After completing a run of the Four-Squares test and returning to monitor with normal RESET, examine video framebuffer around **`$0B00-$0B5F`** (especially `$0B20-$0B5F`). Table 3 of *Ipso Facto* #11 designates `$0B00-$0BFF` as framebuffer and R0 as DMA pointer. For 64x32 one-byte-per-8-horizontal-pixels sprites at (8,4) and (40,4), top row bytes should begin `$0B21=FF` and `$0B25=FF`, next row `$0B29=81`, `$0B2D=81`; other space mostly 00. If RAM buffer has these patterns but TV shows mostly full white, prioritize R0/IRQ/DMA. If RAM is overwritten/FF/garbage, look at interpreter/OS graphics and state management before tracing DMA. Monitor reset behavior must preserve RAM to make this conclusive. Also verify corrected binary is used and check `$0010-$0017`, `$0100-$0107`.

Keep ROM and hardware unchanged for this narrow diagnostic.


## 2026-10-18 hardware proof: CHIP-8 draw engine works; video output remains unstable

After running the **corrected** 1979 Four-Squares test, the owner RESET to the AVI monitor without power loss and ran `EXAMINE 0B20 0B3F`. **Observed exactly**:

```
0B20 00 FF 00 00 00 FF 00 00 00 81 00 00 00 81 00 00
0B30 00 81 00 00 00 81 00 00 00 81 00 00 00 81 00 00
```

These are the **precise expected pixel bytes** from the four-square CHIP-8 test, as predicted before inspection. This proves CHIP-8 instruction dispatch, the test program's drawing operations, RAM persistence, and at least this portion of the graphics framebuffer at **$0B00–$0BFF** all work on real hardware. The continuing alternating white/garbage CRT display is therefore **not caused by incorrect pixels in these rows of RAM**. It does not yet establish that all 256 framebuffer bytes are good or that the interpreter's video ISR is correct.

**Important comparator:** the previously proven AVI ROM `TEST PIXIE` uses the carefully cycle-timed **`INT1PG`** handler in `sw/boots.asm`, which starts with an explicit `NOP` to correct interrupt-ACK timing, saves T/D, reloads **R0** with the image pointer, repeats DMA lines four times and branches on EF1. The historical CHIP-8 variant's R1 target **$0D46** has a different ISR prologue in the relocated VIP OS image. Because the video is stable with the existing monitor routine, **prioritize replacing/isolating the historical ISR with a timing-compatible variant of this known-working routine**, while retaining the untouched CHIP-8 instruction engine and framebuffer at $0B00. Avoid further ad-hoc modifications to hardware or game files. In particular, monitor `TEST PIXIE` ISR directly uses a monitor-defined pointer register, and **cannot be dropped in wholesale** without adapting that register usage to the CHIP-8 runtime. A standalone RAM experiment should install a purpose-built display handler and preserve the CHIP-8 1802 register contract.

**Next bench acceptance:** existing corrected Four-Squares image + one controlled ISR-only alteration. Four squares must become stable on TV. Then test Maze; do not integrate interpreter into ROM before passing.


## 2026-10-18 revised diagnosis: test sprite / period OS stack overlap

Examining *Ipso Facto* #11 printed **page 38**, Table 3, after the owner's successful framebuffer dump reveals a second potentially important problem **in our diagnostic program itself**:

- The period CHIP-8 memory map assigns `$0B00-$0BFF` to refresh display and identifies `$0BAC-$0BFF` as an **84-byte operating-system stack area** (the overlap occurs at the bottom of the video page). It is not yet established whether that stack is actively used in CHIP-8 rather than VIP OS mode; do **not** treat this as proven root cause.
- The initial Four-Squares program deliberately placed two squares at Y=$14 (20). Their 8-pixel heights span scanlines 20..27; from the second row onward their output enters `$0BA8-$0BDF`, including `$0BAC-$0BFF`.
- The user's successful `EXAMINE 0B20 0B3F` dump corresponds to the top pair at Y=$04, outside the overlapping stack. It does not prove bottom squares were safe.
- **New controlled test:** change just one byte of CHIP-8 program from **`$0211: 14 -> 0C`**, moving the lower squares to Y=$0C (12). Now their 8 scanlines occupy only framebuffer rows 12..19 (ending $0B9F), below stack overlap. No other interpreter/ISR bytes change. This can be done in RAM from monitor with `DEPOSIT 0211 0C`, `EXAMINE 020E 0213` expecting `60 08 61 0C D0 18`, then `RUN 0000`.
- This test is also preserved in `sw/chip8-historical/Netronics-1979-CHIP8-Four-Squares-STACK-SAFE.hex` (3584B Intel HEX, valid record checksums, whole-image 16-bit byte sum `0D6C`). Same historical 1979 interpreter as the corrected prior image; not a ROM firmware change.
- If stable now, explore memory overlap and OS/runtime register usage; if **still white/garbage**, refocus on 1861 interrupt/DMA timing, using proven `TEST PIXIE` ISR, rather than repeatedly changing CHIP-8 drawing routines.


## 2026-10-18: Stack-safe sprites still show garbage; isolated video ISR test

Owner loaded the stack-safe Four-Squares variant and confirmed `EXAMINE 0210` shows **`61 0C`**, then `RUN 0000` produced **the same alternating white and garbage** on the CRT. This **eliminates the specific test-sprite/OS-stack overlap hypothesis** as an explanation for this video symptom.

A new isolated RAM test is prepared. Unlike earlier guessing at CHIP-8 draw routines, this changes only the display ISR and its R1 startup vector while keeping the 1979 interpreter, the game at $0200 and the graphic buffer at $0B00 unchanged.

- `sw/chip8-historical/Netronics-1979-CHIP8-Four-Squares-PIXIE-ISR-TEST.hex`: full 3616-byte Intel HEX image ($0000–$0E1F).
- `sw/chip8-historical/Netronics-1979-CHIP8-PIXIE-ISR-PATCH-ONLY.hex`: **five Intel HEX lines** that overlay an already loaded **STACK-SAFE** image after monitor reset. Patches exactly two existing bytes and installs 29 bytes of ISR code.
- Changes to old code: `$0C9E: 0D → 0E`, `$0CA1: 46 → 02`; R1 video interrupt PC is now **$0E02**, rather than $0D46.
- New code at $0E00–$0E1C is derived instruction-by-instruction from the **proven `TEST PIXIE` interrupt/DMA skeleton** in `sw/boots.asm`. It places the `LDXA; RET` return sequence at $0E00–$0E01, so after each interrupt R1 automatically points back to ISR start at $0E02. It begins with NOP to match the monitor's interrupt acknowledgement timing, saves T/D on R2 stack, reloads R0 from video page **RB high=0B / low=00**, and uses the same cycle-timed fourfold horizontal DMA-line repeats while EF1 is asserted.
- The patch **does not run the original CHIP-8 timing/sound tick logic or increment its RNG**. It is **diagnostic only**; do not use it with Airplane or Maze, which depend on timers/random. It should only run our static Four-Squares.
- Expected `EXAMINE 0C9D 0CA2`: `F8 0E B1 F8 02 A1`.
- Expected `EXAMINE 0E00 0E1C`: `72 70 C4 22 78 22 52 9B B0 F8 00 A0 C4 C4 E2 80 E2 20 A0 E2 20 A0 E2 20 A0 3C 0E 30 00`.
- After `RUN 0000`, four hollow 8x8 squares should display if interrupt-acknowledge/cycle-timing difference caused the corruption. This is **not hardware-validated**. No firmware or hardware configuration changes.
- If still no stable video, obtain the full frame buffer ($0B00–$0BFF) and inspect display IRQ/DMA path with analyzer. The sprite execution is already hardware-verified by the owner's $0B20–$0B3F framebuffer dump.

Note on proof levels: successful CHIP-8 draw RAM tests, failed video, and this new untested ISR test are separate milestones. The existing 1C62/F30A monitor cassette images are unaffected.


## 2026-10-18: Hardware ISR substitution yields blank display

The owner reports that following the isolated RAM ISR overlay (published as `Netronics-1979-CHIP8-PIXIE-ISR-PATCH-ONLY.hex`) and `RUN 0000`, **the Panasonic CRT remains black/blank**, rather than alternating white and patterned garbage as before. The stack-safe sprite adjustment had not changed the white/garbage symptom; this ISR patch did change it.

**Do not describe this as a successful video timing fix.** This is a second failed video-output experiment and shows that the ISR path matters, not whether a particular suspected failure mechanism is proven. The ad-hoc ISR is not byte-for-byte the working monitor ISR and omits CHIP-8 frame/sound/timer bookkeeping; it cannot be considered a finished/verified substitute.

Next bench verification before additional patches:
1. Reset into monitor without power-off.
2. `EXAMINE 0C9C 0CA3`; expected `A2 F8 0E B1 F8 02 A1 F8`. Confirms R1 handler address $0E02.
3. `EXAMINE 0E00 0E1F`; expected `72 70 C4 22 78 22 52 9B B0 F8 00 A0 C4 C4 E2 80 E2 20 A0 E2 20 A0 E2 20 A0 3C 0E 30 00 FF FF FF` if just overlay patch was loaded on uninitialized $0E1D–$0E1F those final bytes may be non-FF; only **$0E00–$0E1C** must match.
4. `EXAMINE 0B20 0B3F` to see whether the previously verified four-square pixel patterns survive the ISR experiment.

If vector or code differs, focus on HEX loading/resident RAM. If code matches and buffer remains correct, prioritize **a vetted independent 1802 CDP1861 ISR/frame timing validation** and investigate I/O port-1 VIDEO ON and interrupt-enable state, rather than changing graphics or reprogramming ROM. Continue preserving 1C62/F30A cassette firmware. Hardware oscillator/CRT are not implicated by these tests because `TEST PIXIE` previously worked on the same setup.


## 2026-10-18: Fresh full-image ISR test versus patch-only test

**Owner result:** after running the 29-byte ISR **patch-only** over already-executed CHIP-8 RAM, CRT was completely black and framebuffer $0B20–$0B3F was all zero; vector/handler bytes verified exactly. Then owner loaded **the full** `Netronics-1979-CHIP8-Four-Squares-PIXIE-ISR-TEST.hex` and CRT returned to the **alternating white/patterned-garbage display**.

Checked the actual archived two hex files: the full image does contain both exactly the same IRQ vector **R1=$0E02** and the same 29-byte new handler at $0E00–$0E1C as the patch-only image. The difference is that the full HEX restores all 3584 bytes of interpreter, OS, CHIP-8 test program, RAM working state, and zeroed initial framebuffer, while patch-only restores only two vector bytes and 29 ISR bytes.

**Interpretation:** the earlier patch-only black screen is **not a meaningful fresh-start validation** of the handler. Low-RAM CHIP-8 interpreter state has been mutated by prior execution; patch-only does not reset it. The full-image test must be treated as the valid ISR experiment. This result **does not confirm the modified handler fixes DMA**; apparently it does not produce four stable squares.

**Next smallest useful bench distinction:** after running the full ISR-test HEX and returning to monitor without power-off, `EXAMINE 0B20 0B3F` again. If those pixels match `00 FF .. FF` / `00 81 .. 81`, drawing works while the **new handler** fails to render (check EF1 interrupt timing and whole framebuffer). If pixels are zero/garbage despite full-image load, pursue startup/IRQ register/state corruption before refining the DMA timing. Full HEX and patch-only must only be compared from identical freshly loaded baseline images. No new ROM patch/firmware change performed.


## 2026-10-18: Hardware framebuffer proves CHIP-8 drawing; monitor RUN has interrupts DISABLED

The owner ran the **full experimental PIXIE-ISR HEX** from a fresh Intel HEX load (not the stale patch-only test). CRT remained alternating white/garbage. After returning to monitor without removing power, `EXAMINE 0B20 0B3F` reported exactly:
```
0B20  00 FF 00 00 00 FF 00 00 00 81 00 00 00 81 00 00
0B30  00 81 00 00 00 81 00 00 00 81 00 00 00 81 00 00
```
**CHIP-8 drew correct pixels even with replacement ISR**. No stable displayed picture is yet verified.

### Critical root-cause candidate: 1802 IE flag
Auditing source in `sw/boots.asm` / `sw/boots.inc` reveals:
- Boot `SYSINI` explicitly issues `DIS` (1802 interrupt-disable), sets X=P=0.
- Monitor `RUNUSR` → `RUN2` sets R1 to TRAP, then `SEX 0 ; SEP 0`. **It never executes `RET`/INT_ON to re-enable interrupts.**
- Proven `TEST PIXIE` explicitly invokes `INT_ON` (macro `SEX PC ; RET ; .DB (SP<<4)|PC`) **before `PIXIE_ON`**.
- The 1979 historical CHIP-8 system was designed for a front-panel restart with interrupts enabled; it relies on R1 as the CDP1861 ISR PC. The monitor launching CHIP-8 with IE=0 could leave video enabled but R0 DMA **unrefreshed each frame**, explaining alternating white/random screen even though the graphics buffer is correct.

### Control test: enable interrupts before entering historical CHIP-8
New complete full-load HEX file `sw/chip8-historical/Netronics-1979-CHIP8-Four-Squares-INTERRUPTS-ON.hex`:
- Is **byte-for-byte identical** to the last stack-safe 1979 Netronics image throughout `$0000-$0DFF`, using **original period handler at $0D46** and game at $0200; not the temporary $0E02 experimental ISR.
- Adds only **six native CDP1802 bytes** at free RAM `$0E80-$0E85`: `E0 70 00 C0 0C 10`.
- Start **`RUN 0E80`**, **not** `RUN 0000`. Native code: `SEX R0` (X=0); `RET` reads inline `00` (X=P=0, IE=1) and advances R0 to $0E83; `LBR $0C10` enters original 1979 Netronics startup normally.
- The ROM monitor's `RUN` operation initializes X=P=0, as required by this bootstrap. Following the `RET`, 1802 interrupts are enabled and historical CHIP-8 can service the CDP1861 correctly at R1=$0D46.
- Before run, `EXAMINE 0E80 0E85` should show `E0 70 00 C0 0C 10`.
- **NOT hardware tested yet**. Complete file includes 3590 data bytes and all Intel HEX checksums pass. SHA256 of the full Intel HEX text `e4471c7152f04c33e87b2e324abf2fdb88310b109b1a5966b3a64b15168428bd`.

### Explicit correction to an abandoned interpretation
A proposed experimental DMA loop fix `$0E1A: 0E→0D` was **withdrawn after checking precise byte addresses**. In the experimental ISR, **`$0E0E=E2 (SEX R2)`** and `$0E19=3C $0E1A=0E` correctly branches to that instruction. The 1979 ISR uses different timing code; the copied test does not have the initially alleged one-byte branch error. The incorrectly modified loop-fix HEX was deleted from the branch before being offered as a test. The true significant difference is the **interrupt-enable state on entry**, still pending bench validation.

If the new full-load IE-enabled test still fails, next isolate **RAM-based CDP1861 DMA** versus the previously validated ROM-based `TEST PIXIE` using a purpose-built native 1802 RAM framebuffer viewer. Do not change hardware/jumpers or the cassette ROM for this check.


## 2026-10-19: MAJOR BENCH PASS — period Netronics CHIP-8 video stable with IE enabled

**HARDWARE-VERIFIED SUCCESS**: Owner tested the full `Netronics-1979-CHIP8-Four-Squares-INTERRUPTS-ON.hex` on his original Netronics ELF II + AVI Hyperboard + Panasonic CRT; ran **`RUN 0E80`** instead of `RUN 0000`. Owner supplied photograph demonstrating **stable correctly rendered four-square CHIP-8 graphics** (two columns, with vertically adjacent top and lower squares; this adjacency is expected after moving the lower squares to Y=$0C). The previously persistent white/garbage cycling disappeared.

This is strong hardware evidence that **disabled CPU interrupts at monitor `RUN` entry** were the primary blocker for the historical CHIP-8 video experiment. Prior CRT/clock, drawing instructions and framebuffer were working. The six-byte RAM bootstrap `$0E80: E0 70 00 C0 0C 10` uses `SEX R0; RET` to set X=P=0 **and IE=1**, then `LBR $0C10` into 1979 startup. The historical Netronics $0D46 ISR and normal video DMA now work; no ROM rewrite or hardware modifications.

**Verified**: rendering/graphics dispatch, IRQ enable bootstrap, interrupt-synchronized CDP1861 graphics on real hardware. **Not verified yet**: keypad input, timers/beep, full Maze game, ETI-660 Airplane compatibility, or ROM-resident `CHIP8` monitor command. Do NOT promote them to complete.

Next test artifact: `sw/chip8-historical/Netronics-1979-CHIP8-Maze-INTERRUPTS-ON.hex` (complete image), same interpreter/OS and same six-byte bootstrap as proven Four-Squares, with original Maze at $0200. Upload entire Intel HEX, `EXAMINE 0E80 0E85` expected `E0 70 00 C0 0C 10`, run **`RUN 0E80`**. No ROM programming required.

ROM design implication: eventual built-in monitor `CHIP8` launcher MUST explicitly enable 1802 interrupts when handing off to historical interpreter and provide correct R1 ISR / R0 DMA initialization. A mere `RUN 0000` jump from a monitor with IE=0 is not sufficient.
