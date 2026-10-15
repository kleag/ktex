import os
import shutil
import string
import textwrap

import pytest

from ktex import i18n, logcheck
from ktex.cli import main
from ktex.config import ConfigError, Target, detect_engine, load_targets, resolve_target

HAS = {e: shutil.which(e) is not None for e in ("pdflatex", "xelatex", "bibtex", "biber")}

# In CI, a missing tool must make the integration tests fail instead of
# silently skipping them.
if os.environ.get("KTEX_REQUIRE_TEX") and not all(HAS.values()):
    raise RuntimeError("missing TeX tools: " + ", ".join(e for e, ok in HAS.items() if not ok))


def write(path, text):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(textwrap.dedent(text).lstrip())


@pytest.fixture(autouse=True)
def default_tex_security(monkeypatch):
    """Builds must work with TeX Live's default (paranoid) write policy, even
    if the developer's shell relaxes it (export openout_any=r)."""
    monkeypatch.setenv("openout_any", "p")
    monkeypatch.delenv("TEXMFOUTPUT", raising=False)


@pytest.fixture(autouse=True)
def english():
    """Tests check English messages, whatever the locale of the machine."""
    i18n.set_language("en")
    yield
    i18n.set_language("en")


# --- Configuration -------------------------------------------------------------

def test_detect_engine(tmp_path):
    p = tmp_path / "a.tex"
    write(p, r"\documentclass{article}\usepackage{fontspec}\begin{document}x\end{document}")
    assert detect_engine(p) == "xelatex"
    write(p, "% !TEX program = lualatex\n\\documentclass{article}\\begin{document}x\\end{document}")
    assert detect_engine(p) == "lualatex"
    write(p, "\\documentclass{article}\n%\\usepackage{fontspec}\n\\begin{document}x\\end{document}")
    assert detect_engine(p) == "pdflatex"
    # fontspec loaded by a local beamer theme
    write(tmp_path / "beamerthemeX.sty", "\\RequirePackage[no-math]{fontspec}\n")
    assert detect_engine(p) == "xelatex"


def test_targets_and_overrides(tmp_path, monkeypatch):
    write(tmp_path / "ktex.toml", """
        engine = "xelatex"
        passes = 3
        [targets.first]
        main = "a.tex"
        [targets.second]
        main = "b.tex"
        log_prefix = "out_b"
    """)
    write(tmp_path / "a.tex", "x")
    write(tmp_path / "b.tex", "x")
    os.makedirs(tmp_path / "sub")
    monkeypatch.chdir(tmp_path / "sub")
    t = resolve_target(None, {})
    assert (t.main, t.engine, t.passes, t.root) == ("a.tex", "xelatex", 3, str(tmp_path))
    t = resolve_target("second", {"passes": "auto"})
    assert (t.main, t.log_prefix, t.passes) == ("b.tex", "out_b", "auto")
    t = resolve_target(str(tmp_path / "b.tex"), {})
    assert t.log_prefix == "out_b"
    with pytest.raises(ConfigError):
        resolve_target("nope", {})


def test_build_dir_and_job(tmp_path):
    t = Target(main="doc.tex", root=str(tmp_path))
    assert t.out_of_source and t.job == "doc"
    assert not t.build_path.startswith(str(tmp_path))
    t = Target(main="doc.tex", root=str(tmp_path), build_dir=".")
    assert not t.out_of_source and t.job == "doc-tmp"


# --- ktex init -------------------------------------------------------------------

def test_init_single_document(tmp_path, monkeypatch, capsys):
    write(tmp_path / "paper.tex", "\\documentclass{article}\\usepackage{fontspec}\n\\begin{document}x\\end{document}\n")
    monkeypatch.chdir(tmp_path)
    assert main(["init"]) == 0
    text = (tmp_path / "ktex.toml").read_text(encoding="utf-8")
    assert "detected engine: xelatex" in text
    targets = load_targets(str(tmp_path / "ktex.toml"))
    assert list(targets) == ["paper"] and targets["paper"].main == "paper.tex"
    assert targets["paper"].engine == "auto" and targets["paper"].log_prefix == "output"
    # Never overwritten
    assert main(["init"]) == 1
    assert (tmp_path / "ktex.toml").read_text(encoding="utf-8") == text
    assert "already exists" in capsys.readouterr().out


