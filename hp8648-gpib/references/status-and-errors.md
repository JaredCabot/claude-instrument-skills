# Status reporting and error/message numbers

## Status model (service guide Fig. 2-1)

```
POWer condition            MODulation condition        PAGing condition (1EP)
 bit0 Reverse power (RPP)   bit0 Ext mod level HIGH     bit0 Start of frame/batch
 bit1 Unspecified amplitude bit1 Ext mod level LOW      bit1 End of encoding
        │                           │                           │
        ▼ (summary)                 ▼ (summary)                 ▼ (summary)
QUEStionable: bit3 POWer*   bit7 MODulation (=128)      bit12 PAGing (=4096)
              bit8 CALibration* (FEXTension sub-register)
        │
        ▼
Status Byte: bit3 QUES summary (*SRE 8 to get SRQ), bit4 MAV, bit5 ESB, bit6 MSS/RQS
Standard Event (*ESR?): bit0 OPC, bit1 Request Control, bit2 Query err, bit3 Device err,
                        bit4 Execution err, bit5 Command err, bit6 User request, bit7 Power on
```
\* The manual shows bit numbers only for MOD (7) and PAG (12). POWer = 3 and CAL = 8 follow
the SCPI convention and have not been verified on hardware yet.

Live example (8648C, nothing connected to MOD INPUT, EXT source selected, after power-up):
`STAT:QUES:MOD:COND?` → `+2` (ext level LOW), `STAT:QUES:COND?` → `+128`, `*ESR?` → `+128`
(power-on), `*STB?` → `+16`.

### Recipes
* **SRQ on external modulation level out of range**: `STAT:QUES:MOD:ENAB 3;:STAT:QUES:ENAB 128;*SRE 8`, then serial poll.
* **Check reverse power protection**: `STAT:QUES:POW:COND?` bit 0. To reset, remove the RF source and send `OUTP:STAT ON`.
* **Unspecified level**: `STAT:QUES:POW:COND?` bit 1 (level > +10 dBm, or ATTN HOLD vernier range exceeded).
* **1EP end of encoding**: `STAT:QUES:PAG:ENAB 2;:STAT:QUES:ENAB 4096;*SRE 8`; start of frame: `PAG:ENAB 1`.

## SCPI error queue (`SYST:ERR?`)

| Code | Text | Typical cause on the 8648 |
|---|---|---|
| 0 | No error | |
| −101 | Invalid character | e.g. `SETUP&` |
| −102 | Syntax error | |
| −103 | Invalid separator | missing `;` |
| −104 | Data type error | |
| −105 | GET not allowed | |
| −108 | Parameter not allowed | too many parameters |
| −109 | Missing parameter | |
| −111 | Header separator error | |
| −112 | Program mnemonic too long | header > 12 chars |
| −113 | Undefined header | command does not exist on the 8648 (e.g. `DIAG:INFO:OPT?`) |
| −121 | Invalid character in number | |
| −123 | Exponent too large | |
| −124 | Too many digits | |
| −128 | Numeric data not allowed | |
| −131 | Invalid suffix | wrong unit for the parameter |
| −134 | Suffix too long | |
| −141 | Invalid character data | wrong enum |
| −144 | Character data too long | |
| −148 | Character data not allowed | |
| −158 | String data not allowed | |
| −168 | Block data not allowed | |
| −178 | Expression data not allowed | |
| −221 | Settings conflict | second modulation turned on; `CAL:DCFM` without EXT DC FM |
| −222 | Data out of range | value outside the model's range or the deviation limit |
| −224 | Illegal parameter value | |
| −241 | Hardware missing | pulse modulation without 1E6 |
| −330 | Self-test failed | |
| −350 | Queue overflow | |
| −410 | Query INTERRUPTED | new command before the reply was read |
| −420 | Query UNTERMINATED | read without a pending query (often after a failed query: do a device clear) |
| −430 | Query DEADLOCKED | |
| −440 | Query UNTERMINATED after indefinite response | |

## Front-panel operation messages

