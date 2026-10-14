# AVI ELF II Hyperboard ROM: implementation and hardware audit

**Milestone:** Independent AVIElf2 configuration and reproducible DEVELOPMENT build.
**Branch:** feature/avi-elf2-hyperboard-rom
**Approval status:** Owner authorized a **spare-EEPROM bench experiment** (2026-10-12). No merge is authorized. Real-hardware validation is still pending.

The owner/coordinator removed byte-for-byte historical-stock ROM equivalence as a prerequisite for the custom image. No checked-in stock ROM or stock configuration is overwritten. The pinned stock reconstruction tools, build scripts, artifacts and source references remain in place.

## Explicit first-stage component selections

| Component | AVI choice | Notes / next functional test |
| --- | --- | --- |
| BOOTS $8000-$97FF | **Keep and AVI-port startup** | Preserves checksum/RAM tests; resets to Q/EF3. NVR/RTC/8250/IDE/PS2/GPIO startup is bypassed; unsupported commands omitted from parser in AVI build. |
| HELP $9800-$A0FF | **AVI bench-test HELP** | Documents the Q/EF3 startup and opt-in UART command; legacy stock help unchanged. |
| SEDIT $A100-$A3FF | **Omit, reserve** | Disk sector editor requires Elf2K IDE hardware; revisit if a storage controller is fitted. |
| EDTASM $A400-$B0FF | **Keep (provisional)** | Test serial, BIOS calls, RAM/workspace usage. |
| Visual/02 $B100-$C1FF | **Defer, reserve in first image** | Pinned Asm/02 crashes on Visual/02 in CI; keep all upstream source/history and restore in an optional build after investigating toolchain. |
| rc/BASIC L2 $C200-$DBFF | **Keep (provisional)** | Test initialization, program space and terminal. |
| rc/Forth $DC00-$EFFF | **Omit, reserve** | Frees 5120 bytes for Netronics software; consider separately selectable Forth build later. |
| XMODEM $F000-$F2FF | **Keep (provisional)** | Transfer utility useful with serial; cassette entry conflict requires Tiny BASIC call remapping. |
| BIOS/EBIOS $F300-$FFFF | **AVI Q/EF and CDP1854 backend port** | Replaces active 8250 driver with mode-1 polling CDP1854 backend; disabled storage/NVR vectors remain ABI placeholders. UART electrical/jumper behavior requires bench verification. |
| CDP1861 PIXIE | **Disable at build stage** | Enable after UART/PIXIE coexistence strategy and video verification. |
| Netronics Tiny BASIC | **Planned, not yet imported** | Confirm provenance/build then copy $DC00-$E9AF ROM payload into low RAM $0000-$0DAF. |
| Hyperboard cassette | **Planned, not yet implemented** | Determine electrical polarity, timing, and assigned EF/Q before coding. |
| NCE/NCA | **Investigate only** | Original program binaries/provenance not yet authenticated. |

The selection is explicitly provisional and does not close the outstanding owner review. There is no code to launch Tiny BASIC or drive Hyperboard cassette yet.

## 32 KiB address allocations

| 1802 logical address | Size | Purpose |
| --- | ---: | --- |
| $8000-$97FF | 6144 B | Monitor |
| $9800-$A0FF | 2304 B | AVI help |
| $A100-$A3FF | 768 B | Reserved, SEDIT removed |
| $A400-$B0FF | 3328 B | EDTASM |
| $B100-$C1FF | 4352 B | Reserved until Visual/02 assembler is repaired |
| $C200-$DBFF | 6656 B | rc/BASIC |
| $DC00-$E9AF | 3504 B | Reserved Tiny BASIC payload |
| $E9B0-$E9FF | 80 B | Reserved alignment |
| $EA00-$EBFF | 512 B | Proposed Tiny BASIC launcher budget |
| $EC00-$EFFF | 1024 B | Proposed cassette/AVI helper budget |
| $F000-$F2FF | 768 B | XMODEM |
| $F300-$FFFF | 3328 B | BIOS/EBIOS |

The new HEX image represents physical ROM offsets $0000-$7FFF corresponding to logical $8000-$FFFF. The two reserved regions must contain FF bytes until intentionally populated.

## Hardware audit: inherited assumptions

This is a **source-level risk inventory**, not an assertion of hardware compatibility.

- **Temporary compile compatibility:** boots.asm and Riley sources depend on the existing ELF2K conditional definitions. The Makefile passes both AVIELF2 and ELF2K to the assemblers only when PLATFORM=AVIElf2. This unblocks the *build*, not the *hardware port*.
- **Monitor POST and front panel:** BOOTS uses port 4 for the LED display and reads SWITCHES at port 4. Verify the selected Hyperboard/AVI front-panel decoding and jumper configuration before assuming behavior.
- **NVR/RTC:** BOOTS startup includes NVR reset/probe and RTC ticking/battery checks (legacy POST codes 76/75/74); runtime uses F_RTCTEST, F_RDNVR and SET RESTART/NVR operations. BIOS must be audited for absence of DS1287-family hardware.
- **Legacy UART:** BOOTS includes 8250/16450/16550 loopback initialization (legacy POST codes 69/68/67/65/64/63/60), UART register selection, and baud restoration. These cannot be pointed at CDP1854 registers.
- **IDE/bootstrap:** BOOTS contains IDE probing/BOOT-from-disk, and SEDIT assumes a disk controller. Omission of SEDIT does NOT eliminate IDE code in the inherited monitor or BIOS.
- **Other legacy paths:** conditional PS/2, VT1802 CRT, GPIO/speaker, and Elf2K-specific switch test paths require explicit removal or gating. PIXIE video is disabled for the first scaffold rather than assuming a tested DMA/console combination.
- **BIOS contract:** retain stable service entry points for monitor, EDTASM, BASIC and XMODEM; restore Visual/02 service integration later while replacing the hardware-specific terminal backend.

