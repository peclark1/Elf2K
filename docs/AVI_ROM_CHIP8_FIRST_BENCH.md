# 1979 Netronics CHIP-8 — AVI ELF II ROM first bench plan

Status: **Software build and byte-for-byte verification PASS; ROM command integration NOT yet tested on hardware.** This is a reversible experiment on a new draft PR. Do not merge or overwrite the retained hardware-verified 1C62/F30A OneROM backup.

## History and compatibility

The 1979 `Ipso Facto` #11–12 Netronics ELF II interpreter and original relocated VIP OS/PIXIE ISR work on the owner's physical original Netronics ELF II, AVI Hyperboard and Panasonic CRT. The owner demonstrated FOUR (photo) and Maze with a complete RAM image and **`RUN 0E80`**. The root cause of the earlier white/garbage screen: the monitor's `RUN` leaves 1802 interrupts disabled, so the period video ISR never runs until our **six-byte RAM trampoline `E0 70 00 C0 0C 10` at $0E80** sets IE=1 and branches into the old $0C10 startup.

Airplane is an ETI-660 64×48 game and is **not** a compatibility target for this 64×32 Netronics system. Key scanning and timer/sound behavior of more advanced games are not yet hardware verified.

## ROM layout and unchanged services

- CPU $D000–$D0E6: new AVICHIP8 command, copy/clear helper and startup handoff.
- CPU $D800–$D9FF: exact historical 512-byte CHIP-8 interpreter core (RAM $0000–$01FF).
- CPU $DA00–$DBFF: exact historical 512-byte VIP/Netronics OS (RAM $0C00–$0DFF), including IRQ $0D46.
- CPU $DC00–$DC19: FOUR game code at RAM $0200–$0219.
- CPU $DC1A–$DC21: FOUR sprite at RAM $0300–$0307.
- CPU $DC22–$DC43: Maze code/data at RAM $0200–$0221.
- CPU $DC44–$DC49: six-byte interrupt-enable bootstrap (RAM $0E80–$0E85).
- CPU $DD00–$EFFF remains reserved/FF. CPU $F000–$F0FF original Giant ROM unchanged; CPU $C200–$CFFF cassette service unchanged; BIOS at $F300+ unchanged.

Before launch, the ROM command copies the period RAM code above, clears the CHIP-8 video/scratch area $0A00–$0BFF, and **preserves $0200–$09FF** for user-supplied CHIP-8 programs. Finally sets R0=$0E80, X=0 and P=0 so the bootstrap enables interrupts. There is no monitor terminal when CDP1861 DMA is active. Reset without powering off to return to ROM.

## First-on-hardware procedure

1. **Preserve the owner's current EEPROM image**, already verified for CASSAVE/CASLOAD Tiny BASIC, monitor functions and COM2 9600/19200/38400. Program the new labelled `AVIElf2-Netronics-OneROM-CHIP8-EXPERIMENTAL.bin` into a **separate, reversible test OneROM/flash**, never into the only known-good copy. The paired HEX is for the ROM programmer, with physical address $0000 corresponding to CPU $8000.
2. Restart, confirm the normal monitor banner and HELP lists CHIP8. Check that COM2 still works at your tested clock/baud; no Hyperboard jumper changes are requested.
3. At the monitor, type **`CHIP8 FOUR`**. Expected result: the same stable, two-column four-squares pattern previously hardware-confirmed using `RUN 0E80`. No terminal characters while video runs.
4. Hardware RESET to regain the monitor; type **`CHIP8 MAZE`**. Expected: the same stable Maze pattern verified from the standalone full-RAM HEX.
5. Hardware RESET. Send **`CHIP8-FOUR-GAME-ONLY.hex`** using the existing Intel HEX loader (34 data bytes at $0200–$0219 and $0300–$0307). Then type **`CHIP8`** with no argument. Expect identical FOUR graphics; this tests the **preloaded program preserved in RAM** path. Optionally repeat with `CHIP8-MAZE-GAME-ONLY.hex` (34 bytes at $0200–$0221).
6. If one of these fails, capture the exact monitor output, whether video blank/garbled, and RAM `EXAMINE 0C9D 0CA2`, `EXAMINE 0E80 0E85`, `EXAMINE 0B20 0B3F` **after RESET, without power loss**, then return to the saved 1C62 firmware if desired.

## Software verification

The AVI GitHub Actions workflow performs two clean builds and byte-for-byte compares them. `sw/build/verify-avi.py` checks 32KiB ROM coverage, all intentional reserved/active ranges and checksum, original Giant ROM signature, serial and cassette monitor commands, new CHIP8 dispatch, and checks **all 1,098 ROM CHIP-8 payload bytes against the two independently archived hardware-verified full RAM images**. It does not claim the new ROM command has already run on actual hardware.

Build: `bash sw/build/build-avi.sh`; OneROM conversion: `python3 sw/build/prepare-one-rom.py .build/avi-rom/work/AVIElf2.hex .build/avi-rom/work`.

