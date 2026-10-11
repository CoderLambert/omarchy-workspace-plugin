"""Automatically associate installed desktop entries with stable window identities."""
import copy
import re
import shutil
import subprocess
import time

from .core import Error, validate


GENERIC_BROWSERS = {"google-chrome", "chromium", "brave-browser", "firefox", "helium", "vivaldi-stable", "microsoft-edge"}
NATIVE_CLASSES = {
    "chatgpt_app": {"chatgpt"},
    "grok_bot": {"grokbot", "grockbot", "grok-bot", "grock-bot"},
    "terminal": {"alacritty", "kitty", "foot", "com.mitchellh.ghostty", "org.wezfurlong.wezterm"},
    "vscode": {"code", "code-oss", "vscodium", "com.visualstudio.code"},
    "wechat": {"wechat", "wechat.exe", "com.tencent.wechat", "weixin", "com.tencent.weixin"},
    "slack": {"slack", "com.slack.slack"},
    "discord": {"discord", "discordcanary", "discordptb", "discorddevelopment", "com.discordapp.discord"},
    "browser": GENERIC_BROWSERS,
}


def command_output(argv):
    try:
        r = subprocess.run(argv, capture_output=True, text=True, timeout=3)
        return r.stdout.strip() if r.returncode == 0 else ""
    except (OSError, subprocess.TimeoutExpired):
        return ""


def is_web(entry):
    text = entry.get("Exec", "")
    return "--app=" in text or "--app-id=" in text or "omarchy-launch-webapp" in text


def native_identity(app_id, value):
    normalized = re.sub(r"[^a-z0-9]", "", value.lower())
    values = {re.sub(r"[^a-z0-9]", "", v) for v in NATIVE_CLASSES.get(app_id, set())}
    if normalized in values:
        return True
    return app_id == "grok_bot" and normalized.endswith(("grokbot", "grockbot"))


def web_identity(app_id, value):
    hosts = {
        "chatgpt_web": ("chatgpt.com",),
        "x": ("x.com", "twitter.com"),
        "discord": ("discord.com", "discordapp.com", "canary.discord.com", "ptb.discord.com"),
        "slack": ("app.slack.com", "slack.com"),
    }.get(app_id, ())
    return bool(hosts and (value.startswith("org.omarchy-workspaces." + app_id) or any(re.search(r"(?:chrome|chromium|brave|msedge)[-_]" + re.escape(host) + r"(?:[_/-]|$)", value, re.I) for host in hosts)))


def entry_identity(entry, value):
    """An installed PWA's --app-id is a stronger identity than its product title."""
    if not entry:
        return False
    app_id = re.search(r"--app-id(?:=|\s+)[\"']?([a-p]{32})(?:[\"']|\s|$)", entry.get("Exec", ""))
    return bool(app_id and re.fullmatch(r"(?:chrome|chromium|brave|msedge)[-_]crx_" + app_id.group(1) + r"(?:[-_].*)?", value, re.I))


def score_entry(app_id, entry, preferred=""):
    entry_id = entry["id"]
    text = (entry_id + " " + entry.get("Name", "")).lower()
    if preferred and entry_id == preferred:
        return 1000
    expressions = {
        "chatgpt_app": r"chatgpt|chat[- ]gpt",
        "chatgpt_web": r"chatgpt|chat[- ]gpt",
        "grok_bot": r"grock?[ -]?bot|grok[ -]?bot",
        "vscode": r"visual studio code|(^|[ .-])code(?:[ .-]|$)|vscodium",
        "wechat": r"wechat|weixin|微信",
        "slack": r"slack",
        "discord": r"discord",
        "x": r"(^|[ /])x(?:\.desktop|$)|twitter",
        "browser": r"google-chrome|chromium|brave|firefox|helium|vivaldi|microsoft-edge",
        "terminal": r"alacritty|kitty|ghostty|wezterm|(^|[ .-])foot(?:[ .-]|$)",
    }
    if not re.search(expressions.get(app_id, r"(?!)"), text):
        return 0
    if app_id == "chatgpt_app" and is_web(entry):
        return 0
    if app_id == "chatgpt_web" and not is_web(entry):
        return 0
    score = 30
    if entry.get("NoDisplay", "false").lower() != "true":
        score += 10
    if "url-handler" in entry_id or "handler" in entry_id:
        score -= 20
    return score


def terminal_preference(manager, entries):
    # xdg-terminal-exec's preference list, without running/opening a terminal.
    for path in [manager.p.config / "xdg-terminals.list", manager.p.config / "hypr/xdg-terminals.list"]:
        if path.is_file():
            for line in path.read_text().splitlines():
                value = line.strip()
                if value and not value.startswith(("#", "+", "-")):
                    entry_id = value.split(":", 1)[0]
                    if any(e["id"] == entry_id for e in entries):
                        return entry_id
    # Preserve the user's currently observed terminal if only one installed type is running.
    classes = {c.get("initialClass", c.get("class", "")).lower() for c in manager.hypr.query("clients")}
    observed = [e["id"] for e in entries if score_entry("terminal", e) and (e.get("StartupWMClass", "").lower() in classes or e["id"].removesuffix(".desktop").lower() in classes)]
    return observed[0] if len(observed) == 1 else ""


