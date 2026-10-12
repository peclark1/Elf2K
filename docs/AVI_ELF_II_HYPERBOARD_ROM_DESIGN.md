# AVI ELF II / Hyperboard ROM Design

Status: Initial design draft  
Target hardware: AVI ELF II with AVI Hyperboard  
Base firmware: Spare Time Gizmos Elf2K ROM sources in `sw/`

This is a living design document for a custom 32 KiB ROM image tailored to the AVI ELF II + Hyperboard. The intent is to preserve the useful parts of the Elf2K firmware while removing or replacing Elf2K-specific functions that do not match the AVI hardware, and to use the recovered ROM space for software that is more useful or historically appropriate on an ELF II.

## 1. Goals

The ROM should:

- Boot reliably from the Hyperboard's normal 32 KiB ROM mapping at `$8000-$FFFF`.
- Retain the useful Elf2K monitor/debugger environment and serial console support.
- Prefer the Hyperboard CDP1854 hardware UART as the normal AVI console, while retaining the Q/EF bit-banged serial path as an optional compatibility/fallback mode.
- Keep the ROM build reproducible from source.
- Prefer software that is useful on the actual AVI ELF II / Hyperboard hardware.
- Add historically appropriate ELF II software where practical.
- Provide a clean path from the monitor into resident languages and utilities.
- Make use of the Hyperboard cassette hardware, ideally including BASIC program save/load.
- Preserve compatibility with the CDP1802 and the machine's approximately 1.79 MHz CPU clock.
- Avoid consuming low RAM permanently for ROM-resident tools; load RAM-based software only when invoked.

## 2. Hardware assumptions

### Confirmed for the current machine

- CPU: RCA CDP1802.
- Hyperboard normal memory map:
  - `$0000-$7FFF`: 32 KiB RAM.
  - `$8000-$FFFF`: 32 KiB ROM.
- The current Elf2K alternate image boots and runs from `$8000`.
- The current ROM image passes the Elf2K full-ROM checksum repeatedly with checksum `F0CB` when programmed into a known-good EEPROM.
- Hyperboard SRAM has passed sustained checksum testing.
- Hyperboard serial console operation is working. The currently proven Elf2K console path is the Q/EF bit-banged interface at 2400 baud.
- The Hyperboard provides a CDP1854 hardware UART (COM2) and CDP1863 programmable baud-rate generator.
- With the current bit-banged console, enabling the CDP1861/PIXIE causes serial corruption; the working hypothesis is that PIXIE DMA steals enough CPU timing to disturb software-generated serial bit timing.
- The Hyperboard provides cassette input/output circuitry (`CASS_IN` and `CASS_OUT`).
- CDP1861 PIXIE support is physically available on the AVI ELF II, although video debugging is still in progress.

### To verify before finalizing the ROM

- Exact cassette input/output polarity and EF/Q assignments used by the Hyperboard.
- Exact Hyperboard CDP1854 register/port selects, status wiring, and CDP1863 baud-rate programming as strapped on the assembled board. The classic CDP1854/CDP1863 I/O convention is a useful lead but must be verified before it is encoded in firmware.
- Whether any current Elf2K startup tests or device initialization touch hardware that is absent on the AVI system.
- Whether the final ROM should assume a CDP1861 is always fitted or make PIXIE support optional.

## 3. AVI serial-console architecture

The AVI-specific ROM should use the Hyperboard's **CDP1854 hardware UART** as
its preferred console rather than depending on cycle-counted Q/EF serial.

This is an architectural choice, not a change to the stock Elf2K
configuration. The stock build must remain reproducible and unchanged.

### Rationale

The current bit-banged console works reliably by itself, but CDP1861 DMA and
interrupt activity can stretch the software serial timing enough to corrupt
characters. A CDP1854 shifts the serial bits using hardware clocks, so PIXIE
DMA no longer directly changes individual bit widths. It also makes baud rates
above the presently used 2400 baud practical.

The CDP1854 has no deep receive FIFO, so this does **not** guarantee that every
high baud rate will coexist with heavy PIXIE activity. The CPU still has to
service received characters before overrun. The initial design should
therefore use polling and conservative rates, then measure the real machine.

### Integration strategy

Do not rewrite the monitor's console-facing code. The Elf2K firmware already
has a useful abstraction in which monitor and applications call BIOS terminal
and input services while the low-level implementation selects a console
backend. Preserve that structure and add an AVI-specific CDP1854/CDP1863
backend underneath it.

