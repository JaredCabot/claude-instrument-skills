#!/usr/bin/env python3
"""
hp8648_calbackup.py - backup, compare and (guarded) restore of an HP 8648A/B/C/D's
calibration arrays over GPIB (PyVISA).

SAFETY DESIGN
-------------
Two choke points; nothing reaches the instrument except through them.

`Bus.send()` (backup, compare, verification reads) is READ-ONLY. It refuses, before
touching the bus, anything that is not
  * one of the allow-listed queries: *IDN?  *OPT?  SYST:ERR?  SERV:BOARDID? <board>
  * SERV:PRODUCTION:CAL? <array>,<index> where <array> is listed in known_arrays.txt
    and 0 <= <index> < its element count, and <array> is not an option-hardware array.

`WriteBus.write()` (restore only) additionally allows exactly four write forms:
    SERV:PRODUCTION:CAL:BEGIN
    SERV:PRODUCTION:CAL <array>,<index>,<number>   array in RESTORE_GROUP, index in range
    SERV:PRODUCTION:CAL:END
    SERV:PRODUCTION:CAL:STORE <group>              group in RESTORE_GROUP's values
It can never emit PUP, MEM:*, MEM:SCRATCH, BOARDID or INSTRUMENT writes, DIAG:LATCH,
*RST or anything else. CONFIG_CAL / CONFIG2_CAL writes also need --include-config.

Reads are NOT automatically harmless. On an 8648C (fw B.04.08), 2026-10-05:
  * reading an option array whose hardware is not fitted (dsp_2fsk_cal,0 without 1EP)
    -> "Fatal firmware error";
  * reading one index past the end (outllvl_frq,6)
    -> "FATAL FIRMWARE ERROR: assertion failure 597: h:FileMgr.m".
Both needed a power cycle (calibration was verified unchanged). Hence the exact counts in
known_arrays.txt; never guess names or lengths.

RESTORE (writes calibration EEPROM; get the user's approval before using --apply)
------------------------------------------------------------------------------------
  1. Only to the SAME instrument: model, serial and firmware must match the backup.
  2. A fresh full backup is taken first and saved ("pre-restore").
  3. Only elements whose current value differs from the backup are written (with --all, or the
     menu's default, every element of every writable array is written). Frequency-list
     arrays (*_frq) have no firmware write routine and are never written; fm_acfm_dac has no
     STORE group and is never written; option DSP arrays are never written.
  4. Per STORE group, in the order the HP service software uses:
       CAL:BEGIN, CAL <array>,<i>,<v> ..., CAL:END,
       then every element of the group's arrays is read back and must equal the backup,
       and the error queue must be empty, and ONLY THEN CAL:STORE <group>.
     If a check fails the group is NOT stored and the restore stops. The written values are
     then only in the instrument's working copy [inferred from the firmware: CAL writes go to
     the RAM image, STORE copies it to the board EEPROM]; power-cycle to discard them, then
     run a backup and compare it with the pre-restore one.
  5. A final backup is taken and compared with the target.
Without --apply nothing is written: the plan is printed (dry run).

USAGE
    python hp8648_calbackup.py backup  --addr GPIB0::19::INSTR [--out DIR] [--arrays FILE]
    python hp8648_calbackup.py compare a.json b.json        (exit status 1 if they differ)
    python hp8648_calbackup.py restore backup.json [--addr ...] [--out DIR]   (dry run)
    python hp8648_calbackup.py restore backup.json --apply [--all] [--include-config]
Output: hp8648_<serial>_<timestamp>.json/.csv/.log in --out (default: cwd).
"""
import argparse
import datetime as dt
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
FIXED = {"*IDN?", "*OPT?", "SYST:ERR?"}
BOARD_Q = re.compile(r"^SERV:BOARDID\? [A-Z][A-Z0-9_]{0,20}\Z")
CAL_Q = re.compile(r"^SERV:PRODUCTION:CAL\? ([A-Za-z][A-Za-z0-9_]{0,11}),(\d{1,4})\Z")
KNOWN_BOARDS = ["MOTHER_BD", "OUTPUT_BD", "SYNTH_BD", "REF_BD", "ATTEN_BD", "FREQ_EXT_BD"]
# Option-hardware arrays (1EP pager encoder / 1E2 audio generator DSP). fm_sens_* are standard.
OPTION_ARRAY = re.compile(r"(^dsp_|fsk|pag|enc|sin_cal)", re.I)

