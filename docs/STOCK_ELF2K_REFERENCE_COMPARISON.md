# Stock Elf2K alternate ROM — reproducible build and reference-image forensics

Date: 2026-10-12. Branch: \`fix/stock-elf2k-build\`.

## Objective and acceptance gate

Rebuild exactly the original unmodified \`sw/Elf2K-alternate.hex\` (the
stock alternate 27C256 image) from its original component set. All build
source preparation occurs in disposable \`.build/\` directories. **Neither
tracked stock source/configuration files nor the tracked reference HEX
have been modified or replaced.** No firmware component has been removed,
substituted or omitted to improve the comparison.

The reference is protected in \`sw/build/reproduce-stock.sh\` by:

- Git object ID: \`e1a14af17671dae2b051b53a7ae186d639e7f5b9\`
- Reference Intel HEX SHA-256:
  \`db8d5148b7cb507613a20b28dc31abfce1b1f500cb69a8c2e348cfaea2ab6a4b\`
- Reference decoded 32 KiB SHA-256:
  \`842aa3f4a84d7755dcfadfadaeaa7968e99dde2a9eb9adfda41711d8929c2dad\`
- Reference stored/whole-image checksum16: \`F0CB\`

Current build environment pins all eight external tool/source repositories
in \`sw/build/prepare-deps.sh\`. There are 22 passing source-preparation
regression tests (GitHub Actions run 38275364302).

## Confirmed progress

On Ubuntu 24.04 CI, the build assembles the exact nine stock components:
monitor, help, SEDIT, EDTASM, Visual/02, rc/BASIC, rc/Forth, XMODEM and BIOS.
Two independent clean builds generate **identical decoded 32 KiB ROMs**,
without reference-image input during the build. Both also generate the same
Intel HEX SHA-256:

\`cb27305656a6a2b03f09d85bbeea95a7cf4722eb19bba6b595e957bb8b5edb74\`

The generated binary SHA-256 is
\`ccfb68140acd7bb1bd3a22f82b54e44c7cc7a7d45833d826873e5bc0bc81d6ea\`.
The generated stored/whole-image checksum16 is \`2B78\`.

**The output does not reproduce the original:** 10,441 different bytes.
The authoritative comparison is deliberately strict, and CI fails on the
mismatch; do not replace it with a "reproducible build only" success check.

| Component | CPU address range | Difference count | Reference populated (non-FF) | Generated populated (non-FF) |
|---|---|---:|---:|---:|
| Monitor | 8000–97FF | 0 | — | — |
| Help | 9800–A0FF | 0 | — | — |
| SEDIT | A100–A3FF | 0 | — | — |
| EDTASM | A400–B0FF | 2,677 | 3,121 | 3,117 |
| Visual/02 | B100–C1FF | 1,563 | 3,986 | 3,982 |
| rc/BASIC | C200–DBFF | 0 | — | — |
| rc/Forth | DC00–EFFF | 4,537 | 4,635 | 3,662 |
| XMODEM | F000–F2FF | 0 | — | — |
| BIOS/extended BIOS and vectors | F300–FFFF | 1,664 | 3,113 | 3,107 |

The \`FF\`-populated counts are only structural clues, not a measurement
of source instruction count. All differences are listed by address and byte
in CI's \`.build/stock-rom-repro/reference-byte-differences.csv\`.

## Verified source-preparation fix

The pinned Visual/02 source labels RAM state \`v_r0\` through \`v_rf\` but
forms the subsequent EQU chain using \`r0\` through \`rf\`, which public
Asm/02 interprets as CPU register numbers (0–15). As a result \`q\` was
\`0011\` rather than \`7E20\` and many immediate operands used incorrect
addresses. \`prepare-asm02-source.py\` now repairs only these sequential
memory-field EQU references in its disposable copy, with idempotence and
CPU-register-operand regression coverage; the upstream source is unchanged.

This repair reduced overall differences from 10,477 to 10,441 and
Visual/02 differences from 1,599 to 1,563. The Visual/02 ROM now matches
the reference exactly through \`B100–B977\`, before a separate
source-level \`STR R7\` / \`PLO R7\` discrepancy at \`B978\`.

## Historical-revision experiments — diagnostic only

The CI steps \`probe-historical-sources.sh\` and
\`probe-source-compat.sh\` rebuild isolated component candidates, compare
their original logical address range against the unmodified reference, and
upload candidate sources/listings/HEX/comparison text. No experimental
component replaces the canonical build component.

| Hypothesis / component | Original differences | Experimental differences | Finding |
|---|---:|---:|---|
| EDTASM original pinned 2fe52285 vs older e16c0711 | 2,677 | 2,677 | No improvement from older public commit |
| EDTASM STGROM disposable \`DATA\` \`04000h\` → \`01000h\` | 2,677 | 2,663 | First divergence moves \`A40A\` → \`A446\`; exact reference not reproduced |
| Visual/02 disposable \`PLO R7\` → \`STR R7\` following zeroing of \`ntraps\` | 1,563 | 1,562 | First divergence moves \`B978\` → \`BA10\`; exact reference not reproduced |
| BIOS two disposable \`LBNZ no_uart\` → short \`BNZ no_uart\` branches | 1,664 | 1,576 | First divergence moves \`F30B\` → \`F331\`; exact reference not reproduced |
| Forth pinned d9de6b36 vs 556a89b4 | 4,537 | 4,537 | Same assembled differences |
| Forth older c5ca5fb7 | 4,537 | 4,539 | Slightly worse |
| Forth older 9ecf9fdc | 4,537 | Not assembled | 49 assembler errors; no image comparison |
| Visual/02 older f0f3cf91, fe0ddc3e | 1,563 | Not assembled | Fail with pinned public Asm/02; no image comparison |

The BIOS reference begins a \`BNZ\` at \`F30B\` (\`3A 24\`), whereas
the pinned public BIOS source emits \`LBNZ\` (\`CA F3 26\`).
The Forth reference has **973 more non-FF bytes** in its ROM region than
the pinned public revision, with instruction-stream divergence beginning
at \`DC0A\`. These are evidence of meaningful source/build-environment
differences, not permission to replace code with extracted ROM data.

## Remaining decision and feasible paths

The supplied pinned public source/tool combination has not reproduced the
reference exactly. A clean repeatable *candidate* build exists; a clean
reference-identical build does **not**. We have not proved that no
historical source/tool combination could reproduce it.

1. **Preferred historical recovery:** locate original Spare Time Gizmos
   locally patched component sources/build environment used for the
   published HEX, especially the substantial Forth differences. Pin the
   recovered versions and repeat byte-for-byte acceptance checks. No
   component/software selection changes.
2. **Reference-guided source reconstruction (requires review):** maintain
   an explicit, auditable list of minimal compatibility/source amendments
   applied only to disposable copies, with a test proving each address/byte
   correction against the reference. Changes to assembly opcode or data
   memory-map choices must not be silently promoted into the authoritative
   build.
3. **Distinct alternate result (also requires review):** keep the
   reproducible public-source candidate as a separately named output;
   **never call it identical stock** and never replace the reference.
   Firmware-selection/customization decisions remain postponed.

Diagnostic evidence: [CI run 38275364302](https://github.com/peclark1/Elf2K/actions/runs/38275364302)
with independent-build reports, complete per-byte CSV and both diagnostic
probe families in the workflow artifact. GitHub's strict stock reference
comparison is red by design until the original image is matched.
