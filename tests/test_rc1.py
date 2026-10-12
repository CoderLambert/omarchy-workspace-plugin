"""Reliability regressions for the release-candidate review."""
import copy
from contextlib import redirect_stdout
import io
import unittest
from unittest.mock import patch

from omarchy_workspaces.core import Error
from omarchy_workspaces.cli import review_setup_shortcuts, parser
from omarchy_workspaces.hypr import binding_signature, generate
from test_workspaces import Environment, cfg, client


class ArrangeProtectionTests(Environment):
    def setUp(self):
        super().setUp()
        self.m.apply(cfg())
        normal = client('0x1', workspace=8)
        scratch = client('0x2'); scratch['workspace'] = {'id': -99, 'name': 'special:scratchpad'}
        other = client('0x3'); other['workspace'] = {'id': -2, 'name': 'special:notes'}
        unnamed = client('0x4'); unnamed['workspace'] = {'id': -4, 'name': 'unknown'}
        self.h.clients = [normal, scratch, other, unnamed]

    def test_default_and_single_app_arrange_preserve_all_special_workspaces(self):
        self.assertEqual(len(self.m.arrange(app_id='slack')), 1)
        self.assertEqual(self.h.moved, [('0x1', 4)])
        self.assertEqual(self.h.clients[1]['workspace']['name'], 'special:scratchpad')

    def test_explicit_include_special_moves_them_only_after_dry_run(self):
        self.assertEqual(len(self.m.arrange(dry=True, include_special=True)), 4)
        self.assertEqual(self.h.moved, [])
        self.assertEqual(len(self.m.arrange(include_special=True)), 4)
        self.assertEqual(len(self.h.moved), 4)

    def test_cli_defaults_to_protect_and_exposes_opt_in(self):
        self.assertFalse(parser().parse_args(['arrange']).include_special)
        self.assertTrue(parser().parse_args(['arrange', '--include-special']).include_special)


class ShortcutPreviewTests(Environment):
    def setUp(self):
        super().setUp()
        self.c = cfg()
        self.c['apps']['slack'].update(shortcuts=['SUPER + A', 'SUPER + B', 'SUPER + C'], replace_shortcuts=True)
        self.h.binds = self.h.original_binds = [
            {'combo': 'SUPER + A', 'modmask': 64, 'key': 'A', 'dispatcher': 'exec', 'arg': 'old-a', 'description': 'Original A'},
            {'combo': 'SUPER + B', 'modmask': 64, 'key': 'B', 'dispatcher': 'exec', 'arg': 'old-b', 'description': 'Original B'}]

    def test_noninteractive_setup_skips_conflicts_but_keeps_app_and_safe_keys(self):
        output = io.StringIO()
        with patch('omarchy_workspaces.cli.sys.stdin.isatty', return_value=False), patch('builtins.input', side_effect=AssertionError('Must not prompt')), redirect_stdout(output):
            candidate, signature = review_setup_shortcuts(self.m, self.c)
        self.assertEqual(candidate['apps']['slack']['shortcuts'], ['SUPER + C'])
        self.assertIn('Original A', output.getvalue())
        self.assertIn('old-a', output.getvalue())
        self.assertIn('launch slack', output.getvalue())
        self.m.apply(candidate, expected_bindings=signature)
        self.assertIn('slack', self.m.applied_config()['apps'])
        self.assertEqual(self.c['apps']['slack']['shortcuts'], ['SUPER + A', 'SUPER + B', 'SUPER + C'])

    def test_each_conflict_needs_explicit_approval(self):
        decisions = []
        def decide(key, app_id, existing):
            decisions.append(key)
            return key == 'SUPER + A'
        with redirect_stdout(io.StringIO()):
            candidate, signature = review_setup_shortcuts(self.m, self.c, decide)
        self.assertEqual(decisions, ['SUPER + A', 'SUPER + B'])
        self.assertEqual(candidate['apps']['slack']['shortcuts'], ['SUPER + A', 'SUPER + C'])
        self.m.apply(candidate, expected_bindings=signature)

    def test_binding_change_after_preview_aborts_before_writing(self):
        with redirect_stdout(io.StringIO()):
            candidate, signature = review_setup_shortcuts(self.m, self.c, lambda *args: True)
        self.h.original_binds = copy.deepcopy(self.h.binds)
        self.h.original_binds[0]['arg'] = 'changed-after-confirmation'
        before = self.m.p.file.read_bytes() if self.m.p.file.exists() else None
        with self.assertRaisesRegex(Error, '预览后'):
            self.m.apply(candidate, expected_bindings=signature)
        self.assertEqual(self.m.p.file.read_bytes() if self.m.p.file.exists() else None, before)

    def test_lua_callback_numbers_are_not_treated_as_binding_changes(self):
        first = [{'combo': 'SUPER + A', 'modmask': 64, 'key': 'A', 'dispatcher': '__lua', 'arg': '10', 'description': 'User shortcut'}]
        second = [dict(first[0], arg='11')]
        self.assertEqual(binding_signature(first), binding_signature(second))

    def test_confirming_one_key_never_authorizes_a_different_key(self):
        with redirect_stdout(io.StringIO()):
            candidate, signature = review_setup_shortcuts(self.m, self.c, lambda key, *args: key == 'SUPER + A')
        self.assertFalse(candidate['apps']['slack']['replace_shortcuts'])
        self.assertEqual(candidate['apps']['slack']['replace_shortcut_keys'], ['SUPER + A'])
        later = [{'modmask': 64, 'key': 'C', 'dispatcher': 'exec', 'arg': 'new-foreign-binding'}]
        with self.assertRaisesRegex(Error, '已绑定'):
            generate(candidate, 'lua', self.p.binary, later)
