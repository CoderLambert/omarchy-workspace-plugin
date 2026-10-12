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
        function test_06c_setup_guidance_result_refresh_and_failure() {
            q('receiveState({installed:true,needsInstall:false,active:false,revision:"setup-fixture",apps:[],issues:[]}); opened=true; setupButton.clicked()'); wait(30)
            verify(q('confirmation.opened && confirmKind === "setup" && !busy'))
            verify(q('confirmMessage.indexOf("常用应用") >= 0 && confirmMessage.indexOf("快捷键") >= 0'))
            grabImage(q('panel.contentItem')).save(Qt.resolvedUrl("setup-guidance.png").toString().replace(/^file:\/\//, ""))
            q('cancelConfirm.clicked()'); wait(20); verify(q('!busy'))
            q('setupButton.clicked();acceptConfirmation()');wait(20)
            verify(q('busy && JSON.parse(bridge.command[2]).action === "setup" && JSON.parse(bridge.command[2]).revision === "setup-fixture"'))
            q('bridge.running=false;responseText=JSON.stringify({ok:true,message:"预设完成，应用列表已刷新。",state:{installed:true,needsInstall:false,active:true,revision:"updated",apps:[{id:"new-app",name:"New app",workspace:2}],issues:[]}});finish(0)');wait(30)
            verify(q('opened && !busy && appList.count === 1 && selectedId === "new-app" && confirmKind === "setup-result" && confirmation.opened'))
            verify(q('!cancelConfirm.visible && acceptConfirm.text === "知道了"'))
            grabImage(q('panel.contentItem')).save(Qt.resolvedUrl("setup-result.png").toString().replace(/^file:\/\//, ""))
            q('acceptConfirmation()');wait(20);verify(q('!busy && !confirmation.opened'))
            q('setLanguage("en");setupButton.clicked()');wait(20)
            compare(q('confirmTitle'), 'Start auto setup?')
            compare(q('tr("新增应用：3")'), 'New apps: 3')
            compare(q('tr("Custom App：保留现有设置")'), 'Custom App: Existing settings preserved')
            verify(q('confirmMessage.indexOf("Open your usual apps") >= 0'))
            q('confirmation.close();busy=true;pendingAction="setup";responseText=JSON.stringify({ok:false,message:"external edit",state:{installed:true,needsInstall:false,apps:[],issues:["external edit"]}});finish(1)');wait(20)
            verify(q('opened && !busy && messageIsError && !confirmation.opened && appList.count === 0'))
            q('setLanguage("zh")')
        }
        function test_07_install_gate() {
            q('receiveState({apps:[],issues:[],installed:false,needsInstall:true,pending:true});send({action:"set",app_id:"one"})')
            verify(q('!busy && messageIsError'))
            q('send({action:"install"})');verify(q('busy && JSON.parse(bridge.command[2]).action === "install"'))
        }
    }
}
