# Pete's ELF II Monitor — COM2-first 38,400 baud CHIP-8 test ROM

**Experimental alternate image. Not yet bench tested.** Based on the owner's successful CHIP-8 ROM integration. Preserve the last confirmed working COM1-first OneROM and never overwrite the only copy.

## Purpose

The owner confirmed original RCA VIP CHIP-8 games render on the **AVI ELF II clone motherboard + AVI Hyperboard**, but the normal COM1 receive jumper J15 on EF4 interferes with the 1979 Netronics interpreter's INPUT-button sense. The historical keypad bits are correctly read by `IN 4`; EF4=1 with J15 installed regardless of button. With J15 disconnected, EF4=0 at idle and **does toggle when INPUT is held**. Need a terminal that does not require J15 to be installed at power-on.

This isolated firmware variant **boots directly to COM2**, through the existing tested CDP1854 UART setup and no software bitbang COM1 autobaud. **COM2 38400 8N1** (CDP1854 x16 TX/RX clocks 614400 Hz) is the default at power-on and hardware RESET. It retains the `COM1` command for an optional later switch back to the Q/EF4 serial receiver only if J15 is reconnected.

The hardware baud rate is controlled by the **physical Hyperboard CDP1863/CDP1854 TCLK and RCLK configuration**; the ROM cannot change the base oscillator or jumper-defined clock. The owner already demonstrated COM2 38400 on this Hyperboard, so keep that known-good clock configuration.

## Firmware design

- Isolated branch `feature/avi-com2-38400-default-chip8` off `feature/avi-rom-netronics-chip8`. Its parent COM1-first ROM branch is **not modified**.
- In the AVI disposable `boots.asm` transformation, only `TTYINI` in the AVI variant now branches to `AVICOM2BOOTINIT`, not `TTYAUT`. Startup does not call `COM1` and does not need an EF4 serial edge.
- `AVICOM2BOOTINIT` (in `sw/avi-monitor-commands.asm`) calls exactly the same BIOS `F_USETBD($34)` as the user-verified `COM2 38400` path, stores `BAUD1=$01` and `BAUD0=$34` so `MAIN1` preserves UART selection, and returns to the normal banner/prompt. No serial text occurs until COM2 has been initialized.
- If BIOS initialization indicates error via DF, show `E2` on front panel display rather than falling into COM1 autobaud.
- CHIP8 period core and OS payload, `CHIP8 FOUR`, `CHIP8 MAZE`, `CHIP8`, original Giant ROM, cassette services, and BIOS source are unchanged. The compiled bytes at some ROM addresses will shift as command code and messages move.

## Initial test procedure

1. Preserve old working COM1-first CHIP8 ROM. Program the new 32 KB OneROM BIN/HEX to a **different/test OneROM**. Confirm your Hyperboard 614400 Hz x16 UART TX/RX clock configuration and Tera Term **38400 baud, 8 data, no parity, 1 stop, no flow control**.
2. **Power OFF**, remove the Hyperboard J15 COM1 EF4 receive jumper. Do not change the motherboard INPUT wiring. Power ON.
3. Without pressing Enter to trigger COM1 autobaud, confirm Pete's Monitor banner and `>>>` prompt arrive via COM2 38400. If there is no text, test by pressing Enter on COM2, and if still blank restore old ROM and jumper for rollback.
4. Execute `SHOW EF` with INPUT released and held. It should toggle EF4 now that J15 COM1 serial source is disconnected.
5. Execute `CHIP8 FOUR`, then RESET and `CHIP8 MAZE`: should remain stable, exactly as in the previous user-verified ROM. RESET should bring the console **directly back on COM2**.
6. Load `CHIP8-BREAKOUT-1979.hex` over COM2 and run `CHIP8`. Try hex keypad and INPUT together; record whether game starts and how EF4 reads. Historical interpreter input semantics may still need investigation even if J15 is no longer a factor.
7. Only after these successes consider COM1 fallback and cassette regression tests; no CHIP8 changes are in this build.

**Do not toggle J15 live again.** COM2-first boot eliminates the need for that workaround.

