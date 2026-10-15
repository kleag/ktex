# Installation

ktex is published on [PyPI](https://pypi.org/project/ktex/). It is a
command-line tool, so it is best installed in its own isolated environment
with [uv](https://docs.astral.sh/uv/) or [pipx](https://pipx.pypa.io/):

```sh
uv tool install ktex
# or
pipx install ktex
```

To try it without installing it:

```sh
uvx ktex --help
```

To upgrade: `uv tool upgrade ktex` or `pipx upgrade ktex`.

## Requirements

- Python ≥ 3.11;
- a TeX distribution that provides, depending on your documents, `pdflatex`,
  `xelatex` or `lualatex`, and `biber` or `bibtex`, on the `PATH`.

ktex is developed and tested on Linux. It should work on macOS and other
POSIX systems.

## Development version

```sh
git clone https://github.com/kleag/ktex.git
uv tool install --editable ./ktex
```

With `--editable`, changes to the sources take effect immediately, with no
reinstall.
