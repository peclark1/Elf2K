; Historical 1979 Netronics ELF II CHIP-8 ROM launcher.
; Built only in experimental AVI ELF II ROM with AVIELF2 enabled.
; Period code is copied byte-for-byte from real-hardware-verified images,
; EXCEPT THREE CHANGED BYTES within interpreter RAM $0105-$0109: RCA
; VIP F-group dispatcher / FX07 handler: 45 A3 98 56 D4.
; The 1979 Netronics listing copied 01 B5 F8 56 D4 here, which breaks
; FX07 and FX0A (confirmed via RAM-only patch on actual AVI ELF II).
; No changes to historic period OS IRQ handler ($0D46).
;
; Commands:
;   CHIP8 FOUR  -- copy the proven four-square CHIP-8 test into $0200/$0300
;   CHIP8 MAZE  -- copy proven Maze game into $0200
;   CHIP8       -- run an already-loaded standard VIP 64x32 game at $0200
;   CHIP8 LIST  -- show 27 ROM-resident original VIP game titles
;   CHIP8 01..1B -- copy the selected ROM game to RAM $0200 and launch
;
; This driver overlays $0000-$01FF and $0C00-$0DFF with the original
; Netronics interpreter/OS and clears $0A00-$0BFF for display/workspace.
; It deliberately *preserves* $0200-$09FF for user-supplied CHIP-8 programs.
; After copying $0E80 startup stub, sets R0=$0E80, X=0, P=0. The stub
; uses RET with inline $00 to set IE=1, then branches to $0C10.
; This is essential! Monitor RUN normally leaves IE disabled, the exact
; cause of garbage PIXIE display in prior bench tests.
; Console inaccessible once CDP1861 DMA starts; hardware RESET back to ROM.
;
#ifdef AVIELF2
        .ORG $D000
AVICHIP8:
        CALL(F_LTRIM)
        CALL(ISEOL)
        LBDF AVICH8START          ; empty command: run pre-loaded game
        LDN P1
        CALL(ISHEX)              ; a hex game number follows CHIP8?
        LBDF AVICH8NUMBER
        RLDI(P2,AVICH8ARGS)
        LBR COMND
AVICH8ARGS:
        CMD(4,"FOUR",AVICH8FOUR)
        CMD(4,"MAZE",AVICH8MAZE)
        CMD(4,"LIST",AVICH8LIST)
        .DB 0

AVICH8FOUR:
        CALL(ISEOL)
        LBNF CMDERR
        RLDI(P2,AVICH8FOURDATA)
        RLDI(P3,$0200)
        RLDI(P4,$001A)
        CALL(AVICH8COPY)
        RLDI(P2,AVICH8SPRITEDATA)
        RLDI(P3,$0300)
        RLDI(P4,$0008)
        CALL(AVICH8COPY)
        LBR AVICH8START

AVICH8MAZE:
        CALL(ISEOL)
        LBNF CMDERR
        RLDI(P2,AVICH8MAZEDATA)
        RLDI(P3,$0200)
        RLDI(P4,$0022)
        CALL(AVICH8COPY)
        LBR AVICH8START

; Install 1979 interpreter and OS from ROM into native low-RAM addresses.
AVICH8START:
        RLDI(P2,AVICH8CORE)
        RLDI(P3,$0000)
        RLDI(P4,$0200)
        CALL(AVICH8COPY)
        RLDI(P2,AVICH8OS)
        RLDI(P3,$0C00)
        RLDI(P4,$0200)
        CALL(AVICH8COPY)
; Clear the CHIP-8 register pages and PIXIE display page. IMPORTANT:
; do not zero $0200-$09FF! That's where user-loaded games and sprites go.
        RLDI(P3,$0A00)
        RLDI(P4,$0200)
AVICH8CLEAR:
        LDI $00
        STR P3
        INC P3
        DEC P4
        GHI P4
        LBNZ AVICH8CLEAR
        GLO P4
        LBNZ AVICH8CLEAR
; Copy the exact 6-byte hardware-verified enable-interrupt bootstrap.
        RLDI(P2,AVICH8STUBDATA)
        RLDI(P3,$0E80)
        RLDI(P4,$0006)
        CALL(AVICH8COPY)
; Equivalent to ROM monitor's RUN 0E80, not RUN 0000.
; No subsequent SCRT/monitor calls are permitted once P switches to R0.
        RLDI(0,$0E80)
        SEX 0
        SEP 0
        LBR MAIN                 ; never reached