The existing Elf2K "hardware UART" code targets an 8250/16450/16550-style
register-select/data interface. The CDP1854 is a different device and should
not be made to masquerade as an 8250. The AVI configuration should provide
its own low-level initialize, status, receive, transmit, and baud-rate
routines.

The first AVI implementation should:

- initialize the CDP1854 in its CDP1800-series interface mode;
- program the Hyperboard CDP1863/divider path for the requested baud rate;
- use the hardware UART for the normal console;
- retain the Q/EF bit-banged driver as an explicit fallback/diagnostic option;
- begin with 9600 baud, 8-N-1, then test 19200 and higher rates only after
  9600 is reliable with PIXIE active;
- avoid UART interrupts initially; polling keeps the first implementation
  small and minimizes interaction with the CDP1861 interrupt/DMA path.

The schematic and period CDP1854/CDP1863 examples suggest a compact COSMAC
I/O mapping (commonly separate data and status/control ports plus a baud
generator load port). The exact Hyperboard port numbers and any EF/status
jumper selections remain a **bench-verification item** before code is written.

### Required coexistence test

A successful AVI console implementation is not merely "terminal output works."
The acceptance test must run sustained transmit and receive traffic while the
CDP1861 is enabled and continuously performing display DMA. There should be
no character corruption at the selected default baud rate and no UART
overrun during normal monitor use.

## 4. Current Elf2K alternate ROM layout

The current `sw/config.Elf2K-alternate` configuration uses the 32 KiB ROM as follows:

| Address range | Size | Component |
| --- | ---: | --- |
| `$8000-$97FF` | 6144 bytes | Elf2K monitor / BOOTS |
| `$9800-$A0FF` | 2304 bytes | HELP |
| `$A100-$A3FF` | 768 bytes | SEDIT |
| `$A400-$B0FF` | 3328 bytes | EDTASM |
| `$B100-$C1FF` | 4352 bytes | Visual/02 |
| `$C200-$DBFF` | 6656 bytes | rc/BASIC Level 2 |
| `$DC00-$EFFF` | 5120 bytes | rc/Forth |
| `$F000-$F2FF` | 768 bytes | XMODEM |
| `$F300-$FFFF` | 3328 bytes | extended BIOS / BIOS |

The alternate image already omits the Elf2K VT1802 video-card firmware.

## 5. Component policy

### Likely keep

- Elf2K monitor / BOOTS
- HELP, rewritten for the AVI-specific command set
- EDTASM, if it remains useful and builds cleanly
- Visual/02
- rc/BASIC Level 2
- XMODEM, because serial transfer is useful on the Hyperboard
- BIOS routines needed by the monitor and retained applications

### Candidates for removal or replacement

These should be audited before being removed:

- SEDIT: intended for disk-sector access; likely not useful without the Elf2K IDE/storage hardware.
- rc/Forth: useful software, but its 5 KiB allocation is attractive space for AVI/ELF II-specific additions.
- Elf2K-specific startup/diagnostic code for hardware not present on the AVI system.
- Any BIOS support used only by omitted Elf2K peripherals.

Removing Forth alone frees 5120 bytes. Removing SEDIT as well would free another 768 bytes.

## 6. Netronics ELF II Tiny BASIC

Adding the reconstructed Netronics ELF II Tiny BASIC is a primary design goal.

The recovered source in the Emma 02 project identifies itself as a reconstruction of Netronics Tiny BASIC for the ELF II and states that it:

- is designed to run in RAM starting at `$0000`;
- expects the Giant Board / ROM monitor for cassette `LOAD` and `SAVE`;
- includes PIXIE/keyboard and serial-oriented I/O paths.

The assembled image occupies approximately:

- code/data image: `$0000-$0DAF` (3504 bytes);
- display/work area beginning at `$0DB0`;
- BASIC program space beginning at `$0F40`;
- configured stack top: `$3FF7`.

This is a good match for the Hyperboard's 32 KiB low RAM.

### Proposed integration method

Do not relocate Tiny BASIC to execute directly from high ROM.

Instead:

1. Store a Tiny BASIC payload in unused high-ROM space.
2. Add a monitor command such as:
   - `TBASIC`
3. The command copies the Tiny BASIC image from ROM to RAM `$0000-$0DAF`.
4. Initialize any required RAM state.
5. Transfer execution to Tiny BASIC at `$0000`.

