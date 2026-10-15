"""Configuration : options en ligne de commande, fichier ktex.toml et
détection automatique (moteur, bibliographie).

Exemple de ktex.toml (placé à la racine du document) :

    # Options communes à toutes les cibles
    engine = "xelatex"      # pdflatex | xelatex | lualatex | auto
    bib = "biber"           # biber | bibtex | none | auto
    passes = 3              # nombre fixe de passes LaTeX, ou "auto"

    [targets.these]         # la première cible est celle par défaut
    main = "these.tex"

    [targets.soutenance]
    main = "soutenance.tex"
    bib = "none"
    log_prefix = "output_soutenance"
"""

import hashlib
import os
import re
import sys
import tempfile
import tomllib
from dataclasses import dataclass, field, fields

CONFIG_NAME = "ktex.toml"
ENGINES = ("pdflatex", "xelatex", "lualatex")
BIB_BACKENDS = ("biber", "bibtex")


@dataclass
class Target:
    main: str                     # fichier .tex principal (relatif à root)
    root: str = "."               # répertoire de compilation
    engine: str = "auto"
    bib: str = "auto"
    passes: object = "auto"       # int ou "auto"
    max_passes: int = 5           # plafond en mode auto
    build_dir: str = "auto"       # auto : répertoire temporaire hors des sources ; "." : sur place
    jobname: str = ""             # défaut : <main> (<main>-tmp si build_dir = ".")
    output: str = ""              # défaut : <main>.pdf
    log_prefix: str = "output"    # output.1.log, output.bib.log (build_dir), output.errors.log (root)
    quiet: bool = False           # ne pas recopier la sortie des outils sur le terminal
    engine_args: list = field(default_factory=list)
    show_boxes: bool = False      # boîtes détaillées dans le résumé terminal

    @property
    def stem(self):
        return os.path.splitext(os.path.basename(self.main))[0]

    @property
    def out_of_source(self):
        return os.path.abspath(self.build_path) != os.path.abspath(self.root)

    @property
    def build_path(self):
        """Répertoire absolu où sont écrits les fichiers produits par TeX."""
        if self.build_dir == "auto":
            # Un répertoire par document (le hachage distingue deux documents de même nom)
            h = hashlib.sha1(os.path.abspath(os.path.join(self.root, self.main)).encode()).hexdigest()[:8]
            return os.path.join(tempfile.gettempdir(), f"ktex-{self.stem}-{h}")
        return os.path.abspath(os.path.join(self.root, os.path.expanduser(self.build_dir)))

    @property
    def job(self):
        # Sur place, un nom de job distinct du PDF final permet le renommage
        # atomique. Pas de point : biber prendrait la suite pour une extension.
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
    """Cherche ktex.toml dans start puis ses parents."""
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
        raise ConfigError(f"{where} : option(s) inconnue(s) : {', '.join(sorted(unknown))}")
    if "main" not in values:
        raise ConfigError(f"{where} : « main » manquant")
    return Target(**values)


def load_targets(path):
    """{nom: Target} dans l'ordre du fichier (racine = répertoire du fichier)."""
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
    """Cible désignée par spec : nom de cible du ktex.toml, fichier .tex,
    ou None (cible par défaut du ktex.toml, sinon unique .tex principal
    du répertoire courant). overrides : options de la ligne de commande."""
    target = None
    if spec and (spec.endswith(".tex") or os.path.isfile(spec)):
        main = os.path.abspath(spec)
        if not os.path.isfile(main):
            raise ConfigError(f"{spec} introuvable")
        cfg = find_config(os.path.dirname(main))
        if cfg:
            # Reprendre les options d'une cible qui compile ce fichier, ou les options communes
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
                raise ConfigError(f"{cfg} : aucune cible définie")
            if spec:
                if spec not in targets:
                    raise ConfigError(f"cible « {spec} » inconnue ; cibles : {', '.join(targets)}")
                target = targets[spec]
            else:
                target = next(iter(targets.values()))
        elif spec:
            raise ConfigError(f"« {spec} » n'est ni un fichier .tex ni une cible (pas de {CONFIG_NAME})")
        else:
            mains = find_main_files(os.getcwd())
            if len(mains) != 1:
                raise ConfigError(
                    "impossible de deviner le fichier principal ("
                    + (", ".join(mains) if mains else "aucun \\documentclass trouvé")
                    + f") : le donner en argument ou créer un {CONFIG_NAME}")
            target = Target(main=mains[0], root=os.getcwd())
    for k, v in overrides.items():
        if v is not None:
            setattr(target, k, v)
    if isinstance(target.passes, str) and target.passes != "auto":
        try:
            target.passes = int(target.passes)
        except ValueError:
            raise ConfigError(f"passes : entier ou « auto » attendu, pas « {target.passes} »")
    if target.engine not in ENGINES + ("auto",):
        raise ConfigError(f"moteur inconnu « {target.engine} » ({', '.join(ENGINES)}, auto)")
    if target.bib not in BIB_BACKENDS + ("none", "auto"):
        raise ConfigError(f"bibliographie inconnue « {target.bib} » ({', '.join(BIB_BACKENDS)}, none, auto)")
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
    """Moteur : commentaire magique « % !TEX program = xelatex », sinon
    xelatex si le préambule ou un .sty/.cls local (thème beamer, classe
    maison…) charge fontspec/polyglossia/unicode-math, sinon pdflatex."""
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
    """Après une passe : biber si biblatex a écrit un .bcf, bibtex si le .aux
    contient \\bibdata, sinon rien. jobpath : chemin du job sans extension."""
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