; P2=ROM src, P3=RAM dest, P4=positive 16-bit count.
; CALL/RETURN via monitor SCRT, caller prepares register values.
AVICH8COPY:
AVICH8COPY1:
        LDA P2
        STR P3
        INC P3
        DEC P4
        GHI P4
        LBNZ AVICH8COPY1
        GLO P4
        LBNZ AVICH8COPY1
        RETURN


; Game selection routines stay entirely in the former spare ROM D100-D1FF.
; Catalog from a separately assembled source occupies F100-F2AF:
; 27 records x 16 bytes = big-endian source, length, 12-byte ASCII name.
        .ORG $D100
AVICH8NUMBER:
        CALL(SCANP1)             ; monitor interprets game ID as hexadecimal
        CALL(ISEOL)
        LBNF CMDERR
        GHI P2
        LBNZ CMDERR
        GLO P2
        LBZ CMDERR               ; reject 00
        SMI $1C
        LBDF CMDERR              ; reject 1C or above: valid 01..1B

; Entry n lies at F100 + (n-1)*16. Iterate rather than multiply 16-bit.
        RLDI(P3,$F0F0)
AVICH8NUMLOOP:
        GLO P3
        ADI $10
        PLO P3
        GHI P3
        ADCI $00
        PHI P3
        DEC P2
        GLO P2
        LBNZ AVICH8NUMLOOP
; Load big-endian source pointer and length; all paths use existing copier.
        LDA P3
        PHI P2
        LDA P3
        PLO P2
        LDA P3
        PHI P4
        LDN P3
        PLO P4
        RLDI(P3,$0200)
        CALL(AVICH8COPY)
        LBR AVICH8START

AVICH8LIST:
        CALL(ISEOL)
        LBNF CMDERR
        RLDI(P3,$F100)
        RCLEAR(P4)
        INC P4
AVICH8LISTLOOP:
        GLO P4
        CALL(THEX2)              ; display ID as hexadecimal 01..1B
        OUTCHR(' ')
        RCOPY(P1,P3)
        INC P1
        INC P1
        INC P1
        INC P1                   ; offset 4 = zero-terminated name
        CALL(F_MSG)
        CALL(TCRLF)
        GLO P3
        ADI $10
        PLO P3
        GHI P3
        ADCI $00
        PHI P3
        INC P4
        GLO P4
        SMI $1C
        LBNF AVICH8LISTLOOP
        LBR MAIN

; The original 1979 Netronics byte strings are maintained except for the
; five-byte RCA VIP FX dispatch sequence in CORE at $0105 (only\n; three actual byte differences from the unmodified historical listing).
        .ORG $D800
