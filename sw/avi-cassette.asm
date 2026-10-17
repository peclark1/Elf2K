; AVI ELF II monitor cassette service (experimental, Q output / EF2 input).
; Source assembled into the AVI-only BOOTS ROM at $C200, not into Giant
; Monitor $F000-$F0FF. Genuine Giant single-bit routines at F065/F0BA
; are invoked with their historic timing and framing; no new tape header.
; Assembled as part of disposable boots.asm: BOOTS symbols/macros visible.
;
; CASSAVE start end       -- raw inclusive RAM range, Giant tape format
; CASLOAD start end       -- raw inclusive RAM range, Giant tape format
; CASSAVE TBASIC          -- image 0000 through max(0FFF,MEND-SPARE-1)
; CASLOAD TBASIC          -- read 4K, inspect MEND/SPARE, extend if needed
;
; No commands run in the Giant Monitor. Historical software remains external.
; IMPORTANT: physical tape transport cannot be cancelled through serial.
;
#ifdef AVIELF2
AVICASSAVE:
        CALL(F_LTRIM)
        LDN P1
        CALL(ISHEX)
        LBDF AVICSVNUM
        RLDI(P2,AVICSVKEY)
        LBR COMND
AVICSVKEY:
        CMD(6,"TBASIC",AVICSVTB)
        .DB 0
AVICSVNUM:
        CALL(SCANP1)
        RCOPY(P3,P2)
        CALL(SCANP1)
        RCOPY(P4,P2)
        CALL(ISEOL)
        LBNF CMDERR
        LBR AVICSVCHK
AVICSVTB:
        CALL(ISEOL)
        LBNF CMDERR
        CALL(AVITBEND)
        LBDF AVICTBERR
        RLDI(P3,$0000)
        RCOPY(P4,INTPC)
        DEC P4                   ; convert exclusive to inclusive
AVICSVCHK:
        CALL(P3LEP4)
        LBNF CMDERR
        GHI P4
        SMI $7F
        LBDF AVICRANGE
        OUTSTR(AVICSVMSG)
        CALL(F_READ)            ; start RECORD before typing a key
        RCOPY(T2,P3)            ; RA = byte stream pointer
        RCOPY(INTPC,P4)         ; R1 = end + 1 (exclusive)
        INC INTPC
        ; Save monitor SCRT argument register R6 before it is used as
        ; Giant Monitor's F065 bit-writer program counter.
        RLDI(DP,RESTA)
        GHI A
        STR DP
        INC DP
        GLO A
        STR DP
        RLDI(A,$F065)           ; one-bit Q writer returns via SEP R3
        DEC SP                  ; F065 writes to M(R2)! reserve scratch
        SEX SP
        LDI $80
        PHI P2                  ; 128 one-bits leader, as original
AVICSVLEAD:
        LDI $00
        SMI $00                 ; no borrow sets DF=1
        SEP A
        GHI P2
        LBNZ AVICSVLEAD
AVICSVBYTE:
        GLO T2
        ; Original Giant uses the low pointer value for front-panel
        ; progress. Not needed here because it would clobber SCRT R5.
        SEQ
        LDA T2                  ; D = data byte; RA incremented
        PHI P4                  ; RB.1 = shift register
        LDI $09
        PLO P4                  ; nine bits = start + 8 data
        PLO P2                  ; odd parity accumulator starts at 9
        LDI $00
        ADI $00                 ; DF=0: start bit
AVICSVBIT:
        SEP A                   ; F065 transmits DF then returns to PC R3
        DEC P4
        GLO P4
        LBZ AVICSVPAR
        GHI P4
        SHL                     ; next data bit into DF
        PHI P4
        LBR AVICSVBIT
AVICSVPAR:
        GLO P2
        SHR                     ; parity bit into DF
        SEP A
        ; Stop when the cursor equals end+1; otherwise next data byte.
        GLO INTPC
        STR SP
        GLO T2
        XOR
        LBNZ AVICSVBYTE
        GHI INTPC
        STR SP
        GHI T2
        XOR
        LBNZ AVICSVBYTE
        ; Four training/trailing bits just like the Giant Monitor.
        SEP A
        SEP A
        SEP A
        SEP A
        REQ
        INC SP
        RLDI(DP,RESTA)
        LDA DP
        PHI A
        LDN DP
        PLO A
        RLDI(DP,RAMPAGE)
        OUTSTR(AVICDONE)
        RETURN

AVICASLOAD:
        CALL(F_LTRIM)
        LDN P1
        CALL(ISHEX)
        LBDF AVICLDNUM
        RLDI(P2,AVICLDKEY)
        LBR COMND
AVICLDKEY:
        CMD(6,"TBASIC",AVICLDTB)
        .DB 0
AVICLDNUM:
        CALL(SCANP1)
        RCOPY(P3,P2)
        CALL(SCANP1)
        RCOPY(P4,P2)
        CALL(ISEOL)
        LBNF CMDERR
        LDI 0
        PLO XX                  ; R8.0 = 0, fixed range
        LBR AVICLDCHK
