import copy
import json
import multiprocessing
import os
import re
import shlex
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from omarchy_workspaces.core import Error, Paths, dumps, empty_config, key_identity, load, lock, owner, recent, validate
from omarchy_workspaces.desktop import Desktops, exec_line, parse, proxy, replace_fields
from omarchy_workspaces.hypr import Hypr, generate, literal
from omarchy_workspaces.manager import Manager, encode, snapshot, strip_block


def cfg():
    c = empty_config()
    c["apps"]["slack"] = {"name": "Slack", "workspace": 4, "desktop": "slack.desktop", "matches": [{"initial_class": "Slack"}], "shortcuts": []}
    return c


def client(address="0x1", cls="Slack", workspace=4, history=0):
    return {"address": address, "class": cls, "initialClass": cls, "title": "ChatGPT Slack", "initialTitle": "Slack", "workspace": {"id": workspace, "name": str(workspace)}, "mapped": True, "focusHistoryID": history}


class FakeHypr:
    def __init__(self):
        self.clients = []
        self.monitors = []
        self.binds = []
        self.focused = []
        self.moved = []
        self.reloads = 0
        self.fail_at = 0
        self.original_binds = []

    def query(self, key):
        return {"version": {"version": "0.55.0"}, "binds": self.binds, "clients": self.clients, "monitors": self.monitors}[key]

    def call(self, *args):
        return ""

    def reload(self):
        self.reloads += 1
        if self.reloads == self.fail_at:
            raise Error("injected configerrors")
        self.binds = copy.deepcopy(self.original_binds)
        generated = Path(os.environ['XDG_CONFIG_HOME']) / 'hypr/app-workspaces.lua'
        if generated.exists():
            # Model Hyprland 0.55/0.56's literal combo-string removal.
            for line in generated.read_text().splitlines():
                found = re.match(r'hl\.(unbind|bind)\(("(?:\\.|[^"\\])*")', line)
                if not found:
                    continue
                operation, encoded = found.groups()
                combo = json.loads(encoded)
                if operation == 'unbind':
                    self.binds = [b for b in self.binds if b.get('combo') != combo]
                else:
                    command = re.search(r'hl.dsp.exec_cmd\(("(?:\\.|[^"\\])*")\)', line)
                    description = re.search(r'description = ("(?:\\.|[^"\\])*")', line)
                    mask, _ = key_identity(combo)
                    self.binds.append({'combo':combo, 'modmask':mask, 'key':combo.split(' + ')[-1], 'arg':'42', 'dispatcher':'__lua', 'description':json.loads(description.group(1)), 'test_command':json.loads(command.group(1))})

    visible_scratchpad = Hypr.visible_scratchpad

    def focus(self, c):
        self.focused.append(c["address"])

    def move(self, c, workspace):
        self.moved.append((c["address"], workspace))