This preserves the program's original low-memory assumptions and avoids a large relocation effort.

### Return-to-monitor handling

The reconstructed source currently defines the Giant Board monitor at `$F000`. For the AVI ROM we should provide a deliberate return path to the Elf2K monitor instead of depending on the Giant Board monitor.

Preferred options, in order:

1. Rebuild Tiny BASIC with its monitor-return address changed to the Elf2K warm-start entry.
2. Patch the copied RAM image during the build if rebuilding the source is inconvenient.
3. Provide a compatibility trampoline only if the first two approaches prove impractical.

The return path should not require rebooting the machine.

## 7. Tiny BASIC cassette support

This is especially promising because Tiny BASIC already contains user-visible `SAVE` and `LOAD` commands.

The recovered Tiny BASIC code makes hard-coded calls into the original 256-byte Giant Board monitor ROM:

- cassette save primitive: `$F065`
- cassette load primitive: `$F0BA`

The original Giant Board monitor occupies `$F000-$F0FF`.

### Conflict with the current Elf2K ROM

The Elf2K alternate image currently places XMODEM at `$F000-$F2FF`, so the original Giant Board ROM cannot simply be dropped into its historical location without displacing XMODEM.

### Design options

#### Option A - AVI cassette compatibility routines

Implement Giant-Board-compatible cassette primitives at new ROM addresses and modify/rebuild Tiny BASIC to call those addresses.

Advantages:

- Keeps XMODEM where it is.
- Uses only the cassette routines we need.
- Lets the routines be written specifically for the Hyperboard cassette hardware.
- Avoids carrying an entire second monitor.

This is the preferred long-term approach.

#### Option B - relocate XMODEM and reserve `$F000-$F0FF`

Place the original Giant Board ROM at its historical address and move XMODEM elsewhere.

Advantages:

- Maximum compatibility with unmodified Netronics Tiny BASIC.

Risks:

- XMODEM and other components may not be trivially relocatable because 1802 short branches are page-sensitive.
- Consumes scarce ROM space with Giant Board monitor functions that overlap the Elf2K monitor.

#### Option C - compatibility trampolines at the historical entry points

Reserve enough of `$F000` to provide entry stubs at `$F065` and `$F0BA` that transfer to AVI-specific cassette routines elsewhere.

This may preserve an almost-unmodified Tiny BASIC image, but it still conflicts with the current XMODEM placement and would require careful layout work.

## 8. Proposed first ROM layout experiment

The initial implementation should minimize changes to known-good Elf2K code.

A reasonable first experiment is:

- keep BOOTS, HELP, EDTASM, Visual/02, rc/BASIC, XMODEM, and BIOS at their existing addresses;
- remove Forth;
- initially remove SEDIT if its hardware dependencies are confirmed irrelevant;
- allocate part of the freed `$DC00-$EFFF` area to:
  - Tiny BASIC payload;
  - `TBASIC` loader/launcher;
  - AVI-specific helper routines;
  - future cassette routines.

The 3504-byte Tiny BASIC payload fits inside the 5120 bytes freed by Forth, leaving about 1616 bytes before considering any additional space recovered from SEDIT or other Elf2K-only code.

Exact addresses should not be committed until the stock build can be reproduced and the assembler's page-boundary constraints have been checked.

## 9. Proposed monitor commands

Initial command ideas:

| Command | Purpose | Status |
| --- | --- | --- |
| `BASIC [NEW|OLD]` | Existing rc/BASIC Level 2 | Existing |
| `TBASIC` | Load and start Netronics Tiny BASIC in low RAM | Proposed |
| `ASM [NEW|OLD]` | Existing editor/assembler | Existing |
| `VISUAL` | Existing Visual/02 debugger | Existing |
| `XMODEM` | Existing serial transfer support | Existing |
| `CASSAVE` | Save an arbitrary RAM range using Hyperboard cassette output | Future |
| `CASLOAD` | Load cassette data into RAM | Future |
| `PIXIE` | AVI-specific CDP1861 diagnostics/demo launcher | Future |

Tiny BASIC's own `SAVE` and `LOAD` commands should ultimately call the same cassette primitives used by monitor-level cassette commands.

## 10. Build strategy

Before modifying functionality, establish a reproducible build of the stock Elf2K alternate ROM.

