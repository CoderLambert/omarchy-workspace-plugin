"""The offline payload must not depend on Linux's per-argument size limit."""
import base64
import random
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


class OfflineReleaseTests(unittest.TestCase):
    def test_large_payload_extracts_with_spaces_and_rejects_tampering(self):
        source = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory(prefix='ows large release ') as directory:
            root = Path(directory)
            package = root / 'source'
            shutil.copytree(source, package, ignore=shutil.ignore_patterns('__pycache__', '*.pyc',
                                                                         'install-omarchy-workspaces.sh', 'SHA256SUMS'))
            content = base64.b64encode(random.Random(7).randbytes(150000)).decode()
            (package / 'LARGE-PAYLOAD.md').write_text(content)
            installer = root / 'offline installer.sh'
            subprocess.run([sys.executable, str(package / 'build_release.py'), str(installer)],
                           check=True, capture_output=True, text=True, timeout=20)
            target = root / 'extracted source'
            result = subprocess.run(['bash', str(installer), '--extract', str(target)],
                                    capture_output=True, text=True, timeout=20)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual((target / 'LARGE-PAYLOAD.md').read_text(), content)
            # A package can extract successfully while still omitting runtime
            # imports. Verify translation and theme assets survive packaging.
            for relative in ('qml/Strings.js', 'qml/Theme.qml',
                             'scripts/ui_fixture.py', 'scripts/verify_qml.py',
                             'tests/ui/tst_workspaces.qml'):
                self.assertEqual((target / relative).read_bytes(), (package / relative).read_bytes())
            # Corrupt one payload byte; refuse it before extracting any files.
            header, payload = installer.read_text().split('\n# __OWS_WORKSPACES_PAYLOAD__\n', 1)
            payload = ('A' if payload[0] != 'A' else 'B') + payload[1:]
            installer.write_text(header + '\n# __OWS_WORKSPACES_PAYLOAD__\n' + payload)
            bad_target = root / 'should-not-exist'
            result = subprocess.run(['bash', str(installer), '--extract', str(bad_target)],
                                    capture_output=True, text=True, timeout=20)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('校验失败', result.stderr)
            self.assertFalse(bad_target.exists())
