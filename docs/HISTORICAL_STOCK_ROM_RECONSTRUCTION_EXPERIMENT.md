# Historical stock-ROM reconstruction — isolated experimental milestone

**Date:** 2026-10-12  
**Repository:** `peclark1/Elf2K`  
**Baseline:** `8df2d5b2bc0a512316c192fdbe1a6906fbc406e8`  
**Experiment branch:** `experiment/stock-rom-historical-reconstruction`  
**Status:** VERIFIED FORENSIC PROGRESS, **NOT** A BYTE-IDENTICAL REFERENCE BUILD; **NOT APPROVED** for production, merge, or EEPROM.

## Safety and provenance

- Untouched, immutable reference: `sw/Elf2K-alternate.hex`, git blob `e1a14af17671dae2b051b53a7ae186d639e7f5b9`; Intel HEX SHA-256 `db8d5148b7cb507613a20b28dc31abfce1b1f500cb69a8c2e348cfaea2ab6a4b`; decoded 32K SHA-256 `842aa3f4a84d7755dcfadfadaeaa7968e99dde2a9eb9adfda41711d8929c2dad`; stored checksum `F0CB`.
- Original intended 9-component alternate ROM inventory, `config.Elf2K-alternate`, `sw/Makefile`, `sw/build/prepare-deps.sh` and all production source/tool locks were not changed.
- Experimental code and reports were added exclusively on a new branch. Only isolated copies inside ignored `.build/` received source edits. There is no attempt to construct, rename, ship, program, or approve a replacement ROM.
- A **separate** CI workflow, `.github/workflows/historical-rom-reconstruction.yml`, checks the original git blob and SHA-256 and compares sensitive paths with the baseline commit. It deliberately requires the official two-build reproducer to report the same strict stock **MISMATCH (10,441 differing bytes)**; a green isolated CI run **does not** mean reference reproduction succeeded.
- Primary passing run for the source-semantics hypothesis: [38283175594](https://github.com/peclark1/Elf2K/actions/runs/38283175594) at commit `8274f3be0185db6e4957b4315b7b24a4ed59d6fc`; its [artifact](https://github.com/peclark1/Elf2K/actions/runs/38283175594/artifacts/11761883608) has source copies, assembler listings, HEX files, byte comparisons, build manifest and full experiment logs. The earlier [38282658745](https://github.com/peclark1/Elf2K/actions/runs/38282658745) run at `667b555b` independently establishes the Forth 0.3 display-label trial.

## Results by component

| Original component | Canonical stock-build mismatch | Isolated findings | Reference-identical? |
| --- | ---: | --- | --- |
| EDTASM, `$A400-$B0FF` | **2,677** | Historical archive STGROM workspace `DATA=$1000` gives **2,357** mismatches; changing archived workspace to `$4000` worsens to **2,375**, first `$A40A`. The workspace choice alone does not reconstruct source. | No |
| Visual/02, `$B100-$C1FF` | **1,563** | One independent source-backed trial of `ntraps` initialization `PLO R7→STR R7` yields **1,562**, first `$BA10`; later code has a seven-byte displacement and instruction differences. Archival RcAsm lineage does not match. | No |
| rc/Forth, `$DC00-$EFFF` | **4,537** | Original identifies `Rc/Forth 0.3` at `$ECD8`; pinned public source emits `0.1` at `$E96B`. Archived 0.3 `forth0.asm` assembles with Asm/02 but ends near `$F487` (oversized). Archived 0.3 `forth1.asm` had an unreferenced `disp` label inside a disabled `#if 0` branch; adding an entry label in a throwaway copy yields **0 assembler errors**, **6,268 bytes generated**, end-exclusive **`$F47C`**, **4,884** mismatches within the stock Forth span, and a collision with other stock components. Neither can be substituted unchanged. | No |
| BIOS, `$F300-$FFFF` | **1,664** | Bounded historical short-branch and source-instruction experiments identify clusters of diverging branch encoding and register semantics; latest isolated hypothesis reaches **473** differing BIOS bytes. See ledger below. | No |
| Monitor, HELP, SEDIT, rc/BASIC, XMODEM | **0** | All five still match the original; nothing was exchanged or removed. | Yes |

## BIOS diagnostic progression — not production source

| Isolated trial | Mismatches | Notes |
| --- | ---: | --- |
| Pinned canonical stock candidate | 1,664 | First `$F30B`, reference short `BNZ` vs candidate long `LBNZ` |
| Two `no_uart` short branches | 1,576 | Historical encoding hypothesis |
| Also `abdlp1` short branch | 1,269 | Historical encoding hypothesis |
| Also `rtc_go` short branch | 1,201 | Earlier best; first `$F4A7` |
| One `rtc_notset` short branch | 1,234 | Transient regression; **must not** be judged by a greedy single-step heuristic |
| Second `rtc_notset` short branch | 1,233 | Still a transient regression |
| `rtc_w1` short branch | **493** | New verified best **without** semantic register transfer hypotheses; first `$F746` |
| Then a `size_lp1` short branch | 494 | Isolated additional branch improves local opcode agreement but *slightly worsens* total byte count |
| Two **reference-suggested** register transfers `PLO RF`, `PHI RF` with `size_lp1` trial | 479 | Source semantic change, purely diagnostic; candidate first `$F746` |
| Also both `size_lp2` long-to-short branches | **473** | Latest trial, first `$F746`; two earlier pointer-operand differences remain |

**Why 473 is not ready:** at `$F746` and `$F791`, differences `EF` vs `ED` represent the low byte of pointers to `drqloop`, a relocation symptom. Near `$F7B6`, after contracting the size loops, the original continues with a sequence beginning `98 73 88 73 9F AF 88 BF` whereas the trial emits `97 A7 88 B7 98 A8...`. These are distinct register/stack-handling instructions; changing them is a **semantic code decision**, not a harmless assembler compatibility adjustment. This does not prove the 0.3-era original code is correct or preferable to the public source. Further blind short-branch changes would be unsafe.

One-step tests are insufficient because a local width reduction changes the addresses of subsequent instructions, branch destinations and data references. Each staged source, assembler listing and exact comparison is preserved; the experimental code never replaces the canonical ROM.

## Decision boundary and continuation

**Milestone reached:** a protected historical forensic framework passes CI, deterministically reproduces the unchanged canonical mismatch, resolves the missing Forth 0.3 `disp` label as an assembler problem, and improves BIOS isolation from **1,664 to 473 differing bytes** without accepting modified firmware.

**Not reached:** a complete byte-identical 32 KiB historical stock image. In particular there is no authenticated, stock-sized `Rc/Forth 0.3` source/tool combination, EDTASM still has large code divergences, and Visual/02 and BIOS include historically meaningful instruction differences.

**For owner/coordinator approval before production selection:** choose/approve an authoritative historical Forth release and fit strategy; review and accept/reject historical EDTASM workspace/code changes, Visual/02 instruction changes and BIOS branch/register semantics with source provenance. Do not promote the isolated patched sources or adopt a ROM unless a full independent **0-byte** image check passes and that source/tool provenance has been approved. Continue source-archive investigation in isolation if new evidence can be obtained without adopting any component.

**Explicitly unchanged:** pinned production sources and tools, official reference, stock software inventory, draft PR #2 (unmerged), physical EEPROMs (not programmed).