Keep this change as a draft until the user verifies **FOUR and Maze launched from ROM** and existing COM2/cassette commands have not regressed.


## 2026-10-19: Owner hardware success and historical games shortlist

After receiving the ROM-integrated test, owner reported **"works perfectly"**. This confirms successful real ELF II execution of the integrated ROM feature following the test guidance for `CHIP8 FOUR`/`CHIP8 MAZE`, not just standalone RAM execution. No report was provided yet verifying game keypad input, timer behavior, or regression testing of cassette modes following this flash; retain those as separate test statuses.

Three additional public-domain-era **original RCA COSMAC VIP / original 64x32 CHIP-8** game-only Intel HEX files were selected and source-preserved from the Emma 02 archive, committed under `sw/chip8-netronics/games/`:
- `CHIP8-KALEIDOSCOPE-1978.hex`: 128 bytes $0200-$027F, Joseph Weisbecker's original 1978 VIP Kaleidoscope. **First interactive keypad test**: press 2,4,6,8 to build a pattern, then press 0 to loop; historical example is 44444442220.
- `CHIP8-WIPE-OFF.hex`: 208 bytes $0200-$02CF, Joseph Weisbecker's Wipe Off. 4 and 6 control paddle; includes CHIP-8 FX0A wait-for-key.
- `CHIP8-BREAKOUT-1979.hex`: 240 bytes $0200-$02EF, Carmelo Cortez's 1979 Breakout. Variation of Wipe Off with six walls and 20 balls, paddle controlled by 4 and 6.

All records have valid Intel HEX checksums; none uses ETI-660 64x48 format or loads outside the monitor's preserved game memory range $0200-$09FF. **No hardware test yet** for these three programs. Test: send ONE game-only Intel HEX to monitor; command `CHIP8` (no arguments); hardware RESET to exit; next game can be loaded the same way. The normal `CHIP8` ROM command installs the resident 1979 Netronics interpreter/OS and enables 1802 IE while preserving loaded $0200-$09FF. Avoid `CHIP8 FOUR`/`CHIP8 MAZE` when launching a third-party game because those commands overwrite $0200 bytes with their bundled demos.

Source and documentation:
https://github.com/etxmato/emma_02/tree/master/data/Chip-8/Chip-8%20Games

This is the next **compatibility experiment**, with keypad and original EF4/INPUT mapping to verify before claiming full interactive game support.


## 2026-10-19: Breakout draws correctly but never responds to keys

Owner loaded historical 1979 Carmelo Cortez Breakout game-only HEX at $0200, then `CHIP8`. The **brick field and paddle draw correctly and remain stable**, but the paddle never moves, and **no hex-key presses alone or combined with physical INPUT**, including holds/repetitions, have any visible effect. Other original VIP games (Kaleidoscope and Wipe Off) to be tested by owner. This does **not** prove keypad input works; the ROM graphics execution path is definitely working.

### Exact 1979 Netronics keyboard evidence and diagnostic decision tree

Period *Ipso Facto* #11 p36 documents Netronics 1979 CHIP-8 keyboard as **HEX pad input port $6C = 1802 `INP 4`**, and INPUT switch on **EF4**. The actual archived period OS contains `INP 4` opcodes at RAM `$0CDC`, `$0CF3`, and `$0D9E`, with `BN4` tests around $0CD1/$0CE9. This code has **not** been adapted for AVI Hyperboard port wiring. It was copied byte-identically from the successful, graphics-only Netronics RAM image.

Review of the actual AVI Hyperboard Rev2 schematic shows **J15 selecting COM1 Q/serial EF input lines including EF4**, even if software console is changed to COM2. Serial receive wiring shared with EF4 is a *potential* contention/lack-of-key-detect source, not established until measured. Do not move J15 or disconnect a receiver until tests; any jumper change must be powered off and COM2 used for console afterwards.

Existing monitor commands **do not require new ROM**. After hardware RESET, with COM2 available:
1. `SHOW EF` idle, repeat while physically holding front-panel INPUT, repeat after release. Compare **EF4** values. Source confirms `SHOWEF` samples `BN4` and prints `EF4=0/1`.
2. `IN 4` with no hex key held, then repeatedly **while holding** distinct hex keys 0, 5, A, F (send CR from COM2 while holding). Source confirms `INPUT` handler synthesizes 1802 `INP 4` opcode and reports full read byte in hexadecimal as `Port 4 = xx`. The 1979 interpreter masks to low nibble; examine values & $0F. Keypad number may be latched and require INPUT: test combinations after initial readings.
3. If port4 changes appropriately but EF4 does **not** change with INPUT, prioritize EF4/J15/COM1 RX contention and actual physical INPUT wiring. If EF4 changes but IN4 doesn't, prioritize 1802 I/O decode for port4 and keypad selection (Netronics early board/Giant Board interface). If both change correctly, inspect 1979 keyboard protocol / latency / CPU sense polarity, and prepare an isolated RAM-only poll before ROM patch.
4. Do not assume a CHIP-8 FX0A hang versus other issue until these tests. Breakout begins with a key wait after drawing bricks/paddle so this is a high-value source-level hypothesis.