# Writable array -> STORE group, from fw B.04.08: the per-array write routine (table 0x2695A)
# writes internal EEPROM file N, and :STORe <group> commits file N (group table 0x4AC66,
# file table 0x43F98). See docs/re/firmware-b0408-report.md.
_DB = ["0db", "10db", "20db", "30db", "40db", "50db", "60db", "70db", "80db", "90db",
       "100db", "110db", "120db", "130db"]
RESTORE_GROUP = {
    "out_tune_dac": "OUT_TUNE_CAL",
    "out_lvl_gain": "OUTLVL_DATA", "out_lvl_ofs": "OUTLVL_DATA",
    "out_pre_pwr": "OUT_PRE_PWR",
    "fextlvl_gain": "FEXTLVL_DATA", "fextlvl_ofs": "FEXTLVL_DATA",
    "fm_sens_sgn": "FM_SENS_KV", "fm_sens_mult": "FM_SENS_MULT",
    "timebase": "TIMEBASE",
    "out_temp_cal": "OUT_TEMP_CAL",
    "gen_loss_cal": "GEN_LOSS_CAL",
    "config_cal": "CONFIG_CAL", "config2_cal": "CONFIG2_CAL",
    "atn_comp_cal": "ATN_COMP_CAL",
    "outllvl_gain": "OUT_LF_DATA", "outllvl_ofs": "OUT_LF_DATA",
}
RESTORE_GROUP.update({"out_" + d: "OUT_LOSS" for d in _DB})
RESTORE_GROUP.update({"outl_" + d: "OUT_LF_LOSS" for d in _DB})
RESTORE_GROUP.update({"mod_%s_%s" % (m, s): "MOD_DAC"
                      for m in ("fm", "pm", "am") for s in ("1khz", "400hz", "extdc", "extac")})
RESTORE_GROUP.update({t: "TC_COEFF_CAL" for t in
                      ("tc_thru_path", "tc_10_40db", "tc_50_70db", "tc_80_100db", "tc_110_130db")})
CONFIG_GROUPS = {"CONFIG_CAL", "CONFIG2_CAL"}
NUMBER = re.compile(r"^[+-]?(\d+(\.\d*)?|\.\d+)([Ee][+-]?\d{1,3})?\Z")
CAL_W = re.compile(r"^SERV:PRODUCTION:CAL ([a-z][a-z0-9_]{0,11}),(\d{1,4}),(\S{1,24})\Z")
STORE_W = re.compile(r"^SERV:PRODUCTION:CAL:STORE ([A-Z][A-Z0-9_]{0,15})\Z")
TXN_W = {"SERV:PRODUCTION:CAL:BEGIN", "SERV:PRODUCTION:CAL:END"}


class InstrumentUnresponsive(RuntimeError):
    pass


class Bus:
    """`inst` is anything with query()/clear()/close() (a PyVISA resource in practice).
    `limits` maps lower-case array name -> number of elements that may be read."""

    def __init__(self, inst, log, limits, allow_option=False):
        self.inst, self.log, self.limits, self.allow_option = inst, log, limits, allow_option
        self.n = 0

    def _log(self, s):
        self.log.write("%s %s\n" % (dt.datetime.now().isoformat(sep=" ", timespec="milliseconds"), s))

    def check(self, q):
        """Raise PermissionError unless q is safe to send."""
        if q in FIXED or BOARD_Q.match(q):
            return
        m = CAL_Q.match(q)
        if not m:
            raise PermissionError("refusing non-allow-listed command: %r" % q)
        name, idx = m.group(1).lower(), int(m.group(2))
        if OPTION_ARRAY.search(name) and not self.allow_option:
            raise PermissionError("option-hardware array %r is blocked (see --allow-option-arrays)" % name)
        if idx >= self.limits.get(name, 0):
            raise PermissionError("%s[%d] is outside the known length (%s); reading past the end can "
                                  "halt the firmware" % (name, idx, self.limits.get(name, "unknown array")))

    def send(self, q):
        """Send a safe query. Returns the reply, or None if the instrument gave none."""
        self.check(q)
        self.n += 1
        try:
            r = self.inst.query(q).strip()
            self._log("Q %s -> %s" % (q, r))
            return r
        except Exception as e:  # timeout: instrument produced no reply
            self._log("Q %s -> (no reply: %s)" % (q, type(e).__name__))
            try:
                self.inst.clear()      # IEEE-488 device clear (SDC)
            except Exception as e2:
                self._log("device clear failed: %s -> instrument unresponsive" % e2)
                raise InstrumentUnresponsive("no response to device clear after %r" % q)
            return None

    def errors(self):
        out = []
        for _ in range(20):
            e = self.send("SYST:ERR?")
            if e is None or e.startswith("+0") or e.startswith("0,"):
                break
            out.append(e)
        return out


