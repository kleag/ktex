# Contribuer

Le code est sur [GitHub](https://github.com/kleag/ktex). Les rapports de bogue
sont les bienvenus. Si possible, joignez-y le log TeX en cause (le fichier
`.log` du répertoire de compilation).

## Environnement de développement

Le projet utilise [uv](https://docs.astral.sh/uv/).

```sh
git clone https://github.com/kleag/ktex.git
cd ktex
uv sync                        # environnement (tests, docs, bumpver)
uv run pytest -q               # tests
uv run ktex --help             # lancer ktex depuis les sources
```

Les tests d'intégration compilent de petits documents réels. Ils sont sautés si
`pdflatex`, `xelatex`, `bibtex` ou `biber` manque. En CI, la variable
`KTEX_REQUIRE_TEX=1` fait échouer les tests dans ce cas au lieu de les sauter.

## Documentation

La documentation est écrite en Markdown, en anglais dans `docs/en/` et en
français dans `docs/fr/` (mêmes noms de fichiers), et construite avec
[Zensical](https://zensical.org/) :

```sh
uv run zensical serve                              # aperçu du site anglais
uv run zensical serve -f zensical.fr.toml          # aperçu du site français
uv run zensical build --strict --clean && uv run zensical build --strict -f zensical.fr.toml
```

La seconde construction écrit le site français dans `site/fr/`. La
documentation est publiée sur GitHub Pages à chaque push sur `main`.

## Traductions

Les messages sont écrits en anglais dans le code et passés à `_()` (voir
`src/ktex/i18n.py`). Leurs traductions sont dans
`src/ktex/translations/<langue>.py`, un dictionnaire du message anglais vers sa
traduction. Quand vous ajoutez ou modifiez un message, mettez aussi à jour
`translations/fr.py` : un test vérifie que chaque message a une traduction avec
les mêmes paramètres.

Pour ajouter une langue : créer `translations/<langue>.py`, ajouter son code à
`LANGUAGES` dans `i18n.py`, et traduire la documentation dans `docs/<langue>/`
avec son propre `zensical.<langue>.toml`.

## Principes

- Des dépendances limitées et bien maintenues (aucune à l'exécution pour l'instant).
- L'outil reste générique : rien de propre à un document particulier dans le
  code, les valeurs par défaut, la documentation ou les tests. Les réglages
  d'un document vont dans son `ktex.toml`.
- Chaque nouveau comportement s'accompagne d'un test (log d'exemple ou petit
  document).
- Le format du rapport (`output.errors.log`) est utilisé par des personnes et
  par des outils : ne le modifier que délibérément.

## Publier une version

Les numéros de version sont gérés par [bumpver](https://github.com/mbarkhau/bumpver).
La version est écrite dans `pyproject.toml` (`[tool.bumpver]`) et dans
`src/ktex/__init__.py`, et le paquet lit la sienne dans ce dernier.

1. Déplacer les entrées de « Unreleased » de `CHANGELOG.md` sous la nouvelle
   version, puis commiter.
2. Changer de version : bumpver modifie les deux fichiers, commite et crée le
   tag `vX.Y.Z`.
   ```sh
   uv run bumpver update --patch     # ou --minor, --major ; --dry pour voir
   ```
3. Pousser le commit et le tag :
   ```sh
   git push --follow-tags
   ```
4. Le workflow `release.yml` lance les tests, vérifie que le tag correspond à
   `__version__`, construit les paquets avec `uv build`, les publie sur PyPI
   (Trusted Publishing) et crée la release GitHub.
