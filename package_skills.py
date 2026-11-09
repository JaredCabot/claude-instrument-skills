"""Check every skill in this repo and package each one as an uploadable ZIP.

Usage:  python package_skills.py            (writes dist/<skill-name>.zip)

Each ZIP holds the skill folder as its top level (<name>/SKILL.md ...), which
is the layout Claude's Customize > Skills upload expects. A skill that fails a
check is reported and not packaged.
"""
import pathlib
import re
import sys
import zipfile

ROOT = pathlib.Path(__file__).resolve().parent
DIST = ROOT / "dist"
NAME_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
SKIP_DIRS = {"__pycache__", ".git", "dist", "manuals"}
SKIP_SUFFIXES = {".pyc", ".pyo", ".bak", ".pdf"}


def frontmatter(text):
    m = re.match(r"^---\r?\n(.*?)\r?\n---\r?\n", text, re.S)
    if not m:
        return None
    fields = {}
    for line in m.group(1).splitlines():
        k, sep, v = line.partition(":")
        if sep and not line.startswith((" ", "\t")):
            v = v.strip()
            if len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'":
                v = v[1:-1]
            fields[k.strip()] = v
    return fields


def check(skill_dir):
    problems = []
    text = (skill_dir / "SKILL.md").read_text(encoding="utf-8")
    fm = frontmatter(text)
    if fm is None:
        return ["SKILL.md has no YAML frontmatter"]
    name, desc = fm.get("name", ""), fm.get("description", "")
    if not NAME_RE.match(name) or len(name) > 64:
        problems.append(f"name {name!r} must be lowercase letters, digits and hyphens, at most 64 characters")
    if name != skill_dir.name:
        problems.append(f"name {name!r} does not match folder {skill_dir.name!r}")
    if not desc:
        problems.append("description is missing")
    elif len(desc) > 1024:
        problems.append(f"description is {len(desc)} characters (limit 1024)")
    # files the skill points at with a relative path must ship with it
    for ref in sorted(set(re.findall(r"`((?:scripts|references|assets)/[\w./-]+)`", text))):
        if not (skill_dir / ref).exists():
            problems.append(f"references missing file {ref}")
    return problems


def files_of(skill_dir):
    for f in sorted(skill_dir.rglob("*")):
        rel = f.relative_to(skill_dir)
        if f.is_file() and not SKIP_DIRS & set(rel.parts) and f.suffix not in SKIP_SUFFIXES:
            yield f


def main():
    skills = sorted(d for d in ROOT.iterdir() if d.is_dir() and (d / "SKILL.md").exists())
    DIST.mkdir(exist_ok=True)
    failed = 0
    for d in skills:
        problems = check(d)
        if problems:
            failed += 1
            print(f"FAIL  {d.name}")
            for p in problems:
                print(f"        {p}")
            continue
        out = DIST / f"{d.name}.zip"
        with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
            n = 0
            for f in files_of(d):
                z.write(f, f"{d.name}/{f.relative_to(d).as_posix()}")
                n += 1
        print(f"ok    {d.name:28s} {n:2d} file(s)  {out.stat().st_size / 1024:6.1f} KB")
    print(f"\n{len(skills) - failed} packaged, {failed} failed -> {DIST}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