class WriteBus(Bus):
    """Bus plus the four calibration write forms used by restore. Nothing else is writable."""

    def __init__(self, inst, log, limits, include_config=False):
        Bus.__init__(self, inst, log, limits, allow_option=False)
        self.include_config = include_config

    def check_write(self, cmd):
        if cmd in TXN_W:
            return
        m = STORE_W.match(cmd)
        if m:
            g = m.group(1)
            if g not in set(RESTORE_GROUP.values()):
                raise PermissionError("STORE group %r is not restorable" % g)
            if g in CONFIG_GROUPS and not self.include_config:
                raise PermissionError("STORE %s needs --include-config" % g)
            return
        m = CAL_W.match(cmd)
        if not m:
            raise PermissionError("refusing non-allow-listed write: %r" % cmd)
        name, idx, val = m.group(1), int(m.group(2)), m.group(3)
        g = RESTORE_GROUP.get(name)
        if g is None:
            raise PermissionError("array %r is not restorable" % name)
        if g in CONFIG_GROUPS and not self.include_config:
            raise PermissionError("writing %s needs --include-config" % name)
        if idx >= self.limits.get(name, 0):
            raise PermissionError("%s[%d] is outside the known length" % (name, idx))
        if not NUMBER.match(val):
            raise PermissionError("value %r for %s[%d] is not a plain number" % (val, name, idx))

    def write(self, cmd):
        self.check_write(cmd)
        self.n += 1
        self._log("W %s" % cmd)
        self.inst.write(cmd)


def ident(bus):
    idn = bus.send("*IDN?")
    opt = bus.send("*OPT?")
    boards = {b: bus.send("SERV:BOARDID? %s" % b) for b in KNOWN_BOARDS}
    bus.errors()
    parts = [p.strip() for p in (idn or "").split(",")]
    return {"idn": idn, "opt": opt, "boards": boards,
            "model": parts[1] if len(parts) > 1 else "", "serial": parts[2] if len(parts) > 2 else "",
            "firmware": parts[3] if len(parts) > 3 else ""}


def dump_array(bus, name, count):
    """Read elements 0..count-1. Returns None if the array does not exist on this instrument."""
    vals = []
    for i in range(count):
        r = bus.send("SERV:PRODUCTION:CAL? %s,%d" % (name, i))
        if r is None:
            errs = bus.errors()
            if i == 0 and errs and all(("-224" in e or "-420" in e) for e in errs):
                return None
            raise InstrumentUnresponsive("unexpected failure reading %s[%d]: %s" % (name, i, errs))
        vals.append(r)
    return vals


def load_known(path):
    """known_arrays.txt rows: name count_BCD count_A  [# comment]"""
    rows = []
    with open(path) as f:
        for line in f:
            w = line.split("#")[0].split()
            if len(w) >= 3:
                rows.append((w[0].lower(), int(w[1]), int(w[2])))
    return rows


def limits_for(table, model):
    col = 2 if (model or "").upper() == "8648A" else 1
    return {row[0]: row[col] for row in table}


def read_all(bus, out=print):
    """Read every known array. Returns (data, missing, aborted)."""
    data, missing, aborted = {}, [], None
    try:
        for name, cnt in bus.limits.items():
            if cnt <= 0:
                continue
            vals = dump_array(bus, name, cnt)
            if vals is None:
                missing.append(name)
                out("  %-28s (not present)" % name)
            else:
                data[name] = vals
                out("  %-28s %4d elements" % (name, len(vals)))
    except InstrumentUnresponsive as e:
        aborted = str(e)
        out("\n*** ABORTED: %s\n*** Check the instrument front panel; a power cycle may be needed." % e)
    return data, missing, aborted