Retain the already successfully hardware-tested CHIP8 ROM image and cassette/serial features. Next changes should be small, reversible, and based on sampled I/O data.


## 2026-10-19: Breakout photo and Wipe Off video evidence

Owner supplied an actual **Breakout still photo** (`image(20261019-143342).png`) and a **13-second Wipe Off bench video** (`IMG_9996.MOV`) showing the Panasonic CRT on the real Netronics ELF II:

- Breakout: screen contains roughly six evenly-spaced thin horizontal wall rows and a distinct shorter paddle-like band near bottom. These are **plausible program-drawn blocks/paddle**, confirming that the game reaches graphical setup; neither keypress nor INPUT affects apparent game state, per owner's previous report.
- Wipe Off video: near-empty CRT at beginning; small isolated pixels appear toward bottom within several seconds and accumulate into irregular rows of non-structured marks by ~10–11 s. This **is not a demonstrably normal complete Wipe Off playfield**, and could be framebuffer/data-area overlap as owner has previously observed; cannot conclude the exact source from video alone. There is visible temporal change in the framebuffer even before confirmed key input.
- Both exhibit partial graphics, not necessarily fully initialized/compatible game logic. The original Netronics period OS and ROM FOUR/MAZE are functioning; **keypad/EF4 path remains unproven**, as do sophisticated CHIP-8 timer/stack semantics.

Before changing 1979 period interpreter, bench-test from ROM monitor via **COM2** after hardware RESET:
```
SHOW EF
```
Compare EF4 with physical INPUT released versus held (repeat while held), then:
```
IN 4
```
Compare Port 4 full bytes at idle and while holding keypad 5/A/F. Record both port low nibble and EF4 sense. Key question: does the original Netronics front-panel physical keypad protocol currently reach input port4 and EF4, given J15 COM1 EF4 serial receive jumper? Changing console to COM2 doesn't by itself disconnect the COM1 RX electrical path. Do not modify ROM/jumpers until these reads are known.


## 2026-10-19: Port 4 successful, EF4 stuck high — early Netronics S1 analysis

The user sampled `SHOW EF` in the monitor both with front-panel INPUT released and continuously held:
```
EF1=0 EF2=0 EF3=0 EF4=1    (INPUT released)
EF1=0 EF2=0 EF3=0 EF4=1    (INPUT held)
```
Then the user executed `IN 4` with no key held, key `5`, key `A`, key `F`:
```
Port 4 = 64  (idle)
Port 4 = 45  (5 pressed)
Port 4 = 5A  (A pressed)
Port 4 = AF  (F pressed)
```
The low nibble follows the keypad exactly, and the interpreter masks `INP 4` to low 4 bits. **Keypad scanning and port 4 decoding are verified on hardware.** The upper nibble is variable/floating/other signals and not part of the Netronics CHIP-8 keypad code. Idle value $64 needn't identify a key.

Rechecked **owner's actual early-revision Netronics ELF II assembly manual schematic, page 14**: S1 INPUT, the first A13 4049 inverter (input pin9/output pin10), and D6 diode pull-down into EF4. **Correction after tracing the schematic:** R26 47K belongs to the separate N2/LOAD output circuit, NOT EF4. D6 is oriented to pull EF4 low when the first A13 inverter's output goes low: expected static **EF4=1 with S1 released, EF4=0 with S1 held**, although C8 22µF across S1 may affect transitions. Owner's EF4=1 idle is NORMAL, but EF4=1 continuously held is unexpected. Do not infer which specific component holds EF4 high without a voltage measurement. Original *Ipso Facto* #11 p36 requires Netronics keypad at I/O4 (6C) and INPUT switch at EF4.

Hyperboard J15 schematic: pin9 labelled EF4 and pin7 is COM1 receive-select circuit; a jumper between J15 pins7/9 can feed EF4 to COM1. **Don't remove J15 EF4 select before a cold boot:** current Pete's Monitor defaults to COM1 Q/EF4 and uses that input for startup autobaud. Disconnecting it could prevent reaching the `COM2` command, even though COM2 works after selecting it.

Next **safe** diagnostic while already communicating over COM2:
- Probe **J15 pin9 (EF4)** on the Hyperboard, or known CPU EF4 probe point, with DMM/scope referenced to board GND. Compare DC logic levels INPUT released and continuously held, without moving jumpers.
- If both high, EF4 physically held high: trace S1, A13 output pin10, D6 and the EF4 wiring on the original motherboard, plus possible Hyperboard effects. R26 is NOT connected to EF4.
- If level toggles but `SHOW EF` doesn't, reconsider transient pulse/timing or physical EF4 mapping to CDP1802. If button only produces a momentary signal, use a scope/logic analyzer rather than relying on slow CLI sampling.
- Preserve working ROM while diagnosing; no CHIP-8 code patch justified yet.

