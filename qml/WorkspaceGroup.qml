pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls as Controls
import QtQuick.Layouts
import qs.Commons
import "Strings.js" as Strings

Controls.Pane {
    id: groupCard

    required property var group
    property string language: "zh"
    property bool busy: false
    signal editRequested(string appId)
    signal navigateRequested(string appId, int direction)

    Theme { id: theme }
    function tr(text) { return Strings.translate(language, text); }
    function focusApp(appId) {
        for (var i = 0; i < rows.count; i++) {
            var row = rows.itemAt(i);
            if (row && String(row.app.id) === appId) {
                row.forceActiveFocus();
                return row;
            }
        }
        return null;
    }

    padding: Style.space(12)
    background: Rectangle {
        color: theme.surface
        radius: theme.radius
        border.color: theme.line
    }

    contentItem: ColumnLayout {
        spacing: Style.space(4)
        RowLayout {
            Layout.fillWidth: true
            Layout.bottomMargin: Style.space(8)
            Text {
                Layout.fillWidth: true
                text: groupCard.tr("工作区") + " " + groupCard.group.workspace
                color: theme.ink
                font.family: theme.family
                font.pixelSize: Style.font.title
                font.weight: Font.DemiBold
            }
            Text {
                text: groupCard.group.apps.length + (groupCard.language === "zh" ? " 个应用" : groupCard.group.apps.length === 1 ? " app" : " apps")
                color: theme.muted
                font.family: theme.family
                font.pixelSize: Style.font.bodySmall
            }
        }
        Repeater {
            id: rows
            model: groupCard.group.apps
            delegate: Controls.ItemDelegate {
                id: appRow
                required property var modelData
                readonly property var app: modelData
                readonly property bool elsewhere: Number(app.windows || 0) > 0 && (app.windowWorkspaces || []).some(function (ws) { return String(ws) !== String(app.workspace); })
                objectName: "app-" + String(app.id)
                Layout.fillWidth: true
                implicitHeight: Math.max(Style.space(52), contentItem.implicitHeight + padding * 2)
                padding: Style.space(6)
                enabled: !groupCard.busy
                focusPolicy: Qt.StrongFocus
                hoverEnabled: true
                Accessible.name: String(app.name || app.id) + "，" + groupCard.tr("工作区") + " " + app.workspace
                Accessible.description: groupCard.tr("点击应用修改位置")
                onClicked: groupCard.editRequested(String(app.id))
                Keys.onReturnPressed: clicked()
                Keys.onEnterPressed: clicked()
                Keys.onDownPressed: groupCard.navigateRequested(String(app.id), 1)
                Keys.onUpPressed: groupCard.navigateRequested(String(app.id), -1)
                background: Rectangle {
                    radius: theme.radius
                    color: appRow.activeFocus ? theme.selected : appRow.hovered ? theme.hover : "transparent"
                    border.width: appRow.activeFocus ? 2 : 0
                    border.color: theme.accent
                }
                contentItem: RowLayout {
                    spacing: Style.space(10)
                    Rectangle {
                        implicitWidth: Style.space(7)
                        implicitHeight: implicitWidth
                        radius: width / 2
                        color: Number(appRow.app.windows || 0) > 0 ? theme.accent : "transparent"
                        border.color: Number(appRow.app.windows || 0) > 0 ? theme.accent : theme.muted
                    }
                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: Style.space(3)
                        Text {
                            Layout.fillWidth: true
                            text: String(appRow.app.name || appRow.app.id)
                            textFormat: Text.PlainText
                            elide: Text.ElideRight
                            font.family: theme.family
                            font.pixelSize: Style.font.title
                            color: theme.ink
                        }
                        Text {
                            Layout.fillWidth: true
                            text: appRow.elsewhere ? groupCard.tr("当前工作区：{0}").replace("{0}", (appRow.app.windowWorkspaces || []).join(" / ")) : Number(appRow.app.windows || 0) > 0 ? groupCard.tr("运行中") + " · " + appRow.app.windows + (groupCard.language === "zh" ? " 个窗口" : Number(appRow.app.windows) === 1 ? " window" : " windows") : groupCard.tr("未打开")
                            textFormat: Text.PlainText
                            elide: Text.ElideRight
                            font.family: theme.family
                            font.pixelSize: Style.font.bodySmall
                            color: theme.muted
                        }
                    }
                    Text {
                        text: "›"
                        color: appRow.hovered || appRow.activeFocus ? theme.accent : theme.muted
                        font.pixelSize: Style.font.heading
                    }
                }
            }
        }
    }
}
