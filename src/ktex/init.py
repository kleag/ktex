"""ktex init: write a starter ktex.toml for the LaTeX project of a directory."""

import os
import re

from .config import CONFIG_NAME, detect_engine, find_config, find_main_files
from .i18n import _, language

# Documents that are compiled on their own but are not main documents
RE_PART_CLASS = re.compile(r"^\s*\\documentclass(?:\[[^\]]*\])?\{(?:standalone|subfiles)\}", re.M)
RE_BARE_KEY = re.compile(r"^[A-Za-z0-9_-]+$")


def find_project(start):
    """(directory, main files): the closest directory, from start up, that
    contains main .tex files, without leaving a git repository; (None, [])
    if there is none."""
    d = os.path.abspath(start)
    while True:
        mains = [m for m in find_main_files(d) if not _is_part(os.path.join(d, m))]
        if mains:
            return d, mains
        parent = os.path.dirname(d)
        if parent == d or os.path.exists(os.path.join(d, ".git")):
            return None, []
        d = parent


def _is_part(path):
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            return bool(RE_PART_CLASS.search(f.read(20000)))
    except OSError:
        return False


def _key(name):
    return name if RE_BARE_KEY.match(name) else '"' + name.replace("\\", "\\\\").replace('"', '\\"') + '"'


def _string(value):
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def target_names(mains):
    """Target name of each main file: its base name, made unique."""
    names = []
    for main in mains:
        name = os.path.splitext(main)[0]
        while name in names:
            name += "_"
        names.append(name)
    return names


def render_config(root, mains):
    """Text of a ktex.toml with one target per main file (the first one is the default)."""
    docs = "https://kleag.github.io/ktex/" + ("fr/" if language() == "fr" else "") + "configuration/"
    lines = [
        "# " + _("ktex configuration: {url}", url=docs),
        "# " + _("Paths are relative to this file; command-line options take precedence."),
        "",
        "# " + _("Options shared by all targets (default: automatic detection)"),
        '# engine = "auto"         # pdflatex | xelatex | lualatex | auto',
        '# bib = "auto"            # biber | bibtex | none | auto',
        '# passes = "auto"         # ' + _('fixed number of LaTeX passes, or "auto"'),
        '# build_dir = "auto"      # ' + _('"auto": temporary directory; ".": in place; or a path'),
        '# engine_args = ["-synctex=1"]',
        "",
        "# " + _("The first target is the default one (ktex); the others: ktex <name>."),
    ]
    for i, (main, name) in enumerate(zip(mains, target_names(mains))):
        lines += ["", f"[targets.{_key(name)}]", f"main = {_string(main)}"
                  + "  # " + _("detected engine: {engine}", engine=detect_engine(os.path.join(root, main)))]
        if i:
            # Each target its own report next to the sources
            lines.append(f"log_prefix = {_string('output_' + name)}")
    return "\n".join(lines) + "\n"


def init(start):
    """Create the ktex.toml of the project of start. Return the exit status."""
    existing = find_config(start)
    if existing:
        print("ktex: " + _("{config} already exists", config=existing))
        return 1
    root, mains = find_project(start)
    if not root:
        print("ktex: " + _("no main .tex file (with \\documentclass) here or in the parent directories"))
        return 1
    path = os.path.join(root, CONFIG_NAME)
    with open(path, "x", encoding="utf-8") as f:
        f.write(render_config(root, mains))
    print(_("created {config} with target(s): {targets}", config=path,
            targets=", ".join(target_names(mains))))
    return 0
