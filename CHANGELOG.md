# Changelog

Notable changes to ktex are listed here. The project follows
[semantic versioning](https://semver.org/).

## [Unreleased]

## [0.2.0] - 2026-10-15

- Watch mode: `ktex -w` (`--watch`) rebuilds the document whenever one of the
  source files it reads changes (found in the `.fls` file, plus the
  bibliography databases). Inspired by
  [texbuild](https://github.com/SamDM/texbuild) and latexmk's `-pvc`.
- `ktex init`: create a `ktex.toml` for the LaTeX project of the current
  directory, with one target per main file.
- The raw output of LaTeX and Biber is hidden by default (it is still in the
  logs); `-v`/`--verbose` or `verbose = true` shows it. The `quiet` option is
  replaced by `verbose`. On failure, the path of the raw log is printed.

## [0.1.0] - 2026-10-15

First public release.

- Full build: LaTeX passes (`pdflatex`, `xelatex`, `lualatex`), Biber or
  BibTeX, automatic number of passes.
- Out-of-source build and atomic replacement of the PDF.
- Report of errors located as `file:line`, with hints.
- Subcommands `build`, `check`, `clean`, `corrupt-aux`, `targets`, and
  configuration through `ktex.toml`.
- Messages, help and report in English, or in French depending on the locale
  (`KTEX_LANG` to override).

[Unreleased]: https://github.com/kleag/ktex/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/kleag/ktex/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/kleag/ktex/releases/tag/v0.1.0
