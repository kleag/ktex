# ktex

*Kleag's TeX tool* : compilation LaTeX complète, en une commande, pour
n'importe quel document, suivie d'un rapport d'erreurs et d'avertissements
localisés par `fichier:ligne`.

```sh
ktex
```

Cette commande :

- enchaîne les passes LaTeX (`pdflatex`, `xelatex` ou `lualatex`) et la
  bibliographie (Biber ou BibTeX), [détectés automatiquement](detection.md) ou
  [fixés par configuration](configuration.md) ;
- compile **hors des sources**, dans un répertoire temporaire propre au
  document : aucun `.aux`, `.log`, `.bbl`… dans l'arborescence, y compris ceux
  des chapitres `\include`s ;
- **remplace atomiquement** le PDF final : la visionneuse ne voit jamais de PDF
  vide ou partiel, et un échec laisse l'ancien PDF en place ;
- supprime au préalable les `.aux` **tronqués** par une compilation
  interrompue (cause de l'erreur « File ended while scanning use of… » dès
  `\begin{document}`) ;
- écrit à la fin, en cas de succès comme d'échec, un
  [**rapport**](report.md) qui situe chaque problème dans le bon fichier,
  y compris dans les fichiers `\input`/`\include`, et l'accompagne d'indices.

```text
===== ERREURS (1) =====
chapitres/intro.tex:5: LaTeX Error: \begin{itemize} on input line 3 ended by \end{enumerate}.
    → \end{enumerate} ⟨ici⟩
    ↳ \begin{itemize} ouvert probablement en : chapitres/intro.tex:3
```

Avec `ktex -w`, ktex [tient le PDF à jour](usage.md#mode-surveillance) : il
recompile le document chaque fois qu'un de ses fichiers sources est modifié.
Ce mode surveillance s'inspire de [texbuild](https://github.com/SamDM/texbuild),
et sa façon de trouver les fichiers à surveiller (le fichier `.fls` écrit par
TeX), de [latexmk](https://ctan.org/pkg/latexmk).

ktex n'a besoin que de Python ≥ 3.11 et d'une distribution TeX (TeX Live,
MiKTeX…) qui fournit les moteurs et outils voulus. Ses messages sont en
français si la locale est française, en anglais sinon (voir
[Utilisation](usage.md#langue)).

[Installer ktex](installation.md){ .md-button .md-button--primary }
[Premiers pas](usage.md){ .md-button }
