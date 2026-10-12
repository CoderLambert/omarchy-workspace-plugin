"""Real installer/bridge subprocesses with isolated Omarchy IPC and HOME.

The fake shell checks our argv and lifecycle; it cannot validate QML rendering.
"""
import base64
import json
import subprocess
import sys
import unittest
from pathlib import Path

from omarchy_workspaces import __version__
from omarchy_workspaces.core import dumps, load
import test_cli_integration as cli_fixture


NATIVE_TOOL = r'''
import json, os, sys
from pathlib import Path
tool = Path(sys.argv[0]).name
if tool == 'omarchy-plugin-validate':
    root = Path(sys.argv[1])
    m = json.loads((root / 'manifest.json').read_text())
    sys.exit(0 if m['id'] == 'lambert.workspaces' and (root / m['entryPoints']['panel']).is_file() else 1)
p = Path(os.environ['OWS_TEST_IPC'])
d = json.loads(p.read_text())
d.setdefault('shell_calls', []).append(sys.argv[1:])
if sys.argv[2:3] == ['setPluginEnabled']:
    d['plugin_enabled'] = sys.argv[-1] == 'true'
reply = 'ok'
if sys.argv[2:3] == ['summon'] and not d.get('plugin_enabled'):
    reply = 'disabled'
p.write_text(json.dumps(d))
print(reply)
'''


