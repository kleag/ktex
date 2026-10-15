# Internals

## Running TeX

LaTeX is always run **from the source directory** (`root`), with:

- `-output-directory=<build_dir>` when building outside the sources;
- `-file-line-error`, so that errors are reported as `file:line:`;
- `-interaction=nonstopmode`: a build never waits for an answer at the `?`
  prompt, so it can't be killed there and leave a truncated `.aux`;
- `-recorder`, which writes the `.fls` file (list of files read and written);
- the environment variable `max_print_line=10000`, so that log lines are not
  wrapped.

## Building outside the sources

By default, the files produced by TeX are written to
`$TMPDIR/ktex-<doc>-<hash>`. The hash of the document's path tells apart two
documents with the same name. This directory is kept from one build to the
next, which reduces the number of passes needed.

TeX doesn't create the subdirectories where it writes the `.aux` files of
`\include`d chapters. ktex therefore recreates in the build directory the
subdirectories of the sources that contain `.tex` files.

Biber is run from the sources with `--output-directory`. BibTeX is run in the
build directory, with `BIBINPUTS` and `BSTINPUTS` pointing to the sources.

## Steps

1. Recreate the directory tree in the build directory.
2. Remove truncated `.aux` files.
3. First LaTeX pass.
4. Bibliography (Biber or BibTeX), if needed.
5. Further passes, fixed in number or [automatic](detection.md#passes).
6. Install the final PDF (and the `.synctex.gz`).
7. Error report, always run, even when the build failed.

## Atomic PDF

The final PDF is only replaced after the last pass succeeds, by an atomic
rename (`os.replace`). If the build directory is on another filesystem (`/tmp`
is often a `tmpfs`), the PDF is first copied to a temporary file in the
destination directory, then renamed. A viewer watching the file never sees an
empty or partial PDF, and a failed build leaves the previous PDF intact.

For the same reason, when building in place, the default job name is
`<main>-tmp`: the PDF being written is never the final PDF.

## Cleaning

`ktex clean` is deliberately cautious. It only removes files it can prove were
generated:

- the build directory, only if it contains the `.ktex` marker file and is not
  a parent of the sources;
- in the sources, the files listed as `OUTPUT` in the `.fls` files, or those
  with an auxiliary extension and the same base name as a `.tex` file or as
  the job.

It never removes a source file or the final PDF. `--dry-run` lists what would
be removed, without removing anything.

!!! note "In-place builds and `\include`"
    In place (`build_dir = "."`), the `.aux` files of `\include`d chapters
    don't depend on the job name: two targets that include the same chapters
    share them. Outside the sources, each document has its own directory.
