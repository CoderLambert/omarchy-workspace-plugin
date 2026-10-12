"""CLI and a searchable terminal configuration menu."""
import argparse
import copy
import json
import os
import re
import shutil
import sys
import time
from pathlib import Path

from . import __version__
from .core import binding_shortcut, key_identity, Error, Paths, atomic, dumps, empty_config, load, owner, validate
from .desktop import parse
from .hypr import detect, generate, binding_owned, binding_signature
from .manager import BEGIN, END, Manager
from .discover import discover
from .menu import check as check_menu, register as register_menu, unregister as unregister_menu
from .registration import app_key, executable, find_entries, window_matches
from .plugin import open_gui, remove_installed_plugin


PRESETS = [
    ("chatgpt_app", "ChatGPT App", 1, "chatgpt", []),
    ("grok_bot", "Grok Bot", 1, "grok", []),
    ("chatgpt_web", "ChatGPT 网页", 1, "chatgpt", ["CTRL + SHIFT + A"]),
    ("terminal", "终端", 2, "terminal", ["SUPER + Return"]),
    ("tmux", "Tmux", 2, "tmux", ["SUPER + ALT + Return"]),
    ("vscode", "VS Code", 2, "code", ["SUPER + SHIFT + N"]),
    ("browser", "浏览器", 3, "chrome", ["SUPER + SHIFT + Return", "SUPER + SHIFT + B"]),
    ("wechat", "WeChat", 4, "wechat", []),
    ("slack", "Slack", 4, "slack", []),
    ("x", "X", 4, "x", ["SUPER + SHIFT + X"]),
    ("discord", "Discord", 4, "discord", []),
]


def choose(title, values, label=str, search=""):
    if not values:
        raise Error("没有可选项；先打开应用，再回来登记窗口")
    term = search
    while True:
        selected = [v for v in values if term.lower() in label(v).lower()]
        print(f"\n{title}（输入名称搜索，/ 清除，q 跳过）")
        if not selected:
            print("没有搜索结果。")
        for i, value in enumerate(selected[:80], 1):
            print(f"  {i:2}. {label(value)}")
        if len(selected) > 80:
            print(f"共 {len(selected)} 项；输入 /关键词 缩小范围。")
        value = input("选择: ").strip()
        if value.lower() == "q":
            return None
        if value.startswith("/"):
            term = value[1:]
        elif value.isdigit() and 1 <= int(value) <= min(80, len(selected)):
            return selected[int(value) - 1]
        elif value and not value.isdigit():
            term = value


def prompt(title, default=""):
    result = input(f"{title}" + (f" [{default}]" if default != "" else "") + ": ").strip()
    return result or str(default)


def number(title, default):
    value = prompt(title, default)
    if not value.isdigit() or not 1 <= int(value) <= 999:
        raise Error("工作区应为 1–999 的整数")
    return int(value)


def capture(manager):
    clients = manager.hypr.query("clients")
    chosen = choose("选择该应用的主窗口（可先打开应用，回到这里重试）", [c for c in clients if c.get("mapped", True)], lambda c: f"{c.get('class')} | {c.get('title')} | 工作区 {c.get('workspace', {}).get('name')} | {c.get('address')}")
    if chosen is None:
        return None
    initial = chosen.get("initialClass") or chosen.get("class")
    if not initial:
        raise Error("该窗口没有应用身份，无法安全登记")
    result = {"initial_class": initial}
    print(f"登记精确身份：{json.dumps(result, ensure_ascii=False)}")
    if initial.lower() in {"google-chrome", "chromium", "brave-browser", "firefox", "helium", "vivaldi-stable"}:
        print("这是通用浏览器身份。若登记 ChatGPT/X/Slack 网页，请使用独立 Web App 选项，避免把普通浏览器也移动过去。")
    return result


