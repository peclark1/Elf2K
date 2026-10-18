# Task: Review ROM software together before finalizing AVI ROM layout

**Status:** OPEN — awaiting joint review and decisions  
**Priority:** Before approving final hardware ROM selection (not a blocker for a preliminary AVI build)  
**Parent design:** [AVI ELF II Hyperboard ROM Design](AVI_ELF_II_HYPERBOARD_ROM_DESIGN.md)

## Goal

Review **each component** of the currently working Elf2K-alternate ROM together with the user. Explain what each program does, its practical usefulness on the AVI ELF II and Hyperboard, its hardware dependencies and approximate ROM footprint. Decide what to **KEEP**, **REMOVE**, **REPLACE**, **MAKE OPTIONAL**, or **INVESTIGATE**; record the decision and the reasoning. Do not silently make these decisions.

This is a **review and prioritization task**, not permission to modify or remove stock firmware.

## Current Elf2K-alternate ROM inventory and decisions

| Existing component | Address range | Allocation | Joint decision | Notes |
| --- | --- | ---: | --- | --- |
| Elf2K monitor / BOOTS | $8000-$97FF | 6144 B | **Pending** | Review monitor/diagnostic functions |
| HELP | $9800-$A0FF | 2304 B | **Pending** | Rewrite or reduce for final commands |
| SEDIT disk-sector editor | $A100-$A3FF | 768 B | **Pending** | Audit absent Elf2K disk hardware |
| Michael Riley EDTASM | $A400-$B0FF | 3328 B | **Pending** | Compare to authentic Netronics NCE/NCA |
| Visual/02 debugger | $B100-$C1FF | 4352 B | **Pending** | Determine actual usefulness |
| rc/BASIC Level 2 | $C200-$DBFF | 6656 B | **Pending** | Compare with Netronics Tiny BASIC |
| rc/Forth | $DC00-$EFFF | 5120 B | **Pending** | Possible optional build |
| XMODEM | $F000-$F2FF | 768 B | **Pending** | Valuable with hardware UART |
| BIOS / extended BIOS | $F300-$FFFF | 3328 B | **Pending** | Retain necessary shared services |

## New / replacement software candidates

| Candidate | Known footprint | Joint decision | Open dependency |
| --- | --- | --- | --- |
| Netronics ELF II Tiny BASIC | ~3504-byte RAM payload | **Pending** | Verify image and ROM loader |
| Original Netronics Cassette Editor (NCE) | 4 KiB RAM program per 1979 manual | **Pending** | Recover authentic cassette image / source; adapt serial and cassette |
| Original Netronics Cassette Assembler (NCA) | Unverified | **Pending** | Recover authentic executable / source and determine size |
| CDP1854/CDP1863 serial-console backend | TBD | **Pending** | Confirm Hyperboard port decoding and baud settings |
| Cassette routines / utilities | TBD | **Pending** | Confirm I/O, encoding and transport compatibility |
| Tiny BASIC launcher, other ROM commands | TBD | **Pending** | Design and measure build footprint |

## Review session procedure

1. Go through every existing ROM component in the table individually, describing what it does and concrete ways it would be used on the real ELF II.
2. For each, discuss user preference, actual hardware suitability, and overlapping functionality. Record an explicit choice and rationale.
3. Review original Netronics programs separately; distinguish *documented* software from binaries/sources actually recovered.
4. Add up the total bytes recovered and required, respecting the 32 KiB ROM limit, placement constraints, and page-sensitive 1802 branches.
5. Agree on a primary ROM contents list and optional alternate ROM variants if necessary.
6. Update this table and design with final agreed decisions before hardware ROM approval. A preliminary independent `config.AVIElf2` may be built earlier with explicit provisional choices.

**Hard constraints:** Preserve `config.Elf2K-alternate` and the verified stock `Elf2K-alternate.hex` checksum `F0CB`. No software is removed without a joint decision.

## Completion criteria

- [ ] All nine stock ROM components explicitly reviewed
- [ ] Each has a recorded decision and rationale
- [ ] Original Netronics software candidates considered with provenance status
- [ ] ROM-space budget and optional variants agreed
- [ ] Final software selection documented and approved by the user


## 2026-10-12 revised priority

The owner/coordinator has explicitly authorized the independent `config.AVIElf2`/`AVIElf2.hex` development milestone without requiring historical stock byte matching or first completing the joint selection review. The first AVI layout provisionally retains monitor, HELP, EDTASM, Visual/02, rc/BASIC, XMODEM and BIOS, and reserves the SEDIT and Forth allocations. These are **provisional AVI-only implementation selections, not final component decisions**. All stock configurations, images and historical artifacts remain untouched. See [AVI_ROM_IMPLEMENTATION_STATUS.md](AVI_ROM_IMPLEMENTATION_STATUS.md). Do not merge or program an EEPROM without authorization.
