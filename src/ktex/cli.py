"""Point d'entrée en ligne de commande : ktex build|check|clean|corrupt-aux|targets."""

import argparse
import os
import sys

from . import __version__, logcheck
from .build import build
from .clean import clean
from .config import ConfigError, find_config, load_targets, resolve_target


def _add_target_args(p):
    p.add_argument("target", nargs="?",
                   help="nom de cible du ktex.toml ou fichier .tex (défaut : première cible, "
                        "sinon l'unique .tex principal du répertoire)")
    p.add_argument("-d", "--build-dir",
                   help="répertoire de compilation (défaut : auto, répertoire temporaire hors des "
                        "sources ; « . » pour compiler sur place)")


def _color(args):
    if getattr(args, "color", None) is None:
        return sys.stdout.isatty() and not os.environ.get("NO_COLOR")
    return args.color


def main(argv=None):
    ap = argparse.ArgumentParser(
        prog="ktex",
        description="Compilation LaTeX complète (passes, bibliographie, PDF atomique) "
                    "et rapport d'erreurs localisées par fichier:ligne.")
    ap.add_argument("--version", action="version", version=f"ktex {__version__}")
    common = argparse.ArgumentParser(add_help=False)
    color = common.add_mutually_exclusive_group()
    color.add_argument("--color", dest="color", action="store_true", default=None,
                       help="forcer la couleur (défaut : si la sortie est un terminal)")
    color.add_argument("--no-color", dest="color", action="store_false")
    sub = ap.add_subparsers(dest="cmd")

    b = sub.add_parser("build", parents=[common], help="compiler (commande par défaut)")
    _add_target_args(b)
    b.add_argument("-e", "--engine", choices=["pdflatex", "xelatex", "lualatex", "auto"])
    b.add_argument("-b", "--bib", choices=["biber", "bibtex", "none", "auto"])
    b.add_argument("-n", "--passes", help="nombre fixe de passes LaTeX, ou « auto »")
    b.add_argument("--max-passes", type=int)
    b.add_argument("-j", "--jobname", help="nom du job (défaut : <main>, ou <main>-tmp sur place)")
    b.add_argument("-o", "--output", help="PDF final (défaut : <main>.pdf)")
    b.add_argument("--log-prefix", help="préfixe des logs (défaut : output)")
    b.add_argument("-q", "--quiet", action="store_true", default=None,
                   help="ne pas afficher la sortie de LaTeX/Biber (toujours dans les logs)")
    b.add_argument("--boxes", dest="show_boxes", action="store_true", default=None,
                   help="détailler aussi les boîtes mal remplies dans le terminal")

    c = sub.add_parser("check", parents=[common], help="analyser le log d'une compilation déjà faite")
    _add_target_args(c)
    c.add_argument("-j", "--jobname", help="job dont lire JOB.log / JOB.blg")
    c.add_argument("-o", "--report", help="fichier rapport (défaut : <log_prefix>.errors.log)")
    c.add_argument("--boxes", action="store_true", help="détailler les boîtes dans le terminal")

    k = sub.add_parser("clean", help="supprimer les fichiers auxiliaires")
    _add_target_args(k)
    k.add_argument("--dry-run", action="store_true", help="lister sans supprimer")
    k.add_argument("--keep-logs", action="store_true", help="garder <log_prefix>.errors.log et les logs sur place")

    a = sub.add_parser("corrupt-aux", help="lister les .aux tronqués par une compilation interrompue")
    _add_target_args(a)

    sub.add_parser("targets", help="lister les cibles du ktex.toml")

    argv = sys.argv[1:] if argv is None else list(argv)
    # Sans sous-commande : build (ktex, ktex <cible>, ktex these.tex -n 2…)
    if not argv or (argv[0] not in sub.choices and argv[0] not in ("-h", "--help", "--version")):
        argv = ["build", *argv]
    args = ap.parse_args(argv)

    try:
        if args.cmd == "targets":
            cfg = find_config(os.getcwd())
            if not cfg:
                print("pas de ktex.toml ici ni dans les répertoires parents")
                return 1
            for i, (name, t) in enumerate(load_targets(cfg).items()):
                print(f"{name}{' (défaut)' if i == 0 else ''}: {os.path.join(os.path.relpath(t.root), t.main)}"
                      f" → {t.pdf}")
            return 0

        overrides = {}
        if args.cmd == "build":
            overrides = {k: getattr(args, k) for k in
                         ("engine", "bib", "passes", "max_passes", "jobname", "output",
                          "log_prefix", "quiet", "show_boxes")}
        elif args.cmd == "check":
            overrides = {"jobname": args.jobname}
        overrides["build_dir"] = getattr(args, "build_dir", None)
        # Chemins donnés en ligne de commande : relatifs au répertoire courant
        # (ceux du ktex.toml sont relatifs au fichier de configuration)
        for k in ("build_dir", "output", "log_prefix"):
            if overrides.get(k):
                overrides[k] = os.path.abspath(os.path.expanduser(overrides[k]))
        t = resolve_target(args.target, overrides)
    except ConfigError as e:
        print(f"ktex: {e}", file=sys.stderr)
        return 2

    if args.cmd == "build":
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
