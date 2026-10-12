"""Offline, user-scoped installation of the CLI and native Omarchy plugin."""
import argparse
import hashlib
import json
import os
import shlex
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from . import __version__
from .build import source_build
from .core import Error, Paths, atomic, lock
from .desktop import exec_line
from .manager import restore, snapshot
from .menu import locations, register as register_menu
from .plugin import LAUNCHER_MARKER, PLUGIN_ID, directory, refresh_plugin, overlay_launcher


def payload_files(root):
    """One explicit file list shared by installation and release packaging."""
    files = []
    for pattern in ("*.md", "build_*.py", "manifest.json", "LICENSE", "Panel.qml", "install.sh", "uninstall.sh"):
        files.extend(root.glob(pattern))
    for folder, pattern in (("src", "*.py"), ("scripts", "*.py"), ("tests", "*.py"),
                            ("qml", "*.qml"), ("qml", "*.js"), ("tests", "*.qml"), ("docs", "*.md"), ("examples", "*.toml"),
                            ("reference", "*")):
        files.extend((root / folder).rglob(pattern))
    result = []
    for path in sorted(set(files)):
        if path.is_symlink():
            raise Error(f"源码包含符号链接，未安装：{path}")
        if path.is_file() and "__pycache__" not in path.parts:
            result.append(path)
    return result


def hashes(root):
    return {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in root.rglob("*") if p.is_file() and p.name != ".ows-install.json"
            and "__pycache__" not in p.parts}


def check_target(path):
    if path.is_symlink():
        raise Error(f"安装目标是符号链接，未覆盖：{path}")
    if path.exists() and not path.is_dir():
        raise Error(f"安装目标不是目录：{path}")
    if path.exists() and any(p.is_symlink() for p in path.rglob("*")):
        raise Error(f"安装目标包含符号链接，未覆盖：{path}")


def validate_source(root):
    manifest = json.loads((root / "manifest.json").read_text())
    if manifest.get("id") != PLUGIN_ID or manifest.get("version") != __version__:
        raise Error("插件 manifest 与后端版本不一致")
    if manifest.get("schemaVersion") != 1 or manifest.get("entryPoints") != {"panel": "Panel.qml"}:
        raise Error("插件 manifest 不符合本工具入口约定")
    for needed in ("Panel.qml", "scripts/bridge.py", "src/omarchy_workspaces/cli.py"):
        if not (root / needed).is_file():
            raise Error(f"源码包不完整，缺少 {needed}")
    return payload_files(root)