def test_init_from_subdirectory(tmp_path, monkeypatch):
    write(tmp_path / "thesis.tex", "\\documentclass{report}\n\\begin{document}\\include{chap/one}\\end{document}\n")
    write(tmp_path / "my slides.tex", "\\documentclass{beamer}\n\\begin{document}x\\end{document}\n")
    write(tmp_path / "figure.tex", "\\documentclass[tikz]{standalone}\n\\begin{document}x\\end{document}\n")
    write(tmp_path / "chap/one.tex", "\\chapter{One}\n")
    monkeypatch.chdir(tmp_path / "chap")
    assert main(["init"]) == 0
    assert not (tmp_path / "chap/ktex.toml").exists()
    targets = load_targets(str(tmp_path / "ktex.toml"))
    # Sorted main files, standalone figures left out; each target its own report
    assert [(n, t.main, t.log_prefix) for n, t in targets.items()] == [
        ("my slides", "my slides.tex", "output"), ("thesis", "thesis.tex", "output_thesis")]
    assert resolve_target(None, {}).main == "my slides.tex"


def test_init_without_document_stays_in_repository(tmp_path, monkeypatch):
    write(tmp_path / "doc.tex", "\\documentclass{article}\n")
    os.makedirs(tmp_path / "repo/.git")
    os.makedirs(tmp_path / "repo/src")
    monkeypatch.chdir(tmp_path / "repo/src")
    assert main(["init"]) == 1
    assert not (tmp_path / "ktex.toml").exists() and not (tmp_path / "repo/ktex.toml").exists()


def test_init_in_french_is_valid_toml(tmp_path, monkeypatch):
    write(tmp_path / "these.tex", "\\documentclass{report}\n")
    monkeypatch.chdir(tmp_path)
    i18n.set_language("fr")
    assert main(["init"]) == 0
    text = (tmp_path / "ktex.toml").read_text(encoding="utf-8")
    assert "moteur détecté : pdflatex" in text and "/ktex/fr/configuration/" in text
    assert list(load_targets(str(tmp_path / "ktex.toml"))) == ["these"]


# --- Log analysis ---------------------------------------------------------------

