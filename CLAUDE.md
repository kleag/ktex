# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

`ktex`: a generic command-line tool that runs a full LaTeX build (LaTeX passes, Biber/BibTeX, out-of-source build directory, atomic replacement of the PDF) and writes a report of errors/warnings located as `file:line`. It grew out of the build scripts of a specific document (an HDR manuscript in `../memoire-de-hdr`), but it must stay **document-agnostic**: nothing specific to one document (target names, file names, packages) belongs in the code, defaults, docs or tests. Per-document settings go in that document's `ktex.toml`.

Python ≥ 3.11 (`tomllib`). Currently no runtime dependencies; reasonable, well-maintained dependencies are acceptable when they clearly earn their place (declare them in `pyproject.toml`, keep `uv.lock` in sync). Use uv for everything (envs, running, building).

## Commands

- Install for use (editable, picked up immediately): `uv tool install --editable .`
- Dev environment: `uv sync` (default group `dev` = test + docs + bumpver). Keep `uv.lock` up to date (`uv lock`): CI runs with `--locked`.
- Tests: `uv run pytest -q`
  - Integration tests compile tiny real documents and are skipped if `pdflatex`/`xelatex`/`bibtex`/`biber` are missing; with `KTEX_REQUIRE_TEX=1` (set in CI's TeX Live job) a missing tool is an error instead.
- Run without installing: `uv run ktex …` or `python -m ktex …` (from `src/` on the path).
- Docs (Zensical, deployed to https://kleag.github.io/ktex/ on push to main): English in `docs/en/` (`zensical.toml`, site root), French translation in `docs/fr/` (`zensical.fr.toml`, built into `site/fr/`, so build the English site first). Same file names in both languages. Build: `uv run zensical build --strict --clean && uv run zensical build --strict -f zensical.fr.toml`; preview: `uv run zensical serve [-f zensical.fr.toml]`. Update **both** languages along with user-visible behaviour (options, `ktex.toml` keys, report format). `README.md` (English, shown on PyPI) has a French counterpart `README.fr.md`.
- Packaging: `uv build`; the version is read by hatch from `src/ktex/__init__.py`.
- Release: never edit version numbers by hand — `uv run bumpver update --patch|--minor|--major` (updates `pyproject.toml` `[tool.bumpver]` and `__init__.py`, commits, tags `vX.Y.Z`), update `CHANGELOG.md` first, then `git push --follow-tags`. A pushed `v*` tag publishes to PyPI (`.github/workflows/release.yml`, Trusted Publishing, environment `pypi`): don't tag or push tags unless asked.

## Layout (`src/ktex/`)

- `cli.py` — argparse entry point (`ktex = ktex.cli:main`). Subcommands `build` (default when the first argument isn't a subcommand: `ktex`, `ktex <target>`, `ktex doc.tex`), `check`, `clean`, `corrupt-aux`, `targets`, `init`. Paths given on the command line are made absolute against the invocation directory **before** `resolve_target`; paths in `ktex.toml` are relative to the config file.
- `config.py` — `Target` dataclass (all options, defaults, derived `job`/`pdf`/`build_path`/`out_of_source`), `ktex.toml` loading (top-level keys = options shared by all `[targets.<name>]`, first target = default; searched in cwd then parents), target resolution, engine detection (magic comment `% !TEX program`, else fontspec/polyglossia/unicode-math in the preamble or a local `.sty`/`.cls`, else pdflatex) and bib backend detection (`.bcf` → biber, `\bibdata` in `.aux` → bibtex).
- `build.py` — the build itself: mirror the source subdirectory tree into the build dir, purge truncated `.aux`, pass 1, bibliography, further passes (fixed count, or auto: while aux/toc/nav/… files change or the log asks for a rerun, up to `max_passes`), atomic install of the PDF (+ synctex), and in a `finally` the error report.
- `logcheck.py` — log analysis (ported from the original `check_log.py`): rebuilds the current file from the parentheses TeX writes in the log, parses `-file-line-error` and `!` errors, warnings, bad boxes, Biber `.blg`; `enrich()` adds hints (unclosed environment, duplicate label, missing citation key and where it is cited, unknown package option, truncated `.aux`); `collapse_pending()` folds undefined refs/citations that only await another pass; `render()` groups occurrences.
- `i18n.py` — `_()`: looks an English message up in the catalog of the current language and fills its `str.format` placeholders; language from `KTEX_LANG`, else `LANGUAGE`/`LC_ALL`/`LC_MESSAGES`/`LANG`; `set_language()` to force it (tests force `en` with an autouse fixture). Catalogs: `translations/<lang>.py`, `MESSAGES = {english: translation}`.
- `init.py` — `ktex init`: finds the project (closest dir from cwd up with main `.tex` files, excluding `standalone`/`subfiles` classes, never crossing a `.git` boundary), refuses if `find_config()` already finds a `ktex.toml`, writes one target per main file (first = default; others get `log_prefix = "output_<name>"` so reports don't overwrite each other) with commented shared options; the generated comments go through `_()`. The file is opened with mode `"x"`: never overwrite.
- `watch.py` — `-w`/`--watch`: `dependencies()` = `INPUT` lines of `<job>.fls` (resolved against its `PWD`) inside the source root, plus `.bib`/`.bst` from the `.bcf`/`.aux` (Biber/BibTeX read them outside TeX), minus anything the build writes (`OUTPUT` lines, `<job>.*`, build dir, final PDF/synctex, report); polled with `stat()`, snapshot taken *before* each build so edits made during it trigger a rebuild. The loop takes injectable `build_fn`/`sleep`/`max_builds` for tests.
- `clean.py` — removes the build dir (only if it contains the `.ktex` marker and isn't a parent of the sources) and auxiliary files left in the source tree (`OUTPUT` lines of `.fls`, or aux extensions whose stem matches a `.tex`/job). Never removes sources or the final PDF.

## Invariants — don't break these

- **cwd = source root while TeX runs and while logs are parsed.** File paths in the log are relative to where TeX was launched; `logcheck` resolves them with `os.path.isfile` against cwd. Call `logcheck.set_root(root, build_dir)` after `chdir` (it also clears caches); `PROJECT`/`BUILD_DIR` are module globals read at call time.
- `max_print_line=10000` in the subprocess environment, plus `-file-line-error -interaction=nonstopmode -recorder`: the parser relies on unwrapped log lines; nonstopmode prevents runs killed at the `?` prompt from leaving truncated `.aux`.
- Out of source: `-output-directory=<build_dir>`; TeX doesn't create subdirectories for `\include`d `.aux` files, hence `mirror_tree`. Biber runs from the source root with `--output-directory`; BibTeX runs in the build dir with `BIBINPUTS`/`BSTINPUTS` pointing to the sources.
- Must work with TeX Live's default write policy `openout_any = p` (paranoid: kpathsea refuses to write absolute paths and `..` paths; only `-output-directory` is exempt). Never require users to relax it, and never relax it ourselves. Give TeX tools relative output names from the right cwd (that's why BibTeX runs *in* the build dir with `bibtex <job>`). The tests force `openout_any=p` (autouse fixture), because a developer's shell may export `r`.
- Job name: `<main>` out of source, `<main>-tmp` in place (so the final PDF is never the file being written); no dots in job names (biber treats the suffix as an extension).
- The final PDF is only replaced after the last pass succeeds, atomically (`os.replace`, or copy to a temp file in the destination dir then `os.replace` across filesystems — `/tmp` is often tmpfs).
- The report always runs (even on failure) and must never mask the build's exit status.
- `clean` must stay conservative: anything it deletes must be provably generated.

## Conventions

- Everything is in **English** (code, comments, docstrings, messages, tests, docs, commit messages) for an international audience; French exists only as translations (`translations/fr.py`, `docs/fr/`, `README.fr.md`).
- Every user-facing string (CLI help, errors, progress messages, report text) goes through `_()`, written in English with named `{placeholders}` (`_("{path} not found", path=p)`), never pre-formatted f-strings; double literal braces (`\\begin{{{env}}}`). Add the French translation to `translations/fr.py` in the same change — `test_french_catalog_is_complete` fails on any missing/extra message or placeholder mismatch. Never bind `_` as a throwaway variable in modules that import it. Messages quoted from TeX/packages/Biber are never translated.
- Report output format (`output.errors.log`) is relied upon by users and agents: changes to `render()` or to report messages should be deliberate. When touching `logcheck.py`, check that the report on an existing real log is unchanged except for the intended difference (diff before/after, in both languages: `KTEX_LANG=en` and `KTEX_LANG=fr`).
- Add a test (fixture log or tiny document under `tmp_path`) for each new behaviour; keep integration tests fast and skippable.
- Real-world check after changes to the build: compile a real document out of its tree, e.g. `ktex /path/doc.tex -o $SCRATCH/doc.pdf --log-prefix $SCRATCH/doc -d $SCRATCH/build`, without writing into someone else's sources.
