# Configuration: `ktex.toml`

Without a configuration file, ktex builds the only document of the current
directory with the detected settings. A `ktex.toml` file lets you name
**targets** and set their options. `ktex init` writes a starter one, with a
target for each main file of the project.

ktex looks for `ktex.toml` in the current directory, then in its parents, so
you can run `ktex` from a subdirectory of the document. Paths in the file are
relative to the file itself.

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

Top-level keys apply to every target. Each `[targets.<name>]` section can
override them.

## Options

| Option | Default | Description |
|---|---|---|
| `main` | *(required)* | main `.tex` file, relative to `root` |
| `root` | `"."` | source directory, where LaTeX is run |
| `engine` | `"auto"` | `pdflatex`, `xelatex`, `lualatex` or `auto` ([detection](detection.md#engine)) |
| `bib` | `"auto"` | `biber`, `bibtex`, `none` or `auto` ([detection](detection.md#bibliography)) |
| `passes` | `"auto"` | fixed number of LaTeX passes, or `"auto"` ([detection](detection.md#passes)) |
| `max_passes` | `5` | maximum number of passes in `auto` mode |
| `build_dir` | `"auto"` | `"auto"`: temporary directory `$TMPDIR/ktex-<doc>-<hash>`; `"."`: in place; or a path |
| `jobname` | `<main>` | TeX job name (`<main>-tmp` in place, so that the final PDF is never the file being written) |
| `output` | `<main>.pdf` | final PDF |
| `log_prefix` | `"output"` | prefix of the logs and of the report (`<prefix>.errors.log`) |
| `verbose` | `false` | show the raw output of the tools in the terminal (it is always in the logs) |
| `engine_args` | `[]` | extra engine options, for example `["-synctex=1", "-shell-escape"]` |
| `show_boxes` | `false` | detail bad boxes in the terminal summary |

!!! note "Job names"
    A job name must not contain a dot: Biber would take the end of the name
    for an extension.

!!! tip "SyncTeX"
    With `engine_args = ["-synctex=1"]`, the `.synctex.gz` file is installed
    next to the final PDF, at the same time as the PDF.