def register(manager, config, app_id=None, preset=None):
    if preset:
        app_id, name, workspace, search, shortcuts = preset
    else:
        app_id = app_key(app_id or prompt("应用 ID（小写字母、数字、下划线）"))
        name = prompt("菜单名称", app_id)
        workspace, search, shortcuts = 2, "", []
    if app_id in config["apps"] or app_id in config["aliases"]:
        print(f"{app_id} 已登记，使用 config 或 set 修改。")
        return
    if app_id == "chatgpt_web" and "chatgpt_app" in config["apps"]:
        print("1. 与 ChatGPT App 复用同一窗口  2. 独立网页窗口  q. 跳过")
        choice = prompt("选择", "1")
        if choice == "1":
            app = config["apps"]["chatgpt_app"]
            app["shortcuts"] = list(dict.fromkeys(app.get("shortcuts", []) + shortcuts))
            app["replace_shortcuts"] = False
            app.setdefault("replace_shortcut_keys", [])
            config["aliases"][app_id] = "chatgpt_app"
            return
        if choice == "q":
            return
    print(f"\n{name} → 默认工作区 {workspace}")
    print("1. 选择已安装的应用入口与窗口  2. 独立 Web App  3. 指定 argv 命令与窗口  q. 跳过")
    if app_id == "tmux":
        print("4. 专用 tmux 终端（固定窗口身份，复用 Work 会话）")
    default = "4" if app_id == "tmux" else "2" if app_id in ("chatgpt_web", "x") else "1"
    kind = prompt("入口类型", default)
    if kind == "q":
        return
    app = {"name": name, "workspace": workspace, "shortcuts": shortcuts, "replace_shortcuts": False}
    if kind == "4" and app_id == "tmux":
        if not shutil.which("omarchy-launch-tui") or not shutil.which("tmux"):
            raise Error("缺少 omarchy-launch-tui 或 tmux")
        identity = "org.omarchy-workspaces.tmux"
        app["command"] = ["omarchy-launch-tui", f"--app-id={identity}", "tmux", "new-session", "-A", "-s", "Work"]
        app["matches"] = [{"initial_class": identity}]
        app["icon"] = "utilities-terminal"
    elif kind == "2":
        if not shutil.which("omarchy-launch-webapp"):
            raise Error("缺少 omarchy-launch-webapp")
        url = prompt("Web App URL", "https://chatgpt.com" if "chatgpt" in app_id else "https://x.com" if app_id == "x" else "")
        if not re.match(r"^https?://[^\s]+$", url):
            raise Error("请输入完整 http(s) URL")
        identity = "org.omarchy-workspaces." + app_id
        app["command"] = ["omarchy-launch-webapp", url, "--class=" + identity]
        app["matches"] = [{"initial_class": identity}]
        before = {c.get("address") for c in manager.hypr.query("clients")}
        print("正在打开独立 Web App 并读取实际窗口身份……")
        manager.desktops.launch(app)
        deadline = time.monotonic() + config["defaults"].get("launch_timeout", 20)
        found = []
        while time.monotonic() < deadline:
            clients = manager.hypr.query("clients")
            found = [c for c in clients if c.get("mapped", True) and (c.get("address") not in before or c.get("initialClass") == identity)]
            if found:
                break
            time.sleep(0.2)
        chosen = choose("选择刚打开的 Web App 窗口", found or manager.hypr.query("clients"), lambda c: f"{c.get('initialClass')} | {c.get('title')} | {c.get('address')}")
        if chosen is None:
            return
        actual = chosen.get("initialClass") or chosen.get("class")
        if not actual or actual.lower() in {"google-chrome", "chromium", "brave-browser", "firefox", "helium", "vivaldi-stable"}:
            raise Error("此 Web App 仍共享普通浏览器身份；请先安装独立 PWA，然后用已安装应用入口登记")
        app["matches"] = [{"initial_class": actual}]
        print(f"采用实际窗口身份：{actual}")
    elif kind in ("1", "3"):
        if kind == "1":
            entries = manager.desktops.inventory()
            chosen = choose("选择原始应用入口", entries, lambda e: f"{e.get('Name', '')} | {e['id']}", search)
            if chosen is None:
                return
            app["desktop"] = chosen["id"]
            app["name"] = chosen.get("Name", name)
        else:
            try:
                app["command"] = json.loads(prompt('命令 JSON argv，例如 ["code", "--new-window"]'))
            except ValueError as exc:
                raise Error("命令必须是 JSON 数组，无须 shell 引号") from exc
        match = capture(manager)
        if match is None:
            return
        app["matches"] = [match]
        if app_id not in ("browser",) and match["initial_class"].lower() in {"google-chrome", "chromium", "brave-browser", "firefox", "helium", "vivaldi-stable"}:
            raise Error("此应用与普通浏览器共享身份，请使用独立 Web App 入口")
    else:
        raise Error("入口类型无效")
    app["workspace"] = number("工作区", workspace)
    config["apps"][app_id] = app
    try:
        validate(config)
    except Error:
        del config["apps"][app_id]
        raise


