import base64
import hashlib
import json
from pathlib import Path
from unittest.mock import patch

from omarchy_workspaces.core import Error, atomic
from omarchy_workspaces.menu import BEGIN, END, KEY, check, locations, parse_jsonc, register, unregister
from test_workspaces import Environment


class MenuTests(Environment):
    def setUp(self):
        super().setUp()
        self.which = patch('omarchy_workspaces.menu.shutil.which',return_value='/usr/bin/omarchy-launch-tui')
        self.refresh = patch('omarchy_workspaces.menu.refresh',return_value=True)
        self.which.start()
        self.refresh.start()
        self.addCleanup(self.which.stop)
        self.addCleanup(self.refresh.stop)
        self.target, self.record = locations(self.p)

    def write(self,text):
        self.target.parent.mkdir(parents=True,exist_ok=True)
        self.target.write_text(text)

    def legacy_registration(self, *, recorded=False):
        legacy = self.p.config / 'omarchy/extensions/omarchy-menu.jsonc'
        legacy.parent.mkdir(parents=True, exist_ok=True)
        original = '{\n // old user menu\n "legacy": {"label":"Legacy custom row"}\n}\n'
        managed = ('{\n // old user menu\n "legacy": {"label":"Legacy custom row"},\n'
                   + BEGIN + '\n "' + KEY + '": {"label":"工作区配置","action":"old-config"},\n'
                   + END + '\n}\n')
        legacy.write_text(managed)
        legacy.chmod(0o640)
        state = {'original': {'data': base64.b64encode(original.encode()).decode(), 'mode': 0o640},
                 'sha256': hashlib.sha256(managed.encode()).hexdigest()}
        if recorded:
            state['target'] = str(legacy)
        self.record.write_text(json.dumps(state))
        self.record.chmod(0o600)
        return legacy, original

    def test_native_menu_uses_home_even_when_xdg_config_is_custom(self):
        self.assertEqual(self.target, self.p.home / '.config/omarchy/extensions/omarchy-menu.jsonc')
        self.assertNotEqual(self.target, self.p.config / 'omarchy/extensions/omarchy-menu.jsonc')
        register(self.p)
        self.assertFalse((self.p.config / 'omarchy/extensions/omarchy-menu.jsonc').exists())
        self.assertEqual(json.loads(self.record.read_text())['target'], str(self.target))

    def test_registers_root_row_and_repeat_has_only_one_entry(self):
        self.write('{\n // existing Omarchy comments\n}\n')
        for _ in range(2):
            self.assertTrue(register(self.p))
            check(self.p)
            text = self.target.read_text()
            self.assertEqual(text.count(BEGIN),1)
            self.assertEqual(parse_jsonc(text)[KEY]['label'],'工作区配置')
            self.assertIn('existing Omarchy comments',text)

    def test_jsonc_comments_strings_trailing_commas_and_original_restore(self):
        original = '{\n/* retain */ "personal": {"label":"a ,} \\\" // b", "action":"open https://example.com",}, // tail\n}\n'
        self.write(original)
        self.target.chmod(0o640)
        register(self.p)
        self.assertEqual(parse_jsonc(self.target.read_text())['personal'],parse_jsonc(original)['personal'])
        unregister(self.p)
        self.assertEqual(self.target.read_text(),original)
        self.assertEqual(self.target.stat().st_mode & 0o777,0o640)
        self.assertFalse(self.record.exists())

    def test_later_user_entry_preserved_when_removing_our_row(self):
        self.write('{"personal":{"label":"Personal"}}\n')
        register(self.p)
        text = self.target.read_text().replace(END+'\n}',END+'\n "later":{"label":"New user row"},\n}')
        self.target.write_text(text)
        unregister(self.p)
        data = parse_jsonc(self.target.read_text())
        self.assertNotIn(KEY,data)
        self.assertIn('personal',data)
        self.assertIn('later',data)

    def test_existing_unmanaged_same_id_is_not_overwritten(self):
        self.write('{"ows-workspaces":{"label":"User custom"}}')
        before = self.target.read_bytes()
        with self.assertRaisesRegex(Error,'同名非受管'):
            register(self.p)
        self.assertEqual(self.target.read_bytes(),before)
        self.assertFalse(self.record.exists())

    def test_invalid_existing_jsonc_is_not_overwritten(self):
        self.write('{"personal": nope}')
        before = self.target.read_bytes()
        with self.assertRaises(Error):
            register(self.p)
        self.assertEqual(self.target.read_bytes(),before)

    def test_uninstall_removes_new_extension_file(self):
        register(self.p)
        unregister(self.p)
        self.assertFalse(self.target.exists())

    def test_missing_menu_reported_and_failed_refresh_keeps_entry(self):
        with self.assertRaisesRegex(Error,'repair-menu'):
            check(self.p)
        with patch('omarchy_workspaces.menu.refresh',return_value=False):
            self.assertFalse(register(self.p))
        check(self.p)

    def test_upstream_sample_format_accepted(self):
        sample = Path(__file__).resolve().parents[1] / 'reference/omarchy-menu.sample.jsonc'
        if sample.exists():
            self.write(sample.read_text())
            register(self.p)
            self.assertEqual(list(parse_jsonc(self.target.read_text())),[KEY])

    def test_legacy_xdg_registration_migrates_preserving_both_user_menus(self):
        legacy, _ = self.legacy_registration()
        legacy.write_text(legacy.read_text().replace(END + '\n}', END + '\n "later":{"label":"Later custom row"},\n}'))
        legacy.chmod(0o604)
        native_original = '{\n // native user menu\n "native":{"label":"Native custom row"}\n}\n'
        self.write(native_original)
        self.target.chmod(0o660)

        register(self.p)

        self.assertEqual(set(parse_jsonc(legacy.read_text())), {'legacy', 'later'})
        self.assertIn('old user menu', legacy.read_text())
        self.assertEqual(legacy.stat().st_mode & 0o777, 0o604)
        self.assertEqual(set(parse_jsonc(self.target.read_text())), {'native', KEY})
        self.assertIn('native user menu', self.target.read_text())
        self.assertEqual(self.target.stat().st_mode & 0o777, 0o660)
        self.assertEqual(json.loads(self.record.read_text())['target'], str(self.target))
        check(self.p)

        old_after_migration = legacy.read_bytes()
        unregister(self.p)
        self.assertEqual(self.target.read_text(), native_original)
        self.assertEqual(self.target.stat().st_mode & 0o777, 0o660)
        self.assertEqual(legacy.read_bytes(), old_after_migration)

    def test_failed_migration_restores_both_locations_and_old_registration(self):
        legacy, _ = self.legacy_registration()
        self.write('{"native":{"label":"Keep native"}}\n')
        self.target.chmod(0o660)
        before = {path: (path.read_bytes(), path.stat().st_mode & 0o777)
                  for path in (legacy, self.target, self.record)}
        def fail_record_write(path, data, mode=0o600):
            if path == self.record:
                raise OSError('injected record failure')
            return atomic(path, data, mode)

        with patch('omarchy_workspaces.menu.atomic', side_effect=fail_record_write):
            with self.assertRaisesRegex(OSError, 'injected record failure'):
                register(self.p)

        for path, (content, mode) in before.items():
            self.assertEqual(path.read_bytes(), content)
            self.assertEqual(path.stat().st_mode & 0o777, mode)

    def test_migration_conflict_does_not_touch_legacy_registration(self):
        legacy, _ = self.legacy_registration()
        self.write('{"ows-workspaces":{"label":"User owned row"}}\n')
        before = {path: path.read_bytes() for path in (legacy, self.target, self.record)}
        with self.assertRaisesRegex(Error, '同名非受管'):
            register(self.p)
        for path, content in before.items():
            self.assertEqual(path.read_bytes(), content)

    def test_migration_refuses_a_symlink_at_the_old_location(self):
        legacy, _ = self.legacy_registration()
        self.write('{"native":{"label":"Keep native"}}\n')
        old_record = self.record.read_bytes()
        native = self.target.read_bytes()
        legacy.unlink()
        legacy.symlink_to(self.target)
        with self.assertRaisesRegex(Error, '符号链接'):
            register(self.p)
        self.assertTrue(legacy.is_symlink())
        self.assertEqual(self.record.read_bytes(), old_record)
        self.assertEqual(self.target.read_bytes(), native)

    def test_uninstall_without_migration_restores_the_legacy_location(self):
        legacy, original = self.legacy_registration()
        native = '{"native":{"label":"Unrelated native row"}}\n'
        self.write(native)
        unregister(self.p)
        self.assertEqual(legacy.read_text(), original)
        self.assertEqual(self.target.read_text(), native)
        self.assertFalse(self.record.exists())

    def test_saved_target_survives_later_xdg_config_change(self):
        legacy, original = self.legacy_registration(recorded=True)
        self.p.config = self.p.home / 'new-xdg-config'
        unregister(self.p)
        self.assertEqual(legacy.read_text(), original)
        self.assertFalse(self.record.exists())
