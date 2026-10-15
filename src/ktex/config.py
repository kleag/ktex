"""Configuration: command-line options, ktex.toml file and automatic
detection (engine, bibliography).

Example ktex.toml (at the root of the document):

    # Options shared by all targets
    engine = "xelatex"      # pdflatex | xelatex | lualatex | auto
    bib = "biber"           # biber | bibtex | none | auto
    passes = 3              # fixed number of LaTeX passes, or "auto"

    [targets.thesis]        # the first target is the default one
    main = "thesis.tex"

    [targets.slides]
    main = "slides.tex"
    bib = "none"
    log_prefix = "output_slides"
"""

import hashlib
import os
import re
import sys
import tempfile
import tomllib
from dataclasses import dataclass, field, fields

from .i18n import _

CONFIG_NAME = "ktex.toml"
ENGINES = ("pdflatex", "xelatex", "lualatex")
BIB_BACKENDS = ("biber", "bibtex")


@dataclass
class Target:
    main: str                     # main .tex file (relative to root)
    root: str = "."               # source directory, where LaTeX is run
    engine: str = "auto"
    bib: str = "auto"
    passes: object = "auto"       # int or "auto"
    max_passes: int = 5           # upper bound in auto mode
    build_dir: str = "auto"       # auto: temporary directory outside the sources; ".": in place
    jobname: str = ""             # default: <main> (<main>-tmp if build_dir = ".")
    output: str = ""              # default: <main>.pdf
    log_prefix: str = "output"    # output.1.log, output.bib.log (build_dir), output.errors.log (root)
    verbose: bool = False         # copy the raw output of the tools to the terminal (always in the logs)
    engine_args: list = field(default_factory=list)
    show_boxes: bool = False      # detail bad boxes in the terminal summary

    @property
    def stem(self):
        return os.path.splitext(os.path.basename(self.main))[0]

    @property
    def out_of_source(self):
        return os.path.abspath(self.build_path) != os.path.abspath(self.root)

    @property
    def build_path(self):
        """Absolute directory where the files produced by TeX are written."""
        if self.build_dir == "auto":
            # One directory per document (the hash tells apart two documents with the same name)
            h = hashlib.sha1(os.path.abspath(os.path.join(self.root, self.main)).encode()).hexdigest()[:8]
            return os.path.join(tempfile.gettempdir(), f"ktex-{self.stem}-{h}")
        return os.path.abspath(os.path.join(self.root, os.path.expanduser(self.build_dir)))

    @property
    def job(self):
        # In place, a job name distinct from the final PDF allows the atomic
        # rename. No dot: biber would take what follows for an extension.
        if self.jobname:
            return self.jobname
        return self.stem if self.out_of_source else f"{self.stem}-tmp"

    @property
    def pdf(self):
        return self.output or f"{self.stem}.pdf"

    def log(self, suffix):
        return f"{self.log_prefix}.{suffix}.log"


class ConfigError(Exception):
    pass


def find_config(start):
    """Look for ktex.toml in start, then in its parents."""
    d = os.path.abspath(start)
    while True:
        p = os.path.join(d, CONFIG_NAME)
        if os.path.isfile(p):
            return p
        parent = os.path.dirname(d)
        if parent == d:
            return None
        d = parent


def _make_target(values, where):
    known = {f.name for f in fields(Target)}
    unknown = set(values) - known
    if unknown:
        raise ConfigError(_("{where}: unknown option(s): {options}", where=where, options=", ".join(sorted(unknown))))
    if "main" not in values:
        raise ConfigError(_("{where}: \"main\" is missing", where=where))
    return Target(**values)


def load_targets(path):
    """{name: Target} in file order (root = directory of the file)."""
    with open(path, "rb") as f:
        data = tomllib.load(f)
    targets_data = data.pop("targets", {})
    common = data
    base = os.path.dirname(os.path.abspath(path))
    targets = {}
    for name, values in targets_data.items():
        merged = {**common, **values}
        merged["root"] = os.path.normpath(os.path.join(base, merged.get("root", ".")))
        targets[name] = _make_target(merged, f"{path} [targets.{name}]")
    if not targets and "main" in common:
        common["root"] = os.path.normpath(os.path.join(base, common.get("root", ".")))
        targets["default"] = _make_target(common, path)
    return targets


