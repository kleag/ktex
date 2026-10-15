"""Compilation complète : passes LaTeX, bibliographie, copie atomique du
PDF et rapport d'erreurs."""

import hashlib
import os
import re
import shutil
import subprocess
import sys

from . import logcheck
from .config import detect_bib, detect_engine

# Messages par lesquels LaTeX et ses paquets réclament une passe de plus
RE_RERUN = re.compile(
    r"Rerun to get|Label\(s\) may have changed|Please rerun LaTeX|Rerun LaTeX|"
    r"\(rerunfilecheck\).*[Rr]erun")


# Fichier témoin d'un répertoire de compilation créé par ktex (seul cas
# où ktex clean le supprime entièrement)
MARKER = ".ktex"


def step(msg):
    print(f"--- {msg} ---", flush=True)


def run_logged(cmd, log_path, env, quiet=False, cwd=None):
    """Lance cmd en recopiant sa sortie, au fil de l'eau, dans log_path et
    (sauf quiet) sur le terminal : « cmd 2>&1 | tee log_path »."""
    out = sys.stdout.buffer
    with open(log_path, "wb") as log:
        try:
            proc = subprocess.Popen(cmd, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                    stderr=subprocess.STDOUT, env=env, cwd=cwd)
        except FileNotFoundError:
            msg = f"ktex: commande introuvable : {cmd[0]}\n".encode()
            log.write(msg)
            out.write(msg)
            out.flush()
            return 127
        try:
            for chunk in iter(lambda: proc.stdout.read1(65536), b""):
                if not quiet:
                    out.write(chunk)
                    out.flush()
                log.write(chunk)
        except KeyboardInterrupt:
            proc.terminate()
            proc.wait()
            raise
        return proc.wait()


# Fichiers relus par la passe suivante : s'ils changent, il faut une passe de plus
STATE_EXTENSIONS = (".aux", ".toc", ".lof", ".lot", ".out", ".nav", ".snm", ".bbl")


def state_digest(bdir):
    """Empreinte des fichiers auxiliaires du répertoire de compilation."""
    h = hashlib.sha1()
    for d, dirs, names in os.walk(bdir):
        dirs.sort()
        for nm in sorted(names):
            if nm.endswith(STATE_EXTENSIONS):
                p = os.path.join(d, nm)
                h.update(p.encode())
                try:
                    with open(p, "rb") as f:
                        h.update(f.read())
                except OSError:
                    pass
    return h.hexdigest()


def needs_rerun(jobpath):
    try:
        with open(jobpath + ".log", encoding="utf-8", errors="replace") as f:
            return bool(RE_RERUN.search(f.read()))
    except OSError:
        return False


def purge_corrupt_aux():
    bad = logcheck.corrupt_aux_files()
    if bad:
        step("Removing truncated .aux files from an interrupted run")
        for f in bad:
            print(f)
            try:
                os.remove(f)
            except OSError:
                pass


def mirror_tree(root, build_dir):
    """Avec -output-directory, TeX écrit l'.aux de \\include{dir/chap} dans
    build_dir/dir/ sans créer ce répertoire : on reproduit l'arborescence des
    sources (répertoires contenant des .tex)."""
    os.makedirs(build_dir, exist_ok=True)
    marker = os.path.join(build_dir, MARKER)
    if not os.path.exists(marker):
        with open(marker, "w") as f:
            f.write(f"Répertoire de compilation de ktex pour {root}\n")
    for d, dirs, names in os.walk(root):
        dirs[:] = [x for x in dirs if not x.startswith(".")
                   and os.path.abspath(os.path.join(d, x)) != build_dir]
        if any(n.endswith(".tex") for n in names):
            os.makedirs(os.path.join(build_dir, os.path.relpath(d, root)), exist_ok=True)


def install_atomic(src, dest):
    """Remplace dest par src sans que dest soit jamais vide ou partiel, même
    si src est sur un autre système de fichiers (/tmp en tmpfs)."""
    try:
        os.replace(src, dest)
    except OSError:
        tmp = dest + ".ktex-part"
        shutil.copyfile(src, tmp)
        os.replace(tmp, dest)
        os.remove(src)