### Phase 1 - reproduce upstream

- Build the unmodified `Elf2K-alternate.hex`.
- Compare resulting layout and checksum against the repository image.
- Record all required assembler/tool versions.
- Eliminate machine-specific hard-coded paths from the Makefile where practical.

The upstream `sw/readme.txt` notes that the ROM combines multiple independently maintained components. Some Michael Riley sources and assembler tools are not included directly in the Elf2K repository, so our fork should document exactly which external sources and versions are required.

### Phase 2 - create an AVI configuration

Add an AVI-specific configuration rather than modifying `config.Elf2K-alternate` in place. Candidate names:

- `config.AVIElf2`
- output image `AVIElf2.hex`

The original Elf2K and Elf2K-alternate configurations should remain buildable.

### Phase 3 - remove unsupported components

Audit each component and hardware dependency before removal. Rebuild after each change and verify the ROM on real hardware.

### Phase 4 - add Tiny BASIC loader

- Add payload to the ROM merge process.
- Add `TBASIC` monitor command.
- Copy payload into low RAM.
- Start Tiny BASIC.
- Establish clean return to the Elf2K monitor.

### Phase 5 - cassette support

- Verify Hyperboard cassette signal behavior.
- Implement cassette primitives.
- Test monitor-level cassette save/load with known byte patterns.
- Connect Tiny BASIC `SAVE` and `LOAD` to those primitives.
- Test with both a real recorder and captured WAV/audio files if convenient.

## 11. Verification plan

Every ROM revision should be tested in layers:

1. Build succeeds with a documented toolchain.
2. ROM image is exactly 32 KiB and passes the expected image checksum process.
3. EEPROM programmer verify passes.
4. ELF boots cleanly to the monitor.
5. Repeated full-ROM checksum is stable.
6. RAM test remains stable.
7. CDP1854 hardware-UART console works at 9600 baud with PIXIE disabled.
8. Sustained CDP1854 transmit/receive remains clean with PIXIE display DMA active.
9. Bit-banged serial remains available as a fallback/diagnostic path.
10. Existing retained languages/utilities launch and return correctly.
11. `TBASIC` loads correctly into RAM.
12. Tiny BASIC can enter, list, and run a small program.
13. Tiny BASIC can return to the Elf2K monitor.
14. Cassette save/load round trip succeeds once implemented.
15. PIXIE behavior is retested after the separate hardware video problem is resolved.

## 12. Source/provenance notes

Before importing third-party source into this repository, confirm copyright and redistribution terms for each component.

Relevant upstream/source locations currently include:

- Spare Time Gizmos Elf2K: this repository's upstream.
- Michael H. Riley's rc/BASIC, BIOS, EDTASM, Visual/02, and related 1802 software.
- Netronics Tiny BASIC reconstruction in the Emma 02 project:
  - `data/Elf/Netronics Tiny Basic/Tinybasi.asm`
  - `data/Elf/Netronics Tiny Basic/TINYBASI.LST`
  - `data/Elf/Netronics Tiny Basic/NTBManual.txt`
- Original Giant Board monitor image in Emma 02:
  - `data/NetronicsElfII/giantboard.hex`

Do not import binaries or source solely because they are technically useful; preserve provenance and licensing information.

## Historical Netronics software: NCE and NCA

