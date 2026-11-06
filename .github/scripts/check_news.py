r"""
Check that the staged news entries in doc/news/ are well-formed.

rever merges every file in doc/news/ except TEMPLATE.rst into the ChangeLog
when a release is made, so a malformed entry would end up in the ChangeLog.

Each entry must be UTF-8 without BOM, contain only the known section
headers, each followed by at least one bullet starting with the verb of its
section, and no ``<news item>`` placeholders.

Adapted from the metadata-schema repository.

Run with ``pixi run check-news``.
"""

import re
import sys
from pathlib import Path

NEWS_DIR = Path(__file__).resolve().parents[2] / "doc" / "news"
TEMPLATE = "TEMPLATE.rst"
SECTIONS = {
    "**Added:**": "Added",
    "**Changed:**": "Changed",
    "**Deprecated:**": "Deprecated",
    "**Removed:**": "Removed",
    "**Fixed:**": "Fixed",
    "**Performance:**": "Improved",
}
HEADER = re.compile(r"^\*\*.*\*\*$")


def check(path):
    r"""Return a list of problems found in the news entry at ``path``."""
    raw = path.read_bytes()
    if raw.startswith(b"\xef\xbb\xbf"):
        return ["starts with a byte order mark (BOM); save as UTF-8 without BOM"]
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as error:
        return [f"is not valid UTF-8 ({error})"]

    problems = []
    if "<news item>" in text:
        problems.append("contains a '<news item>' placeholder")

    section = None
    bullets = {}
    for number, line in enumerate(text.replace("\r", "").split("\n"), start=1):
        if not line.strip():
            continue
        if HEADER.match(line.strip()):
            section = line.strip()
            if section not in SECTIONS:
                problems.append(f"line {number}: unknown section header {section}")
            bullets.setdefault(section, 0)
        elif section is None:
            problems.append(f"line {number}: text before the first section header")
        elif line.startswith("* "):
            bullets[section] += 1
            verb = SECTIONS.get(section)
            if verb and not line[2:].startswith(verb):
                problems.append(f"line {number}: bullet in {section} must start with '{verb}'")
        elif not line.startswith("  "):
            problems.append(
                f"line {number}: expected a '* ' bullet or an indented continuation line"
            )

    if not bullets:
        problems.append("contains no section")
    problems.extend(
        f"section {name} has no entries; remove it"
        for name, count in bullets.items()
        if count == 0
    )
    return problems


def main():
    r"""Check all news entries and exit with 1 if any is malformed."""
    failed = False
    for path in sorted(NEWS_DIR.iterdir()):
        if path.name == TEMPLATE or not path.is_file():
            continue
        for problem in check(path):
            print(f"doc/news/{path.name}: {problem}")
            failed = True
    if failed:
        print("See 'News entry' in CONTRIBUTING.md.")
        sys.exit(1)


if __name__ == "__main__":
    main()
