#!/usr/bin/env python3
"""Port the pinned stock monitor/BIOS to a safe AVI Q/EF bench bootstrap.

Transformations affect ONLY disposable working copies. Originals untouched.
This is the controlled first-test fallback while the CDP1854 pin straps are
verified on the assembled Hyperboard. Each patch enforces expected anchors.
"""
from __future__ import annotations
from pathlib import Path
import re
import sys

def substitute_exact(s: str, old: str, new: str) -> str:
    n = s.count(old)
    if n != 1:
        raise RuntimeError(f"expected once, got {n}: {old[:100]!r}")
    return s.replace(old, new)

def port_bios(path: Path) -> None:
    s = path.read_text()
    start = s.index("#ifdef ELF2K\ninclude config.inc")
    end = s.index("\n#endif", start) + len("\n#endif")
    original = s[start:end]
    # Retain all stock ELF2K paths when built without -DAVIELF2.
    # Netronics-compatible AVI uses Q/EF4; the current tested Q/EF3 remains on the baseline branch. Don't define UART,
    # NVR or EIDE because their stock routines are 8250/DS1287/IDE drivers.
    replacement = """#ifdef ELF2K
include config.inc
#define STGROM
#ifdef AVIELF2
#define SERHDX
#define UART                    ; CDP1854 mode 1, NOT 8250
#define SERP            b4
#define SERN            bn4
#define SERSEQ          seq
#define SERREQ          req
#define BASE            0f000h
; IDE registers remain referenced by unreachable legacy code. Compile-only
; constants: the AVI monitor disables IDE boot and access vectors.
#define IDE_SELECT       2
#define IDE_DATA         3
#else
""" + original.split("#define STGROM", 1)[1].rsplit("#endif", 1)[0] + """#endif
#endif"""
    s = s[:start] + replacement + s[end:]
    # Entire 8250 driver is replaced with the explicitly separate RCA1854
    # polling driver. Keep the ABI at F800/FF00 unchanged.
    legacy_start = s.index("#ifdef UART\n; ****************************************")
    legacy_end = s.index('#endif  ;; "#ifdef UART"', legacy_start)
    legacy_end = s.index("\n", legacy_end) + 1
    native = (Path(__file__).resolve().parent.parent / "avi-cdp1854.asm").read_text()
    s = s[:legacy_start] + "#ifdef UART\n" + native + "\n#endif\n" + s[legacy_end:]
    # Keep the public BIOS vector table but disconnect storage calls from
    # absent IDE peripherals. The generic BIOS return-error routine is used.
    for label, target in (
        ("f_boot:", "bootide"),
        ("f_iderst:", "resetide"),
        ("f_idewrt:", "wrtide"),
        ("f_ideread:", "rdide"),
        ("f_ideboot:", "bootret"),
    ):
        pat = re.compile(r"(?m)^(" + re.escape(label) + r"\s+lbr\s+)" + target + r"(\s*(?:;.*)?)$")
        if len(pat.findall(s)) != 1:
            raise RuntimeError(f"expected one BIOS vector: {label}")
        s = pat.sub(r"\1err\2", s)
    s = substitute_exact(s,
        "DEVICES:equ     05h     ; all versions support IDE and bit banged serial",
        """#ifdef AVIELF2
DEVICES:equ     04h     ; AVI Q/EF serial, no IDE
#else
DEVICES:equ     05h     ; all versions support IDE and bit banged serial
#endif""")
    path.write_text(s)

