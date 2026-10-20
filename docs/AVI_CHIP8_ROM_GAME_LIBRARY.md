# AVI ELF II — 27 built-in CHIP-8 games (GAME27 ROM experiment)

**Status:** software experiment on feature/avi-chip8-rom-library, draft PR #8.
Not yet tested on the physical AVI ELF II. Keep the existing working
COM2-first/Fxfix OneROM unchanged as a rollback.

## What changed

The original, hardware-tested 1979 Netronics CHIP-8 interpreter, its three-byte
FX dispatcher correction, original Giant Monitor, UART init, cassette services,
and the previously working ROM CHIP8 FOUR and CHIP8 MAZE demos remain intact.

This variant adds **27 byte-exact original CHIP-8 game images** (10,958 bytes)
in previously reserved 32-KiB ROM space. The menu and command handler use
D100-D1FF, and the 27-entry directory is F100-F2AF (16 bytes/entry:
ROM address, byte count, 12-byte NUL-padded ASCII title). The build repacks
games deterministically into four ROM windows, never splitting an image:

| ROM space | Uses |
|---|---|
| A100-A3FF | 768 of 768 game bytes |
| B100-C1FF | 4,342 of 4,352 game bytes |
| D100-D1FF | built-in CHIP8 menu, number parser, copier setup |
| D200-D7FF | 1,536 of 1,536 game bytes |
| D800-DCFF | **original Netronics interpreter / OS / tests, unchanged** |
| DD00-EFFF | 4,312 of 4,864 game bytes |
| F000-F0FF | **original Giant Monitor, unchanged** |
| F100-F2AF | ROM library directory, 432 bytes |
| F300-FFFF | **BIOS, unchanged apart from checksum tail** |

Existing monitor HELP at 9800 now mentions game commands. A fresh
ROM checksum and programming-image checksum-bypass patch are calculated.

## Console usage

COM2 serial remains **38,400 baud 8N1**, with the user's established
614,400-Hz x16 TCLK/RCLK clock and **J15 removed** to free EF4.

At Pete's Monitor:

    CHIP8 LIST
    CHIP8 01
    CHIP8 02
    CHIP8 03
    CHIP8 04
    CHIP8 1B

Each number is **hexadecimal** (01..1B), not decimal. The command
loads the chosen ROM game into RAM $0200, clearing $0200-$09FF first
to prevent another game's stale sprites, then installs the period
interpreter/OS and runs the normal interrupt-enabled PIXIE startup.

- **01**: 1979 Breakout, hardware-proven on the previous FXFIX ROM.
- **02**: Wipe Off, still needs a complete gameplay test.
- **03**: Kaleidoscope, not yet confirmed on real hardware.
- **04**: Lunar Lander, not yet confirmed on real hardware.
- **1B**: Sum Fun, not yet confirmed on real hardware.

Original interfaces remain:

    CHIP8          (launch program loaded by serial Intel HEX at 0200)
    CHIP8 FOUR     (original four-squares display diagnostic)
    CHIP8 MAZE     (original Maze diagnostic)

The original Netronics controls require a hex key and INPUT to
register a press. For Breakout, **hold 4+INPUT to move left** or
**6+INPUT to move right**. The INPUT button starts/launches a ball.
With autoboot disabled, toggling RUN off/on restarts the RAM game on
the tested FXFIX hardware. With autoboot enabled, RESET returns to the
monitor so CHIP8 or CHIP8 01 can restart.

## Source preservation and build integrity

Game sources: Emma 02 public CHIP-8 collection, pinned at commit
9bd1cdb1fd020081d6536a94d19351c94578acd0. Each title and original
HEX source file SHA is stored with its exact truncated-to-CH8-size
binary payload in two versioned JSON files. The library manifest from
our previous hardware-oriented audit ranks these 27 games as *likely*
compatible; that is a static prediction, not an emulator or real-hardware
guarantee. Breakout alone has the proven hardware-playable result.

Assembler procedure (after cloning the repository and installing the
pinned tools):

    bash sw/build/build-avi.sh
    python3 sw/build/prepare-one-rom.py \
      .build/avi-rom/work/AVIElf2.hex .build/avi-rom/work

