"""Extrait erreurs et warnings d'un log (Xe|Lua|pdf)LaTeX (et du log Biber)
en les localisant par fichier:ligne.

Le fichier courant est reconstitué en suivant les parenthèses ouvrantes et
fermantes que TeX écrit dans le log à chaque ouverture/fermeture de fichier.
Pour un log lisible, compiler avec max_print_line=10000 (pas de coupure des
lignes à 79 caractères) et -file-line-error.
"""

import os
import re
import sys
from collections import Counter

# Racine du projet : les chemins du log sont relatifs au répertoire où TeX a
# été lancé, qui doit être le répertoire courant lors de l'analyse.
PROJECT = os.path.abspath(os.getcwd())
# Répertoire de compilation (-output-directory), s'il est hors des sources
BUILD_DIR = None


def set_root(root, build_dir=None):
    """Fixe la racine du projet et le répertoire de compilation (et vide les
    caches qui en dépendent)."""
    global PROJECT, BUILD_DIR
    PROJECT = os.path.abspath(root)
    BUILD_DIR = os.path.abspath(build_dir) if build_dir else None
    if BUILD_DIR == PROJECT:
        BUILD_DIR = None
    _source_cache.clear()

# --- Expressions régulières -------------------------------------------------

RE_FILE_LINE_ERROR = re.compile(r"^(\.?/?[^:\s]+\.\w+):(\d+): (.*)$")
RE_BANG_ERROR = re.compile(r"^! (.*)$")
RE_LNUM = re.compile(r"^l\.(\d+)(.*)$")
RE_WARNING = re.compile(
    r"^((?:LaTeX|Package|Class|Module)\s*(?:[\w.-]+\s+)?Warning|LaTeX Font Warning|pdfTeX warning.*?):?\s*(.*)$"
)
RE_BOX = re.compile(r"^(Overfull|Underfull) \\[hv]box .*$")
RE_MISSING_CHAR = re.compile(r"^Missing character: (.*)$")
RE_INPUT_LINE = re.compile(r"on input line (\d+)")
RE_BOX_LINES = re.compile(r"(?:in paragraph|in alignment|detected) at lines? (\d+)")
RE_UNCLOSED_ENV = re.compile(r"\\begin\{([^}]+)\} on input line (\d+) ended by \\end\{([^}]+)\}")
RE_REF_KEY = re.compile(r"(?:Reference|Citation|Label) [`'‘]([^'’]+)['’]")
RE_BIBER = re.compile(r"^\[\d+\] .*?> (WARN|ERROR) - (.*)$|^(WARN|ERROR) - (.*)$")
RE_BIBER_MISSING = re.compile(
    r"I didn't find a database entry for '([^']+)'|could not be found in the database: (\S+)")
RE_BIBER_BIBLINE = re.compile(r"([\w./-]+\.bib)(?:_\d+\.utf8)?, line (\d+)")
RE_UNKNOWN_KEY = re.compile(r"The key '([\w@-]+)/([^']+)' is unknown")
RE_CONTINUATION = re.compile(r"^\([\w.@-]+\)\s+(.*)$")
# Parties variables d'un message, ignorées pour regrouper les occurrences
RE_VARIABLE = re.compile(r"\s*on (?:page \d+|input line \d+)")


def rel(path):
    """Chemin relatif au projet si le fichier en fait partie, sinon tel quel."""
    ap = os.path.abspath(path)
    if ap.startswith(PROJECT + os.sep):
        return os.path.relpath(ap, PROJECT)
    return path


def in_project(path):
    return path is not None and os.path.abspath(path).startswith(PROJECT + os.sep)


class Entry:
    def __init__(self, kind, file, line, msg, note=None, ctx=None):
        self.kind = kind  # "error", "warning", "box"
        self.file = file
        self.line = line
        self.msg = msg
        self.note = note
        self.ctx = ctx  # extrait de la ligne source où TeX s'est arrêté
        self.label = None  # libellé de regroupement imposé (voir collapse_pending)

    def loc(self):
        if not self.file:
            return "(fichier inconnu)"
        return f"{self.file}:{self.line}" if self.line else f"{self.file}"

    def key(self):
        return (self.kind, self.file, self.line, self.msg, self.ctx)

    def group_key(self):
        return (self.kind, self.label or RE_VARIABLE.sub("", self.msg))