def save_doc(doc, out_dir, serial, stamp, tag=""):
    base = os.path.join(out_dir, "hp8648_%s_%s%s" % (serial or "unknown", stamp, tag))
    with open(base + ".json", "w") as f:
        json.dump(doc, f, indent=1)
    with open(base + ".csv", "w") as f:
        f.write("array,index,value\n")
        for n, vals in doc["arrays"].items():
            for i, v in enumerate(vals):
                f.write("%s,%d,%s\n" % (n, i, v))
    return base


def backup_doc(bus, table, out=print, note="Read-only backup."):
    """Identity, all arrays, identity again. Sets bus.limits from the model."""
    bus.limits = {}
    info = ident(bus)
    out("Instrument: %s" % info["idn"])
    if "8648" not in (info["idn"] or ""):
        raise SystemExit("not an 8648: %r" % info["idn"])
    bus.limits = limits_for(table, info["model"])
    data, missing, aborted = read_all(bus, out)
    info2 = None if aborted else ident(bus)
    return {"tool": "hp8648_calbackup.py", "created": dt.datetime.now().isoformat(timespec="seconds"),
            "instrument": info, "instrument_after": info2, "arrays": data, "not_present": missing,
            "aborted": aborted,
            "note": "Values are the raw SCPI replies of SERV:PRODUCTION:CAL? <array>,<index>. " + note}


def open_inst(a):
    import pyvisa
    return pyvisa.ResourceManager().open_resource(a.addr, timeout=a.timeout,
                                                  read_termination="\n", write_termination="\n")


def give_back(inst):
    try:
        inst.control_ren(6)   # GTL: give the front panel back
    except Exception:
        pass


def cmd_backup(a):
    table = load_known(a.arrays or os.path.join(HERE, "known_arrays.txt"))
    stamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path = os.path.join(a.out, "hp8648_backup_%s.log" % stamp)
    inst = open_inst(a)
    with open(log_path, "a", encoding="utf-8", buffering=1) as log:   # line-buffered: survives crashes
        bus = Bus(inst, log, {}, a.allow_option_arrays)
        try:
            doc = backup_doc(bus, table)
        finally:
            give_back(inst)
            inst.close()
    base = save_doc(doc, a.out, doc["instrument"].get("serial"), stamp)
    os.replace(log_path, base + ".log")
    print("Saved %s.json/.csv/.log  (%d transactions; identity unchanged: %s)"
          % (base, bus.n, doc["instrument"] == doc["instrument_after"]))
    return 1 if doc["aborted"] else 0


def compare(A, B, out=print):
    """Print differences between two backup documents; return the number of differences."""
    diffs = 0
    ia, ib = A["instrument"], B["instrument"]
    for k in ("model", "serial", "firmware", "opt"):
        if ia.get(k) != ib.get(k):
            diffs += 1
            out("instrument %-8s %s -> %s" % (k, ia.get(k), ib.get(k)))
    ba, bb = ia.get("boards") or {}, ib.get("boards") or {}
    for k in sorted(set(ba) & set(bb)):        # older backups read fewer boards
        if ba[k] != bb[k]:
            diffs += 1
            out("board %-12s %s -> %s" % (k, ba[k], bb[k]))
    for doc, tag in ((A, "A"), (B, "B")):
        if doc.get("aborted"):
            diffs += 1
            out("WARNING: backup %s was aborted (%s); it is incomplete" % (tag, doc["aborted"]))
    for n in sorted(set(A["arrays"]) | set(B["arrays"])):
        x, y = A["arrays"].get(n), B["arrays"].get(n)
        if x == y:
            continue
        diffs += 1
        if x is None or y is None:
            out("%-24s only in %s" % (n, "A" if y is None else "B"))
            continue
        for i in range(max(len(x), len(y))):
            u, v = (x[i] if i < len(x) else None), (y[i] if i < len(y) else None)
            if u != v:
                out("%-24s [%3d] %s -> %s" % (n, i, u, v))
    out("identical" if not diffs else "%d differences" % diffs)
    return diffs


def cmd_compare(a):
    with open(a.a) as fa, open(a.b) as fb:
        return 1 if compare(json.load(fa), json.load(fb)) else 0


# ------------------------------------------------------------------ restore

def same_value(u, v):
    """Two SCPI number replies are equal if they parse to the same float."""
    try:
        return float(u) == float(v)
    except (TypeError, ValueError):
        return u == v


