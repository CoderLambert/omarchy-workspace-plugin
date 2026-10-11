"""Register a reversible row in Omarchy 4's native JSONC system menu."""
import base64
import hashlib
import json
import re
import shlex
import shutil
import subprocess
from pathlib import Path

from .core import Error, atomic, lock
from .manager import snapshot


KEY = 'ows-workspaces'
BEGIN = '// omarchy-workspaces: menu begin'
END = '// omarchy-workspaces: menu end'


def uncomment(text):
    chars = list(text)
    i, quoted = 0, False
    while i < len(text):
        if quoted:
            if text[i] == '\\':
                i += 2
                continue
            if text[i] == '"':
                quoted = False
        elif text[i] == '"':
            quoted = True
        elif text.startswith('//', i) or text.startswith('/*', i):
            if text.startswith('//', i):
                end = text.find('\n', i)
                end = len(text) if end < 0 else end
            else:
                end = text.find('*/', i + 2)
                if end < 0:
                    raise Error('Omarchy 菜单 JSONC 注释没有闭合')
                end += 2
            for j in range(i, end):
                if chars[j] != '\n':
                    chars[j] = ' '
            i = end
            continue
        i += 1
    return ''.join(chars)


def parse_jsonc(text):
    clean = uncomment(text)
    chars = list(clean)
    i, quoted = 0, False
    while i < len(clean):
        if quoted:
            if clean[i] == '\\':
                i += 2
                continue
            if clean[i] == '"':
                quoted = False
        elif clean[i] == '"':
            quoted = True
        elif clean[i] == ',':
            j = i + 1
            while j < len(clean) and clean[j].isspace():
                j += 1
            if j < len(clean) and clean[j] in '}]':
                chars[i] = ' '
        i += 1
    try:
        value = json.loads(''.join(chars))
    except ValueError as exc:
        raise Error(f'Omarchy 菜单 JSONC 无效，未覆盖原文件：{exc}') from exc
    if not isinstance(value, dict):
        raise Error('Omarchy 菜单扩展必须是 JSONC 对象')
    return value


def strip_entry(text):
    if text.count(BEGIN) != text.count(END) or text.count(BEGIN) > 1:
        raise Error('工作区菜单标记不完整，请保留原文件并检查 menu begin/end')
    return re.sub(r'(?m)^' + re.escape(BEGIN) + r'\n.*?^' + re.escape(END) + r'\n?', '', text, flags=re.S)


def locations(paths):
    # Omarchy v4.0.4 Menu.qml reads this HOME path even with XDG_CONFIG_HOME set.
    return paths.home / '.config/omarchy/extensions/omarchy-menu.jsonc', paths.state / 'menu-registration.json'


def recorded_target(paths, state):
    if 'target' not in state:
        # Versions <= 1.1.3 incorrectly used XDG_CONFIG_HOME for this extension.
        return paths.config / 'omarchy/extensions/omarchy-menu.jsonc'
    value = state['target']
    if not isinstance(value, str) or not Path(value).is_absolute():
        raise Error('菜单恢复记录中的目标路径无效，未覆盖文件')
    return Path(value)


def encoded(data, mode):
    return {'data': base64.b64encode(data).decode(), 'mode': mode}


def write_snapshot(path, value):
    if value is None:
        path.unlink(missing_ok=True)
    else:
        atomic(path, base64.b64decode(value['data']), value['mode'])


def commit(edits):
    """Update both menu locations and their record as one reversible operation."""
    before = {path: snapshot(path) for path in edits}
    try:
        for path, value in edits.items():
            write_snapshot(path, value)
    except BaseException as exc:
        failures = []
        for path, value in reversed(list(before.items())):
            try:
                if snapshot(path) != value:
                    write_snapshot(path, value)
            except (Error, OSError, ValueError) as restore_error:
                failures.append(f'{path}: {restore_error}')
        if failures:
            raise Error('菜单更新失败，部分文件未能恢复：' + '; '.join(failures)) from exc
        raise