# --- Lecture du log ----------------------------------------------------------

def read_log(path):
    with open(path, encoding="utf-8", errors="replace") as f:
        lines = f.read().split("\n")
    # Si le log a été coupé à 79 colonnes (max_print_line par défaut),
    # recoller les lignes coupées.
    if lines and max(len(l) for l in lines) <= 79:
        joined, buf = [], ""
        for l in lines:
            buf += l
            if len(l) != 79:
                joined.append(buf)
                buf = ""
        if buf:
            joined.append(buf)
        lines = joined
    return lines


class FileStack:
    """Pile des fichiers ouverts, reconstituée via les parenthèses du log."""

    def __init__(self):
        self.stack = []

    def feed(self, text):
        i = 0
        n = len(text)
        while i < n:
            c = text[i]
            if c == "(":
                m = re.match(r"\(([^()\s\"]+|\"[^\"]+\")", text[i:])
                cand = m.group(1).strip('"') if m else None
                if cand and os.path.isfile(cand):
                    self.stack.append(cand)
                    i += len(m.group(0))
                    continue
                self.stack.append(None)
            elif c == ")":
                if self.stack:
                    self.stack.pop()
            i += 1

    def current(self):
        """Fichier du projet le plus interne (on ignore les fichiers système)."""
        for f in reversed(self.stack):
            if f is not None and in_project(f):
                return rel(f)
        for f in reversed(self.stack):
            if f is not None:
                return f
        return None


def parse_tex_log(path):
    lines = read_log(path)
    stack = FileStack()
    entries = []
    i = 0
    n = len(lines)
    while i < n:
        line = lines[i]

        # Erreur au format -file-line-error : ./fichier.tex:12: message
        m = RE_FILE_LINE_ERROR.match(line)
        if m and os.path.isfile(m.group(1)):
            msg, ctx, j = collect_error(lines, i + 1, m.group(3))
            entries.append(Entry("error", rel(m.group(1)), int(m.group(2)), msg, ctx=ctx))
            i = j
            continue

        # Erreur au format classique : ! message ... l.12
        m = RE_BANG_ERROR.match(line)
        if m:
            msg, ctx, j, lnum = collect_error(lines, i + 1, m.group(1), want_lnum=True)
            entries.append(Entry("error", stack.current(), lnum, msg, ctx=ctx))
            i = j
            continue

        m = RE_WARNING.match(line)
        if m:
            text, j = collect_warning(lines, i)
            lm = RE_INPUT_LINE.search(text)
            entries.append(Entry("warning", stack.current(), int(lm.group(1)) if lm else None, text))
            i = j
            continue

        m = RE_BOX.match(line)
        if m:
            lm = RE_BOX_LINES.search(line)
            entries.append(Entry("box", stack.current(), int(lm.group(1)) if lm else None, line.strip()))
            # Les lignes suivantes reproduisent le contenu de la boîte (texte
            # avec parenthèses non équilibrées) jusqu'à la ligne " []" : on les saute.
            j = i + 1
            if "has occurred while \\output is active" not in line:
                while j < n and lines[j].strip() != "[]" and lines[j].strip() != "":
                    j += 1
                j += 1
            i = j
            continue

        m = RE_MISSING_CHAR.match(line)
        if m:
            entries.append(Entry("warning", stack.current(), None, line.strip()))
            i += 1
            continue

        stack.feed(line)
        i += 1
    return entries


HELP_PREFIXES = ("See the ", "Type  H", "Type X", "or enter new name", "Enter file name",
                 "You're in trouble", "<read ", "<*>", "<inserted text>", "...",
                 "For immediate help")


