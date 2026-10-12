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
sys.dont_write_bytecode = True

os.environ['QT_QPA_PLATFORM'] = 'offscreen'
os.environ['QT_QUICK_BACKEND'] = 'software'
os.environ['QML_DISABLE_DISK_CACHE'] = '1'

try:
    from PySide6.QtCore import QTimer, QUrl, QPointF, Qt, qInstallMessageHandler, qVersion
    from PySide6.QtGui import QGuiApplication, QFontDatabase, QFont
    from PySide6.QtQml import QQmlApplicationEngine, QQmlExpression
    from PySide6.QtQuick import QQuickWindow
    from PySide6.QtTest import QTest
except ImportError as exc:
    print("Qt import failed: " + str(exc) + ". Install PySide6 and its system libraries.", file=sys.stderr)
    raise SystemExit(77)

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--output', type=Path, help='QA output directory; defaults to a new temporary directory')
parser.add_argument('--theme', choices=['dark', 'light'], default='dark', help='Initial fixture palette; both palettes are tested live')
parser.add_argument('--font', type=Path, help='Optional local CJK font for readable screenshots')
args = parser.parse_args()
source = Path(__file__).resolve().parents[1]
check = args.output.resolve() if args.output else Path(tempfile.mkdtemp(prefix='omarchy-workspaces-ui-'))
# Keep fixture/adaptor writes outside both source and installed plugin folders.
if check == source or source in check.parents:
    parser.error('--output must be outside the plugin/source directory')
from ui_fixture import prepare_ui_fixture
prepare_ui_fixture(source, check)

messages = []
def log(kind, context, message):
    messages.append(str(message))
    print('QT:', message)
qInstallMessageHandler(log)
app = QGuiApplication([])
if args.font:
    font_id = QFontDatabase.addApplicationFont(str(args.font))
    if font_id >= 0:
        font_family = QFontDatabase.applicationFontFamilies(font_id)[0]
        app.setFont(QFont(font_family, 10))
        # The shell fixture explicitly supplies its font family. Match that role
        # too so CJK layout checks exercise the requested font's actual metrics.
        fixture_style = check / 'qs' / 'Commons' / 'Style.qml'
        fixture_style.write_text(fixture_style.read_text().replace('"sans-serif"', json.dumps(font_family)))
engine = QQmlApplicationEngine()
engine.addImportPath(str(check))
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
    'version':'1.3.0-rc.1', 'backendVersion':'1.3.0-rc.1', 'installed':True,
    'needsInstall':False, 'active':True, 'draft':False, 'pending':False,
    'revision':'fixture-revision', 'configPath':'/home/demo/.config/omarchy-workspaces/apps.toml',
    'issues':[],
    'apps':[
        {'id':'chatgpt','name':'ChatGPT App','workspace':1,'existing_window':'focus','shortcuts':['Ctrl + Shift + A'],'windows':1,'windowWorkspaces':[1]},
        {'id':'grok-bot','name':'Grok Bot','workspace':1,'existing_window':'focus','shortcuts':[],'windows':0,'windowWorkspaces':[]},
        {'id':'terminal','name':'终端','workspace':2,'existing_window':'move','shortcuts':['Super + Return'],'windows':3,'windowWorkspaces':[2,5]},
        {'id':'vscode','name':'Visual Studio Code','workspace':2,'existing_window':'focus','shortcuts':[],'windows':1,'windowWorkspaces':[2]},
        {'id':'browser','name':'Chromium','workspace':3,'existing_window':'focus','shortcuts':[],'windows':2,'windowWorkspaces':[3]},
        {'id':'wechat','name':'微信','workspace':4,'existing_window':'focus','shortcuts':[],'windows':0,'windowWorkspaces':[]},
        {'id':'slack','name':'Slack','workspace':4,'existing_window':'focus','shortcuts':[],'windows':1,'windowWorkspaces':[4]},
        {'id':'discord','name':'Discord','workspace':4,'existing_window':'focus','shortcuts':[],'windows':1,'windowWorkspaces':[4]},
        {'id':'chatgpt-web','name':'ChatGPT 网页','workspace':1,'existing_window':'focus','shortcuts':[],'windows':2,'windowWorkspaces':[1]},
        {'id':'tmux','name':'Tmux','workspace':2,'existing_window':'move','shortcuts':[],'windows':1,'windowWorkspaces':[2,5]},
        {'id':'x','name':'X','workspace':4,'existing_window':'focus','shortcuts':[],'windows':0,'windowWorkspaces':[]},
    ]
}
evaluate('receiveState(' + json.dumps(fixture, ensure_ascii=False) + ')')
evaluate('opened = true; showMessage("", false)')
evaluate('Color.useLight()' if args.theme == 'light' else 'Color.useDark()')
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

def click(window, code):
    item = evaluate(code)
    point = item.mapToScene(QPointF(item.width() / 2, item.height() / 2)).toPoint()
    QTest.mouseClick(window, Qt.LeftButton, Qt.NoModifier, point)
    app.processEvents()


def idle():
    evaluate('busy=false; bridge.running=false; pendingAction=""; startGuard.stop(); patienceTimer.stop()')


