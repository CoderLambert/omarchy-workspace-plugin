"""Configuration, exact window identity and filesystem primitives (stdlib only)."""
from __future__ import annotations

import contextlib
import fcntl
import json
import os
import re
import tempfile
import tomllib
from pathlib import Path


class Error(RuntimeError):
    pass


def quote(value):
    return json.dumps(value, ensure_ascii=False)


def atomic(path: Path, data: bytes, mode=0o600):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp = tempfile.mkstemp(prefix=".ows-", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as file:
            os.fchmod(file.fileno(), mode)
            file.write(data)
            file.flush()
            os.fsync(file.fileno())
        os.replace(temp, path)
        directory = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)


@contextlib.contextmanager
def lock(path: Path, blocking=True):
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    with path.open("a+") as file:
        os.chmod(path, 0o600)
        try:
            fcntl.flock(file, fcntl.LOCK_EX | (0 if blocking else fcntl.LOCK_NB))
        except BlockingIOError:
            yield False
            return
        try:
            yield True
        finally:
            fcntl.flock(file, fcntl.LOCK_UN)


class Paths:
    def __init__(self):
        self.home = Path.home()
        self.config = Path(os.environ.get("XDG_CONFIG_HOME", self.home / ".config"))
        self.data = Path(os.environ.get("XDG_DATA_HOME", self.home / ".local/share"))
        self.state = Path(os.environ.get("XDG_STATE_HOME", self.home / ".local/state")) / "omarchy-workspaces"
        self.apps = self.data / "applications"
        self.file = self.config / "omarchy-workspaces/apps.toml"
        self.binary = self.home / ".local/bin/omarchy-workspaces"
        runtime = os.environ.get("XDG_RUNTIME_DIR")
        self.runtime = (Path(runtime) if runtime else self.state) / "omarchy-workspaces-locks"
        for path in (self.state, self.runtime):
            path.mkdir(parents=True, exist_ok=True, mode=0o700)
            os.chmod(path, 0o700)


MODS = {"SHIFT": 1, "CTRL": 4, "ALT": 8, "SUPER": 64}
FIELDS = {"class": "class", "initial_class": "initialClass", "initial_title": "initialTitle"}
ID = re.compile(r"^[a-z][a-z0-9_-]{0,63}$")


def shortcut(value):
    if not isinstance(value, str):
        raise Error("快捷键必须是字符串")
    parts = [x.strip() for x in value.split("+")]
    mods = set()
    for part in parts[:-1]:
        part = {"CONTROL": "CTRL", "MOD4": "SUPER"}.get(part.upper(), part.upper())
        if part not in MODS or part in mods:
            raise Error(f"无效快捷键：{value}")
        mods.add(part)
    key = parts[-1]
    if not re.fullmatch(r"(?:[A-Za-z0-9_]+|code:[0-9]+)", key) or key.upper() in MODS:
        raise Error(f"快捷键缺少或包含无效主键：{value}")
    # XKB keysyms are case sensitive for Lua unbind; retain the supplied spelling.
    if len(key) == 1:
        key = key.upper()
    key = {"return": "Return", "enter": "Return", "escape": "Escape", "tab": "Tab"}.get(key.lower(), key)
    return " + ".join([m for m in MODS if m in mods] + [key])


def key_identity(value):
    parts = shortcut(value).split(" + ")
    return sum(MODS[m] for m in parts[:-1]), parts[-1].lower()


def binding_shortcut(bind):
    mask = bind.get("modmask", 0)
    key = bind.get("key") or (f"code:{bind['keycode']}" if bind.get("keycode") else "")
    if not key or mask & ~sum(MODS.values()) or not re.fullmatch(r"(?:[A-Za-z0-9_]+|code:[0-9]+)", key) or key.upper() in MODS:
        return None
    return " + ".join([m for m, bit in MODS.items() if mask & bit] + [key])


def empty_config():
    return {"defaults": {"launch_timeout": 20, "existing_window": "focus", "backend": "auto"}, "apps": {}, "aliases": {}}


