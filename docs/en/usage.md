# Usage

## Building

```sh
ktex                     # default target of ktex.toml, else the only main .tex file of the directory
ktex thesis.tex          # a given file
ktex slides              # the "slides" target of ktex.toml
```

`build` is the default subcommand: `ktex thesis.tex` is the same as
`ktex build thesis.tex`. Without a configuration file, ktex picks the only
`.tex` file of the current directory that contains `\documentclass`.

Options of `ktex build`:

| Option | Effect |
|---|---|
| `-e`, `--engine` | `pdflatex`, `xelatex`, `lualatex` or `auto` |
| `-b`, `--bib` | `biber`, `bibtex`, `none` or `auto` |
| `-n`, `--passes` | fixed number of LaTeX passes, or `auto` |
| `--max-passes` | maximum number of passes in `auto` mode (default 5) |
| `-d`, `--build-dir` | build directory (default: temporary; `.`: in place) |
| `-j`, `--jobname` | job name (default: `<main>`, or `<main>-tmp` in place) |
| `-o`, `--output` | final PDF (default: `<main>.pdf`) |
| `--log-prefix` | prefix of the logs (default: `output`) |
| `-v`, `--verbose` | show the raw output of LaTeX/Biber (hidden by default; it is always in the logs) |
| `-q`, `--quiet` | hide the raw output (the default; overrides `verbose = true`) |
| `--boxes` | also detail bad boxes in the terminal |
| `--color`, `--no-color` | force or disable colors (default: if the output is a terminal and `NO_COLOR` is not set) |

Command-line options take precedence over `ktex.toml`. Paths given on the
command line are relative to the current directory.

```sh
ktex build -e lualatex -b bibtex -n 2 thesis.tex
ktex -d .                # build in place, the old way
ktex -o ~/thesis.pdf     # write the PDF elsewhere
ktex -v                  # also show the raw output of LaTeX and Biber
```

## Other commands

`ktex init`
:   Create a [`ktex.toml`](configuration.md) for the LaTeX project of the
    current directory: the closest directory, from the current one up (without
    leaving the git repository), that contains main `.tex` files. It defines
    one target per main file, the first one being the default target;
    `standalone` and `subfiles` documents are left out. It does nothing if a
    `ktex.toml` already applies to the current directory.

`ktex check [target]`
:   Re-analyze the log of the last build and rewrite the report, without
    building anything. With `-o FILE`, the report goes to another file.

`ktex clean [target] [--dry-run] [--keep-logs]`
:   Remove the build directory and the auxiliary files left in the sources.
    It never touches the sources or the final PDF
    (see [Internals](internals.md#cleaning)).

`ktex corrupt-aux [target]`
:   List the `.aux` files truncated by an interrupted run.

`ktex targets`
:   List the targets of `ktex.toml`. The first one is the default target.

## Files produced

With the default prefix `output`:

- in the build directory: `output.1.log`, `output.2.log`… (the raw output of
  each pass, which the terminal only shows with `-v`) and `output.bib.log`;
- next to the sources: the PDF and `output.errors.log`, the full
  [report](report.md).

When there are errors, the terminal only shows the errors, because warnings
and undefined references often follow from them. It only details bad boxes
with `--boxes`. The full report always contains everything.

## Exit status

`ktex build` returns 0 if the build succeeded. Otherwise it returns a non-zero
status and the previous PDF is kept. A configuration error (unknown target,
invalid `ktex.toml`…) returns 2.

## Language

Messages, help and the report are in English, or in French when the locale is
French (`LANGUAGE`, `LC_ALL`, `LC_MESSAGES` or `LANG`, in that order, as with
gettext). The `KTEX_LANG` environment variable takes precedence:

```sh
KTEX_LANG=en ktex        # English, whatever the locale
KTEX_LANG=fr ktex        # French
```

Messages quoted from TeX, LaTeX packages and Biber are left as they are.
