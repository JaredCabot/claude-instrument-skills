# claude-instrument-skills

Claude agent skills for operating, programming and servicing bench test
equipment. Each folder is a self-contained skill: an operating and
remote-control reference for one instrument family, written for a Claude agent
to load and act on.

They are distilled from the instruments' own manuals and from hands-on
reverse-engineering and bench verification on the author's equipment. Where a
fact is inferred, measured, or taken from a firmware supplement rather than a
manual, the text says so.

## Instruments

| Skill | Instrument |
|---|---|
| `agilent-epm-power-meter` | Agilent E4418B / E4419B EPM power meters and their sensors |
| `hp-3458a` | HP / Agilent / Keysight 3458A 8.5-digit multimeter |
| `hp-53132a` | HP / Agilent 53132A / 53131A / 53181A universal counters |
| `hp8648-gpib` | HP / Agilent 8648A/B/C/D signal generators |
| `keysight-truevolt-dmm` | Keysight 34460A / 34461A / 34465A / 34470A DMMs |
| `siglent-sdg2000x` | Siglent SDG2000X arbitrary waveform generators |
| `siglent-sds2000x-hd` | Siglent SDS2000X HD oscilloscopes |
| `siglent-spd3303x` | Siglent SPD3303X bench power supplies |
| `siglent-sva1032x` | Siglent SVA1032X spectrum analyzer / VNA |
| `tektronix-sg5030` | Tektronix SG 5030 leveled sine wave generator (TM 5000 plug-in) |
| `tektronix-tds-gpib` | Tektronix TDS 400/500/600/700/800 oscilloscopes |

## Installing a skill

Each folder holds a single `SKILL.md`. Drivers and helper tools are included in
it as code blocks for the agent to save and run, so the file alone is the whole
skill. Nothing assumes a particular PC, operating system, VISA vendor or
instrument address: the examples use factory addresses and placeholder resource
strings. The skills are independent, so install only the ones you need.

For the Claude desktop app or claude.ai, upload each skill as a ZIP. Run
`python package_skills.py` from the repository root. It checks each skill's
name, its description and the files its `SKILL.md` points to, then writes
`dist/<skill-name>.zip` with the skill folder at the top level of the archive,
which is the layout the upload expects. Upload the ZIP under Customize > Skills
and turn the skill on.

For Claude Code, copy the folder to `~/.claude/skills/<skill-name>/`; no ZIP is
needed.

Most skills drive the instrument with PyVISA (any backend: NI-VISA, Keysight
VISA or pyvisa-py), and each carries its own connection and quick-start
examples.

## Scope and safety

These references include documented service, calibration and diagnostic
commands, some of which change calibration or stored state. Each skill marks
those and says what they affect. Read the relevant section before sending one
to an instrument you care about.

## License

MIT, see `LICENSE`. The skills are reference documentation written by the
author; the instruments, firmware and trademarks belong to their respective
manufacturers, and no manufacturer firmware or manual is included here.