def build(t, color=None):
    """Compile la cible t. Renvoie le code de sortie (0 si le PDF a été produit)."""
    if color is None:
        color = sys.stdout.isatty()
    root = os.path.abspath(t.root)
    os.chdir(root)
    if not os.path.isfile(t.main):
        print(f"ktex: {t.main} introuvable dans {root}", file=sys.stderr)
        return 2
    bdir = t.build_path
    logcheck.set_root(root, bdir)
    engine = t.engine if t.engine != "auto" else detect_engine(t.main)
    job = t.job
    jobpath = os.path.join(bdir, job)
    errors_log = t.log("errors")  # rapport dans les sources, logs bruts dans bdir
    # Pas de coupure des lignes du log à 79 colonnes : noms de fichiers et
    # messages restent sur une ligne, analysable par logcheck
    env = dict(os.environ, max_print_line="10000")
    # -file-line-error : erreurs au format ./fichier.tex:LIGNE: message
    # -interaction=nonstopmode : jamais d'arrêt sur l'invite « ? » ; une passe
    # tuée pendant cette attente laisse des .aux tronqués
    # -recorder : liste des fichiers lus et produits dans <job>.fls
    latex = [engine, "-file-line-error", "-interaction=nonstopmode", "-recorder",
             f"-jobname={job}"]
    if t.out_of_source:
        latex.append(f"-output-directory={bdir}")
    latex += [*t.engine_args, t.main]

    print(f"ktex: {t.main} → {t.pdf} ({engine}, {bdir}/{job}.*)", flush=True)
    try:
        if t.out_of_source:
            mirror_tree(root, bdir)
        # Des .aux tronqués par une compilation interrompue font échouer la
        # passe suivante dès \begin{document} (« File ended while scanning use of… »)
        purge_corrupt_aux()

        npass = 1
        fixed = t.passes if isinstance(t.passes, int) else None
        total = f" of {fixed}" if fixed else ""

        changed = True  # les fichiers auxiliaires ont-ils changé pendant la dernière passe ?

        def latex_pass():
            nonlocal changed
            step(f"Running {engine} (pass {npass}{total})")
            before = state_digest(bdir)
            if run_logged(latex, os.path.join(bdir, t.log(npass)), env, t.quiet) != 0:
                print(f"ERROR: {engine} failed on pass {npass}. Aborting.")
                return False
            changed = state_digest(bdir) != before
            return True

        if not latex_pass():
            return 1

        bib = t.bib if t.bib != "auto" else detect_bib(jobpath)
        if bib != "none":
            step(f"Running {bib} for bibliography")
            if bib == "biber":
                # Lancé depuis les sources : chemins des .bib relatifs à root
                cmd, cwd, benv = ["biber", f"--output-directory={bdir}", job], root, env
            else:
                # bibtex écrit à côté du .aux : on le lance dans bdir en lui
                # indiquant où chercher .bib et .bst
                sep = os.pathsep
                benv = dict(env, BIBINPUTS=root + sep + env.get("BIBINPUTS", ""),
                            BSTINPUTS=root + sep + env.get("BSTINPUTS", ""))
                cmd, cwd = ["bibtex", job], bdir
            if run_logged(cmd, os.path.join(bdir, t.log("bib")), benv, t.quiet, cwd=cwd) != 0:
                print(f"ERROR: {bib} failed. Aborting.")
                return 1

        while True:
            if fixed is not None:
                if npass >= fixed:
                    break
            else:
                # Après la bibliographie il faut au moins une passe (deux pour
                # bibtex) ; ensuite, tant que les fichiers auxiliaires changent
                # (table des matières, navigation beamer… ne le signalent pas
                # toujours) ou que LaTeX réclame une passe
                want = ((bib != "none" and npass < (3 if bib == "bibtex" else 2))
                        or changed or needs_rerun(jobpath))
                if not want:
                    break
                if npass >= t.max_passes:
                    print(f"WARNING: still asking for a rerun after {npass} passes; giving up.")
                    break
            npass += 1
            if not latex_pass():
                print_banner("❌ Failure: LaTeX compilation reported an error.\nThe final PDF was not updated.")
                return 1

        if not os.path.isfile(jobpath + ".pdf"):
            print_banner(f"❌ Failure: {jobpath}.pdf was not produced.")
            return 1
        step("Moving PDF to final destination")
        # Remplacement atomique : la visionneuse ne voit jamais un PDF vide ou partiel
        install_atomic(jobpath + ".pdf", t.pdf)
        if os.path.isfile(jobpath + ".synctex.gz"):
            install_atomic(jobpath + ".synctex.gz", os.path.splitext(t.pdf)[0] + ".synctex.gz")
        print_banner(f"✅ Success: Full compilation process complete!\nFinal file: {t.pdf}")
        return 0
    finally:
        # Quelle que soit l'issue, résumer erreurs et avertissements avec leur fichier:ligne
        if os.path.isfile(jobpath + ".log"):
            step(f"Errors and warnings (details in {errors_log})")
            try:
                logcheck.report(jobpath, errors_log, color=color, show_boxes=t.show_boxes)
            except Exception as e:  # le rapport ne doit jamais masquer l'issue du build
                print(f"ktex: analyse du log impossible : {e}", file=sys.stderr)


def print_banner(msg):
    print("=================================================")
    print(msg)
    print("=================================================", flush=True)
