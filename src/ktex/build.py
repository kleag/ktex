"""Full build: LaTeX passes, bibliography, atomic installation of the PDF
and error report."""

import hashlib
import os
import re
import shutil
import subprocess
import sys

from . import logcheck
from .i18n import _
from .config import detect_bib, detect_engine

# Messages by which LaTeX and its packages ask for another pass
RE_RERUN = re.compile(
    r"Rerun to get|Label\(s\) may have changed|Please rerun LaTeX|Rerun LaTeX|"
    r"\(rerunfilecheck\).*[Rr]erun")


# Marker file of a build directory created by ktex (the only case where
# ktex clean removes it entirely)
MARKER = ".ktex"


def step(msg):
    print(f"--- {msg} ---", flush=True)


def run_logged(cmd, log_path, env, verbose=False, cwd=None):
    """Run cmd with its output written to log_path: "cmd >& log_path", or,
    if verbose, also copied as it comes to the terminal: "cmd 2>&1 | tee log_path"."""
    out = sys.stdout.buffer
    with open(log_path, "wb") as log:
        try:
            proc = subprocess.Popen(cmd, stdin=subprocess.DEVNULL,
                                    stdout=subprocess.PIPE if verbose else log,
                                    stderr=subprocess.STDOUT, env=env, cwd=cwd)
        except FileNotFoundError:
            msg = ("ktex: " + _("command not found: {cmd}", cmd=cmd[0]) + "\n").encode()
            log.write(msg)
            out.write(msg)
            out.flush()
            return 127
        try:
            if verbose:
                for chunk in iter(lambda: proc.stdout.read1(65536), b""):
                    out.write(chunk)
                    out.flush()
                    log.write(chunk)
            return proc.wait()
        except KeyboardInterrupt:
            proc.terminate()
            proc.wait()
            raise


# Files read back by the next pass: if they change, another pass is needed
STATE_EXTENSIONS = (".aux", ".toc", ".lof", ".lot", ".out", ".nav", ".snm", ".bbl")


def state_digest(bdir):
    """Digest of the auxiliary files of the build directory."""
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
        step(_("Removing truncated .aux files from an interrupted run"))
        for f in bad:
            print(f)
            try:
                os.remove(f)
            except OSError:
                pass


def mirror_tree(root, build_dir):
    """With -output-directory, TeX writes the .aux of \\include{dir/chap} to
    build_dir/dir/ without creating that directory: mirror the source tree
    (directories containing .tex files)."""
    os.makedirs(build_dir, exist_ok=True)
    marker = os.path.join(build_dir, MARKER)
    if not os.path.exists(marker):
        with open(marker, "w") as f:
            f.write(f"ktex build directory for {root}\n")
    for d, dirs, names in os.walk(root):
        dirs[:] = [x for x in dirs if not x.startswith(".")
                   and os.path.abspath(os.path.join(d, x)) != build_dir]
        if any(n.endswith(".tex") for n in names):
            os.makedirs(os.path.join(build_dir, os.path.relpath(d, root)), exist_ok=True)


def install_atomic(src, dest):
    """Replace dest by src without dest ever being empty or partial, even
    when src is on another filesystem (/tmp on tmpfs)."""
    try:
        os.replace(src, dest)
    except OSError:
        tmp = dest + ".ktex-part"
        shutil.copyfile(src, tmp)
        os.replace(tmp, dest)
        os.remove(src)