def install(root, *, cli_only=False, backend_only=False):
    root = Path(root).resolve()
    paths = Paths()
    for command in ("hyprctl", "gtk-launch", "omarchy-launch-tui"):
        if not shutil.which(command):
            hint = "（sudo pacman -S --needed gtk3）" if command == "gtk-launch" else ""
            raise Error(f"缺少 {command}{hint}，请在 Omarchy 桌面中安装")
    files = validate_source(root)
    native = bool(shutil.which("omarchy-shell") and shutil.which("omarchy-plugin-validate"))
    install_plugin = native and not cli_only and not backend_only
    plugin = directory(paths)
    same_plugin = plugin.resolve() == root
    runtime = paths.data / "omarchy-workspaces"
    desktop = paths.apps / "ows-config.desktop"
    warnings = []
    if not native and not cli_only and not backend_only:
        warnings.append("未检测到 Omarchy 原生插件命令，已安装命令行版；GUI 入口将回退到终端。")
    if install_plugin:
        checked = subprocess.run(["omarchy-plugin-validate", str(root)], capture_output=True,
                                 text=True, timeout=20)
        if checked.returncode:
            raise Error("Omarchy 插件验证未通过：" + (checked.stderr or checked.stdout).strip())
    with lock(paths.state / "install.lock"), lock(paths.state / "apply.lock"):
        if (paths.state / "pending.json").exists():
            # Only program/menu files are installed here. Leave every core
            # transaction target untouched so a missing/old backend can be
            # repaired before its interrupted configuration is recovered.
            warnings.append("发现中断的配置事务，已原样保留。安装后请先执行 omarchy-workspaces recover，再应用配置。")
        preserve_launcher = overlay_launcher(paths.binary)
        for path, marker in ((paths.binary, LAUNCHER_MARKER), (desktop, "X-Omarchy-Workspaces=true")):
            if path == paths.binary and preserve_launcher:
                continue
            if path.is_symlink() or (path.exists() and (not path.is_file() or marker not in path.read_text())):
                raise Error(f"已有同名非受管文件或符号链接，停止覆盖：{path}")
        check_target(runtime)
        if runtime.exists() and not (runtime / "omarchy_workspaces/__init__.py").is_file():
            raise Error(f"已有同名非受管目录，停止覆盖：{runtime}")
        if install_plugin and not same_plugin:
            check_target(plugin)
            if plugin.exists():
                try:
                    owned = json.loads((plugin / ".ows-install.json").read_text())
                except (OSError, ValueError) as exc:
                    raise Error("已有手动安装或 Git 管理的插件目录；请在该目录运行 install.sh --backend-only，或先备份并用 omarchy plugin remove 移除 UI") from exc
                if (plugin / ".git").exists() or owned.get("id") != PLUGIN_ID or owned.get("files") != hashes(plugin):
                    raise Error("插件目录包含本地改动或由 Git 管理，未覆盖；请先备份并核对插件源码")
        before = {p: snapshot(p) for p in (paths.binary, desktop, *locations(paths))}
        swapped = []
        runtime.parent.mkdir(parents=True, exist_ok=True)
        stage_root = Path(tempfile.mkdtemp(prefix=".ows-runtime-", dir=runtime.parent))
        plugin_work = None
        try:
            staged_runtime = stage_root / "runtime"
            staged_runtime.mkdir()
            shutil.copytree(root / "src/omarchy_workspaces", staged_runtime / "omarchy_workspaces",
                            ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
            for path in files:
                relative = path.relative_to(root)
                if relative == Path("LICENSE") or (relative.suffix == ".md" and (len(relative.parts) == 1 or relative.parts[0] == "docs")):
                    target = staged_runtime / relative
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(path, target)
            (staged_runtime / "installation.json").write_text(json.dumps({"version": __version__, "buildId": source_build(root), "plugin_id": PLUGIN_ID,
                                                                        "plugin_path": str(plugin)}, indent=2))
            if install_plugin and not same_plugin:
                plugin.parent.mkdir(parents=True, exist_ok=True)
                # Stage outside plugins/ so the watcher never discovers half a plugin.
                plugin_work = Path(tempfile.mkdtemp(prefix=".ows-plugin-", dir=plugin.parent.parent))
                staged_plugin = plugin_work / "plugin"
                staged_plugin.mkdir()
                for path in files:
                    target = staged_plugin / path.relative_to(root)
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(path, target)
                (staged_plugin / ".ows-install.json").write_text(json.dumps({"id": PLUGIN_ID, "files": hashes(staged_plugin)}))
            def swap(target, stage, backup):
                existed = target.exists()
                if existed:
                    os.replace(target, backup)
                try:
                    os.replace(stage, target)
                except BaseException:
                    if existed:
                        os.replace(backup, target)
                    raise
                swapped.append((target, backup, existed))
            swap(runtime, staged_runtime, stage_root / "old-runtime")
            if install_plugin and not same_plugin:
                swap(plugin, staged_plugin, plugin_work / "old-plugin")
            code = "import sys; sys.dont_write_bytecode=True; sys.path.insert(0, " + repr(str(runtime)) + "); from omarchy_workspaces.cli import main; sys.exit(main())"
            launcher = "#!/bin/sh\n# " + LAUNCHER_MARKER + "\nexec python3 -B -c " + shlex.quote(code) + ' "$@"\n'
            if not preserve_launcher:
                atomic(paths.binary, launcher.encode(), 0o755)
            entry = ("[Desktop Entry]\nType=Application\nName=工作区配置\nName[en]=Workspace Settings\n"
                     "Comment=原生工作区面板、应用分配与窗口复用\nIcon=preferences-desktop\nTerminal=false\n"
                     "X-Omarchy-Workspaces=true\nCategories=Settings;\nExec=" + exec_line([paths.binary, "gui"]) + "\n")
            atomic(desktop, entry.encode(), 0o644)
            if not register_menu(paths):
                warnings.append("菜单刷新未成功；进入桌面后执行 omarchy-menu refresh。")
        except BaseException:
            for path, previous in before.items():
                restore(path, previous)
            for target, backup, existed in reversed(swapped):
                shutil.rmtree(target)
                if existed:
                    os.replace(backup, target)
            raise
        finally:
            shutil.rmtree(stage_root, ignore_errors=True)
            if plugin_work:
                shutil.rmtree(plugin_work, ignore_errors=True)
    if install_plugin and not refresh_plugin(enable=True):
        warnings.append(f"插件已安装，Shell 尚未启用；进入桌面后运行 omarchy-shell shell rescanPlugins，再运行 omarchy plugin enable {PLUGIN_ID}。")
    return {"version": __version__, "binary": str(paths.binary), "pluginInstalled": install_plugin or plugin.is_dir(),
            "warnings": warnings}


def main(root, argv=None):
    parser = argparse.ArgumentParser(description="安装 Omarchy Workspaces 原生插件（默认保留现有应用配置，不自动扫描）")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--cli-only", action="store_true", help="只安装命令行和菜单入口，不复制或启用插件")
    mode.add_argument("--backend-only", action="store_true", help="为已添加的原生插件安装/更新后端和菜单，不改动插件目录")
    setup = parser.add_mutually_exclusive_group()
    setup.add_argument("--setup", action="store_true", help="安装后自动识别预设应用并应用 1/2/3/4 工作区分配")
    setup.add_argument("--no-setup", action="store_true", help="保留配置、不扫描应用（默认，兼容旧安装命令）")
    args = parser.parse_args(argv)
    try:
        result = install(root, cli_only=args.cli_only, backend_only=args.backend_only)
        print(f"已安装 Omarchy Workspaces {result['version']}：{result['binary']}")
        for warning in result["warnings"]:
            print(warning)
        if args.setup:
            return subprocess.run([result["binary"], "setup"], check=False).returncode
        print("现有分配与生效规则已保留。打开系统菜单 → 工作区配置，或运行 omarchy-workspaces gui。")
        print("首次使用可在面板选择“自动预设”，或运行 omarchy-workspaces setup。")
        return 0
    except (Error, OSError, ValueError, subprocess.TimeoutExpired) as exc:
        print(f"安装失败：{exc}", file=sys.stderr)
        return 1