def quick_register(manager, config, query=None, workspace=None, command=None):
    query = (query or prompt('应用名称，例如 Obsidian')).strip()
    if not query:
        return None
    requested_id = app_key(query) if re.search(r'[a-zA-Z]', query) else None
    existing = config['aliases'].get(requested_id, requested_id)
    if existing in config['apps']:
        if workspace is None:
            print(f'{query} 已登记到工作区 {config["apps"][existing]["workspace"]}；可用 set 修改')
            return None
        updated = copy.deepcopy(config)
        updated['apps'][existing]['workspace'] = workspace
        validate(updated)
        config.clear()
        config.update(updated)
        return existing
    entry = None
    if command is None:
        candidates = find_entries(manager.desktops.inventory(), query)
        entry = candidates[0] if len(candidates) == 1 else choose('有多个安装入口，选择一个', candidates, lambda e: f'{e.get("Name", "")} | {e["id"]}') if candidates else None
        if candidates and entry is None:
            return None
    resolved = None if entry else executable(command or query)
    if not entry and not resolved:
        raise Error(f'未找到 {query} 的安装入口或启动命令。可指定 AppImage/程序路径：add {requested_id or "app"} --command /完整路径/程序 --workspace 2')
    if entry:
        used = next((key for key, value in config['apps'].items() if value.get('desktop') == entry['id']), None)
        if used:
            if workspace is None:
                print(f'此应用已登记为 {used}，当前工作区 {config["apps"][used]["workspace"]}；可用 set 修改')
                return None
            updated = copy.deepcopy(config)
            updated['apps'][used]['workspace'] = workspace
            validate(updated)
            config.clear()
            config.update(updated)
            return used
    matches = window_matches(manager.hypr.query('clients'), query, entry, resolved)
    if not matches:
        raise Error(f'已找到启动入口，但尚未确认 {query} 的窗口身份。请先打开该应用，再执行同一条 add 命令')
    match = matches[0] if len(matches) == 1 else choose('找到多个窗口身份，选择应用窗口', matches, lambda m: next(iter(m.values())))
    if match is None:
        return None
    app_id = requested_id or app_key(entry['id'].removesuffix('.desktop').split('.')[-1] if entry else Path(resolved).stem)
    name = entry.get('Name', query) if entry else query
    app = {'name':name, 'workspace':workspace if workspace is not None else number('放到哪个工作区',2), 'matches':[match], 'shortcuts':[]}
    if entry:
        app['desktop'] = entry['id']
    else:
        app['command'] = [resolved]
    updated = copy.deepcopy(config)
    updated['apps'][app_id] = app
    validate(updated)
    config.clear()
    config.update(updated)
    print(f'已识别：{name} → 工作区 {app["workspace"]}')
    return app_id


def show(config):
    for app_id, app in config["apps"].items():
        print(f"{app_id:16} 工作区 {app['workspace']:3}  {app.get('name', app_id)}  {', '.join(app.get('shortcuts', []))}")
    for alias, target in config["aliases"].items():
        print(f"{alias:16} → {target}（共用窗口）")


