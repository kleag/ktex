"""Removal of auxiliary files, without touching the sources.

Two sources of truth, never going outside the root:
- the OUTPUT lines of the <job>.fls files written by -recorder;
- otherwise, the usual auxiliary extensions, only for files whose base name
  is that of an existing .tex file or of a known job.
"""

import os
import shutil

from .build import MARKER
from .i18n import _

AUX_EXTENSIONS = (
    ".aux", ".bbl", ".bcf", ".blg", ".fls", ".lof", ".log", ".lot", ".nav", ".out",
    ".run.xml", ".snm", ".synctex.gz", ".toc", ".vrb", ".xdv", ".idx", ".ind", ".ilg",
    ".glo", ".gls", ".glg", ".ist", ".acn", ".acr", ".alg", ".loa", ".lol", ".thm",
    ".fdb_latexmk",
)
# Never remove these files, even if they appear as OUTPUT
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
    """Remove the build directory of target t if it is outside the sources,
    and the auxiliary files left in the sources (in-place build, older
    builds…)."""
    root = os.path.abspath(t.root)
    bdir = t.build_path
    removed_dir = False
    if t.out_of_source and os.path.isdir(bdir):
        # Only a directory created by ktex, and never a parent of the sources
        if root == bdir or root.startswith(bdir + os.sep) or not os.path.isfile(os.path.join(bdir, MARKER)):
            print("ktex: " + _("{dir} was not created by ktex (no {marker}): not removed", dir=bdir, marker=MARKER))
        else:
            print(_("would remove {path}" if dry_run else "removed {path}", path=bdir + os.sep))
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
        print(_("would remove {path}" if dry_run else "removed {path}", path=os.path.relpath(p, root)))
        if not dry_run:
            os.remove(p)
    if not victims and not removed_dir:
        print(_("nothing to clean"))
    return 0
