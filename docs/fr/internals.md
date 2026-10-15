# Fonctionnement

## Lancement de TeX

LaTeX est toujours lancé **depuis le répertoire des sources** (`root`), avec :

- `-output-directory=<build_dir>` quand la compilation se fait hors des sources ;
- `-file-line-error`, pour que les erreurs soient données sous la forme
  `fichier:ligne:` ;
- `-interaction=nonstopmode` : une compilation n'attend jamais de réponse à
  l'invite `?` et ne peut pas être tuée en laissant un `.aux` tronqué ;
- `-recorder`, qui produit le `.fls` (liste des fichiers lus et écrits) ;
- la variable d'environnement `max_print_line=10000`, pour que les lignes du
  log ne soient pas coupées.

## Compilation hors des sources

Par défaut, les fichiers produits par TeX sont écrits dans
`$TMPDIR/ktex-<doc>-<hash>`. Le hachage du chemin du document distingue deux
documents de même nom. Ce répertoire est conservé d'une compilation à l'autre,
ce qui réduit le nombre de passes nécessaires.

TeX ne crée pas lui-même les sous-répertoires où il écrit les `.aux` des
chapitres `\include`s. ktex recrée donc dans le répertoire de compilation
l'arborescence des sous-répertoires des sources qui contiennent des `.tex`.

Biber est lancé depuis les sources avec `--output-directory`. BibTeX est lancé
dans le répertoire de compilation, avec `BIBINPUTS` et `BSTINPUTS` pointant sur
les sources.

## Déroulement

1. Recréation de l'arborescence dans le répertoire de compilation.
2. Suppression des `.aux` tronqués.
3. Première passe LaTeX.
4. Bibliographie (Biber ou BibTeX), si nécessaire.
5. Passes suivantes, en nombre fixe ou [automatique](detection.md#passes).
6. Installation du PDF final (et du `.synctex.gz`).
7. Rapport d'erreurs, toujours exécuté, même en cas d'échec.

## PDF atomique

Le PDF final n'est remplacé qu'après la réussite de la dernière passe, par un
renommage atomique (`os.replace`). Si le répertoire de compilation est sur un
autre système de fichiers (`/tmp` est souvent un `tmpfs`), le PDF est d'abord
copié dans un fichier temporaire du répertoire de destination, puis renommé.
Une visionneuse qui surveille le fichier ne voit donc jamais de PDF vide ou
partiel, et un échec laisse l'ancien PDF intact.

Pour la même raison, en compilation sur place, le nom de job par défaut est
`<main>-tmp` : le PDF en cours d'écriture n'est jamais le PDF final.

## Nettoyage

`ktex clean` est volontairement prudent. Il ne supprime que des fichiers dont
il peut prouver qu'ils ont été générés :

- le répertoire de compilation, seulement s'il contient le fichier témoin
  `.ktex` et qu'il n'est pas un parent des sources ;
- dans les sources, les fichiers listés comme `OUTPUT` dans les `.fls`, ou
  ceux qui ont une extension auxiliaire et le même nom de base qu'un `.tex`
  ou que le job.

Il ne supprime jamais un fichier source ni le PDF final. `--dry-run` liste ce
qui serait supprimé, sans rien supprimer.

!!! note "Compilation sur place et `\include`"
    Sur place (`build_dir = "."`), les `.aux` des chapitres `\include`s ne
    dépendent pas du nom de job : deux cibles qui incluent les mêmes chapitres
    les partagent. Hors des sources, chaque document a son propre répertoire.