def removal_plan(target, state):
    """Remove our row while retaining later user rows and their permissions."""
    current = snapshot(target)
    if current is None:
        return None
    data = base64.b64decode(current['data'])
    if hashlib.sha256(data).hexdigest() == state['sha256']:
        original = state['original']
        if original is not None:
            # The tool preserves mode on insertion; a later chmod belongs to
            # the user and should survive migration or removal of the row.
            return {**original, 'mode': current['mode']}
        return None
    clean = strip_entry(data.decode())
    if KEY in parse_jsonc(clean):
        raise Error(f'工作区菜单项已被手工改写，未删除；请先检查菜单扩展：{target}')
    return encoded(clean.encode(), current['mode'])


def refresh():
    try:
        result = subprocess.run(['omarchy-menu', 'refresh'], capture_output=True, text=True, timeout=5)
        return result.returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False


def register(paths):
    if not shutil.which('omarchy-launch-tui'):
        raise Error('缺少 omarchy-launch-tui，请在 Omarchy 4 桌面中安装')
    target, state_file = locations(paths)
    with lock(paths.state / 'menu.lock'):
        previous_record = snapshot(state_file)
        state = json.loads(base64.b64decode(previous_record['data'])) if previous_record else None
        source_target = recorded_target(paths, state) if state else target
        migrating = source_target != target
        edits = {}
        if state and migrating:
            edits[source_target] = removal_plan(source_target, state)
        current_snapshot = snapshot(target)
        current = base64.b64decode(current_snapshot['data']) if current_snapshot else None
        text = current.decode() if current is not None else '{\n}\n'
        current_state = state if not migrating else None
        if BEGIN in text and not current_state:
            raise Error('已有工作区菜单标记但恢复记录缺失，未覆盖')
        clean = strip_entry(text)
        data = parse_jsonc(clean)
        if KEY in data:
            raise Error(f'已有同名非受管菜单项 {KEY}，未覆盖')
        end = uncomment(clean).rfind('}')
        prefix = clean[:end].rstrip()
        if data and not uncomment(prefix).rstrip().endswith(','):
            prefix += '\n  ,'
        command = shlex.join([str(paths.binary), 'gui'])
        row = {'icon':'󰕰', 'label':'工作区配置', 'action':command,
               'aliases':['workspace-settings'], 'description':'修改应用工作区、自动识别与整理窗口'}
        source = prefix + '\n' + BEGIN + '\n  ' + json.dumps(KEY) + ': ' + json.dumps(row, ensure_ascii=False) + ',\n' + END + '\n' + clean[end:]
        parse_jsonc(source)
        mode = current_snapshot['mode'] if current_snapshot else 0o600
        original = current_state['original'] if current_state else current_snapshot
        record = {'target': str(target), 'original': original,
                  'sha256': hashlib.sha256(source.encode()).hexdigest()}
        edits[target] = encoded(source.encode(), mode)
        edits[state_file] = encoded(json.dumps(record).encode(), 0o600)
        commit(edits)
    return refresh()


def unregister(paths):
    _, state_file = locations(paths)
    with lock(paths.state / 'menu.lock'):
        previous_record = snapshot(state_file)
        if previous_record is None:
            return
        state = json.loads(base64.b64decode(previous_record['data']))
        target = recorded_target(paths, state)
        commit({target: removal_plan(target, state), state_file: None})
    refresh()


def check(paths):
    target, state_file = locations(paths)
    if not target.exists() or not state_file.exists():
        raise Error('系统菜单入口缺失；执行 omarchy-workspaces repair-menu')
    state = json.loads(state_file.read_text())
    if recorded_target(paths, state) != target:
        raise Error('系统菜单仍登记在旧位置；执行 omarchy-workspaces repair-menu 迁移')
    row = parse_jsonc(target.read_text()).get(KEY, {})
    if not isinstance(row, dict) or row.get('label') != '工作区配置' or not row.get('action'):
        raise Error('系统菜单入口缺失或被改写；执行 omarchy-workspaces repair-menu')