def build(t, color=None):
    """Build target t. Return the exit status (0 if the PDF was produced)."""
    if color is None:
        color = sys.stdout.isatty()
    root = os.path.abspath(t.root)
    os.chdir(root)
    if not os.path.isfile(t.main):
        print("ktex: " + _("{main} not found in {root}", main=t.main, root=root), file=sys.stderr)
        return 2
    bdir = t.build_path
    logcheck.set_root(root, bdir)
    engine = t.engine if t.engine != "auto" else detect_engine(t.main)
    job = t.job
    jobpath = os.path.join(bdir, job)
    errors_log = t.log("errors")  # report next to the sources, raw logs in bdir
    # Log lines not wrapped at 79 columns: file names and messages stay on
    # one line, which logcheck can parse
    env = dict(os.environ, max_print_line="10000")
    # -file-line-error: errors as ./file.tex:LINE: message
    # -interaction=nonstopmode: never stop at the "?" prompt; a pass killed
    # while waiting there leaves truncated .aux files
    # -recorder: list of the files read and written in <job>.fls
    latex = [engine, "-file-line-error", "-interaction=nonstopmode", "-recorder",
             f"-jobname={job}"]
    if t.out_of_source:
        latex.append(f"-output-directory={bdir}")
    latex += [*t.engine_args, t.main]

    print(f"ktex: {t.main} → {t.pdf} ({engine}, {bdir}/{job}.*)", flush=True)
    try:
        if t.out_of_source:
            mirror_tree(root, bdir)
        # .aux files truncated by an interrupted run make the next pass fail
        # at \begin{document} ("File ended while scanning use of…")
        purge_corrupt_aux()

        npass = 1
        fixed = t.passes if isinstance(t.passes, int) else None
        total = _(" of {n}", n=fixed) if fixed else ""

        changed = True  # did the auxiliary files change during the last pass?

        def latex_pass():
            nonlocal changed
            step(_("Running {engine} (pass {n}{total})", engine=engine, n=npass, total=total))
            before = state_digest(bdir)
            log = os.path.join(bdir, t.log(npass))
            if run_logged(latex, log, env, t.verbose) != 0:
                print(_("ERROR: {engine} failed on pass {n} (output in {log}). Aborting.",
                        engine=engine, n=npass, log=log))
                return False
            changed = state_digest(bdir) != before
            return True

        if not latex_pass():
            return 1

        bib = t.bib if t.bib != "auto" else detect_bib(jobpath)
        if bib != "none":
            step(_("Running {bib} for bibliography", bib=bib))
            if bib == "biber":
                # Run from the sources: .bib paths are relative to root
                cmd, cwd, benv = ["biber", f"--output-directory={bdir}", job], root, env
            else:
                # bibtex writes next to the .aux: run it in bdir and tell it
                # where to find the .bib and .bst files
                sep = os.pathsep
                benv = dict(env, BIBINPUTS=root + sep + env.get("BIBINPUTS", ""),
                            BSTINPUTS=root + sep + env.get("BSTINPUTS", ""))
                cmd, cwd = ["bibtex", job], bdir
            log = os.path.join(bdir, t.log("bib"))
            if run_logged(cmd, log, benv, t.verbose, cwd=cwd) != 0:
                print(_("ERROR: {bib} failed (output in {log}). Aborting.", bib=bib, log=log))
                return 1

        while True:
            if fixed is not None:
                if npass >= fixed:
                    break
            else:
                # After the bibliography, at least one pass (two for bibtex);
                # then as long as the auxiliary files change (the table of
                # contents, beamer navigation… don't always say so) or LaTeX
                # asks for another pass
                want = ((bib != "none" and npass < (3 if bib == "bibtex" else 2))
                        or changed or needs_rerun(jobpath))
                if not want:
                    break
                if npass >= t.max_passes:
                    print(_("WARNING: still asking for a rerun after {n} passes; giving up.", n=npass))
                    break
            npass += 1
            if not latex_pass():
                print_banner(_("❌ Failure: LaTeX compilation reported an error.\nThe final PDF was not updated."))
                return 1

        if not os.path.isfile(jobpath + ".pdf"):
            print_banner(_("❌ Failure: {pdf} was not produced.", pdf=jobpath + ".pdf"))
            return 1
        step(_("Moving PDF to final destination"))
        # Atomic replacement: the viewer never sees an empty or partial PDF
        install_atomic(jobpath + ".pdf", t.pdf)
        if os.path.isfile(jobpath + ".synctex.gz"):
            install_atomic(jobpath + ".synctex.gz", os.path.splitext(t.pdf)[0] + ".synctex.gz")
        print_banner(_("✅ Success: Full compilation process complete!\nFinal file: {pdf}", pdf=t.pdf))
        return 0
    finally:
        # Whatever the outcome, summarize errors and warnings with their file:line
        if os.path.isfile(jobpath + ".log"):
            step(_("Errors and warnings (details in {report})", report=errors_log))
            try:
                logcheck.report(jobpath, errors_log, color=color, show_boxes=t.show_boxes)
            except Exception as e:  # the report must never mask the build's outcome
                print("ktex: " + _("cannot analyze the log: {error}", error=e), file=sys.stderr)


def print_banner(msg):
    print("=================================================")
    print(msg)
    print("=================================================", flush=True)
