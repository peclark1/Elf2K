# Historical CHIP-8 game library for AVI ELF II

**Status:** experimental and independent of AVI CHIP-8 interpreter / OneROM firmware. No ROM changes.

## Scope and provenance

Our target is the **1979 Netronics original RCA COSMAC VIP 64x32 CHIP-8
interpreter** on the CDP1861. Pete's Monitor command **CHIP8** preserves
game RAM **$0200–$09FF (2048 bytes)** while installing the interpreter/OS.
The three-byte historical interpreter repair has been tested on hardware;
Breakout (1979) is playable on the user's AVI ELF II.

Source collection: [Emma 02 historical CHIP-8 games](https://github.com/etxmato/emma_02/tree/master/data/Chip-8/Chip-8%20Games).
The workflow pins commit **9bd1cdb1fd020081d6536a94d19351c94578acd0**
rather than relying on whatever master points to in the future.

The upstream folder at that commit includes **172 CH8 binaries, 83 HEX
listings and 121 text descriptions**. Some upstream HEX files pad the
last record; the converter instead reads the original exact-length CH8
and regenerates Intel HEX at $0200 with tested record checksums.

## Downloadable package and catalog

Open [Historical CHIP-8 library audit — GitHub Actions](https://github.com/peclark1/Elf2K/actions/workflows/chip8-library.yml).

A successful workflow run uploads **AVI-ELF-II-CHIP8-HISTORICAL-GAMES**,
a ZIP containing:

- **README.md** — prioritized load-ready historical candidates.
- **catalog.csv** — complete, sortable inventory with screening reasons.
- **catalog.json** — inventory including source SHA256 and opcode findings.
- **loadable-hex/** — up to 30 historical candidates as monitor-ready Intel HEX.

The job downloads only the games subdirectory via pinned sparse git checkout,
audits it, checks Intel HEX round-trips, and publishes the package. It
does not rebuild or change the user's ROM.

Run locally with Python 3.10+ and an existing Emma 02 checkout:

    python3 -m unittest discover -s sw/build -p 'test-chip8-library.py' -v
    python3 sw/build/chip8-library.py \
      --source "/path/to/emma_02/data/Chip-8/Chip-8 Games" \
      --revision 9bd1cdb1fd020081d6536a94d19351c94578acd0 \
      --output /tmp/avi-chip8-games --max-games 30

## Screen outcomes (never a hardware guarantee)

| Status | Interpretation |
|---|---|
| likely | Original/vintage provenance suggested, fits 2K preserved area, reachable instructions are VIP-style, no unresolved scanned paths |
| review | Newer/unknown provenance, VIP-specific machine SYS calls, computed BNNN jumps, or questionable control-flow targets |
| incompatible | Known ETI-660 program, exceeds game RAM, or uses unsupported / extended reachable opcode |
| hardware_status | Independent annotation: confirmed actual AVI ELF II test vs. not yet tested |

The analyzer follows branch and subroutine paths beginning at $0200 rather
than treating ALL sprite pixels as opcodes. It explores both conditional
outcomes. Dynamic BNNN branches are flagged; it cannot prove behavior of
self-modifying programs or diagnose original-VIP shift, carry, random,
sound, timer, keyboard or CPU/video DMA timing differences. A program marked
likely can still fail on the real machine.

**Airplane** is explicitly excluded based on this project's prior ETI-660
investigation, *not* by interpreting its short upstream text instructions
(which do not mention ETI-660).

## Loading / testing

1. Keep the existing FXFIX OneROM and Hyperboard setup.
2. Send ONE generated game-only Intel HEX file through Pete's Monitor
   serial Intel HEX loader (addresses $0200–$09FF).
3. Type **CHIP8** without an argument. CHIP8 FOUR and CHIP8 MAZE
   overwrite the supplied game bytes and must not be used for external games.
4. Record display, correct controls, responsiveness and win/loss behavior.
   RESET returns to the monitor when autoboot is active. With autoboot
   disabled, toggling RUN off/on has been tested to restart Breakout in RAM.
5. For Breakout, hold **4 + INPUT** to move paddle left; **6 + INPUT**
   to move right. INPUT also launches/starts the ball.

## Hardware test status

- **Breakout (Carmelo Cortez, 1979):** real hardware proven playable,
  including direction+INPUT controls and RUN restart with autoboot off.
- **Wipe Off (Joseph Weisbecker):** previous CRT video showed changing
  pixels but did not establish correct complete gameplay.
- **Kaleidoscope (Joseph Weisbecker, 1978):** awaiting hardware test.
- All other scanned titles: automated predictions, not hardware verified.

## Rights

Games span different authors and periods; do not presume public-domain
status or permission to redistribute every game. Preserve original names,
attributions, source links and source checksums. Check permissions before
redistributing beyond personal research/testing.
