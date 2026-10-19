; AVI / Netronics ROM additional monitor commands.
; This file is injected into the disposable TASM boots.asm by avi-port.py.
; All original Elf2K source remains unchanged.
; COM1 uses Q/EF4 (physical J15 must be configured accordingly).
; COM2 UART 8N1: 9600 tested; 19200/38400 are external-clock bench modes.

#ifdef AVIELF2
; Dedicated COM2-first test ROM. Called from TTYINI *before the banner*.
; CDP1854 x16 clock must already be physically set to 614400 Hz.
; The proven AVIUSET sequence initialized this UART in previous ROMs;
; here we apply the same hardware setup without emitting any text on COM1.
AVICOM2BOOTINIT:
        LDI $34
        CALL(F_USETBD)
        LBDF AVICOM2BOOTFAIL
        RLDI(DP,BAUD1)
        LDI $01              ; BAUD.1 = 1 => hardware UART + echo
        PHI BAUD
        STR DP               ; persist COM2 selection across MAIN1
        INC DP
        LDI $34
        STR DP               ; BAUD0 saved UART format
        RETURN
AVICOM2BOOTFAIL:
        ; Fail visibly on LEDs rather than silently blocking in COM1 autobaud.
        ; Never attempt to read bitbang EF4 on the CHIP8 dedicated build.
        OUTI(LEDS,$E2)
        LBR AVICOM2BOOTFAIL

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
         CMD(5, "19200", AVIU19)
         CMD(5, "38400", AVIU38)
         .DB 0

; All baud choices operate the SAME 8N1 CDP1854 driver. The UART has
; external 16x TCLK/RCLK: CDP1863/4040 wiring determines real baud.
; 9600 is known working. Higher selections are honest hardware-clock
; test modes. They DO NOT change the Hyperboard jumpers or generator
; frequency; select the appropriate clocks while POWERED OFF.
; The confirmation is sent over the PREVIOUS active console, allowing
; Tera Term to be changed before input at the new UART rate.
AVIU19:  CALL(ISEOL)
         LBNF CMDERR
         OUTSTR(AVI19MSG)
         LBR AVIUSET
AVIU38:  CALL(ISEOL)
         LBNF CMDERR
         OUTSTR(AVI38MSG)
         LBR AVIUSET

; 9600 is the only baud physically tested so far.
AVIU96:  CALL(ISEOL)
         LBNF CMDERR
         OUTSTR(AVIC2MSG)
AVIUSET: LDI $34
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
; An optional four-digit address prefix must end with a colon.
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
; Optional explicit address prefix, e.g. "0200: F8 01 B1".
; A four-digit byte run without a colon still means ordinary data bytes.
        RCOPY(P4,P1)
        CALL(GHEX4)
        LBNF AVIHXNOADDR
        LDN P1
        XRI ':'
        LBNZ AVIHXNOADDR
        INC P1
        GHI P2
        SMI $7F
        LBDF AVIHXER
        RLDI(DP,RESTA)
        GHI P2
        STR DP
        INC DP
        GLO P2
        STR DP
        LBR AVIHXB
AVIHXNOADDR:
        RCOPY(P1,P4)
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
AVI19MSG: .TEXT "COM2 19200 TEST: SET 307200 HZ TCLK/RCLK FIRST\r\n\000"
AVI38MSG: .TEXT "COM2 38400 TEST: SET 614400 HZ TCLK/RCLK FIRST\r\n\000"
AVIHXERRMSG: .TEXT "?HEX WRITE NOT IN RAM OR VERIFY FAILED\r\n\000"
AVIHXDATAMSG: .TEXT "?HEX DATA: EXPECT TWO HEX DIGITS\r\n\000"
#endif