Software CI can validate assembler, ROM layout, checksum, golden 1098-byte period CHIP8 contents, and byte-stable clean rebuilds. Actual UART startup on real Hyperboard **must still be tested by owner**.


## Owner hardware confirmation: COM2-first startup (2026-10-19)

Owner reports: **"works perfect! com2 started right up at 38400 in the monitor"** on the real AVI ELF II clone + AVI Hyperboard. This establishes that the experimental COM2-first ROM cold-start/monitor path works on the physical board at **38400 baud, 8N1**. No need for COM1 autobaud at startup. It does **not** yet establish that J15 removal plus COM2 enables original CHIP-8 keyboard routines to recognize FX0A, or confirm ROM regressions; those remain pending bench tests. Preserve previously hardware-verified ROM until other functions have been checked.


## Two-square FX0A RAM isolation — user bench results (2026-10-19)

The two-square user-program memory was read back and matches program at $0200 and sprite at $0300 (FF 81 81 81 FF). Original two-square program with **FX0A at $0208** produces flashing garbage on CRT. Replacing FX0A with branch $0208 (`D 0208 12 08`) produces a **stable first square**. Replacing FX0A with `LD V2,05` (`D 0208 62 05`) produces **two stable squares**. Restoring FX0A and patching the period OS at $0D9A from `3F 9A` to `30 9E` (bypass EF4 wait) **still produces flashing garbage**; additionally replacing `INP4 / ANI $0F` at $0D9E with `F8 05 C4` (forced synthetic value) **still produces flashing garbage**. Original diagnostic had a second-square redraw loop (`12 0E` at $0210); correcting that to a proper self-loop (`12 10`) **still produces flashing garbage**. These strongly indicate something about **FX0A dispatch/return**, not solely keypad or EF4 hardware. Do not claim those RAM patches have been read back after all changes; no evidence yet whether patched handler is reached.

**Next isolating test:** With J15 removed and COM2-first ROM, patch user game `D 0208 F2 07` (read delay timer instead of wait-for-key); `D 0210 12 10` (proper self-loop), then `CHIP8` (reinstalls clean interpreter, retains test program and sprite). Two stable squares would indicate Fx opcode family works and FX0A special path is faulty; flashing garbage would implicate broader Fx dispatch or ROM/OS compatibility. Inspect original $01C4–$01D8 interpreter sequence and $0D94–$0DA4 keyboard before modifying ROM. Also note Pete Monitor `SHOW EF` displays **logical inverted-active EF values**, not literal CPU-pin voltages.


### 2026-10-19 FX07 video (IMG_0005.MOV)

Owner power-cycled and loaded the complete `CHIP8_FX07_TWO_SQUARES_FULL.hex` over 38400 COM2. The HEX artifact has three valid Intel HEX records: $0200..$020F = `60 08 61 08 A3 00 D0 15 F2 07 60 28 D0 15 12 0E` and sprite $0300..$0304 = `FF 81 81 81 FF`. Its final branch `12 0E` at $020E correctly loops at itself. The owner's 6.5-sec video visibly shows vertical bars followed by rapidly changing dense static, then near-solid PIXIE region, **not stable two squares**. This establishes FX07 also fails and that failure is **not specific to FX0A's EF4 or INP4 path**, conditional on verifying actual board memory. No memory-examine readback was supplied after this new power cycle, so first confirm `E 0200 020F`, `E 0300 0304`. If correct, patch just `D 0208 62 05` then `CHIP8` (restores stock OS; program preserved), expecting two stable squares as earlier observed. This is a same-load control test; only then investigate the historical Fx dispatch/return code. Avoid firmware reflashing or blaming hardware until this control passes.

## 2026-10-19 — Suspected 1979 F-group dispatcher corruption (unverified fix)

After the owner confirmed **two stable squares** with the same valid externally loaded test program by replacing `FX07` at $0208 with `62 05`, we examined the original RCA COSMAC VIP interpreter (RCA manual Appendix C), compared with the *Ipso Facto* #11 p37 Netronics Table 2 and the byte-identical integrated copy.

