#!/usr/bin/env python3
"""bumpver pre-commit hook: move the "Unreleased" entries of CHANGELOG.md
under the new version, dated today, and stage the file so that it is part
of the release commit.

bumpver passes the versions in BUMPVER_OLD_VERSION / BUMPVER_NEW_VERSION
(vX.Y.Z). Can also be run by hand: changelog_release.py vX.Y.Z [vOLD].
Fails (and so stops the release before the commit) if there is nothing
under "Unreleased".
"""

import datetime
import os
import re
import subprocess
import sys

CHANGELOG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "CHANGELOG.md")
RE_UNRELEASED_LINK = re.compile(r"^\[Unreleased\]: (\S+)/compare/(\S+)\.\.\.HEAD$", re.M)


def release(text, new, old, today):
    """CHANGELOG text with the Unreleased entries released as version new
    (vX.Y.Z), the previous version being old (vX.Y.Z)."""
    head, sep, rest = text.partition("## [Unreleased]\n")
    if not sep:
        raise SystemExit("CHANGELOG.md: no \"## [Unreleased]\" section")
    entries, nxt, tail = rest.partition("\n## [")
    if not entries.strip():
        raise SystemExit("CHANGELOG.md: nothing under \"## [Unreleased]\"; write the entries first")
    number = new.removeprefix("v")
    text = (f"{head}## [Unreleased]\n\n## [{number}] - {today}\n\n{entries.strip()}\n"
            + (f"\n## [{tail}" if nxt else ""))
    m = RE_UNRELEASED_LINK.search(text)
    if m:
        url, since = m.group(1), m.group(2)
        text = (text[:m.start()]
                + f"[Unreleased]: {url}/compare/{new}...HEAD\n[{number}]: {url}/compare/{old or since}...{new}"
                + text[m.end():])
    return text


def main(argv):
    new = argv[1] if len(argv) > 1 else os.environ.get("BUMPVER_NEW_VERSION")
    old = argv[2] if len(argv) > 2 else os.environ.get("BUMPVER_OLD_VERSION")
    if not new:
        raise SystemExit("usage: changelog_release.py vX.Y.Z [vOLD] (or run from bumpver)")
    with open(CHANGELOG, encoding="utf-8") as f:
        text = f.read()
    text = release(text, new, old, datetime.date.today().isoformat())
    with open(CHANGELOG, "w", encoding="utf-8") as f:
        f.write(text)
    # bumpver only stages the files of its file_patterns
    if os.environ.get("BUMPVER_NEW_VERSION"):
        subprocess.run(["git", "add", CHANGELOG], check=True)
    print(f"CHANGELOG.md: Unreleased → {new.removeprefix('v')}")


if __name__ == "__main__":
    main(sys.argv)