def collect_error(lines, i, first, want_lnum=False):
    """Rassemble le message d'erreur jusqu'à la ligne de contexte l.NNN.
    Renvoie (message, contexte, indice suivant[, numéro de ligne])."""
    text = first.strip()
    extra = []
    ctx = None
    lnum = None
    n = len(lines)
    start = i
    while i < n and i - start < 30:
        l = lines[i]
        m = RE_LNUM.match(l)
        if m:
            lnum = int(m.group(1))
            before = m.group(2).strip()
            after = lines[i + 1].strip() if i + 1 < n else ""
            if before or after:
                ctx = f"{before} ⟨ici⟩ {after}".strip()
            i += 2
            break
        mc = RE_CONTINUATION.match(l)
        if mc and not extra:
            # Suite du message : "(LaTeX)        ignored."
            text += " " + mc.group(1).strip()
        elif l.strip() and not l.strip().startswith(HELP_PREFIXES):
            if len(extra) < 3:
                extra.append(l.strip())
        i += 1
    msg = " | ".join([text] + extra)
    if want_lnum:
        return msg, ctx, i, lnum
    return msg, ctx, i


def collect_warning(lines, i):
    """Un warning se poursuit sur les lignes '(paquet)   ...' ou jusqu'à une ligne vide."""
    parts = [lines[i].strip()]
    j = i + 1
    n = len(lines)
    while j < n and lines[j].strip() != "":
        l = lines[j]
        if re.match(r"^\([\w.-]+\)\s", l):
            parts.append(re.sub(r"^\([\w.-]+\)\s+", "", l).strip())
            j += 1
        elif lines[i].startswith("LaTeX") and not l.startswith(("(", "[", "<", ")")):
            parts.append(l.strip())
            j += 1
        else:
            break
    return " ".join(parts), j


# --- Biber -------------------------------------------------------------------

def parse_biber_log(path):
    entries = []
    if not os.path.isfile(path):
        return entries
    with open(path, encoding="utf-8", errors="replace") as f:
        for l in f:
            m = RE_BIBER.match(l.rstrip())
            if not m:
                continue
            level = m.group(1) or m.group(3)
            msg = (m.group(2) or m.group(4)).strip()
            bm = RE_BIBER_BIBLINE.search(msg)
            file, line = (rel(bm.group(1)), int(bm.group(2))) if bm else ("biber", None)
            entries.append(Entry("error" if level == "ERROR" else "warning", file, line, "Biber: " + msg))
    return entries


# --- Fichiers .aux tronqués --------------------------------------------------

def corrupt_aux_files():
    """Fichiers .aux tronqués (du projet et du répertoire de compilation),
    typiquement par une compilation tuée avant d'avoir vidé ses tampons
    d'écriture : accolades non équilibrées ou dernière ligne incomplète. Ils
    font échouer la passe suivante dès \\begin{document} (« File ended while
    scanning use of ... »). Chemins relatifs au projet, absolus hors du projet."""
    bad = []
    for top in [PROJECT] + ([BUILD_DIR] if BUILD_DIR and os.path.isdir(BUILD_DIR) else []):
        for root, dirs, names in os.walk(top):
            dirs[:] = [d for d in dirs if not d.startswith(".")]
            for nm in names:
                if not nm.endswith(".aux"):
                    continue
                path = os.path.join(root, nm)
                try:
                    with open(path, encoding="utf-8", errors="replace") as f:
                        text = f.read()
                except OSError:
                    continue
                if not text:
                    continue
                code = re.sub(r"\\[{}]", "", text)
                if code.count("{") != code.count("}") or not text.endswith("\n"):
                    bad.append(rel(path))
    return sorted(set(bad))


# --- Enrichissements ---------------------------------------------------------

_source_cache = {}


def project_tex_files():
    if "list" not in _source_cache:
        files = []
        for root, dirs, names in os.walk(PROJECT):
            dirs[:] = [d for d in dirs if not d.startswith(".")]
            for nm in names:
                if nm.endswith(".tex"):
                    files.append(os.path.relpath(os.path.join(root, nm), PROJECT))
        _source_cache["list"] = sorted(files)
    return _source_cache["list"]


def source_lines(f):
    if f not in _source_cache:
        try:
            with open(f, encoding="utf-8", errors="replace") as fh:
                _source_cache[f] = fh.read().split("\n")
        except OSError:
            _source_cache[f] = []
    return _source_cache[f]


