"""Optional Qt UI checks using explicit, local Quickshell adapters.

Run in a Python environment with PySide6 installed:
    python scripts/verify_ui.py --output /tmp/omarchy-workspaces-ui-check

This never calls the workspace backend, changes a desktop configuration,
starts Quickshell, or accesses the network. It verifies Qt Quick construction
and UI interaction; it does not certify a live Omarchy/Hyprland session.
"""
import argparse
import json
import re
import tempfile
import traceback
import os
from pathlib import Path
import shutil
import sys

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
os.environ.setdefault('QT_QUICK_BACKEND', 'software')
os.environ.setdefault('QML_DISABLE_DISK_CACHE', '1')

try:
    from PySide6.QtCore import QTimer, QUrl, Qt, qInstallMessageHandler, qVersion
    from PySide6.QtGui import QGuiApplication, QFontDatabase, QFont
    from PySide6.QtQml import QQmlApplicationEngine, QQmlExpression
    from PySide6.QtQuick import QQuickWindow
    from PySide6.QtTest import QTest
except ImportError:
    print("Optional dependency missing: install PySide6 in a development environment.", file=sys.stderr)
    raise SystemExit(77)

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--output', type=Path, help='QA output directory; defaults to a new temporary directory')
parser.add_argument('--font', type=Path, help='Optional local CJK font for readable screenshots')
args = parser.parse_args()
source = Path(__file__).resolve().parents[1]
check = args.output.resolve() if args.output else Path(tempfile.mkdtemp(prefix='omarchy-workspaces-ui-'))
# Keep fixture/adaptor writes outside both source and installed plugin folders.
if check == source or source in check.parents:
    parser.error('--output must be outside the plugin/source directory')
(check / 'stubs').mkdir(parents=True, exist_ok=True)
shutil.copytree(source / 'qml', check / 'qml', dirs_exist_ok=True)

# The source UI remains unchanged except the real host's window/process
# adapters. This verifies Qt Quick construction and interaction, not Wayland
# compositor behavior or Quickshell's runtime module implementation.
qml = (source / 'Panel.qml').read_text()
qml = qml.replace('import Quickshell\n', 'import "stubs"\n')
qml = qml.replace('import Quickshell.Io\n', '')
qml = qml.replace('import Quickshell.Wayland\n', '')
qml = re.sub(r'^\s*(?:exclusionMode:|WlrLayershell\.).*$', '', qml, flags=re.MULTILINE)
(check / 'Panel.qml').write_text(qml)
(check / 'stubs' / 'PanelWindow.qml').write_text('''
import QtQuick
import QtQuick.Window
Window {
    width: 1100
    height: 850
    transientParent: null
    readonly property bool backingWindowVisible: visible
    property PanelAnchors anchors: PanelAnchors {}
}
''')
(check / 'stubs' / 'PanelAnchors.qml').write_text('''
import QtQuick
QtObject {
    property bool top: false
    property bool bottom: false
    property bool left: false
    property bool right: false
}
''')
(check / 'stubs' / 'Process.qml').write_text('''
import QtQuick
QtObject {
    property var environment: ({})
    property var command: []
    property bool running: false
    property QtObject stdout: null
    property QtObject stderr: null
    signal started()
    signal exited(int exitCode, int exitStatus)
}
''')
(check / 'stubs' / 'StdioCollector.qml').write_text('''
import QtQuick
QtObject {
    property string text: ""
    signal streamFinished()
}
''')

messages = []
def log(kind, context, message):
    messages.append(str(message))
    print('QT:', message)
qInstallMessageHandler(log)
app = QGuiApplication([])
if args.font:
    font_id = QFontDatabase.addApplicationFont(str(args.font))
    if font_id >= 0:
        app.setFont(QFont(QFontDatabase.applicationFontFamilies(font_id)[0], 10))
engine = QQmlApplicationEngine()
engine.load(QUrl.fromLocalFile(str(check / 'Panel.qml')))
if not engine.rootObjects():
    raise SystemExit('QML construction failed')
root = engine.rootObjects()[0]
context = engine.contextForObject(root)
def evaluate(code):
    expression = QQmlExpression(context, root, code)
    result = expression.evaluate()
    if expression.hasError():
        raise RuntimeError(expression.error().toString())
    return result[0] if isinstance(result, tuple) else result

fixture = {
    'version':'1.2.0', 'backendVersion':'1.2.0', 'installed':True,
    'needsInstall':False, 'active':True, 'draft':False, 'pending':False,
    'revision':'fixture-revision', 'configPath':'/home/demo/.config/omarchy-workspaces/apps.toml',
    'issues':[],
    'apps':[
        {'id':'chatgpt','name':'ChatGPT','workspace':1,'existing_window':'focus','shortcuts':['Ctrl + Shift + A'],'windows':1,'windowWorkspaces':[1]},
        {'id':'grok-bot','name':'Grok Bot','workspace':1,'existing_window':'focus','shortcuts':[],'windows':0,'windowWorkspaces':[]},
        {'id':'terminal','name':'终端 / Tmux','workspace':2,'existing_window':'move','shortcuts':['Super + Return'],'windows':3,'windowWorkspaces':[2,5]},
        {'id':'vscode','name':'Visual Studio Code','workspace':2,'existing_window':'focus','shortcuts':[],'windows':1,'windowWorkspaces':[2]},
        {'id':'browser','name':'Chromium','workspace':3,'existing_window':'focus','shortcuts':[],'windows':2,'windowWorkspaces':[3]},
        {'id':'wechat','name':'微信','workspace':4,'existing_window':'focus','shortcuts':[],'windows':0,'windowWorkspaces':[]},
        {'id':'slack','name':'Slack','workspace':4,'existing_window':'focus','shortcuts':[],'windows':1,'windowWorkspaces':[4]},
        {'id':'discord','name':'Discord','workspace':4,'existing_window':'focus','shortcuts':[],'windows':1,'windowWorkspaces':[4]},
    ]
}
evaluate('receiveState(' + json.dumps(fixture, ensure_ascii=False) + ')')
evaluate('opened = true; showMessage("配置已生效，当前管理 8 个应用。", false)')
checks=[]
failed = []
def report():
    result = {
        'passed': not failed,
        'checks': checks,
        'errors': failed,
        'qtMessages': messages,
        'host': 'Qt ' + qVersion() + ' offscreen with explicit window/process adapters; not a live Omarchy validation'
    }
    (check / 'report.json').write_text(json.dumps(result, ensure_ascii=False, indent=2))
    return result

