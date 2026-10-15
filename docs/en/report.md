# The error report

At the end of every build, successful or not, ktex analyzes the TeX log (and
Biber's `.blg`) and writes `output.errors.log` next to the sources.
`ktex check` regenerates it from the existing logs.

## Format

```text
===== ERRORS (1) =====
chapters/intro.tex:5: LaTeX Error: \begin{itemize} on input line 3 ended by \end{enumerate}.
    → \end{enumerate} ⟨here⟩
    ↳ \begin{itemize} probably opened at: chapters/intro.tex:3

===== WARNINGS (7, 6 distinct) =====
Undefined citations: Biber has not been rerun yet (expected if the build stopped before) (×2)
    chapters/intro.tex:2 ; thesis.tex:7
thesis.tex:7: Undefined references: another LaTeX pass is needed (expected if the build stopped before)
thesis.tex:8: LaTeX Warning: Empty bibliography on input line 8.
thesis.tex: LaTeX Warning: There were undefined references.
thesis.tex: LaTeX Warning: Label(s) may have changed. Rerun to get cross-references right.
thesis.tex: Package biblatex Warning: Please (re)run Biber on the file: thesis and rerun LaTeX afterwards.

===== OVERFULL / UNDERFULL BOXES (1) =====
chapters/intro.tex:6: Overfull \hbox (110.37259pt too wide) detected at line 6

Summary: 1 error(s), 7 warning(s), 1 bad box(es)
```

Each entry starts with `file:line:`. Most editors (Emacs, Vim, VS Code…)
recognize this format and can jump straight to the location. Indented lines
give context:

- `→`: the exact place in the line where TeX stopped;
- `↳`: a hint added by ktex.

Several occurrences of the same message are grouped, with their locations
gathered by file.

The report is written in the [language](usage.md#language) of the messages;
the messages quoted from TeX, LaTeX packages and Biber are kept as is.

## Locating the right file

TeX doesn't always say which file it is reading. ktex rebuilds the current
file from the parentheses TeX writes to the log whenever it opens or closes a
file. Errors and warnings are thus attributed to the `\input` or `\include`d
file where they happen, not to the main file.

## Hints

ktex adds to TeX's raw messages when it can:

- **unclosed environment**: where the mismatched environment was probably
  opened;
- **duplicate `\label`**: the locations of both definitions;
- **citation key missing** from the bibliography, and where it is cited;
- **unknown package option**;
- **`.aux` file truncated** by an interrupted run.

Undefined references and citations that only await another pass, for example
because the build stopped before Biber ran, are folded into a single line, so
they don't drown out the real errors.

## Terminal

When there are errors, ktex only shows the errors in the terminal, because
warnings and undefined references often follow from them. It only details bad
boxes with `--boxes`. The final summary always gives the number of errors,
warnings and bad boxes.