def test_logcheck_locates_errors_in_included_files(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    logcheck.set_root(tmp_path)
    write(tmp_path / "main.tex", "x\n")
    write(tmp_path / "ch/one.tex", "a\nb\nc\n")
    write(tmp_path / "job.log", r"""
        This is XeTeX
        (./main.tex (./ch/one.tex
        ./ch/one.tex:3: Undefined control sequence.
        l.3 \foo
                 bar
        LaTeX Warning: Reference `sec:x' on page 1 undefined on input line 2.

        ) [1] )
        LaTeX Warning: There were undefined references.
    """)
    entries = logcheck.analyze(str(tmp_path / "job"))
    err = [e for e in entries if e.kind == "error"]
    assert len(err) == 1 and (err[0].file, err[0].line) == ("ch/one.tex", 3)
    warn = [e for e in entries if "sec:x" in e.msg]
    assert (warn[0].file, warn[0].line) == ("ch/one.tex", 2)


def test_corrupt_aux_in_build_dir(tmp_path, monkeypatch):
    src, bdir = tmp_path / "src", tmp_path / "build"
    write(src / "a.tex", "x")
    write(bdir / "ok.aux", "\\relax\n")
    write(bdir / "bad.aux", "\\relax\n\\newlabel{x}{{1}")
    monkeypatch.chdir(src)
    logcheck.set_root(src, bdir)
    assert logcheck.corrupt_aux_files() == [str(bdir / "bad.aux")]


# --- Real builds -----------------------------------------------------------------

BIB = """
    @article{knuth84,
      author = {Donald E. Knuth}, title = {Literate Programming},
      journal = {The Computer Journal}, year = {1984}, volume = {27}, pages = {97--111}}
"""


@pytest.mark.skipif(not (HAS["pdflatex"] and HAS["bibtex"]), reason="pdflatex/bibtex missing")
def test_pdflatex_bibtex_out_of_source(tmp_path, monkeypatch, capsys):
    write(tmp_path / "refs.bib", BIB)
    write(tmp_path / "doc.tex", r"""
        \documentclass{article}
        \begin{document}
        \section{Intro}\label{s}
        See \ref{s} and \cite{knuth84}.
        \bibliographystyle{plain}
        \bibliography{refs}
        \end{document}
    """)
    monkeypatch.chdir(tmp_path)
    assert main(["doc.tex", "-q", "-d", str(tmp_path / "out")]) == 0
    assert (tmp_path / "doc.pdf").is_file()
    assert sorted(os.listdir(tmp_path)) == ["doc.pdf", "doc.tex", "out", "output.errors.log", "refs.bib"]
    with open(tmp_path / "out" / "doc.bbl") as f:
        assert "knuth84" in f.read()
    assert "0 error(s), 0 warning(s)" in capsys.readouterr().out
    # clean removes the build directory and the report, not the PDF
    assert main(["clean", "-d", str(tmp_path / "out")]) == 0
    assert sorted(os.listdir(tmp_path)) == ["doc.pdf", "doc.tex", "refs.bib"]


@pytest.mark.skipif(not (HAS["xelatex"] and HAS["biber"]), reason="xelatex/biber missing")
def test_xelatex_biber_include_subdir(tmp_path, monkeypatch, capsys):
    write(tmp_path / "bib/refs.bib", BIB)
    write(tmp_path / "chap/one.tex", r"""
        \chapter{One}\label{c1}
        As shown by \textcite{knuth84}, see \cref{c2}.
    """)
    write(tmp_path / "chap/two.tex", r"""
        \chapter{Two}\label{c2}
    """)
    write(tmp_path / "these.tex", r"""
        \documentclass{report}
        \usepackage{fontspec}
        \usepackage[backend=biber]{biblatex}
        \usepackage{hyperref}
        \usepackage{cleveref}
        \addbibresource{bib/refs.bib}
        \begin{document}
        \tableofcontents
        \include{chap/one}
        \include{chap/two}
        \printbibliography
        \end{document}
    """)
    os.makedirs(tmp_path / "sub")
    monkeypatch.chdir(tmp_path / "sub")  # run from a subdirectory
    write(tmp_path / "ktex.toml", """
        [targets.t]
        main = "these.tex"
        build_dir = "_build"
    """)
    assert main([]) == 0
    out = capsys.readouterr().out
    assert "xelatex" in out and "biber" in out
    assert "0 error(s), 0 warning(s)" in out
    assert (tmp_path / "_build/chap/one.aux").is_file()
    assert not (tmp_path / "chap/one.aux").exists()
    assert not (tmp_path / "_build/_build").exists()
    # Up-to-date build directory: the pass after biber is enough
    assert main([]) == 0
    assert "(pass 3)" not in capsys.readouterr().out


@pytest.mark.skipif(not HAS["pdflatex"], reason="pdflatex missing")
def test_error_keeps_old_pdf_and_reports_location(tmp_path, monkeypatch, capsys):
    write(tmp_path / "doc.tex", r"""
        \documentclass{article}
        \begin{document}
        \input{part}
        \end{document}
    """)
    write(tmp_path / "part.tex", "Fine.\n\n\\undefinedmacro\n")
    write(tmp_path / "doc.pdf", "old")
    monkeypatch.chdir(tmp_path)
    assert main(["-d", str(tmp_path / "out")]) == 1
    out = capsys.readouterr().out
    # Raw TeX output hidden by default, but kept in the log named on failure
    assert "This is pdfTeX" not in out and "output.1.log" in out
    with open(tmp_path / "out" / "output.1.log") as f:
        assert "This is pdfTeX" in f.read()
    assert main(["-v", "-d", str(tmp_path / "out")]) == 1
    assert "This is pdfTeX" in capsys.readouterr().out
    with open(tmp_path / "doc.pdf") as f:
        assert f.read() == "old"
    with open(tmp_path / "output.errors.log") as f:
        assert "part.tex:3: Undefined control sequence" in f.read()


# --- Watch mode --------------------------------------------------------------------

def test_watch_dependencies(tmp_path):
    from ktex.watch import dependencies
    t = Target(main="doc.tex", root=str(tmp_path), build_dir="out")
    for f in ("doc.tex", "chap/one.tex", "img/a.png", "refs.bib", "local.sty", "doc.pdf",
              "output.errors.log", "out/doc.aux", "out/doc.bbl"):
        write(tmp_path / f, "x")
    write(tmp_path / "out/doc.fls", f"""
        PWD {tmp_path}
        INPUT /usr/share/texmf/tex/latex/base/article.cls
        INPUT doc.tex
        OUTPUT out/doc.log
        INPUT ./chap/one.tex
        INPUT {tmp_path}/local.sty
        INPUT ./img/a.png
        INPUT out/doc.aux
        INPUT out/doc.bbl
        INPUT ./missing.tex
    """)
    # A shared bibliography outside the sources is watched, a database of the
    # TeX distribution found by Biber is not
    write(tmp_path.parent / "shared/common.bib", "x")
    write(tmp_path / "out/doc.bcf", """
        <bcf:datasource type="file" datatype="bibtex">refs.bib</bcf:datasource>
        <bcf:datasource type="file" datatype="bibtex">../shared/common.bib</bcf:datasource>
        <bcf:datasource type="file" datatype="bibtex">biblatex-examples.bib</bcf:datasource>
    """)
    rel = lambda: sorted(os.path.relpath(p, os.path.realpath(tmp_path)) for p in dependencies(t))
    assert rel() == ["../shared/common.bib", "chap/one.tex", "doc.tex", "img/a.png", "local.sty", "refs.bib"]
    # In place: the job files and what LaTeX writes are not watched,
    # the BibTeX database and a local style are
    t = Target(main="doc.tex", root=str(tmp_path), build_dir=".")
    write(tmp_path / "doc-tmp.fls", f"""
        PWD {tmp_path}
        INPUT doc.tex
        INPUT doc-tmp.aux
        OUTPUT doc-tmp.aux
        INPUT doc-tmp.bbl
        INPUT ./other.aux
        OUTPUT ./other.aux
    """)
    write(tmp_path / "doc-tmp.aux", "\\bibstyle{mystyle}\n\\bibdata{refs,nope}\n")
    for f in ("doc-tmp.bbl", "other.aux", "mystyle.bst"):
        write(tmp_path / f, "x")
    assert rel() == ["doc.tex", "mystyle.bst", "refs.bib"]


def test_watch_rebuilds_on_change(tmp_path, capsys):
    from ktex.watch import watch
    t = Target(main="doc.tex", root=str(tmp_path), build_dir="out")
    write(tmp_path / "doc.tex", "v1")
    write(tmp_path / "part.tex", "p1")
    write(tmp_path / "out/doc.fls", f"PWD {tmp_path}\nINPUT doc.tex\nINPUT part.tex\n")
    builds = []

    def build_fn(target):
        builds.append(1)
        if len(builds) == 1:
            # Edited while the first build runs: rebuild right after it
            write(tmp_path / "part.tex", "p2, longer")
        return len(builds) % 2

    sleeps = []

    def sleep(seconds):
        sleeps.append(seconds)
        if len(builds) == 2 and len(sleeps) == 3:
            write(tmp_path / "doc.tex", "v2, longer")

    assert watch(t, build_fn, sleep=sleep, max_builds=3) == 1
    out = capsys.readouterr().out
    assert "part.tex changed" in out and "doc.tex changed" in out
    assert "watching 2 file(s)" in out


# --- Translations ----------------------------------------------------------------

def test_detect_language():
    assert i18n.detect_language({}) == "en"
    assert i18n.detect_language({"LANG": "fr_FR.UTF-8"}) == "fr"
    assert i18n.detect_language({"LANG": "de_DE.UTF-8"}) == "en"
    assert i18n.detect_language({"LANGUAGE": "fr:en", "LANG": "en_US.UTF-8"}) == "fr"
    assert i18n.detect_language({"LC_ALL": "C.UTF-8", "LANG": "fr_FR.UTF-8"}) == "en"
    assert i18n.detect_language({"KTEX_LANG": "en", "LC_ALL": "fr_FR.UTF-8"}) == "en"


def _message_ids():
    """English messages passed to _() in the sources (plus the report section titles)."""
    import ast
    ids = set()
    for path in sorted(os.listdir(os.path.dirname(i18n.__file__))):
        if not path.endswith(".py"):
            continue
        with open(os.path.join(os.path.dirname(i18n.__file__), path), encoding="utf-8") as f:
            tree = ast.parse(f.read())
        for n in ast.walk(tree):
            if isinstance(n, ast.Call) and getattr(n.func, "id", None) == "_" and n.args:
                args = [n.args[0]] if not isinstance(n.args[0], ast.IfExp) else [n.args[0].body, n.args[0].orelse]
                ids |= {a.value for a in args if isinstance(a, ast.Constant)}
    ids |= {title for _kind, title in logcheck.SECTIONS}
    return ids


def test_french_catalog_is_complete():
    from ktex.translations.fr import MESSAGES
    ids = _message_ids()
    assert len(ids) > 50
    assert sorted(ids - set(MESSAGES)) == []
    assert sorted(set(MESSAGES) - ids) == []
    fields = lambda s: sorted(f for _t, f, _s, _c in string.Formatter().parse(s) if f)
    for en, fr in MESSAGES.items():
        assert fields(en) == fields(fr), en


def test_french_report(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    logcheck.set_root(tmp_path)
    write(tmp_path / "main.tex", "a\n\\begin{itemize}\nb\n")
    write(tmp_path / "job.log", r"""
        (./main.tex
        ./main.tex:4: LaTeX Error: \begin{itemize} on input line 2 ended by \end{document}.
        l.4 \end{document}

        )
    """)
    i18n.set_language("fr")
    out = tmp_path / "report.log"
    assert logcheck.report(str(tmp_path / "job"), str(out), stream=open(os.devnull, "w")) == 1
    text = out.read_text(encoding="utf-8")
    assert text.startswith("===== ERREURS (1) =====\nmain.tex:4: LaTeX Error")
    assert "↳ \\begin{itemize} ouvert probablement en : main.tex:2" in text
    assert "Bilan : 1 erreur(s), 0 avertissement(s), 0 boîte(s) mal remplie(s)" in text
    i18n.set_language("en")
    logcheck.report(str(tmp_path / "job"), str(out), stream=open(os.devnull, "w"))
    assert "↳ \\begin{itemize} probably opened at: main.tex:2" in out.read_text(encoding="utf-8")