AVICH8CORE:
        .DB $C0,$0C,$10,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00
        .DB $B4,$F8,$1B,$A4,$F8,$01,$B5,$F8,$FC,$A5,$D4,$96,$B7,$E2,$94,$BC
        .DB $45,$AF,$F6,$F6,$F6,$F6,$32,$44,$F9,$50,$AC,$8F,$FA,$0F,$F9,$F0
        .DB $A6,$05,$F6,$F6,$F6,$F6,$F9,$F0,$A7,$4C,$B3,$8C,$FC,$0F,$AC,$0C
        .DB $A3,$D3,$30,$1B,$8F,$FA,$0F,$B3,$45,$30,$40,$22,$69,$12,$D4,$00
        .DB $00,$01,$01,$01,$01,$01,$01,$01,$01,$01,$01,$01,$01,$00,$01,$01
        .DB $00,$7C,$75,$83,$8B,$95,$B4,$B7,$BC,$91,$EB,$A4,$D9,$70,$99,$05
        .DB $06,$FA,$07,$BE,$06,$FA,$3F,$F6,$F6,$F6,$22,$52,$07,$FA,$1F,$FE
        .DB $FE,$FE,$F1,$AC,$9B,$BC,$45,$FA,$0F,$AD,$A7,$F8,$D0,$A6,$93,$AF
        .DB $87,$32,$F3,$27,$4A,$BD,$9E,$AE,$8E,$32,$A4,$9D,$F6,$BD,$8F,$76
        .DB $AF,$2E,$30,$98,$9D,$56,$16,$8F,$56,$16,$30,$8E,$00,$EC,$F8,$D0
        .DB $A6,$93,$A7,$8D,$32,$D9,$06,$F2,$2D,$32,$BE,$F8,$01,$A7,$46,$F3
        .DB $5C,$02,$FB,$07,$32,$D2,$1C,$06,$F2,$32,$CE,$F8,$01,$A7,$06,$F3
        .DB $5C,$2C,$16,$8C,$FC,$08,$AC,$3B,$B3,$F8,$FF,$A6,$87,$56,$12,$D4
        .DB $9B,$BF,$F8,$FF,$AF,$93,$5F,$8F,$32,$DF,$2F,$30,$E5,$00,$42,$B5
        .DB $42,$A5,$D4,$8D,$A7,$87,$32,$AC,$2A,$27,$30,$F5,$00,$00,$00,$00
        .DB $00,$00,$00,$00,$F8,$45,$A3,$98,$56,$D4,$F8,$0D,$BC,$F8,$95,$AC
        .DB $22,$DC,$12,$56,$D4,$06,$B8,$D4,$06,$A8,$D4,$64,$0A,$01,$E6,$8A
        .DB $F4,$AA,$3B,$28,$9A,$FC,$01,$BA,$D4,$F8,$0D,$BA,$06,$FA,$0F,$AA
        .DB $0A,$AA,$D4,$F8,$0C,$BC,$F8,$AD,$AC,$DC,$30,$53,$00,$F8,$0C,$BC
        .DB $F8,$D1,$AC,$DC,$30,$A0,$F8,$0C,$BC,$F8,$E8,$AC,$DC,$30,$A3,$00
        .DB $00,$00,$2A,$D4,$00,$22,$86,$52,$F8,$F0,$A7,$07,$5A,$87,$F3,$17
        .DB $1A,$3A,$5B,$12,$D4,$22,$86,$52,$F8,$F0,$A7,$0A,$57,$87,$F3,$17
        .DB $1A,$3A,$6B,$12,$D4,$15,$85,$22,$73,$95,$52,$25,$45,$A5,$86,$FA
        .DB $0F,$B5,$D4,$45,$E6,$F3,$3A,$82,$15,$15,$D4,$45,$E6,$F3,$3A,$88
        .DB $D4,$45,$07,$30,$8C,$45,$07,$30,$84,$30,$F2,$5E,$45,$A3,$30,$3D
        .DB $D4,$30,$46,$D4,$F8,$F0,$A7,$E7,$45,$F4,$A5,$86,$FA,$0F,$3B,$B2
        .DB $FC,$01,$B5,$D4,$45,$56,$D4,$45,$E6,$F4,$56,$D4,$45,$FA,$0F,$3A
        .DB $C4,$07,$56,$D4,$AF,$22,$F8,$D3,$73,$8F,$F9,$F0,$52,$E6,$07,$D2
        .DB $56,$F8,$FF,$A6,$F8,$00,$7E,$56,$D4,$19,$89,$AE,$93,$BE,$99,$EE
        .DB $F4,$56,$76,$E6,$F4,$B9,$56,$45,$F2,$56,$D4,$45,$AA,$86,$FA,$0F
        .DB $BA,$D4,$F8,$0F,$BE,$F8,$FF,$AE,$06,$30,$9B,$00,$00,$E0,$00,$4B

