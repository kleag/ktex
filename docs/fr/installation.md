# Installation

ktex est publié sur [PyPI](https://pypi.org/project/ktex/). Comme c'est un
outil en ligne de commande, il vaut mieux l'installer dans un environnement
isolé, avec [uv](https://docs.astral.sh/uv/) ou [pipx](https://pipx.pypa.io/) :

```sh
uv tool install ktex
# ou
pipx install ktex
```

Pour l'essayer sans l'installer :

```sh
uvx ktex --help
```

Mise à jour : `uv tool upgrade ktex` ou `pipx upgrade ktex`.

## Prérequis

- Python ≥ 3.11 ;
- une distribution TeX qui fournit, selon les documents, `pdflatex`, `xelatex`
  ou `lualatex`, et `biber` ou `bibtex`. Les outils doivent être dans le `PATH`.

ktex est développé et testé sous Linux. Il devrait fonctionner sous macOS et
sur les autres systèmes POSIX.

## Version de développement

```sh
git clone https://github.com/kleag/ktex.git
uv tool install --editable ./ktex
```

Avec `--editable`, les modifications des sources sont prises en compte tout de
suite, sans réinstaller.