def apply(manager, config, adopt=False, text=None, expected_revision=None):
    for change in manager.apply(config, adopt, text, expected_revision=expected_revision):
        print("替换快捷键：" + change)
    print("配置已应用；新窗口按规则落位。已有窗口保持当前位置，可执行 arrange 整理。")


def wizard(manager):
    revision = manager.revision()
    config = load(manager.p.file) if manager.p.file.exists() else empty_config()
    print("Omarchy 工作区设置：1 AI / 2 开发 / 3 浏览器 / 4 通信")
    print("请先打开要登记的应用；每项可 q 跳过，之后随时 add。默认快捷键会接管选中应用对应的原绑定。")
    for preset in PRESETS:
        before = copy.deepcopy(config)
        try:
            register(manager, config, preset=preset)
            if config != before:
                # Commit each completed registration; an interrupted setup loses no prior work.
                apply(manager, config, expected_revision=revision)
                revision = manager.revision()
        except Error as exc:
            config = before
            print(f"未登记：{exc}")
    print("初始设置结束。omarchy-workspaces config 可继续修改。")


def advanced_menu(manager):
    while True:
        revision = manager.revision()
        config = load(manager.p.file) if manager.p.file.exists() else empty_config()
        print("\n工作区配置")
        show(config)
        print("1. 添加应用  2. 修改工作区  3. 设置快捷键  4. 复用方式  5. 重新捕获窗口身份")
        print("6. 整理已打开窗口  7. 取消管理  8. 检查配置  9. 应用配置  0. 初始预设登记  q. 退出")
        action = prompt("操作", "q")
        try:
            if action == "q":
                return
            if action == "0":
                wizard(manager)
                continue
            if action == "1":
                register(manager, config)
            elif action in ("2", "3", "4", "5", "7"):
                app_id = choose("选择应用", list(config["apps"]), lambda key: f"{key} | {config['apps'][key].get('name', key)}")
                if not app_id:
                    continue
                app = config["apps"][app_id]
                if action == "2":
                    app["workspace"] = number("工作区", app["workspace"])
                elif action == "3":
                    value = prompt("快捷键（多个用逗号分隔，- 清空）", ",".join(app.get("shortcuts", [])))
                    app.pop("replace_shortcut_keys", None)
                    app["shortcuts"] = [] if value == "-" else [s.strip() for s in value.split(",") if s.strip()]
                    app["replace_shortcuts"] = prompt("若与原绑定冲突，是否接管（yes/no）", "no") == "yes"
                elif action == "4":
                    app["existing_window"] = choose("已有窗口行为", ["focus", "move"], lambda v: "focus: 跳到窗口当前位置" if v == "focus" else "move: 归位后聚焦") or app.get("existing_window", "focus")
                elif action == "5":
                    match = capture(manager)
                    if match:
                        app["matches"] = [match]
                else:
                    remove(config, app_id)
            elif action == "6":
                print("\n".join(manager.arrange()))
                continue
            elif action == "8":
                doctor(manager)
                continue
            elif action != "9":
                continue
            apply(manager, config, expected_revision=revision)
        except Error as exc:
            print(f"操作失败：{exc}")


def review_setup_shortcuts(manager, config, decide=None):
    """Preview every foreign binding; skip it unless explicitly accepted."""
    config = copy.deepcopy(config)
    binds = manager.hypr.query("binds")
    for app_id, app in config["apps"].items():
        kept = []
        previously_approved = {key_identity(k) for k in app.get("replace_shortcut_keys", [])}
        app["replace_shortcuts"] = False
        app["replace_shortcut_keys"] = []
        for key in app.get("shortcuts", []):
            existing = [b for b in binds if binding_shortcut(b)
                        and key_identity(binding_shortcut(b)) == key_identity(key)
                        and not binding_owned(b, manager.p.binary, app_id, app)]
            if existing:
                print(f"\n快捷键冲突 {key}：")
                for b in existing:
                    print(f"  原绑定：{b.get('description') or '(无说明)'} | {b.get('dispatcher')} {b.get('arg', '')}")
                print(f"  新绑定：{manager.p.binary} launch {app_id}")
                accept = decide(key, app_id, existing) if decide else (
                    sys.stdin.isatty() and sys.stdout.isatty()
                    and prompt("明确替换该快捷键？yes/no（no 仅跳过此快捷键）", "no") == "yes")
                if not accept:
                    print("  已跳过冲突快捷键，仍登记应用和工作区。")
                    continue
                app["replace_shortcut_keys"].append(key)
            elif key_identity(key) in previously_approved:
                app["replace_shortcut_keys"].append(key)
            kept.append(key)
        app["shortcuts"] = kept
    return config, binding_signature(binds)


