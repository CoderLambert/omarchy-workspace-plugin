"""Resolve an application name to an installed entry, executable and window."""
import os
import re
import shutil
from pathlib import Path

from .core import Error, ID
from .discover import GENERIC_BROWSERS, entry_identity, is_web


def normalized(value):
    return re.sub(r'[\W_]+', '', value.casefold())


def app_key(value):
    key = re.sub(r'[^a-z0-9_-]+', '_', value.lower()).strip('_')
    if key and not key[0].isalpha():
        key = 'app_' + key
    if not ID.fullmatch(key):
        raise Error('无法生成应用 ID；请使用英文应用名，例如 obsidian')
    return key


def names(entry):
    return [v for k, v in entry.items() if k == 'Name' or k.startswith('Name[')]


def find_entries(entries, query):
    term = normalized(query)
    scored = []
    for entry in entries:
        stem = entry['id'].removesuffix('.desktop')
        fields = names(entry)
        if re.search(r'(?:url|protocol)[ _-]?handler', stem + ' ' + ' '.join(fields), re.I):
            continue
        score = 100 if term in [normalized(v) for v in fields] else 0
        if term in (normalized(stem), normalized(stem.split('.')[-1])):
            score = max(score, 95)
        if term and not score and any(term in normalized(v) for v in [stem, *fields]):
            score = 40
        if score:
            scored.append((score, entry))
    if not scored:
        return []
    best = max(score for score, _ in scored)
    return [entry for score, entry in scored if score == best]


def executable(query):
    path = Path(query).expanduser()
    if '/' in query:
        if path.is_file() and os.access(path, os.X_OK):
            return str(path.resolve())
        return None
    return shutil.which(query) or shutil.which(query.lower())


def window_matches(clients, query, entry=None, command=None):
    declared = entry.get('StartupWMClass', '') if entry else ''
    terms = [query]
    if entry:
        stem = entry['id'].removesuffix('.desktop')
        terms += names(entry) + [stem, stem.split('.')[-1]]
    if command:
        terms += [Path(command).stem]
    terms = {normalized(v) for v in terms if v}
    scored = []
    for client in clients:
        if not client.get('mapped', True):
            continue
        identity = client.get('initialClass') or client.get('class') or ''
        if not identity:
            continue
        generic = identity.lower() in GENERIC_BROWSERS
        if generic and (not entry or is_web(entry)):
            continue
        score = 1000 if declared and identity.casefold() == declared.casefold() else 0
        if entry_identity(entry, identity):
            score = 1100
        if normalized(identity) in terms:
            score = max(score, 100)
        if normalized(identity.split('.')[-1]) in terms:
            score = max(score, 90)
        if score:
            field = 'initial_class' if client.get('initialClass') else 'class'
            scored.append((score, {field:identity}))
    if scored:
        best = max(score for score, _ in scored)
        result = []
        for score, match in scored:
            if score == best and match not in result:
                result.append(match)
        return result
    if declared and declared.lower() not in GENERIC_BROWSERS:
        return [{'initial_class':declared}]
    return []
