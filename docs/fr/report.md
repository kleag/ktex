# Le rapport d'erreurs

À la fin de chaque compilation, qu'elle ait réussi ou non, ktex analyse le log
de TeX (et le `.blg` de Biber) et écrit `output.errors.log` à côté des
sources. `ktex check` le regénère à partir des logs existants.

## Format

```text
===== ERREURS (1) =====
chapitres/intro.tex:5: LaTeX Error: \begin{itemize} on input line 3 ended by \end{enumerate}.
    → \end{enumerate} ⟨ici⟩
    ↳ \begin{itemize} ouvert probablement en : chapitres/intro.tex:3

===== AVERTISSEMENTS (4) =====
these.tex:4: Références indéfinies : une passe LaTeX supplémentaire est nécessaire (normal si la compilation s'est arrêtée avant)
these.tex:4: LaTeX Warning: Citation `inconnu' on page 2 undefined on input line 4.
these.tex: LaTeX Warning: There were undefined references.
these.tex: LaTeX Warning: Label(s) may have changed. Rerun to get cross-references right.

===== BOÎTES TROP PLEINES / TROP VIDES (1) =====
chapitres/intro.tex:6: Overfull \hbox (110.37259pt too wide) detected at line 6

Bilan : 1 erreur(s), 4 avertissement(s), 1 boîte(s) mal remplie(s)
```

Chaque entrée commence par `fichier:ligne:`. C'est le format que reconnaissent
la plupart des éditeurs (Emacs, Vim, VS Code…) pour aller directement à
l'emplacement. Les lignes indentées donnent le contexte :

- `→` : l'endroit exact de la ligne où TeX s'est arrêté ;
- `↳` : un indice ajouté par ktex.

Les occurrences multiples d'un même message sont regroupées, avec leurs
emplacements rassemblés par fichier.

Le rapport est écrit dans la [langue](usage.md#langue) des messages ; les
messages cités de TeX, des paquets LaTeX et de Biber sont conservés tels quels.

## Localisation dans le bon fichier

TeX n'indique pas toujours dans quel fichier il se trouve. ktex reconstitue le
fichier courant à partir des parenthèses que TeX écrit dans le log à chaque
ouverture et fermeture de fichier. Les erreurs et avertissements sont ainsi
attribués au fichier `\input` ou `\include` où ils se produisent, et non au
fichier principal.

## Indices

ktex complète les messages bruts de TeX quand il le peut :

- **environnement non fermé** : où l'environnement mal fermé a probablement été
  ouvert ;
- **`\label` dupliqué** : les emplacements des deux définitions ;
- **clé de citation absente** de la bibliographie, et les endroits où elle est
  citée ;
- **option de paquet inconnue** ;
- **`.aux` tronqué** par une compilation interrompue.

Les références et citations indéfinies qui attendent seulement une passe
supplémentaire, par exemple parce que la compilation s'est arrêtée avant
Biber, sont regroupées en une seule ligne, pour ne pas noyer les vraies erreurs.

## Terminal

Dans le terminal, ktex n'affiche que les erreurs s'il y en a, car les
avertissements et les références indéfinies en découlent souvent. Il ne
détaille les boîtes mal remplies qu'avec `--boxes`. Le bilan final rappelle
toujours les nombres d'erreurs, d'avertissements et de boîtes.
