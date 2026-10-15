# Contributing

The code is on [GitHub](https://github.com/kleag/ktex). Bug reports are
welcome. If you can, attach the TeX log involved (the `.log` file of the build
directory).

## Development environment

The project uses [uv](https://docs.astral.sh/uv/).

```sh
git clone https://github.com/kleag/ktex.git
cd ktex
uv sync                        # environment (tests, docs, bumpver)
uv run pytest -q               # tests
uv run ktex --help             # run ktex from the sources
```

The integration tests compile small real documents. They are skipped if
`pdflatex`, `xelatex`, `bibtex` or `biber` is missing. In CI, the variable
`KTEX_REQUIRE_TEX=1` makes them fail instead of being skipped.

## Documentation

The documentation is written in Markdown, in English in `docs/en/` and in
French in `docs/fr/` (same file names), and built with
[Zensical](https://zensical.org/):

```sh
uv run zensical serve                              # preview of the English site
uv run zensical serve -f zensical.fr.toml          # preview of the French site
uv run zensical build --strict --clean && uv run zensical build --strict -f zensical.fr.toml
```

The second build writes the French site to `site/fr/`. The documentation is
published to GitHub Pages on every push to `main`.

## Translations

Messages are written in English in the code and wrapped in `_()` (see
`src/ktex/i18n.py`). Their translations live in `src/ktex/translations/<lang>.py`,
a dict from the English message to its translation. When you add or change a
message, update `translations/fr.py` as well: a test checks that every message
has a translation with the same placeholders.

To add a language: create `translations/<lang>.py`, add the code to
`LANGUAGES` in `i18n.py`, and translate the documentation into `docs/<lang>/`
with its own `zensical.<lang>.toml`.

## Principles

- Keep dependencies minimal and well-maintained (currently none at runtime).
- The tool stays generic: nothing specific to one document in the code, the
  defaults, the documentation or the tests. Per-document settings go in that
  document's `ktex.toml`.
- Every new behaviour comes with a test (sample log or small document).
- The format of the report (`output.errors.log`) is used by people and by
  tools: only change it deliberately.

## Releasing

Version numbers are managed with [bumpver](https://github.com/mbarkhau/bumpver).
The version is written in `pyproject.toml` (`[tool.bumpver]`) and in
`src/ktex/__init__.py`, from which the package reads its own.

1. Move the "Unreleased" entries of `CHANGELOG.md` under the new version, and
   commit.
2. Bump the version: bumpver updates both files, commits and creates the
   `vX.Y.Z` tag.
   ```sh
   uv run bumpver update --patch     # or --minor, --major; --dry to preview
   ```
3. Push the commit and the tag:
   ```sh
   git push --follow-tags
   ```
4. The `release.yml` workflow runs the tests, checks that the tag matches
   `__version__`, builds the packages with `uv build`, publishes them to PyPI
   (Trusted Publishing) and creates the GitHub release.
