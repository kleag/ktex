import os
import shutil
import textwrap

import pytest

from ktex import logcheck
from ktex.cli import main
from ktex.config import ConfigError, Target, detect_engine, resolve_target

HAS = {e: shutil.which(e) is not None for e in ("pdflatex", "xelatex", "bibtex", "biber")}


def write(path, text):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(textwrap.dedent(text).lstrip())


# --- Configuration -------------------------------------------------------------

def test_detect_engine(tmp_path):
    p = tmp_path / "a.tex"
    write(p, r"\documentclass{article}\usepackage{fontspec}\begin{document}x\end{document}")
    assert detect_engine(p) == "xelatex"
    write(p, "% !TEX program = lualatex\n\\documentclass{article}\\begin{document}x\\end{document}")
    assert detect_engine(p) == "lualatex"
    write(p, "\\documentclass{article}\n%\\usepackage{fontspec}\n\\begin{document}x\\end{document}")
    assert detect_engine(p) == "pdflatex"
    # fontspec chargé par un thème beamer local
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


# --- Analyse de log --------------------------------------------------------------

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


# --- Compilations réelles ------------------------------------------------------

BIB = """
    @article{knuth84,
      author = {Donald E. Knuth}, title = {Literate Programming},
      journal = {The Computer Journal}, year = {1984}, volume = {27}, pages = {97--111}}
"""


@pytest.mark.skipif(not (HAS["pdflatex"] and HAS["bibtex"]), reason="pdflatex/bibtex absents")
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
    assert "0 erreur(s), 0 avertissement(s)" in capsys.readouterr().out
    # clean supprime le répertoire de compilation et le rapport, pas le PDF
    assert main(["clean", "-d", str(tmp_path / "out")]) == 0
    assert sorted(os.listdir(tmp_path)) == ["doc.pdf", "doc.tex", "refs.bib"]


@pytest.mark.skipif(not (HAS["xelatex"] and HAS["biber"]), reason="xelatex/biber absents")
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
    monkeypatch.chdir(tmp_path / "sub")  # lancé depuis un sous-répertoire
    write(tmp_path / "ktex.toml", """
        [targets.t]
        main = "these.tex"
        build_dir = "_build"
        quiet = true
    """)
    assert main([]) == 0
    out = capsys.readouterr().out
    assert "xelatex" in out and "biber" in out
    assert "0 erreur(s), 0 avertissement(s)" in out
    assert (tmp_path / "_build/chap/one.aux").is_file()
    assert not (tmp_path / "chap/one.aux").exists()
    assert not (tmp_path / "_build/_build").exists()
    # Répertoire de compilation à jour : la passe après biber suffit
    assert main([]) == 0
    assert "(pass 3)" not in capsys.readouterr().out


@pytest.mark.skipif(not HAS["pdflatex"], reason="pdflatex absent")
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
    assert main(["-q", "-d", str(tmp_path / "out")]) == 1
    with open(tmp_path / "doc.pdf") as f:
        assert f.read() == "old"
    with open(tmp_path / "output.errors.log") as f:
        assert "part.tex:3: Undefined control sequence" in f.read()