class NativePluginTests(unittest.TestCase):
    tearDown = cli_fixture.InstalledCliTests.tearDown
    run_cli = cli_fixture.InstalledCliTests.run_cli

    def setUp(self):
        cli_fixture.InstalledCliTests.setUp(self)
        self.package = Path(__file__).resolve().parents[1]
        for name in ('omarchy-shell', 'omarchy-plugin-validate'):
            command = self.fakebin / name
            command.write_text('#!' + sys.executable + '\n' + NATIVE_TOOL)
            command.chmod(0o755)
        self.plugin = self.root / '.config/omarchy/plugins/lambert.workspaces'
        self.install()

    def install(self, *args, source=None, success=True):
        result = subprocess.run(['bash', str((source or self.package) / 'install.sh'), *args],
                                capture_output=True, text=True, env=self.env, timeout=15)
        self.assertEqual(result.returncode == 0, success, result.stdout + result.stderr)
        return result

    def bridge(self, request, success=True):
        result = subprocess.run([sys.executable, '-B', str(self.plugin / 'scripts/bridge.py'), json.dumps(request)],
                                capture_output=True, text=True, env=self.env, timeout=15)
        parsed = json.loads(result.stdout)
        self.assertEqual(result.returncode == 0, success, result.stdout + result.stderr)
        self.assertEqual(parsed['ok'], success, parsed)
        return parsed

    def test_install_upgrade_preserve_old_configuration_and_register_native_menu(self):
        before = self.config.read_bytes()
        self.install('--no-setup')
        self.assertEqual(self.config.read_bytes(), before)
        self.assertFalse((self.root / 'state/omarchy-workspaces/manifest.json').exists())
        self.assertTrue((self.plugin / 'manifest.json').is_file())
        self.assertFalse((self.root / 'config/omarchy/plugins').exists())
        self.assertEqual(json.loads(self.ipc.read_text())['launches'], [])
        self.assertEqual(json.loads((self.plugin / 'manifest.json').read_text())['version'], __version__)
        self.run_cli('gui')
        d = json.loads(self.ipc.read_text())
        self.assertEqual(d['shell_calls'][-1], ['shell', 'summon', 'lambert.workspaces', '{}'])
        self.assertNotIn('tui_launches', d)
        self.assertEqual(len(list(self.plugin.rglob('__pycache__'))), 0)

    def test_overlay_launcher_is_recognized_and_preserved_on_repeated_install(self):
        from omarchy_workspaces.plugin import OVERLAY_LAUNCHER
        self.binary.write_text(OVERLAY_LAUNCHER)
        self.binary.chmod(0o755)
        before = self.config.read_bytes()
        state = self.bridge({'action': 'status'})['state']
        self.assertTrue(state['installed'])
        self.assertFalse(state['needsInstall'])
        for _ in range(2):
            self.install('--backend-only', source=self.package)
            self.assertEqual(self.binary.read_text(), OVERLAY_LAUNCHER)
            self.assertEqual(self.config.read_bytes(), before)

    def test_overlay_marker_does_not_authorize_unknown_launcher(self):
        self.binary.write_text('#!/bin/sh\n# managed-by: omarchy-overlay-dotfiles\nexit 0\n')
        before = self.binary.read_bytes()
        result = self.install('--backend-only', success=False)
        self.assertIn('停止覆盖', result.stderr)
        self.assertEqual(self.binary.read_bytes(), before)

    def test_bridge_save_moves_only_selected_app_and_refuses_stale_edit(self):
        self.c['apps']['other'] = {'name': 'Other', 'workspace': 2, 'command': ['other'],
                                   'matches': [{'initial_class': 'Other'}], 'shortcuts': []}
        self.config.write_text(dumps(self.c))
        self.run_cli('apply')
        d = json.loads(self.ipc.read_text())
        d['clients'] = [{'address': '0xa', 'initialClass': 'Slack', 'mapped': True, 'workspace': {'id': 7, 'name': '7'}},
                        {'address': '0xb', 'initialClass': 'Other', 'mapped': True, 'workspace': {'id': 8, 'name': '8'}}]
        self.ipc.write_text(json.dumps(d))
        state = self.bridge({'action': 'status'})['state']
        self.assertTrue(state['active'])
        request = {'action': 'set', 'app_id': 'slack', 'workspace': 5, 'existing_window': 'focus',
                   'move_existing': True, 'revision': state['revision']}
        changed = self.bridge(request)
        self.assertNotEqual(changed['state']['revision'], state['revision'])
        d = json.loads(self.ipc.read_text())
        self.assertEqual([c['workspace']['id'] for c in d['clients']], [5, 8])
        request['workspace'] = 6
        rejected = self.bridge(request, success=False)
        self.assertIn('刷新', rejected['message'])
        self.assertEqual(load(self.config)['apps']['slack']['workspace'], 5)

    def test_bridge_reset_keeps_plugin_and_configuration_then_uninstall_removes_owned_ui(self):
        self.run_cli('apply')
        state = self.bridge({'action': 'status'})['state']
        self.bridge({'action': 'reset', 'revision': state['revision']})
        self.assertTrue(self.binary.exists())
        self.assertTrue(self.config.exists())
        self.assertTrue(self.plugin.exists())
        self.assertFalse((self.root / 'data/applications/ows-slack.desktop').exists())
        state = self.bridge({'action': 'status'})['state']
        self.assertFalse(state['active'])
        self.bridge({'action': 'apply', 'revision': state['revision']})
        self.assertTrue((self.root / 'data/applications/ows-slack.desktop').exists())
        self.run_cli('uninstall')
        self.assertFalse(self.plugin.exists())
        self.assertFalse(self.binary.exists())
        self.assertTrue(self.config.exists())

    def test_native_add_backend_bootstrap_updates_version_without_touching_checkout(self):
        self.run_cli('apply')
        config = self.config.read_bytes()
        manifest = (self.plugin / 'manifest.json').read_bytes()
        (self.plugin / '.git').mkdir()
        backend = self.root / 'data/omarchy-workspaces/omarchy_workspaces/__init__.py'
        backend.write_text('__version__ = "1.1.3"\n')
        state = self.bridge({'action': 'status'})['state']
        self.assertTrue(state['needsInstall'])
        rejected = self.bridge({'action': 'reset', 'revision': state['revision']}, success=False)
        self.assertIn('版本', rejected['message'])
        result = self.bridge({'action': 'install'})
        self.assertFalse(result['state']['needsInstall'])
        self.assertEqual(self.config.read_bytes(), config)
        self.assertEqual((self.plugin / 'manifest.json').read_bytes(), manifest)
        self.assertTrue((self.plugin / '.git').is_dir())
        self.assertEqual(len(list(self.plugin.rglob('__pycache__'))), 0)

    def test_failed_menu_registration_rolls_back_runtime_plugin_and_launcher(self):
        menu = self.root / '.config/omarchy/extensions/omarchy-menu.jsonc'
        menu.write_text('{broken')
        binary = self.binary.read_bytes()
        own = (self.plugin / '.ows-install.json').read_bytes()
        self.install(success=False)
        self.assertEqual(menu.read_text(), '{broken')
        self.assertEqual(self.binary.read_bytes(), binary)
        self.assertEqual((self.plugin / '.ows-install.json').read_bytes(), own)
        self.assertEqual(self.run_cli('--version').stdout.strip(), __version__)

    def test_backend_can_be_repaired_before_an_interrupted_configuration_is_recovered(self):
        self.run_cli('apply')
        previous = self.config.read_bytes()
        mode = self.config.stat().st_mode & 0o777
        interrupted = previous + b'\n# interrupted update\n'
        self.config.write_bytes(interrupted)
        journal = self.root / 'state/omarchy-workspaces/pending.json'
        journal.write_text(json.dumps({
            'before': {str(self.config): {'data': base64.b64encode(previous).decode(), 'mode': mode}},
            'after': {str(self.config): {'data': base64.b64encode(interrupted).decode(), 'mode': mode}},
        }))
        pending = journal.read_bytes()
        (self.root / 'data/omarchy-workspaces/omarchy_workspaces/__init__.py').write_text('__version__ = "1.1.3"\n')
        installed = self.bridge({'action': 'install'})
        self.assertFalse(installed['state']['needsInstall'])
        self.assertTrue(installed['state']['pending'])
        self.assertEqual(journal.read_bytes(), pending)
        self.assertEqual(self.config.read_bytes(), interrupted)
        self.bridge({'action': 'recover'})
        self.assertEqual(self.config.read_bytes(), previous)
        self.assertFalse(journal.exists())

    def test_upgrade_does_not_overwrite_user_plugin_changes(self):
        panel = self.plugin / 'Panel.qml'
        panel.write_text(panel.read_text() + '\n// local user change\n')
        previous = panel.read_bytes()
        self.install(success=False)
        self.assertEqual(panel.read_bytes(), previous)
        self.run_cli('uninstall')
        self.assertTrue(self.plugin.exists())
        self.assertEqual(panel.read_bytes(), previous)

    def test_status_reports_missing_hyprland_include(self):
        self.run_cli('apply')
        main = self.root / 'config/hypr/hyprland.lua'
        main.write_text('-- removed managed include\n')
        state = self.bridge({'action': 'status'})['state']
        self.assertFalse(state['active'])
        self.assertTrue(any('加载入口' in issue for issue in state['issues']))

    def test_invalid_bridge_requests_never_write_configuration(self):
        previous = self.config.read_bytes()
        for request in ({'action': 'shell', 'command': 'touch /tmp/should-never-exist'},
                        {'action': 'terminal', 'view': 'unknown'},
                        {'action': 'set', 'app_id': 'slack', 'workspace': 6}, []):
            self.bridge(request, success=False)
        self.assertEqual(self.config.read_bytes(), previous)

    def test_cli_single_app_arrange_rejects_unknown_id(self):
        self.run_cli('apply')
        self.run_cli('arrange', '--app', 'missing', success=False)
        self.run_cli('arrange', '--app', 'slack', '--dry-run')
