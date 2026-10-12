"""One-request/one-JSON-response bridge; no terminal input and no shell eval."""
import contextlib
import io
import json
import re
import subprocess
from pathlib import Path

from . import __version__
from .build import source_build, backend_build, fingerprint
from .core import Error, Paths, empty_config, load, lock, owner
from .manager import BEGIN, END, Manager
from .plugin import backend_version, terminal, directory


def status(manager, source_root=None):
    p = manager.p
    revision = manager.revision()
    issues = []
    rules_ready = True
    config = empty_config()
    if p.file.exists():
        try:
            config = load(p.file)
        except (Error, OSError, ValueError) as exc:
            issues.append(str(exc))
            rules_ready = False
    state = {"files": {}}
    try:
        state = manager.state()
        for target, record in state["files"].items():
            path = Path(target)
            if not path.exists():
                issues.append(f"受管文件缺失：{path}")
                rules_ready = False
            elif record.get("main"):
                source = path.read_text()
                if source.count(BEGIN) != 1 or source.count(END) != 1:
                    issues.append(f"Hyprland 配置的工作区加载入口缺失或损坏：{path}")
                    rules_ready = False
            elif not record.get("main"):
                try:
                    manager.check_owned(path, record)
                except Error as exc:
                    issues.append(str(exc))
    except (Error, OSError, ValueError) as exc:
        issues.append(str(exc))
        rules_ready = False
    clients = []
    try:
        clients = manager.hypr.query("clients")
        errors = manager.hypr.call("configerrors")
        if errors not in ("", "[]"):
            issues.append("Hyprland 配置错误：" + errors)
            rules_ready = False
    except Error as exc:
        issues.append(str(exc))
        rules_ready = False
    apps = []
    for app_id, app in config["apps"].items():
        hits = [client for client in clients if owner(config, client) == app_id]
        apps.append({"id": app_id, "name": app.get("name", app_id), "workspace": app["workspace"],
                     "existing_window": app.get("existing_window", config["defaults"].get("existing_window", "focus")),
                     "shortcuts": app.get("shortcuts", []), "windows": len(hits),
                     "windowWorkspaces": sorted({str(c.get("workspace", {}).get("name", "?")) for c in hits})})
    installed = backend_version(p)
    if source_root is None:
        plugin_root = directory(p)
        expected_build = source_build(plugin_root) if plugin_root.is_dir() else fingerprint(Path(__file__).parent)
    else:
        expected_build = source_build(source_root)
    installed_build = backend_build(p)
    pending = manager.journal.exists()
    if pending:
        issues.append("上次配置事务被中断，请点击“恢复事务”")
    return {"version": __version__, "backendVersion": installed, "installed": bool(installed),
            "buildId": expected_build, "backendBuildId": installed_build,
            "needsInstall": installed != __version__ or not expected_build or installed_build != expected_build, "active": "config" in state and not pending and rules_ready,
            "draft": p.file.exists() and config != state.get("config"), "pending": pending,
            "configPath": str(p.file), "revision": revision, "issues": issues,
            "apps": sorted(apps, key=lambda app: (app["workspace"], app["name"].casefold()))}


def expected(request):
    value = request.get("revision")
    if not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{64}", value):
        raise Error("缺少有效配置版本，请刷新面板后重试")
    return value


def app_key(request, config):
    value = request.get("app_id")
    if not isinstance(value, str) or value not in config["apps"]:
        raise Error("应用未登记，请刷新列表")
    return value


def special_opt_in(request):
    value = request.get("include_special", False)
    if type(value) is not bool:
        raise Error("包含临时工作区必须是布尔值")
    return value


