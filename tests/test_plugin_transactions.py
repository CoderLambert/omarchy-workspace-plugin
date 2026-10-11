"""Regressions for concurrent plugin/CLI edits and desktop update adoption."""
import copy
import json
from pathlib import Path

from omarchy_workspaces.core import Error, dumps, empty_config, load
from omarchy_workspaces.desktop import parse
from test_workspaces import Environment, cfg


class RevisionTests(Environment):
    def test_stale_edit_is_rejected_without_overwriting_the_first_change(self):
        self.m.apply(cfg())
        revision = self.m.revision()
        first = load(self.p.file)
        second = copy.deepcopy(first)
        first["apps"]["slack"]["workspace"] = 5
        second["apps"]["slack"]["existing_window"] = "move"
        self.m.apply(first, expected_revision=revision)
        files_before = {target: Path(target).read_bytes()
                        for target in self.m.state()["files"]}
        config_before = self.p.file.read_bytes()
        state_before = self.m.state_file.read_bytes()
        reloads_before = self.h.reloads

        with self.assertRaisesRegex(Error, "配置已被其他操作修改"):
            self.m.apply(second, expected_revision=revision)

        self.assertEqual(self.h.reloads, reloads_before)
        self.assertEqual(self.p.file.read_bytes(), config_before)
        self.assertEqual(self.m.state_file.read_bytes(), state_before)
        for target, content in files_before.items():
            self.assertEqual(Path(target).read_bytes(), content)
        self.assertFalse(self.m.journal.exists())

        refreshed_revision = self.m.revision()
        second = load(self.p.file)
        second["apps"]["slack"]["existing_window"] = "move"
        self.m.apply(second, expected_revision=refreshed_revision)
        final = self.m.applied_config()["apps"]["slack"]
        self.assertEqual(final["workspace"], 5)
        self.assertEqual(final["existing_window"], "move")

    def test_manual_draft_edit_invalidates_revision(self):
        self.m.apply(cfg())
        revision = self.m.revision()
        self.p.file.write_text(self.p.file.read_text() + "# user note\n")
        with self.assertRaisesRegex(Error, "配置已被其他操作修改"):
            self.m.apply(cfg(), expected_revision=revision)
        self.assertTrue(self.p.file.read_text().endswith("# user note\n"))

    def test_runtime_state_edit_invalidates_revision(self):
        self.m.apply(cfg())
        revision = self.m.revision()
        state = self.m.state()
        state["version"] = 2
        self.m.state_file.write_text(json.dumps(state))
        with self.assertRaisesRegex(Error, "配置已被其他操作修改"):
            self.m.apply(cfg(), expected_revision=revision)

    def test_stale_reset_does_not_remove_a_new_configuration(self):
        self.m.apply(cfg())
        revision = self.m.revision()
        updated = cfg()
        updated["apps"]["slack"]["workspace"] = 6
        self.m.apply(updated)
        with self.assertRaisesRegex(Error, "配置已被其他操作修改"):
            self.m.uninstall(expected_revision=revision)
        self.assertTrue((self.p.apps / "ows-slack.desktop").exists())
        self.assertEqual(self.m.applied_config()["apps"]["slack"]["workspace"], 6)

    def test_current_revision_allows_uninstall(self):
        self.m.apply(cfg())
        self.m.uninstall(expected_revision=self.m.revision())
        self.assertFalse(self.m.state_file.exists())
        self.assertFalse((self.p.apps / "ows-slack.desktop").exists())


class AdoptSourceTests(Environment):
    def test_adopt_does_not_freeze_an_unchanged_system_desktop_override(self):
        self.m.apply(cfg())
        updated = self.original.replace("/usr/bin/slack", "/usr/bin/updated-slack")
        self.system.write_text(updated)
        self.m.apply(cfg(), adopt=True)
        effective = parse((self.p.apps / "slack.desktop").read_text())
        self.assertEqual(effective["Exec"], "/usr/bin/updated-slack %U")
        self.m.uninstall()
        self.assertFalse((self.p.apps / "slack.desktop").exists())
        self.assertEqual(self.system.read_text(), updated)

    def test_adopt_preserves_actual_external_changes_as_the_restore_baseline(self):
        self.m.apply(cfg())
        override = self.p.apps / "slack.desktop"
        changed = self.original.replace("/usr/bin/slack", "/usr/bin/custom-slack")
        override.write_text(changed)
        self.m.apply(cfg(), adopt=True)
        self.assertEqual(parse(override.read_text())["Exec"], "/usr/bin/custom-slack %U")
        self.m.uninstall()
        self.assertEqual(override.read_text(), changed)

    def test_removal_draft_adopts_external_desktop_and_relinquishes_ownership(self):
        self.m.apply(cfg())
        override = self.p.apps / "slack.desktop"
        changed = self.original.replace("/usr/bin/slack", "/usr/bin/user-slack")
        override.write_text(changed)
        override.chmod(0o640)
        self.p.file.write_text(dumps(empty_config()))
        with self.assertRaises(Error):
            self.m.apply(load(self.p.file))

        self.m.apply(load(self.p.file), adopt=True, text=self.p.file.read_text())

        self.assertEqual(override.read_text(), changed)
        self.assertEqual(override.stat().st_mode & 0o777, 0o640)
        self.assertNotIn(str(override), self.m.state()["files"])
        self.assertFalse((self.p.apps / "ows-slack.desktop").exists())
        self.assertEqual(self.m.applied_config()["apps"], {})
        self.m.uninstall()
        self.assertEqual(override.read_text(), changed)
        self.assertEqual(override.stat().st_mode & 0o777, 0o640)

    def test_removal_adopt_restores_unchanged_files_to_the_original_baseline(self):
        self.m.apply(cfg())
        self.m.apply(empty_config(), adopt=True)
        self.assertFalse((self.p.apps / "slack.desktop").exists())
        self.assertFalse((self.p.apps / "ows-slack.desktop").exists())
        self.assertEqual(self.system.read_text(), self.original)

    def test_removal_adopt_still_refuses_symlinks(self):
        self.m.apply(cfg())
        override = self.p.apps / "slack.desktop"
        override.unlink()
        override.symlink_to(self.system)
        with self.assertRaisesRegex(Error, "符号链接"):
            self.m.apply(empty_config(), adopt=True)
        self.assertTrue(override.is_symlink())
        self.assertEqual(self.system.read_text(), self.original)
        self.assertIn("slack", self.m.applied_config()["apps"])
