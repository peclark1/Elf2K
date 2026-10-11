# AVI ELF II / Hyperboard ROM Design

Status: Initial design draft  
Target hardware: AVI ELF II with AVI Hyperboard  
Base firmware: Spare Time Gizmos Elf2K ROM sources in `sw/`

This is a living design document for a custom 32 KiB ROM image tailored to the AVI ELF II + Hyperboard. The intent is to preserve the useful parts of the Elf2K firmware while removing or replacing Elf2K-specific functions that do not match the AVI hardware, and to use the recovered ROM space for software that is more useful or historically appropriate on an ELF II.

## 1. Goals

The ROM should:

- Boot reliably from the Hyperboard's normal 32 KiB ROM mapping at `$8000-$FFFF`.
- Retain the useful Elf2K monitor/debugger environment and serial console support.
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
- Hyperboard serial console operation is working.
- The Hyperboard provides cassette input/output circuitry (`CASS_IN` and `CASS_OUT`).
- CDP1861 PIXIE support is physically available on the AVI ELF II, although video debugging is still in progress.

### To verify before finalizing the ROM

- Exact cassette input/output polarity and EF/Q assignments used by the Hyperboard.
- Which Elf2K BIOS routines map cleanly to the CDP1854 UART implementation on the Hyperboard.
- Whether any current Elf2K startup tests or device initialization touch hardware that is absent on the AVI system.
- Whether the final ROM should assume a CDP1861 is always fitted or make PIXIE support optional.

## 3. Current Elf2K alternate ROM layout

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

## 4. Component policy

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

## 5. Netronics ELF II Tiny BASIC

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

## 6. Tiny BASIC cassette support

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

## 7. Proposed first ROM layout experiment

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

## 8. Proposed monitor commands

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

## 9. Build strategy

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

## 10. Verification plan

Every ROM revision should be tested in layers:

1. Build succeeds with a documented toolchain.
2. ROM image is exactly 32 KiB and passes the expected image checksum process.
3. EEPROM programmer verify passes.
4. ELF boots cleanly to the monitor.
5. Repeated full-ROM checksum is stable.
6. RAM test remains stable.
7. Serial console commands work.
8. Existing retained languages/utilities launch and return correctly.
9. `TBASIC` loads correctly into RAM.
10. Tiny BASIC can enter, list, and run a small program.
11. Tiny BASIC can return to the Elf2K monitor.
12. Cassette save/load round trip succeeds once implemented.
13. PIXIE behavior is retested after the separate hardware video problem is resolved.

## 11. Source/provenance notes

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

## 12. Open questions

- Which Elf2K monitor/BIOS routines are truly hardware-neutral, and which assume Elf2K-specific peripherals?
- Is SEDIT completely unusable on the Hyperboard, or could it be repurposed for another block device later?
- Should Forth be omitted permanently, or made an alternate ROM build option?
- Can XMODEM remain at `$F000` while Tiny BASIC cassette calls are redirected elsewhere?
- What exact signals and timing do the Giant Board cassette routines at `$F065` and `$F0BA` expect?
- Does the Hyperboard cassette circuit intentionally reproduce the Giant Board interface closely enough that those algorithms can be reused nearly unchanged?
- Should the ROM support both CDP1861/PIXIE and a serial-only configuration?
- Should the monitor expose a general-purpose application/payload loader abstraction so other RAM-resident ELF software can be added later without writing a new command each time?
- Can the build be modernized enough to run reproducibly on current Linux while still generating an image identical to the historical/upstream build?

## 13. Near-term next steps

1. Get the unmodified upstream `Elf2K-alternate.hex` building from this fork.
2. Record the toolchain and missing external source dependencies.
3. Create the AVI-specific configuration without changing the stock configurations.
4. Audit the existing monitor and BIOS for Elf2K-specific hardware assumptions.
5. Decide the first freed ROM region.
6. Add a minimal `TBASIC` loader before changing cassette support.
7. Once Tiny BASIC runs reliably, analyze the Giant Board cassette routines and implement the Hyperboard-compatible save/load path.
