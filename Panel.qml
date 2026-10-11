pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls as Controls
import QtQuick.Layouts
import Quickshell
import Quickshell.Io
import Quickshell.Wayland
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
    readonly property color ink: "#263e30"
    readonly property color muted: "#607365"
    readonly property color accent: "#286449"
    readonly property color paper: "#f5f1e5"
    readonly property color surface: "#fffdf5"
    readonly property color line: "#cfdbc9"
    readonly property color danger: "#993f32"

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
    property string selectedId: ""
    property int editorWorkspace: 1
    property string editorBehavior: "focus"
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
        if (!query)
            return apps;
        return apps.filter(function (app) {
            return String(app.name || "").toLowerCase().indexOf(query) !== -1 || String(app.id || "").toLowerCase().indexOf(query) !== -1 || String(app.workspace).indexOf(query) !== -1;
        });
    }
    readonly property var selectedApp: appById(selectedId)
    readonly property bool editorDirty: selectedApp !== null && (editorWorkspace !== Number(selectedApp.workspace) || editorBehavior !== String(selectedApp.existing_window || "focus"))
    readonly property int selectedFilteredIndex: {
        for (var i = 0; i < filteredApps.length; i++) {
            if (filteredApps[i].id === selectedId)
                return i;
        }
        return -1;
    }
    readonly property bool compact: card.width < 740

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
    }

    function receiveState(next) {
        if (!next || !Array.isArray(next.apps))
            return;
        var previous = selectedId;
        snapshot = next;
        stateLoaded = true;
        if (!appById(previous))
            previous = apps.length ? String(apps[0].id) : "";
        loadEditor(previous);
    }

    function selectApp(id) {
        if (busy || id === selectedId)
            return;
        if (editorDirty) {
            ask("discard-select", {
                id: id
            }, "放弃未保存的修改？", "当前应用的工作区设置尚未保存。继续后将显示另一个应用。", false);
            return;
        }
        loadEditor(id);
    }

    function moveSelection(direction) {
        if (!filteredApps.length || busy)
            return;
        var index = Math.max(0, Math.min(filteredApps.length - 1, selectedFilteredIndex + direction));
        selectApp(String(filteredApps[index].id));
        appList.positionViewAtIndex(index, ListView.Contain);
    }

    function showMessage(message, isError) {
        lastMessage = String(message || "");
        messageIsError = isError === true;
    }

    function actionLabel(action) {
        var labels = {
            status: "正在读取状态",
            install: "正在安装或更新组件",
            set: "正在保存并整理此应用",
            launch: "正在聚焦或启动",
            remove: "正在取消管理",
            arrange: "正在整理全部窗口",
            apply: "正在应用配置",
            adopt: "正在接纳外部修改",
            reset: "正在撤销工作区规则",
            recover: "正在恢复中断任务",
            doctor: "正在检查",
            terminal: "正在打开终端"
        };
        return labels[action] || "正在处理";
    }

    function send(request) {
        if (busy)
            return;
        var action = String(request.action || "");
        if (!ready && action !== "status" && action !== "install") {
            showMessage("请先安装或更新组件，再修改工作区配置。", true);
            return;
        }
        if (snapshot.pending && ["status", "install", "doctor", "recover"].indexOf(action) === -1) {
            showMessage("存在中断任务，请先恢复后继续。", true);
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
            showMessage("组件未返回有效结果（退出码 " + exitCode + "）。" + (errorText ? "\n" + errorText.trim().slice(0, 1800) : " 请点击刷新重试，或从终端执行 doctor。"), true);
            return;
        }
        if (result.state)
            receiveState(result.state);
        var success = result.ok === true && exitCode === 0;
        showMessage(result.message || (success ? "操作完成。" : "操作未完成，请检查提示后重试。"), !success);
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
            ask("discard-action", request, "放弃未保存的修改？", "当前编辑内容尚未保存。继续操作将重新读取配置。", false);
        } else {
            send(request);
        }
    }

    function saveSelected() {
        if (!writable || !selectedApp)
            return;
        // Clicking Save can precede SpinBox's editing-finished notification.
        // Read the editor explicitly so a just-typed value is never lost.
        var value = workspaceInput.valueFromText(String(workspaceInput.contentItem.text), workspaceInput.locale);
        if (!Number.isInteger(value) || value < 1 || value > 999) {
            showMessage("工作区编号必须是 1–999 的整数。", true);
            workspaceInput.forceActiveFocus();
            return;
        }
        editorWorkspace = value;
        send(withRevision({
            action: "set",
            app_id: selectedId,
            workspace: value,
            existing_window: editorBehavior,
            move_existing: true
        }));
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
        if (kind === "discard-select") {
            loadEditor(request.id);
        } else if (kind === "discard-close") {
            loadEditor(selectedId);
            dismiss();
        } else {
            loadEditor(selectedId);
            send(request);
        }
    }

    function requestDismiss() {
        if (confirmation.opened) {
            confirmation.close();
            return;
        }
        if (busy) {
            showMessage("操作正在完成，请稍候再关闭。", false);
        } else if (editorDirty) {
            ask("discard-close", {}, "放弃未保存的修改？", "关闭后将保留上一次已保存的工作区设置。", false);
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
            if (root.opened)
                searchField.forceActiveFocus();
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
            showMessage("操作正在完成，请稍候再关闭。", false);
            return;
        }
        confirmation.close();
        opened = false;
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
                root.errorText = "无法启动 python3。请确认 Python 已安装，插件 scripts/bridge.py 存在。";
                root.finish(-1);
            }
        }
    }

    Timer {
        id: patienceTimer
        interval: 25000
        onTriggered: if (root.busy)
            root.showMessage(root.actionLabel(root.pendingAction) + "，耗时较长，请保持面板打开。", false)
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
                    if (root.opened)
                        searchField.forceActiveFocus();
                });
            }
        }

        Rectangle {
            anchors.fill: parent
            color: "#60213629"
            MouseArea {
                anchors.fill: parent
                onClicked: root.requestDismiss()
            }
        }

        Controls.Pane {
            id: card
            anchors.centerIn: parent
            width: Math.max(1, Math.min(1010, parent.width - 24))
            height: Math.max(1, Math.min(790, parent.height - 24))
            padding: width < 520 ? 12 : 20
            palette.text: root.ink
            palette.windowText: root.ink
            palette.buttonText: root.ink
            palette.base: root.surface
            palette.window: root.paper
            palette.button: root.surface
            palette.highlight: root.accent
            palette.highlightedText: root.surface
            palette.mid: root.line
            palette.light: root.surface

            background: Rectangle {
                color: root.paper
                radius: 18
                border.color: "#acbfa9"
                border.width: 1
            }

            // Prevent clicks in an empty part of the card from dismissing it.
            MouseArea {
                anchors.fill: parent
                acceptedButtons: Qt.AllButtons
            }

            FocusScope {
                id: contentFocus
                anchors.fill: parent
                focus: true
                Keys.onEscapePressed: function (event) {
                    root.requestDismiss();
                    event.accepted = true;
                }

                Controls.ScrollView {
                    id: outerScroll
                    anchors.fill: parent
                    clip: true
                    contentWidth: availableWidth
                    Controls.ScrollBar.horizontal.policy: Controls.ScrollBar.AlwaysOff

                    ColumnLayout {
                        width: outerScroll.availableWidth
                        height: Math.max(outerScroll.availableHeight, implicitHeight)
                        spacing: root.compact ? 10 : 13

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 12
                            Rectangle {
                                implicitWidth: 43
                                implicitHeight: 43
                                radius: 13
                                color: root.accent
                                Text {
                                    anchors.centerIn: parent
                                    text: "1·2"
                                    color: root.surface
                                    font.pixelSize: 18
                                    font.weight: Font.Bold
                                }
                            }
                            ColumnLayout {
                                Layout.fillWidth: true
                                spacing: 3
                                Text {
                                    Layout.fillWidth: true
                                    text: "工作区管理"
                                    color: root.ink
                                    font.pixelSize: root.compact ? 22 : 25
                                    font.weight: Font.Bold
                                }
                                Text {
                                    Layout.fillWidth: true
                                    text: "应用各就其位，再次打开直接复用。"
                                    color: root.muted
                                    font.pixelSize: 12
                                    elide: Text.ElideRight
                                }
                            }
                            Ui.ActionButton {
                                id: closeButton
                                text: "关闭"
                                hint: root.busy ? "操作完成后可以关闭" : "Escape"
                                enabled: !root.busy
                                onClicked: root.requestDismiss()
                            }
                        }

                        Flow {
                            Layout.fillWidth: true
                            Layout.preferredHeight: childrenRect.height
                            spacing: 7
                            Ui.ActionButton {
                                id: refreshButton
                                text: "刷新"
                                enabled: !root.busy
                                onClicked: root.requestAction({
                                    action: "status"
                                })
                            }
                            Ui.ActionButton {
                                text: "自动预设…"
                                hint: "在终端识别 AI、开发、浏览器与通信应用；完成后重新打开面板"
                                enabled: root.writable
                                onClicked: root.requestAction({
                                    action: "terminal",
                                    view: "setup"
                                })
                            }
                            Ui.ActionButton {
                                text: "添加应用…"
                                hint: "从桌面应用选择，或通过已有窗口匹配"
                                enabled: root.writable
                                onClicked: root.requestAction({
                                    action: "terminal",
                                    view: "add"
                                })
                            }
                            Ui.ActionButton {
                                text: "高级设置…"
                                hint: "在终端管理快捷键、匹配规则和更多选项"
                                enabled: root.writable
                                onClicked: root.requestAction({
                                    action: "terminal",
                                    view: "advanced"
                                })
                            }
                            Ui.ActionButton {
                                text: "检查"
                                enabled: root.ready && !root.busy
                                onClicked: root.requestAction({
                                    action: "doctor"
                                })
                            }
                            Ui.ActionButton {
                                text: "整理全部"
                                hint: "把所有受管应用的已有窗口移到各自目标工作区"
                                enabled: root.writable && root.apps.length > 0
                                onClicked: root.requestAction({
                                    action: "arrange"
                                })
                            }
                        }

                        Rectangle {
                            Layout.fillWidth: true
                            Layout.preferredHeight: installLayout.implicitHeight + 22
                            visible: root.stateLoaded && root.snapshot.needsInstall === true
                            color: "#e5eee0"
                            border.color: "#b9cbb4"
                            radius: 11
                            RowLayout {
                                id: installLayout
                                anchors.fill: parent
                                anchors.margins: 11
                                spacing: 12
                                Text {
                                    Layout.fillWidth: true
                                    text: root.snapshot.installed ? "组件需要更新，安装后继续使用。现有应用配置会保留。" : "插件已加载。安装工作区组件后，即可管理应用和快捷键。"
                                    textFormat: Text.PlainText
                                    wrapMode: Text.WordWrap
                                    color: root.ink
                                    font.pixelSize: 13
                                }
                                Ui.ActionButton {
                                    text: root.snapshot.installed ? "更新组件" : "安装组件"
                                    primary: true
                                    enabled: !root.busy
                                    onClicked: root.send({
                                        action: "install"
                                    })
                                }
                            }
                        }

                        Rectangle {
                            Layout.fillWidth: true
                            Layout.preferredHeight: pendingLayout.implicitHeight + 20
                            visible: root.ready && (!!root.snapshot.pending || !!root.snapshot.draft)
                            color: "#f4eaca"
                            border.color: "#d9ca9d"
                            radius: 10
                            RowLayout {
                                id: pendingLayout
                                anchors.fill: parent
                                anchors.margins: 10
                                Text {
                                    Layout.fillWidth: true
                                    text: root.snapshot.pending ? "上一次操作中断，恢复后再继续修改。" : "有已保存但尚未生效的配置。"
                                    wrapMode: Text.WordWrap
                                    font.pixelSize: 13
                                    color: "#755720"
                                }
                                Ui.ActionButton {
                                    text: root.snapshot.pending ? "恢复任务" : "应用配置"
                                    enabled: !root.busy
                                    onClicked: root.requestAction(root.withRevision({
                                        action: root.snapshot.pending ? "recover" : "apply"
                                    }))
                                }
                            }
                        }

                        GridLayout {
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            columns: root.compact ? 1 : 2
                            rowSpacing: 10
                            columnSpacing: 14

                            Rectangle {
                                Layout.fillWidth: true
                                Layout.fillHeight: !root.compact
                                Layout.preferredWidth: 340
                                Layout.preferredHeight: root.compact ? Math.min(190, card.height * 0.28) : 400
                                Layout.minimumHeight: 90
                                color: root.surface
                                border.color: root.line
                                radius: 12

                                ColumnLayout {
                                    anchors.fill: parent
                                    anchors.margins: 12
                                    spacing: 8
                                    RowLayout {
                                        Layout.fillWidth: true
                                        Text {
                                            text: "受管应用"
                                            color: root.ink
                                            font.pixelSize: 14
                                            font.weight: Font.DemiBold
                                        }
                                        Text {
                                            Layout.fillWidth: true
                                            text: root.apps.length + " 个"
                                            color: root.muted
                                            font.pixelSize: 12
                                            horizontalAlignment: Text.AlignRight
                                        }
                                    }
                                    Controls.TextField {
                                        id: searchField
                                        Layout.fillWidth: true
                                        implicitHeight: 38
                                        placeholderText: "搜索应用 / 工作区"
                                        placeholderTextColor: "#81917f"
                                        color: root.ink
                                        font.pixelSize: 13
                                        selectByMouse: true
                                        leftPadding: 11
                                        rightPadding: 11
                                        Accessible.name: "搜索受管应用"
                                        background: Rectangle {
                                            color: "#f5f7ef"
                                            radius: 8
                                            border.width: searchField.activeFocus ? 2 : 1
                                            border.color: searchField.activeFocus ? root.accent : root.line
                                        }
                                        Keys.onDownPressed: function (event) {
                                            if (root.filteredApps.length) {
                                                if (root.selectedFilteredIndex < 0)
                                                    root.selectApp(String(root.filteredApps[0].id));
                                                appList.forceActiveFocus();
                                            }
                                            event.accepted = true;
                                        }
                                    }
                                    ListView {
                                        id: appList
                                        Layout.fillWidth: true
                                        Layout.fillHeight: true
                                        clip: true
                                        spacing: 5
                                        model: root.filteredApps
                                        currentIndex: root.selectedFilteredIndex
                                        activeFocusOnTab: true
                                        boundsBehavior: Flickable.StopAtBounds
                                        Controls.ScrollBar.vertical: Controls.ScrollBar {}
                                        Keys.onDownPressed: function (event) {
                                            root.moveSelection(1);
                                            event.accepted = true;
                                        }
                                        Keys.onUpPressed: function (event) {
                                            root.moveSelection(-1);
                                            event.accepted = true;
                                        }

                                        delegate: Controls.ItemDelegate {
                                            id: appRow
                                            required property var modelData
                                            width: appList.width
                                            implicitHeight: 64
                                            padding: 10
                                            highlighted: root.selectedId === modelData.id
                                            focusPolicy: Qt.StrongFocus
                                            enabled: !root.busy
                                            Accessible.name: String(modelData.name) + "，工作区 " + modelData.workspace
                                            onClicked: root.selectApp(String(modelData.id))
                                            background: Rectangle {
                                                radius: 8
                                                color: appRow.highlighted ? "#e2eddd" : appRow.hovered ? "#eff3e8" : "transparent"
                                                border.width: appRow.activeFocus ? 2 : appRow.highlighted ? 1 : 0
                                                border.color: appRow.activeFocus ? root.accent : "#b3c8ac"
                                            }
                                            contentItem: RowLayout {
                                                spacing: 8
                                                ColumnLayout {
                                                    Layout.fillWidth: true
                                                    spacing: 4
                                                    Text {
                                                        Layout.fillWidth: true
                                                        text: String(appRow.modelData.name || appRow.modelData.id)
                                                        textFormat: Text.PlainText
                                                        font.pixelSize: 14
                                                        font.weight: appRow.highlighted ? Font.DemiBold : Font.Normal
                                                        color: root.ink
                                                        elide: Text.ElideRight
                                                    }
                                                    Text {
                                                        Layout.fillWidth: true
                                                        text: Number(appRow.modelData.windows || 0) > 0 ? appRow.modelData.windows + " 个窗口 · " + (appRow.modelData.windowWorkspaces || []).join(" / ") : "尚未打开"
                                                        textFormat: Text.PlainText
                                                        color: root.muted
                                                        font.pixelSize: 11
                                                        elide: Text.ElideRight
                                                    }
                                                }
                                                Rectangle {
                                                    implicitWidth: Math.max(31, workspaceNumber.implicitWidth + 14)
                                                    implicitHeight: 31
                                                    radius: 8
                                                    color: appRow.highlighted ? root.accent : "#e9eee2"
                                                    Text {
                                                        id: workspaceNumber
                                                        anchors.centerIn: parent
                                                        text: appRow.modelData.workspace
                                                        color: appRow.highlighted ? root.surface : root.accent
                                                        font.pixelSize: 14
                                                        font.weight: Font.Bold
                                                    }
                                                }
                                            }
                                        }

                                        Text {
                                            anchors.centerIn: parent
                                            width: parent.width - 16
                                            visible: root.filteredApps.length === 0
                                            text: !root.stateLoaded ? "正在读取应用…" : root.apps.length ? "没有匹配的应用。" : "还没有受管应用。\n使用“自动预设”或“添加应用”开始。"
                                            color: root.muted
                                            font.pixelSize: 13
                                            lineHeight: 1.4
                                            horizontalAlignment: Text.AlignHCenter
                                            wrapMode: Text.WordWrap
                                        }
                                    }
                                }
                            }

                            Controls.ScrollView {
                                id: detailScroll
                                Layout.fillWidth: true
                                Layout.fillHeight: true
                                Layout.preferredWidth: 565
                                Layout.preferredHeight: root.compact ? 350 : 400
                                Layout.minimumHeight: 100
                                clip: true
                                contentWidth: availableWidth
                                Controls.ScrollBar.horizontal.policy: Controls.ScrollBar.AlwaysOff

                                ColumnLayout {
                                    width: detailScroll.availableWidth
                                    spacing: 12

                                    RowLayout {
                                        Layout.fillWidth: true
                                        Text {
                                            Layout.fillWidth: true
                                            text: root.selectedApp ? String(root.selectedApp.name || root.selectedId) : "为每个应用安排位置"
                                            textFormat: Text.PlainText
                                            font.pixelSize: 21
                                            font.weight: Font.Bold
                                            color: root.ink
                                            wrapMode: Text.WordWrap
                                        }
                                        Text {
                                            visible: root.editorDirty
                                            text: "未保存"
                                            color: "#947024"
                                            font.pixelSize: 12
                                        }
                                    }

                                    Text {
                                        Layout.fillWidth: true
                                        text: root.selectedApp ? root.selectedId : "1 AI · 2 开发 · 3 浏览器 · 4 通信"
                                        textFormat: Text.PlainText
                                        color: root.muted
                                        font.pixelSize: 12
                                        wrapMode: Text.WrapAnywhere
                                    }

                                    ColumnLayout {
                                        Layout.fillWidth: true
                                        visible: root.selectedApp !== null
                                        spacing: 10

                                        Text {
                                            text: "默认工作区"
                                            color: root.ink
                                            font.pixelSize: 14
                                            font.weight: Font.DemiBold
                                        }
                                        RowLayout {
                                            Layout.fillWidth: true
                                            spacing: 10
                                            Controls.SpinBox {
                                                id: workspaceInput
                                                from: 1
                                                to: 999
                                                editable: true
                                                value: root.editorWorkspace
                                                enabled: root.writable
                                                implicitWidth: 140
                                                implicitHeight: 40
                                                font.pixelSize: 16
                                                focusPolicy: Qt.StrongFocus
                                                Accessible.name: "默认工作区编号"
                                                onValueModified: root.editorWorkspace = value
                                            }
                                            Text {
                                                Layout.fillWidth: true
                                                text: "1–999。保存后立即整理此应用的已有窗口。"
                                                wrapMode: Text.WordWrap
                                                color: root.muted
                                                font.pixelSize: 12
                                            }
                                        }

                                        Text {
                                            Layout.topMargin: 5
                                            text: "再次打开时"
                                            color: root.ink
                                            font.pixelSize: 14
                                            font.weight: Font.DemiBold
                                        }
                                        Controls.ButtonGroup {
                                            id: behaviorGroup
                                        }
                                        Ui.WindowChoice {
                                            id: focusChoice
                                            Layout.fillWidth: true
                                            text: "跳到已有窗口"
                                            description: "保留窗口当前的位置，直接切换并聚焦。"
                                            checked: root.editorBehavior === "focus"
                                            enabled: root.writable
                                            Controls.ButtonGroup.group: behaviorGroup
                                            onClicked: root.editorBehavior = "focus"
                                        }
                                        Ui.WindowChoice {
                                            id: moveChoice
                                            Layout.fillWidth: true
                                            text: "先归位，再聚焦"
                                            description: "先移到上面的默认工作区，再切换并聚焦。"
                                            checked: root.editorBehavior === "move"
                                            enabled: root.writable
                                            Controls.ButtonGroup.group: behaviorGroup
                                            onClicked: root.editorBehavior = "move"
                                        }

                                        Text {
                                            Layout.fillWidth: true
                                            Layout.topMargin: 3
                                            text: "快捷键：" + (root.selectedApp && root.selectedApp.shortcuts && root.selectedApp.shortcuts.length ? root.selectedApp.shortcuts.join(" · ") : "未单独设置，可在高级设置中添加")
                                            textFormat: Text.PlainText
                                            wrapMode: Text.WordWrap
                                            color: root.muted
                                            font.pixelSize: 12
                                        }

                                        Flow {
                                            Layout.fillWidth: true
                                            Layout.preferredHeight: childrenRect.height
                                            Layout.topMargin: 5
                                            spacing: 8
                                            Ui.ActionButton {
                                                text: "保存并整理此应用"
                                                primary: true
                                                enabled: root.writable && root.selectedApp !== null
                                                onClicked: root.saveSelected()
                                            }
                                            Ui.ActionButton {
                                                text: "聚焦 / 启动"
                                                enabled: root.writable && root.selectedApp !== null
                                                onClicked: root.requestAction({
                                                    action: "launch",
                                                    app_id: root.selectedId
                                                })
                                            }
                                            Ui.ActionButton {
                                                text: "取消管理…"
                                                enabled: root.writable && root.selectedApp !== null
                                                onClicked: root.ask("remove", root.withRevision({
                                                    action: "remove",
                                                    app_id: root.selectedId
                                                }), "取消管理此应用？", "将恢复“" + root.selectedApp.name + "”的受管启动器和快捷键。其他应用保持原有配置，已有窗口不会被关闭。", false)
                                            }
                                        }
                                    }

                                    Text {
                                        Layout.fillWidth: true
                                        visible: root.selectedApp === null
                                        text: "先选择左侧应用，再设置工作区和复用方式。自动预设可识别当前已安装的常见应用；自定义程序可通过已有窗口添加。"
                                        color: root.muted
                                        font.pixelSize: 14
                                        lineHeight: 1.5
                                        wrapMode: Text.WordWrap
                                    }

                                    Rectangle {
                                        Layout.fillWidth: true
                                        Layout.preferredHeight: statusDetails.implicitHeight + 20
                                        Layout.topMargin: 4
                                        color: "#eaf0e2"
                                        radius: 10
                                        ColumnLayout {
                                            id: statusDetails
                                            anchors.fill: parent
                                            anchors.margins: 10
                                            spacing: 5
                                            Text {
                                                Layout.fillWidth: true
                                                text: !root.stateLoaded ? "状态待读取" : root.snapshot.active ? "工作区规则已启用" : "工作区规则尚未启用"
                                                color: root.accent
                                                font.pixelSize: 13
                                                font.weight: Font.DemiBold
                                            }
                                            Text {
                                                Layout.fillWidth: true
                                                text: "插件 " + String(root.snapshot.version || "1.2.0") + (root.snapshot.backendVersion ? " · 组件 " + root.snapshot.backendVersion : "")
                                                textFormat: Text.PlainText
                                                color: root.muted
                                                font.pixelSize: 11
                                            }
                                            Text {
                                                Layout.fillWidth: true
                                                text: String(root.snapshot.configPath || "")
                                                textFormat: Text.PlainText
                                                visible: text !== ""
                                                wrapMode: Text.WrapAnywhere
                                                color: root.muted
                                                font.pixelSize: 11
                                            }
                                        }
                                    }
                                }
                            }
                        }

                        Rectangle {
                            Layout.fillWidth: true
                            Layout.preferredHeight: Math.min(100, messageLabel.implicitHeight + 20)
                            visible: root.lastMessage !== ""
                            color: root.messageIsError ? "#f7e6db" : "#e9efdf"
                            border.color: root.messageIsError ? "#dab9a8" : "#cad8bc"
                            radius: 10
                            Controls.ScrollView {
                                anchors.fill: parent
                                anchors.margins: 10
                                contentWidth: availableWidth
                                clip: true
                                Controls.ScrollBar.horizontal.policy: Controls.ScrollBar.AlwaysOff
                                Text {
                                    id: messageLabel
                                    width: parent.width
                                    text: root.lastMessage
                                    textFormat: Text.PlainText
                                    color: root.messageIsError ? root.danger : root.ink
                                    font.pixelSize: 12
                                    wrapMode: Text.WrapAnywhere
                                    Accessible.role: Accessible.StaticText
                                    Accessible.name: text
                                }
                            }
                        }

                        Flow {
                            Layout.fillWidth: true
                            Layout.preferredHeight: childrenRect.height
                            spacing: 8
                            Ui.ActionButton {
                                text: "撤销全部规则…"
                                danger: true
                                enabled: root.writable
                                onClicked: root.ask("reset", root.withRevision({
                                    action: "reset"
                                }), "撤销全部工作区规则？", "将恢复受管文件的原有内容，并停用当前工作区路由。应用配置仍保留，已经打开的窗口不会自动搬回。", true)
                            }
                            Ui.ActionButton {
                                text: "接纳外部修改…"
                                visible: root.issues.length > 0
                                enabled: root.writable
                                hint: "先检查具体路径，再决定是否把当前内容保存为新的恢复基线"
                                onClicked: root.ask("adopt", root.withRevision({
                                    action: "adopt"
                                }), "接纳这些外部修改？", "请确认下列改动是你希望保留的。接纳后，受管文件的当前内容会成为新的恢复基线，再应用工作区配置。\n\n" + root.issues.join("\n"), false)
                            }
                            Text {
                                height: 38
                                verticalAlignment: Text.AlignVCenter
                                text: root.busy ? "处理中，请保持面板打开" : "Tab 切换 · ↑ ↓ 选择应用 · Esc 关闭"
                                color: root.muted
                                font.pixelSize: 11
                            }
                        }
                    }
                }
            }

            Controls.Dialog {
                id: confirmation
                parent: panel.contentItem
                anchors.centerIn: parent
                width: Math.max(1, Math.min(560, panel.width - 40))
                height: Math.min(440, panel.height - 40)
                modal: true
                focus: true
                padding: 18
                closePolicy: Controls.Popup.NoAutoClose
                title: root.confirmTitle
                onOpened: cancelConfirm.forceActiveFocus()
                onClosed: Qt.callLater(function () {
                    if (root.opened)
                        searchField.forceActiveFocus();
                })
                background: Rectangle {
                    color: root.surface
                    radius: 13
                    border.width: 2
                    border.color: root.confirmDanger ? root.danger : root.accent
                }
                header: Text {
                    text: root.confirmTitle
                    textFormat: Text.PlainText
                    color: root.ink
                    font.pixelSize: 19
                    font.weight: Font.Bold
                    wrapMode: Text.WordWrap
                    padding: 18
                    bottomPadding: 4
                }
                contentItem: ColumnLayout {
                    spacing: 15
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
                            font.pixelSize: 14
                            background: null
                            Accessible.name: root.confirmMessage
                        }
                    }
                    RowLayout {
                        Layout.fillWidth: true
                        Item {
                            Layout.fillWidth: true
                        }
                        Ui.ActionButton {
                            id: cancelConfirm
                            text: "取消"
                            onClicked: confirmation.close()
                            KeyNavigation.backtab: acceptConfirm
                        }
                        Ui.ActionButton {
                            id: acceptConfirm
                            text: root.confirmDanger ? "确认撤销" : "确认继续"
                            primary: true
                            danger: root.confirmDanger
                            onClicked: root.acceptConfirmation()
                            KeyNavigation.tab: cancelConfirm
                        }
                    }
                }
            }
        }
    }
}
