# Automatic detection

Options set to `auto` (the default) are worked out from the document.

## Engine

1. The magic comment `% !TEX program = <engine>` in the main file, if there
   is one.
2. Otherwise `xelatex`, if the preamble loads `fontspec`, `polyglossia` or
   `unicode-math`, or if a `.sty`/`.cls` file in the directory of the main
   file loads them (beamer theme, custom class…).
3. Otherwise `pdflatex`.

Commented-out lines are ignored.

## Bibliography

ktex looks at the files produced by the first pass:

- `biber` if biblatex wrote a `.bcf` file;
- `bibtex` if the `.aux` contains `\bibdata`;
- otherwise, no bibliography.

## Passes

In `auto` mode, ktex runs a first pass, then the bibliography, then:

- one pass (two for BibTeX);
- then more passes as long as the auxiliary files (`.aux`, `.toc`, `.nav`…)
  change or the log asks for another pass (`Rerun to get…`,
  `Label(s) may have changed`, `Please rerun LaTeX`…), up to `max_passes`.

The build directory is kept between builds, so rebuilding after a small change
often takes only one or two passes.