def resolve_target(spec, overrides):
    """Target designated by spec: target name from ktex.toml, .tex file, or
    None (default target of ktex.toml, else the only main .tex file of the
    current directory). overrides: command-line options."""
    target = None
    if spec and (spec.endswith(".tex") or os.path.isfile(spec)):
        main = os.path.abspath(spec)
        if not os.path.isfile(main):
            raise ConfigError(_("{path} not found", path=spec))
        cfg = find_config(os.path.dirname(main))
        if cfg:
            # Use the options of a target that builds this file, or the shared options
            for t in load_targets(cfg).values():
                if os.path.abspath(os.path.join(t.root, t.main)) == main:
                    target = t
                    break
        if target is None:
            target = Target(main=os.path.basename(main), root=os.path.dirname(main))
            if cfg:
                with open(cfg, "rb") as f:
                    common = {k: v for k, v in tomllib.load(f).items() if k not in ("targets", "main", "root")}
                for k, v in common.items():
                    setattr(target, k, v)
    else:
        cfg = find_config(os.getcwd())
        if cfg:
            targets = load_targets(cfg)
            if not targets:
                raise ConfigError(_("{config}: no target defined", config=cfg))
            if spec:
                if spec not in targets:
                    raise ConfigError(_("unknown target \"{name}\"; targets: {targets}", name=spec, targets=", ".join(targets)))
                target = targets[spec]
            else:
                target = next(iter(targets.values()))
        elif spec:
            raise ConfigError(_("\"{spec}\" is neither a .tex file nor a target (no {config})", spec=spec, config=CONFIG_NAME))
        else:
            mains = find_main_files(os.getcwd())
            if len(mains) != 1:
                raise ConfigError(_(
                    "cannot guess the main file ({found}): give it as an argument or create a {config}",
                    found=", ".join(mains) if mains else _("no \\documentclass found"), config=CONFIG_NAME))
            target = Target(main=mains[0], root=os.getcwd())
    for k, v in overrides.items():
        if v is not None:
            setattr(target, k, v)
    if isinstance(target.passes, str) and target.passes != "auto":
        try:
            target.passes = int(target.passes)
        except ValueError:
            raise ConfigError(_("passes: integer or \"auto\" expected, not \"{value}\"", value=target.passes))
    if target.engine not in ENGINES + ("auto",):
        raise ConfigError(_("unknown engine \"{engine}\" ({choices}, auto)", engine=target.engine, choices=", ".join(ENGINES)))
    if target.bib not in BIB_BACKENDS + ("none", "auto"):
        raise ConfigError(_("unknown bibliography backend \"{bib}\" ({choices}, none, auto)", bib=target.bib, choices=", ".join(BIB_BACKENDS)))
    return target


RE_DOCUMENTCLASS = re.compile(r"^\s*\\documentclass", re.M)


def find_main_files(d):
    out = []
    for nm in sorted(os.listdir(d)):
        if nm.endswith(".tex"):
            try:
                with open(os.path.join(d, nm), encoding="utf-8", errors="replace") as f:
                    if RE_DOCUMENTCLASS.search(f.read(20000)):
                        out.append(nm)
            except OSError:
                pass
    return out


RE_MAGIC_PROGRAM = re.compile(r"^%\s*!\s*TEX\s+(?:TS-)?program\s*=\s*(\w+)", re.M | re.I)
RE_UNICODE_PKG = re.compile(
    r"^[^%\n]*\\(?:usepackage|RequirePackage)(?:\[[^\]]*\])?\{[^}]*\b(fontspec|polyglossia|unicode-math)\b", re.M)


def detect_engine(main_path):
    """Engine: magic comment "% !TEX program = xelatex", else xelatex if the
    preamble or a local .sty/.cls (beamer theme, custom class…) loads
    fontspec/polyglossia/unicode-math, else pdflatex."""
    with open(main_path, encoding="utf-8", errors="replace") as f:
        head = f.read(50000)
    m = RE_MAGIC_PROGRAM.search(head)
    if m and m.group(1).lower() in ENGINES:
        return m.group(1).lower()
    if RE_UNICODE_PKG.search(head.split("\\begin{document}")[0]):
        return "xelatex"
    d = os.path.dirname(os.path.abspath(main_path))
    for nm in sorted(os.listdir(d)):
        if nm.endswith((".sty", ".cls")):
            try:
                with open(os.path.join(d, nm), encoding="utf-8", errors="replace") as f:
                    if RE_UNICODE_PKG.search(f.read()):
                        return "xelatex"
            except OSError:
                pass
    return "pdflatex"


def detect_bib(jobpath):
    """After a pass: biber if biblatex wrote a .bcf, bibtex if the .aux
    contains \\bibdata, else none. jobpath: path of the job without extension."""
    if os.path.isfile(jobpath + ".bcf"):
        return "biber"
    try:
        with open(jobpath + ".aux", encoding="utf-8", errors="replace") as f:
            if "\\bibdata" in f.read():
                return "bibtex"
    except OSError:
        pass
    return "none"


def warn(msg):
    print(f"ktex: {msg}", file=sys.stderr)
