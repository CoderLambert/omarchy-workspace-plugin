import QtQuick
import QtTest
import qs.Commons
import QtCore as Core
Item {
    width: 1100; height: 850
    Panel { id: plugin }
    Core.Settings {
        id: otherSettings
        location: Qt.resolvedUrl("ui.ini")
        category: "ui"
    }
    TestCase {
        name: "workspaces-theme-and-layout"
        when: windowShown
        function q(code) { return plugin.qa(code) }
        function initTestCase() {
            q('receiveState({installed:true,needsInstall:false,active:true,revision:"fixture",apps:[{id:"one",name:"应用一",workspace:1,existing_window:"focus"},{id:"two",name:"应用二",workspace:2,existing_window:"move"}],issues:[]}); opened=true')
            wait(200)
            compare(q('language'), otherSettings.value("language", "zh"))
            compare(q('closeButton.text'), q('language') === "en" ? "Close" : "关闭")
        }
        function test_00_language() {
            q('setLanguage("zh")'); wait(50)
            compare(q('closeButton.text'), "关闭")
            q('languageButton.clicked()'); wait(600)
            compare(q('language'), "en")
            compare(q('closeButton.text'), "Close")
            compare(q('focusChoice.text'), "Focus existing window")
            compare(q('searchField.placeholderText'), "Search apps / workspaces")
            compare(q('tr("已整理 3 个窗口")'), "Arranged 3 windows")
            compare(q('tr("受管文件缺失：/tmp/你好")'), "Managed file missing: /tmp/你好")
            compare(q('tr("工作区和复用方式已保存")'), "Workspace and window reuse settings saved")
            compare(q('tr("unknown 诊断 /tmp/原样")'), "unknown 诊断 /tmp/原样")
            q('showMessage("工作区和复用方式已保存",false)')
            compare(q('messageLabel.text'), "Workspace and window reuse settings saved")
            otherSettings.sync()
            compare(otherSettings.value("language"), "en")
            q('ask("remove",{},tr("取消管理此应用？"),tr("操作完成。"),false)');wait(30)
            compare(q('confirmTitle'), "Stop managing this app?")
            compare(q('cancelConfirm.text'), "Cancel")
            verify(q('!languageButton.enabled'))
            q('confirmation.close(); setLanguage("invalid")')
            compare(q('language'), "en")
            grabImage(q('panel.contentItem')).save(Qt.resolvedUrl("english.png").toString().replace(/^file:\/\//, ""))
            q('languageButton.clicked()'); wait(600)
            compare(q('closeButton.text'), "关闭")
            otherSettings.sync();compare(otherSettings.value("language"),"zh")
        }
        function test_01_dark() {
            Color.useDark(); wait(20)
            verify(q('paper === Color.menu.background && ink === Color.menu.text && accent === Color.accent && danger === Color.urgent'))
            verify(q('theme.muted.a > 0.6 && theme.muted.a < 0.8'))
            verify(q('appList.count === 2 && !compact'))
            verify(q('card.width <= panel.width && card.height <= panel.height'))
            grabImage(q('panel.contentItem')).save(Qt.resolvedUrl("dark.png").toString().replace(/^file:\/\//, ""))
        }
        function test_02_light_open_panel() {
            Color.useLight(); wait(20)
            verify(q('opened && paper === Color.menu.background && ink === Color.menu.text && theme.border === Color.menu.border'))
            verify(q('closeButton.contentItem.color === ink'))
            grabImage(q('panel.contentItem')).save(Qt.resolvedUrl("light.png").toString().replace(/^file:\/\//, ""))
        }
        function test_03_typography_and_corners() {
            Style.scale=1.25; Style.cornerRadius=0; wait(20)
            verify(q('theme.radius === 0 && card.background.radius === 0 && card.padding === Style.spacing.panelPadding'))
            verify(q('searchField.font.pixelSize === Style.font.subtitle && closeButton.font.pixelSize === Style.font.subtitle'))
            Style.scale=1; Style.cornerRadius=8
        }
        function test_04_search_and_dirty_selection() {
            q('searchField.text="2"'); compare(q('filteredApps.length'),1)
            q('searchField.text=""; editorWorkspace=5; selectApp("two")')
            verify(q('confirmation.opened && selectedId === "one"'))
            q('acceptConfirmation()'); wait(20)
            verify(q('selectedId === "two" && editorWorkspace === 2 && moveChoice.checked && !focusChoice.checked'))
        }
        function test_05_keyboard_and_save() {
            q('searchField.forceActiveFocus()'); wait(20)
            keyClick(Qt.Key_Tab)
            verify(q('!searchField.activeFocus'))
            q('workspaceInput.contentItem.text="7"; saveSelected()')
            verify(q('JSON.parse(bridge.command[2]).workspace === 7 && JSON.parse(bridge.command[2]).revision === "fixture"'))
            q('requestDismiss()'); verify(q('opened && busy'))
            q('busy=false; bridge.running=false; loadEditor("one")')
            verify(q('workspaceInput.value === 1 && focusChoice.checked'))
        }
        function test_06_narrow() {
            q('panel.width=640; panel.height=480'); wait(100)
            verify(q('compact && outerScroll.contentHeight > outerScroll.height'))
            verify(q('card.width <= panel.width && card.height <= panel.height'))
            grabImage(q('panel.contentItem')).save(Qt.resolvedUrl("narrow.png").toString().replace(/^file:\/\//, ""))
            q('ask("adopt",{},"接纳修改？","这是验证对话框。",false)');wait(50)
            verify(q('confirmation.opened && confirmation.modal && cancelConfirm.activeFocus'))
            keyClick(Qt.Key_Tab);verify(q('acceptConfirm.activeFocus'))
            keyClick(Qt.Key_Tab);verify(q('cancelConfirm.activeFocus'))
            keyClick(Qt.Key_Escape);verify(q('!confirmation.opened && opened'))
            keyClick(Qt.Key_Escape);verify(q('!opened'))
        }
        function test_065_special_workspace_opt_in() {
            q('receiveState({installed:true,needsInstall:false,active:true,revision:"fixture",apps:[{id:"one",name:"应用一",workspace:1,existing_window:"focus"}],issues:[]}); opened=true')
            verify(q('!includeSpecial && !includeSpecialChoice.checked'))
            q('send({action:"arrange",include_special:includeSpecial})')
            verify(q('JSON.parse(bridge.command[2]).include_special === false'))
            q('busy=false; bridge.running=false; includeSpecialChoice.toggle(); includeSpecialChoice.toggled(); saveSelected()')
            verify(q('JSON.parse(bridge.command[2]).include_special === true'))
            q('busy=false; bridge.running=false; includeSpecial=false; loadEditor("one")')
        }
        function test_07_install_gate() {
            q('receiveState({apps:[],issues:[],installed:false,needsInstall:true,pending:true});send({action:"set",app_id:"one"})')
            verify(q('!busy && messageIsError'))
            q('send({action:"install"})');verify(q('busy && JSON.parse(bridge.command[2]).action === "install"'))
        }
    }
}