def find_in_sources(pattern, only_line=None, max_hits=6):
    """Cherche une regex dans les .tex du projet (lignes non commentées)."""
    hits = []
    rx = re.compile(pattern)
    for f in project_tex_files():
        for k, l in enumerate(source_lines(f), 1):
            if only_line is not None and k != only_line:
                continue
            code = re.split(r"(?<!\\)%", l, maxsplit=1)[0]
            if rx.search(code):
                hits.append(f"{f}:{k}")
    return hits[:max_hits], len(hits)


def enrich(entries):
    for e in entries:
        km = RE_UNKNOWN_KEY.search(e.msg)
        if km:
            pkg, key = km.groups()
            hits, total = find_in_sources(r"(?<![\w-])" + re.escape(key) + r"\s*=")
            e.note = (f"option « {key} » inconnue du paquet {pkg} dans sa version installée"
                      " (faute de frappe, ou option d'une ancienne version)")
            if hits:
                e.note += " ; écrite en : " + ", ".join(hits) + (" …" if total > len(hits) else "")
            continue
        if "File ended while scanning" in e.msg or "Runaway argument" in e.msg:
            bad = corrupt_aux_files()
            if bad:
                e.note = ("fichier(s) .aux tronqué(s) par une compilation interrompue : "
                          + ", ".join(bad) + " — les supprimer (ou ktex clean) puis relancer")
                if "\\begin{document}" in e.msg:
                    e.file, e.line = bad[0], None
                continue
        m = RE_UNCLOSED_ENV.search(e.msg)
        if m:
            env, lnum = m.group(1), int(m.group(2))
            hits, _ = find_in_sources(r"\\begin\{" + re.escape(env) + r"\}", only_line=lnum)
            if hits:
                e.note = "\\begin{%s} ouvert probablement en : %s" % (env, ", ".join(hits))
            continue
        bm = RE_BIBER_MISSING.search(e.msg)
        if bm:
            key = bm.group(1) or bm.group(2)
            hits, total = find_in_sources(r"\\\w*cite\w*\*?(\[[^\]]*\])*\{([^}]*[,\s])?" + re.escape(key) + r"\s*[,}]")
            if hits:
                e.file, e.line = hits[0].rsplit(":", 1)
                e.line = int(e.line)
                if total > 1:
                    e.note = "cité aussi en : " + ", ".join(hits[1:]) + (" …" if total > len(hits) else "")
            continue
        if "multiply defined" in e.msg or "multiply-defined" in e.msg:
            km = RE_REF_KEY.search(e.msg)
            if km:
                hits, _ = find_in_sources(r"\\label\{" + re.escape(km.group(1)) + r"\}")
                if hits:
                    e.note = "\\label défini en : " + ", ".join(hits)


# --- Sortie ------------------------------------------------------------------

SECTIONS = [
    ("error", "ERREURS"),
    ("warning", "AVERTISSEMENTS"),
    ("box", "BOÎTES TROP PLEINES / TROP VIDES"),
]


RE_UNDEF_CITE = re.compile(r"Citation .* undefined")
RE_UNDEF_REF = re.compile(r"Reference .* undefined")


def collapse_pending(entries):
    """Si le log réclame une nouvelle passe (Biber ou LaTeX), les citations et
    références indéfinies sont attendues : on les regroupe en une seule ligne."""
    msgs = " ".join(e.msg for e in entries if e.kind == "warning")
    biber = "Please (re)run Biber" in msgs
    rerun = biber or "Rerun to get cross-references" in msgs or "Label(s) may have changed" in msgs
    for e in entries:
        if e.kind != "warning":
            continue
        if biber and RE_UNDEF_CITE.search(e.msg):
            e.label = ("Citations indéfinies : Biber n'a pas encore été relancé"
                       " (normal si la compilation s'est arrêtée avant)")
        elif rerun and RE_UNDEF_REF.search(e.msg):
            e.label = ("Références indéfinies : une passe LaTeX supplémentaire est nécessaire"
                       " (normal si la compilation s'est arrêtée avant)")
        if e.label:
            e.msg = e.label


