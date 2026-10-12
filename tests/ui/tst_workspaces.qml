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
        function uiState() {
            return q('JSON.stringify({busy:busy,error:messageIsError,editor:editorDialog.opened,confirmation:confirmation.opened,dirty:editorDirty,workspace:editorWorkspace,text:workspaceInput.contentItem.text,original:editorOriginalWorkspace,revision:editorRevision})')
        }
        function buttonWithText(item, label) {
            if (item.text === label && typeof item.clicked === "function") return item
            for (var i=0; i<item.children.length; i++) {
                var found = buttonWithText(item.children[i], label)
                if (found) return found
            }
            return null
        }
        function fixture() {
            return {
                installed: true, needsInstall: false, active: true, pending: false,
                revision: "fixture", issues: [],
                apps: [
                    {id: "one", name: "应用一", workspace: 1, existing_window: "focus", windows: 1, windowWorkspaces: [1]},
                    {id: "two", name: "应用二", workspace: 2, existing_window: "move", windows: 2, windowWorkspaces: [2, 5]}
                ]
            }
        }
        function receive(state) { q('receiveState(' + JSON.stringify(state) + ')') }
        function idle() {
            q('busy=false; bridge.running=false; pendingAction=""; startGuard.stop(); patienceTimer.stop()')
        }
        function finishRequest(ok, state, message) {
            q('bridge.running=false; responseText=' + JSON.stringify(JSON.stringify({ok: ok, state: state, message: message})) + '; finish(' + (ok ? 0 : 1) + ')')
            wait(30)
        }
        function initTestCase() {
            compare(q('language'), otherSettings.value("language", "zh"))
        }
        function init() {
            idle()
            q('confirmation.close(); reportDialog.close(); morePopup.close(); editorDialog.close(); searchField.text=""; includeSpecial=false; panel.width=1100; panel.height=850; setLanguage("zh")')
            receive(fixture())
            q('opened=true; showMessage("",false)')
            Color.useDark(); Style.scale=1; Style.cornerRadius=8
            wait(50)
        }

        function test_00_language() {
            compare(q('closeButton.text'), "关闭")
            var chineseSearch = q('searchField.placeholderText')
            q('languageButton.clicked()'); wait(600)
            compare(q('language'), "en")
            compare(q('closeButton.text'), "Close")
            verify(q('searchField.placeholderText') !== chineseSearch)
            compare(q('tr("已整理 3 个窗口")'), "Arranged 3 windows")
            compare(q('tr("受管文件缺失：/tmp/你好")'), "Managed file missing: /tmp/你好")
            compare(q('tr("unknown 诊断 /tmp/原样")'), "unknown 诊断 /tmp/原样")
            q('showMessage("工作区和复用方式已保存",false)')
            compare(q('messageLabel.text'), "Workspace and window reuse settings saved")
            verify(q('!reportDialog.opened'))
            otherSettings.sync()
            compare(otherSettings.value("language"), "en")
            q('selectApp("one")'); wait(30)
            compare(q('saveButton.text'), "Save")
            q('ask("remove",{},tr("取消管理此应用？"),tr("操作完成。"),false)'); wait(30)
            compare(q('confirmTitle'), "Stop managing this app?")
            compare(q('cancelConfirm.text'), "Cancel")
            verify(q('!languageButton.enabled'))
            q('confirmation.close(); editorDialog.close(); setLanguage("invalid")')
            compare(q('language'), "en")
            grabImage(q('panel.contentItem')).save(Qt.resolvedUrl("english.png").toString().replace(/^file:\/\//, ""))
            q('languageButton.clicked()'); wait(600)
            compare(q('closeButton.text'), "关闭")
            otherSettings.sync(); compare(otherSettings.value("language"), "zh")
        }

        function test_01_grouped_home_and_search() {
            verify(q('!editorDialog.opened && !morePopup.opened && !reportDialog.opened'))
            compare(q('workspaceGroups.length'), 2)
            compare(q('groupRepeater.count'), 2)
            compare(q('workspaceGroups[0].workspace'), 1)
            compare(q('workspaceGroups[1].workspace'), 2)
            q('searchField.text="2"'); wait(20)
            compare(q('filteredApps.length'), 1)
            compare(q('groupRepeater.count'), 1)
            compare(q('workspaceGroups[0].workspace'), 2)
            q('searchField.text="应用一"'); compare(q('filteredApps[0].id'), "one")
            q('searchField.text="no-match"'); compare(q('groupRepeater.count'), 0)
            q('searchField.text=""')
            var state = fixture()
            state.apps.unshift({id: "custom", name: "Custom app", workspace: 999, existing_window: "focus"})
            receive(state); wait(20)
            compare(q('workspaceGroups.length'), 3)
            compare(q('workspaceGroups[2].workspace'), 999)
            compare(q('workspaceGroups[2].apps[0].name'), "Custom app")
            verify(q('card.width <= panel.width && card.height <= panel.height'))
        }

        function test_02_theme() {
            verify(q('paper === Color.menu.background && ink === Color.menu.text && accent === Color.accent && danger === Color.urgent'))
            verify(q('theme.muted.a > 0.6 && theme.muted.a < 0.8'))
            grabImage(q('panel.contentItem')).save(Qt.resolvedUrl("dark.png").toString().replace(/^file:\/\//, ""))
            Color.useLight(); wait(20)
            verify(q('opened && paper === Color.menu.background && ink === Color.menu.text && theme.border === Color.menu.border'))
            verify(q('closeButton.contentItem.color === ink'))
            grabImage(q('panel.contentItem')).save(Qt.resolvedUrl("light.png").toString().replace(/^file:\/\//, ""))
        }

        function test_03_typography_and_corners() {
            Style.scale=1.25; Style.cornerRadius=0; wait(20)
            verify(q('theme.radius === 0 && card.background.radius === 0 && card.padding === Style.spacing.panelPadding'))
            verify(q('searchField.font.pixelSize === Style.font.subtitle && closeButton.font.pixelSize === Style.font.subtitle'))
        }

        function test_04_click_and_keyboard_open_editor_then_restore_focus() {
            var row = q('groupRepeater.itemAt(0).focusApp("one")')
            verify(row !== null)
            mouseClick(row); wait(50)
            verify(q('editorDialog.opened && editorDialog.modal && selectedId === "one"'))
            verify(q('!editorMoveExisting && !moveExistingChoice.checked'))
            compare(q('saveButton.text'), "保存")
            keyClick(Qt.Key_Escape); wait(40)
            verify(q('!editorDialog.opened && opened'))
            compare(q('panel.activeFocusItem.objectName'), "app-one")
            q('focusApp("two")'); wait(30)
            keyClick(Qt.Key_Return); wait(40)
            verify(q('editorDialog.opened && selectedId === "two" && moveChoice.checked && !focusChoice.checked'))
            keyClick(Qt.Key_Escape); wait(40)
            compare(q('panel.activeFocusItem.objectName'), "app-two")
        }

        function test_05_unsaved_editor_close_and_selection() {
            q('selectApp("one"); editorWorkspace=5'); wait(30)
            keyClick(Qt.Key_Escape); wait(30)
            verify(q('confirmation.opened && editorDialog.opened && editorWorkspace === 5'))
            keyClick(Qt.Key_Escape); wait(20)
            verify(q('!confirmation.opened && editorDialog.opened && editorDirty'))
            q('selectApp("two")'); wait(30)
            verify(q('confirmation.opened && selectedId === "one"'))
            q('acceptConfirmation()'); wait(30)
            verify(q('editorDialog.opened && selectedId === "two" && editorWorkspace === 2 && moveChoice.checked'))
            q('editorWorkspace=6; requestDismiss()'); wait(20)
            q('acceptConfirmation()'); wait(40)
            verify(q('!editorDialog.opened && opened'))
            compare(q('panel.activeFocusItem.objectName'), "app-two")
        }

        function test_05b_uncommitted_workspace_text_needs_discard_confirmation() {
            q('selectApp("one"); workspaceInput.contentItem.forceActiveFocus()'); wait(20)
            keyClick(Qt.Key_A, Qt.ControlModifier); keyClick(Qt.Key_5)
            // Closing must account for text still being edited, without requiring
            // the user to blur the SpinBox or press Enter first.
            q('requestDismiss()'); wait(30)
            verify(q('confirmation.opened && editorDialog.opened'))
            q('acceptConfirmation()'); wait(30)
            verify(q('!editorDialog.opened && opened'))
            verify(q('!editorDirty'), uiState())
            q('selectApp("one")'); wait(30)
            verify(q('editorDialog.opened && workspaceInput.value === 1 && workspaceInput.contentItem.text === "1"'), uiState())
        }

        function test_06_save_defaults_to_not_moving_existing_windows() {
            q('selectApp("one"); workspaceInput.contentItem.forceActiveFocus()'); wait(20)
            keyClick(Qt.Key_A, Qt.ControlModifier); keyClick(Qt.Key_7)
            mouseClick(q('saveButton')); wait(20)
            verify(q('busy && JSON.parse(bridge.command[2]).workspace === 7'))
            verify(q('JSON.parse(bridge.command[2]).revision === "fixture" && JSON.parse(bridge.command[2]).move_existing === false && JSON.parse(bridge.command[2]).include_special === false'))
            q('requestDismiss()'); verify(q('opened && busy && editorDialog.opened'))
            q('send({action:"status"})')
            compare(q('JSON.parse(bridge.command[2]).action'), "set")
            var state = fixture(); state.revision="saved"; state.apps[0].workspace=7
            finishRequest(true, state, "工作区和复用方式已保存")
            verify(q('!busy && !editorDialog.opened && opened'))
            compare(q('appById("one").workspace'), 7)
            compare(q('panel.activeFocusItem.objectName'), "app-one")
        }

        function test_06b_custom_workspace_and_explicit_move() {
            q('selectApp("one"); workspaceInput.contentItem.text="1000"; saveSelected()')
            verify(q('!busy && messageIsError && editorDialog.opened'), uiState())
            q('workspaceInput.contentItem.text="999"')
            mouseClick(q('moveExistingChoice')); wait(20)
            verify(q('editorMoveExisting && moveExistingChoice.checked'))
            verify(q('saveButton.text !== "保存"'))
            q('saveSelected()')
            verify(q('JSON.parse(bridge.command[2]).workspace === 999 && JSON.parse(bridge.command[2]).move_existing === true && JSON.parse(bridge.command[2]).include_special === false'))
        }

        function test_06c_failed_save_preserves_draft_and_original_revision() {
            q('selectApp("one"); workspaceInput.contentItem.text="7"; editorBehavior="move"; saveSelected()')
            var state = fixture(); state.revision="concurrent-revision"; state.apps[0].workspace=6
            finishRequest(false, state, "配置已变化，请刷新后重试。")
            verify(q('!busy && messageIsError && editorDialog.opened'), uiState())
            compare(q('editorWorkspace'), 7)
            compare(q('workspaceInput.value'), 7)
            compare(q('editorBehavior'), "move")
            compare(q('editorRevision'), "fixture")
            compare(q('snapshot.revision'), "concurrent-revision")
            q('saveSelected()')
            verify(q('JSON.parse(bridge.command[2]).workspace === 7 && JSON.parse(bridge.command[2]).revision === "fixture"'))
        }

        function test_06d_workspace_quick_choice_keeps_later_editor_text_in_sync() {
            q('selectApp("one")'); wait(30)
            var quickChoice = buttonWithText(q('editorDialog.contentItem'), "3")
            verify(quickChoice !== null)
            mouseClick(quickChoice); wait(20)
            verify(q('editorWorkspace === 3 && workspaceInput.value === 3 && workspaceInput.contentItem.text === "3"'))
            mouseClick(q('saveButton'))
            var state = fixture(); state.revision="quick-choice-saved"; state.apps[0].workspace=3
            finishRequest(true, state, "工作区和复用方式已保存")
            q('selectApp("two")'); wait(30)
            verify(q('editorDialog.opened && editorWorkspace === 2 && workspaceInput.value === 2 && workspaceInput.contentItem.text === "2"'), uiState())
            mouseClick(q('saveButton'))
            verify(q('JSON.parse(bridge.command[2]).app_id === "two" && JSON.parse(bridge.command[2]).workspace === 2'))
        }

        function test_06e_diagnostics_preserve_failed_edit_and_block_adoption() {
            q('selectApp("one"); workspaceInput.contentItem.text="7"; editorBehavior="move"; saveSelected()')
            var state = fixture(); state.revision="concurrent-revision"; state.apps[0].workspace=6; state.issues=["external edit"]
            finishRequest(false, state, "配置已变化，请刷新后重试。")
            q('openReport()'); wait(30)
            verify(q('editorDialog.opened && reportDialog.opened && adoptButton.visible && !adoptButton.enabled'))
            mouseClick(q('adoptButton')); wait(20)
            verify(q('!busy && !confirmation.opened'))
            mouseClick(q('checkButton'))
            verify(q('busy && JSON.parse(bridge.command[2]).action === "doctor"'))
            state.revision="doctor-revision"
            finishRequest(true, state, "检查完成。")
            verify(q('reportDialog.opened && editorDialog.opened && editorWorkspace === 7 && workspaceInput.value === 7 && editorBehavior === "move" && editorRevision === "fixture"'), uiState())
            verify(q('snapshot.revision === "doctor-revision" && !adoptButton.enabled'))
        }

        function test_07_special_workspaces_require_opt_in() {
            q('requestArrange()'); wait(30)
            verify(q('confirmation.opened && includeSpecialChoice.visible && !includeSpecial && !includeSpecialChoice.checked'))
            mouseClick(q('acceptConfirm'))
            verify(q('JSON.parse(bridge.command[2]).include_special === false'))
            idle()
            q('requestArrange()'); wait(30)
            mouseClick(q('includeSpecialChoice')); wait(20)
            verify(q('includeSpecial && includeSpecialChoice.checked'))
            mouseClick(q('acceptConfirm'))
            verify(q('JSON.parse(bridge.command[2]).include_special === true'))
            verify(q('!includeSpecial'))
        }

        function test_08_narrow_layout_and_popup_escape_order() {
            var state = fixture()
            for (var i=3; i<=6; i++)
                state.apps.push({id:"app"+i, name:"应用 "+i, workspace:i, existing_window:"focus"})
            receive(state)
            q('panel.width=640; panel.height=480'); wait(100)
            verify(q('compact && outerScroll.contentHeight > outerScroll.height'))
            verify(q('card.width <= panel.width && card.height <= panel.height'))
            grabImage(q('panel.contentItem')).save(Qt.resolvedUrl("narrow.png").toString().replace(/^file:\/\//, ""))
            q('morePopup.open()'); wait(30)
            keyClick(Qt.Key_Escape); wait(30)
            verify(q('!morePopup.opened && opened'))
            q('selectApp("one"); openReport()'); wait(30)
            verify(q('reportDialog.opened && editorDialog.opened'), uiState())
            keyClick(Qt.Key_Escape); wait(30)
            verify(q('!reportDialog.opened && editorDialog.opened && opened'))
            q('ask("adopt",{},"接纳修改？","这是验证对话框。",false)'); wait(30)
            verify(q('confirmation.opened && confirmation.modal && cancelConfirm.activeFocus'))
            keyClick(Qt.Key_Tab); verify(q('acceptConfirm.activeFocus'))
            keyClick(Qt.Key_Tab); verify(q('cancelConfirm.activeFocus'))
            keyClick(Qt.Key_Escape); wait(20)
            verify(q('!confirmation.opened && editorDialog.opened && opened'))
            keyClick(Qt.Key_Escape); wait(20)
            verify(q('!editorDialog.opened && opened'))
            keyClick(Qt.Key_Escape); verify(q('!opened'))
        }

        function test_09_setup_guidance_refresh_and_failure() {
            var state = fixture(); state.apps=[]; state.active=false; state.revision="setup-fixture"
            receive(state)
            q('setupButton.clicked()'); wait(30)
            verify(q('confirmation.opened && confirmKind === "setup" && !busy'))
            verify(q('confirmMessage.indexOf("常用应用") >= 0 && confirmMessage.indexOf("快捷键") >= 0'))
            grabImage(q('panel.contentItem')).save(Qt.resolvedUrl("setup-guidance.png").toString().replace(/^file:\/\//, ""))
            q('cancelConfirm.clicked()'); wait(20); verify(q('!busy'))
            q('setupButton.clicked(); acceptConfirmation()'); wait(20)
            verify(q('busy && JSON.parse(bridge.command[2]).action === "setup" && JSON.parse(bridge.command[2]).revision === "setup-fixture"'))
            state.apps=[{id:"new-app",name:"New app",workspace:2}]; state.active=true; state.revision="updated"
            finishRequest(true, state, "预设完成，应用列表已刷新。")
            verify(q('opened && !busy && groupRepeater.count === 1 && confirmKind === "setup-result" && confirmation.opened'))
            verify(q('!cancelConfirm.visible && acceptConfirm.text === "知道了" && !editorDialog.opened'))
            grabImage(q('panel.contentItem')).save(Qt.resolvedUrl("setup-result.png").toString().replace(/^file:\/\//, ""))
            q('acceptConfirmation()'); wait(20); verify(q('!busy && !confirmation.opened'))
            q('setLanguage("en"); requestSetup()'); wait(20)
            compare(q('confirmTitle'), "Start auto setup?")
            verify(q('confirmMessage.indexOf("Open your usual apps") >= 0'))
            q('confirmation.close(); busy=true; pendingAction="setup"')
            state.apps=[]; state.issues=["external edit"]
            finishRequest(false, state, "external edit")
            verify(q('opened && !busy && messageIsError && !confirmation.opened && groupRepeater.count === 0'))
        }

        function test_10_report_is_on_demand_and_scrolls() {
            q('showMessage(Array.from({length:80},function(_,i){return "检查信息 "+i+" · long report"}).join("\\n"),false)'); wait(50)
            verify(q('!reportDialog.opened'))
            q('openReport()'); wait(100)
            verify(q('reportDialog.opened && reportDialog.modal && reportScroll.contentHeight > reportScroll.availableHeight'))
            verify(q('messageLabel.readOnly && messageLabel.selectByMouse'))
            compare(q('reportScroll.contentItem.contentY'), 0)
            mouseWheel(q('messageLabel'),20,20,0,-360); wait(150)
            verify(q('reportScroll.contentItem.contentY > 0'))
            q('reportScroll.Controls.ScrollBar.vertical.position=1-reportScroll.Controls.ScrollBar.vertical.size'); wait(50)
            verify(q('reportScroll.contentItem.contentY >= reportScroll.contentHeight-reportScroll.availableHeight-2'))
            q('panel.width=640; panel.height=480'); wait(100)
            q('reportScroll.contentItem.contentY=0'); wait(30)
            var outerPosition=q('outerScroll.contentItem.contentY')
            mouseWheel(q('messageLabel'),20,20,0,-360); wait(100)
            verify(q('reportScroll.contentItem.contentY > 0'))
            compare(q('outerScroll.contentItem.contentY'),outerPosition)
            q('messageLabel.selectAll()'); verify(q('messageLabel.selectedText.indexOf("检查信息 79") >= 0'))
            q('showMessage("new report",false)'); wait(100)
            compare(q('reportScroll.contentItem.contentY'),0)
        }

        function test_11_install_and_pending_gates() {
            var state = fixture(); state.pending=true
            receive(state)
            q('selectApp("one")'); verify(q('!saveButton.enabled'))
            q('send({action:"set",app_id:"one"})')
            verify(q('!busy && messageIsError'))
            q('send({action:"recover"})')
            verify(q('busy && JSON.parse(bridge.command[2]).action === "recover"'))
            idle()
            receive({apps:[],issues:[],installed:false,needsInstall:true,pending:true})
            q('send({action:"set",app_id:"one"})')
            verify(q('!busy && messageIsError'))
            q('send({action:"install"})')
            verify(q('busy && JSON.parse(bridge.command[2]).action === "install"'))
        }
    }
}
