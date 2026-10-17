; AVI / Netronics ROM additional monitor commands.
; This file is injected into the disposable TASM boots.asm by avi-port.py.
; All original Elf2K source remains unchanged.
; COM1 uses Q/EF4 (physical J15 must be configured accordingly).
; COM2 is a fixed 9600 baud CDP1854 until higher clock sources are verified.

#ifdef AVIELF2
; Console switch to Q/EF4 bitbang. The confirmation is emitted on the
; currently active console; BIOS F_SETBD then waits for a CR on COM1.
AVICOM1: CALL(ISEOL)
         LBNF CMDERR
         OUTSTR(AVIC1MSG)
         CALL(TTYAUT)       ; native BIOS autobaud on EF4, Q TX
         LBR MAIN

; Console switch to the optional UART. Decimal baud strings are dispatched
; as strings (SCANP1 interprets HEX and cannot parse 19200 as decimal).
AVICOM2: CALL(F_LTRIM)
         CALL(ISEOL)
         LBDF AVIU96
         RLDI(P2,AVIRATES)
         LBR COMND
AVIRATES:
         CMD(4, "9600", AVIU96)
         CMD(5, "19200", AVIUUNSUP)
         CMD(5, "38400", AVIUUNSUP)
         .DB 0

; The hardware jumpers provide the UART clocks. A command cannot
; magically change J10/J11. Do NOT overclock via software guessing.
AVIUUNSUP:
         CALL(ISEOL)
         LBNF CMDERR
         OUTSTR(AVIUNMSG)
         RETURN

; The original e2k_stbd backend is verified at 9600.
AVIU96:  CALL(ISEOL)
         LBNF CMDERR
         OUTSTR(AVIC2MSG)
         LDI $34
         CALL(F_USETBD)
         LBDF CMDERR
         RLDI(DP,BAUD1)
         LDI $01
         PHI BAUD
         STR DP
         INC DP
         LDI $34
         STR DP
         LBR MAIN

; Interactive raw hexadecimal loader, independent from : Intel HEX.
;   HEX 0200
;   0200> F8 00 B1 F8 20 A1
;   0206> ...
;   020C> .
; For unambiguous input only bytes are accepted (no address labels).
; RE/START location RESTA is reclaimed for the scratch write pointer:
; SET RESTART is disabled on AVI. The buffer still belongs to the monitor.
AVIHEX: CALL(SCANP1)
        CALL(ISEOL)
        LBNF CMDERR
        GHI P2
        SMI $7F
        LBDF AVIHXER
        RLDI(DP,RESTA)
        GHI P2
        STR DP
        INC DP
        GLO P2
        STR DP

AVIHXL: RLDI(DP,RESTA)
        LDA DP
        PHI P1
        LDN DP
        PLO P1
        CALL(THEX4)
        INLMES("> ")
        RLDI(P1,CMDBUF)
        RLDI(P3,CMDMAX)
        CALL(F_INPUTL)
        LBDF AVIHXDONE         ; Ctrl+C aborts
        RLDI(P1,CMDBUF)
        CALL(F_LTRIM)
        LDN P1
        XRI '.'
        LBZ AVIHXDONE
AVIHXB: CALL(F_LTRIM)
        CALL(ISEOL)
        LBDF AVIHXL
        CALL(GHEX2)
        LBNF AVIHXBAD
        PUSHD
        RLDI(DP,RESTA)
        LDA DP
        PHI P3
        LDN DP
        PLO P3
        GHI P3
        SMI $7F
        LBDF AVIHXPOP          ; forbid $7F00+ (monitor or ROM)
        POPD
        STR P3                 ; write the data byte
        SEX P3
        SM                     ; D - memory content must be zero
        SEX SP
        LBNZ AVIHXER          ; failed RAM readback
        INC P3
        RLDI(DP,RESTA)
        GHI P3
        STR DP
        INC DP
        GLO P3
        STR DP
        LBR AVIHXB

AVIHXPOP:
        POPD                   ; keep stack balanced
AVIHXER:
        OUTSTR(AVIHXERRMSG)
        RETURN
AVIHXBAD:
        OUTSTR(AVIHXDATAMSG)
        RETURN
AVIHXDONE:
        CALL(TCRLF)
        RETURN
AVIC1MSG: .TEXT "COM1 Q/EF4: PRESS CR AT 2400\r\n\000"
AVIC2MSG: .TEXT "COM2 UART 9600 8N1\r\n\000"
AVIUNMSG: .TEXT "?HIGHER UART BAUD REQUIRES CLOCK CHANGE\r\n\000"
AVIHXERRMSG: .TEXT "?HEX WRITE NOT IN RAM OR VERIFY FAILED\r\n\000"
AVIHXDATAMSG: .TEXT "?HEX DATA: EXPECT TWO HEX DIGITS\r\n\000"
#endif
