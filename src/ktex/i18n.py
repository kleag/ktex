"""Translation of user-facing messages.

English is the source language: messages are written in English in the code
and wrapped in _(), which looks them up in the catalog of the current
language (ktex/translations/<lang>.py, a dict from English message to
translation) and fills in their str.format placeholders.

The language is taken from KTEX_LANG, else from the locale (LANGUAGE,
LC_ALL, LC_MESSAGES, LANG, in gettext's order); languages without a catalog
fall back to English.
"""

import importlib
import os

LANGUAGES = ("en", "fr")
_catalog = {}
_lang = None


def detect_language(environ=None):
    environ = os.environ if environ is None else environ
    for var in ("KTEX_LANG", "LANGUAGE", "LC_ALL", "LC_MESSAGES", "LANG"):
        value = environ.get(var)
        if value:
            # "fr_FR.UTF-8", "fr:en", "C.UTF-8"…
            code = value.split(":")[0].split("_")[0].split(".")[0].lower()
            return code if code in LANGUAGES else "en"
    return "en"


def set_language(lang=None):
    """Select the language of messages (None: detect it from the environment)."""
    global _lang, _catalog
    _lang = lang if lang in LANGUAGES else detect_language()
    _catalog = {} if _lang == "en" else importlib.import_module(f".translations.{_lang}", __package__).MESSAGES


def language():
    if _lang is None:
        set_language()
    return _lang


def _(msg, **kwargs):
    """Translation of msg in the current language, formatted with kwargs."""
    if _lang is None:
        set_language()
    text = _catalog.get(msg, msg)
    return text.format(**kwargs) if kwargs else text