AVICH8OS:
        .DB $F8,$0C,$B2,$F8,$06,$A2,$E2,$D2,$F8,$FF,$A1,$F8,$0B,$B1,$30,$28
        .DB $F8,$0C,$B0,$F8,$16,$A0,$D0,$30,$93,$00,$00,$00,$00,$00,$00,$00
        .DB $00,$00,$00,$00,$00,$00,$00,$00,$E1,$F8,$00,$73,$81,$FB,$AF,$3A
        .DB $29,$F8,$D2,$73,$F8,$9F,$51,$81,$A0,$91,$B0,$F8,$CF,$A1,$D0,$73
        .DB $20,$20,$40,$FF,$01,$20,$50,$FB,$82,$3A,$3E,$92,$B3,$F8,$51,$A3
        .DB $D3,$90,$B2,$BB,$BD,$F8,$0D,$B1,$B4,$B5,$B7,$BA,$BC,$F8,$46,$A1
        .DB $F8,$AF,$A2,$F8,$DD,$A4,$F8,$C6,$A5,$F8,$BA,$A7,$F8,$95,$AC,$E2
        .DB $69,$DC,$D7,$D7,$D7,$B6,$D7,$D7,$D7,$A6,$D4,$DC,$BE,$32,$8A,$FB
        .DB $0A,$32,$85,$30,$83,$DC,$16,$D4,$30,$85,$D7,$D7,$D7,$56,$D4,$16
        .DB $30,$8A,$00,$F8,$0B,$BB,$F8,$0A,$B2,$B6,$F8,$CF,$A2,$F8,$0D,$B1
        .DB $F8,$46,$A1,$F8,$00,$B4,$F8,$1B,$A4,$C0,$00,$14,$00,$E6,$06,$BF
        .DB $9C,$BE,$F8,$CE,$AE,$2A,$1A,$F8,$00,$5A,$0E,$F5,$3B,$C5,$56,$0A
        .DB $FC,$01,$5A,$30,$BA,$4E,$F6,$3B,$B6,$9F,$56,$2A,$2A,$D3,$64,$0A
        .DB $01,$3F,$E7,$F8,$FF,$AF,$BF,$AE,$F8,$0F,$BE,$EF,$6C,$FA,$0F,$EE
        .DB $F3,$FA,$0F,$3A,$E7,$15,$15,$D3,$3F,$E5,$F8,$FF,$AF,$BF,$AE,$F8
        .DB $0F,$BE,$EF,$6C,$FA,$0F,$EE,$F3,$FA,$0F,$3A,$E5,$D3,$00,$00,$00
        .DB $30,$39,$22,$2A,$3E,$20,$24,$34,$26,$28,$2E,$18,$14,$1C,$10,$12
        .DB $F0,$80,$F0,$80,$F0,$80,$80,$80,$F0,$50,$70,$50,$F0,$50,$50,$50
        .DB $F0,$80,$F0,$10,$F0,$80,$F0,$90,$F0,$90,$F0,$10,$F0,$10,$F0,$90
        .DB $F0,$90,$90,$90,$F0,$10,$10,$10,$10,$60,$20,$20,$20,$70,$A0,$A0
        .DB $F0,$20,$20,$7A,$42,$70,$22,$78,$22,$52,$C4,$19,$F8,$00,$A0,$9B
        .DB $B0,$E2,$E2,$80,$E2,$E2,$20,$A0,$E2,$20,$A0,$E2,$20,$A0,$3C,$53
        .DB $98,$32,$67,$AB,$2B,$8B,$B8,$88,$32,$43,$7B,$28,$30,$44,$D3,$F8
        .DB $0A,$3B,$76,$F8,$20,$17,$7B,$BF,$FF,$01,$3A,$78,$39,$6E,$7A,$9F
        .DB $30,$78,$D3,$F8,$10,$3D,$85,$3D,$8F,$FF,$01,$3A,$87,$17,$9C,$FE
        .DB $35,$90,$30,$82,$D3,$F8,$FF,$AF,$BF,$EF,$3F,$9A,$37,$9C,$6C,$FA
        .DB $0F,$52,$E2,$30,$94,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00
        .DB $00,$00,$00,$00,$00,$00,$00,$00,$00,$D3,$DC,$FE,$FE,$FE,$FE,$AE
        .DB $DC,$8E,$F1,$30,$B9,$D4,$AA,$0A,$AA,$F8,$05,$AF,$4A,$5D,$8D,$FC
        .DB $08,$AD,$2F,$8F,$3A,$CC,$8D,$FC,$D9,$AD,$30,$C5,$D3,$22,$06,$73
        .DB $86,$73,$96,$52,$F8,$06,$AE,$F8,$D8,$AD,$02,$F6,$F6,$F6,$F6,$D5
        .DB $42,$FA,$0F,$D5,$8E,$F6,$AE,$32,$DC,$3B,$EA,$1D,$1D,$30,$EA,$01

AVICH8FOURDATA:
        .DB $00,$E0,$60,$08,$61,$04,$A3,$00,$D0,$18,$60,$28,$D0,$18,$60,$08
        .DB $61,$0C,$D0,$18,$60,$28,$D0,$18,$12,$18

AVICH8SPRITEDATA:
        .DB $FF,$81,$81,$81,$81,$81,$81,$FF

AVICH8MAZEDATA:
        .DB $A2,$1E,$C2,$01,$32,$01,$A2,$1A,$D0,$14,$70,$04,$30,$40,$12,$00
        .DB $60,$00,$71,$04,$31,$20,$12,$00,$12,$18,$80,$40,$20,$10,$20,$40
        .DB $80,$10

AVICH8STUBDATA:
        .DB $E0,$70,$00,$C0,$0C,$10
#endif