def setup(manager):
    revision = manager.revision()
    config = load(manager.p.file) if manager.p.file.exists() else empty_config()
    print("正在自动设置：1 AI · 2 开发 · 3 浏览器 · 4 通信", flush=True)
    config, statuses = discover(manager, config, PRESETS)
    config, preview = review_setup_shortcuts(manager, config)
    changes = manager.apply(config, expected_revision=revision, expected_bindings=preview)
    manager.arrange()
    for name, status in statuses:
        print(f"  {name}：{status}")
    if changes:
        print("已接管对应快捷键；原绑定在撤销设置后恢复。")
    print("完成。以后在 Omarchy 系统菜单打开“工作区配置”即可修改。")


def menu(manager):
    while True:
        revision = manager.revision()
        config = load(manager.p.file) if manager.p.file.exists() else empty_config()
        print("\n工作区配置")
        for workspace in sorted({app["workspace"] for app in config["apps"].values()}):
            names = [app.get("name", key) for key, app in config["apps"].items() if app["workspace"] == workspace]
            print(f"  工作区 {workspace}：{'、'.join(names)}")
        print("\n1. 修改应用的工作区\n2. 自动识别预设应用\n3. 整理已打开窗口\n4. 撤销全部设置\n5. 新增应用\n0. 退出")
        action = prompt("输入数字", "0")
        try:
            if action in ("0", "q"):
                return
            if action == "1":
                app_id = choose("选择应用", list(config["apps"]), lambda key: config["apps"][key].get("name", key))
                if app_id:
                    app = config["apps"][app_id]
                    app["workspace"] = number("放到哪个工作区", app["workspace"])
                    manager.apply(config, expected_revision=revision)
                    manager.arrange(app_id=app_id)
                    print("已修改并移动窗口。")
            elif action == "2":
                setup(manager)
            elif action == "3":
                manager.arrange()
                print("已整理。")
            elif action == '5':
                added = quick_register(manager, config)
                if added:
                    manager.apply(config, expected_revision=revision)
                    manager.arrange(app_id=added)
            elif action == "4":
                manager.uninstall(expected_revision=revision)
                print("已恢复原来的应用入口和快捷键；分配表和配置界面已保留，可执行 apply 重新启用。")
        except Error as exc:
            print(f"操作失败：{exc}")


def remove(config, app_id):
    if app_id in config["aliases"]:
        del config["aliases"][app_id]
    elif app_id in config["apps"]:
        del config["apps"][app_id]
        config["aliases"] = {key: value for key, value in config["aliases"].items() if value != app_id}
    else:
        raise Error(f"应用未登记：{app_id}")