AVICLDTB:
        CALL(ISEOL)
        LBNF CMDERR
        RLDI(P3,$0000)
        RLDI(P4,$0FFF)          ; first transfer first 4 KiB
        LDI 1
        PLO XX                  ; 1 = extend dynamically at $1000
AVICLDCHK:
        CALL(P3LEP4)
        LBNF CMDERR
        GHI P4
        SMI $7F
        LBDF AVICRANGE
        OUTSTR(AVICLDMSG)
        CALL(F_READ)            ; begin PLAY before typing a key
        RCOPY(T2,P3)
        RCOPY(INTPC,P4)
        INC INTPC
        ; Giant F0BA is the EF2 single-bit reader (uses RD as
        ; timing/parity scratch); temporarily use DP=R7 as its PC.
        DEC SP
        SEX SP
        RLDI(DP,$F0BA)
AVICLDPRE0:
        LDI $F9
        PHI P2
AVICLDPRE1:
        SEP DP
        LBNF AVICLDPRE0
        GHI P2
        LBNZ AVICLDPRE1         ; seven leader one-bits
AVICLDWAIT:
        SEP DP
        LBDF AVICLDWAIT         ; wait for zero start bit
        LDI 1
        PHI P2                  ; sentinel for 8 data bits
        PLO P2                  ; parity starts at one
AVICLDBIT:
        SEP DP
        GHI P2
        SHLC                    ; next data bit from DF
        PHI P2
        LBNF AVICLDBIT          ; repeat until sentinel shifts out
        SEP DP                  ; parity bit
        GLO P2
        SHR
        LBDF AVICLDERR         ; invalid parity
        GHI P2
        STR T2
        INC T2
        ; TBASIC format is headerless. At 4K the now-loaded Tiny
        ; BASIC MEND/SPARE specifies whether more bytes follow.
        GLO XX
        LBZ AVICLDNEXT
        GHI T2
        XRI $10
        LBNZ AVICLDNEXT
        GLO T2
        LBNZ AVICLDNEXT
        CALL(AVITBEND)
        LBDF AVICLDERR
AVICLDNEXT:
        GLO INTPC
        STR SP
        GLO T2
        XOR
        LBNZ AVICLDWAIT
        GHI INTPC
        STR SP
        GHI T2
        XOR
        LBNZ AVICLDWAIT
        INC SP
        RLDI(DP,RAMPAGE)
        OUTSTR(AVICDONE)
        RETURN
AVICLDERR:
        INC SP
        RLDI(DP,RAMPAGE)
        OUTSTR(AVICPARERR)
        RETURN

; AVITBEND: validate original Netronics Tiny BASIC and return
; end+1 exclusive in R1 (INTPC), DF=0 success / DF=1 error.
; Interpreter+workspace must be preserved through at least $0FFF.
; Netronics MEND ($0024, big-endian) is end+SPARE, not byte count.
AVITBEND:
        RLDI(P1,$0000)
        LDA P1
        XRI $C0
        LBNZ AVITBBAD
        LDA P1
        XRI $01
        LBNZ AVITBBAD
        LDA P1
        LBNZ AVITBBAD
        LDA P1
        XRI $C0
        LBNZ AVITBBAD
        LDA P1
        XRI $F0
        LBNZ AVITBBAD
        LDA P1
        LBNZ AVITBBAD
        RLDI(P1,$0020)
        LDA P1
        XRI $0F
        LBNZ AVITBBAD
        LDN P1
        XRI $40
        LBNZ AVITBBAD
        RLDI(P1,$0024)
        LDA P1
        PHI P4
        LDN P1
        PLO P4
        RLDI(P1,$0017)
        LDN P1
        SEX SP
        STR SP
        GLO P4
        SM                      ; subtract SPARE from MEND low
        PLO P4
        GHI P4
        SMBI $00                ; carry borrow into high byte
        PHI P4
        GHI P4
        SMI $10
        LBDF AVITBMINOK
        RLDI(P4,$1000)          ; at least original 4K interpreter
AVITBMINOK:
        GHI P4
        SMI $7F
        LBDF AVITBBAD          ; 7F00 monitor RAM/ROM is excluded
        RCOPY(INTPC,P4)
        LDI 0
        ADI 0                   ; DF=0 (success)
        RETURN
AVITBBAD:
        LDI 0
        SMI 0                   ; DF=1 (failure)
        RETURN

AVICTBERR:
        OUTSTR(AVICTBMSG)
        RETURN
AVICRANGE:
        OUTSTR(AVICRMSG)
        RETURN
AVICSVMSG:
        .TEXT "CASSAVE: START RECORD, THEN PRESS KEY\r\n\000"
AVICLDMSG:
        .TEXT "CASLOAD: START PLAY, THEN PRESS KEY\r\n\000"
AVICDONE:
        .TEXT "CASSETTE TRANSFER COMPLETE\r\n\000"
AVICPARERR:
        .TEXT "?CASSETTE PARITY OR DATA ERROR\r\n\000"
AVICTBMSG:
        .TEXT "?NOT EXPECTED NETRONICS TINY BASIC IMAGE\r\n\000"
AVICRMSG:
        .TEXT "?CASSETTE RANGE MUST END BELOW 7F00\r\n\000"
#endif