def plan_restore(target, current, include_config=False, full=False):
    """Work out what a restore would write. With full=True every element of every writable
    array is written, not only the ones that differ.

    Returns (plan, skipped, problems):
      plan     {group: [(array, index, value), ...]}  elements that differ and can be written
      skipped  [text]  differences that restore will not touch (read-only or excluded arrays)
      problems [text]  reasons the restore must not run at all"""
    problems, skipped, plan = [], [], {}
    ti, ci = target.get("instrument") or {}, current.get("instrument") or {}
    for k in ("model", "serial", "firmware"):
        if not ti.get(k) or ti.get(k) != ci.get(k):
            problems.append("%s differs: backup %r, instrument %r" % (k, ti.get(k), ci.get(k)))
    for doc, tag in ((target, "backup"), (current, "pre-restore read")):
        if doc.get("aborted"):
            problems.append("%s is incomplete (%s)" % (tag, doc["aborted"]))
    tb, cb_ = ti.get("boards") or {}, ci.get("boards") or {}
    for b in sorted(set(tb) & set(cb_)):
        if tb[b] != cb_[b]:
            problems.append("board %s ID differs (%s -> %s): a board was changed; "
                            "its calibration must be redone, not restored" % (b, tb[b], cb_[b]))
    for name in sorted(set(target["arrays"]) | set(current["arrays"])):
        t, c = target["arrays"].get(name), current["arrays"].get(name)
        if t is None or c is None:
            problems.append("array %s is only in the %s" % (name, "instrument" if t is None else "backup"))
            continue
        if len(t) != len(c):
            problems.append("array %s has %d elements in the backup, %d now" % (name, len(t), len(c)))
            continue
        diff = [(i, t[i]) for i in range(len(t)) if not same_value(t[i], c[i])]
        g = RESTORE_GROUP.get(name)
        if full and g is not None:
            diff = list(enumerate(t))
        if not diff:
            continue
        if g is None:
            skipped.append("%s: %d element(s) differ but this array is not writable (left as is)"
                           % (name, len(diff)))
            continue
        if g in CONFIG_GROUPS and not include_config:
            if not full or any(not same_value(t[i], c[i]) for i in range(len(t))):
                skipped.append("%s: %d element(s) differ; CONFIG data is only written with "
                               "--include-config" % (name, len(diff)))
            continue
        for i, v in diff:
            if not NUMBER.match(v):
                problems.append("%s[%d] backup value %r is not a plain number" % (name, i, v))
        plan.setdefault(g, []).extend((name, i, v) for i, v in diff)
    return plan, skipped, problems


def print_plan(plan, skipped, problems, out=print, current=None):
    for p in problems:
        out("PROBLEM: " + p)
    for s in skipped:
        out("not restored: " + s)
    if not plan:
        out("Nothing to write: every restorable element already matches the backup.")
    for g in sorted(plan):
        out("STORE group %s: %d element(s)" % (g, len(plan[g])))
        for name, i, v in plan[g]:
            same = current is not None and same_value(current["arrays"][name][i], v)
            out("    %-14s [%3d] -> %s%s" % (name, i, v, "  (unchanged)" if same else ""))


def apply_group(wbus, target, group, items, out=print):
    """Write one group, verify it, and store it only if verification passes. Returns True if stored."""
    wbus.write("SERV:PRODUCTION:CAL:BEGIN")
    for name, i, v in items:
        wbus.write("SERV:PRODUCTION:CAL %s,%d,%s" % (name, i, v))
    wbus.write("SERV:PRODUCTION:CAL:END")
    errs = wbus.errors()
    if errs:
        out("  %s: instrument reported %s; NOT stored" % (group, errs))
        return False
    for name in sorted({n for n, g in RESTORE_GROUP.items() if g == group} & set(target["arrays"])):
        now = dump_array(wbus, name, len(target["arrays"][name]))
        bad = [i for i, (u, w) in enumerate(zip(target["arrays"][name], now or [])) if not same_value(u, w)]
        if now is None or bad:
            out("  %s: read-back of %s does not match the backup at %s; NOT stored"
                % (group, name, bad[:10] if now else "(no reply)"))
            return False
    wbus.write("SERV:PRODUCTION:CAL:STORE %s" % group)
    errs = wbus.errors()
    if errs:
        out("  %s: STORE reported %s" % (group, errs))
        return False
    out("  %s: %d element(s) written, verified and stored" % (group, len(items)))
    return True


def confirm(prompt_serial, ask=None):
    s = (ask or input)("Type the instrument serial number (%s) to write its calibration: " % prompt_serial)
    return s.strip() == prompt_serial


