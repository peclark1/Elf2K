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
    # AVI uses the already proven Q/EF3 serial path. Don't define UART,
    # NVR or EIDE because their stock routines are 8250/DS1287/IDE drivers.
    replacement = """#ifdef ELF2K
include config.inc
#define STGROM
#ifdef AVIELF2
#define SERHDX
#define SERP            b3
#define SERN            bn3
#define SERSEQ          seq
#define SERREQ          req
#define BASE            0f000h
#else
""" + original.split("#define STGROM", 1)[1].rsplit("#endif", 1)[0] + """#endif
#endif"""
    s = s[:start] + replacement + s[end:]
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
                          """\tOUTSTR(RIGHTS)\t; type the copyright notices
#ifdef AVIELF2
        LBR     MAIN0       ; first AVI bench test: enter monitor
#endif""")
    s = substitute_exact(s, "TTYINI:\n", """TTYINI:
#ifdef AVIELF2
        LBR     TTYAUT      ; Q/EF3 autobaud (UART not yet enabled)
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
    s = substitute_exact(s, "SHOWEF:\\n", "        PAGE\\nSHOWEF:\\n")
    # Keep obsolete NVR logic unreachable, but make its small loop valid
    # even as ROM allocation differs from the stock Elf2K image.
    s = substitute_exact(s, "\\tBZ\\tNVRL2\\t\\t; wait for it to set",
                         "\\tLBZ\\tNVRL2\\t\\t; wait for it to set")
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
                line = tablabel.group(1) + "\\n;" + tablabel.group(2)
            else:
                line = ";" + line
            count += 1
        lines.append(line)
    if count < 8:
        raise RuntimeError(f"expected >=8 absent-hardware commands, got {count}")
    path.write_text("".join(lines))

def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("usage: avi-port.py WORK_DIR")
    directory = Path(sys.argv[1])
    port_boots(directory / "boots.asm")
    port_bios(directory / "bios.asm")
    print("AVI safe-bootstrap transformations applied")
if __name__ == "__main__":
    main()
