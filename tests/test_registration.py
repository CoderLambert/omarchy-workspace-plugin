"""Add installed Omarchy applications without the manual entrance wizard."""
import copy
import io
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

from omarchy_workspaces.cli import choose, menu, quick_register
from omarchy_workspaces.core import Error, empty_config, load
from omarchy_workspaces.registration import find_entries, window_matches
from test_workspaces import Environment, cfg, client


class SearchTests(unittest.TestCase):
    def test_plain_name_finds_entry_beyond_first_page(self):
        values = [f'App {i}' for i in range(90)] + ['Obsidian']
        with redirect_stdout(io.StringIO()), patch('builtins.input', side_effect=['Obsidian', '1']):
            self.assertEqual(choose('入口', values), 'Obsidian')

    def test_legacy_slash_search_still_works(self):
        with redirect_stdout(io.StringIO()), patch('builtins.input', side_effect=['/obsidian', '1']):
            self.assertEqual(choose('入口', ['Slack', 'Obsidian']), 'Obsidian')

    def test_exact_name_beats_related_entries_and_url_handler(self):
        entries = [
            {'id':'obsidian.desktop', 'Name':'Obsidian'},
            {'id':'obsidian-handler.desktop', 'Name':'Obsidian URL Handler'},
            {'id':'related.desktop', 'Name':'Obsidian Tools'},
        ]
        self.assertEqual(find_entries(entries, 'OBSIDIAN'), [entries[0]])

    def test_localized_name_can_find_original_entry(self):
        entry = {'id':'obsidian.desktop', 'Name':'Obsidian', 'Name[zh_CN]':'黑曜石'}
        self.assertEqual(find_entries([entry], '黑曜石'), [entry])

    def test_browser_title_is_not_an_application_identity(self):
        self.assertEqual(window_matches([client(cls='google-chrome')], 'ChatGPT'), [])


class RegistrationTests(Environment):
    def add_entry(self, identity='obsidian', desktop='obsidian.desktop', name='Obsidian'):
        path = self.system.parent / desktop
        path.write_text(f'[Desktop Entry]\nType=Application\nName={name}\nExec=obsidian %U\n' + (f'StartupWMClass={identity}\n' if identity else ''))
        return path

    def register(self, config, *args, **kwargs):
        with redirect_stdout(io.StringIO()):
            return quick_register(self.m, config, *args, **kwargs)

    def test_uppercase_app_name_needs_no_manual_identity_selection(self):
        self.add_entry(identity='')
        self.h.clients = [client(cls='obsidian')]
        config = empty_config()
        with patch('builtins.input', side_effect=AssertionError('Unexpected prompt')), patch.object(self.m.desktops, 'launch') as launch:
            self.assertEqual(self.register(config, 'Obsidian', workspace=2), 'obsidian')
        self.assertEqual(config['apps']['obsidian']['desktop'], 'obsidian.desktop')
        self.assertEqual(config['apps']['obsidian']['matches'], [{'initial_class':'obsidian'}])
        launch.assert_not_called()

    def test_default_add_only_asks_workspace(self):
        self.add_entry()
        config = empty_config()
        with patch('builtins.input', return_value='7') as ask:
            self.register(config, 'Obsidian')
        self.assertEqual(ask.call_count, 1)
        self.assertIn('放到哪个工作区', ask.call_args.args[0])
        self.assertEqual(config['apps']['obsidian']['workspace'], 7)

    def test_no_window_identity_leaves_config_untouched_and_does_not_launch(self):
        self.add_entry(identity='')
        config = cfg()
        before = copy.deepcopy(config)
        with patch.object(self.m.desktops, 'launch') as launch, self.assertRaisesRegex(Error, '请先打开'):
            self.register(config, 'Obsidian', workspace=2)
        self.assertEqual(config, before)
        launch.assert_not_called()

    def test_explicit_executable_fallback_does_not_require_desktop(self):
        executable = self.p.home / 'Obsidian.AppImage'
        executable.write_text('#!/bin/sh\n')
        executable.chmod(0o755)
        self.h.clients = [client(cls='obsidian')]
        config = empty_config()
        self.register(config, 'Obsidian', workspace=2, command=str(executable))
        self.assertEqual(config['apps']['obsidian']['command'], [str(executable)])

    def test_localized_command_name_gets_id_from_executable(self):
        executable = self.p.home / 'obsidian'
        executable.write_text('#!/bin/sh\n')
        executable.chmod(0o755)
        self.h.clients = [client(cls='obsidian')]
        config = empty_config()
        self.assertEqual(self.register(config, '黑曜石', workspace=2, command=str(executable)), 'obsidian')

    def test_missing_installation_reports_actionable_error_without_config_changes(self):
        config = cfg()
        before = copy.deepcopy(config)
        with patch('omarchy_workspaces.registration.shutil.which', return_value=None), self.assertRaisesRegex(Error, '未找到.*安装入口或启动命令'):
            self.register(config, 'UnknownApplication', workspace=2)
        self.assertEqual(config, before)

    def test_invalid_workspace_does_not_commit_registration(self):
        self.add_entry()
        config = cfg()
        before = copy.deepcopy(config)
        with self.assertRaises(Error):
            self.register(config, 'Obsidian', workspace=0)
        self.assertEqual(config, before)

    def test_ambiguous_desktops_ask_for_selection(self):
        self.add_entry(desktop='obsidian.desktop')
        self.add_entry(desktop='obsidian-alternative.desktop')
        config = empty_config()
        with patch('builtins.input', return_value='2') as ask:
            self.register(config, 'Obsidian', workspace=2)
        self.assertEqual(ask.call_count, 1)
        self.assertEqual(config['apps']['obsidian']['desktop'], 'obsidian.desktop')

    def test_existing_desktop_under_another_id_updates_instead_of_duplicates(self):
        self.add_entry()
        config = empty_config()
        config['apps']['notes'] = {'name':'Notes', 'desktop':'obsidian.desktop', 'matches':[{'initial_class':'obsidian'}], 'workspace':5, 'shortcuts':[]}
        self.assertEqual(self.register(config, 'Obsidian', workspace=2), 'notes')
        self.assertEqual(list(config['apps']), ['notes'])
        self.assertEqual(config['apps']['notes']['workspace'], 2)

    def test_desktop_filename_with_spaces_is_registered_and_applied(self):
        self.add_entry(identity='clash-verge', desktop='Clash Verge.desktop', name='Clash Verge')
        config = empty_config()
        self.register(config, 'Clash Verge', workspace=4)
        self.m.apply(config)
        self.assertEqual(load(self.p.file)['apps']['clash_verge']['desktop'], 'Clash Verge.desktop')
        self.assertTrue((self.p.apps / 'Clash Verge.desktop').is_file())

    def test_desktop_filename_cannot_escape_application_directory(self):
        self.add_entry()
        config = empty_config()
        self.register(config, 'Obsidian', workspace=2)
        config['apps']['obsidian']['desktop'] = '../obsidian.desktop'
        with self.assertRaises(Error):
            self.m.apply(config)

    def test_simple_menu_add_only_moves_the_added_app(self):
        self.add_entry()
        self.m.apply(cfg())
        self.h.clients = [client(workspace=7), client('0x2', cls='obsidian', workspace=6)]
        with redirect_stdout(io.StringIO()), patch('builtins.input', side_effect=['5', 'Obsidian', '2', '0']):
            menu(self.m)
        self.assertEqual(load(self.p.file)['apps']['obsidian']['workspace'], 2)
        self.assertEqual(self.h.moved, [('0x2', 2)])