def doctor(manager):
    print(f"版本 {__version__}; 配置 {manager.p.file}")
    problems = []
    try:
        config = load(manager.p.file)
        backend, main = detect(manager.p, config, manager.hypr)
        print(f"Hyprland: {backend}; 入口 {main}")
        errors = manager.hypr.call("configerrors")
        if errors not in ("", "[]"):
            problems.append(errors)
        if manager.journal.exists():
            problems.append("存在中断事务，执行 recover")
        state = manager.state()
        if state.get("config") != config:
            problems.append("apps.toml 尚未成功应用，与当前生效配置不同")
        if not manager.p.binary.is_file():
            problems.append(f"找不到启动脚本 {manager.p.binary}")
        try:
            check_menu(manager.p)
        except Error as exc:
            problems.append(str(exc))
        for target, record in state["files"].items():
            path = Path(target)
            if not path.exists():
                problems.append(f"受管文件缺失：{path}")
            elif record.get("main"):
                text = path.read_text()
                if text.count(BEGIN) != 1 or text.count(END) != 1:
                    problems.append(f"Hyprland 配置的工具加载入口缺失或损坏：{path}")
            else:
                try:
                    manager.check_owned(path, record)
                except Error as exc:
                    problems.append(str(exc))
        clients = manager.hypr.query("clients")
        for app_id, app in config["apps"].items():
            hits = [c for c in clients if owner(config, c) == app_id]
            print(f"{app_id}: {len(hits)} 个登记窗口；目标工作区 {app['workspace']}")
            if app.get("desktop"):
                manager.desktops.text(app["desktop"], state["files"])
        _, replacements = generate(config, backend, manager.p.binary, manager.hypr.query("binds"))
        for change in replacements:
            print("接管原绑定：" + change)
    except Error as exc:
        problems.append(str(exc))
    for problem in problems:
        print("问题：" + problem)
    if not problems:
        print("配置与受管文件检查通过。0 个窗口仅表示当前未打开，不能证明启动验收通过。")
    return bool(problems)


def parser():
    result = argparse.ArgumentParser(description="Omarchy 工作区与应用窗口复用管理")
    result.add_argument("--version", action="version", version=__version__)
    commands = result.add_subparsers(dest="action", required=True)
    for command in ("setup", "wizard", "list", "doctor", "recover", "windows", "uninstall", "reset", "gui", "repair-menu"):
        commands.add_parser(command)
    sub = commands.add_parser("config")
    sub.add_argument("--advanced", action="store_true")
    sub = commands.add_parser("apply")
    sub.add_argument("--adopt", action="store_true", help="将外部更新后的受管启动项作为新的恢复基线")
    sub = commands.add_parser("arrange")
    sub.add_argument("--dry-run", action="store_true")
    sub.add_argument("--app", help="只整理指定应用")
    sub.add_argument("--include-special", action="store_true", help="明确允许整理 special:* 临时工作区的窗口")
    sub = commands.add_parser("status")
    sub.add_argument("--json", action="store_true", help="输出插件使用的结构化状态")
    sub = commands.add_parser("launch")
    sub.add_argument("app_id")
    sub.add_argument("--new", action="store_true", help="跳过工具的复用逻辑，直接调用原始入口；保留原应用行为")
    sub.add_argument("args", nargs="*")
    sub = commands.add_parser("add")
    sub.add_argument("app_id", nargs="?")
    sub.add_argument('--workspace',type=int,help='指定工作区，省去交互选择')
    sub.add_argument('--command',help='找不到 desktop 时指定可执行程序或 AppImage 路径')
    sub.add_argument('--advanced',action='store_true',help='使用原来的手工入口和窗口登记向导')
    sub = commands.add_parser("remove")
    sub.add_argument("app_id")
    sub = commands.add_parser("alias")
    sub.add_argument("alias")
    sub.add_argument("target")
    sub = commands.add_parser("set")
    sub.add_argument("app_id")
    sub.add_argument("--workspace", type=int)
    sub.add_argument("--existing-window", choices=("focus", "move"))
    sub.add_argument("--shortcut", action="append")
    sub.add_argument("--clear-shortcuts", action="store_true")
    sub.add_argument("--replace-shortcut", action="store_true")
    return result


