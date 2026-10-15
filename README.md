# ktex

[![PyPI](https://img.shields.io/pypi/v/ktex)](https://pypi.org/project/ktex/)
[![Python](https://img.shields.io/pypi/pyversions/ktex)](https://pypi.org/project/ktex/)
[![CI](https://github.com/kleag/ktex/actions/workflows/ci.yml/badge.svg)](https://github.com/kleag/ktex/actions/workflows/ci.yml)
[![Documentation](https://img.shields.io/badge/docs-kleag.github.io%2Fktex-blue)](https://kleag.github.io/ktex/)

*Kleag's TeX tool.* — [Français](https://github.com/kleag/ktex/blob/main/README.fr.md)

A complete LaTeX build, in one command, for any document:

- LaTeX passes (`pdflatex`, `xelatex` or `lualatex`) and bibliography (Biber
  or BibTeX), detected automatically or set in the configuration;
- build **outside the sources**, in a temporary directory specific to the
  document (`$TMPDIR/ktex-<doc>-<hash>`): no `.aux`, `.log`, `.bbl`… in your
  tree, including those of `\include`d chapters;
- **atomic replacement** of the final PDF: the viewer never sees an empty or
  partial PDF, and a failed build leaves the previous PDF in place;
- prior removal of `.aux` files **truncated** by an interrupted run (the cause
  of "File ended while scanning use of…" right at `\begin{document}`);
- at the end (success or failure), a **report of errors and warnings located
  as `file:line`** — including in `\input`/`\include`d files — with grouped
  occurrences and hints: unclosed environment, duplicate `\label`, citation key
  missing (and where it is cited), unknown package option, undefined citations
  merely waiting for Biber…

Python ≥ 3.11. Messages in English, or in French when the locale is French (or
with `KTEX_LANG=fr`).

## Installation

```sh
uv tool install ktex     # or: pipx install ktex
uvx ktex                 # without installing
```

Full documentation: <https://kleag.github.io/ktex/>.

## Usage

```sh
ktex                     # build the default target (or the only main .tex file of the directory)
ktex thesis.tex          # build a given file
ktex slides              # build the "slides" target of ktex.toml
ktex build -e lualatex -b bibtex -n 2 thesis.tex   # explicit options
ktex -v                  # also show the raw output of LaTeX/Biber (always in the logs)
ktex -d .                # build in place, the old way
ktex check               # re-analyze the log of the last build
ktex clean [--dry-run]   # remove auxiliary files
ktex corrupt-aux         # list truncated .aux files
ktex targets             # list the configured targets
ktex init                # create a ktex.toml for the project of the current directory
```

Files produced (prefix `output` by default, option `log_prefix`): in the build
directory, `output.1.log`, `output.2.log`… (output of each pass) and
`output.bib.log`; next to the sources, the PDF and `output.errors.log`, the
full report. When there are errors, the terminal only shows the errors
(warnings and undefined references often follow from them), and it only
details bad boxes with `--boxes`.

## Automatic detection

- **Engine**: magic comment `% !TEX program = xelatex` in the main file;
  otherwise `xelatex` if the preamble loads `fontspec`, `polyglossia` or
  `unicode-math`; otherwise `pdflatex`.
- **Bibliography** (after the first pass): `biber` if biblatex wrote a `.bcf`,
  `bibtex` if the `.aux` contains `\bibdata`, otherwise none.
- **Passes**: after the bibliography, one pass (two for BibTeX), then as long
  as the log asks for another pass (`Rerun to get…`, `Label(s) may have
  changed`, `Please rerun LaTeX`…), up to `max_passes` (5).

## Configuration: `ktex.toml`

Looked for in the current directory, then in its parents; paths are relative
to the configuration file.

```toml
# Options shared by all targets
engine = "xelatex"        # pdflatex | xelatex | lualatex | auto
bib = "biber"             # biber | bibtex | none | auto
passes = 3                # fixed number of LaTeX passes, or "auto"

[targets.thesis]          # the first target is the default one
main = "thesis.tex"

[targets.slides]
main = "slides.tex"
bib = "none"
log_prefix = "output_slides"
```

Target options: `main` (required), `root`, `engine`, `bib`, `passes`,
`max_passes`, `build_dir` (`"auto"` by default: temporary directory; `"."`: in
place; or a path), `jobname` (default `<main>`, `<main>-tmp` in place),
`output` (default `<main>.pdf`), `log_prefix`, `verbose`, `engine_args` (list of
extra engine options, for example `["-synctex=1", "-shell-escape"]`),
`show_boxes`.

## Notes

- LaTeX is run from the source directory with `-output-directory=<build_dir>`,
  `max_print_line=10000` (unwrapped log lines), `-file-line-error`,
  `-interaction=nonstopmode` and `-recorder`. Subdirectories of the sources
  that contain `.tex` files are recreated in the build directory (TeX doesn't
  create them for the `.aux` files of `\include`s). Biber is run with
  `--output-directory`, BibTeX in the build directory with
  `BIBINPUTS`/`BSTINPUTS` pointing to the sources.
- The build directory is kept from one build to the next (fewer passes);
  `ktex clean` removes it, only if it contains the `.ktex` marker file. It also
  removes the auxiliary files left in the sources (listed as `OUTPUT` in the
  `.fls` files, or with an auxiliary extension and the same base name as a
  `.tex` file), never touching the sources or the final PDF.
- In place (`build_dir = "."`), with `\include`, the `.aux` files of the
  chapters don't depend on the job name: two targets that include the same
  chapters share them. Outside the sources, each document has its own
  directory.

## License

MIT