The script generates the separate chip8-games.asm source. TASM assembles
chip8-games.hex independently; ROMMERGE fills the entire 32-KiB ROM;
the checksum tool stamps it. verify-avi.py checks every game byte, menu
pointer/label, all unused library bank padding, historical 1,098-byte
interpreter payload invariants and final ROM checksum.

Only the file named **AVIElf2-COM2-38400-CHIP8-GAME27-OneROM.bin** should
be considered for this experimental game-library test; it is **not**
the same as the previously successful FXFIX ROM. The paired Intel HEX
is meant for the programmer; verify size 32,768 and checksum against
SHA256SUMS-GAME27.txt before flashing. Both files include the same
previously experimental startup ROM self-check bypass approach.

## Bench acceptance checklist

1. **Do not overwrite the only working OneROM.** Use a separate chip
   and preserve the full verified FXFIX test image.
2. With power off, fit the experimental GAME27 OneROM; retain existing
   COM2 clock and J15 wiring. Boot to Pete's Monitor at 38400 8N1.
3. Run CHIP8 LIST and verify 01..1B exactly 27 entries without
   garbled serial or hangs; test invalid 00 and 1C commands.
4. Type CHIP8 01. Test Breakout graphics, ball launch, 4+INPUT,
   6+INPUT, and game-over behavior; RESET and select it again.
5. Select CHIP8 02 and CHIP8 03. Record display/input differences,
   including any original keypad+INPUT adjustments.
6. Verify CHIP8 FOUR and CHIP8 MAZE still display properly.
7. Send the original Breakout Intel HEX via serial at $0200, then
   launch bare CHIP8. The preserved external-game path must still work.
8. Recheck serial COM2 after RESET, RAM readback and normal monitor
   commands before considering this candidate proven.
9. If boot or monitor behaves unexpectedly, power down and restore
   the known-good FXFIX OneROM rather than changing jumpers under power.

No merge until the real hardware reports are recorded.

## Emma 02 live test and HELP overlap fix (2026-10-20)

Owner confirmed that the **unchanged GAME27 binary booted in Emma 02**
and displayed Pete's ELF II Monitor V120 (initial checksum `95D5`) with
functional CDP1854 VT100 output. Running `HELP` revealed a genuine
ROM overlap: the original 2466-byte HELP hex starting at $9800 overflowed
its 2304-byte reservation by 162 bytes, into the first ROM game at $A100.
ROMMERGE's overlapping game image hid the HELP terminator. The monitor
printed a couple of stray game opcode bytes as characters, then found
the game's $00 and returned to the prompt.

The corrected HELP text is 2138 bytes including the NUL and terminates
at **$A059**, leaving **166 bytes** of $FF padding before $A100.
`verify-avi.py` now reads the *separately assembled* `help.hex`,
rejects out-of-window bytes, checks its NUL terminator and verifies that
the final ROM contains the complete HELP text and untouched padding.

GitHub Actions clean two-pass ROM build and verifier **passed** at
[run 39351228206](https://github.com/peclark1/Elf2K/actions/runs/39351228206).
Corrected GAME27 OneROM image: **SHA256
`452761030c4cf316b9067696d149bed7f6e8f209ca036f3add431b9c8087d715`**,
boot checksum **`F586`**. Bytewise comparison to the prior 32-KiB
`95D5` GAME27 image: all changes are strictly limited to HELP
$9800-$A0FF and the four STG checksum/correction bytes
$FFFC-$FFFF. In particular all 27 game ROM bytes and the
Netronics interpreter/OS, monitor, Giant Monitor and BIOS are unchanged.
New ROM has not yet been independently hardware-tested beyond the
owner's successful older GAME27 boot.

[Revised OneROM programmer ZIP](https://github.com/peclark1/Elf2K/actions/runs/39351228206/artifacts/12232862564).

With Emma 02 stopped, replace the existing ROM file in the active
`data/NetronicsElfII/` folder with the new, identically named BIN from
the ZIP, then fully restart the emulator. Confirm boot checksum F586;
`HELP` should now end cleanly with the `HEL[p]` line. Next run
`CHIP8 LIST`, then `CHIP8 01`, recording both VT100 and PIXIE output.
