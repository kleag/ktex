# Utilisation

## Premiers pas

```sh
cd mon-document          # ou n'importe lequel de ses sous-répertoires
ktex init                # crée ktex.toml, avec une cible par fichier .tex principal
ktex                     # compile la cible par défaut
```

`ktex init` est facultatif : sans `ktex.toml`, `ktex` compile l'unique fichier
`.tex` principal du répertoire courant. Un fichier de configuration permet de
compiler depuis n'importe quel sous-répertoire, de nommer plusieurs documents
et de fixer des [options](configuration.md). Voir [`ktex init`](#ktex-init)
plus bas.

## Compiler

```sh
ktex                     # cible par défaut du ktex.toml, sinon l'unique .tex principal du répertoire
ktex these.tex           # un fichier donné
ktex soutenance          # la cible « soutenance » du ktex.toml
```

`build` est la sous-commande par défaut : `ktex these.tex` équivaut à
`ktex build these.tex`. Si aucune configuration n'existe, ktex prend dans le
répertoire courant l'unique fichier `.tex` qui contient `\documentclass`.

Options de `ktex build` :

| Option | Effet |
|---|---|
| `-e`, `--engine` | `pdflatex`, `xelatex`, `lualatex` ou `auto` |
| `-b`, `--bib` | `biber`, `bibtex`, `none` ou `auto` |
| `-n`, `--passes` | nombre fixe de passes LaTeX, ou `auto` |
| `--max-passes` | plafond du nombre de passes en mode `auto` (défaut 5) |
| `-d`, `--build-dir` | répertoire de compilation (défaut : temporaire ; `.` : sur place) |
| `-j`, `--jobname` | nom du job (défaut : `<main>`, ou `<main>-tmp` sur place) |
| `-o`, `--output` | PDF final (défaut : `<main>.pdf`) |
| `--log-prefix` | préfixe des logs (défaut : `output`) |
| `-v`, `--verbose` | afficher la sortie brute de LaTeX/Biber (masquée par défaut ; elle est toujours dans les logs) |
| `-q`, `--quiet` | masquer la sortie brute (le défaut ; l'emporte sur `verbose = true`) |
| `--boxes` | détailler aussi les boîtes mal remplies dans le terminal |
| `-w`, `--watch` | recompiler à chaque modification d'un fichier source, jusqu'à Ctrl-C (voir [Mode surveillance](#mode-surveillance)) |
| `--color`, `--no-color` | forcer ou désactiver la couleur (défaut : si la sortie est un terminal et que `NO_COLOR` n'est pas défini) |

Les options de la ligne de commande l'emportent sur le `ktex.toml`. Les
chemins qu'elles donnent sont relatifs au répertoire courant.

```sh
ktex build -e lualatex -b bibtex -n 2 these.tex
ktex -d .                # compilation sur place, à l'ancienne
ktex -o ~/these.pdf      # PDF écrit ailleurs
ktex -v                  # afficher aussi la sortie brute de LaTeX et Biber
ktex -w                  # compiler, puis recompiler à chaque modification
```

## Mode surveillance

Avec `-w`/`--watch`, ktex compile le document, puis attend et le recompile
chaque fois qu'un de ses fichiers sources est modifié, jusqu'à Ctrl-C. Gardez
le PDF ouvert dans une visionneuse qui le recharge quand il change. Le PDF
n'est remplacé que si la compilation réussit : vous continuez à lire la version
précédente pendant une compilation ou après un échec.

Les fichiers surveillés sont ceux que la dernière compilation a lus dans le
répertoire des sources : les lignes `INPUT` du fichier `.fls` que TeX écrit
avec `-recorder` (fichiers `.tex`, classes et paquets locaux, images…), plus
les bases bibliographiques (même hors du répertoire des sources), lues par
Biber ou BibTeX hors de TeX. Les fichiers
de la distribution TeX et ceux produits par la compilation ne sont pas
surveillés. Les fichiers sont vérifiés deux fois par seconde ; une
modification faite pendant une compilation en déclenche une autre juste après.

Limites : un fichier que le document ne lit pas encore (un nouveau chapitre
appelé par `\input` mais qui n'existe pas) n'est surveillé qu'une fois qu'une
compilation l'a lu. Les modifications du `ktex.toml` ne sont prises en compte
qu'au redémarrage de ktex.

## Autres commandes

`ktex init`{ #ktex-init }
:   Crée un [`ktex.toml`](configuration.md) pour le projet LaTeX du
    répertoire courant : le plus proche répertoire, en remontant depuis le
    répertoire courant (sans sortir du dépôt git), qui contient des fichiers
    `.tex` principaux. Il définit une cible par fichier principal, la première
    étant la cible par défaut ; les documents `standalone` et `subfiles` sont
    ignorés. Il ne fait rien si un `ktex.toml` s'applique déjà au répertoire
    courant.

`ktex check [cible]`
:   Ré-analyse le log de la dernière compilation et réécrit le rapport, sans
    rien recompiler. Avec `-o FICHIER`, le rapport est écrit dans un autre fichier.

`ktex clean [cible] [--dry-run] [--keep-logs]`
:   Supprime le répertoire de compilation et les fichiers auxiliaires restés
    dans les sources. Il ne touche jamais aux sources ni au PDF final
    (voir [Fonctionnement](internals.md#nettoyage)).

`ktex corrupt-aux [cible]`
:   Liste les `.aux` tronqués par une compilation interrompue.

`ktex targets`
:   Liste les cibles du `ktex.toml`. La première est la cible par défaut.

## Fichiers produits

Avec le préfixe par défaut `output` :

- dans le répertoire de compilation : `output.1.log`, `output.2.log`… (la sortie
  brute de chaque passe, que le terminal n'affiche qu'avec `-v`) et `output.bib.log` ;
- à côté des sources : le PDF et `output.errors.log`, le [rapport](report.md)
  complet.

Le terminal n'affiche que les erreurs s'il y en a, car les avertissements et
les références indéfinies en découlent souvent. Il ne détaille les boîtes mal
remplies qu'avec `--boxes`. Le rapport complet contient toujours tout.

## Code de retour

`ktex build` renvoie 0 si la compilation a réussi. Sinon il renvoie un code
non nul, et le PDF précédent est conservé. Une erreur de configuration (cible
inconnue, `ktex.toml` invalide…) renvoie 2. En mode surveillance, ktex
renvoie, quand on l'arrête, le code de la dernière compilation.

## Langue

Les messages, l'aide et le rapport sont en français si la locale est
française (`LANGUAGE`, `LC_ALL`, `LC_MESSAGES` ou `LANG`, dans cet ordre, comme
pour gettext), en anglais sinon. La variable d'environnement `KTEX_LANG`
l'emporte :

```sh
KTEX_LANG=fr ktex        # français, quelle que soit la locale
KTEX_LANG=en ktex        # anglais
```

Les messages cités de TeX, des paquets LaTeX et de Biber sont laissés tels quels.
