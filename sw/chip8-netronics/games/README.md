# Period RCA COSMAC VIP CHIP-8 games for Netronics ELF II

The 1979 historical interpreter launched by the AVI ELF II Monitor's `CHIP8` command is based on the original RCA VIP 64×32 CHIP-8 format. These are original low-resolution programs sourced from [Emma 02's historical CHIP-8 collection](https://github.com/etxmato/emma_02/tree/master/data/Chip-8/Chip-8%20Games), not the incompatible 64×48 ETI-660 variants.

All three game-only Intel HEX records and checksums have been validated. All bytes load at `$0200` and stay within the protected game area `$0200–$09FF`. **None has been verified on the physical Netronics ELF II yet.** The ROM launcher and embedded Four-Squares and Maze images *have* been verified by the owner.

| File | Original author/period | Bytes | Load range | How to play |
|---|---|---:|---|---|
| `CHIP8-KALEIDOSCOPE-1978.hex` | Joseph Weisbecker (1978) | 128 | $0200–$027F | Press 2,4,6,8 to make a pattern; 0 to start repeating it; try 44444442220 |
| `CHIP8-WIPE-OFF.hex` | Joseph Weisbecker | 208 | $0200–$02CF | Use 4 and 6 for paddle movement |
| `CHIP8-BREAKOUT-1979.hex` | Carmelo Cortez (1979) | 240 | $0200–$02EF | Variation of Wipe Off; use 4 and 6 to move paddle; six walls and 20 balls |

To use:

1. Start the current CHIP-8-enabled Pete's ELF II Monitor ROM.
2. Send just **one game-only** Intel HEX file to the monitor using its existing serial Intel HEX loader.
3. Enter `CHIP8` (without FOUR or MAZE).
4. Hardware RESET to exit when ready; another game HEX file can then be sent and launched similarly.

`CHIP8 FOUR` or `CHIP8 MAZE` are bundled tests and overwrite low game memory, so do not use them to launch newly loaded files.

Kaleidoscope is our suggested first interactive keypad test. The period Netronics input port/EF4/INPUT key circuitry has not been exercised with the new ROM launcher, and sound/timers have not yet been conclusively verified. A stable screen plus responsive 2/4/6/8/0 entry will be the next genuine compatibility milestone.

Sources: original game .hex and .txt entries in Emma 02. Keep provenance with any redistributed archive.
