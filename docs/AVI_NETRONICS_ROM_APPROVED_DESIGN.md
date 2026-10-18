# AVI ELF II Netronics-Compatible ROM — Approved Design (2026-10-17)

**Decision:** Implement as an isolated firmware variant on `feature/avi-netronics-compatible-rom`. This supersedes contrary *proposals* in the earlier AVI design document for this variant; it does not change the proven baseline.

## Hardware and interface contract

- 32 KiB SRAM at `$0000–$7FFF`, 32 KiB ROM at `$8000–$FFFF`.
- Boot the AVI/Elf2K-derived monitor at `$8000`. Warm entry `$8003`.
- **Default COM1**: Q transmit / **EF4** receive, bit-banged at the machine's proven nominal 2400-baud mode. Change the Hyperboard COM1 receiver select jumper to EF4 before trying this variant; do not switch physical jumpers powered.
- Optional COM2: CDP1854 polling UART, verified **9600 8N1**, on Hyperboard ports 2/3, clock-latch OUT5. Keep the existing successful `LDX` receive-echo bug fix.
- Monitor commands: `COM1` / `1`, `COM2 [9600|19200|38400]` / `2 [baud]`; retain `UART` as a COM2 alias. Selection acts on the *monitor*, not on independent historical applications. Give confirmation on the old active console first.
- **2026-10-18 bench-test decision:** accept `COM2 19200` and `COM2 38400` as explicit experimental external-clock modes. These commands initialize the SAME polling CDP1854 UART as `COM2 9600`; they do not modify the CDP1863/4040 hardware clock, so the user must select and measure 307.2 kHz or 614.4 kHz at BOTH UART TCLK and RCLK (16× desired baud) before testing. A mismatch may lose console characters, but a power/reset restarts COM1. Higher baud rates are not yet electrically verified and should not be presented as software-selectable clock modes. Do not reposition jumper leads while powered.
- On cold boot, always return to COM1. For a live switch *back* from COM2, re-autobaud from COM1 (press CR at 2400) rather than assume a software-serial delay value.
- Do not redirect historical Q/EF4 applications to the CDP1854.

## ROM component policy

- Retain: AVI/Elf2K monitor, HELP, EDTASM, hardware-neutral BIOS, proven CDP1854 UART, Intel HEX `:` record input, `EXAMINE`, `DEPOSIT`, `RUN`.
- **Remove** from this variant: rc/BASIC and XMODEM. Do not delete their source or modify the original stock builds.
- Install the **original unmodified 256-byte Netronics Giant Monitor** at `$F000–$F0FF`, sourced from Emma 02 `data/NetronicsElfII/giantboard.hex`. Its original keyboard and cassette operations are not modern monitor commands. `RUN F000` enters it.
- Leave `$F100–$F2FF` available and preserve the existing BIOS `$F300–$FFFF`.
- **Tiny BASIC is NOT ROM-resident**. Build the authentic Netronics version as a separate Intel HEX payload for loading into low RAM `$0000` and executing with `RUN 0000`. Preserve Tiny BASIC's original Giant Monitor calls at `$F065` and `$F0BA` until hardware tests prove compatibility. Preserve low RAM on monitor return; verify cold/warm entry semantics.
- Generic cassette services at monitor level are a future enhancement. The original Giant Monitor must be tested first for its keypad, timing, Q output, EF2 input, and compatibility with Hyperboard cassette hardware. Do not invent cassette save-format guarantees.

## Loaders

- Keep existing Intel HEX records (with per-record checksum validation).
- Add interactive **`HEX <start>`** for plain hex byte listings: consecutive byte pairs, spaces between bytes, a terminal `.` line, address progression, RAM-range guard, and readback verification. Existing `D <addr> <bytes...>` remains available. A host-side magazine-listing converter is a separate optional utility; do not infer labels from ambiguous byte sequences.
- Ensure no loader writes into the monitor's RAM page at `$7F00–$7FFF`.

## Image and test policy

- The successfully tested One ROM image with expected checksum **875B** is an immutable fallback, NOT to be overwritten in the working branch.
- A build, correct checksum, and 32 KiB size are not proof of hardware safety. Deliver experimental files separately and label them as not bench-tested.
- The baseline checksum-scanning anomaly remains unresolved. If preparing a One ROM test image, preserve and document the known diagnostic bypass separately from the pure assembled image, and compare every resulting byte.
- Test gate order: reproducible assembly -> layout/checksum/bytes -> startup COM1/EF4 -> COM2 at 9600 -> switch-back COM1 -> Intel HEX -> raw HEX -> Giant Monitor keypad/examine -> cassette electrical measurements -> Netronics Tiny BASIC from RAM -> cassette round-trip.
- Do not energize or re-jumper physical hardware via automation.

## Provenance

- Giant Monitor source: [Emma 02 archive](https://github.com/etxmato/emma_02/blob/master/data/NetronicsElfII/giantboard.hex); verified 256 data bytes at CPU `$F000–$F0FF`.
- AVI Hyperboard documentation explicitly describes the Giant Monitor at `$F000`: [AVI Hyperboard assembly notes](https://github-wiki-see.page/m/awasson/AVI-ELF-II/wiki/AVI-Hyperboard-Expansion-Card-Assembly-Notes).
- Netronics Tiny BASIC source uploaded for this project, `Tinybasi(1).asm`.
