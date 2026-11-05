# 8648 Service Support Software (EPSG090522 rev A7.0/"7.01") on Windows 10/11

## Installing (once)

Double-click `legacy\install.cmd` in the repository, or:
```
powershell -ExecutionPolicy Bypass -File legacy\install.ps1 -Root C:\HP_SVC -SiclInterface gpib0 [-GpibLog] [-Force]
```
Uninstall from Settings > Apps > Installed apps ("HP 8648 Service Support Software").

* Requirements:
  * Keysight (or Agilent) IO Libraries with **32-bit SICL** (`C:\Windows\SysWOW64\sicl32.dll`).
  * The GPIB adapter's **SICL interface ID**, shown in Connection Expert as e.g. `gpib0`.
  * The Microsoft VC++ x86 runtime, which otvdm needs. No Python. Windows 10/11 x64 only.
* The root must be 8.3-safe (no spaces, ≤ 8 characters per folder name).
* The installer reproduces the original InstallShield layout and INI files byte-for-byte,
  installs the bundled **otvdm v0.9.0** (hash-checked), and replaces only `BIN\iolib_32.dll`
  with the shim. The original is kept as `iolib_32.orig.dll`.
* The `iolib_32.ini` shim config:
  * `[Interfaces] hpib7=gpib0`
  * `[Debug] Log=C:\HP_SVC\iolib_32.log` logs every GPIB transaction. Leave it on during
    adjustments: it is the record of what was written to the instrument.
  * `[Safety] BlockCalWrites=1`: dry run. `SERV:PRODUCTION` writes are logged as `BLOCKED` and
    not sent (the software is told they succeeded). Use it for the first run with new equipment.
  * `[Devices] <addr>=<SICL address> [3458A|33120A|8563E]`: route an instrument anywhere and,
    with a suffix, let a substitute answer the original driver: 34401A-family/34465A as 3458A,
    Siglent SDG as 33120A, Siglent SVA/SSA as 8563E. `[Emulation] SAPreamp=1` turns the SVA's
    preamp back on after every `IP`. 8901B (as HP8902A) and E4419B in 438A language (as HP438A)
    need no translation. Bench plan and caveats: `docs/bench-substitutes.md` in the repo.
* Datapack points are gated by the DUT's `*IDN?`/`*OPT?` (per-model option bit tables; codes
  `<mask><T|S><O|A>`, see `docs/re/datapacks.md` §1.4).
* Ete.ini (the equipment list) format and an example: `docs/re/architecture.md` §2.4.

## Running

| Program | Launch | Login |
|---|---|---|
| Test executive | `C:\HP_SVC\TestExec.cmd` (or Start menu "8648 Service Software") | `User` / `User` runs tests; `Admin` / `Falcon` also edits test equipment, drivers and datapacks (case-sensitive; publicly documented) |
| Motherboard Repair Utility | `C:\HP_SVC\MBUtil.cmd` | **Cancel** at the password = read-only view (auto-reads serial, model, options, board IDs). Password `8648` enables **Send Data** |

Flow: DUT Selection (family 8648, model, serial, GPIB address), then Select Test Equipment and
Tests, then a Save As log file (`C:\HP_SVC\HP8648\Log\*.log`), then Run / Stop / Restart /
Next Test / Rerun / Abort.
In Admin mode, enter every instrument first under **File ▸ Test Equipment**: model, serial,
GPIB address, cal due date and trace number. A power sensor must use GPIB address **−1** and
needs its cal-factor table (CAL DATA: frequency in MHz / cal factor in %).

> ⚠ **Never press Send Data in the Motherboard Utility unless the A3 motherboard has really
> been replaced.** Send Data erases the scratch memory and rewrites CONFIG_CAL/CONFIG2_CAL,
> OUT_PRE_PWR, the board IDs, model and serial. It also resets GEN_LOSS/OUT_LOSS/OUT_LF_LOSS and
> the level tables to defaults, so every adjustment must then be re-run.
> On a stock unit it can also clear configuration bits the utility doesn't know about. Example: an
> 8648C reads `CONFIG_CAL,2 = 99` (0x63); the utility would write 97 (0x61).
> Take a backup first: `scripts\hp8648_calbackup.py backup`. It can be put back with `restore`.

## Tests available

