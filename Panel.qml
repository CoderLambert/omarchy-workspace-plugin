pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls as Controls
import QtQuick.Layouts
import Quickshell
import Quickshell.Io
import Quickshell.Wayland
import QtCore as Core
import "qml/Strings.js" as Strings
import qs.Commons
import qs.Ui as ShellUi
import "qml" as Ui

// Omarchy v4.0.4 loads exactly one Item for this panel ID. The host injects
// these optional properties before delivering open(payloadJson). This plugin
// only uses its own lifecycle facade; all workspace state comes from the
// bundled bridge and remains outside the watched plugin directory.
Item {
    id: root

    property var shell: null
    property var manifest: ({})
    property string omarchyPath: ""
    property bool opened: false

    readonly property string pluginId: "lambert.workspaces"
    readonly property string bridgePath: decodeURIComponent(Qt.resolvedUrl("scripts/bridge.py").toString().replace(/^file:\/\//, ""))
    Core.Settings {
        id: uiSettings
        category: "ui"
        location: "file://" + (Quickshell.env("XDG_CONFIG_HOME") || Quickshell.env("HOME") + "/.config") + "/omarchy-workspaces/ui.ini"
        property string language: "zh"
    }
    readonly property string language: uiSettings.language === "en" ? "en" : "zh"
    function tr(text) { return Strings.translate(language, text); }
    function setLanguage(value) {
        if (value !== "zh" && value !== "en") return;
        uiSettings.language = value;
        uiSettings.sync();
    }
    Ui.Theme { id: theme }
    readonly property color ink: theme.ink
    readonly property color muted: theme.muted
    readonly property color accent: theme.accent
    readonly property color paper: theme.paper
    readonly property color surface: theme.surface
    readonly property color line: theme.line
    readonly property color danger: theme.danger

    property var snapshot: ({
            apps: [],
            issues: [],
            needsInstall: true
        })
    property bool stateLoaded: false
    property bool busy: false
    property string pendingAction: ""
    property string responseText: ""
    property string errorText: ""
    property bool processStarted: false
    property string lastMessage: ""
    property bool messageIsError: false
    property bool includeSpecial: false
    property string selectedId: ""
    property int editorWorkspace: 1
    property string editorBehavior: "focus"
    property bool editorMoveExisting: false
    property bool editorIncludeSpecial: false
    property bool editorOptionsExpanded: false
    property int editorOriginalWorkspace: 1
    property string editorOriginalBehavior: "focus"
    property string editorRevision: ""
    property bool editorSaveError: false
    property string editorSaveMessage: ""
    property string confirmKind: ""
    property var confirmRequest: ({})
    property string confirmTitle: ""
    property string confirmMessage: ""
    property bool confirmDanger: false
    property bool focusPrimed: false

    readonly property bool ready: stateLoaded && snapshot.installed === true && snapshot.needsInstall !== true
    readonly property bool writable: ready && !busy && !snapshot.pending
    readonly property var apps: Array.isArray(snapshot.apps) ? snapshot.apps : []
    readonly property var issues: Array.isArray(snapshot.issues) ? snapshot.issues : []
    readonly property var filteredApps: {
        var query = searchField.text.trim().toLowerCase();
        var workspaceQuery = query.replace(/^(工作区|workspace)\s*/, "");
        if (!query)
            return apps;
        return apps.filter(function (app) {
            return String(app.name || "").toLowerCase().indexOf(query) !== -1 || String(app.id || "").toLowerCase().indexOf(query) !== -1 || String(app.workspace).indexOf(workspaceQuery) !== -1;
        });
    }
    readonly property var workspaceGroups: {
        var groups = [];
        filteredApps.forEach(function (app) {
            var group = groups.find(function (entry) { return entry.workspace === Number(app.workspace); });
            if (!group) {
                group = {workspace: Number(app.workspace), apps: []};
                groups.push(group);
            }
            group.apps.push(app);
        });
        return groups.sort(function (a, b) { return a.workspace - b.workspace; });
    }
    readonly property int workspaceCount: {
        var numbers = [];
        apps.forEach(function (app) {
            if (numbers.indexOf(Number(app.workspace)) === -1) numbers.push(Number(app.workspace));
        });
        return numbers.length;
    }
    readonly property var selectedApp: appById(selectedId)
    readonly property bool editorDirty: selectedApp !== null && (editorWorkspace !== editorOriginalWorkspace || workspaceInput.valueFromText(String(workspaceInput.contentItem.text), workspaceInput.locale) !== editorOriginalWorkspace || editorBehavior !== editorOriginalBehavior || editorMoveExisting)
    readonly property string messageSummary: root.tr(lastMessage).split("\n")[0]
    readonly property int selectedFilteredIndex: {
        for (var i = 0; i < filteredApps.length; i++) {
            if (filteredApps[i].id === selectedId)
                return i;
        }
        return -1;
    }
    readonly property bool compact: card.width < Style.space(740)

    function appById(id) {
        for (var i = 0; i < apps.length; i++) {
            if (apps[i].id === id)
                return apps[i];
        }
        return null;
    }

    function loadEditor(id) {
        var app = appById(id);
        selectedId = app ? String(app.id) : "";
        editorWorkspace = app ? Number(app.workspace) : 1;
        editorBehavior = app ? String(app.existing_window || "focus") : "focus";
        editorOriginalWorkspace = editorWorkspace;
        editorOriginalBehavior = editorBehavior;
        editorRevision = String(snapshot.revision || "");
        editorMoveExisting = false;
        editorIncludeSpecial = false;
        editorOptionsExpanded = false;
        editorSaveError = false;
        editorSaveMessage = "";
        // An explicit reset also restores text after an uncommitted edit.
        workspaceInput.contentItem.text = Qt.binding(function () { return workspaceInput.displayText; });
    }

    function chooseWorkspace(value) {
        editorWorkspace = value;
        // Keep the TextInput bound to SpinBox; direct text assignment would
        // otherwise survive selecting a different application later.
        workspaceInput.contentItem.text = Qt.binding(function () { return workspaceInput.displayText; });
    }

    function receiveState(next, preserveEditor) {
        if (!next || !Array.isArray(next.apps))
            return;
        var previous = selectedId;
        snapshot = next;
        stateLoaded = true;
        if (!appById(previous))
            previous = apps.length ? String(apps[0].id) : "";
        if (!preserveEditor)
            loadEditor(previous);
    }

    function selectApp(id) {
        if (busy)
            return;
        if (editorDirty) {
            ask("discard-select", {
                id: id
            }, root.tr("放弃未保存的修改？"), root.tr("当前应用的工作区设置尚未保存。继续后将显示另一个应用。"), false);
            return;
        }
        loadEditor(id);
        if (selectedApp) editorDialog.open();
    }

    function focusApp(id) {
        for (var i = 0; i < groupRepeater.count; i++) {
            var group = groupRepeater.itemAt(i);
            var row = group ? group.focusApp(id) : null;
            if (row) {
                if (outerScroll.availableHeight <= 0) return true;
                var position = row.mapToItem(homeBody, 0, 0);
                var viewport = outerScroll.contentItem;
                var firstInGroup = String(group.group.apps[0].id) === id;
                var top = firstInGroup ? group.mapToItem(homeBody, 0, 0).y : position.y;
                var target = viewport.contentY;
                if (top < viewport.contentY) target = top;
                else if (position.y + row.height > viewport.contentY + outerScroll.availableHeight)
                    target = position.y + row.height - outerScroll.availableHeight;
                viewport.contentY = Math.max(0, Math.min(Math.max(0, outerScroll.contentHeight - outerScroll.availableHeight), target));
                return true;
            }
        }
        searchField.forceActiveFocus();
        return false;
    }

    function moveSelection(id, direction) {
        if (!filteredApps.length || busy) return;
        var current = filteredApps.findIndex(function (app) { return String(app.id) === id; });
        var index = Math.max(0, Math.min(filteredApps.length - 1, current + direction));
        focusApp(String(filteredApps[index].id));
    }

    function restoreFocus() {
        if (!opened) return;
        if (confirmation.visible) cancelConfirm.forceActiveFocus();
        else if (reportDialog.visible) reportCloseButton.forceActiveFocus();
        else if (morePopup.visible) refreshButton.forceActiveFocus();
        else if (editorDialog.visible) workspaceInput.forceActiveFocus();
        else focusApp(selectedId);
    }

    function requestEditorClose() {
        if (busy) return;
        if (editorDirty) {
            ask("discard-editor", {}, root.tr("放弃未保存的修改？"), root.tr("设置未保存，返回前要放弃修改吗？"), false);
        } else {
            editorDialog.close();
        }
    }

    function openReport() {
        morePopup.close();
        reportDialog.open();
    }

    function requestArrange() {
        morePopup.close();
        includeSpecial = false;
        ask("arrange", {action: "arrange"}, root.tr("整理已打开的窗口？"), root.tr("将已登记的普通窗口移到各自的默认工作区。窗口中的任务会继续运行。"), false);
    }

    function showMessage(message, isError) {
        lastMessage = String(message || "");
        messageIsError = isError === true;
    }

    function actionLabel(action) {
        var labels = {
            status: "正在读取状态",
            install: "正在安装或更新组件",
            set: "正在保存设置",
            launch: "正在聚焦或启动",
            remove: "正在取消管理",
            arrange: "正在整理全部窗口",
            apply: "正在应用配置",
            adopt: "正在接纳外部修改",
            reset: "正在撤销工作区规则",
            recover: "正在恢复中断任务",
            doctor: "正在检查",
            setup: "正在识别应用并应用预设，请保持面板打开",
            terminal: "正在打开终端"
        };
        return labels[action] || "正在处理";
    }

    function send(request) {
        if (busy)
            return;
        var action = String(request.action || "");
        if (!ready && action !== "status" && action !== "install") {
            showMessage(root.tr("请先安装或更新组件，再修改工作区配置。"), true);
            return;
        }
        if (snapshot.pending && ["status", "install", "doctor", "recover"].indexOf(action) === -1) {
            showMessage(root.tr("存在中断任务，请先恢复后继续。"), true);
            return;
        }
        busy = true;
        pendingAction = action;
        responseText = "";
        errorText = "";
        processStarted = false;
        showMessage(actionLabel(action) + "…", false);
        bridge.command = ["python3", bridgePath, JSON.stringify(request)];
        bridge.running = true;
        startGuard.restart();
        patienceTimer.restart();
    }

    function finish(exitCode) {
        if (!busy)
            return;
        startGuard.stop();
        patienceTimer.stop();
        var action = pendingAction;
        busy = false;
        pendingAction = "";
        var result;
        try {
            result = JSON.parse(responseText);
            if (!result || typeof result.ok !== "boolean")
                throw new Error("invalid envelope");
        } catch (error) {
            if (action === "set") editorSaveError = true;
            showMessage(root.tr("组件未返回有效结果（退出码 ") + exitCode + (root.language === "en" ? ")." : "）。") + (errorText ? "\n" + errorText.trim().slice(0, 1800) : root.tr(" 请点击刷新重试，或从终端执行 doctor。")), true);
            if (action === "set") editorSaveMessage = lastMessage;
            return;
        }
        var success = result.ok === true && exitCode === 0;
        if (action === "set") {
            editorSaveError = !success;
            editorSaveMessage = success ? "" : String(result.message || root.tr("保存失败，修改仍保留。"));
        }
        // Keep both the user's fields and the original revision on failure.
        // A fresh response revision is not permission to overwrite a concurrent edit.
        if (result.state)
            receiveState(result.state, editorDialog.visible && (action === "doctor" || (!success && action === "set")));
        showMessage(result.message || (success ? (action === "status" ? "" : root.tr("操作完成。")) : root.tr("操作未完成，请检查提示后重试。")), !success);
        if (success && action === "set") editorDialog.close();
        if (success && action === "remove") editorDialog.close();
        if (success && action === "setup") {
            ask("setup-result", {}, root.tr("自动预设结果"), root.tr(result.message), false);
        }
        if (success && (action === "terminal" || action === "launch")) {
            // Release the overlay so the newly focused app or terminal is usable.
            dismiss();
        }
    }

    function withRevision(request) {
        var copy = Object.assign({}, request);
        copy.revision = String(snapshot.revision || "");
        return copy;
    }

    function requestAction(request) {
        if (busy)
            return;
        if (editorDirty) {
            ask("discard-action", request, root.tr("放弃未保存的修改？"), root.tr("当前编辑内容尚未保存。继续操作将重新读取配置。"), false);
        } else {
            send(request);
        }
    }

    function requestSetup() {
        ask("setup", withRevision({action: "setup"}), root.tr("开始自动预设？"),
            root.tr("建议先打开常用应用，以便识别窗口。将识别 AI、开发、浏览器与通信应用，补齐工作区分配并整理已登记窗口。部分应用可能短暂启动用于确认身份。\n\n已有应用设置与快捷键会保留；临时工作区中的窗口不会移动。识别不了的应用可随后使用“添加应用”。\n\n执行期间请保持面板打开，完成后会显示结果并自动刷新列表。") + (editorDirty ? "\n\n" + root.tr("当前未保存的编辑会被放弃。") : ""), false);
    }

    function saveSelected() {
        if (!writable || !selectedApp)
            return;
        // Clicking Save can precede SpinBox's editing-finished notification.
        // Read the editor explicitly so a just-typed value is never lost.
        var value = workspaceInput.valueFromText(String(workspaceInput.contentItem.text), workspaceInput.locale);
        if (!Number.isInteger(value) || value < 1 || value > 999) {
            editorSaveError = true;
            editorSaveMessage = root.tr("工作区编号必须是 1–999 的整数。");
            showMessage(editorSaveMessage, true);
            workspaceInput.forceActiveFocus();
            return;
        }
        editorWorkspace = value;
        send({
            action: "set",
            app_id: selectedId,
            workspace: value,
            existing_window: editorBehavior,
            move_existing: editorMoveExisting,
            include_special: editorMoveExisting && editorIncludeSpecial,
            revision: editorRevision
        });
    }

    function ask(kind, request, title, message, isDanger) {
        if (busy)
            return;
        confirmKind = kind;
        confirmRequest = request;
        confirmTitle = title;
        confirmMessage = message;
        confirmDanger = isDanger === true;
        confirmation.open();
    }

    function acceptConfirmation() {
        var kind = confirmKind;
        var request = confirmRequest;
        confirmation.close();
        if (kind === "setup-result") {
            return;
        } else if (kind === "discard-select") {
            loadEditor(request.id);
            editorDialog.open();
        } else if (kind === "discard-editor") {
            loadEditor(selectedId);
            editorDialog.close();
        } else if (kind === "discard-close") {
            loadEditor(selectedId);
            dismiss();
        } else {
            if (kind === "arrange") {
                request.include_special = includeSpecial;
                includeSpecial = false;
            }
            if (kind === "discard-action") editorDialog.close();
            loadEditor(selectedId);
            send(request);
        }
    }

    function requestDismiss() {
        if (confirmation.opened) {
            confirmation.close();
            return;
        }
        if (reportDialog.visible) { reportDialog.close(); return; }
        if (morePopup.visible) { morePopup.close(); return; }
        if (busy) {
            showMessage(root.tr("操作正在完成，请稍候再关闭。"), false);
        } else if (editorDialog.visible) {
            requestEditorClose();
        } else if (editorDirty) {
            ask("discard-close", {}, root.tr("放弃未保存的修改？"), root.tr("关闭后将保留上一次已保存的工作区设置。"), false);
        } else {
            dismiss();
        }
    }

    function dismiss() {
        if (busy)
            return;
        var hidden = shell && typeof shell.hide === "function" ? shell.hide(pluginId) : false;
        if (hidden !== true)
            close();
    }

    function open(payloadJson) {
        opened = true;
        focusPrimed = false;
        focusPrime.restart();
        Qt.callLater(function () {
            if (root.opened) {
                if (root.editorDirty) { editorDialog.open(); root.restoreFocus(); }
                else searchField.forceActiveFocus();
            }
        });
        if (!busy) {
            // Repeated summons preserve local edits; explicit Refresh asks before
            // discarding them. The host uses the same live panel instance.
            if (!editorDirty)
                send({
                    action: "status"
                });
        }
    }

    function close() {
        // shell.hide() calls close() itself. Calling shell.hide() from here
        // would recurse. keepLoaded keeps an in-flight bridge alive on hide.
        if (busy) {
            showMessage(root.tr("操作正在完成，请稍候再关闭。"), false);
            return;
        }
        opened = false;
        confirmation.close();
        editorDialog.close();
        morePopup.close();
        reportDialog.close();
        focusPrimed = false;
        focusPrime.stop();
    }

    Process {
        id: bridge
        environment: ({
                PYTHONDONTWRITEBYTECODE: "1"
            })
        onStarted: {
            root.processStarted = true;
            startGuard.stop();
        }
        stdout: StdioCollector {
            onStreamFinished: root.responseText = this.text
        }
        stderr: StdioCollector {
            onStreamFinished: root.errorText = this.text
        }
        onExited: function (exitCode, exitStatus) {
            // Stdio stream-finished events must settle before decoding a reply.
            Qt.callLater(function () {
                root.finish(exitCode);
            });
        }
    }

    Timer {
        id: startGuard
        interval: 2000
        onTriggered: {
            if (root.busy && !root.processStarted && !bridge.running) {
                root.errorText = root.tr("无法启动 python3。请确认 Python 已安装，插件 scripts/bridge.py 存在。");
                root.finish(-1);
            }
        }
    }

    Timer {
        id: patienceTimer
        interval: 25000
        onTriggered: if (root.busy)
            root.showMessage(root.actionLabel(root.pendingAction) + root.tr("，耗时较长，请保持面板打开。"), false)
    }

    Timer {
        id: focusPrime
        interval: 75
        onTriggered: if (root.opened && panel.backingWindowVisible)
            root.focusPrimed = true
    }

    PanelWindow {
        id: panel
        visible: root.opened
        color: "transparent"
        anchors {
            top: true
            bottom: true
            left: true
            right: true
        }
        exclusionMode: ExclusionMode.Ignore
        WlrLayershell.namespace: "lambert-workspaces"
        WlrLayershell.layer: WlrLayer.Overlay
        WlrLayershell.keyboardFocus: root.opened ? (root.focusPrimed ? WlrKeyboardFocus.OnDemand : WlrKeyboardFocus.Exclusive) : WlrKeyboardFocus.None

        onBackingWindowVisibleChanged: {
            if (backingWindowVisible && root.opened) {
                focusPrime.restart();
                Qt.callLater(function () {
                    if (root.opened) {
                        if (editorDialog.visible || confirmation.visible || reportDialog.visible) root.restoreFocus();
                        else searchField.forceActiveFocus();
                    }
                });
            }
        }

        Rectangle {
            anchors.fill: parent
            color: theme.scrim
            MouseArea {
                anchors.fill: parent
                onClicked: root.requestDismiss()
            }
        }

        Controls.Pane {
            id: card
            anchors.centerIn: parent
            width: Math.max(1, Math.min(Style.space(900), parent.width - Style.space(32)))
            height: Math.max(1, Math.min(Style.space(700), parent.height - Style.space(32)))
            padding: width < Style.space(520) ? Style.space(12) : Style.spacing.panelPadding
            palette.text: root.ink
            palette.windowText: root.ink
            palette.buttonText: root.ink
            palette.base: root.surface
            palette.window: root.paper
            palette.button: root.surface
            palette.highlight: root.accent
            palette.highlightedText: root.paper
            palette.mid: root.line
            palette.light: root.surface
            background: ShellUi.BorderSurface {
                color: root.paper
                radius: theme.radius
                borderSpec: Border.surfaceSpec("menu", "border", theme.border, Math.max(1, Style.space(1)))
            }
            MouseArea { anchors.fill: parent; acceptedButtons: Qt.AllButtons }
            FocusScope {
                anchors.fill: parent
                focus: true
                Keys.onEscapePressed: function (event) { root.requestDismiss(); event.accepted = true; }
                ColumnLayout {
                    anchors.fill: parent
                    spacing: Style.space(14)
                    RowLayout {
                        Layout.fillWidth: true
                        spacing: Style.space(12)
                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: Style.space(4)
                            Text {
                                Layout.fillWidth: true
                                text: root.tr("工作区安排")
                                color: root.ink
                                font.family: theme.family
                                font.pixelSize: Style.font.display
                                font.weight: Font.Bold
                                elide: Text.ElideRight
                            }
                            Text {
                                Layout.fillWidth: true
                                text: root.tr("安排应用位置，设置再次打开的方式。")
                                color: root.muted
                                font.family: theme.family
                                font.pixelSize: Style.font.body
                                wrapMode: Text.WordWrap
                            }
                        }
                        Ui.ActionButton {
                            id: moreButton
                            text: root.tr("更多") + " ···"
                            enabled: !root.busy
                            onClicked: morePopup.open()
                        }
                        Ui.ActionButton {
                            id: closeButton
                            text: root.tr("关闭")
                            hint: "Escape"
                            enabled: !root.busy
                            onClicked: root.requestDismiss()
                        }
                    }
                    RowLayout {
                        Layout.fillWidth: true
                        spacing: Style.space(10)
                        Controls.TextField {
                            id: searchField
                            Layout.fillWidth: true
                            implicitHeight: Style.space(38)
                            placeholderText: root.tr("搜索应用 / 工作区")
                            placeholderTextColor: root.muted
                            color: root.ink
                            font.family: theme.family
                            font.pixelSize: Style.font.subtitle
                            selectByMouse: true
                            leftPadding: Style.space(12)
                            rightPadding: Style.space(12)
                            Accessible.name: root.tr("搜索受管应用")
                            background: Rectangle {
                                color: root.surface
                                radius: theme.radius
                                border.width: searchField.activeFocus ? 2 : 1
                                border.color: searchField.activeFocus ? root.accent : root.line
                            }
                            Keys.onDownPressed: function (event) {
                                if (root.filteredApps.length) root.focusApp(String(root.filteredApps[0].id));
                                event.accepted = true;
                            }
                            Keys.onReturnPressed: if (root.filteredApps.length === 1) root.selectApp(String(root.filteredApps[0].id))
                        }
                        Ui.ActionButton {
                            id: addButton
                            text: "+ " + root.tr("添加应用")
                            primary: true
                            enabled: root.writable
                            hint: root.tr("添加应用会打开终端向导，可选择已安装的应用或识别已打开的窗口。")
                            onClicked: root.requestAction({action: "terminal", view: "add"})
                        }
                    }
                    Rectangle {
                        Layout.fillWidth: true
                        implicitHeight: installLayout.implicitHeight + Style.space(24)
                        visible: root.stateLoaded && root.snapshot.needsInstall === true
                        color: theme.notice
                        radius: theme.radius
                        RowLayout {
                            id: installLayout
                            anchors.fill: parent
                            anchors.margins: Style.space(12)
                            Text {
                                Layout.fillWidth: true
                                text: root.snapshot.installed ? root.tr("组件需要更新，安装后继续使用。现有应用配置会保留。") : root.tr("插件已加载。安装工作区组件后，即可管理应用和快捷键。")
                                textFormat: Text.PlainText
                                wrapMode: Text.WordWrap
                                color: root.ink
                                font.family: theme.family
                                font.pixelSize: Style.font.subtitle
                            }
                            Ui.ActionButton {
                                id: installButton
                                text: root.snapshot.installed ? root.tr("更新组件") : root.tr("安装组件")
                                primary: true
                                enabled: !root.busy
                                onClicked: root.send({action: "install"})
                            }
                        }
                    }
                    Rectangle {
                        Layout.fillWidth: true
                        implicitHeight: pendingLayout.implicitHeight + Style.space(24)
                        visible: root.ready && (!!root.snapshot.pending || !!root.snapshot.draft)
                        color: theme.notice
                        radius: theme.radius
                        RowLayout {
                            id: pendingLayout
                            anchors.fill: parent
                            anchors.margins: Style.space(12)
                            Text {
                                Layout.fillWidth: true
                                text: root.snapshot.pending ? root.tr("上一次操作中断，恢复后再继续修改。") : root.tr("有已保存但尚未生效的配置。")
                                wrapMode: Text.WordWrap
                                color: root.ink
                                font.family: theme.family
                                font.pixelSize: Style.font.subtitle
                            }
                            Ui.ActionButton {
                                id: recoverButton
                                text: root.snapshot.pending ? root.tr("恢复任务") : root.tr("应用配置")
                                enabled: !root.busy
                                onClicked: root.requestAction(root.withRevision({action: root.snapshot.pending ? "recover" : "apply"}))
                            }
                        }
                    }
                    Rectangle {
                        Layout.fillWidth: true
                        implicitHeight: noticeRow.implicitHeight + Style.space(16)
                        visible: root.lastMessage !== "" || root.issues.length > 0
                        color: root.messageIsError || root.issues.length ? theme.error : theme.notice
                        radius: theme.radius
                        RowLayout {
                            id: noticeRow
                            anchors.fill: parent
                            anchors.margins: Style.space(8)
                            Text {
                                Layout.fillWidth: true
                                text: root.issues.length ? root.tr("需要检查 {0} 项问题。").replace("{0}", root.issues.length) : root.messageSummary
                                textFormat: Text.PlainText
                                elide: Text.ElideRight
                                color: root.messageIsError || root.issues.length ? root.danger : root.ink
                                font.family: theme.family
                                font.pixelSize: Style.font.body
                                Accessible.name: text
                            }
                            Ui.ActionButton {
                                id: detailsButton
                                text: root.issues.length ? root.tr("查看问题") : root.tr("查看详情")
                                visible: !root.busy
                                onClicked: root.openReport()
                            }
                        }
                    }
                    Controls.ScrollView {
                        id: outerScroll
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        Layout.minimumHeight: 0
                        clip: true
                        contentWidth: availableWidth
                        contentHeight: homeBody.implicitHeight
                        Controls.ScrollBar.horizontal.policy: Controls.ScrollBar.AlwaysOff
                        ColumnLayout {
                            id: homeBody
                            width: outerScroll.availableWidth
                            spacing: Style.space(12)
                            GridLayout {
                                id: workspaceGrid
                                Layout.fillWidth: true
                                columns: root.compact ? 1 : 2
                                columnSpacing: Style.space(12)
                                rowSpacing: Style.space(12)
                                Repeater {
                                    id: groupRepeater
                                    model: root.workspaceGroups
                                    delegate: Ui.WorkspaceGroup {
                                        required property var modelData
                                        Layout.fillWidth: true
                                        Layout.alignment: Qt.AlignTop
                                        Layout.preferredWidth: 1
                                        group: modelData
                                        language: root.language
                                        busy: root.busy
                                        onEditRequested: function (appId) { root.selectApp(appId); }
                                        onNavigateRequested: function (appId, direction) { root.moveSelection(appId, direction); }
                                    }
                                }
                            }
                            ColumnLayout {
                                Layout.fillWidth: true
                                Layout.topMargin: Style.space(36)
                                Layout.bottomMargin: Style.space(36)
                                visible: root.filteredApps.length === 0
                                spacing: Style.space(14)
                                Text {
                                    Layout.fillWidth: true
                                    text: !root.stateLoaded ? root.tr("正在读取应用…") : root.apps.length ? root.tr("没有找到匹配的应用") : root.tr("还没有安排应用")
                                    color: root.ink
                                    font.family: theme.family
                                    font.pixelSize: Style.font.heading
                                    font.weight: Font.DemiBold
                                    horizontalAlignment: Text.AlignHCenter
                                    wrapMode: Text.WordWrap
                                }
                                Text {
                                    Layout.fillWidth: true
                                    Layout.maximumWidth: Style.space(430)
                                    Layout.alignment: Qt.AlignHCenter
                                    visible: root.stateLoaded && !root.apps.length
                                    text: root.tr("使用推荐分组，一次安排 AI、开发、浏览器和通信应用。也可以从添加一个应用开始。")
                                    color: root.muted
                                    font.family: theme.family
                                    font.pixelSize: Style.font.subtitle
                                    horizontalAlignment: Text.AlignHCenter
                                    wrapMode: Text.WordWrap
                                }
                                Ui.ActionButton {
                                    id: emptyActionButton
                                    Layout.alignment: Qt.AlignHCenter
                                    visible: root.stateLoaded
                                    text: root.apps.length ? root.tr("清除搜索") : root.tr("使用推荐分组…")
                                    primary: !root.apps.length
                                    enabled: root.apps.length > 0 || root.writable
                                    onClicked: if (root.apps.length) searchField.clear(); else root.requestSetup()
                                }
                            }
                        }
                    }
                    RowLayout {
                        Layout.fillWidth: true
                        spacing: Style.space(10)
                        Rectangle {
                            implicitWidth: Style.space(6)
                            implicitHeight: implicitWidth
                            radius: width / 2
                            color: root.issues.length ? root.danger : root.snapshot.active ? root.accent : root.muted
                        }
                        Text {
                            Layout.fillWidth: true
                            text: root.busy ? root.tr(root.actionLabel(root.pendingAction)) + "…" : !root.stateLoaded ? root.tr("状态待读取") : root.tr("在 {0} 个工作区安排了 {1} 个应用").replace("{0}", root.workspaceCount).replace("{1}", root.apps.length) + " · " + (root.snapshot.active ? root.tr("已启用") : root.tr("未启用"))
                            textFormat: Text.PlainText
                            elide: Text.ElideRight
                            color: root.muted
                            font.family: theme.family
                            font.pixelSize: Style.font.bodySmall
                        }
                        Text {
                            visible: !root.compact
                            text: root.tr("点击应用修改位置")
                            color: root.muted
                            font.family: theme.family
                            font.pixelSize: Style.font.bodySmall
                        }
                    }
                }
            }

            Controls.Dialog {
                id: editorDialog
                parent: panel.contentItem
                anchors.centerIn: parent
                width: Math.max(1, Math.min(Style.space(520), panel.width - Style.space(32)))
                height: Math.max(1, Math.min(Style.space(650), panel.height - Style.space(32)))
                z: 10
                modal: true
                focus: true
                padding: Style.space(20)
                closePolicy: Controls.Popup.NoAutoClose
                onOpened: workspaceInput.forceActiveFocus()
                onClosed: Qt.callLater(function () { root.restoreFocus(); })
                background: Rectangle { color: root.paper; radius: theme.radius; border.color: root.line }
                header: RowLayout {
                    spacing: Style.space(12)
                    Text {
                        Layout.fillWidth: true
                        Layout.leftMargin: Style.space(20)
                        Layout.topMargin: Style.space(18)
                        text: root.selectedApp ? String(root.selectedApp.name || root.selectedId) : root.tr("打开位置")
                        textFormat: Text.PlainText
                        elide: Text.ElideRight
                        color: root.ink
                        font.family: theme.family
                        font.pixelSize: Style.font.heading
                        font.weight: Font.Bold
                    }
                    Text {
                        Layout.rightMargin: Style.space(20)
                        Layout.topMargin: Style.space(18)
                        visible: root.editorDirty
                        text: root.tr("未保存")
                        color: root.muted
                        font.family: theme.family
                        font.pixelSize: Style.font.bodySmall
                    }
                }
                contentItem: ColumnLayout {
                    spacing: Style.space(14)
                    Keys.onEscapePressed: function (event) { root.requestDismiss(); event.accepted = true; }
                    Controls.ScrollView {
                        id: detailScroll
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        Layout.minimumHeight: 0
                        clip: true
                        contentWidth: availableWidth
                        contentHeight: editorBody.implicitHeight
                        Controls.ScrollBar.horizontal.policy: Controls.ScrollBar.AlwaysOff
                        ColumnLayout {
                            id: editorBody
                            width: detailScroll.availableWidth
                            spacing: Style.space(12)
                            Text {
                                Layout.fillWidth: true
                                text: root.tr("打开位置")
                                color: root.ink
                                font.family: theme.family
                                font.pixelSize: Style.font.title
                                font.weight: Font.DemiBold
                            }
                            RowLayout {
                                Layout.fillWidth: true
                                spacing: Style.space(8)
                                Repeater {
                                    model: [1, 2, 3, 4]
                                    delegate: Ui.ActionButton {
                                        required property int modelData
                                        Layout.fillWidth: true
                                        text: String(modelData)
                                        primary: root.editorWorkspace === modelData
                                        enabled: root.writable
                                        Accessible.name: root.tr("工作区") + " " + modelData
                                        onClicked: root.chooseWorkspace(modelData)
                                    }
                                }
                            }
                            RowLayout {
                                Layout.fillWidth: true
                                spacing: Style.space(12)
                                Text {
                                    Layout.fillWidth: true
                                    text: root.tr("工作区") + " 1–999"
                                    color: root.muted
                                    font.family: theme.family
                                    font.pixelSize: Style.font.body
                                }
                                Controls.SpinBox {
                                    id: workspaceInput
                                    from: 1
                                    to: 999
                                    editable: true
                                    value: root.editorWorkspace
                                    enabled: root.writable
                                    implicitWidth: Style.space(140)
                                    implicitHeight: Style.space(40)
                                    palette.base: root.paper
                                    palette.text: root.ink
                                    palette.button: root.surface
                                    palette.buttonText: root.ink
                                    palette.highlight: root.accent
                                    palette.highlightedText: root.paper
                                    font.family: theme.family
                                    font.pixelSize: Style.font.title
                                    focusPolicy: Qt.StrongFocus
                                    Accessible.name: root.tr("默认工作区编号")
                                    onValueModified: root.editorWorkspace = value
                                }
                            }
                            Text {
                                Layout.fillWidth: true
                                Layout.topMargin: Style.space(5)
                                text: root.tr("再次打开应用")
                                color: root.ink
                                font.family: theme.family
                                font.pixelSize: Style.font.title
                                font.weight: Font.DemiBold
                            }
                            Controls.ButtonGroup { id: behaviorGroup }
                            Ui.WindowChoice {
                                id: focusChoice
                                Layout.fillWidth: true
                                text: root.tr("直接切换到已有窗口")
                                description: root.tr("保留你手动移动过的位置。")
                                checked: root.editorBehavior === "focus"
                                enabled: root.writable
                                Controls.ButtonGroup.group: behaviorGroup
                                onClicked: root.editorBehavior = "focus"
                            }
                            Ui.WindowChoice {
                                id: moveChoice
                                Layout.fillWidth: true
                                text: root.tr("先移回默认工作区，再切换")
                                description: root.tr("每次打开都回到上面设置的位置。")
                                checked: root.editorBehavior === "move"
                                enabled: root.writable
                                Controls.ButtonGroup.group: behaviorGroup
                                onClicked: root.editorBehavior = "move"
                            }
                            Controls.CheckBox {
                                id: moveExistingChoice
                                Layout.fillWidth: true
                                Layout.topMargin: Style.space(4)
                                text: root.tr("现在也移动已打开的窗口")
                                checked: root.editorMoveExisting
                                enabled: root.writable && root.selectedApp !== null
                                font.family: theme.family
                                font.pixelSize: Style.font.body
                                palette.windowText: root.ink
                                palette.text: root.ink
                                palette.highlight: root.accent
                                onToggled: root.editorMoveExisting = checked
                                Accessible.description: root.tr("仅影响此应用")
                            }
                            Text {
                                Layout.fillWidth: true
                                text: root.editorMoveExisting ? root.tr("仅影响此应用") : root.tr("此处修改只决定之后的打开方式。")
                                wrapMode: Text.WordWrap
                                color: root.muted
                                font.family: theme.family
                                font.pixelSize: Style.font.bodySmall
                            }
                            Ui.ActionButton {
                                id: editorOptionsButton
                                Layout.fillWidth: true
                                text: (root.editorOptionsExpanded ? "− " : "+ ") + root.tr("更多应用选项")
                                enabled: !root.busy
                                onClicked: root.editorOptionsExpanded = !root.editorOptionsExpanded
                            }
                            ColumnLayout {
                                Layout.fillWidth: true
                                visible: root.editorOptionsExpanded
                                spacing: Style.space(10)
                                Text {
                                    Layout.fillWidth: true
                                    text: root.tr("快捷键：") + (root.selectedApp && root.selectedApp.shortcuts && root.selectedApp.shortcuts.length ? root.selectedApp.shortcuts.join(" · ") : root.tr("未单独设置，可在高级设置中添加"))
                                    textFormat: Text.PlainText
                                    wrapMode: Text.WordWrap
                                    color: root.muted
                                    font.family: theme.family
                                    font.pixelSize: Style.font.body
                                }
                                Text {
                                    Layout.fillWidth: true
                                    text: root.tr("临时工作区中的窗口遵循 Scratchpad 打开方式。")
                                    wrapMode: Text.WordWrap
                                    color: root.muted
                                    font.family: theme.family
                                    font.pixelSize: Style.font.bodySmall
                                }
                                Controls.CheckBox {
                                    id: editorSpecialChoice
                                    Layout.fillWidth: true
                                    text: root.tr("整理时包含临时工作区")
                                    checked: root.editorIncludeSpecial
                                    enabled: root.writable && root.editorMoveExisting
                                    font.family: theme.family
                                    font.pixelSize: Style.font.body
                                    palette.windowText: root.ink
                                    palette.text: root.ink
                                    palette.highlight: root.accent
                                    onToggled: root.editorIncludeSpecial = checked
                                    Accessible.description: root.tr("默认保护 scratchpad 和其他特殊工作区；勾选后保存或整理才会迁移这些窗口。")
                                }
                                Ui.ActionButton {
                                    Layout.fillWidth: true
                                    text: root.tr("打开或切换到此应用")
                                    enabled: root.writable && root.selectedApp !== null
                                    onClicked: root.requestAction({action: "launch", app_id: root.selectedId})
                                }
                                Ui.ActionButton {
                                    Layout.fillWidth: true
                                    text: root.tr("高级设置…")
                                    enabled: root.writable
                                    onClicked: root.requestAction({action: "terminal", view: "advanced"})
                                }
                                Ui.ActionButton {
                                    id: removeButton
                                    Layout.fillWidth: true
                                    text: root.tr("停止管理此应用…")
                                    danger: true
                                    enabled: root.writable && root.selectedApp !== null
                                    onClicked: root.ask("remove", root.withRevision({action: "remove", app_id: root.selectedId}), root.tr("取消管理此应用？"), root.tr("将恢复“") + String(root.selectedApp.name) + root.tr("”的受管启动器和快捷键。其他应用保持原有配置，已有窗口不会被关闭。"), false)
                                }
                            }
                        }
                    }
                    RowLayout {
                        Layout.fillWidth: true
                        visible: root.editorSaveError
                        Text {
                            Layout.fillWidth: true
                            text: root.tr(root.editorSaveMessage)
                            wrapMode: Text.WordWrap
                            maximumLineCount: 2
                            elide: Text.ElideRight
                            color: root.danger
                            font.family: theme.family
                            font.pixelSize: Style.font.body
                        }
                        Ui.ActionButton { text: root.tr("查看详情"); onClicked: root.openReport() }
                    }
                    RowLayout {
                        Layout.fillWidth: true
                        Text {
                            Layout.fillWidth: true
                            text: root.busy ? root.tr("正在保存设置") + "…" : ""
                            color: root.muted
                            font.family: theme.family
                            font.pixelSize: Style.font.bodySmall
                        }
                        Ui.ActionButton {
                            id: editorCancelButton
                            text: root.tr("返回")
                            enabled: !root.busy
                            onClicked: root.requestEditorClose()
                        }
                        Ui.ActionButton {
                            id: saveButton
                            text: root.editorMoveExisting ? root.tr("保存并移动") : root.tr("保存")
                            primary: true
                            enabled: root.writable && root.selectedApp !== null
                            onClicked: root.saveSelected()
                        }
                    }
                }
            }

            Controls.Dialog {
                id: morePopup
                parent: panel.contentItem
                anchors.centerIn: parent
                width: Math.max(1, Math.min(Style.space(390), panel.width - Style.space(32)))
                height: Math.max(1, Math.min(Style.space(540), panel.height - Style.space(32)))
                z: 20
                modal: true
                focus: true
                padding: Style.space(18)
                closePolicy: Controls.Popup.CloseOnEscape | Controls.Popup.CloseOnPressOutside
                onOpened: refreshButton.forceActiveFocus()
                onClosed: Qt.callLater(function () { if (root.opened && !reportDialog.visible && !confirmation.visible) moreButton.forceActiveFocus(); })
                background: Rectangle { color: root.paper; radius: theme.radius; border.color: root.line }
                header: Text {
                    text: root.tr("更多")
                    padding: Style.space(18)
                    bottomPadding: Style.space(4)
                    color: root.ink
                    font.family: theme.family
                    font.pixelSize: Style.font.heading
                    font.weight: Font.Bold
                }
                contentItem: ColumnLayout {
                    spacing: Style.space(10)
                    Controls.ScrollView {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        clip: true
                        contentWidth: availableWidth
                        Controls.ScrollBar.horizontal.policy: Controls.ScrollBar.AlwaysOff
                        ColumnLayout {
                            width: parent.width
                            spacing: Style.space(8)
                            Ui.ActionButton {
                                id: refreshButton
                                Layout.fillWidth: true
                                text: root.tr("重新读取状态")
                                enabled: !root.busy
                                onClicked: { morePopup.close(); root.requestAction({action: "status"}); }
                            }
                            Ui.ActionButton {
                                id: setupButton
                                Layout.fillWidth: true
                                text: root.tr("使用推荐分组…")
                                enabled: root.writable
                                onClicked: { morePopup.close(); root.requestSetup(); }
                            }
                            Ui.ActionButton {
                                id: arrangeButton
                                Layout.fillWidth: true
                                text: root.tr("整理已打开窗口…")
                                enabled: root.writable && root.apps.length > 0
                                onClicked: root.requestArrange()
                            }
                            Ui.ActionButton {
                                id: diagnosticsButton
                                Layout.fillWidth: true
                                text: root.tr("配置与诊断")
                                onClicked: root.openReport()
                            }
                            Ui.ActionButton {
                                id: advancedButton
                                Layout.fillWidth: true
                                text: root.tr("高级设置…")
                                enabled: root.writable
                                onClicked: { morePopup.close(); root.requestAction({action: "terminal", view: "advanced"}); }
                            }
                            Ui.ActionButton {
                                id: languageButton
                                Layout.fillWidth: true
                                text: root.language === "zh" ? "中文 / English" : "English / 中文"
                                Accessible.name: "语言 / Language"
                                enabled: !root.busy && !confirmation.opened
                                onClicked: root.setLanguage(root.language === "zh" ? "en" : "zh")
                            }
                            Ui.ActionButton {
                                id: resetButton
                                Layout.fillWidth: true
                                Layout.topMargin: Style.space(8)
                                text: root.tr("停用全部规则…")
                                danger: true
                                enabled: root.writable
                                onClicked: {
                                    morePopup.close();
                                    root.ask("reset", root.withRevision({action: "reset"}), root.tr("撤销全部工作区规则？"), root.tr("将恢复受管文件的原有内容，并停用当前工作区路由。应用配置仍保留，已经打开的窗口不会自动搬回。"), true);
                                }
                            }
                        }
                    }
                    Ui.ActionButton {
                        id: moreCloseButton
                        Layout.alignment: Qt.AlignRight
                        text: root.tr("返回")
                        onClicked: morePopup.close()
                    }
                }
            }

            Controls.Dialog {
                id: reportDialog
                parent: panel.contentItem
                anchors.centerIn: parent
                width: Math.max(1, Math.min(Style.space(640), panel.width - Style.space(32)))
                height: Math.max(1, Math.min(Style.space(520), panel.height - Style.space(32)))
                z: 30
                modal: true
                focus: true
                padding: Style.space(18)
                closePolicy: Controls.Popup.CloseOnEscape
                onOpened: reportCloseButton.forceActiveFocus()
                onClosed: Qt.callLater(function () { root.restoreFocus(); })
                background: Rectangle { color: root.paper; radius: theme.radius; border.color: root.line }
                header: Text {
                    text: root.tr("配置与诊断")
                    padding: Style.space(18)
                    bottomPadding: Style.space(4)
                    color: root.ink
                    font.family: theme.family
                    font.pixelSize: Style.font.heading
                    font.weight: Font.Bold
                }
                contentItem: ColumnLayout {
                    spacing: Style.space(12)
                    Controls.ScrollView {
                        id: reportScroll
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        clip: true
                        contentWidth: availableWidth
                        contentHeight: reportBody.implicitHeight
                        Controls.ScrollBar.horizontal.policy: Controls.ScrollBar.AlwaysOff
                        Controls.ScrollBar.vertical.policy: Controls.ScrollBar.AsNeeded
                        WheelHandler {
                            target: null
                            onWheel: function (event) {
                                var delta = event.pixelDelta.y || event.angleDelta.y / 120 * Style.space(48);
                                var maximum = Math.max(0, reportScroll.contentHeight - reportScroll.availableHeight);
                                reportScroll.contentItem.contentY = Math.max(0, Math.min(maximum, reportScroll.contentItem.contentY - delta));
                                event.accepted = true;
                            }
                        }
                        ColumnLayout {
                            id: reportBody
                            width: reportScroll.availableWidth
                            spacing: Style.space(12)
                            Text {
                                Layout.fillWidth: true
                                text: root.snapshot.active ? root.tr("工作区规则已启用") : root.tr("工作区规则尚未启用")
                                color: root.ink
                                font.family: theme.family
                                font.pixelSize: Style.font.title
                                font.weight: Font.DemiBold
                            }
                            Controls.TextArea {
                                id: messageLabel
                                Layout.fillWidth: true
                                text: root.tr(root.lastMessage)
                                visible: text !== ""
                                textFormat: TextEdit.PlainText
                                readOnly: true
                                selectByMouse: true
                                persistentSelection: true
                                padding: 0
                                background: null
                                color: root.messageIsError ? root.danger : root.ink
                                font.family: theme.family
                                font.pixelSize: Style.font.body
                                wrapMode: TextEdit.WrapAnywhere
                                onTextChanged: Qt.callLater(function () { reportScroll.contentItem.contentY = 0; })
                                Accessible.name: text
                            }
                            Controls.TextArea {
                                Layout.fillWidth: true
                                visible: root.issues.length > 0
                                text: root.issues.map(function (issue) { return root.tr(issue); }).join("\n\n")
                                textFormat: TextEdit.PlainText
                                readOnly: true
                                selectByMouse: true
                                wrapMode: TextEdit.WrapAnywhere
                                padding: 0
                                background: null
                                color: root.danger
                                font.family: theme.family
                                font.pixelSize: Style.font.body
                            }
                            Text {
                                Layout.fillWidth: true
                                text: root.tr("技术信息")
                                color: root.muted
                                font.family: theme.family
                                font.pixelSize: Style.font.body
                                font.weight: Font.DemiBold
                            }
                            Controls.TextArea {
                                Layout.fillWidth: true
                                text: root.tr("版本") + " " + String(root.snapshot.version || "1.3.0-rc.1") + (root.snapshot.backendVersion ? root.tr(" · 组件 ") + root.snapshot.backendVersion : "") + "\n" + String(root.snapshot.configPath || "")
                                textFormat: TextEdit.PlainText
                                readOnly: true
                                selectByMouse: true
                                wrapMode: TextEdit.WrapAnywhere
                                padding: 0
                                background: null
                                color: root.muted
                                font.family: theme.family
                                font.pixelSize: Style.font.bodySmall
                            }
                        }
                    }
                    Flow {
                        Layout.fillWidth: true
                        Layout.preferredHeight: childrenRect.height
                        spacing: Style.space(8)
                        Ui.ActionButton {
                            id: checkButton
                            text: root.tr("检查配置")
                            enabled: root.ready && !root.busy
                            onClicked: root.send({action: "doctor"})
                        }
                        Ui.ActionButton {
                            id: adoptButton
                            text: root.tr("接纳外部修改…")
                            visible: root.issues.length > 0
                            enabled: root.writable && !editorDialog.visible
                            hint: root.tr("请先返回并处理未保存的设置，再接纳外部修改。")
                            onClicked: root.ask("adopt", root.withRevision({action: "adopt"}), root.tr("接纳这些外部修改？"), root.tr("请确认下列改动是你希望保留的。接纳后，受管文件的当前内容会成为新的恢复基线，再应用工作区配置。\n\n") + root.issues.map(function (issue) { return root.tr(issue); }).join("\n"), false)
                        }
                        Ui.ActionButton {
                            id: reportCloseButton
                            text: root.tr("返回")
                            onClicked: reportDialog.close()
                        }
                    }
                }
            }

            Controls.Dialog {
                id: confirmation
                z: 40
                parent: panel.contentItem
                anchors.centerIn: parent
                width: Math.max(1, Math.min(Style.space(560), panel.width - Style.space(40)))
                height: Math.min(Style.space(440), panel.height - Style.space(40))
                modal: true
                focus: true
                padding: Style.space(18)
                closePolicy: Controls.Popup.NoAutoClose
                title: root.confirmTitle
                onOpened: root.confirmKind === "setup-result" ? acceptConfirm.forceActiveFocus() : cancelConfirm.forceActiveFocus()
                onClosed: Qt.callLater(function () {
                    root.restoreFocus();
                })
                background: Rectangle {
                    color: root.paper
                    radius: theme.radius
                    border.width: 2
                    border.color: root.confirmDanger ? root.danger : root.accent
                }
                header: Text {
                    text: root.confirmTitle
                    textFormat: Text.PlainText
                    color: root.ink
                    font.family: theme.family
                    font.pixelSize: Style.font.heading
                    font.weight: Font.Bold
                    wrapMode: Text.WordWrap
                    padding: Style.space(18)
                    bottomPadding: Style.space(4)
                }
                contentItem: ColumnLayout {
                    spacing: Style.space(15)
                    Keys.onEscapePressed: function (event) {
                        confirmation.close();
                        event.accepted = true;
                    }
                    Controls.ScrollView {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        clip: true
                        contentWidth: availableWidth
                        Controls.ScrollBar.horizontal.policy: Controls.ScrollBar.AlwaysOff
                        Controls.TextArea {
                            text: root.confirmMessage
                            textFormat: TextEdit.PlainText
                            readOnly: true
                            selectByMouse: true
                            wrapMode: TextEdit.WrapAnywhere
                            color: root.ink
                            font.family: theme.family
                            font.pixelSize: Style.font.title
                            background: null
                            Accessible.name: root.confirmMessage
                        }
                    }
                    Controls.CheckBox {
                        id: includeSpecialChoice
                        KeyNavigation.tab: cancelConfirm
                        KeyNavigation.backtab: acceptConfirm
                        Layout.fillWidth: true
                        visible: root.confirmKind === "arrange"
                        text: root.tr("整理时包含临时工作区")
                        checked: root.includeSpecial
                        font.family: theme.family
                        font.pixelSize: Style.font.body
                        palette.windowText: root.ink
                        palette.text: root.ink
                        palette.highlight: root.accent
                        onToggled: root.includeSpecial = checked
                        Accessible.description: root.tr("默认保护 scratchpad 和其他特殊工作区；勾选后保存或整理才会迁移这些窗口。")
                    }
                    RowLayout {
                        Layout.fillWidth: true
                        Item { Layout.fillWidth: true }
                        Ui.ActionButton {
                            id: cancelConfirm
                            visible: root.confirmKind !== "setup-result"
                            text: root.tr("取消")
                            onClicked: confirmation.close()
                            KeyNavigation.backtab: includeSpecialChoice.visible ? includeSpecialChoice : acceptConfirm
                        }
                        Ui.ActionButton {
                            id: acceptConfirm
                            text: root.confirmKind === "setup-result" ? root.tr("知道了") : root.confirmKind === "setup" ? root.tr("开始预设") : root.confirmKind === "arrange" ? root.tr("现在整理") : root.confirmDanger ? root.tr("确认撤销") : root.tr("确认继续")
                            primary: true
                            danger: root.confirmDanger
                            onClicked: root.acceptConfirmation()
                            KeyNavigation.tab: includeSpecialChoice.visible ? includeSpecialChoice : cancelConfirm
                        }
                    }
                }
            }
        }
    }
}