def main(argv=None):
    args = parser().parse_args(argv)
    p = Paths()
    manager = Manager(p)
    try:
        if args.action == "launch":
            print(manager.launch(args.app_id, args.new, args.args))
        elif args.action == "setup":
            setup(manager)
        elif args.action == "wizard":
            wizard(manager)
        elif args.action == "config":
            advanced_menu(manager) if args.advanced else menu(manager)
        elif args.action == "gui":
            print(open_gui(p))
        elif args.action == "status":
            from .gui import status
            current = status(manager)
            if args.json:
                print(json.dumps(current, ensure_ascii=False, indent=2))
            else:
                print(f"版本 {current['version']}；管理{'生效' if current['active'] else '未启用'}；{len(current['apps'])} 个已登记应用")
                for issue in current['issues']:
                    print('问题：' + issue)
        elif args.action == "repair-menu":
            refreshed = register_menu(p)
            print('已添加 Omarchy 系统菜单：工作区配置' if refreshed else '已添加菜单入口；桌面启动后执行 omarchy-menu refresh')
        elif args.action == "doctor":
            return int(doctor(manager))
        elif args.action == "recover":
            print("已恢复中断事务" if manager.recover() else "没有需要恢复的事务")
        elif args.action == "windows":
            print(json.dumps(manager.hypr.query("clients"), ensure_ascii=False, indent=2))
        elif args.action == "arrange":
            app_id = args.app
            if app_id:
                config = manager.applied_config()
                app_id = config['aliases'].get(app_id, app_id)
                if app_id not in config['apps']:
                    raise Error(f'应用未登记：{app_id}')
            print("\n".join(manager.arrange(args.dry_run, app_id=app_id, include_special=args.include_special)))
        elif args.action == "reset":
            manager.uninstall(expected_revision=manager.revision())
            print("已撤销工作区规则与应用入口接管；保留插件、命令和分配表，执行 apply 可恢复管理。")
        elif args.action == "uninstall":
            manager.uninstall(expected_revision=manager.revision())
            unregister_menu(p)
            for path, marker in ((p.apps / 'ows-config.desktop', 'X-Omarchy-Workspaces=true'),
                                 (p.binary, 'Omarchy Workspaces managed launcher')):
                if path.exists() and not path.is_symlink() and marker in path.read_text():
                    path.unlink()
            message = remove_installed_plugin(p)
            print("已恢复应用入口与快捷键，并移除受管命令和插件入口；保留 apps.toml、后端副本和日志，方便诊断或重新安装。")
            if message:
                print(message)
        else:
            revision = manager.revision()
            config = load(p.file) if p.file.exists() else empty_config()
            added = None
            if args.action == "list":
                show(config)
                return 0
            elif args.action == "add":
                if args.advanced:
                    if args.workspace is not None or args.command is not None:
                        raise Error('--advanced 使用手工向导，不能同时指定 --workspace 或 --command')
                    register(manager, config, args.app_id)
                else:
                    added = quick_register(manager, config, args.app_id, args.workspace, args.command)
                    if not added:
                        return 0
            elif args.action == "remove":
                remove(config, args.app_id)
            elif args.action == "alias":
                config["aliases"][args.alias] = args.target
            elif args.action == "set":
                target = config["aliases"].get(args.app_id, args.app_id)
                if target not in config["apps"]:
                    raise Error(f"应用未登记：{args.app_id}")
                app = config["apps"][target]
                if args.workspace is not None:
                    app["workspace"] = args.workspace
                if args.existing_window:
                    app["existing_window"] = args.existing_window
                if args.shortcut is not None:
                    app.pop("replace_shortcut_keys", None)
                    app["shortcuts"] = args.shortcut
                    app["replace_shortcuts"] = args.replace_shortcut
                elif args.clear_shortcuts:
                    app.pop("replace_shortcut_keys", None)
                    app["shortcuts"] = []
            text = p.file.read_text() if args.action == "apply" and p.file.exists() else None
            apply(manager, config, getattr(args, "adopt", False), text, expected_revision=revision)
            if added:
                manager.arrange(app_id=added)
    except (Error, OSError, ValueError) as exc:
        print(f"错误：{exc}", file=sys.stderr)
        if args.action == "launch" and shutil.which("notify-send"):
            import subprocess
            try:
                subprocess.run(["notify-send", "工作区启动失败", str(exc)], timeout=3, check=False)
            except (OSError, subprocess.TimeoutExpired):
                pass
        return 1
    except (KeyboardInterrupt, EOFError):
        print("\n已退出；已成功应用的配置会保留。", file=sys.stderr)
        return 130
    return 0


if __name__ == "__main__":
    sys.exit(main())
