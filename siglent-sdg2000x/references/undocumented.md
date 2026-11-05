# Commands and behaviour Siglent doesn't document

Recovered from the firmware image `SDG2000X_P39R7.ADS` (application binary `awg.app`) and
confirmed against an SDG2122X running 2.01.01.39R7. Everything here is *in addition to*
PG02-E05C; `scpi-reference.md` covers the documented set.

Provenance is marked throughout: **bench** = observed on the instrument, **firmware** =
found in the binary only, **both** = found in firmware and confirmed on the instrument.
The full write-up, including the firmware container format, is in
`SDG2000X_Supplemental_Programming_Manual.pdf`.

## Contents

- [The status model and error queue](#the-status-model-and-error-queue)
- [Identification](#identification)
- [System and display](#system-and-display)
- [Diagnostics](#diagnostics)
- [Storage and waveforms](#storage-and-waveforms)
- [Aliases](#aliases)
- [The MMEMory subsystem](#the-mmemory-subsystem)
- [Undocumented parameters on documented commands](#undocumented-parameters-on-documented-commands)
- [Commands not to send](#commands-not-to-send)
- [Firmware package format](#firmware-package-format)
- [`awg.app` has a full symbol table](#awgapp-has-a-full-symbol-table)

## The status model and error queue

The single most useful omission from the guide. All **bench**-confirmed:

```
SYST:ERR?     ->  0,"No error"          FIFO, standard SCPI, survives across sessions
*ESR?         ->  32 after an error     self-clears on read
*CLS          ->  clears queue and registers
*STB?  *TST?  *SRE?  *ESE?              all answer
```

Use it as a capability test — far better than waiting for a query to time out:

```python
while "No error" not in dev.query("SYST:ERR?"):
    pass                                  # drain: the queue outlives sessions
dev.write(candidate + " ZZQQ")            # bogus arg so a real command can't execute
exists = "-113" not in dev.query("SYST:ERR?")
```

Send the **write form with a bogus argument** and stop on the first timeout. A header with no
query form (`Clear_fcnt?`, `DEL_STORE_FILE?`, `ReadFLASH?`, `PAraCoPy?`) times out *harmlessly*
— writes and the error queue keep working — but the timeout desynchronises the session, so a
loop that carries on through one reports every later header as present. Two sessions here did
exactly that and had to be thrown away.

Channel-prefixed probing *does* work — `C1:NOTAREALHEADER`, `C1:PRODuct` and `C1:BAND` all
answer `-113` while `C1:BSWV` answers cleanly and `C9:BSWV` gives `-113`. One session
suggested otherwise; that session was faulty.

**Never probe `C1:WVDT:BLOCK`.** With a non-block argument it leaves the parser waiting for
block data and consuming every subsequent command: writes keep succeeding, every read times
out, and nothing short of a physical USB re-plug recovers it — not `dev.clear()`, not
reopening the session. It is the single cause of every interface lockup found here, and it was
misattributed twice (to `viClear`, then to read timeouts) before a controlled test isolated
it.

The cause is a two-line bug in `scpi_ch1_build_in_wavedata_block` (`0x004d0744`): it calls
`SCPI_ParamArbitraryBlock(ctx, &ptr, &len, FALSE)`, **discards the return value**, and then
runs `std::string::assign(ptr, len)` where `ptr` is NULL and `len` was never initialised. The
copy walks into unmapped memory and kills the task that answers reads. Writes still land
because they are accepted lower down in the USBTMC stack. `0x004d07e0` is the same code for
CH2. Sent *correctly* the command is harmless and works: see the storage table below.

Codes seen in practice: `-113` undefined header (also for bad channel prefixes `C3:`/`C0:`),
`-108` parameter not allowed, `-101` invalid character, `-200` execution error, `0` no error.
Those five are all that ever appear. The firmware carries the complete SCPI-99 message table —
58 messages, listed in the supplement PDF — but nothing in the parameter path reaches it: a
missing parameter, `FRQ,abc`, `FRQ,1000QQ`, `FRQ,1E999`, `FRQ,-5000`, `LOAD,"abc"` and
`INVT ON,ON,ON,ON` all answer `0,"No error"`.

## Identification

| Command | Response | Notes |
|---|---|---|
| `PRODuct?` | `PROD MODEL,SDG2000X,BAND,120MHZ` | **both.** `BAND` is **not** the installed bandwidth despite the name — it is the *current waveform's* maximum frequency, and follows whichever channel was set last. On a 120 MHz unit: SINE/NOISE/DC → 120MHZ, SQUARE/PULSE → 25MHZ, RAMP → 1MHZ, ARB → 20MHZ. Nothing else queries this, but don't use it to identify the model. |
| `MD5_PR?` | `SDG2000X` | **both.** Product string alone. No hash despite the name. |
| `MD5_SRLN?` | `<serial>` | **both.** Serial number alone. |
| `MCBD?` | a 16-char code | **both.** `scpi_get_bandwidth_update_string_cb` — the bandwidth authorisation string, registered among `LICENSE`, `LICENSE_KEY` and `LCISL?`. Constant, unrelated to the serial. Don't send the set form. |
| `SRTIme?` | `1787837427` | **both.** A POSIX timestamp; the observed value matched the observation date. |

`MODEL?` and `BAND?` exist as response prefixes inside `PRODuct` but are **not** registered as
top-level headers.

## System and display

| Command | Response | Notes |
|---|---|---|
| `SCPI_UPDATE_UI ON\|OFF` / `?` | `ON` | **both.** The `Utility > System > SCPI UPUI` setting, which the user manual presents as front-panel-only. Decides whether SCPI writes redraw the screen. It does **not** affect command timing: a `BSWV` write cost 45.1 ms with it ON and 45.2 ms OFF. |
| `Screen_capture_png ON\|OFF` / `?` | `Screen_capture_png ON` | **both.** PNG vs BMP for screen captures. |
| `SCREEN_SHOT_TYPE <type>` / `?` | `PNG` | **both.** Same setting as a bare enum. `PNG` and `BMP` work; `JPG`, `0`, `1`, `2` are accepted in silence and change nothing. |
| `SCREEN_SHOT` | — | **both.** Captures the screen to internal storage as `Local/screen.png` or `screen.bmp` per `SCREEN_SHOT_TYPE`. **No USB drive needed.** Fixed name, so each capture overwrites the last (7,156 B as PNG, 391,734 B as BMP). |
| `SCDP` | a 391,734-byte BMP | **both.** Returns the screen **over the interface**, no file involved: 480x272, 24-bit, uncompressed. Registered as a query under a name with no `?`, so *write* `SCDP` then read. `SCDP?` answers `-113`. Use a big chunk size. |
| `VNC_PORT <port>` / `?` | `5900` | **both.** The VNC server port (5900–5999). |
| `Freq_com_switch ON\|OFF` / `?` | `Freq_com_switch ON` | **both.** The frequency-compensation option of the phase-mode menu — effectively the third member of `MODE`, which the guide documents without it. |

## Diagnostics

| Command | Response | Notes |
|---|---|---|
| `BOARD_TEST?` | `DAC,pass,FPGA,pass` | **both.** Runs the board self-test and returns a verdict per subsystem — the *only* part of `Utility > Test/Cal > SelfTest` reachable remotely. Safe to run; exercises hardware, so not mid-measurement. |
| `led?` | `MOD,OFF,SWEEP,OFF,BURST,OFF,...` | **both.** Lit state of each front-panel lamp: MOD, SWEEP, BURST, PARAMETER, UTILITY, STORE_RECACLL (the firmware's own misspelling), WAVEFORM, OUTPUT_CH1, OUTPUT_CH2. A cheap read-back of which mode the instrument thinks it is in. |
| `IQSP` / `IQSP?` | 17 NUL bytes | **both.** `scpi_get_iq_support_string_cb` — the I/Q support string. Empty here; no I/Q hardware, and nothing else in the firmware reads it. |
| `LCISL?` | `-200` | **both.** Recognised, not executable here. |
| `k7dump ON\|OFF` / `k7dump?` | empty | **both.** The Kintex-7 FPGA register dump switch (`drv_if_main_t::set_k7fpga_dump_switch`); `k7dump?` returns the buffer. Both forms accepted cleanly, but the buffer stays empty with the switch on — the facility is gated by the `SIGL_DEBUG=ON` build flag. A bad parameter goes to a debug stream, not the error queue. |

## Storage and waveforms

| Command | Notes |
|---|---|
| `DEL_STORE_FILE <name>.bin` | **both.** **Deletes a stored user waveform.** A user waveform is a pair, `<name>.bin` plus `<name>.info`, and this removes only the `.bin`, orphaning the `.info` invisibly (`STL? USER` lists neither member by name). **Prefer `MMEMory:DELete`**, which works on this model and deletes exactly what you name. **The `.bin` extension is required**: `DEL_STORE_FILE mywave` is accepted with a clean error queue and deletes nothing; `DEL_STORE_FILE mywave.bin` works. Exactly the opposite of `ARWV NAME`, which rejects `.bin` with `-101`. |
| `Clear_fcnt` | **both.** Clears the frequency counter's statistics — the counter menu's Clear softkey. Added in firmware 2.01.01.37R8 and never documented. |
| `C1:WVDT:BLOCK` / `C2:WVDT:BLOCK` | **both.** The block-transfer form of `WVDT`. The payload is the ordinary parameter list (`WVNM` ... `WAVEDATA`) wrapped as an IEEE 488.2 definite-length block; the handler unwraps it and calls the same routine as `C1:WVDT`, so the forms are equivalent and there is no reason to prefer it. **Get the block header wrong and you lose the interface** (see above). |
| `WaVePaRameter?` / `WaVeDaTa?` | **both.** Long spellings of `WVPR?` and `WVDT?`, sharing their handlers. **Queries, not writes.** `WaVeDaTa? USER,<name>` returns the same 65,606-byte response as `WVDT?`, with the same spurious `-108`. No channel prefix: `C1:WaVePaRameter?` gives `-113`. |
| `C<n>:DcUFAmplifier ON\|OFF` / `?` | `C1:DcUFAmplifier,OFF` | **both.** The DC final amplifier switch (`cfg_bswv_main_t::set_dc_final_amplifier_switch`). Registered with a `C#:` wildcard. Default OFF. |

The firmware implements `DEL_STORE_FILE` by interpolating your name into
`rm -rf /usr/bin/siglent/usr/usr/<name>`, i.e. the parameter reaches a shell. Pass plain
alphanumeric/underscore names — which is all the instrument's file manager supports anyway —
and reject anything else if you build the name from user input or a directory listing.

## Aliases

Convenience rather than capability, all **both**-confirmed. The un-prefixed forms act on CH1.

| Alias | Equivalent to |
|---|---|
| `BaSicWaVe` / `BaSicWaVe?` | `BaSic_WaVe`, and usable with no channel prefix |
| `INVERT` / `INVERT?` | `INVerT` (response still says `C1:INVT`) |
| `ROSCILLATOR?` | `ROSCillator?` |
| `NumBerForMat?` | `NumBer_ForMat?` |
| `SCREEN_SAVE` / `?` | `SCreen_SaVe` |
| `SystemConFiG` / `?` | `Sys_CFG` |
| `PAraCoPy` | `ParaCoPy` (the guide's spelling differs from the firmware's) |

## The MMEMory subsystem

The Programming Manual marks all of `MMEMory` as SDG7000A-only. **On the SDG2000X it is fully
functional**, with the syntax given in 3.46 working unchanged, quoted paths included. Every
command below was exercised on a dummy file and verified by listing the directory before and
after.

| Command | Form | Result |
|---|---|---|
| `MMEMory:CATalog? "Local"` | query | free, used, then one quoted `name,type,size` per entry |
| `MMEMory:CATalog:DATA:ARBitrary? "Local"` | query | answers |
| `MMEMory:CATalog:STATe:XMLanguage? "Local"` | query | answers |
| `MMEMory:COPY "src","dst"` | write | copies; returns a spurious `-108` |
| `MMEMory:MOVE "src","dst"` | write | moves; returns a spurious `-108` |
| `MMEMory:DELete "path"` | write | deletes, clean |
| `MMEMory:MDIRectory "Local/dir"` | write | creates the directory, clean |
| `MMEMory:RDIRectory "Local/dir"` | write | removes it, clean |
| `MMEMory:SAVE:XML` | write | accepted; not exercised |
| `MMEMory:LOAD:XML` | write | accepted; not exercised |
| `MMEMory:TRANsfer` | write | accepted; not exercised |
| `MMEMory:CFIle` | write | accepted; not exercised |

Two details matter. **`MMEMory:CATalog?` returns nothing at all without its path parameter**,
leaving `-200,"Execution error"` in the queue — which is exactly what makes the subsystem look
unimplemented if you probe it bare. With the parameter it answers on one line: free space, used
space, then a quoted triple per entry.

```
86528000,258048,"CAN_D_DATA.bin,BIN,65536","RS232_CLK.info,INFO,152","mydir",...
```

A **file** is `"name,type,size"`; a **subdirectory** is a bare quoted name with no type and no
size, which is easy to drop if you parse on a fixed field count. A path that **does not exist**
answers `0,0` with an empty error queue, and `MDIRectory` / `RDIRectory` on a nonexistent path
report nothing either, so an empty listing is the only signal that a path was wrong.

And **`COPY` and `MOVE` do the work while reporting `-108,"Parameter not allowed"`.** The
operation succeeds; the error is spurious. Do not treat a non-empty queue as failure here.

This subsystem is the better way to manage instrument storage: it is the only route to a
directory listing with sizes and free space, the only way to create or remove directories, and
`MMEMory:DELete` deletes exactly the file named, which `DEL_STORE_FILE` does not.

**There is no undo.** `MMEMory:DELete` removes whatever path it is given. Back a library up with
`WVDT? USER,<name>` first.

**A `"` in a filename breaks every path operation.** All the handlers above strip every double
quote from their path argument (via `sdg_scpi_cmd_t::sdg_eraser_string_character(path, "\"")` at
`0x4cb5c0`) before touching the filesystem, and the tokeniser also drops `"` from unquoted
parameters, so **no SCPI escape can name a file whose name contains a `"`**. Such files (created
off-instrument, e.g. from a USB drive — `"` is legal on the instrument's Linux filesystem) list
and play fine but cannot be deleted, moved or renamed remotely. Worse, the strip makes
`MMEMory:DELete "Local/""x"".bin"` collapse to `Local/x.bin` and delete the *un-quoted*
namesake — a wrong-file hazard. Delete such files from the front panel instead. This is a
firmware bug; there is no driver-side fix.

## Undocumented parameters on documented commands

| Command | Parameter | Values | Source |
|---|---|---|---|
| `FreqCouNTer` | `TYPE` | `SLOW` / `FAST` | **both** — in every `FCNT?` response |
| `FreqCouNTer` | `DEF` | (action) | **both** — restores counter defaults; the query afterwards returns only `FCNT STATE,OFF` |
| `OUTPut` | `POWERON_STATE` | `ON` / `OFF` | **bench** — in every `OUTP?` response |
| `BaSic_WaVe` | `MAX_OUTPUT_AMP` | 1–20 Vpp | **bench** — in every `BSWV?` response; applies to both channels |
| `SweepWaVe` | `IDLE_FREQ` | `START_FREQ` / `STOP_FREQ` / `ZERO_FREQ` | **both** |
| `SweepWaVe` | `STEPNUM` | integer | **both** |
| `CASCADE` | `SYNC_PHASE` | **not implemented** | **both** — accepted, never in `CASCADE?` (which does carry `DELAY`) |
| `COUPling` | `DELAY` | **not implemented** | **both** — accepted, never in `COUP?` |
| `SampleRATE` | `INTER` | `LINE`/`HOLD`/`SINC`/`SINC27`/`SINC13` | firmware — silently ignored on this model |

Also worth knowing: `SWWV?`'s `SYM` field returns uninitialised garbage unless `DIR,UP_DOWN` is
set, and built-in arb indices **0 and 1 do work** (`Sine`, `Noise`) despite the guide's stated
range of 2–198. Index 67, which the guide calls `NA`, is **`Radar`** — confirmed by `STL? BUILDIN` on the
instrument, and shipped in the firmware as `70_radar_ram.bin`.

## Commands not to send

Present in the firmware, deliberately never exercised. Each writes flash, alters calibration,
or reconfigures hardware, and none has a documented parameter syntax:

```
ClearFLASH      DAC_SAVE      RESETADC      DRV_RECONFIG_PHASE
```

Named from the symbol table: `DAC_SAVE` is `scpi_save_time_base_cali_cb`, `RESETADC` is
`scpi_reset_ad9122`, `DRV_RECONFIG_PHASE` is `scpi_drp_dynamic_reconfig_phase_test_cb`. Note
that **`DACC`/`DAC_CODE` are `scpi_set/get_time_base_cali_cb`** — the time-base trim, not a DAC
output code, whatever the mnemonic suggests. The query forms are safe and returned `48153`.

(`MMEMory:DELete`, `MOVE` and `COPY` were on this list in an earlier draft. They have since been
exercised on a dummy file and are documented above; they touch stored files only, never flash or
calibration.)

`DACC?` and `DAC_CODE?` *are* safe to read — both answer, returning `48153` on the unit
tested. Only their set forms were left alone.

`ReadFLASH` and `ReadFLASHBLocK` are recognised and are read operations by name, but were not
exercised either. Calibration lives in the filesystem at `/usr/bin/siglent/usr/cali/`,
`cali.bin`, `cali.tar.gz` and `firmdata0/cali_date`; the service manual is clear that there is
no user calibration path and a failing unit goes back for service. Corrupting that storage
destroys the factory calibration and there is no second copy.

## Firmware package format

The SDG2000X firmware ships as a Siglent `.ADS` update container. That format —
its 112-byte header, the obfuscation transform, the non-standard two-key 3DES
layer, the ZIP container, and a reference decoder — is documented and decoded in
a separate project:

  Siglent .ADS firmware format (the separate siglent-ads-format project)

Two points matter from the SCPI side: you can inspect or extract a firmware
release before installing it, and the 216 built-in waveform tables come out of it
as plain 32,768-byte `.bin` files in exactly the layout `WVDT` expects (see
Storage and waveforms, above).

## `awg.app` has a full symbol table

The application binary is stripped of its `.symtab`, which makes it look opaque, but it ships a
`.dynsym` with **40,601 defined symbols** carrying addresses and C++ mangled names. So you never
have to guess what a command does:

```bash
readelf --dyn-syms -W awg.app | awk '$7!="UND"'
```

Command registration goes through two functions, `0x2cc0c8` and `0x2cc1f4`, both called as
`reg(name_ptr, handler_ptr, 1)` with the pointers built by `movw`/`movt` pairs. Walk the `.text`
section with capstone, track those pairs, and every `bl` to either address yields a
`(command string, handler address)` pair; look the handler up in `.dynsym` and it has a name.
Function boundaries come free from `.ARM.exidx`.

That method is what turned `MCBD` into `scpi_set_bandwidth_update_string_cb`, `k7dump` into
`drv_if_main_t::set_k7fpga_dump_switch`, and `DACC` into `scpi_set_time_base_cali_cb` rather
than the DAC write its mnemonic implies. **Presence in this table does not mean the command is
registered on the SDG2000X** — the binary is shared across SDG families and carries the whole
IQ and SDG7000A command set. Always confirm on the instrument with the `-113` oracle.