## Hyperboard facts and bench-verification blockers

The supplied Rev.2 schematic identifies an A3 CDP1854 UART on COM2, an A14 CDP1863 baud-rate generator, and J10 TCLK / J11 RCLK selection, plus COM2_RX, COM2_TX, COM2_CTS, COM2_RTS and COM2_CD nets. Those labels do **not by themselves** prove a software I/O port map or selected board jumper configuration.

The first native CDP1854 driver has been coded as an **opt-in experimental path**, based on the Rev.2 schematic and period datasheet: INP/OUT 2 data, INP/OUT 3 status/control, OUT 5 CDP1863 programming via J3=I65, control $19 then $99 (8N1, TR on, interrupts off). The assembled board's J3/J10/J11/J14 positions, CS2 decode, 2.4576 MHz clock selection and 153.6 kHz x16 clocks, CTS behavior and COM2 TTL wiring still need actual measurements. See [AVI_FIRST_BENCH_TEST.md](AVI_FIRST_BENCH_TEST.md). Do NOT substitute 8250 register semantics for the CDP1854.

Hyperboard CASS_IN / CASS_OUT also need polarity, EF/Q assignment, encoding, and timing validation. Original Netronics Tiny BASIC's $F065 and $F0BA cassette calls fall *inside XMODEM* here; any payload must be rebuilt/patched to point at future AVI cassette primitives. Do not copy the Giant Board ROM there.

## Reproducible build and validation

From the repository root:

    bash sw/build/build-avi.sh

Output: .build/avi-rom/work/AVIElf2.hex (never overwrites sw/Elf2K*.hex or sw/PicoElf.hex).

The separate CI job builds into avi-pass1 and avi-pass2; uses pinned dependencies; checks both image runs through verify-avi.py; requires identical HEX outputs; and uploads development files. verify-avi.py independently verifies Intel HEX record checksums, exact 32 KiB record coverage, disjoint required active/reserved spans, all-FF reserved space, four STG ROM checksum/correction bytes, and the completed ROM's 16-bit checksum. The expected checksum is derived from **this image**, not forced to match historical F0CB.

**Pass/fail build validation is not functional acceptance.** Startup's unsupported hardware probes have been bypassed in the AVI-only build. The Q/EF3 fallback and the CDP1854 polling backend are implemented, but physical boot/COM2/PIXIE tests still await the owner's bench results. Tiny BASIC and cassette remain separate future milestones.

**No merge is authorized.** The owner may burn a **spare test EEPROM** under the experimental bench procedure; the system has not yet passed physical hardware tests.


## CI toolchain blocker recorded

The stock-rebuild helper now passes Forth source normalization, but the pinned historical Asm/02 crashes compiling Visual/02 on the current GitHub runner. For the first AVI development image only, Visual/02 is temporarily omitted and its 4352-byte region reserved FF. This does not change the stock configuration, baseline ROM, Visual/02 sources or the owner selection review. Stock rebuild CI may remain red until Asm/02 is repaired; the AVI CI is a distinct check. Do not present those failures as a loss of stock image/artifact preservation.

## 2026-10-12 bench-test UART milestone

New AVI-only files: `sw/build/avi-port.py` applies guarded transformations to disposable monitor/BIOS copies, `sw/avi-cdp1854.asm` is the distinct CDP1854 polling backend, and `docs/AVI_FIRST_BENCH_TEST.md` records wiring and EEPROM tests. The stock alternate, original BIOS sources, and old ROM checksum F0CB remain intact.

After RESET the monitor starts Q/EF3 autobaud. `UART` initializes CDP1863/CDP1854 for *provisional* COM2 9600 baud 8-N-1 and changes BIOS terminal I/O to mode-1 hardware UART. A RESET returns to Q/EF3 even when COM2 is mis-strapped. The native backend is NOT an 8250 emulation and does not use UART interrupts. `SHOW EF`, `HELP`, `EXAMINE`, `DEPOSIT`, `BASIC`, `ASM`, and XMODEM remain available subject to real-machine validation. Legacy IDE/RTC/NVR commands are removed from the AVI monitor dispatcher; functions still present but unreachable in legacy blobs must not be treated as tested. All source-level replacements are isolated to disposable build workspace.

The validator now checks the AVI monitor signature, UART command table presence, and mode-1 register sequence in addition to full-size checksums, ROM address ranges and two-run determinism. These are *static smoke checks only*. No physical CPU/Hyperboard emulator acceptance test has yet been run and no sustained PIXIE DMA/serial-coexistence measurement is available.