def guarded(callback):
    def run():
        try:
            callback()
        except Exception:
            failed.append(traceback.format_exc())
            print(json.dumps(report(), ensure_ascii=False, indent=2))
            app.exit(1)
    return run

def expect(name, code):
    if not evaluate(code):
        raise AssertionError(name)
    checks.append(name)

def desktop():
    windows = app.allWindows()
    window = next(w for w in windows if w.width() >= 1000)
    window.grabWindow().save(str(check / 'desktop.png'))
    expect('state selected first app', 'selectedId === "chatgpt" && editorWorkspace === 1 && ready === true')
    evaluate('searchField.forceActiveFocus()')
    QTest.keyClick(window, Qt.Key_Tab)
    expect('native Tab traversal leaves search', '!searchField.activeFocus')
    evaluate('searchField.text = "4"')
    expect('workspace search', 'filteredApps.length === 3')
    evaluate('searchField.text = ""; editorWorkspace = 5; selectApp("terminal")')
    expect('dirty selection needs confirmation', 'confirmation.opened && selectedId === "chatgpt"')
    evaluate('acceptConfirmation()')
    QTest.qWait(200)
    expect('confirmed selection loads correct editor', 'selectedId === "terminal" && editorWorkspace === 2 && editorBehavior === "move"')
    expect('radio binding follows selection', 'moveChoice.checked && !focusChoice.checked')
    evaluate('workspaceInput.contentItem.forceActiveFocus()')
    app.processEvents()
    QTest.keyClick(window, Qt.Key_A, Qt.ControlModifier)
    QTest.keyClick(window, Qt.Key_7)
    evaluate('saveSelected()')
    expect('just typed SpinBox value used', 'JSON.parse(bridge.command[2]).workspace === 7')
    expect('revision included', 'JSON.parse(bridge.command[2]).revision === "fixture-revision"')
    evaluate('requestDismiss()')
    expect('busy close blocked', 'opened && busy')
    expect('one process command while busy', 'send({action:"status"}) === undefined && JSON.parse(bridge.command[2]).action === "set"')
    evaluate('busy = false; bridge.running = false; loadEditor("chatgpt"); showMessage("状态已更新。", false)')
    expect('SpinBox binding survives save and selection', 'workspaceInput.value === 1 && editorWorkspace === 1')
    expect('radio binding restores focus choice', 'focusChoice.checked && !moveChoice.checked')
    window.resize(640, 480)
    QTimer.singleShot(250, guarded(lambda: small(window)))

def small(window):
    window.grabWindow().save(str(check / 'small.png'))
    expect('small layout scrolls vertically', 'outerScroll.contentHeight > outerScroll.height')
    evaluate('ask("adopt", withRevision({action:"adopt"}), "接纳这些外部修改？", "受管文件被其他工具修改：/home/demo/.local/share/applications/grok-bot.desktop\\n接纳后当前内容会成为新的恢复基线。", false)')
    QTimer.singleShot(200, guarded(lambda: dialog(window)))

def dialog(window):
    window.grabWindow().save(str(check / 'confirmation.png'))
    expect('confirmation remains modal', 'confirmation.opened && confirmation.modal')
    QTest.keyClick(window, Qt.Key_Tab)
    expect('dialog Tab reaches confirmation button', 'acceptConfirm.activeFocus')
    QTest.keyClick(window, Qt.Key_Tab)
    expect('dialog Tab wraps to cancel', 'cancelConfirm.activeFocus')
    QTest.keyClick(window, Qt.Key_Escape)
    expect('Escape closes dialog before panel', '!confirmation.opened && opened')
    QTest.keyClick(window, Qt.Key_Escape)
    expect('close releases panel', '!opened')
    evaluate('receiveState({apps:[],issues:[],installed:false,needsInstall:true,pending:true}); send({action:"set",app_id:"chatgpt"})')
    expect('installation gate rejects other writes', '!busy && messageIsError')
    evaluate('send({action:"install"})')
    expect('installation available before recovering old state', 'busy && JSON.parse(bridge.command[2]).action === "install"')
    evaluate('busy=false; bridge.running=false; close()')
    if messages:
        failed.extend(messages)
    print(json.dumps(report(), ensure_ascii=False, indent=2))
    print('QA output:', check)
    app.exit(1 if failed else 0)

def timed_out():
    failed.append('UI checks did not complete within 10 seconds')
    print(json.dumps(report(), ensure_ascii=False, indent=2))
    app.exit(1)

QTimer.singleShot(350, guarded(desktop))
QTimer.singleShot(10000, timed_out)
raise SystemExit(app.exec())
