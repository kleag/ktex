# Configuration : `ktex.toml`

Sans configuration, ktex compile l'unique document du répertoire courant avec
les réglages détectés. Un fichier `ktex.toml` permet de nommer des **cibles**
et de fixer leurs options. `ktex init` en écrit un premier, avec une cible par
fichier principal du projet.

ktex cherche `ktex.toml` dans le répertoire courant, puis dans ses parents :
on peut donc lancer `ktex` depuis un sous-répertoire du document. Les chemins
du fichier sont relatifs à son emplacement.

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

Les clés placées au premier niveau s'appliquent à toutes les cibles. Chaque
section `[targets.<nom>]` peut les redéfinir.

## Options

| Option | Défaut | Description |
|---|---|---|
| `main` | *(obligatoire)* | fichier `.tex` principal, relatif à `root` |
| `root` | `"."` | répertoire des sources, d'où LaTeX est lancé |
| `engine` | `"auto"` | `pdflatex`, `xelatex`, `lualatex` ou `auto` ([détection](detection.md#moteur)) |
| `bib` | `"auto"` | `biber`, `bibtex`, `none` ou `auto` ([détection](detection.md#bibliographie)) |
| `passes` | `"auto"` | nombre fixe de passes LaTeX, ou `"auto"` ([détection](detection.md#passes)) |
| `max_passes` | `5` | plafond du nombre de passes en mode `auto` |
| `build_dir` | `"auto"` | `"auto"` : répertoire temporaire `$TMPDIR/ktex-<doc>-<hash>` ; `"."` : sur place ; ou un chemin |
| `jobname` | `<main>` | nom du job TeX (`<main>-tmp` sur place, pour que le PDF final ne soit jamais le fichier en cours d'écriture) |
| `output` | `<main>.pdf` | PDF final |
| `log_prefix` | `"output"` | préfixe des logs et du rapport (`<prefix>.errors.log`) |
| `verbose` | `false` | afficher la sortie brute des outils dans le terminal (elle est toujours dans les logs) |
| `engine_args` | `[]` | options supplémentaires du moteur, par exemple `["-synctex=1", "-shell-escape"]` |
| `show_boxes` | `false` | détailler les boîtes mal remplies dans le résumé du terminal |

!!! note "Noms de job"
    Un nom de job ne doit pas contenir de point : Biber prendrait la fin du nom
    pour une extension.

!!! tip "SyncTeX"
    Avec `engine_args = ["-synctex=1"]`, le fichier `.synctex.gz` est installé
    à côté du PDF final, en même temps que lui.
