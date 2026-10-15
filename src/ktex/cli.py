"""Command-line entry point: ktex build|check|clean|corrupt-aux|targets|init."""

import argparse
import os
import sys

from . import __version__, logcheck
from .build import build
from .clean import clean
from .config import ConfigError, find_config, load_targets, resolve_target
from .i18n import _
from .init import init
from .watch import watch


def _add_target_args(p):
    p.add_argument("target", nargs="?",
                   help=_("target name from ktex.toml, or .tex file (default: first target, "
                          "else the only main .tex file of the directory)"))
    p.add_argument("-d", "--build-dir",
                   help=_("build directory (default: auto, a temporary directory outside the "
                          "sources; \".\" to build in place)"))


def _color(args):
    if getattr(args, "color", None) is None:
        return sys.stdout.isatty() and not os.environ.get("NO_COLOR")
    return args.color


def main(argv=None):
    ap = argparse.ArgumentParser(
        prog="ktex",
        description=_("Full LaTeX build (passes, bibliography, atomic PDF) "
                      "and report of errors located as file:line."))
    ap.add_argument("--version", action="version", version=f"ktex {__version__}")
    common = argparse.ArgumentParser(add_help=False)
    color = common.add_mutually_exclusive_group()
    color.add_argument("--color", dest="color", action="store_true", default=None,
                       help=_("force colors (default: if the output is a terminal)"))
    color.add_argument("--no-color", dest="color", action="store_false", help=_("disable colors"))
    sub = ap.add_subparsers(dest="cmd")

    b = sub.add_parser("build", parents=[common], help=_("build (default command)"))
    _add_target_args(b)
    b.add_argument("-e", "--engine", choices=["pdflatex", "xelatex", "lualatex", "auto"], help=_("LaTeX engine"))
    b.add_argument("-b", "--bib", choices=["biber", "bibtex", "none", "auto"], help=_("bibliography backend"))
    b.add_argument("-n", "--passes", help=_("fixed number of LaTeX passes, or \"auto\""))
    b.add_argument("--max-passes", type=int, help=_("maximum number of passes in auto mode (default: 5)"))
    b.add_argument("-j", "--jobname", help=_("job name (default: <main>, or <main>-tmp in place)"))
    b.add_argument("-o", "--output", help=_("final PDF (default: <main>.pdf)"))
    b.add_argument("--log-prefix", help=_("prefix of the logs (default: output)"))
    verbosity = b.add_mutually_exclusive_group()
    verbosity.add_argument("-v", "--verbose", dest="verbose", action="store_true", default=None,
                           help=_("show the raw output of LaTeX/Biber (always in the logs)"))
    verbosity.add_argument("-q", "--quiet", dest="verbose", action="store_false",
                           help=_("hide the raw output of LaTeX/Biber (default)"))
    b.add_argument("--boxes", dest="show_boxes", action="store_true", default=None,
                   help=_("also detail bad boxes in the terminal"))
    b.add_argument("-w", "--watch", action="store_true",
                   help=_("rebuild whenever a source file changes, until Ctrl-C"))

    c = sub.add_parser("check", parents=[common], help=_("analyze the log of a previous build"))
    _add_target_args(c)
    c.add_argument("-j", "--jobname", help=_("job whose JOB.log / JOB.blg to read"))
    c.add_argument("-o", "--report", help=_("report file (default: <log_prefix>.errors.log)"))
    c.add_argument("--boxes", action="store_true", help=_("detail bad boxes in the terminal"))

    k = sub.add_parser("clean", help=_("remove auxiliary files"))
    _add_target_args(k)
    k.add_argument("--dry-run", action="store_true", help=_("list without removing"))
    k.add_argument("--keep-logs", action="store_true", help=_("keep <log_prefix>.errors.log and in-place logs"))

    a = sub.add_parser("corrupt-aux", help=_("list .aux files truncated by an interrupted run"))
    _add_target_args(a)

    sub.add_parser("targets", help=_("list the targets of ktex.toml"))
    sub.add_parser("init", help=_("create a ktex.toml for the LaTeX project of the current directory"))

    argv = sys.argv[1:] if argv is None else list(argv)
    # Without a subcommand: build (ktex, ktex <target>, ktex thesis.tex -n 2…)
    if not argv or (argv[0] not in sub.choices and argv[0] not in ("-h", "--help", "--version")):
        argv = ["build", *argv]
    args = ap.parse_args(argv)

    try:
        if args.cmd == "init":
            return init(os.getcwd())
        if args.cmd == "targets":
            cfg = find_config(os.getcwd())
            if not cfg:
                print(_("no ktex.toml here or in the parent directories"))
                return 1
            for i, (name, t) in enumerate(load_targets(cfg).items()):
                print(f"{name}{_(' (default)') if i == 0 else ''}: {os.path.join(os.path.relpath(t.root), t.main)}"
                      f" → {t.pdf}")
            return 0

        overrides = {}
        if args.cmd == "build":
            overrides = {k: getattr(args, k) for k in
                         ("engine", "bib", "passes", "max_passes", "jobname", "output",
                          "log_prefix", "verbose", "show_boxes")}
        elif args.cmd == "check":
            overrides = {"jobname": args.jobname}
        overrides["build_dir"] = getattr(args, "build_dir", None)
        # Paths given on the command line are relative to the current directory
        # (those of ktex.toml are relative to the configuration file)
        for k in ("build_dir", "output", "log_prefix"):
            if overrides.get(k):
                overrides[k] = os.path.abspath(os.path.expanduser(overrides[k]))
        t = resolve_target(args.target, overrides)
    except ConfigError as e:
        print(f"ktex: {e}", file=sys.stderr)
        return 2

    if args.cmd == "build":
        if args.watch:
            return watch(t, lambda target: build(target, color=_color(args)))
        return build(t, color=_color(args))

    report = os.path.abspath(args.report) if args.cmd == "check" and args.report else None
    os.chdir(t.root)
    logcheck.set_root(t.root, t.build_path)
    if args.cmd == "check":
        return logcheck.report(os.path.join(t.build_path, t.job), report or t.log("errors"), color=_color(args),
                               show_boxes=args.boxes or t.show_boxes)
    if args.cmd == "clean":
        return clean(t, dry_run=args.dry_run, logs=not args.keep_logs)
    if args.cmd == "corrupt-aux":
        for f in logcheck.corrupt_aux_files():
            print(f)
        return 0
    return 2


if __name__ == "__main__":
    sys.exit(main())
