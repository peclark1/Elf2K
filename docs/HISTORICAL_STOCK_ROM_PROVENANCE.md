# Historical stock ROM provenance: byte-level findings and decision boundary

**2026-10-12 — firmware recovery investigation. Reference reproduction is BLOCKED pending owner/coordinator approval of historical component versions.**

## Why this is more than a toolchain problem

The untouched `sw/Elf2K-alternate.hex` has Intel HEX SHA-256 `db8d5148b7cb507613a20b28dc31abfce1b1f500cb69a8c2e348cfaea2ab6a4b` (Git blob `e1a14af17671dae2b051b53a7ae186d639e7f5b9`). At the initial [CI 38274161318](https://github.com/peclark1/Elf2K/actions/runs/38274161318) recovery checkpoint, two independent clean candidate ROM builds were byte-identical to **each other**, with Intel HEX SHA-256 `5b517539d44392bf1e93bac95a4088f3e98e1050aaa3eb6d64199ba977893cea`, but differed from the original in **10,477 bytes**. This was an intentionally failed reference-validation gate, not an acceptable stock reproduction.

The initial mismatch was isolated to EDTASM (2,677), Visual/02 (1,599), rc/Forth (4,537), and BIOS (1,664). Monitor, HELP, SEDIT, rc/BASIC, and XMODEM have **zero** differing bytes. Full CSV evidence, reference/compiled images, original pinned source provenance, and CI results are in [the worker checkpoint](STOCK_ELF2K_REPRODUCIBILITY_REPORT.md) and [CI run 38274161318](https://github.com/peclark1/Elf2K/actions/runs/38274161318).

### Latest verified CI on the forensic report commit

[CI run 38275388177](https://github.com/peclark1/Elf2K/actions/runs/38275388177), at commit `aa7bc9870063ad170205fe9efa3e25d9bb2a638f`, ran **22 passing regression tests** and again built two byte-identical images. After the concurrently landed disposable-source Visual/02 state-address fix (`f3c30c11aafb7dfd1440cb18412287fc814d741d`), the mismatch declined to **10,441 bytes**: EDTASM **2,677**, Visual/02 **1,563**, rc/Forth **4,537**, BIOS **1,664**, all other components **0**. Candidate Intel HEX SHA-256: `cb27305656a6a2b03f09d85bbeea95a7cf4722eb19bba6b595e957bb8b5edb74`; candidate decoded 32 KiB SHA-256: `ccfb68140acd7bb1bd3a22f82b54e44c7cc7a7d45833d826873e5bc0bc81d6ea`; stored checksum `2B78`. Strict reference check **FAILS AS EXPECTED**, with all other workflow steps successful. [Latest build/listings/probe artifact](https://github.com/peclark1/Elf2K/actions/runs/38275388177/artifacts/11758408907).

## Finding A — rc/Forth is an unequivocally different release

Extracting printable strings from the decoded 32 KiB ROMs identifies:

| Firmware | CPU address | Literal embedded version banner | Non-FF bytes in DC00-EFFF |
| --- | --- | --- | ---: |
| Unchanged original | `$ECD8` | `Rc/Forth 0.3` | 4,635 |
| Independent reproducible build | `$E96B` | `Rc/Forth 0.1` | 3,662 |

The banner text is machine-code/data content; it cannot be attributed to different Intel HEX formatting or mere branch-address relaxation. This is **direct evidence that the pinned rc/Forth source does not represent the original ROM's software release**. Public Riley source pin: [`rileym65/Elf-RcForth@d9de6b3`](https://github.com/rileym65/Elf-RcForth/tree/d9de6b36190d811b7d962d7c495b31c5ff23e2d5).

Historical source candidates exist in the **already pinned** [`wd5gnr/1802black@1d5f8b2`](https://github.com/wd5gnr/1802black/tree/1d5f8b2bb4295d83a6ac35db06c43c7eb009ec34/bios) archive: [`bios/forth0.asm`](https://github.com/wd5gnr/1802black/blob/1d5f8b2bb4295d83a6ac35db06c43c7eb009ec34/bios/forth0.asm) and [`bios/forth1.asm`](https://github.com/wd5gnr/1802black/blob/1d5f8b2bb4295d83a6ac35db06c43c7eb009ec34/bios/forth1.asm) both literally contain `hello: db 'Rc/Forth 0.3'`. These are **provenance candidates, not proven byte-identical substitutes**. Crucially, `bios/forth.hex` in that same archive is a still different *0.55* revision and **must not** be treated as the original ROM component.

**Decision implication:** no exact reference build is possible from the currently pinned Forth 0.1 source as-is. Reconstructing it requires selecting or restoring older **software contents**, beyond a permissible build-tool compatibility repair.

## Finding B — EDTASM uses a different historical data workspace

At the first differing operands in EDTASM:

| Logical address | Original | Reproducible candidate |
| --- | --- | --- |
| `$A40A` | `11` | `41` |
| `$A413` | `10` | `40` |
| `$A41E` | `10` | `40` |
| `$A42C` | `11` | `41` |

The candidate's generated `edtasm.lst` identifies the immediate operands as workspace/data addresses: `curline = $4004`, `textbuf = $41F9`, `stack = $41F7`. The [pinned public EDTASM](https://github.com/rileym65/Elf-EDTASM/blob/2fe52285245c206769ebe4e3d4707a3cced328c8/edtasm.asm) has an STGROM declaration `#define DATA 04000h`. By contrast, the [archived independent EDTASM](https://github.com/wd5gnr/1802black/blob/1d5f8b2bb4295d83a6ac35db06c43c7eb009ec34/bios/edtasm.asm) declares `#define DATA 01000h` under STGROM. This directly accounts for the `$10xx`/`$11xx` vs `$40xx`/`$41xx` difference. It is **not** yet proof that replacing only the data origin will match all 2,677 EDTASM bytes: other code and displacement differences are present.

## Finding C — Visual/02 provenance and shifted code

In the initial recovery candidate the first mismatch was `$B219` (original `20`, candidate `11`); the Visual/02 compatibility correction moved the first differing byte to `$B978` (original `57`, candidate `A7`) and reduced this region's difference count from 1,599 to 1,563. Many early instruction sequences match, whereas later exact sequences are seven bytes earlier in the candidate (for example original `$BF46` aligns with candidate `$BF3F`). The pinned [public Visual/02 at 61f7c97](https://github.com/rileym65/Elf-Visual02/blob/61f7c978d01509086195084155fbe3f5fc014fc9/visual02.asm) uses Asm/02-oriented public source; the historical archive's [`bios/visual02.asm`](https://github.com/wd5gnr/1802black/blob/1d5f8b2bb4295d83a6ac35db06c43c7eb009ec34/bios/visual02.asm) and [`bios/Makefile`](https://github.com/wd5gnr/1802black/blob/1d5f8b2bb4295d83a6ac35db06c43c7eb009ec34/bios/Makefile) show an Rc/Asm-era assembly path. That is an identifiable historical source/tool lineage, but no exact substitute has been proven.

Later worker commits on this branch added **non-mutating historical probes** and a disposable-source Visual/02 state-address correction/regression (up to `b492284ff0a565176a5378c392a6eefe6f484f71`). [CI run 38275030479](https://github.com/peclark1/Elf2K/actions/runs/38275030479) still correctly fails the strict stock reference comparison; its historical source probes show that some earlier Visual/02 revisions change the difference count but do **not** eliminate it. Do not conflate a reduced diff count with reference reproduction.

## Finding D — BIOS begins with divergent conditional branch encoding

At `$F30B`, the original has bytes `3A 24` (CDP1802 short `BNZ` to `$F324`); the candidate listing emits `CA F3 26` (long `LBNZ` to `$F326`). The archived [`bios/bios.asm`](https://github.com/wd5gnr/1802black/blob/1d5f8b2bb4295d83a6ac35db06c43c7eb009ec34/bios/bios.asm) literally has `lbnz no_uart` at this point, and the archived component output retains the long form. The original's short instruction therefore **cannot be explained by merely reassembling that exact source with the observed public output**. The responsible original source edit or historical branch-relaxation behavior has not yet been established. The one-byte length difference alone shifts subsequent addresses; 1,664 BIOS mismatch bytes do not imply 1,664 independent source edits.

## Engineering status / required decision

**Reproducible stock build: YES. Historical reference-identical stock build: NO.** Latest reproducible candidate mismatch **10,441 bytes**, not the initial **10,477**. There is conclusive evidence of a different Forth software release and EDTASM workspace definitions; the Visual/02 and BIOS differences have grounded historical-source/assembler leads but remain incompletely isolated.

Stop before selecting alternate versions or changing ROM contents. Per the assignment, the owner/coordinator must decide whether to authorize a **separately labeled, disposable historical reference-reconstruction experiment** using the archived Forth 0.3 variants, archive EDTASM/Visual/02, and a controlled BIOS assembler/source comparison. Such an experiment must keep the tracked reference, original configuration, production source locks and intended ROM software inventory unchanged until reviewed. Do not merge; do not program EEPROM from an unaccepted candidate; and do not make future AVI/Hyperboard ROM software selections.

### Independent reproduction

From a clean checkout of `fix/stock-elf2k-build`:

```sh
python3 -m unittest discover -s sw/build/tests -v
bash sw/build/reproduce-stock.sh
```

The current `reproduce-stock.sh` exits nonzero **by design**, because neither generated ROM matches the original reference. This document records the diagnosed cause and owner decision boundary; it does not relax that gate.