def group(entries):
    """Regroupe les occurrences d'un même message : [(entrée, [entrées])]."""
    groups = {}
    for e in entries:
        groups.setdefault(e.group_key(), []).append(e)
    return list(groups.values())


def locations(group):
    """« fichier:12, 15, 20 ; autre.tex:3 », lignes regroupées par fichier."""
    by_file = {}
    for e in group:
        by_file.setdefault(e.file or "(fichier inconnu)", [])
        if e.line and e.line not in by_file[e.file or "(fichier inconnu)"]:
            by_file[e.file or "(fichier inconnu)"].append(e.line)
    out = []
    for f, ls in by_file.items():
        shown = ", ".join(str(l) for l in ls[:12]) + (", …" if len(ls) > 12 else "")
        out.append(f"{f}:{shown}" if ls else f)
    return " ; ".join(out)


def render(entries, color, show_boxes, only_errors=False):
    C = {
        "error": "\033[1;31m", "warning": "\033[1;33m", "box": "\033[36m",
        "loc": "\033[1;4m", "dim": "\033[2m", "end": "\033[0m",
    } if color else {k: "" for k in ("error", "warning", "box", "loc", "dim", "end")}
    out = []
    counts = Counter(e.kind for e in entries)
    for kind, title in SECTIONS:
        if (kind == "box" and not show_boxes) or (only_errors and kind != "error"):
            continue
        groups = group([e for e in entries if e.kind == kind])
        if not groups:
            continue
        nb = sum(len(g) for g in groups)
        detail = f"{nb}, {len(groups)} distinct(e)s" if nb != len(groups) else f"{nb}"
        out.append(f"{C[kind]}===== {title} ({detail}) ====={C['end']}")
        for g in groups:
            e = g[0]
            if len(g) == 1:
                out.append(f"{C['loc']}{e.loc()}{C['end']}: {C[kind]}{e.msg}{C['end']}")
                if e.ctx:
                    out.append(f"    {C['dim']}→ {e.ctx}{C['end']}")
            else:
                out.append(f"{C[kind]}{RE_VARIABLE.sub('', e.msg)}{C['end']}"
                           f" {C['dim']}(×{len(g)}){C['end']}")
                out.append(f"    {C['loc']}{locations(g)}{C['end']}")
            if e.note:
                out.append(f"    {C['dim']}↳ {e.note}{C['end']}")
        out.append("")
    summary = (f"Bilan : {counts['error']} erreur(s), {counts['warning']} avertissement(s), "
               f"{counts['box']} boîte(s) mal remplie(s)")
    if only_errors and (counts["warning"] or counts["box"]):
        summary += (" — avertissements et boîtes non affichés : corriger d'abord les erreurs"
                    " (les références/citations indéfinies en découlent souvent)")
    elif not show_boxes and counts["box"]:
        summary += " (non détaillées)"
    out.append(summary)
    return "\n".join(out)


def analyze(job):
    """Entrées dédoublonnées des logs JOB.log et JOB.blg ; JOB peut être un
    chemin (répertoire de compilation), le répertoire courant doit être celui
    où TeX a été lancé."""
    entries = parse_tex_log(job + ".log") + parse_biber_log(job + ".blg")
    enrich(entries)
    collapse_pending(entries)
    # Dédoublonnage en conservant l'ordre
    seen, uniq = set(), []
    for e in entries:
        if e.key() not in seen:
            seen.add(e.key())
            uniq.append(e)
    return uniq


def report(job, out_path="output.errors.log", color=False, show_boxes=True, stream=None):
    """Écrit le rapport complet dans out_path et un résumé sur stream.
    Renvoie 1 s'il y a des erreurs, 0 sinon, 2 si le log est introuvable."""
    stream = stream or sys.stdout
    log = job + ".log"
    if not os.path.isfile(log):
        print(f"ktex: {log} introuvable", file=sys.stderr)
        return 2
    uniq = analyze(job)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(render(uniq, color=False, show_boxes=True) + "\n")
    has_errors = any(e.kind == "error" for e in uniq)
    print(render(uniq, color=color, show_boxes=show_boxes, only_errors=has_errors), file=stream)
    print(f"Rapport complet : {out_path}", file=stream)
    return 1 if has_errors else 0