class Environment(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.env = patch.dict(os.environ, {"HOME": str(root), "XDG_CONFIG_HOME": str(root / "config"), "XDG_DATA_HOME": str(root / "data"), "XDG_STATE_HOME": str(root / "state"), "XDG_RUNTIME_DIR": str(root / "run"), "XDG_DATA_DIRS": str(root / "system"), "HYPRLAND_INSTANCE_SIGNATURE": "test"})
        self.env.start()
        self.p = Paths()
        self.main = self.p.config / "hypr/hyprland.lua"
        self.main.parent.mkdir(parents=True)
        self.main.write_text('-- user setting\nlocal setting = "keep"\n')
        self.system = root / "system/applications/slack.desktop"
        self.system.parent.mkdir(parents=True)
        self.original = '[Desktop Entry]\nType=Application\nName=Slack\nIcon=slack\nExec=/usr/bin/slack %U\nDBusActivatable=true\nMimeType=x-scheme-handler/slack;\n'
        self.system.write_text(self.original)
        self.h = FakeHypr()
        self.m = Manager(self.p, self.h)

    def tearDown(self):
        self.env.stop()
        self.tmp.cleanup()


class IdentityTests(unittest.TestCase):
    def test_exact_identity_never_matches_browser_title(self):
        self.assertIsNone(owner(cfg(), client(cls="google-chrome")))
        self.assertEqual(owner(cfg(), client()), "slack")
        self.assertIsNone(owner(cfg(), client(cls="slack")))

    def test_mru_zero_current_negative_unknown(self):
        windows = [client("0x1", history=-1), client("0x2", history=4), client("0x3", history=0)]
        self.assertEqual(recent(windows)["address"], "0x3")

    def test_specific_identity_owns_window_over_generic(self):
        c = cfg()
        c["apps"]["detail"] = {"workspace": 1, "command": ["echo"], "matches": [{"initial_class": "Slack", "initial_title": "Slack"}]}
        validate(c)
        self.assertEqual(owner(c, client()), "detail")

    def test_duplicate_or_title_only_identity_rejected(self):
        c = cfg()
        c["apps"]["copy"] = {"workspace": 1, "command": ["echo"], "matches": [{"initial_class": "Slack"}]}
        with self.assertRaises(Error):
            validate(c)
        del c["apps"]["copy"]
        c["apps"]["slack"]["matches"] = [{"initial_title": "Slack"}]
        with self.assertRaises(Error):
            validate(c)

    def test_alias_and_shared_desktop_rules(self):
        c = cfg()
        c["aliases"]["communication"] = "slack"
        validate(c)
        c["aliases"]["bad"] = "communication"
        with self.assertRaises(Error):
            validate(c)

    def test_special_identity_regex_escaped(self):
        self.assertEqual(literal("a.b[c]+"), r"^a\.b\[c\]\+$")

    def test_shortcut_without_main_key_rejected(self):
        with self.assertRaises(Error):
            key_identity("SUPER + ALT")
        self.assertEqual(key_identity("SUPER + ALT + Return"), (72, "return"))

    def test_all_supported_configuration_fields_roundtrip(self):
        c = cfg()
        c["apps"]["slack"]["menu"] = False
        c["defaults"]["launch_timeout"] = 2.5
        import tomllib
        self.assertEqual(validate(__import__('tomllib').loads(dumps(c))), validate(c))


class TransactionTests(Environment):
    def test_apply_proxy_original_exec_unchanged_and_remove_restores(self):
        self.m.apply(cfg())
        override = self.p.apps / "slack.desktop"
        fields = parse(override.read_text())
        self.assertEqual(fields["Exec"], "/usr/bin/slack %U")
        self.assertEqual(fields["DBusActivatable"], "true")
        self.assertEqual(fields["NoDisplay"], "true")
        proxy_fields = parse((self.p.apps / "ows-slack.desktop").read_text())
        self.assertNotIn("MimeType", proxy_fields)
        self.assertEqual(proxy_fields["DBusActivatable"], "false")
        self.m.apply(empty_config())
        self.assertFalse(override.exists())
        self.assertFalse((self.p.apps / "ows-slack.desktop").exists())
        self.assertEqual(self.system.read_text(), self.original)

    def test_user_override_bytes_and_mode_restore(self):
        override = self.p.apps / "slack.desktop"
        override.parent.mkdir(parents=True)
        text = self.original + "X-Custom=value\n"
        override.write_text(text)
        override.chmod(0o640)
        self.m.apply(cfg())
        self.m.uninstall()
        self.assertEqual(override.read_text(), text)
        self.assertEqual(override.stat().st_mode & 0o777, 0o640)

    def test_reload_error_rolls_back_every_file_and_applied_config(self):
        self.m.apply(cfg())
        before = {str(p): p.read_bytes() for p in self.p.config.rglob('*') if p.is_file()}
        before.update({str(p): p.read_bytes() for p in self.p.apps.rglob('*') if p.is_file()})
        state = self.m.state_file.read_bytes()
        changed = cfg()
        changed["apps"]["slack"]["workspace"] = 5
        self.h.fail_at = self.h.reloads + 2
        with self.assertRaises(Error):
            self.m.apply(changed)
        for name, data in before.items():
            self.assertEqual(Path(name).read_bytes(), data)
        self.assertEqual(self.m.state_file.read_bytes(), state)
        self.assertEqual(self.m.applied_config()["apps"]["slack"]["workspace"], 4)
        self.assertFalse(self.m.journal.exists())

    def test_invalid_baseline_is_never_modified(self):
        self.h.fail_at = 1
        with self.assertRaises(Error):
            self.m.apply(cfg())
        self.assertNotIn('omarchy-workspaces', self.main.read_text())
        self.assertFalse(self.p.apps.exists())

    def test_existing_main_user_edits_survive_uninstall(self):
        self.m.apply(cfg())
        self.main.write_text(self.main.read_text() + '-- later custom changes\n')
        self.m.uninstall()
        self.assertIn('local setting = "keep"', self.main.read_text())
        self.assertIn('-- later custom changes', self.main.read_text())
        self.assertNotIn('omarchy-workspaces: begin', self.main.read_text())

    def test_desktop_refresh_drift_requires_adopt_then_preserves_updated_exec(self):
        self.m.apply(cfg())
        override = self.p.apps / "slack.desktop"
        refreshed = self.original.replace('/usr/bin/slack', '/usr/bin/new-slack')
        override.write_text(refreshed)
        with self.assertRaises(Error):
            self.m.apply(cfg())
        self.m.apply(cfg(), adopt=True)
        self.assertEqual(parse(override.read_text())["Exec"], '/usr/bin/new-slack %U')
        self.m.uninstall()
        self.assertEqual(override.read_text(), refreshed)

    def test_crash_recovery_restores_partial_transaction(self):
        target = self.p.apps / 'ows-slack.desktop'
        old = snapshot(target)
        after = encode((b'partial', 0o644))
        self.m.journal.write_text(json.dumps({'before': {str(target): old}, 'after': {str(target): after}}))
        target.parent.mkdir(parents=True)
        target.write_bytes(b'partial')
        target.chmod(0o644)
        self.assertTrue(self.m.recover())
        self.assertFalse(target.exists())

    def test_crash_recovery_refuses_later_user_change(self):
        target = self.main
        self.m.journal.write_text(json.dumps({'before': {str(target): snapshot(target)}, 'after': {str(target): encode((b'partial', 0o644))}}))
        target.write_text('user changed later')
        with self.assertRaises(Error):
            self.m.recover()
        self.assertEqual(target.read_text(), 'user changed later')

    def test_reapply_only_one_managed_source_block(self):
        self.m.apply(cfg())
        self.m.apply(cfg())
        self.assertEqual(self.main.read_text().count('omarchy-workspaces: begin'), 1)
        self.assertIn('local setting = "keep"', self.main.read_text())


class LaunchTests(Environment):
    def test_existing_legacy_tmux_terminal_reused_instead_of_new_client(self):
        c = cfg()
        c['apps']['tmux'] = {'workspace':2, 'command':['omarchy-launch-tui','--app-id=org.omarchy-workspaces.tmux','tmux','new-session','-A','-s','Work'], 'matches':[{'initial_class':'org.omarchy-workspaces.tmux'}]}
        self.m.apply(c)
        legacy = client('0x2',cls='Alacritty',workspace=2)
        legacy['pid'] = 120
        unrelated = client('0x3',cls='Alacritty',workspace=2)
        unrelated['pid'] = 999
        embedded = client('0x4',cls='Code',workspace=2)
        embedded['pid'] = 120
        self.h.clients = [legacy, unrelated, embedded]
        from types import SimpleNamespace
        with patch('omarchy_workspaces.tmux.subprocess.run',return_value=SimpleNamespace(returncode=0,stdout='Work\t150\nOther\t999\n')), patch('omarchy_workspaces.tmux.ancestors',return_value={150,120}), patch.object(self.m.desktops,'launch') as launch:
            self.assertEqual(self.m.launch('tmux'),'已聚焦已有窗口')
            launch.assert_not_called()
        self.assertEqual(self.h.focused,['0x2'])

    def test_native_launch_rules_follow_target_workspace_without_changing_keys(self):
        for backend in ('lua', 'conf', 'v2'):
            with self.subTest(backend=backend):
                text, changes = generate(cfg(), backend, '/bin/ows', [])
                self.assertNotIn('silent', text)
                self.assertIn('s[false]', text)
                self.assertEqual(changes, [])
                if backend == 'lua':
                    self.assertIn('workspace = "4"', text)
                    self.assertNotIn('hl.bind(', text)
                    self.assertIn('focus_on_activate = true', text)
                elif backend == 'conf':
                    self.assertIn('workspace = 4\n', text)
                    self.assertIn('focus_on_activate = true', text)
                else:
                    self.assertIn('workspace 4,', text)
                    self.assertIn('focusonactivate 1,', text)

    def test_existing_window_focus_mru_preserves_manual_workspace(self):
        self.m.apply(cfg())
        self.h.clients = [client('0x1', workspace=4, history=5), client('0x2', workspace=7, history=0)]
        with patch.object(self.m.desktops, 'launch') as launch:
            self.m.launch('slack')
            launch.assert_not_called()
        self.assertEqual(self.h.focused, ['0x2'])
        self.assertEqual(self.h.moved, [])

    def test_existing_window_move_policy_and_alias(self):
        c = cfg()
        c['apps']['slack']['existing_window'] = 'move'
        c['aliases']['chat'] = 'slack'
        self.m.apply(c)
        self.h.clients = [client(workspace=7)]
        self.m.launch('chat')
        self.assertEqual(self.h.moved, [('0x1', 4)])

    def show_scratchpad(self):
        self.h.monitors = [{"focused": True, "specialWorkspace": {"id": -99, "name": "special:scratchpad"}}]

    def test_scratchpad_reuses_existing_app_without_normal_assignment(self):
        self.m.apply(cfg())
        self.show_scratchpad()
        self.h.clients = [client(workspace=4)]
        self.m.launch("slack")
        self.assertEqual(self.h.moved, [("0x1", "special:scratchpad")])

    def test_scratchpad_prefers_its_existing_window(self):
        self.m.apply(cfg())
        self.show_scratchpad()
        special = client("0x2", history=1)
        special["workspace"] = {"id": -99, "name": "special:scratchpad"}
        self.h.clients = [client(history=0), special]
        self.m.launch("slack")
        self.assertEqual(self.h.focused, ["0x2"])
        self.assertFalse(self.h.moved)

    def test_scratchpad_first_launch_and_hide_during_startup(self):
        self.m.apply(cfg())
        self.show_scratchpad()
        def launch(app, extra=()):
            self.h.clients = [client()]
            self.h.monitors = []
            process = subprocess.Popen(["true"])
            process.wait()
            return process
        with patch.object(self.m.desktops, "launch", side_effect=launch):
            self.m.launch("slack")
        self.assertEqual(self.h.moved, [("0x1", "special:scratchpad")])
        self.assertFalse(self.h.focused)

    def test_normal_launch_returns_scratchpad_app_to_assigned_workspace(self):
        self.m.apply(cfg())
        special = client()
        special["workspace"] = {"id": -99, "name": "special:scratchpad"}
        self.h.clients = [special]
        self.m.launch("slack")
        self.assertEqual(self.h.moved, [("0x1", 4)])

    def test_generated_assignment_rules_exclude_special_workspaces(self):
        for backend in ("lua", "conf", "v2"):
            text, _ = generate(cfg(), backend, "/bin/ows", [])
            self.assertIn("s[false]", text)

    def test_first_launch_waits_for_window_and_routes(self):
        self.m.apply(cfg())
        def launch(app, extra=()):
            self.h.clients = [client(workspace=1)]
            process = subprocess.Popen(['true'])
            process.wait()
            return process
        with patch.object(self.m.desktops, 'launch', side_effect=launch) as mocked:
            self.assertEqual(self.m.launch('slack'), '已启动并聚焦')
            mocked.assert_called_once()
        self.assertEqual(self.h.moved, [('0x1', 4)])

    def test_new_window_and_file_uri_bypass_reuse(self):
        self.m.apply(cfg())
        self.h.clients = [client()]
        with patch.object(self.m.desktops, 'launch') as launch:
            self.m.launch('slack', new=True)
            self.m.launch('slack', extra=['file:///tmp/example'])
            self.assertEqual(launch.call_count, 2)
            self.assertEqual(launch.call_args.args[1], ['file:///tmp/example'])
        self.assertFalse(self.h.focused)

    def test_pending_application_lock_blocks_duplicate_process(self):
        self.m.apply(cfg())
        from omarchy_workspaces.manager import digest
        key = digest(b'test')[:12] + '-slack'
        with lock(self.p.runtime / (key + '.lock')):
            with patch.object(self.m.desktops, 'launch') as launch:
                self.assertEqual(self.m.launch('slack'), '应用正在启动')
                launch.assert_not_called()

    def test_unknown_app_rejected_before_launch(self):
        self.m.apply(cfg())
        with self.assertRaises(Error):
            self.m.launch('unknown')

    def test_unapplied_draft_does_not_change_runtime_behavior(self):
        self.m.apply(cfg())
        c = cfg()
        c['apps']['slack']['workspace'] = 8
        c['apps']['slack']['existing_window'] = 'move'
        self.p.file.write_text(dumps(c))
        self.h.clients = [client(workspace=9)]
        self.m.launch('slack')
        self.assertFalse(self.h.moved)

    def test_arrange_preview_is_read_only(self):
        self.m.apply(cfg())
        self.h.clients = [client(), client('0x2', cls='google-chrome')]
        self.assertEqual(len(self.m.arrange(dry=True)), 1)
        self.assertFalse(self.h.moved)


class GenerationTests(unittest.TestCase):
    def test_binding_conflict_requires_explicit_replace(self):
        c = cfg()
        c['apps']['slack']['shortcuts'] = ['CTRL + SHIFT + A']
        bind = {'modmask': 5, 'key': 'A', 'arg': 'old command', 'description': 'Old'}
        with self.assertRaises(Error):
            generate(c, 'lua', Path('/tmp/bin/ows'), [bind])
        c['apps']['slack']['replace_shortcuts'] = True
        source, changes = generate(c, 'lua', Path('/tmp/bin/ows'), [bind])
        self.assertIn('hl.unbind("SHIFT + CTRL + A")', source)
        self.assertEqual(len(changes), 1)

    def test_unbind_preserves_original_keysym_case(self):
        c = cfg()
        c['apps']['slack'].update(shortcuts=['SUPER + Return'], replace_shortcuts=True)
        source, _ = generate(c, 'lua', Path('/tmp/bin/ows'), [{'modmask':64,'key':'RETURN','arg':'terminal'}])
        self.assertIn('hl.unbind("SUPER + RETURN")', source)
        self.assertIn('hl.unbind("SUPER + Return")', source)

    def test_lua_unbind_removes_original_omarchy_modifier_order(self):
        c = cfg()
        c['apps']['slack'].update(shortcuts=['SHIFT + ALT + SUPER + Return'], replace_shortcuts=True)
        source, _ = generate(c,'lua',Path('/tmp/ows'),[{'modmask':73,'key':'RETURN','arg':'original'}])
        # Default Omarchy spells and orders this combo differently from IPC normalization.
        self.assertIn('hl.unbind("SUPER + ALT + SHIFT + RETURN")',source)
        self.assertIn('hl.unbind("SUPER + SHIFT + ALT + RETURN")',source)

    def test_proxy_exec_escapes_desktop_metacharacters(self):
        line = exec_line(['/path with spaces/a%"$`\\', 'launch', 'slack'])
        self.assertIn('%%', line)
        self.assertIn('\\$', line)
        self.assertIn('\\`', line)

    def test_proxy_original_actions_preserved(self):
        text = '[Desktop Entry]\nType=Application\nName=App\nActions=Files;\n\n[Desktop Action Files]\nName=Open files\nExec=app %F\n'
        result = proxy('slack',cfg()['apps']['slack'],'/tmp/ows',text)
        self.assertIn('Exec=app %F', result)
        self.assertIn('Actions=OWSOriginalLaunch;Files;', result)

    def test_backend_formats(self):
        for backend, expected in [('lua','hl.window_rule'),('conf','match:initial_class'),('v2','windowrulev2')]:
            text,_ = generate(cfg(), backend, '/bin/ows', [])
            self.assertIn(expected, text)

    def test_strip_block_preserves_surrounding_lines(self):
        text = 'keep one\n-- omarchy-workspaces: begin\ndofile("a")\n-- omarchy-workspaces: end\nkeep two\n'
        self.assertEqual(strip_block(text), 'keep one\nkeep two\n')


class BindingRuntimeTests(Environment):
    def config(self):
        c = cfg()
        c['apps']['slack'].update(shortcuts=['SUPER + ALT + Return'],replace_shortcuts=True)
        return c

    def test_one_physical_binding_after_install_and_reapply(self):
        self.h.original_binds = [{'combo':'SUPER + ALT + RETURN','modmask':72,'key':'RETURN','arg':'old tmux'}]
        for _ in range(2):
            self.m.apply(self.config())
            self.assertEqual(len(self.h.binds),1)
            self.assertIn('launch slack',self.h.binds[0]['test_command'])

    def test_duplicate_runtime_binding_rejected_and_transaction_restored(self):
        before = self.main.read_bytes()
        self.h.original_binds = [{'combo':'SUPER+ALT+RETURN','modmask':72,'key':'RETURN','arg':'old tmux'}]
        with self.assertRaisesRegex(Error,'接管校验失败'):
            self.m.apply(self.config())
        self.assertEqual(self.main.read_bytes(),before)
        self.assertFalse(self.m.state_file.exists())
        self.assertFalse(self.m.journal.exists())
        self.assertFalse((self.p.config/'hypr/app-workspaces.lua').exists())


if __name__ == '__main__':
    unittest.main()
