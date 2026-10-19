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

The owner has now confirmed FX0A from a programmed ROM image, without the RAM interpreter patch. Do not merge until the remaining game regression checks are completed.


## Downloadable programming artifact

The passing `AVI ELF II ROM development build` GitHub Actions run creates an independent `AVIElf2-COM2-38400-CHIP8-FXFIX-OneROM-PROGRAMMING` ZIP with a 32,768-byte binary, corresponding Intel HEX, short README, and SHA-256 checksum manifest. CI runs two clean builds and requires byte-for-byte identical assembled HEX before packaging. The image retains the proven COM2-first 38,400-baud setup and existing experimental OneROM startup-checksum bypass. **The owner has now confirmed FX0A on a programmed FXFIX test ROM supplied previously; identify the flashed binary hash before equating it with this separate CI package.**


## 2026-10-19 — Owner bench confirmation of programmed FXFIX ROM

The owner reports that the **previously supplied FXFIX test ROM** was programmed and the two-square FX0A diagnostic **works from ROM**, with no manual interpreter RAM fix needed. Crucially, the successful keyboard sequence also works as:

1. Press hexadecimal **5** and release it completely.
2. Press **INPUT** and release it.
3. The second square appears.

Earlier patched-RAM testing used a *held* hex key while INPUT was pressed. This new ROM test demonstrates the two actions need not overlap on the tested hardware, consistent with a retained/stable encoded keypad value between the two button presses. This establishes the **FX0A path of the installed FXFIX ROM** is operational. It is not proof that every original CHIP-8 game is playable, nor is it a fresh standalone FX07 ROM test.

The owner identifies the firmware as the ROM supplied for testing in the preceding conversation; the *exact flashed binary SHA-256 has not yet been reconfirmed*. Do not automatically assign this observed result to the separately generated newer programming-package checksum until the binaries are matched.

**Next:** Test FX07 with no RAM patches if not already done on this installed ROM; then load Breakout (1979), Wipe Off and Kaleidoscope (1978) in turn. Keep the proven COM2-first ROM as rollback; leave PR draft pending these game regressions.


## Breakout (1979) hardware controls — encoded key and INPUT

On the programmed repaired FXFIX-ROM AVI ELF II + Hyperboard, the owner confirms **Breakout starts and launches the ball when INPUT is pressed**. Paddle motion uses a two-step procedure: **press 4 or 6 to select the direction, then hold the separate INPUT button to move the paddle**. The selected direction continues to apply after releasing the hexadecimal key; INPUT acts like a held-action signal. This is a user-observed behavior, not yet a source-level proof of the exact latch/EF4 mechanism.

This is consistent with the Netronics adaptation's separately encoded hexadecimal keypad data (1802 `INP 4`) and INPUT/EF4 signal; it differs from modern CHIP-8 emulators where holding 4 or 6 alone generally moves the paddle. The earlier FX0A two-square test similarly worked when hex 5 was pressed and released *before* a separate INPUT press. Avoid describing these separate-button observations as a new firmware defect.

Still to be characterized: whether 4 and 6 can switch directions while INPUT stays held; full-game outcomes and other historical games (Wipe Off and Kaleidoscope) are not established by the Breakout control test.


## Breakout verified play ergonomics and RUN restart

Further owner testing on the actual AVI ELF II confirms:

- With **autoboot disabled**, toggling hardware **RUN OFF then RUN ON** restarts the resident CHIP-8 Breakout game directly, without serial reload or a return to the ROM monitor. This was explicitly tested; it is not only a theoretical behavior.
- Although selecting hex **4** or **6** and pressing/holding INPUT afterward works, actual gameplay is much easier with **hex 4 + INPUT held together** to move left and **hex 6 + INPUT held together** to move right. The owner's real-world preference is simultaneous holding for natural reaction to the ball.
- The earlier two-stage direction-latch procedure remains useful for electrical diagnosis, but should **not** be presented as the preferred play instructions.

Do not infer that the interpreter has been changed or that other games are fully tested from these observations. A test of switching 4/6 while INPUT is kept held was proposed but is not yet independently confirmed.
