# AVI ELF II — verified 1979 CHIP-8 FX-dispatch repair

**RAM patch hardware-proven on 2026-10-19. New ROM integration not yet hardware-tested.**

## Problem and confirmed repair

The AVI ELF II clone + AVI Hyperboard runs the period 1979 Netronics CHIP-8 interpreter, including its FOUR and MAZE demos, but Breakout, Wipe Off, and Kaleidoscope initially did not recognize keys.

- CDP1802 INP 4 successfully reads the physical hexadecimal keypad.
- After COM2-first 38,400-baud monitor boot and removal of the COM1-to-EF4 jumper, INPUT correctly changes EF4 (as seen through the monitor SHOW EF command).
- An externally loaded two-square test gave rapidly flashing garbage with F2 0A (FX0A, wait for key) or F2 07 (FX07, read delay timer), but drew two stable squares with 62 05 (LD V2,05).
- The archived 1979 Netronics interpreter contains 01 B5 F8 56 D4 at RAM 0105-0109, where the F-group dispatcher expects the original RCA COSMAC VIP sequence 45 A3 98 56 D4.

The owner changed only RAM:

    D 0105 45 A3 98 56 D4
    D 0208 F2 07
    RUN 0E80

**Result: FX07 worked, two stable squares.**

Then after RESET, with the RAM-patched interpreter intact:

    D 0208 F2 0A
    RUN 0E80

The owner held hex key 5, pressed and released INPUT, then released 5. **Result: FX0A worked; second square appeared.**

The exact five-byte patch is proven on real AVI ELF II hardware, and there is no justification for changing EF4 or the native 1979 keypad handler.

## ROM implementation and verification

Separate branch: feature/avi-chip8-fx-dispatch-fix, based on hardware-tested COM2-first 38400 branch. Original branch and older OneROM chips remain intact.

- sw/avi-chip8.asm: the interpreter ROM archive at CPU D905-D909 is changed from 01 B5 F8 56 D4 to 45 A3 98 56 D4, so CHIP8 automatically copies the correct dispatcher to RAM at 0105.
- sw/build/verify-avi.py: all 1098 interpreter, OS, sprite, game and boot data bytes are checked against *unmodified* 1979 archived RAM HEX fixtures, with exactly three changed bytes (RAM $0105: 01→45, $0106: B5→A3, $0107: F8→98). The remaining 1,095 bytes, including the two unchanged bytes at $0108–$0109, match the original period sources.
- sw/build/prepare-one-rom.py: output labelled FXFIX, checksum-bypass procedure otherwise unchanged.
- Independent CI builds must succeed and match byte-for-byte, with verified layout and ROM checksum.

## New ROM bench checklist

1. Preserve the already hardware-working COM2-first 38400 OneROM as rollback. Program FXFIX into a **separate** test OneROM.
2. Keep Hyperboard J15 COM1-to-EF4 jumper disconnected **with power off**. Retain existing CDP1854 x16 clock at 614400 Hz, and set Tera Term COM2 38400 8N1.
3. Power on and confirm monitor prompt appears directly on COM2, without COM1 autobaud.
4. Try CHIP8 FOUR and CHIP8 MAZE for display regression.
5. Re-load two-square FX0A diagnostic and run CHIP8 **without any RAM patches**. While first square is visible, hold 5; press and release INPUT; release 5. Expect second square.
6. Load historical Breakout game-only HEX and launch CHIP8, then test gameplay. Other games can follow. **The whole games are not yet hardware-verified playable** merely from the passing minimal FX0A test.
7. If the new ROM fails, reinstall previous working COM2-first OneROM; do not change jumpers live.

Do not merge until owner confirms ROM image, not just the RAM patch.


## Downloadable programming artifact

The passing `AVI ELF II ROM development build` GitHub Actions run creates an independent `AVIElf2-COM2-38400-CHIP8-FXFIX-OneROM-PROGRAMMING` ZIP with a 32,768-byte binary, corresponding Intel HEX, short README, and SHA-256 checksum manifest. CI runs two clean builds and requires byte-for-byte identical assembled HEX before packaging. The image retains the proven COM2-first 38,400-baud setup and existing experimental OneROM startup-checksum bypass. **Only the RAM patch has been bench verified; this newly compiled ROM awaits bench verification.**
