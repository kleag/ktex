# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

`ktex`: a generic command-line tool that runs a full LaTeX build (LaTeX passes, Biber/BibTeX, out-of-source build directory, atomic replacement of the PDF) and writes a report of errors/warnings located as `file:line`. It grew out of the build scripts of a specific document (an HDR manuscript in `../memoire-de-hdr`), but it must stay **document-agnostic**: nothing specific to one document (target names, file names, packages) belongs in the code, defaults, docs or tests. Per-document settings go in that document's `ktex.toml`.

Pure stdlib, Python ≥ 3.11 (`tomllib`). No runtime dependencies — keep it that way.

## Commands

- Install for use (editable, picked up immediately): `uv tool install --editable .`
- Tests: `uv run --with pytest --with-editable . pytest -q`
  - Integration tests compile tiny real documents and are skipped if `pdflatex`/`xelatex`/`bibtex`/`biber` are missing.
- Run without installing: `python -m ktex …` (from `src/` on the path) or `uv run ktex …`.

## Layout (`src/ktex/`)

- `cli.py` — argparse entry point (`ktex = ktex.cli:main`). Subcommands `build` (default when the first argument isn't a subcommand: `ktex`, `ktex <target>`, `ktex doc.tex`), `check`, `clean`, `corrupt-aux`, `targets`. Paths given on the command line are made absolute against the invocation directory **before** `resolve_target`; paths in `ktex.toml` are relative to the config file.
- `config.py` — `Target` dataclass (all options, defaults, derived `job`/`pdf`/`build_path`/`out_of_source`), `ktex.toml` loading (top-level keys = options shared by all `[targets.<name>]`, first target = default; searched in cwd then parents), target resolution, engine detection (magic comment `% !TEX program`, else fontspec/polyglossia/unicode-math in the preamble or a local `.sty`/`.cls`, else pdflatex) and bib backend detection (`.bcf` → biber, `\bibdata` in `.aux` → bibtex).
- `build.py` — the build itself: mirror the source subdirectory tree into the build dir, purge truncated `.aux`, pass 1, bibliography, further passes (fixed count, or auto: while aux/toc/nav/… files change or the log asks for a rerun, up to `max_passes`), atomic install of the PDF (+ synctex), and in a `finally` the error report.
- `logcheck.py` — log analysis (ported from the original `check_log.py`): rebuilds the current file from the parentheses TeX writes in the log, parses `-file-line-error` and `!` errors, warnings, bad boxes, Biber `.blg`; `enrich()` adds hints (unclosed environment, duplicate label, missing citation key and where it is cited, unknown package option, truncated `.aux`); `collapse_pending()` folds undefined refs/citations that only await another pass; `render()` groups occurrences.
- `clean.py` — removes the build dir (only if it contains the `.ktex` marker and isn't a parent of the sources) and auxiliary files left in the source tree (`OUTPUT` lines of `.fls`, or aux extensions whose stem matches a `.tex`/job). Never removes sources or the final PDF.

## Invariants — don't break these

- **cwd = source root while TeX runs and while logs are parsed.** File paths in the log are relative to where TeX was launched; `logcheck` resolves them with `os.path.isfile` against cwd. Call `logcheck.set_root(root, build_dir)` after `chdir` (it also clears caches); `PROJECT`/`BUILD_DIR` are module globals read at call time.
- `max_print_line=10000` in the subprocess environment, plus `-file-line-error -interaction=nonstopmode -recorder`: the parser relies on unwrapped log lines; nonstopmode prevents runs killed at the `?` prompt from leaving truncated `.aux`.
- Out of source: `-output-directory=<build_dir>`; TeX doesn't create subdirectories for `\include`d `.aux` files, hence `mirror_tree`. Biber runs from the source root with `--output-directory`; BibTeX runs in the build dir with `BIBINPUTS`/`BSTINPUTS` pointing to the sources.
- Job name: `<main>` out of source, `<main>-tmp` in place (so the final PDF is never the file being written); no dots in job names (biber treats the suffix as an extension).
- The final PDF is only replaced after the last pass succeeds, atomically (`os.replace`, or copy to a temp file in the destination dir then `os.replace` across filesystems — `/tmp` is often tmpfs).
- The report always runs (even on failure) and must never mask the build's exit status.
- `clean` must stay conservative: anything it deletes must be provably generated.

## Conventions

- Code comments, docstrings, the report and error messages are in **French**; the build progress messages (`--- Running xelatex (pass 2) ---`, success/failure banners) are in English, as in the original scripts. Match the surrounding file.
- Report output format (`output.errors.log`) is relied upon by users and agents: changes to `render()` should be deliberate. When touching `logcheck.py`, check that the report on an existing real log is unchanged except for the intended difference (diff before/after).
- Add a test (fixture log or tiny document under `tmp_path`) for each new behaviour; keep integration tests fast and skippable.
- Real-world check after changes to the build: compile a real document out of its tree, e.g. `ktex /path/doc.tex -q -o $SCRATCH/doc.pdf --log-prefix $SCRATCH/doc -d $SCRATCH/build`, without writing into someone else's sources.