def validate(config):
    if not isinstance(config, dict) or set(config) - {"defaults", "apps", "aliases"}:
        raise Error("配置仅允许 defaults、apps、aliases 三个顶层表")
    defaults = config.setdefault("defaults", {})
    apps = config.setdefault("apps", {})
    aliases = config.setdefault("aliases", {})
    if not all(isinstance(v, dict) for v in (defaults, apps, aliases)):
        raise Error("defaults/apps/aliases 必须是表")
    if set(defaults) - {"launch_timeout", "existing_window", "backend", "hypr_config"}:
        raise Error("defaults 存在不支持的字段")
    timeout = defaults.get("launch_timeout", 20)
    if type(timeout) not in (int, float) or not 1 <= timeout <= 120:
        raise Error("launch_timeout 必须在 1–120 秒之间")
    if defaults.get("backend", "auto") not in ("auto", "lua", "conf", "v2"):
        raise Error("backend 必须是 auto/lua/conf/v2")
    if defaults.get("existing_window", "focus") not in ("focus", "move"):
        raise Error("existing_window 必须是 focus 或 move")
    if "hypr_config" in defaults:
        safe_text(defaults["hypr_config"])
    keys, desktop_ids = {}, {}
    for app_id, app in apps.items():
        if not ID.fullmatch(app_id) or not isinstance(app, dict):
            raise Error(f"无效应用 ID：{app_id}")
        if set(app) - {"name", "workspace", "desktop", "command", "matches", "shortcuts", "existing_window", "replace_shortcuts", "replace_shortcut_keys", "menu", "icon"}:
            raise Error(f"{app_id} 存在不支持的字段")
        if type(app.get("workspace")) is not int or not 1 <= app["workspace"] <= 999:
            raise Error(f"{app_id} workspace 必须是 1–999 的整数")
        if bool(app.get("desktop")) == bool(app.get("command")):
            raise Error(f"{app_id} 必须且只能设置 desktop 或 command")
        if "desktop" in app:
            desktop = app["desktop"]
            safe_text(desktop)
            if not re.fullmatch(r"[^/\\]+\.desktop", desktop) or desktop.startswith("ows-"):
                raise Error(f"{app_id} 无效 desktop ID")
            if desktop in desktop_ids:
                raise Error(f"{app_id} 与 {desktop_ids[desktop]} 使用相同入口，请使用 alias")
            desktop_ids[desktop] = app_id
        else:
            command = app["command"]
            if not isinstance(command, list) or not command:
                raise Error(f"{app_id} command 必须是非空 argv 数组")
            for part in command:
                safe_text(part)
        for key in ("name", "icon"):
            if key in app:
                safe_text(app[key])
        for key in ("replace_shortcuts", "menu"):
            if key in app and type(app[key]) is not bool:
                raise Error(f"{app_id} {key} 必须是布尔值")
        if app.get("existing_window", defaults.get("existing_window", "focus")) not in ("focus", "move"):
            raise Error(f"{app_id} 无效 existing_window")
        matches = app.get("matches")
        if not isinstance(matches, list) or not matches:
            raise Error(f"{app_id} 缺少窗口身份 matches")
        for match in matches:
            if not isinstance(match, dict) or set(match) - set(FIELDS) or not (match.get("class") or match.get("initial_class")):
                raise Error(f"{app_id} 匹配必须包含 class 或 initial_class，不能仅匹配标题")
            for value in match.values():
                safe_text(value)
        shortcuts = app.get("shortcuts", [])
        if not isinstance(shortcuts, list):
            raise Error(f"{app_id} shortcuts 必须是数组")
        app["shortcuts"] = [shortcut(s) for s in shortcuts]
        if "replace_shortcut_keys" in app:
            permitted = app["replace_shortcut_keys"]
            if not isinstance(permitted, list):
                raise Error(f"{app_id} replace_shortcut_keys 必须是数组")
            app["replace_shortcut_keys"] = [shortcut(s) for s in permitted]
            if any(key_identity(s) not in {key_identity(k) for k in app["shortcuts"]} for s in app["replace_shortcut_keys"]):
                raise Error(f"{app_id} 只能授权已配置的快捷键")
        for key in app["shortcuts"]:
            identity = key_identity(key)
            if identity in keys:
                raise Error(f"快捷键重复：{key}（{keys[identity]} / {app_id}）")
            keys[identity] = app_id
    # Equal-specificity intersections are ambiguous, including class vs initial_class.
    entries = [(k, m) for k, a in apps.items() for m in a["matches"]]
    for i, (a, x) in enumerate(entries):
        for b, y in entries[i + 1:]:
            if a != b and len(x) == len(y) and not any(x[k] != y[k] for k in x.keys() & y.keys()):
                raise Error(f"{a} / {b} 的窗口身份可能重叠；请使用相同身份字段或更具体的匹配")
    for alias, target in aliases.items():
        if not ID.fullmatch(alias) or alias in apps or not isinstance(target, str) or target not in apps:
            raise Error(f"无效 alias：{alias} -> {target}")
    return config


def safe_text(value):
    if not isinstance(value, str) or not value or any(ord(c) < 32 or ord(c) == 127 for c in value):
        raise Error("配置字段不能为空或包含控制字符")
    return value


def load(path):
    try:
        return validate(tomllib.loads(Path(path).read_text()))
    except (OSError, tomllib.TOMLDecodeError) as exc:
        raise Error(f"读取配置失败：{exc}") from exc


def dumps(config):
    validate(config)
    lines = ["# Omarchy Workspaces — 修改后执行 omarchy-workspaces apply", "[defaults]"]
    for key, value in config["defaults"].items():
        lines.append(f"{key} = {toml_value(value)}")
    lines.extend(["", "[aliases]"])
    for key, value in config["aliases"].items():
        lines.append(f"{key} = {quote(value)}")
    for app_id, app in config["apps"].items():
        lines.extend(["", f"[apps.{app_id}]"])
        for key, value in app.items():
            if key != "matches":
                lines.append(f"{key} = {toml_value(value)}")
        for match in app["matches"]:
            lines.extend(["", f"[[apps.{app_id}.matches]]"])
            lines.extend(f"{key} = {quote(value)}" for key, value in match.items())
    return "\n".join(lines) + "\n"


def toml_value(value):
    if type(value) is bool:
        return "true" if value else "false"
    if isinstance(value, list):
        return "[" + ", ".join(toml_value(v) for v in value) + "]"
    return quote(value)


def matching(match, client):
    return client.get("mapped", True) and all(client.get(FIELDS[k], "") == v for k, v in match.items())


def owner(config, client):
    hits = [(len(m), app_id) for app_id, app in config["apps"].items() for m in app["matches"] if matching(m, client)]
    if not hits:
        return None
    hits.sort(reverse=True)
    if len({app_id for score, app_id in hits if score == hits[0][0]}) > 1:
        raise Error(f"窗口 {client.get('address')} 同时匹配多个应用，拒绝操作")
    return hits[0][1]


def recent(clients):
    def key(client):
        history = client.get("focusHistoryID", -1)
        return (history if isinstance(history, int) and history >= 0 else 10**9, client.get("address", ""))
    return min(clients, key=key) if clients else None
