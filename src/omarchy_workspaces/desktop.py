"""XDG desktop IDs, proxy entries and original launch delegation."""
import configparser
import hashlib
import os
import shutil
import subprocess
from pathlib import Path

from .core import Error


def parse(text):
    parser = configparser.ConfigParser(interpolation=None, strict=False)
    parser.optionxform = str
    try:
        parser.read_string(text)
        return dict(parser["Desktop Entry"])
    except (configparser.Error, KeyError) as exc:
        raise Error(f"无效 .desktop：{exc}") from exc


def replace_fields(text, fields):
    lines, active, written = [], False, set()
    for line in text.splitlines():
        if line.startswith("["):
            if active:
                lines.extend(f"{k}={v}" for k, v in fields.items() if k not in written)
            active = line == "[Desktop Entry]"
        key = line.split("=", 1)[0] if "=" in line else ""
        if active and key in fields:
            if key not in written:
                lines.append(f"{key}={fields[key]}")
            written.add(key)
        else:
            lines.append(line)
    if active:
        lines.extend(f"{k}={v}" for k, v in fields.items() if k not in written)
    return "\n".join(lines) + "\n"


def exec_line(argv):
    def escape(value):
        value = str(value).replace("%", "%%")
        for char in ("\\", '"', "`", "$"):
            value = value.replace(char, "\\" + char)
        return '"' + value + '"'
    return " ".join(escape(arg) for arg in argv)


def proxy(app_id, app, binary, original=None):
    fields = parse(original) if original else {}
    keep = {k: v for k, v in fields.items() if k in {"Name", "Icon", "Comment", "Categories", "Keywords", "OnlyShowIn", "NotShowIn"} or k.startswith(("Name[", "Comment[", "Keywords["))}
    keep.update({"Type": "Application", "Name": app.get("name", fields.get("Name", app_id)), "Icon": app.get("icon", fields.get("Icon", "application-x-executable")), "Exec": exec_line([binary, "launch", app_id]), "Terminal": "false", "DBusActivatable": "false", "X-Omarchy-Workspaces": "true", "Actions": "OWSOriginalLaunch;" + fields.get("Actions", "")})
    # Original action commands remain untouched (file/URL/new-window actions are explicit).
    actions = original[original.find("\n[Desktop Action "):] if original and "\n[Desktop Action " in original else ""
    main = "[Desktop Entry]\n" + "\n".join(f"{k}={v}" for k, v in keep.items()) + "\n"
    return main + actions + "\n[Desktop Action OWSOriginalLaunch]\nName=调用原始启动入口\nExec=" + exec_line([binary, "launch", app_id, "--new"]) + "\n"


class Desktops:
    def __init__(self, paths):
        self.paths = paths
        dirs = os.environ.get("XDG_DATA_DIRS", "/usr/local/share:/usr/share").split(":")
        self.roots = list(dict.fromkeys([paths.data / 'applications'] + [Path(d) / 'applications' for d in dirs if d]))

    def candidates(self, desktop_id):
        for root in self.roots:
            direct = root / desktop_id
            if direct.is_file():
                yield direct
            if root.exists():
                for path in sorted(root.rglob("*.desktop")):
                    if path != direct and str(path.relative_to(root)).replace("/", "-") == desktop_id:
                        yield path

    def text(self, desktop_id, records=None, adopt=False):
        target = str(self.paths.apps / desktop_id)
        record = (records or {}).get(target)
        adopt_current = False
        if record and adopt and Path(target).is_file():
            # Only a changed override represents an external update. Reading
            # our unchanged NoDisplay copy would mask an updated system entry
            # whenever --adopt was needed for some other application.
            adopt_current = hashlib.sha256(Path(target).read_bytes()).hexdigest() != record["sha256"]
        if record and not adopt_current:
            import base64
            if record["original"] is not None:
                return base64.b64decode(record["original"]["data"]).decode()
            # The user-level override was created by us; fall through to system entry.
            skip = Path(target)
        else:
            skip = None
        for path in self.candidates(desktop_id):
            if path != skip:
                return path.read_text()
        raise Error(f"找不到原始启动项：{desktop_id}")

    def inventory(self):
        result, seen = [], set()
        for root in self.roots:
            if not root.exists():
                continue
            for path in sorted(root.rglob("*.desktop")):
                desktop_id = str(path.relative_to(root)).replace("/", "-")
                if desktop_id in seen:
                    continue
                seen.add(desktop_id)
                try:
                    fields = parse(path.read_text())
                except (OSError, UnicodeError, Error):
                    continue
                if fields.get("Type") != "Application" or fields.get("Hidden", "false").lower() == "true" or desktop_id.startswith("ows-"):
                    continue
                result.append({"id": desktop_id, "path": str(path), **fields})
        return sorted(result, key=lambda entry: entry.get("Name", entry["id"]).lower())

    def launch(self, app, extra=()):
        if app.get("desktop"):
            if not shutil.which("gtk-launch"):
                raise Error("缺少 gtk-launch，请安装 gtk3")
            command = ["gtk-launch", app["desktop"], *extra]
        else:
            command = [*app["command"], *extra]
        # Same application slice as Omarchy's menu; never shell/eval the desktop Exec.
        if shutil.which("uwsm-app"):
            command = ["uwsm-app", "--", *command]
        self.paths.state.mkdir(parents=True, exist_ok=True)
        with (self.paths.state / "launch.log").open("ab") as log:
            try:
                return subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=log, stderr=log, start_new_session=True)
            except OSError as exc:
                raise Error(f"应用启动失败：{exc}") from exc
