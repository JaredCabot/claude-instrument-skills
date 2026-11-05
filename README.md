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
| `hp-53132a` | HP / Agilent 53132A / 53131A / 53181A universal counters |
| `hp8648-gpib` | HP / Agilent 8648A/B/C/D signal generators |
| `keysight-truevolt-dmm` | Keysight 34460A / 34461A / 34465A / 34470A DMMs |
| `siglent-sdg2000x` | Siglent SDG2000X arbitrary waveform generators |
| `siglent-sds2000x-hd` | Siglent SDS2000X HD oscilloscopes |
| `siglent-spd3303x` | Siglent SPD3303X bench power supplies |
| `siglent-sva1032x` | Siglent SVA1032X spectrum analyzer / VNA |
| `tektronix-tds-gpib` | Tektronix TDS 400/500/600/700/800 oscilloscopes |

## Using a skill

Each folder holds a `SKILL.md`, and some carry extra reference files and a
driver script. To make one available to a Claude agent, place the folder where
your Claude surface looks for skills (for Claude Code, a directory on the
agent's skill path, such as `~/.claude/skills/<name>/`). Copy only the folders
you need; each is independent.

The agent reads `SKILL.md` and follows it. Most skills drive the instrument
over SCPI with PyVISA, and each carries its own connection and quick-start
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