def receive(state):
    evaluate('receiveState(' + json.dumps(state, ensure_ascii=False) + ')')


def finish_request(ok, state, message):
    response = {'ok': ok, 'state': state, 'message': message}
    evaluate('bridge.running=false; responseText=' + json.dumps(json.dumps(response, ensure_ascii=False)) + '; finish(' + ('0' if ok else '1') + ')')
    QTest.qWait(50)


def desktop():
    window = next(w for w in app.allWindows() if w.width() >= 1000)
    window.grabWindow().save(str(check / 'desktop.png'))
    expect('home groups apps into four workspaces', 'workspaceGroups.length === 4 && groupRepeater.count === 4 && workspaceCount === 4')
    expect('eleven-app first open keeps the top workspace heading visible', 'apps.length === 11 && Math.abs(outerScroll.contentItem.contentY) < 0.5 && groupRepeater.itemAt(0).mapToItem(outerScroll, 0, 0).y >= -0.5 && groupRepeater.itemAt(0).mapToItem(outerScroll, 0, 0).y < outerScroll.availableHeight')
    expect('home starts without editor, tools or report overlays', '!editorDialog.opened && !morePopup.opened && !reportDialog.opened')
    expect('theme surface and text follow shell roles', 'paper === Color.menu.background && ink === Color.menu.text && accent === Color.accent && danger === Color.urgent')
    expect('theme corner radius follows shell', 'theme.radius === Style.cornerRadius')
    evaluate('Color.useLight()' if args.theme == 'dark' else 'Color.useDark()')
    app.processEvents()
    expect('open panel reacts to palette change', 'paper === Color.menu.background && ink === Color.menu.text && theme.border === Color.menu.border')
    window.grabWindow().save(str(check / 'alternate-theme.png'))
    evaluate('Style.cornerRadius = 0; Style.scale = 1.25')
    app.processEvents()
    expect('open panel reacts to typography and radius', 'theme.radius === 0 && card.padding === Style.spacing.panelPadding && searchField.font.pixelSize === Style.font.subtitle')
    evaluate('Style.cornerRadius = 8; Style.scale = 1')
    evaluate('Color.useLight()' if args.theme == 'light' else 'Color.useDark()')
    evaluate('setLanguage("en")')
    expect('English labels update', 'closeButton.text === "Close" && searchField.placeholderText === "Search apps / workspaces"')
    QTest.qWait(600)
    evaluate('uiSettings.sync()')
    if 'language=en' not in (check / 'ui.ini').read_text():
        raise AssertionError('English preference was not persisted')
    checks.append('language persisted')
    evaluate('setLanguage("zh")')
    expect('Chinese labels restore', 'closeButton.text === "关闭"')
    evaluate('searchField.forceActiveFocus()')
    QTest.keyClick(window, Qt.Key_Tab)
    expect('native Tab traversal leaves search', '!searchField.activeFocus')
    evaluate('searchField.text = "4"')
    expect('workspace search filters groups and apps', 'filteredApps.length === 4 && groupRepeater.count === 1 && workspaceGroups[0].workspace === 4')
    evaluate('searchField.text = "no matching app"')
    expect('unmatched search shows no groups', 'filteredApps.length === 0 && groupRepeater.count === 0')
    evaluate('searchField.text = ""; focusApp("chatgpt")')
    QTest.qWait(30)
    QTest.keyClick(window, Qt.Key_Return)
    QTest.qWait(50)
    expect('keyboard activates an app editor', 'editorDialog.opened && editorDialog.modal && selectedId === "chatgpt"')
    expect('save defaults to preserving current windows', '!editorMoveExisting && !moveExistingChoice.checked && saveButton.text === "保存"')
    window.grabWindow().save(str(check / 'editor.png'))
    evaluate('workspaceInput.contentItem.forceActiveFocus()')
    QTest.keyClick(window, Qt.Key_A, Qt.ControlModifier)
    QTest.keyClick(window, Qt.Key_7)
    click(window, 'saveButton')
    expect('just typed SpinBox value used', 'busy && JSON.parse(bridge.command[2]).workspace === 7')
    expect('save includes original revision and no move by default', 'JSON.parse(bridge.command[2]).revision === "fixture-revision" && JSON.parse(bridge.command[2]).move_existing === false && JSON.parse(bridge.command[2]).include_special === false')
    evaluate('requestDismiss()')
    expect('busy close blocked', 'opened && busy && editorDialog.opened')
    expect('one process command while busy', 'send({action:"status"}) === undefined && JSON.parse(bridge.command[2]).action === "set"')
    saved = json.loads(json.dumps(fixture))
    saved['revision'] = 'saved-revision'
    saved['apps'][0]['workspace'] = 7
    finish_request(True, saved, '工作区和复用方式已保存')
    expect('successful save returns to the changed app in its new group', '!editorDialog.opened && groupRepeater.count === 5 && appById("chatgpt").workspace === 7 && panel.activeFocusItem.objectName === "app-chatgpt"')
    receive(fixture)
    evaluate('selectApp("terminal"); workspaceInput.contentItem.text="5"; saveSelected()')
    changed = json.loads(json.dumps(fixture))
    changed['revision'] = 'concurrent-revision'
    changed['apps'][2]['workspace'] = 6
    finish_request(False, changed, '配置已变化，请刷新后重试。')
    expect('failed save keeps the draft and its original revision', 'editorDialog.opened && messageIsError && editorWorkspace === 5 && workspaceInput.value === 5 && editorRevision === "fixture-revision" && snapshot.revision === "concurrent-revision"')
    evaluate('saveSelected()')
    expect('retry cannot silently overwrite a concurrent edit', 'JSON.parse(bridge.command[2]).revision === "fixture-revision"')
    idle()
    evaluate('requestDismiss()')
    expect('dirty editor back needs confirmation', 'confirmation.opened && editorDialog.opened')
    evaluate('acceptConfirmation()')
    QTest.qWait(50)
    expect('discard returns to home and restores app focus', '!editorDialog.opened && opened && panel.activeFocusItem.objectName === "app-terminal"')
    receive(fixture)
    evaluate('selectApp("chatgpt"); workspaceInput.contentItem.text="999"')
    click(window, 'moveExistingChoice')
    expect('moving existing windows requires an explicit choice', 'editorMoveExisting && moveExistingChoice.checked && saveButton.text === "保存并移动"')
    evaluate('saveSelected()')
    expect('custom workspace 999 and explicit move are sent', 'JSON.parse(bridge.command[2]).workspace === 999 && JSON.parse(bridge.command[2]).move_existing === true && JSON.parse(bridge.command[2]).include_special === false')
    idle()
    evaluate('loadEditor("chatgpt"); editorDialog.close()')
    QTest.qWait(30)
    expect('editor choices reset between edits', 'workspaceInput.value === 1 && workspaceInput.contentItem.text === "1" && !editorMoveExisting && !editorIncludeSpecial')
    evaluate('requestArrange()')
    QTest.qWait(30)
    expect('special workspaces protected in the arrange confirmation', 'confirmation.opened && includeSpecialChoice.visible && !includeSpecial && !includeSpecialChoice.checked')
    click(window, 'includeSpecialChoice')
    click(window, 'acceptConfirm')
    expect('special workspace opt-in is explicit and resets after use', 'JSON.parse(bridge.command[2]).include_special === true && !includeSpecial')
    idle()
    evaluate('showMessage("状态已更新。", false)')
    expect('details stay closed until requested', '!reportDialog.opened')
    click(window, 'detailsButton')
    QTest.qWait(30)
    expect('details open in a separate modal', 'reportDialog.opened && reportDialog.modal && messageLabel.readOnly && messageLabel.selectByMouse')
    QTest.keyClick(window, Qt.Key_Escape)
    QTest.qWait(30)
    expect('Escape returns from details to home', '!reportDialog.opened && opened')
    window.resize(640, 480)
    QTimer.singleShot(250, guarded(lambda: small(window)))


