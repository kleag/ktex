# ktex

*Kleag's TeX tool.*

Compilation LaTeX complète, en une commande, pour n'importe quel document :

- passes LaTeX (`pdflatex`, `xelatex` ou `lualatex`) et bibliographie (Biber ou BibTeX),
  détectés automatiquement ou fixés par configuration ;
- compilation **hors des sources**, dans un répertoire temporaire propre au
  document (`$TMPDIR/ktex-<doc>-<hash>`) : aucun `.aux`, `.log`, `.bbl`…
  dans l'arborescence, y compris ceux des chapitres `\include`s ;
- **remplacement atomique** du PDF final : la visionneuse ne voit jamais de PDF
  vide ou partiel, et un échec laisse l'ancien PDF en place ;
- suppression préalable des `.aux` **tronqués** par une compilation interrompue
  (cause de l'erreur « File ended while scanning use of… » dès `\begin{document}`) ;
- à la fin (succès ou échec), **rapport d'erreurs et d'avertissements localisés
  par `fichier:ligne`** — y compris dans les fichiers `\input`/`\include` — avec
  regroupement des occurrences et indices : environnement non fermé, `\label`
  dupliqué, clé de citation absente (et où elle est citée), option de paquet
  inconnue, citations indéfinies simplement en attente de Biber…

Aucune dépendance hors bibliothèque standard (Python ≥ 3.11).

## Installation

```sh
uv tool install --editable /chemin/vers/ktex   # ou : pipx install /chemin/vers/ktex
```

## Utilisation

```sh
ktex                     # compile la cible par défaut (ou l'unique .tex principal du répertoire)
ktex these.tex           # compile un fichier donné
ktex soutenance          # compile la cible « soutenance » du ktex.toml
ktex build -e lualatex -b bibtex -n 2 these.tex   # options explicites
ktex -q                  # sans la sortie de LaTeX/Biber (toujours dans les logs)
ktex -d .                # compilation sur place, à l'ancienne
ktex check               # ré-analyse le log de la dernière compilation
ktex clean [--dry-run]   # supprime les fichiers auxiliaires
ktex corrupt-aux         # liste les .aux tronqués
ktex targets             # liste les cibles configurées
```

Fichiers produits (préfixe `output` par défaut, option `log_prefix`) : dans le
répertoire de compilation, `output.1.log`, `output.2.log`… (sortie de chaque
passe) et `output.bib.log` ; à côté des sources, le PDF et `output.errors.log`,
le rapport complet. Le terminal n'affiche que les erreurs
s'il y en a (avertissements et références indéfinies en découlent souvent),
et ne détaille pas les boîtes mal remplies sauf avec `--boxes`.

## Détection automatique

- **Moteur** : commentaire magique `% !TEX program = xelatex` dans le fichier
  principal ; sinon `xelatex` si le préambule charge `fontspec`, `polyglossia`
  ou `unicode-math` ; sinon `pdflatex`.
- **Bibliographie** (après la première passe) : `biber` si biblatex a écrit un
  `.bcf`, `bibtex` si le `.aux` contient `\bibdata`, sinon aucune.
- **Passes** : après la bibliographie, une passe (deux pour BibTeX), puis tant
  que le log réclame une nouvelle passe (`Rerun to get…`, `Label(s) may have
  changed`, `Please rerun LaTeX`…), dans la limite de `max_passes` (5).

## Configuration : `ktex.toml`

Cherché dans le répertoire courant puis ses parents ; les chemins sont
relatifs au fichier de configuration.

```toml
# Options communes à toutes les cibles
engine = "xelatex"        # pdflatex | xelatex | lualatex | auto
bib = "biber"             # biber | bibtex | none | auto
passes = 3                # nombre fixe de passes LaTeX, ou "auto"

[targets.these]           # la première cible est la cible par défaut
main = "these.tex"

[targets.soutenance]
main = "soutenance.tex"
bib = "none"
log_prefix = "output_soutenance"
```

Options d'une cible : `main` (obligatoire), `root`, `engine`, `bib`, `passes`,
`max_passes`, `build_dir` (`"auto"` par défaut : répertoire temporaire ;
`"."` : sur place ; ou un chemin), `jobname` (défaut `<main>`, `<main>-tmp`
sur place), `output` (défaut `<main>.pdf`), `log_prefix`, `quiet`,
`engine_args` (liste d'options supplémentaires du moteur, par exemple
`["-synctex=1", "-shell-escape"]`), `show_boxes`.

## Notes

- LaTeX est lancé depuis le répertoire des sources avec
  `-output-directory=<build_dir>`, `max_print_line=10000` (lignes du log non
  coupées), `-file-line-error`, `-interaction=nonstopmode` et `-recorder`.
  Les sous-répertoires des sources contenant des `.tex` sont recréés dans le
  répertoire de compilation (TeX ne les crée pas pour les `.aux` des
  `\include`). Biber est lancé avec `--output-directory`, BibTeX dans le
  répertoire de compilation avec `BIBINPUTS`/`BSTINPUTS` pointant sur les sources.
- Le répertoire de compilation est conservé d'une fois sur l'autre (moins de
  passes) ; `ktex clean` le supprime, uniquement s'il contient le fichier
  témoin `.ktex`. Il supprime aussi les fichiers auxiliaires restés dans
  les sources (listés comme `OUTPUT` dans les `.fls`, ou d'extension
  auxiliaire et de même nom de base qu'un `.tex`), sans jamais toucher aux
  sources ni au PDF final.
- Sur place (`build_dir = "."`), avec `\include`, les `.aux` des chapitres ne
  dépendent pas du nom de job : deux cibles qui incluent les mêmes chapitres
  les partagent. Hors des sources, chaque document a son propre répertoire.
