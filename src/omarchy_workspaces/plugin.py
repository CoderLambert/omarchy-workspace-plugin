"""Omarchy's native plugin entry and safe terminal fallback."""
import json
import shutil
import subprocess

from .core import Error


PLUGIN_ID = "lambert.workspaces"
LAUNCHER_MARKER = "Omarchy Workspaces managed launcher"

# Exact portable launcher deployed by the personal Chezmoi overlay.
OVERLAY_LAUNCHER = '#!/bin/sh\n# managed-by: omarchy-overlay-dotfiles\nexec python3 -B -c \'import sys; from pathlib import Path; sys.path.insert(0, str(Path.home()/".local/share/omarchy-workspaces")); from omarchy_workspaces.cli import main; sys.exit(main())\' "$@"\n'


def overlay_launcher(path):
    """Recognize only the audited regular launcher; never follow symlinks."""
    return not path.is_symlink() and path.is_file() and path.read_text() == OVERLAY_LAUNCHER



def directory(paths):
    # Omarchy v4.0.4 PluginRegistry and plugin CLI use HOME, not XDG_CONFIG_HOME.
    return paths.home / ".config/omarchy/plugins" / PLUGIN_ID


def backend_version(paths):
    import re
    init = paths.data / "omarchy-workspaces/omarchy_workspaces/__init__.py"
    try:
        if paths.binary.is_symlink() or (LAUNCHER_MARKER not in paths.binary.read_text()
                                         and not overlay_launcher(paths.binary)):
            return ""
        found = re.search(r'__version__\s*=\s*[\'\"]([^\'\"]+)[\'\"]', init.read_text())
        return found.group(1) if found else ""
    except OSError:
        return ""


def terminal(paths, view="config"):
    commands = {"config": ["config"], "advanced": ["config", "--advanced"],
                "setup": ["setup"], "add": ["add"], "doctor": ["doctor"]}
    if view not in commands:
        raise Error("不支持的终端操作")
    if not paths.binary.is_file() or not shutil.which("omarchy-launch-tui"):
        raise Error("缺少工作区后端或 omarchy-launch-tui，请重新运行安装器")
    # Do not make the QML bridge wait for a terminal window to close.
    subprocess.Popen(["omarchy-launch-tui", "--app-id=org.omarchy-workspaces.config",
                      str(paths.binary), *commands[view]],
                     stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                     stderr=subprocess.DEVNULL, start_new_session=True)


def open_gui(paths):
    if directory(paths).is_dir() and shutil.which("omarchy-shell"):
        try:
            result = subprocess.run(["omarchy-shell", "shell", "summon", PLUGIN_ID, "{}"],
                                    capture_output=True, text=True, timeout=8)
            if result.returncode == 0 and result.stdout.strip() == "ok":
                return "已打开原生工作区面板"
        except (OSError, subprocess.TimeoutExpired):
            pass
    terminal(paths)
    return "原生插件未启用或 Shell 不可用，已打开终端配置界面"


def refresh_plugin(enable=False):
    """Use the supported IPC; never overwrite shell.json or restart the desktop."""
    if not shutil.which("omarchy-shell"):
        return False
    try:
        result = subprocess.run(["omarchy-shell", "shell", "rescanPlugins"],
                                capture_output=True, text=True, timeout=8)
        if result.returncode:
            return False
        if enable:
            # setPluginEnabled's second argument is the literal string "true".
            for _ in range(6):
                result = subprocess.run(["omarchy-shell", "shell", "setPluginEnabled", PLUGIN_ID, "true"],
                                        capture_output=True, text=True, timeout=8)
                if result.returncode == 0 and result.stdout.strip() == "ok":
                    return True
                import time
                time.sleep(0.1)  # Registry discovery is asynchronous after rescan.
            return False
        return True
    except (OSError, subprocess.TimeoutExpired):
        return False


def remove_installed_plugin(paths):
    """Remove only this installer's unchanged, non-git plugin copy."""
    import hashlib
    target = directory(paths)
    if not target.exists():
        return ""
    if target.is_symlink() or (target / ".git").exists():
        return f"插件由 Git/Omarchy 管理，请执行 omarchy plugin remove {PLUGIN_ID}"
    marker = target / ".ows-install.json"
    try:
        saved = json.loads(marker.read_text())
    except (OSError, ValueError):
        return f"插件目录不是本安装器创建，已保留；可执行 omarchy plugin remove {PLUGIN_ID}"
    if saved.get("id") != PLUGIN_ID:
        return "插件所有权记录不匹配，已保留插件目录"
    actual = {}
    for path in target.rglob("*"):
        if path.is_symlink():
            return "插件目录含符号链接，已保留插件目录"
        if path.is_file() and path != marker and "__pycache__" not in path.parts:
            actual[str(path.relative_to(target))] = hashlib.sha256(path.read_bytes()).hexdigest()
    if actual != saved.get("files"):
        return "插件源码含本地修改，已保留；可执行 omarchy plugin remove " + PLUGIN_ID
    # Disable before deletion so the shell releases its QML objects.
    if shutil.which("omarchy-shell"):
        try:
            subprocess.run(["omarchy-shell", "shell", "setPluginEnabled", PLUGIN_ID, "false"],
                           capture_output=True, timeout=8, check=False)
        except (OSError, subprocess.TimeoutExpired):
            pass
    shutil.rmtree(target)
    refresh_plugin()
    return ""