def execute(request, manager, source_root):
    if not isinstance(request, dict) or not isinstance(request.get("action"), str):
        raise Error("无效面板请求")
    action = request["action"]
    if action == "status":
        return ""
    if action == "install":
        from .installer import install
        result = install(source_root, backend_only=True)
        return "后端与菜单已就绪。首次使用请点击“自动预设”或“新增应用”。" + "\n".join(result["warnings"])
    if (backend_version(manager.p) != __version__ or not source_build(source_root)
            or backend_build(manager.p) != source_build(source_root)):
        raise Error("插件与后端版本或构建不同，请先点击“安装 / 更新后端”")
    if action == "terminal":
        view = request.get("view")
        if view not in ("setup", "add", "advanced", "doctor"):
            raise Error("不支持的终端操作")
        terminal(manager.p, view)
        return "已打开终端，完成操作后点击面板的“刷新”。"
    if action == "doctor":
        from .cli import doctor
        report = io.StringIO()
        with contextlib.redirect_stdout(report):
            doctor(manager)
        return report.getvalue().strip()
    if action == "recover":
        return "已恢复中断的配置事务" if manager.recover() else "没有需要恢复的事务"
    if action == "reset":
        manager.uninstall(expected_revision=expected(request))
        return "已撤销工作区规则与应用入口接管；保留插件、程序和分配表，可点击“应用配置”恢复。"
    if action == "launch":
        return manager.launch(app_key(request, manager.applied_config()))
    if action == "arrange":
        moved = manager.arrange(include_special=special_opt_in(request))
        return f"已整理 {len(moved)} 个窗口"
    if action not in ("set", "remove", "apply", "adopt"):
        raise Error("不支持的面板操作")
    if action == "set":
        special_opt_in(request)
    revision = expected(request)
    config = load(manager.p.file) if manager.p.file.exists() else empty_config()
    if action in ("set", "remove"):
        key = app_key(request, config)
        if manager.state().get("config") not in (None, config):
            raise Error("apps.toml 有尚未应用的修改，请先应用配置或修复草稿，再修改应用")
        if action == "set":
            workspace = request.get("workspace")
            behavior = request.get("existing_window")
            if type(workspace) is not int or not 1 <= workspace <= 999:
                raise Error("工作区必须是 1–999 的整数")
            if behavior not in ("focus", "move"):
                raise Error("窗口复用方式必须是 focus 或 move")
            config["apps"][key].update(workspace=workspace, existing_window=behavior)
        else:
            del config["apps"][key]
            config["aliases"] = {alias: target for alias, target in config["aliases"].items() if target != key}
        manager.apply(config, expected_revision=revision)
        if action == "set" and request.get("move_existing", True):
            try:
                manager.arrange(app_id=key, include_special=special_opt_in(request))
            except Error as exc:
                return f"配置已保存，但已有窗口移动失败：{exc}。刷新后可重试整理窗口。"
        return "工作区和复用方式已保存" if action == "set" else "已取消管理并恢复该应用原入口"
    manager.apply(config, adopt=action == "adopt",
                  text=manager.p.file.read_text() if manager.p.file.exists() else None,
                  expected_revision=revision)
    return "已采用当前外部改动并重新应用配置" if action == "adopt" else "已应用配置"


def respond(request, source_root, manager=None):
    manager = manager or Manager(Paths())
    try:
        # A stale or external second panel never queues an unseen mutation.
        with lock(manager.p.state / "gui.lock", blocking=False) as acquired:
            if not acquired:
                raise Error("另一项工作区操作正在执行，请稍后刷新")
            message = execute(request, manager, source_root)
            current = status(manager, source_root)
        return {"ok": True, "message": message, "state": current}
    except (Error, OSError, ValueError, TypeError, KeyError, subprocess.TimeoutExpired) as exc:
        result = {"ok": False, "message": str(exc)}
        try:
            result["state"] = status(manager, source_root)
        except (Error, OSError, ValueError, TypeError, KeyError):
            pass
        return result


def main(source_root, argv):
    try:
        if len(argv) != 1 or len(argv[0]) > 32768:
            raise Error("桥接接口要求一个 JSON 请求参数")
        request = json.loads(argv[0])
        response = respond(request, source_root)
    except (Error, ValueError) as exc:
        response = {"ok": False, "message": str(exc)}
    print(json.dumps(response, ensure_ascii=False))
    return 0 if response["ok"] else 1
