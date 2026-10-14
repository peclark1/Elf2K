# AVI ELF II / Hyperboard: first EEPROM bench test

Target: `AVIElf2.hex` from the successful **AVI ELF II ROM development build** CI workflow on branch `feature/avi-elf2-hyperboard-rom`. The image is 32768 bytes / 27C256 or 28C256-class ROM byte addresses $0000-$7FFF, intended at 1802 logical addresses $8000-$FFFF.

**Experiment only.** This code is reproducibly assembled but has NOT yet been proven in a complete CPU/Hyperboard emulator or on the physical hardware. This document gives a controlled first test, not a production firmware endorsement. Do not merge the branch or overwrite the working original ROM.

## Prepare and program

1. Preserve the known-working ROM and record its full-ROM checksum, jumper positions, terminal cabling and programmer device choice. Use a separate compatible EEPROM to test.
2. Download `AVIElf2.hex` from the Actions artifact for the selected successful CI run. The project Makefile/ROM merge tool uses **physical EEPROM offsets** $0000-$7FFF in Intel HEX; do not shift addresses by $8000 in the programmer.
3. Configure the programmer for the **actual device marking**, check its loaded buffer covers exactly 32768 bytes and verify the programming against the buffer. Use the latest generated checksum from CI, not the old stock F0CB checksum.
4. With power off, install the spare ROM. Keep J8 and J7 at the same known-working HIGH-ROM/RAM-LOW boot settings that already launch the Elf2K alternate ROM. Do not change multiple hardware variables at once.
5. Start on the known-working bit-banged Q/EF3 (COM1) terminal at **2400 baud, 8-N-1**. Boot ROM now bypasses the nonexistent Elf2K RTC, NVR, 8250 and IDE hardware; it leaves CDP1854 unused until you explicitly type `UART`.

## First boot tests — COM1/Q/EF3

1. Set display/PIXIE OFF for the initial UART-independent test. Power up or reset and send several carriage returns until the boot autobaud captures the character. Expect an AVI/Elf2K-derived banner including the checksum followed by `>>>`. Check that neither a fixed RTC/NVR POST wait nor an 8250 loopback POST occurs.
2. Type `HELP`, then `SHOW VERSION` or `SHOW EF`. The latter prints the logical EF levels.
3. Type `E FFFE FFFF` and compare these two bytes to the checksum printed by the ROM. Check that the 2-byte value matches CI's ROM checksum. `E 8000 803F` should show non-FF monitor machine code.
4. Confirm basic RAM operations before running intrusive tests: `E 0200`; if that address contains data to preserve, choose an unused location; `D 0200 5A`; `E 0200` should show `5A`. Use `TEST RAM` only once you are comfortable with the test's memory effects.
5. If any problem occurs, note POST code, terminal output, whether input still works, and the last successful command. Reinstall the working ROM rather than repeatedly power-cycling a questionable image.

## Optional CDP1854 test — COM2 at 9600 baud

**Do not type `UART` until the relevant jumper positions and COM2 TTL serial wiring are inspected.** The schematic suggests, but the assembled hardware has not independently verified, the following:

- CDP1854 A3 is strapped for MODE 1, with N1 chip select and N0 register select, making **port 2 data** (`INP 2`/`OUT 2`) and **port 3 status/control** (`INP 3`/`OUT 3`) *when* the remaining UART selects are asserted (check **J14** and its CS2 routing).
- CDP1863 A14 has the PFG programming input STR from **J3**. The experimental ROM uses `OUT 5, $00`, so **J3 must select I65 (OUT 5)** rather than I61 (OUT 1). On the Rev.2 schematic this appears to be J3 pins 1-2; verify board silkscreen and continuity before relying on the position.
- **J10/TCLK and J11/RCLK** must route A14's generated output to the CDP1854 (the schematic's generated-clock side appears to be pin 1 for each 3-pin jumper). Confirm both signal frequencies on the oscilloscope. At 9600 baud and a 16x UART, both clocks should be approximately **153.6 kHz**.
- The A14 clock source is the nominal 2.4576 MHz oscillator X1. The initial divisor value is zero, assuming the CDP1863 CLK2 path produces the 16x clock. If your jumper/CLK1/CLK2 routing differs, adjust the divisor in the firmware; don't assume a port write changes A14 until you verify it on the scope.
- COM2_TX/RX are TTL-level UART signals on the schematic, not ±12 V RS-232. Use an appropriately configured **5 V TTL-level** USB serial adapter and common ground; cross TX/RX. Check the CDP1854 CTS line is asserted in its active-low state or that your adapter correctly drives CTS.

Once the oscilloscope and jumpers are correct, open a second terminal on COM2 at **9600, 8-N-1**, keeping COM1 connected. At the working COM1 `>>>` prompt, type `UART`. The monitor should print `UART 9600 8N1` on COM1 and then switch its prompt/input to COM2. Test `HELP`, `SHOW EF`, and serial receive/transmit repeatedly on COM2. If you don't see a prompt, **reset the ELF II**: the startup firmware will return to COM1 Q/EF3 and require CR autobaud. Do not assume failure proves the CDP1854 is bad without verifying J3/J10/J11/J14/CTS and clock pins.

CDP1861 PIXIE and continuous DMA should remain **OFF during the first COM2 test**. Only after clean hardware UART TX/RX is proven should you enable video and test for UART overruns during sustained data traffic. Tiny BASIC's `TBASIC`, its cassette LOAD/SAVE, and original NCE/NCA remain future work, not part of this image.

## Record back to the firmware project

Please provide: (1) image checksum shown in CI and at boot, (2) exact J3/J10/J11/J14 jumper settings, (3) scoped A3 TCLK pin 40 and RCLK pin17 frequencies, (4) COM1 and COM2 terminal results, (5) any POST number where startup pauses, and (6) whether PIXIE active changes UART behavior. These measurements will let us refine port mapping and default UART policy without losing the known-working fallback.