def run_restore(inst, target, table, out_dir, apply=False, include_config=False,
                out=print, ask=None, log=None, full=False):
    """The whole restore procedure on an open instrument. Returns a process exit status."""
    stamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    log = log or open(os.path.join(out_dir, "hp8648_restore_%s.log" % stamp), "a", encoding="utf-8",
                      buffering=1)
    wbus = WriteBus(inst, log, {}, include_config)
    out("Reading the instrument's current calibration (pre-restore backup)...")
    current = backup_doc(wbus, table, out, note="Taken by restore before writing.")
    base = save_doc(current, out_dir, current["instrument"].get("serial"), stamp, "_prerestore")
    out("Saved %s.json" % base)
    plan, skipped, problems = plan_restore(target, current, include_config, full)
    print_plan(plan, skipped, problems, out, current)
    if full and plan:
        out("Full restore: %d element(s) in %d group(s), %d of them different from now."
            % (sum(len(v) for v in plan.values()), len(plan),
               sum(1 for v in plan.values() for n, i, x in v
                   if not same_value(current["arrays"][n][i], x))))
    if problems:
        out("Restore refused.")
        return 2
    if not plan:
        return 0
    if not apply:
        out("Dry run: nothing was written. (Command line: add --apply to write the groups above.)")
        return 0
    if not confirm(current["instrument"]["serial"], ask):
        out("Serial number not confirmed; nothing was written.")
        return 2
    wbus.limits = limits_for(table, current["instrument"]["model"])
    for g in sorted(plan):
        try:
            ok = apply_group(wbus, target, g, plan[g], out)
        except InstrumentUnresponsive as e:
            ok = False
            out("  %s: instrument stopped responding (%s)" % (g, e))
        if not ok:
            out("\n*** Restore stopped at group %s. Groups before it were stored. Group %s was NOT\n"
                "*** stored; its new values are only in the working copy. Power-cycle the instrument\n"
                "*** to discard them, then run a backup and compare it with %s.json." % (g, g, base))
            return 1
    out("Final check...")
    final = backup_doc(wbus, table, out, note="Taken by restore after writing.")
    fbase = save_doc(final, out_dir, final["instrument"].get("serial"), stamp, "_postrestore")
    rest, _, _ = plan_restore(target, final, include_config)
    if rest:
        out("WARNING: some elements still differ after the restore:")
        print_plan(rest, [], [], out)
        return 1
    out("Restore complete; saved %s.json. Every restorable element now matches the backup." % fbase)
    return 0


def cmd_restore(a):
    with open(a.backup) as f:
        target = json.load(f)
    table = load_known(a.arrays or os.path.join(HERE, "known_arrays.txt"))
    inst = open_inst(a)
    try:
        return run_restore(inst, target, table, a.out, a.apply, a.include_config, full=a.all)
    finally:
        give_back(inst)
        inst.close()


def main(argv=None):
    sys.stdout.reconfigure(line_buffering=True)
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("backup")
    p.add_argument("--addr", default="GPIB0::19::INSTR")
    p.add_argument("--out", default=".")
    p.add_argument("--timeout", type=int, default=1200, help="ms per query")
    p.add_argument("--arrays", help="array table (default: known_arrays.txt next to this script)")
    p.add_argument("--allow-option-arrays", action="store_true",
                   help="also read 1EP/1E2 DSP arrays (ONLY if those options are fitted)")
    p = sub.add_parser("compare")
    p.add_argument("a")
    p.add_argument("b")
    p = sub.add_parser("restore", help="write a backup back to the SAME instrument (dry run by default)")
    p.add_argument("backup", help="backup .json made by this tool from this instrument")
    p.add_argument("--addr", default="GPIB0::19::INSTR")
    p.add_argument("--out", default=".")
    p.add_argument("--timeout", type=int, default=1200, help="ms per query")
    p.add_argument("--arrays", help="array table (default: known_arrays.txt next to this script)")
    p.add_argument("--apply", action="store_true", help="actually write (asks for the serial number)")
    p.add_argument("--all", action="store_true",
                   help="write every element of every writable array, not only the ones that differ")
    p.add_argument("--include-config", action="store_true",
                   help="also restore CONFIG_CAL / CONFIG2_CAL (model, frequency range, option bits)")
    a = ap.parse_args(argv)
    return {"backup": cmd_backup, "compare": cmd_compare, "restore": cmd_restore}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