def observed_match(manager, app_id, entry=None):
    declared = entry.get("StartupWMClass", "") if entry else ""
    matches = set()
    for client in manager.hypr.query("clients"):
        if not client.get("mapped", True):
            continue
        identity = client.get("initialClass") or client.get("class") or ""
        if (declared and identity == declared) or native_identity(app_id, identity) or web_identity(app_id, identity) or entry_identity(entry, identity):
            if app_id not in ("browser",) and identity.lower() in GENERIC_BROWSERS:
                continue
            if app_id == "chatgpt_app" and web_identity("chatgpt_web", identity):
                continue
            matches.add(identity)
    if declared in matches:
        return {"initial_class": declared}
    return {"initial_class": next(iter(matches))} if len(matches) == 1 else None


def probe(manager, app, app_id, timeout=5, declared=""):
    old = {c.get("address") for c in manager.hypr.query("clients")}
    manager.desktops.launch(app)
    until = time.monotonic() + timeout
    while time.monotonic() < until:
        clients = [c for c in manager.hypr.query("clients") if c.get("mapped", True) and c.get("address") not in old]
        identities = {c.get("initialClass") or c.get("class") for c in clients}
        identities = {value for value in identities if value and ((declared and value == declared) or native_identity(app_id, value) or web_identity(app_id, value))}
        if app_id != "browser":
            identities = {v for v in identities if v.lower() not in GENERIC_BROWSERS}
        if len(identities) == 1:
            return {"initial_class": next(iter(identities))}
        time.sleep(0.15)
    return None


def discover(manager, config, presets, preferred_browser=None):
    config = copy.deepcopy(config)
    entries = manager.desktops.inventory()
    browser = preferred_browser if preferred_browser is not None else command_output(["xdg-settings", "get", "default-web-browser"])
    terminal = terminal_preference(manager, entries)
    statuses = []
    for app_id, name, workspace, _, shortcuts in presets:
        if app_id in config["apps"] or app_id in config["aliases"]:
            statuses.append((name, "保留现有设置"))
            continue
        before = copy.deepcopy(config)
        try:
            preferred = browser if app_id == "browser" else terminal if app_id == "terminal" else ""
            candidates = sorted([(score_entry(app_id, e, preferred), e) for e in entries if score_entry(app_id, e, preferred)], key=lambda x: x[0], reverse=True)
            entry = candidates[0][1] if candidates and (len(candidates) == 1 or candidates[0][0] > candidates[1][0]) else None
            app = {"name": name, "workspace": workspace, "shortcuts": shortcuts, "replace_shortcuts": bool(shortcuts)}
            if app_id == "tmux":
                if not shutil.which("tmux") or not shutil.which("omarchy-launch-tui"):
                    statuses.append((name, "未安装，跳过"))
                    continue
                identity = "org.omarchy-workspaces.tmux"
                app["command"] = ["omarchy-launch-tui", "--app-id=" + identity, "tmux", "new-session", "-A", "-s", "Work"]
                app["matches"] = [{"initial_class": identity}]
                app["icon"] = "utilities-terminal"
            elif entry:
                app["desktop"] = entry["id"]
                match = observed_match(manager, app_id, entry)
                declared = entry.get("StartupWMClass")
                if not match and declared and (app_id == "browser" or declared.lower() not in GENERIC_BROWSERS):
                    match = {"initial_class": declared}
                if not match:
                    print(f"正在识别 {name}……", flush=True)
                    match = probe(manager, app, app_id, declared=declared or "")
                if not match:
                    statuses.append((name, "请打开应用后再点“自动识别”"))
                    continue
                app["matches"] = [match]
            elif app_id in ("chatgpt_web", "x") and shutil.which("omarchy-launch-webapp"):
                app["command"] = ["omarchy-launch-webapp", "https://chatgpt.com" if app_id == "chatgpt_web" else "https://x.com/"]
                match = observed_match(manager, app_id)
                if not match:
                    print(f"正在识别 {name}……", flush=True)
                    match = probe(manager, app, app_id)
                if not match:
                    statuses.append((name, "请打开独立网页窗口后再点“自动识别”"))
                    continue
                app["matches"] = [match]
            else:
                statuses.append((name, "未找到应用，跳过"))
                continue
            used = next((key for key, value in config["apps"].items() if app.get("desktop") and value.get("desktop") == app["desktop"]), None)
            if used:
                config["aliases"][app_id] = used
                config["apps"][used]["shortcuts"] = list(dict.fromkeys(config["apps"][used].get("shortcuts", []) + shortcuts))
                config["apps"][used]["replace_shortcuts"] = True
            else:
                config["apps"][app_id] = app
            validate(config)
            statuses.append((name, f"工作区 {workspace}"))
        except (Error, OSError) as exc:
            config = before
            statuses.append((name, "暂未识别，保留原来的启动方式"))
    return config, statuses
