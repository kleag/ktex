# Détection automatique

Les options qui valent `auto` (c'est le défaut) sont déterminées à partir du
document.

## Moteur

1. Le commentaire magique `% !TEX program = <moteur>` dans le fichier
   principal, s'il est présent.
2. Sinon `xelatex`, si le préambule charge `fontspec`, `polyglossia` ou
   `unicode-math`, ou si un fichier `.sty`/`.cls` du répertoire du fichier
   principal les charge (thème beamer, classe maison…).
3. Sinon `pdflatex`.

Les lignes commentées sont ignorées.

## Bibliographie

ktex examine les fichiers produits par la première passe :

- `biber` si biblatex a écrit un fichier `.bcf` ;
- `bibtex` si le `.aux` contient `\bibdata` ;
- sinon, pas de bibliographie.

## Passes

En mode `auto`, ktex fait une première passe, puis la bibliographie, puis :

- une passe (deux pour BibTeX) ;
- puis d'autres passes tant que les fichiers auxiliaires (`.aux`, `.toc`,
  `.nav`…) changent ou que le log réclame une nouvelle passe (`Rerun to get…`,
  `Label(s) may have changed`, `Please rerun LaTeX`…), dans la limite de
  `max_passes`.

Comme le répertoire de compilation est conservé d'une fois sur l'autre, une
recompilation après une petite modification n'a souvent besoin que d'une ou
deux passes.
