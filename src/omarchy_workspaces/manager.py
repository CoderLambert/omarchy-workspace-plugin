"""Transactional apply, crash recovery, reversible menu registration and launch locks."""
import base64
import copy
import hashlib
import json
import os
import re
import shlex
import subprocess
import time
from pathlib import Path

from .core import Error, atomic, binding_shortcut, dumps, key_identity, lock, owner, recent, validate
from .desktop import Desktops, proxy, replace_fields
from .hypr import Hypr, detect, generate
from .tmux import windows as tmux_windows


BEGIN = "omarchy-workspaces: begin"
END = "omarchy-workspaces: end"


def digest(data):
    return hashlib.sha256(data).hexdigest()


def snapshot(path):
    if path.is_symlink():
        raise Error(f"受管文件是符号链接：{path}；请使用实际文件路径")
    if not path.exists():
        return None
    if not path.is_file():
        raise Error(f"路径不是普通文件：{path}")
    return {"data": base64.b64encode(path.read_bytes()).decode(), "mode": path.stat().st_mode & 0o777}


def restore(path, snap):
    if snap is None:
        path.unlink(missing_ok=True)
    else:
        atomic(path, base64.b64decode(snap["data"]), snap["mode"])


def strip_block(text):
    if text.count(BEGIN) != text.count(END) or text.count(BEGIN) > 1:
        raise Error("Hyprland 配置内受管标记不完整，请先修复 begin/end 标记")
    return re.sub(r"(?m)^[^\n]*omarchy-workspaces: begin[^\n]*\n.*?^[^\n]*omarchy-workspaces: end[^\n]*\n?", "", text, flags=re.S)