| No. | Message |
|---|---|
| 001 | No external dc coupling for PM |
| 002 | Modulation exceeds deviation range |
| 003 | There are no registers available |
| 004 | Invalid units selection |
| 005 | Increment value entry out of range |
| 006 | End of increment range |
| 007 | Entered value out of range |
| 010 | End of knob range |
| 011 | Amplitude exceeds ATTN HOLD limits (vernier exceeded by > 5 dB) |
| 017 | Copying registers from 8647/8 (83301A memory interface) |
| 020 | Press SAV to copy memory FROM 8647/8 |
| 021 | DCFM calibration in progress |
| 022 | Press SAV to copy memory TO 8647/8 |
| 023 | Copying registers to 8647/8 |
| 024 | Invalid data in Memory Interface |
| 025 | Communication failure: copy aborted |
| 026 | Memory copy was successful |
| — | "Five second self test ..." while `*TST?` runs |

## Service error messages (5xx/6xx, power-up self test)

| No. | Message | Check / replace |
|---|---|---|
| 502 | Updated cal file (RAM updated from cal ROM) | normal after a module swap |
| 503 | Cal corrupt: restored | no action |
| 504 | Modulation cal restore failure | A3 |
| 505 | FM sense cal restore failure | A5 (cal ROM), then A3 (RAM) |
| 506 | FM mult cal restore failure | A5, then A3 |
| 507 | Output level cal restore failure | A6, then A3 |
| 508 | Attenuator cal restore failure | A7, then A3 |
| 509 | Timebase cal restore failure | A4, then A3 |
| 510 | Temperature cal restore failure | A7, then A3 |
| 511 | TC coeff's cal restore failure | A7, then A3 |
| 512 | Generic path cal restore failure | A3 |
| 513 | Output tune cal restore failure | A6, then A3 |
| 515 | FreqExt level cal restore failure | A10, then A3 |
| 516 | Config cal restore failure | A3 |
| 517 | Output prelevel cal restore failure | A6, then A3 |
| 518 | Atten comp loss cal restore failure | A3 |
| 514 | Failed attempt to access cal file (not in the service guide; from the firmware) | A3 |
| 519 | Output LF level cal restore failure (firmware only) | A3 |
| 520 | LF Attenuator cal restore failure (firmware only) | A3 |
| 521 | DSP cal restore failure (firmware only) | A3 |
| 601 | −12 V power supply failure (dropped > 0.4 V) | A3 −12 V regulator / A2 −15 V |
| 603 | +12 V power supply failure | A3 +12 V regulator / A2 +15 V |
| 604 | +38 V power supply failure (dropped > 2.2 V) | A2 +38 V |
| 605 | ALC out-of-lock div/het/main band | A6 output, A5 synth input, A4 ref (het only → A4) |
| 608 | Synth out-of-lock div/het/main band | A5, or A4 reference |
| 611 | 200 kHz reference missing at synth | A4 200 kHz out → A5 |
| 612 | Reference out-of-lock at 10 MHz | remove ext ref; then A4 |
| 613 | Reference out-of-lock at 1 GHz | A4 |
| 614 | 400 Hz modulation source failed | A4 200 kHz → A3 |
| 615 | 1 kHz modulation source failed | A3 (if 400 Hz passed) |
| 616 | AM modulation path failure | A3 |
| 617 | FM modulation path failure | A3 |
| 618 | PM modulation path failure | A3 |
| 619 | Modulation 20 dB step failure | A3 |
| 620 | Comm failure: <assembly> | A3 controller and/or the named assembly |
| 625 | ROM checksum failure | motherboard–ROM board connection |
| 626 | Volatile RAM read/write failure | A3 |
| 627 | Battery RAM failure: memory lost | battery (or DEL held at power-up) |
| 628 | Non-volatile RAM read/write failure | A3 |
| 629 | dsp board failure | DSP board on the display, then A3 |
| 700 | Reverse power: Press a key to reset (firmware only) | remove the source, press a key or `OUTP:STAT ON` |
| 701 | Temperature correction failed (firmware only) | A3 / output board |

Assemblies: A1 front panel, A2 power supply, A3 motherboard/controller (cal RAM), A4 reference,
A5 sig-gen synth, A6 output, A7 attenuator (8648A), A10 frequency extension (B/C/D),
A11 attenuator (B/C/D), A12 reverse-power protection (B/C/D), A13 pulse modulator (1E6),
A14 modulation generator (1E2), A30 pager encoder (1EP).