The original RCA VIP group-F dispatch address table in RAM **$006F = $05** (with $005F=$01) enters **$0105**, where the original bytes are:

```
0105: 45    LDA R5      ; fetch second opcode byte, advance CHIP8 PC
0106: A3    PLO R3      ; executable dispatch to $01xx, e.g. xx=07 or 0A
0107: 98    GHI R8      ; FX07 read timer
0108: 56    STR R6      ; store into Vx
0109: D4    SEP R4      ; return to fetch/decode
010A: F8 0D BC F8 95 AC ... ; Netronics FX0A keyboard entry
```

The published *Ipso Facto* Table 2 writes `0104: F8 01 B5 F8` and `0108: 56 D4 F8 0D ...`, so the adapted RAM is:

```
0104: F8 01 B5 F8 56 D4 F8 0D BC F8 95 AC ...
0105: 01 B5 F8 56 D4 ... ; actual F-group entry is now broken
```

This would execute `LDN R1; PHI R5` on every F opcode, corrupt the CHIP8 program counter, and then fall back to the fetch loop without selecting an F operation. It exactly fits the identical FX07 and FX0A video-failure results. The #12 erratum appears to discuss only hardware video mapping at $0C70, not this dispatch.

**Proposed unverified minimal RAM-only patch**, preserving period Netronics FX0A routine and both monitor images:

1. The externally loaded two-square diagnostic remains in RAM after RESET (verify `E 0200 020F`, `E 0300 0304`; it last had `62 05` at $0208 and displayed two stable squares).
2. `E 0100 0114` to confirm current pre-patch interpreter code. Then `D 0105 45 A3 98 56 D4`. This restores original RCA VIP group-F dispatch and FX07 handler only; Netronics 010A keyboard routine and original $0D95 OS remain unchanged.
3. `D 0208 F2 07`; optionally verify with E. **`RUN 0E80`** (NOT `CHIP8`, which would overwrite patch). Expect two stable squares, proving FX07 now works.
4. On success, RESET and `D 0208 F2 0A`, then `RUN 0E80`; expect first square waiting until physical INPUT + hexadecimal key sequence, then second square. That would prove the keyboard path too.
5. If fail, don't change shipped ROM; further trace program pointer $0105 before proposing other changes.

Do **not** simply change $006F to $04: that would enter at 0104 but would **not** restore the original $0105 LDA R5/PLO R3 dispatch. It would not solve the F handler logic.

External corroboration: RCA 1978 COSMAC VIP manual Appendix C has `0100: 00 00 00 00 00 45 A3 98 / 0108: 56 D4 F8 81 BC F8 95 AC`; Laurence Scotford's "Chip-8 on the COSMAC VIP: The Call Routine (Fetch and Decode)" and "Keyboard Input" describe the F-group dispatch and FX0A.


## 2026-10-19 hardware verified F-dispatch five-byte repair

After confirming in monitor `E 0105 0109` that the current Netronics interpreter had `01 B5 F8 56 D4` at $0105, the owner patched RAM `D 0105 45 A3 98 56 D4`, restored `FX07` in the two-square program with `D 0208 F2 07`, and ran `RUN 0E80` rather than `CHIP8` (which would overwrite the RAM patch). **Hardware outcome: TWO STABLE SQUARES.** This is a decisive positive controlled test that restoring original VIP $0105 F-family dispatch fixes FX07 on the actual AVI ELF II/Hyperboard with COM2-first 38400 monitor. The ROM image itself has NOT been changed; patch is RAM only.

Next bench step: RESET, `D 0208 F2 0A`, then `RUN 0E80` with the same $0105 patched interpreter still in RAM. With first square displayed, hold key 5, tap INPUT and release INPUT while continuing to hold 5; expect second square if original Netronics FX0A implementation can use EF4/INP4. Do not issue `CHIP8` until completing patched test. If succeeds, develop a separate ROM-fix variant that patches the 5 bytes of the historically copied interpreter, preserving previous known-good ROM as a rollback and requiring independent checks.
