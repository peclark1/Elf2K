; AVI ELF II / Hyperboard CDP1854 MODE 1 polling console.
; Copyright 2026. Adapted for the AVI ROM from the RCA CDP1854 datasheet.
; This module is incorporated into the DISPOSABLE Rc/Asm bios source by
; sw/build/avi-port.py, replacing the stock 8250/16550 UART implementation.
;
; This is an experimental 9600 8N1 backend, activated only with the monitor
; UART command. This ROM variant starts on Q/EF4. The Q/EF3 875B baseline remains separate.
;
; Hardware assumptions to verify:
;   CDP1854 MODE=1; CS1=N1; RSEL=N0; CS3 asserted; CS2 controlled by J14.
;   INP 2/OUT 2 = receiver/transmitter data.
;   INP 3/OUT 3 = status/control.
;   OUT 5 (I65 via J3) = CDP1863 divisor latch, N=0.
;   CDP1863 clocks routed to both CDP1854 TCLK and RCLK via J10/J11.
;   Expected oscillator 2.4576 MHz, divider CLK2, yielding 153.6 kHz
;   for CDP1854 x16 9600 bps. VERIFY WITH A SCOPE, not by assumption.
;   Status bit7 THRE, bit0 DA. Control $19 = 8N1 parity inhibited;
;   $99 = transmit request enabled, interrupts disabled.
;
; No 8250 register-select accesses. No interrupts, no DMA modifications.

e2k_timalc:
        lbr     timalc_o       ; always acquire startup BAUD via Q/EF

e2k_brk:
        ghi     re
        ani     0feh
        lbz     f_utest
        lbr     f_btest

e2k_tx:
        plo     re             ; char in RE.0
        ghi     re
        ani     0feh           ; 0/1 selects hardware UART
        lbz     avi_tx_hw
        glo     re
        lbr     f_btype
avi_tx_hw:
        glo     re
        lbr     f_utype

e2k_rx:
        ghi     re
        ani     0feh
        lbz     f_uread
        lbr     f_bread

; Input/control/status are directly decoded CDP1802 I/O (not 8250 ports).
e2k_utest:
        sex     r2
        inp     3              ; CDP1854 status register
        shr                    ; DA status bit 0 -> DF
        sep     sret

e2k_uread:
avi_rx_wait:
        sex     r2
        inp     3
        ani     1              ; DA status
        lbz     avi_rx_wait
        inp     2              ; received byte; also resets DA
        plo     re
        ghi     re
        shr                    ; echo if RE.1 bit 0
        glo     re
        lbdf    e2k_utype
        sep     sret

e2k_utype:
        stxd                   ; temporarily push character (decrements R2)
avi_tx_wait:
        sex     r2
        inp     3
        ani     080h           ; THRE status bit 7
        lbz     avi_tx_wait
        irx                    ; point to saved character
        ldx                    ; restore D: BIOS F_READ must return the received character after echo
        out     2              ; CDP1854 transmitter holding register
        dec     r2             ; OUT increments R(X): restore stack
        sep     sret

; Initial experimental setting for 2.4576 MHz oscillator and divider.
; If a board uses different jumpers/clock source, OUT 5 may not load A14.
; D = old Elf2K port parameters (currently ignored; fixed 9600 8N1).
e2k_stbd:
        plo     re
        sex     r3
        out     5
        db      000h           ; CDP1863 N=0 when J3 selects I65
        out     3
        db      019h           ; 8 data, 1 stop, no parity, TR=0
        out     3
        db      099h           ; TR=1, RTS active, IE=0
        sex     r2
        adi     0              ; report success DF=0
        sep     sret