def small(window):
    window.grabWindow().save(str(check / 'small.png'))
    expect('small layout scrolls vertically', 'compact && outerScroll.contentHeight > outerScroll.height')
    evaluate('selectApp("chatgpt")')
    QTest.qWait(50)
    window.grabWindow().save(str(check / 'small-editor.png'))
    expect('editor fits a small viewport', 'editorDialog.width <= panel.width && editorDialog.height <= panel.height')
    evaluate('ask("adopt", withRevision({action:"adopt"}), "接纳这些外部修改？", "受管文件被其他工具修改：/home/demo/.local/share/applications/grok-bot.desktop\\n接纳后当前内容会成为新的恢复基线。", false)')
    QTimer.singleShot(200, guarded(lambda: dialog(window)))


def dialog(window):
    window.grabWindow().save(str(check / 'confirmation.png'))
    expect('confirmation remains modal above the editor', 'confirmation.opened && confirmation.modal && editorDialog.opened')
    QTest.keyClick(window, Qt.Key_Tab)
    expect('dialog Tab reaches confirmation button', 'acceptConfirm.activeFocus')
    QTest.keyClick(window, Qt.Key_Tab)
    expect('dialog Tab wraps to cancel', 'cancelConfirm.activeFocus')
    QTest.keyClick(window, Qt.Key_Escape)
    QTest.qWait(30)
    expect('Escape closes confirmation before editor', '!confirmation.opened && editorDialog.opened && opened')
    QTest.keyClick(window, Qt.Key_Escape)
    QTest.qWait(30)
    expect('Escape closes editor before panel', '!editorDialog.opened && opened')
    QTest.keyClick(window, Qt.Key_Escape)
    expect('close releases panel', '!opened')
    evaluate('receiveState({apps:[],issues:[],installed:false,needsInstall:true,pending:true}); send({action:"set",app_id:"chatgpt"})')
    expect('installation gate rejects other writes', '!busy && messageIsError')
    evaluate('send({action:"install"})')
    expect('installation available before recovering old state', 'busy && JSON.parse(bridge.command[2]).action === "install"')
    idle()
    evaluate('close()')
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
