"""French translation of ktex messages (see ktex.i18n)."""

MESSAGES = {
    # build
    "Removing truncated .aux files from an interrupted run":
        "Suppression des .aux tronqués par une compilation interrompue",
    " of {n}": " sur {n}",
    "Running {engine} (pass {n}{total})": "Exécution de {engine} (passe {n}{total})",
    "Running {bib} for bibliography": "Exécution de {bib} pour la bibliographie",
    "ERROR: {engine} failed on pass {n} (output in {log}). Aborting.":
        "ERREUR : échec de {engine} à la passe {n} (sortie dans {log}). Abandon.",
    "ERROR: {bib} failed (output in {log}). Aborting.": "ERREUR : échec de {bib} (sortie dans {log}). Abandon.",
    "WARNING: still asking for a rerun after {n} passes; giving up.":
        "ATTENTION : une nouvelle passe est encore demandée après {n} passes ; abandon.",
    "❌ Failure: LaTeX compilation reported an error.\nThe final PDF was not updated.":
        "❌ Échec : la compilation LaTeX a signalé une erreur.\nLe PDF final n'a pas été mis à jour.",
    "❌ Failure: {pdf} was not produced.": "❌ Échec : {pdf} n'a pas été produit.",
    "Moving PDF to final destination": "Installation du PDF final",
    "✅ Success: Full compilation process complete!\nFinal file: {pdf}":
        "✅ Succès : compilation complète terminée !\nFichier final : {pdf}",
    "Errors and warnings (details in {report})": "Erreurs et avertissements (détails dans {report})",
    "{main} not found in {root}": "{main} introuvable dans {root}",
    "cannot analyze the log: {error}": "analyse du log impossible : {error}",
    "command not found: {cmd}": "commande introuvable : {cmd}",
    # watch
    "watching {n} file(s) (Ctrl-C to stop)": "surveillance de {n} fichier(s) (Ctrl-C pour arrêter)",
    "{files} changed, rebuilding": "{files} modifié(s), nouvelle compilation",
    # clean
    "would remove {path}": "supprimerait {path}",
    "removed {path}": "supprimé : {path}",
    "nothing to clean": "rien à nettoyer",
    "{dir} was not created by ktex (no {marker}): not removed":
        "{dir} n'a pas été créé par ktex (pas de {marker}) : non supprimé",
    # cli
    "rebuild whenever a source file changes, until Ctrl-C":
        "recompiler à chaque modification d'un fichier source, jusqu'à Ctrl-C",
    "Full LaTeX build (passes, bibliography, atomic PDF) and report of errors located as file:line.":
        "Compilation LaTeX complète (passes, bibliographie, PDF atomique) "
        "et rapport d'erreurs localisées par fichier:ligne.",
    "target name from ktex.toml, or .tex file (default: first target, "
    "else the only main .tex file of the directory)":
        "nom de cible du ktex.toml ou fichier .tex (défaut : première cible, "
        "sinon l'unique .tex principal du répertoire)",
    "build directory (default: auto, a temporary directory outside the "
    "sources; \".\" to build in place)":
        "répertoire de compilation (défaut : auto, répertoire temporaire hors des "
        "sources ; « . » pour compiler sur place)",
    "force colors (default: if the output is a terminal)": "forcer la couleur (défaut : si la sortie est un terminal)",
    "disable colors": "désactiver la couleur",
    "build (default command)": "compiler (commande par défaut)",
    "LaTeX engine": "moteur LaTeX",
    "bibliography backend": "outil de bibliographie",
    "fixed number of LaTeX passes, or \"auto\"": "nombre fixe de passes LaTeX, ou « auto »",
    "maximum number of passes in auto mode (default: 5)": "nombre maximal de passes en mode auto (défaut : 5)",
    "job name (default: <main>, or <main>-tmp in place)": "nom du job (défaut : <main>, ou <main>-tmp sur place)",
    "final PDF (default: <main>.pdf)": "PDF final (défaut : <main>.pdf)",
    "prefix of the logs (default: output)": "préfixe des logs (défaut : output)",
    "show the raw output of LaTeX/Biber (always in the logs)":
        "afficher la sortie brute de LaTeX/Biber (toujours dans les logs)",
    "hide the raw output of LaTeX/Biber (default)": "masquer la sortie brute de LaTeX/Biber (défaut)",
    "also detail bad boxes in the terminal": "détailler aussi les boîtes mal remplies dans le terminal",
    "analyze the log of a previous build": "analyser le log d'une compilation déjà faite",
    "job whose JOB.log / JOB.blg to read": "job dont lire JOB.log / JOB.blg",
    "report file (default: <log_prefix>.errors.log)": "fichier rapport (défaut : <log_prefix>.errors.log)",
    "detail bad boxes in the terminal": "détailler les boîtes dans le terminal",
    "remove auxiliary files": "supprimer les fichiers auxiliaires",
    "list without removing": "lister sans supprimer",
    "keep <log_prefix>.errors.log and in-place logs": "garder <log_prefix>.errors.log et les logs sur place",
    "list .aux files truncated by an interrupted run": "lister les .aux tronqués par une compilation interrompue",
    "list the targets of ktex.toml": "lister les cibles du ktex.toml",
    "no ktex.toml here or in the parent directories": "pas de ktex.toml ici ni dans les répertoires parents",
    " (default)": " (défaut)",
    "create a ktex.toml for the LaTeX project of the current directory":
        "créer un ktex.toml pour le projet LaTeX du répertoire courant",
    # init
    "ktex configuration: {url}": "configuration de ktex : {url}",
    "Paths are relative to this file; command-line options take precedence.":
        "Chemins relatifs à ce fichier ; les options de la ligne de commande l'emportent.",
    "Options shared by all targets (default: automatic detection)":
        "Options communes à toutes les cibles (défaut : détection automatique)",
    "\"auto\": temporary directory; \".\": in place; or a path":
        "« auto » : répertoire temporaire ; « . » : sur place ; ou un chemin",
    "The first target is the default one (ktex); the others: ktex <name>.":
        "La première cible est la cible par défaut (ktex) ; les autres : ktex <nom>.",
    "detected engine: {engine}": "moteur détecté : {engine}",
    "{config} already exists": "{config} existe déjà",
    "no main .tex file (with \\documentclass) here or in the parent directories":
        "aucun fichier .tex principal (avec \\documentclass) ici ni dans les répertoires parents",
    "created {config} with target(s): {targets}": "{config} créé, cible(s) : {targets}",
    # config
    "{where}: unknown option(s): {options}": "{where} : option(s) inconnue(s) : {options}",
    "{where}: \"main\" is missing": "{where} : « main » manquant",
    "{path} not found": "{path} introuvable",
    "{config}: no target defined": "{config} : aucune cible définie",
    "unknown target \"{name}\"; targets: {targets}": "cible « {name} » inconnue ; cibles : {targets}",
    "\"{spec}\" is neither a .tex file nor a target (no {config})":
        "« {spec} » n'est ni un fichier .tex ni une cible (pas de {config})",
    "cannot guess the main file ({found}): give it as an argument or create a {config}":
        "impossible de deviner le fichier principal ({found}) : le donner en argument ou créer un {config}",
    "no \\documentclass found": "aucun \\documentclass trouvé",
    "passes: integer or \"auto\" expected, not \"{value}\"": "passes : entier ou « auto » attendu, pas « {value} »",
    "unknown engine \"{engine}\" ({choices}, auto)": "moteur inconnu « {engine} » ({choices}, auto)",
    "unknown bibliography backend \"{bib}\" ({choices}, none, auto)":
        "bibliographie inconnue « {bib} » ({choices}, none, auto)",
    # report
    "ERRORS": "ERREURS",
    "WARNINGS": "AVERTISSEMENTS",
    "OVERFULL / UNDERFULL BOXES": "BOÎTES TROP PLEINES / TROP VIDES",
    "{n}, {k} distinct": "{n}, {k} distinct(e)s",
    "(unknown file)": "(fichier inconnu)",
    "⟨here⟩": "⟨ici⟩",
    "Summary: {errors} error(s), {warnings} warning(s), {boxes} bad box(es)":
        "Bilan : {errors} erreur(s), {warnings} avertissement(s), {boxes} boîte(s) mal remplie(s)",
    " — warnings and boxes not shown: fix the errors first"
    " (undefined references/citations often follow from them)":
        " — avertissements et boîtes non affichés : corriger d'abord les erreurs"
        " (les références/citations indéfinies en découlent souvent)",
    " (not detailed)": " (non détaillées)",
    "Full report: {path}": "Rapport complet : {path}",
    "option \"{key}\" unknown to package {pkg} in its installed version"
    " (typo, or option of an older version)":
        "option « {key} » inconnue du paquet {pkg} dans sa version installée"
        " (faute de frappe, ou option d'une ancienne version)",
    "; written at: {locations}": " ; écrite en : {locations}",
    ".aux file(s) truncated by an interrupted run: {files} — remove them (or ktex clean) and rebuild":
        "fichier(s) .aux tronqué(s) par une compilation interrompue : {files}"
        " — les supprimer (ou ktex clean) puis relancer",
    "\\begin{{{env}}} probably opened at: {locations}": "\\begin{{{env}}} ouvert probablement en : {locations}",
    "also cited at: {locations}": "cité aussi en : {locations}",
    "\\label defined at: {locations}": "\\label défini en : {locations}",
    "Undefined citations: Biber has not been rerun yet (expected if the build stopped before)":
        "Citations indéfinies : Biber n'a pas encore été relancé"
        " (normal si la compilation s'est arrêtée avant)",
    "Undefined references: another LaTeX pass is needed (expected if the build stopped before)":
        "Références indéfinies : une passe LaTeX supplémentaire est nécessaire"
        " (normal si la compilation s'est arrêtée avant)",
}