def port_boots(path: Path) -> None:
    s = path.read_text()
    # Distinctive banner, without changing the stock historical source.
    s = substitute_exact(s, r'COSMAC ELF 2000 \000', r"Pete's ELF II Monitor\000")
    s = substitute_exact(s, 'INLMES(" EPROM V")', 'INLMES(" V")')
    # Only the AVI disposable build omits the startup credit text.
    # Underlying license/source files are NOT modified.
    s = substitute_exact(s,
        'RIGHTS:\t.TEXT\t"Copyright (C) 2004-2020 by Spare Time Gizmos.  All rights reserved.\\r\\n"',
        'RIGHTS:\t.TEXT\t"\\000"')
    s = substitute_exact(s,
        '\t.TEXT\t"ElfOS BIOS Copyright (C) 2004-2020 by Mike Riley.\\r\\n"',
        '')
    # Historic 1977 Enterprise artwork, not STG's replacement top banner.
    # Source: Popular Electronics July 1977 Table I ($0000-$003F) and
    # original Netronics manual Table II ($0040-$00FF); the latter is
    # already present verbatim in the inherited NCC1701 bitmap.
    start_marker = "; SPARE TIME GIZMOS..."
    end_marker = "; The original NCC1701 starts here...."
    if s.count(start_marker) != 1 or s.count(end_marker) != 1:
        raise RuntimeError("original PIXIE graphic anchors changed")
    a = s.index(start_marker)
    b = s.index(end_marker)
    first_64 = [
        "    .DB $90,$B1,$B2,$B3,$B4,$F8,$2D,$A3",
        "    .DB $F8,$3F,$A2,$F8,$11,$A1,$D3,$72",
        "    .DB $70,$22,$78,$22,$52,$C4,$C4,$C4",
        "    .DB $F8,$00,$B0,$F8,$00,$A0,$80,$E2",
        "    .DB $E2,$20,$A0,$E2,$20,$A0,$E2,$20",
        "    .DB $A0,$3C,$1E,$30,$0F,$E2,$69,$3F",
        "    .DB $2F,$6C,$A4,$37,$33,$3F,$35,$6C",
        "    .DB $54,$14,$30,$33,$00,$00,$00,$00",
    ]
    original_bitmap = (
        "; ORIGINAL COSMAC ELF JULY 1977 - FIRST 64 DISPLAY BYTES\n"
        + "\n".join(first_64) + "\n\n"
    )
    s = s[:a] + original_bitmap + s[b:]
    # The original ELF2K PIXIE test enabled video before printing its
    # EF1 timing diagnostic and Enterprise caption. CDP1861 DMA then
    # corrupts Q/EF4 bit-banged serial characters on the AVI board.
    # EF1 vertical timing is free-running even with the display disabled;
    # leave video OFF until after all console messages have completed.
    # The existing PIXCHM path calls INT_ON / PIXIE_ON only after printing.
    s = substitute_exact(s,
        "PIXIE0:\tPIXIE_ON\t\t; enable the display ",
        "PIXIE0:\t; keep video off during terminal diagnostics")
    # Removing the early PIXIE_ON changes ROM offsets, so the ISR's
    # short return branch can straddle a 256-byte page boundary.
    # This branch runs at vertical frame end (outside timed scanlines),
    # so using an explicit long branch preserves the behavior safely.
    s = substitute_exact(s,
        "BR\tINT1RT\t\t; and return when the frame is finished",
        "LBR\tINT1RT\t; and return when the frame is finished")
    # Netronics COM1 receives serial data on EF4, normally idle high.
    # The stock PIXIE test loops for idle-low keypad EF4; in this variant,
    # loop while COM1 idles high and quit on a PC serial start bit.
    s = substitute_exact(s, "BN4\tPIXIE1\t\t; or break when INPUT is pressed",
                         "B4\tPIXIE1\t; exit when EF4 COM1 RX falls")
    s = substitute_exact(s, "[Toggle INPUT to end]",
                         "[Send a character on COM1 to end]")
    # Self-checks for ROM and RAM remain intact; bypass only absent
    # DS1287, 8250, PPI, speaker, PS/2 POST sequences.
    s = substitute_exact(s, "DPDONE:\n", """DPDONE:
#ifdef AVIELF2
        LBR     SYSI2B      ; direct to SCRT; no option-board probes
#endif
""")
    # Skip NVR initialization and use Q/EF autobaud; retaining this code
    # in the source is safe as long as no control flow reaches it.
    s = substitute_exact(s, "SYSIN3:\tOUTI(LEDS,$18)", """SYSIN3:
#ifdef AVIELF2
        LBR     SYSI3B      ; skip absent Elf2K NVR
#endif
        OUTI(LEDS,$18)""")
    # After printing memory status/copyright, omit IDE enumeration,
    # clock and historical autonomous boot flags.
    s = substitute_exact(s, "\tOUTSTR(RIGHTS)\t\t; type the copyright notices",
                          """\t; upstream copyright text hidden in AVI startup banner
#ifdef AVIELF2
        LBR     MAIN0       ; first AVI bench test: enter monitor
#endif""")
    s = substitute_exact(s, "TTYINI:\n", """TTYINI:
#ifdef AVIELF2
        LBR     TTYAUT      ; Netronics Q/EF4 autobaud
#endif
""")
    anchor = "\tSTR\tDP\t\t; ...\n\n;   And lastly, if there is a NVR/CMOS"
    s = substitute_exact(s, anchor, """\tSTR\tDP\t; ...
#ifdef AVIELF2
        RETURN             ; no nonvolatile RAM on Hyperboard
#endif

;   And lastly, if there is a NVR/CMOS""")
    # Page-align the EF status display's short branches. ROM positioning
    # changes in the AVI image can make otherwise-nearby branches cross
    # a 256-byte page, which 1802 short branches cannot do.
    s = substitute_exact(s, "SHOWEF:\n", "        PAGE\nSHOWEF:\n")
    # Keep obsolete NVR logic unreachable, but make its small loop valid
    # even as ROM allocation differs from the stock Elf2K image.
    s = substitute_exact(s, "\tBZ\tNVRL2\t\t; wait for it to set",
                         "\tLBZ\tNVRL2\t\t; wait for it to set")
    s = substitute_exact(s, "\tBNZ\tNVRL3\t\t; wait for it to clear",
                         "\tLBNZ\tNVRL3\t\t; wait for it to clear")
    # Opt-in hardware UART. BOOTS always defaults to bit-banged serial
    # on reset so incorrect jumpers cannot make the system unbootable.
    cmd = 'CMDTBL:\tCMD(4, "CONTINUE", CONTINUE)'
    s = substitute_exact(s, cmd, cmd + '\n#ifdef AVIELF2\n'
        + '\tCMD(4, "COM1", AVICOM1)\n'
        + '\tCMD(4, "COM2", AVICOM2)\n'
        + '\tCMD(1, "1", AVICOM1)\n'
        + '\tCMD(1, "2", AVICOM2)\n'
        + '\tCMD(3, "UART", AVICOM2)\n'
        + '\tCMD(3, "HEX", AVIHEX)\n'
        + '\tCMD(4, "CASSAVE", AVICASSAVE)\n'
        + '\tCMD(4, "CASLOAD", AVICASLOAD)\n#endif')
    end_marker = "; The table always ends with a zero byte...\n\t.DB\t0"
    if s.count(end_marker) != 1:
        raise RuntimeError("missing primary command table terminator")
    uart_handler = (Path(__file__).resolve().parent.parent / "avi-monitor-commands.asm").read_text()
    s = substitute_exact(s, end_marker, end_marker + uart_handler)
    # Disable commands that knowingly touch Elf2K IDE, RTC or NVR
    # hardware. INPUT/OUTPUT remain available to test COM2 explicitly.
    forbidden = {"BOOT", "NVR", "IDE", "DATE", "RESTART", "CPU", "TERMINAL"}
    count = 0
    lines = []
    for line in s.splitlines(keepends=True):
        match = re.search(r'\bCMD\(\d+,\s*"([^"]+)"', line)
        if match and match.group(1) in forbidden and not line.lstrip().startswith(";"):
            # Preserve table labels on the first entries of disabled tables.
            tablabel = re.match(r"^([A-Z_0-9]+:)(.*)$", line)
            if tablabel:
                line = tablabel.group(1) + "\n;" + tablabel.group(2)
            else:
                line = ";" + line
            count += 1
        lines.append(line)
    if count < 8:
        raise RuntimeError(f"expected >=8 absent-hardware commands, got {count}")
    s = "".join(lines)
    # Cassette service is linked into the unused C200 ROM region. Stock
    # BOOTS and original Giant monitor remain byte-for-byte unmodified.
    s = substitute_exact(s, "\t.END",
                         '\t.ORG $C200\n\t.INCLUDE "avi-cassette.asm"\n\t.END')
    path.write_text(s)

def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("usage: avi-port.py WORK_DIR")
    directory = Path(sys.argv[1])
    port_boots(directory / "boots.asm")
    port_bios(directory / "bios.asm")
    print("AVI safe-bootstrap transformations applied")
if __name__ == "__main__":
    main()
