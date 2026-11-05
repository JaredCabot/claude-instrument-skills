# Undocumented SERVice / DIAGnostic commands (HP 8648)

These commands were reverse-engineered from Agilent's 8648 Service Support Software (all
binaries decompiled). Full evidence is in `docs/re/service-commands.md`. Lines marked ✔ were
verified on a live **8648C, firmware B.04.08** on 2026-10-05.

## Golden rules

1. **Queries only, unless the user explicitly asks for a write and confirms it.**
2. **Back up first:**
   `python scripts/hp8648_calbackup.py backup --addr GPIB0::19::INSTR`, and
   `... compare old.json new.json` afterwards.
3. **Never read cal arrays that belong to option hardware the unit doesn't have.**
   ✔ `SERV:PRODUCTION:CAL? dsp_2fsk_cal,0` on an 8648C without 1EP caused a **"Fatal firmware
   error"**. The instrument stopped answering GPIB, even device clear and IFC, until it was power
   cycled. Calibration was verified unchanged afterwards. Treat `dsp_*` (1E2/1EP DSP) and other
   FSK/pager/encoder arrays (`*fsk*`, `*pag*`, `*enc*`, `dsp_sin_cal`) as **option-only**.
4. **Never read past the last element.** ✔ `outllvl_frq,6` (the array has 6 elements) halted the
   firmware with "assertion failure 597: h:FileMgr.m,v 1.18". Use only the exact counts below.
5. Do not "discover" array names or lengths by trial. Unknown *queries* are mostly harmless
   (−113/−224), but rules 3 and 4 show that even reads can crash the firmware. Never guess write
   commands.

## Reading calibration arrays (safe for the arrays listed below)