class Manager:
    def __init__(self, paths, hypr=None, desktops=None):
        self.p = paths
        self.hypr = hypr or Hypr()
        self.desktops = desktops or Desktops(paths)
        self.state_file = paths.state / "manifest.json"
        self.journal = paths.state / "pending.json"

    def state(self):
        if not self.state_file.exists():
            return {"files": {}}
        try:
            return json.loads(self.state_file.read_text())
        except (ValueError, OSError) as exc:
            raise Error(f"恢复信息损坏：{exc}") from exc

    def applied_config(self):
        if self.journal.exists():
            raise Error("上一次应用配置被中断，请先执行 omarchy-workspaces recover")
        state = self.state()
        if "config" not in state:
            raise Error("尚未应用配置，请执行 omarchy-workspaces setup")
        return validate(copy.deepcopy(state["config"]))

    def revision(self):
        """Version both the editable draft and the last committed runtime state.

        Call before loading a configuration to edit, then pass this token back
        to apply/uninstall. The check under the transaction lock prevents a
        second GUI or CLI process from overwriting a completed first edit.
        """
        result = hashlib.sha256()
        for path in (self.p.file, self.state_file):
            try:
                data = path.read_bytes()
            except FileNotFoundError:
                result.update(b"missing\0")
            else:
                result.update(b"present\0" + len(data).to_bytes(8, "big") + data)
        return result.hexdigest()

    def check_revision(self, expected_revision):
        if expected_revision is not None and expected_revision != self.revision():
            raise Error("配置已被其他操作修改，请刷新后重试；本次修改未写入")

    def apply(self, config, adopt=False, text=None, expected_revision=None, expected_bindings=None):
        with lock(self.p.state / "apply.lock"):
            if self.journal.exists():
                raise Error("存在中断事务，请先执行 omarchy-workspaces recover")
            self.check_revision(expected_revision)
            validate(config)
            state = self.state()
            records = state["files"]
            self.hypr.reload()  # Baseline must be valid before touching any file.
            backend, main = detect(self.p, config, self.hypr)
            generated = self.p.config / f"hypr/app-workspaces.{ 'lua' if backend == 'lua' else 'conf'}"
            binds = self.hypr.query("binds")
            if expected_bindings is not None:
                from .hypr import binding_signature
                if binding_signature(binds) != expected_bindings:
                    raise Error("快捷键绑定在预览后发生变化，请重新执行自动预设；本次修改未写入")
            source, changes = generate(config, backend, self.p.binary, binds)
            planned = {str(generated): (source.encode(), 0o600)}
            current_main = main.read_text()
            clean = strip_block(current_main)
            prefix = "--" if backend == "lua" else "#"
            include = f"dofile({json.dumps(str(generated), ensure_ascii=False)})" if backend == "lua" else f"source = {generated}"
            planned[str(main)] = ((clean.rstrip() + f"\n\n{prefix} {BEGIN}\n{include}\n{prefix} {END}\n").encode(), main.stat().st_mode & 0o777)
            for app_id, app in config["apps"].items():
                if not app.get("menu", True):
                    continue
                original = self.desktops.text(app["desktop"], records, adopt) if app.get("desktop") else None
                if original:
                    planned[str(self.p.apps / app["desktop"])] = (replace_fields(original, {"NoDisplay": "true"}).encode(), 0o644)
                planned[str(self.p.apps / f"ows-{app_id}.desktop")] = (proxy(app_id, app, str(self.p.binary), original).encode(), 0o644)
            config_text = text if text is not None else dumps(config)
            edits = dict(planned)
            next_records = {}
            for target, (data, mode) in planned.items():
                path = Path(target)
                previous = records.get(target)
                now = snapshot(path)
                is_main = path == main
                if not previous and now is not None and (path == generated or path.name.startswith("ows-")):
                    raise Error(f"已有同名非受管文件：{path}；请先移动该文件以免覆盖")
                drift = previous and now is not None and digest(base64.b64decode(now["data"])) != previous["sha256"]
                if previous and drift and not is_main and not adopt:
                    raise Error(f"受管文件被其他工具修改：{path}；doctor 检查后可 apply --adopt 保留现状作为恢复基线")
                original = now if not previous or (drift and adopt) else previous["original"]
                next_records[target] = {"original": original, "sha256": digest(data), "main": is_main}
            for target, record in records.items():
                if target in planned:
                    continue
                path = Path(target)
                if record.get("main"):
                    if path.exists():
                        edits[target] = (strip_block(path.read_text()).encode(), path.stat().st_mode & 0o777)
                else:
                    now = snapshot(path)
                    drift = now is not None and digest(base64.b64decode(now["data"])) != record["sha256"]
                    if adopt and drift:
                        # An edited draft may remove this application. Explicit
                        # adoption keeps its external update as an unmanaged
                        # file instead of requiring the deleted app to return.
                        edits[target] = decode(now)
                    else:
                        self.check_owned(path, record)
                        edits[target] = decode(record["original"])
            edits[str(self.p.file)] = (config_text.encode(), 0o600)
            next_state = {"version": 1, "files": next_records, "config": config}
            edits[str(self.state_file)] = (json.dumps(next_state, ensure_ascii=False, indent=2).encode(), 0o600)
            self.commit(edits, config)
            self.refresh()
            return changes

    def check_owned(self, path, record):
        now = snapshot(path)
        if now is not None and digest(base64.b64decode(now["data"])) != record["sha256"]:
            raise Error(f"{path} 在应用后被修改，拒绝覆盖；执行 apply --adopt 后重试")

    def verify_shortcuts(self, config):
        binds = self.hypr.query('binds')
        for app_id, app in config['apps'].items():
            for key in app.get('shortcuts', []):
                matches = [b for b in binds if b.get('submap', '') in ('', 'reset')
                           and binding_shortcut(b) and key_identity(binding_shortcut(b)) == key_identity(key)]
                expected = shlex.join([str(self.p.binary), 'launch', app_id])
                # Lua's IPC arg is a callback registry number, not the shell command.
                managed = len(matches) == 1 and (matches[0].get('arg') == expected or (
                    matches[0].get('dispatcher') == '__lua'
                    and matches[0].get('description') == '工作区: ' + app.get('name', app_id)))
                if not managed:
                    raise Error(f'{key} 接管校验失败：仍有重复绑定或未找到受管绑定；本次配置已撤回')

    def commit(self, edits, config=None):
        before = {target: snapshot(Path(target)) for target in edits}
        after = {target: encode(item) for target, item in edits.items()}
        atomic(self.journal, json.dumps({"before": before, "after": after}, ensure_ascii=False).encode())
        try:
            for target, item in edits.items():
                restore(Path(target), encode(item))
            self.hypr.reload()
            if config is not None:
                self.verify_shortcuts(config)
        except BaseException:
            for target, snap in reversed(list(before.items())):
                restore(Path(target), snap)
            try:
                self.hypr.reload()
            except Error as exc:
                # Keep recovery journal if compositor couldn't be revalidated.
                raise Error(f"文件已恢复，但重载仍失败；执行 recover：{exc}") from exc
            self.journal.unlink()
            raise
        self.journal.unlink()

    def recover(self):
        with lock(self.p.state / "apply.lock"):
            if not self.journal.exists():
                return False
            journal = json.loads(self.journal.read_text())
            for target, old in journal["before"].items():
                now = snapshot(Path(target))
                if now != old and now != journal["after"][target]:
                    raise Error(f"事务中断后 {target} 又被修改，拒绝自动覆盖；请保留 pending.json 并手动核对")
            for target, old in reversed(list(journal["before"].items())):
                restore(Path(target), old)
            self.hypr.reload()
            self.journal.unlink()
            self.refresh()
            return True

    def uninstall(self, expected_revision=None):
        with lock(self.p.state / "apply.lock"):
            if self.journal.exists():
                raise Error("先执行 recover 再卸载")
            self.check_revision(expected_revision)
            state = self.state()
            self.hypr.reload()
            edits = {}
            for target, record in state["files"].items():
                path = Path(target)
                if record.get("main") and path.exists():
                    edits[target] = (strip_block(path.read_text()).encode(), path.stat().st_mode & 0o777)
                else:
                    self.check_owned(path, record)
                    edits[target] = decode(record["original"])
            edits[str(self.state_file)] = None
            self.commit(edits)
            self.refresh()

    def refresh(self):
        try:
            subprocess.run(["update-desktop-database", str(self.p.apps)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=10)
        except (OSError, subprocess.TimeoutExpired):
            pass  # Quickshell watches entries; database utility isn't required.

    def launch(self, app_id, new=False, extra=()):
        config = self.applied_config()
        app_id = config["aliases"].get(app_id, app_id)
        if app_id not in config["apps"]:
            raise Error(f"应用未登记：{app_id}")
        app = config["apps"][app_id]
        scratchpad = self.hypr.visible_scratchpad()
        if new or extra:
            self.desktops.launch(app, extra)
            return "已转交原始入口"
        signature = os.environ.get("HYPRLAND_INSTANCE_SIGNATURE", "default")
        key = digest(signature.encode())[:12] + "-" + app_id
        with lock(self.p.runtime / f"{key}.lock", blocking=False) as acquired:
            if not acquired:
                return "应用正在启动"
            pending = self.p.runtime / f"{key}.json"
            clients = self.matching_clients(config, app_id)
            preferred = [c for c in clients if (c.get("workspace", {}).get("name") == "special:scratchpad") == bool(scratchpad)]
            client = recent(preferred or clients)
            if client:
                pending.unlink(missing_ok=True)
                if scratchpad:
                    if client.get("workspace", {}).get("name") != scratchpad:
                        self.hypr.move(client, scratchpad)
                elif client.get("workspace", {}).get("name") == "special:scratchpad" or app.get("existing_window", config["defaults"].get("existing_window", "focus")) == "move":
                    self.hypr.move(client, app["workspace"])
                self.hypr.focus(client)
                return "已聚焦已有窗口"
            # Persist a cooldown through process exits/timeouts; no repeated launcher storm.
            timeout = config["defaults"].get("launch_timeout", 20)
            if pending.exists():
                try:
                    when = json.loads(pending.read_text())["started"]
                except (ValueError, KeyError):
                    when = 0
                if time.time() - when < timeout:
                    return "应用正在启动"
            atomic(pending, json.dumps({"started": time.time()}).encode())
            try:
                process = self.desktops.launch(app)
                deadline = time.monotonic() + timeout
                while time.monotonic() < deadline:
                    clients = self.matching_clients(config, app_id)
                    client = recent(clients)
                    if client:
                        # Correct the first observed window too; DBus/singleton relaunch may ignore PID rules.
                        self.hypr.move(client, scratchpad or app["workspace"])
                        # If the user hid scratchpad while startup was pending, keep it hidden.
                        if not scratchpad or self.hypr.visible_scratchpad() == scratchpad:
                            self.hypr.focus(client)
                        pending.unlink(missing_ok=True)
                        return "已启动并聚焦"
                    code = process.poll()
                    if code not in (None, 0):
                        raise Error(f"启动入口退出码 {code}，查看 {self.p.state / 'launch.log'}")
                    time.sleep(0.2)
            except BaseException:
                pending.unlink(missing_ok=True)
                raise
            # Keep the marker briefly after timeout (covers slow/tray applications).
            atomic(pending, json.dumps({"started": time.time()}).encode())
            raise Error("已调用启动入口，但未找到登记窗口；检查窗口身份或启动日志。可在超时后重试。")

    def matching_clients(self, config, app_id):
        clients = self.hypr.query('clients')
        matched = [c for c in clients if owner(config, c) == app_id]
        if app_id == 'tmux':
            known = {c.get('address') for c in matched}
            matched += [c for c in tmux_windows(config['apps'][app_id], clients) if c.get('address') not in known]
        return matched

    def arrange(self, dry=False, app_id=None, include_special=False):
        if type(include_special) is not bool:
            raise Error("包含临时工作区必须是布尔值")
        config = self.applied_config()
        result = []
        for client in self.hypr.query("clients"):
            location = client.get("workspace") or {}
            if not include_special and (str(location.get("name", "")).startswith("special:")
                                        or (isinstance(location.get("id"), int) and location["id"] < 0)):
                continue
            matched_id = owner(config, client)
            if matched_id and (app_id is None or matched_id == app_id):
                workspace = config["apps"][matched_id]["workspace"]
                result.append(f"{matched_id} {client['address']} -> {workspace}")
                if not dry:
                    self.hypr.move(client, workspace)
        return result


def encode(item):
    if item is None:
        return None
    data, mode = item
    return {"data": base64.b64encode(data).decode(), "mode": mode}


def decode(snap):
    if snap is None:
        return None
    return base64.b64decode(snap["data"]), snap["mode"]
