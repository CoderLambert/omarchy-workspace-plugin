import QtQuick
import QtQuick.Controls
import qs.Commons

RadioButton {
    id: control

    Theme { id: theme }
    property string description: ""
    focusPolicy: Qt.StrongFocus
    hoverEnabled: true
    padding: Style.space(10)
    leftPadding: Style.space(40)
    implicitHeight: Math.max(Style.space(64), contentItem.implicitHeight + topPadding + bottomPadding)
    Accessible.name: text
    Accessible.description: description

    indicator: Rectangle {
        x: Style.space(12)
        y: Style.space(15)
        width: Style.space(18)
        height: Style.space(18)
        radius: 9
        color: theme.paper
        border.width: Style.space(2)
        border.color: control.enabled ? theme.accent : theme.muted
        Rectangle {
            width: Style.space(8)
            height: Style.space(8)
            radius: 4
            anchors.centerIn: parent
            visible: control.checked
            color: control.enabled ? theme.accent : theme.muted
        }
    }

    contentItem: Column {
        spacing: 4
        Text {
            width: parent.width
            text: control.text
            textFormat: Text.PlainText
            font.family: theme.family
            font.pixelSize: Style.font.title
            font.weight: Font.DemiBold
            color: control.enabled ? theme.ink : theme.muted
            wrapMode: Text.WordWrap
        }
        Text {
            width: parent.width
            text: control.description
            textFormat: Text.PlainText
            font.family: theme.family
            font.pixelSize: Style.font.body
            color: theme.muted
            wrapMode: Text.WordWrap
        }
    }

    background: Rectangle {
        radius: theme.radius
        color: control.checked ? theme.selected : control.hovered ? theme.hover : theme.paper
        border.width: control.activeFocus ? 2 : 1
        border.color: control.checked || control.activeFocus ? theme.accent : theme.line
    }
}