`SERV:PRODUCTION:CAL? <array>,<index>` reads one element. ✔
* Array names are case-insensitive and at most 12 characters (longer → −112 "Program mnemonic
  too long"). Indices start at 0.
* Unknown array → no reply, error −224 "Illegal parameter value". Index past the end → usually
  −224 "Index into file is outside of legal range!", **but on some arrays (`outllvl_frq`) a
  firmware crash**, so never rely on it. The −224 replies also leave −420
  (query unterminated): device clear and drain `SYST:ERR?`. ✔
* Numeric array ids (`165,0`) are rejected with −128 on B.04.08, although an unused helper in
  the motherboard utility tries them. ✔
* STORE/file names (`OUT_LOSS`, `Outlvl_data`, `OUT_TUNE_CAL`, …) are *not* readable arrays. ✔

Arrays present on the 8648C (element counts) ✔:

| Array | n | Meaning (inferred from the adjustment that writes it) | Written by |
|---|---|---|---|
| `config_cal` | 5 | [0] min freq, [1] max freq (Hz in the reply; stored as kHz), [2] options word (bits below), [3] min settable amplitude dBm (−136), [4] max settable amplitude dBm (13/14.5; ≥ +16.01 makes `*OPT?` report HIGH POWER = 1EA) [fw] | motherboard utility |
| `config2_cal` | 1 | 10: level (dBm) above which the AM ALC bandwidth is reduced [fw] | motherboard utility |
| `timebase` | 2 | reference DAC coarse, fine (0–255) | ATBASE / TIMEBASE ADJ switch |
| `out_pre_pwr` | 7 | preleveler constants (2.5e9, 14, 4, 16, 12, 4, 16) | motherboard utility |
| `atn_comp_cal` | 106 | attenuator compensation (dB) | motherboard utility defaults / factory |
| `gen_loss_cal` | 34 | general path loss vs frequency (0 after the AM-level adjustment) | AAMLVL*, motherboard utility |
| `out_lvl_gain`, `out_lvl_ofs` | 32 | output-level DAC slope/offset vs frequency (8648A main band, B/C/D prelevel) | AOM_LVL, APRE_LVL (store `Outlvl_data`) |
| `fextlvl_gain`, `fextlvl_ofs` | 108 | frequency-extension level slope/offset | AFE_LVL (store `fextlvl_data`) |
| `outllvl_gain`, `outllvl_ofs` | 6 | LF (9–100 kHz) output level slope/offset | AOMLLVL (store `Out_lf_data`) |
| `out_0db` … `out_130db` | 22 each | level correction per attenuator step (dB) vs frequency | AHF_PLA (store `out_loss`) |
| `outl_0db` … `outl_130db` | 6 each | LF level correction per attenuator step | ALF_PLA (store `out_lf_loss`) |
| `mod_am_1khz/400hz/extdc/extac` | 2 | AM path full-scale DAC values | AAUDPATH (store `mod_dac`) |
| `mod_fm_*`, `mod_pm_*` (same suffixes) | 4 | FM/PM path full-scale DAC values | AAUDPATH |

More arrays. Counts are for B/C/D, with 8648A in brackets, and all agree with firmware
B.04.08's read routines (`docs/re/firmware-b0408-report.md`). The *_frq arrays hold the frequency
points of the matching data arrays and cannot be written.
`gen_loss_frq` 34 · `out_loss_frq` 22 (34) · `outlloss_frq` 6 · `atn_comp_frq` 106 (A: none) ·
`fextlvl_frq` 108 (A: none) · `fm_acfm_dac` 1 (A: none) · `out_lvl_frq` 32 · `outllvl_frq` **6, index 6
crashes** · `fm_sens_frq` 44 · `fm_sens_sgn` 44 · `fm_sens_mult` 1 · `out_tune_frq` 25 ·
`out_tune_dac` 25 · `out_temp_cal` 1 · `tc_thru_path`, `tc_10_40db`, `tc_50_70db`, `tc_80_100db`,
`tc_110_130db` 3 each. The authoritative list is `scripts/known_arrays.txt`; the backup tool refuses any index beyond it.
`gen_loss_frq` and `gen_loss_cal` have 34 elements on every model (firmware limit; the 8648C
answered all 34). `outllvl_frq` is the one array whose read routine has no index check.

Option-only arrays (read **only** if the option is fitted): `dsp_sin_cal` (1E2/1EP audio
generator, AAUDENC), `dsp_2fsk_cal`, `dsp_4fsk_cal` (1EP filter path, APG_ENC). The
`fm_sens_*` arrays are standard: YO4HFU reads them on an 8648B, and 1EP exists only on the 8648A.

Board IDs for `SERV:BOARDID?`: `MOTHER_BD`, `OUTPUT_BD`, `SYNTH_BD`, `REF_BD`, `ATTEN_BD`,
`FREQ_EXT_BD`. Typical CONFIG_CAL[2] values for B/C/D: 97/99 = no options, 101 = 1E6,
105 = H01, 225 = 1E2 (YO4HFU).

`config_cal[2]` bits (from firmware B.04.08): 0x01 model B/C/D (clear = 8648A), 0x02 default
low-band breakpoints from 100 kHz (clear: 250 kHz), 0x04 pulse 1E6, 0x08 when clear the
pulse/RF-off state is reset at power-on [inferred], 0x10 150 Hz internal source instead of
400 Hz, 0x20 DC-coupled external AM allowed, 0x40 output level below 100 kHz supported, 0x80
audio generator 1E2 (DSP), 0x100 pager encoder 1EP (DSP). **1E5 and 1EA are not in this word**:
1E5 is read from a hardware ID line and 1EA is `config_cal[4]` ≥ +16.01. The 8648C here reads
**99 = 0x63**. The motherboard utility's model bases (A 0x22, B/C 0x23, D 0x61, newer B/C +0x3E)
would write 97 to this unit, clearing bit 0x02 (only the default breakpoints change).

`*OPT?` always returns six comma-terminated fields (name or 0): HIGH STABILITY REF, PULSE
MODULATION, HIGH POWER, 150 HZ MODULATION, AUDIO GENERATOR, PAGER ENCODER.

## Other read-only queries ✔

| Query | Reply (8648C) |
|---|---|
| `SERV:BOARDID? MOTHER_BD` | `"031403293\x01"`: A3 part suffix 0314, serial 03293 |
| `SERV:BOARDID? ATTEN_BD` | `"00113351A\x01"`: A11 attenuator part 0011, serial 3351A (not on 8648A) |
| `SYST:LANG?` | `"scpi"` |
| `DIAG:LATCH:SEL "<name>"` then `DIAG:LATCH:VAL?` | reads a hardware latch/DAC (the select only chooses; not verified live) |

## Write / service commands (expert only, NEVER without explicit consent)

| Command | Effect |
|---|---|
| `SERV:PRODUCTION:CAL:BEGIN` … `SERV:PRODUCTION:CAL <array>,<i>,<value>` … `SERV:PRODUCTION:CAL:END` | stage new array values |
| `SERV:PRODUCTION:CAL:STORE <group>` | **commit to calibration EEPROM.** B.04.08 groups (18): `ATN_COMP_CAL`, `CONFIG2_CAL`, `CONFIG_CAL`, `DSP_CAL`, `FEXTLVL_DATA`, `FM_SENS_KV`, `FM_SENS_MULT`, `GEN_LOSS_CAL`, `MOD_DAC`, `OUTLVL_DATA`, `OUT_LF_DATA`, `OUT_LF_LOSS`, `OUT_LOSS`, `OUT_PRE_PWR`, `OUT_TEMP_CAL`, `OUT_TUNE_CAL`, `TC_COEFF_CAL`, `TIMEBASE`. The array → group map is in `hp8648_calbackup.py` (`RESTORE_GROUP`) |
| `SERV:PRODUCTION:BOARDID <board>,"<id>"` | rewrite an assembly ID |
| `SERV:PRODUCTION:INSTRUMENT:MODEL "HP8648x"` / `:SERNUM "<sn>"` | rewrite the identity |
| `SERV:PRODUCTION:MEM:SCRATCH` | initialise (erase) scratch/state memory |
| `SERV:PRODUCTION:PUP` | executes a 68000 RESET: warm reboot (used after STORE) |
| `CAL:DCFM` | documented. Stores the DC-FM offset |
| `DIAG:LATCH:VAL #H<hex>` | raw latch/DAC write (volatile; can drive hardware out of range) |
| `SERV:PRODUCTION:MEM:BYTE\|WORD\|LONG #H<addr>,<value>` | raw memory write, no checks. The queries read memory (B.04.08: `#H` address only); an odd-address WORD/LONG or unmapped read halts the firmware |
| Holding `+/−` at power-on | rewrites every cal file with defaults |
| Holding SAV at power-on | rewrites Config2, Out LF Lvl and LF Atten EEPROM files from RAM when their checksums differ |
| `DIAG:BLOCK:DSP:RESET`, `:DSP:MOD:ABORT`, `:DSP:PATH LPF_LF\|LPF_HF\|THRU\|OFF`, `:DSP:MOD:SIN f,amp`, `:DSP:MOD:OFFSET n`, `:DSP:CAL:SETTO g,o,g,o`, `:DSP:CAL:FSK …` | 1E2/1EP DSP control (volatile) |
| `DIAG:BLOCK:SG:SYNT:CWF <f>` | set the synthesizer directly (1EP FSK cal) |
| `SERV:PRODUCTION:DISP:FILL` / `:CLEAR` | display test pattern |

Latch names used by the adjustments: `out_carrier_level_DAC`, `freq_ext_level_DAC`,
`refs_DAC_coarse`, `refs_DAC_fine`, `refs_tbase_select`, `out_service_mux`, `out_ALC_bw_cntl`,
`fext_service_level_DAC`, `fext_service_mux`, `atten_4GHz_rpp_reset`,
`atten_4GHz_am_mod_select`, `fext_ALC_state`, `modist_mod_range_DAC`, `gsyn_sdfm_FM_level_DAC`.

The service DLLs also contain ESG commands (`:SOURCE:RADIO:*`, `BURST`, `ARB`, `DIAG:BLOCK:IQCAL?`,
`SERV:PROD:CARD:DATA?`, `DIAG:BLOC:LNF:AUTO`, `SOUR:AM:WID`) from shared code. **They are not
8648 commands; do not send them.**

## Firmware

The firmware (68000, Objective-C) lives in ROMs on the **A3A1 memory board**. It can be read over
GPIB, read-only, with `SERV:PRODUCTION:MEM:LONG? #H<addr>` (B.04.08), 0x000000–0x07FFFF; the tool
is `tools/fw/gpib_romdump.py`. There is no command to load firmware. Analysis:
`docs/re/firmware.md`, `docs/re/firmware-b0408-report.md` and the reference manual
`docs/re/manual/HP8648_Firmware_Reference.pdf`. `DIAG:BLOCk:DSP:STATus?` is a single latch read;
`:TEST?` has no board-presence check (no write or halt path found; untried on a non-DSP unit).
