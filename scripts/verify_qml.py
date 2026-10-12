"""Run isolated UI checks with Qt 6 QtTest; never call the live backend."""
import argparse
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import sys
sys.dont_write_bytecode = True
from ui_fixture import prepare_ui_fixture

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--output', type=Path)
parser.add_argument('--runner', type=Path, help='Qt 6 qmltestrunner executable')
args = parser.parse_args()
source = Path(__file__).resolve().parents[1]
check = args.output.resolve() if args.output else Path(tempfile.mkdtemp(prefix='workspaces-qml-qa-'))
if check == source or source in check.parents:
    parser.error('--output must be outside the plugin/source directory')
runner = args.runner or (Path('/usr/lib/qt6/bin/qmltestrunner') if Path('/usr/lib/qt6/bin/qmltestrunner').is_file() else shutil.which('qmltestrunner'))
if not runner:
    parser.error('Qt 6 qmltestrunner is required')
prepare_ui_fixture(source, check)
panel = check / 'Panel.qml'
panel.write_text(panel.read_text().replace('id: root', 'id: root\n    function qa(code) { return eval(code); }', 1))
shutil.copy2(source / 'tests/ui/tst_workspaces.qml', check / 'tst_workspaces.qml')
env = dict(os.environ, QT_QPA_PLATFORM='offscreen', QT_QUICK_BACKEND='software', QML_DISABLE_DISK_CACHE='1', QT_LOGGING_RULES='*.debug=false')
result = subprocess.run([str(runner), '-input', str(check), '-import', str(check), '-o', str(check / 'results.txt') + ',txt'], env=env)
if (check / 'results.txt').exists():
    print((check / 'results.txt').read_text())
print('QA output:', check)
raise SystemExit(result.returncode)
