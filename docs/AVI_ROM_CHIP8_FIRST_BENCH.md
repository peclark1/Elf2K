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