The 1979 *Netronics Cassette Text Editor* user manual (23-page scan held in
the restoration project's sources) describes two distinct original ELF II
programs:

- **NCE** (Netronics Cassette Editor): interactive terminal editor for text
  and COSMAC assembly source; search, substitute, insert, delete, save/get,
  composite/nested commands and cassette input/output.
- **NCA** (Netronics Cassette Assembler): converts source files to machine
  code, originally using the cassette workflow.

### Documented hardware and memory constraints

- The editor is loaded at **$0000-$0FFF** (4 KiB) and ordinarily needs at
  least another 4 KiB for text/work space. The manual recommends 8 KiB RAM.
- Original I/O supports a serial terminal with first-character baud timing,
  rather than an initialized CDP1854 hardware UART.
- Original file I/O expects cassette audio and a *two-recorder* tape-control
  interface. The Hyperboard provides cassette signals but the two-deck
  transport-control hardware has **not** been established.
- The editor's **U** command returns to the original ELF II monitor and must
  be redirected to the custom ROM's monitor/warm-start path.

### Proposed integration

Treat NCE and NCA as **optional, historically authentic ROM-stored RAM
payloads**, analogous to the Netronics Tiny BASIC loader. Do not assume
that the original 4 KiB NCE executable can execute directly from high ROM:
locate a genuine cassette capture or machine-code listing first, establish
its precise byte length, load and entry points, writable locations, and
dependencies. If available, store a documented payload in high ROM and
copy to low RAM on `NCE` (and later `NCA`) monitor commands.

Patch or adapt the serial interface to use the CDP1854 BIOS console.
Design cassette compatibility independently from the ROM image: first test
editor buffer operations over serial, then tape operations. Support a
non-destructive path back to the resident monitor. Maintain license and
provenance records before incorporating third-party binaries.

**Important:** the manual is *documentation*, not the executable or source.
No genuine NCE/NCA binary has been recovered or verified yet. The known
Emma 02 `data/NetronicsElfII/` archive contains Giant Board monitor and
other ROM images, but does not establish the availability of NCE/NCA. Avoid
treating its `vt100.bin` or BASIC III ROM as an editor image.

### ROM-capacity trade-off

The stock 32 KiB alternate ROM map is fully allocated. Removing 5 KiB Forth
can make room for Tiny BASIC (~3504 bytes) **or** a ~4 KiB NCE payload, not
both without additional space recovery. SEDIT's 768 bytes alone does not
solve that shortfall. Consider separately selectable build configurations
or further audits of Elf2K-only components before promising both in one
ROM. Do not alter stock `config.Elf2K-alternate`.

### Acceptance milestones

1. Locate and authenticate the original editor and assembler programs.
2. Confirm exact payload sizes, entry points, and ROM/RAM relocation behavior.
3. Launch original editor from monitor in RAM with CDP1854 terminal I/O.
4. Exercise insert/type/search/substitute and return to monitor.
5. Verify cassette transfer or explicitly document any unsupported
   original dual-transport commands.
6. Add original assembler only after independent image/provenance validation.

## 13. Open questions

- Which Elf2K monitor/BIOS routines are truly hardware-neutral, and which assume Elf2K-specific peripherals?
- What are the exact CDP1854 data/status/control port selects and CDP1863 baud programming values on the assembled Hyperboard?
- What is the highest CDP1854 baud rate that remains loss-free during continuous CDP1861 display DMA?
- Is SEDIT completely unusable on the Hyperboard, or could it be repurposed for another block device later?
- Should Forth be omitted permanently, or made an alternate ROM build option?
- Can XMODEM remain at `$F000` while Tiny BASIC cassette calls are redirected elsewhere?
- What exact signals and timing do the Giant Board cassette routines at `$F065` and `$F0BA` expect?
- Does the Hyperboard cassette circuit intentionally reproduce the Giant Board interface closely enough that those algorithms can be reused nearly unchanged?
- Should the ROM support both CDP1861/PIXIE and a serial-only configuration?
- Should the monitor expose a general-purpose application/payload loader abstraction so other RAM-resident ELF software can be added later without writing a new command each time?
- Can the build be modernized enough to run reproducibly on current Linux while still generating an image identical to the historical/upstream build?

## 14. Near-term next steps

1. Get the unmodified upstream `Elf2K-alternate.hex` building from this fork.
2. Record the toolchain and missing external source dependencies.
3. Create the AVI-specific configuration without changing the stock configurations.
4. Audit the existing monitor and BIOS for Elf2K-specific hardware assumptions.
5. Decide the first freed ROM region.
6. Add a minimal `TBASIC` loader before changing cassette support.
7. Once Tiny BASIC runs reliably, analyze the Giant Board cassette routines and implement the Hyperboard-compatible save/load path.


## 15. Current AVI-specific implementation milestone

As reassessed by the owner/coordinator on 2026-10-12, historical stock ROM byte-for-byte reconstruction is not a dependency of the custom AVI image. The first distinct configuration is `sw/config.AVIElf2`, producing `AVIElf2.hex` through an isolated pinned Linux build. The initial component selection, allocation, remaining hardware risks, and deterministic CI verification are maintained in [AVI_ROM_IMPLEMENTATION_STATUS.md](AVI_ROM_IMPLEMENTATION_STATUS.md). This first image is explicitly build-only, retaining temporary Elf2K monitor/BIOS conditional compatibility; it is not a CDP1854 port and is not EEPROM-ready. No merge is authorized.