| Test (DLL) | Description | Models | Required test equipment |
|---|---|---|---|
| AAMLVL | AM Level and Distortion | A | DVM 3458A, function gen 33120A, J31 test-point extender |
| AAMLVL05 | AM Level | B/C/D | DVM, function gen, J31 extender |
| AAMLVLFE | AM Level: FE | B/C/D | DVM, function gen, J31 extender |
| AAMMOD | AM Modulator | A | measuring receiver 8902A, audio analyzer 8903B, function gen, DVM, J31 |
| AAUDPATH | Motherboard Audio Path | all | function gen, DVM, measuring receiver |
| ADCFM | DCFM | all | none |
| ADET_OFS | Predistortion and Detector Offset | B/C/D | power meter 438A + sensor 8482A |
| AOMDETOF | Detector Offset | A | power meter + sensor |
| AOM_LVL | Output Level | A | power meter + sensor |
| AFE_LVL | Output Level: FE | B/C/D | power meter + sensor |
| APRE_LVL | Prelevel | B/C/D | power meter + sensor |
| AOMLLVL | LF Output Level (9–100 kHz) | B/C/D (not early B/C) | DVM + 50 Ω feedthrough |
| ALF_PLA | LF Power Level Accuracy | B/C/D (not early B/C) | DVM, spectrum analyzer 8560E/8563E, 6 dB pad, feedthrough |
| AHF_PLA | HF Power Level Accuracy | all | power meter + sensor, spectrum analyzer, LF amp 8447D, HF amp 8449B, 6 dB pad |
| ATBASE | Time Base DAC | all | spectrum analyzer + 10 MHz primary standard |
| AAUDENC | Audio Generator | 1E2/1EP | DVM |
| AFSK | FSK Deviation | A 1EP | VSA 89441A |
| APG_ENC | Filter Path | A 1EP | VSA 89441A |
| PHF_PLA | Power Level Accuracy (performance test) | all | as AHF_PLA |

Default GPIB addresses expected by the drivers: 33120A=10, 3458A=22, 438A=13, 53131A/53132A=3,
8560E/8563E=18, 8663A=19, 8902A=14, 8903A/B=28, 8904A=26, 89441A=99 (set your own),
power sensor=−1, DUT 8648=19 (clashes with the 8663A default, so change one of them).

Adjustments that applied only before serial prefix 3847A/3847U (pot-based output/FE modules):
AM Level & Distortion, AM Level, Detector Offset, AM Level: FE and Predistortion & Detector
Offset. The software asks whether pots are present.

Warm-up: DUT and all test equipment for **≥ 45 min** before adjusting.

## Manual adjustments (no software)

* **Internal reference oscillator**:
  1. Power off and set the rear **TIMEBASE ADJ** switch to 1.
  2. Power on and follow the display prompts, using the knobs, until the counter (locked to a
     primary standard) reads 100 MHz ± 1 Hz at the RF output.
  3. Power off and set the switch back to 0.
  Equivalent to the automated ATBASE (writes cal array `timebase`, 2 elements = coarse/fine DAC).
* **Pager encoder timebase (1EP)**:
  1. Select FM, ENCODER, FORMAT=SERVICE, CALIBRATION FSK=3200/2 and START.
  2. Trim the "TIMEBASE ADJUST 1EP" capacitor until MOD OUT reads 1600 Hz ± 0.0016 Hz.

## Which adjustments after which repair (service guide table 5-2, abridged)

A3 motherboard: all (after the motherboard utility). A3A1 memory (ROM) board: none.
A3BT1 battery: DCFM. A4 reference: Time Base DAC. A5 synth: DCFM and FSK Deviation (1EP).
A6 output: Output Level/Prelevel family + AM + HF PLA. A7/A11 attenuator: HF PLA (+ LF PLA).
A10 FE: Output Level: FE, AM Level: FE, Predistortion & Det Offset.
A14/A30: Audio Generator (+ Filter Path, FSK for 1EP).

## Under the hood (for debugging)

`testexec.exe` → test DLL (`HP8648\Adj\a*.dll`, `Perf\phf_pla.dll`) driven by a datapack
(`HP8648\DP\*.00n`), then the equipment drivers (`DRIVERS\drv*.dll`) and the DUT driver
`drv8648.dll`, then `io_sicl.dll` → generic thunk → `BIN\iolib_32.dll` (shim) → `sicl32.dll`.
Configuration lives in `OTVDM\WINDOWS\Testexec.ini`, `Models.ini`, `Devices.ini`, `Dut.ini`,
`Ete.ini` (your equipment list), `HP8648\Adjust.ini` and `HP8648\Test.ini`.
Setting the environment variable `HSI_DEBUG_ETE=1` puts iolib_32 into the original "SICL I/O is
in debug mode" simulation in the *original* DLL. The shim does not implement it.
Full reverse-engineering notes: `docs/re/` (architecture, datapacks, service commands,
motherboard utility).
