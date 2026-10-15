# ktex

*Kleag's TeX tool*: a complete LaTeX build, in one command, for any
document, followed by a report of errors and warnings located as
`file:line`.

```sh
ktex
```

This command:

- runs the LaTeX passes (`pdflatex`, `xelatex` or `lualatex`) and the
  bibliography (Biber or BibTeX), either [detected automatically](detection.md)
  or [set in the configuration](configuration.md);
- builds **outside the sources**, in a temporary directory specific to the
  document: no `.aux`, `.log`, `.bbl`… in your tree, including those of
  `\include`d chapters;
- **replaces the final PDF atomically**: the viewer never sees an empty or
  partial PDF, and a failed build leaves the previous PDF in place;
- first removes `.aux` files **truncated** by an interrupted run (the cause of
  "File ended while scanning use of…" right at `\begin{document}`);
- at the end, whether the build succeeded or failed, writes a
  [**report**](report.md) that locates each problem in the right file,
  including `\input`/`\include`d files, with hints.

```text
===== ERRORS (1) =====
chapters/intro.tex:5: LaTeX Error: \begin{itemize} on input line 3 ended by \end{enumerate}.
    → \end{enumerate} ⟨here⟩
    ↳ \begin{itemize} probably opened at: chapters/intro.tex:3
```

With `ktex -w`, ktex [keeps the PDF up to date](usage.md#watch-mode): it
rebuilds the document whenever one of its source files changes. This watch
mode was inspired by [texbuild](https://github.com/SamDM/texbuild), and the
way it finds the files to watch (the `.fls` file written by TeX) by
[latexmk](https://ctan.org/pkg/latexmk).

ktex only needs Python ≥ 3.11 and a TeX distribution (TeX Live, MiKTeX…) that
provides the engines and tools you use. Its messages are in English, or in
French when your locale is French (see [Usage](usage.md#language)).

[Install ktex](installation.md){ .md-button .md-button--primary }
[Getting started](usage.md){ .md-button }
