"""Watch mode: rebuild whenever a source file of the document changes.

The files to watch are the ones the last build actually read: the INPUT
lines of the <job>.fls written by -recorder (the idea comes from latexmk),
restricted to the source tree, plus the bibliography databases, which Biber
and BibTeX read outside TeX (from the .bcf, or \\bibdata in the .aux), even
outside the source tree.
The files are polled: a few hundred stat() calls per second cost nothing,
work everywhere, and survive editors that save by renaming a new file over
the old one.
"""

import os
import re
import time

from .i18n import _

RE_BCF_DATASOURCE = re.compile(r"<bcf:datasource[^>]*>([^<]+)</bcf:datasource>")
RE_BIBDATA = re.compile(r"\\bibdata\{([^}]*)\}")
RE_BIBSTYLE = re.compile(r"\\bibstyle\{([^}]*)\}")


def _inside(path, d):
    return os.path.commonpath([path, d]) == d


def dependencies(t):
    """Absolute paths of the source files read by the last build of target t."""
    # Real paths: the PWD line of the .fls has symbolic links resolved
    root = os.path.realpath(t.root)
    bdir = os.path.realpath(t.build_path)
    jobpath = os.path.join(bdir, t.job)
    inputs, outputs = set(), set()
    try:
        with open(jobpath + ".fls", encoding="utf-8", errors="replace") as f:
            pwd = root
            for line in f:
                kind, _sep, path = line.rstrip("\n").partition(" ")
                if kind == "PWD":
                    pwd = path
                elif kind in ("INPUT", "OUTPUT"):
                    p = os.path.realpath(os.path.join(pwd, path))
                    (inputs if kind == "INPUT" else outputs).add(p)
    except OSError:
        pass
    bibs = []
    try:
        with open(jobpath + ".bcf", encoding="utf-8", errors="replace") as f:
            bibs += RE_BCF_DATASOURCE.findall(f.read())
    except OSError:
        pass
    try:
        with open(jobpath + ".aux", encoding="utf-8", errors="replace") as f:
            aux = f.read()
        for m in RE_BIBDATA.finditer(aux):
            bibs += [b.strip() + ".bib" for b in m.group(1).split(",") if b.strip()]
        bibs += [m.group(1).strip() + ".bst" for m in RE_BIBSTYLE.finditer(aux)]
    except OSError:
        pass
    # Outside the sources, only the bibliography databases named by the
    # document are watched: other files come from the TeX distribution
    bibs = {os.path.realpath(os.path.join(root, os.path.expanduser(b))) for b in bibs}
    main = os.path.realpath(os.path.join(root, t.main))
    inputs.add(main)
    # Never watch what the build writes, or each build would trigger the next
    pdf = os.path.realpath(os.path.join(root, t.pdf))
    # (in place, <job>.bbl is written by BibTeX, not recorded in the .fls)
    generated = outputs | {pdf, os.path.splitext(pdf)[0] + ".synctex.gz",
                           os.path.realpath(os.path.join(root, t.log("errors")))}
    return sorted(p for p in {p for p in inputs if _inside(p, root)} | bibs
                  if not (t.out_of_source and _inside(p, bdir))
                  and p not in generated and os.path.isfile(p)
                  and (p == main or not p.startswith(jobpath + ".")))


def snapshot(paths):
    """{path: (mtime, size, inode)}, None for a file that disappeared."""
    out = {}
    for p in paths:
        try:
            st = os.stat(p)
            out[p] = (st.st_mtime_ns, st.st_size, st.st_ino)
        except OSError:
            out[p] = None
    return out


def changed(before, after):
    return sorted(p for p, v in after.items() if before.get(p, v) != v)


def watch(t, build_fn, interval=0.5, settle=0.3, sleep=time.sleep, max_builds=None):
    """Build t with build_fn(t), then rebuild each time one of its source
    files changes, until Ctrl-C (or max_builds builds, for the tests).
    Return the exit status of the last build."""
    status = 0
    builds = 0
    try:
        while True:
            # Files as they were when the build started: an edit made while
            # it runs triggers another build right after it
            before = snapshot(dependencies(t))
            status = build_fn(t)
            builds += 1
            if max_builds is not None and builds >= max_builds:
                return status
            deps = dependencies(t)
            # Files that this build read for the first time: from now on
            current = snapshot(deps)
            seen = {p: before.get(p, current[p]) for p in deps}
            print("ktex: " + _("watching {n} file(s) (Ctrl-C to stop)", n=len(deps)), flush=True)
            while True:
                diff = changed(seen, snapshot(deps))
                if diff:
                    break
                sleep(interval)
            # Wait until the editor has finished writing
            prev = snapshot(deps)
            while True:
                sleep(settle)
                cur = snapshot(deps)
                if cur == prev:
                    break
                prev = cur
            print("ktex: " + _("{files} changed, rebuilding",
                    files=", ".join(os.path.relpath(p, os.path.realpath(t.root)) for p in diff)), flush=True)
    except KeyboardInterrupt:
        print(flush=True)
        return status
