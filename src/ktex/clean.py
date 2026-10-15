"""Suppression des fichiers auxiliaires, sans toucher aux sources.

Deux sources de vérité, sans jamais descendre en dehors de la racine :
- les lignes OUTPUT des fichiers <job>.fls écrits par -recorder ;
- à défaut, les extensions auxiliaires usuelles, uniquement pour les fichiers
  dont le nom de base est celui d'un .tex existant ou d'un job connu.
"""

import os
import shutil

from .build import MARKER

AUX_EXTENSIONS = (
    ".aux", ".bbl", ".bcf", ".blg", ".fls", ".lof", ".log", ".lot", ".nav", ".out",
    ".run.xml", ".snm", ".synctex.gz", ".toc", ".vrb", ".xdv", ".idx", ".ind", ".ilg",
    ".glo", ".gls", ".glg", ".ist", ".acn", ".acr", ".alg", ".loa", ".lol", ".thm",
    ".fdb_latexmk",
)
# Ne jamais supprimer ces fichiers, même s'ils apparaissent comme OUTPUT
PROTECTED = (".tex", ".bib", ".sty", ".cls", ".bst", ".bbx", ".cbx", ".png", ".jpg",
             ".jpeg", ".svg", ".eps")


def _inside(root, path):
    ap = os.path.abspath(os.path.join(root, path))
    return ap if ap.startswith(root + os.sep) else None


def _from_fls(root, keep):
    found = set()
    for nm in os.listdir(root):
        if not nm.endswith(".fls"):
            continue
        with open(os.path.join(root, nm), encoding="utf-8", errors="replace") as f:
            for line in f:
                if line.startswith("OUTPUT "):
                    ap = _inside(root, line[7:].strip())
                    if ap and ap not in keep and not ap.endswith(PROTECTED):
                        found.add(ap)
        found.add(os.path.join(root, nm))
    return found


def _by_extension(root, jobs, keep):
    found = set()
    for d, dirs, names in os.walk(root):
        dirs[:] = [x for x in dirs if not x.startswith(".")]
        stems = {n[:-4] for n in names if n.endswith(".tex")}
        if d == root:
            stems |= set(jobs)
        for n in names:
            for ext in AUX_EXTENSIONS:
                if n.endswith(ext) and n[:-len(ext)] in stems:
                    p = os.path.join(d, n)
                    if p not in keep:
                        found.add(p)
                    break
    return found


def clean(t, dry_run=False, logs=True):
    """Supprime le répertoire de compilation de la cible t s'il est hors des
    sources, et les fichiers auxiliaires restés dans les sources (compilation
    sur place, ancienne compilation…)."""
    root = os.path.abspath(t.root)
    bdir = t.build_path
    removed_dir = False
    if t.out_of_source and os.path.isdir(bdir):
        # Uniquement un répertoire créé par ktex, et jamais un parent des sources
        if root == bdir or root.startswith(bdir + os.sep) or not os.path.isfile(os.path.join(bdir, MARKER)):
            print(f"ktex: {bdir} n'a pas été créé par ktex (pas de {MARKER}) : non supprimé")
        else:
            print(("would remove " if dry_run else "removed ") + bdir + os.sep)
            if not dry_run:
                shutil.rmtree(bdir)
            removed_dir = True
    keep = {os.path.join(root, t.pdf), os.path.join(root, t.main)}
    jobs = {t.job, t.stem}
    victims = _from_fls(root, keep) | _by_extension(root, jobs, keep)
    if not t.out_of_source:
        victims.add(os.path.join(root, t.job + ".pdf"))
    victims -= keep
    if logs:
        for nm in os.listdir(root):
            if nm.startswith(t.log_prefix + ".") and nm.endswith(".log"):
                victims.add(os.path.join(root, nm))
    victims = sorted(p for p in victims if os.path.isfile(p))
    for p in victims:
        print(("would remove " if dry_run else "removed ") + os.path.relpath(p, root))
        if not dry_run:
            os.remove(p)
    if not victims and not removed_dir:
        print("nothing to clean")
    return 0
