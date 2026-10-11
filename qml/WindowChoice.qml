import QtQuick
import QtQuick.Controls

RadioButton {
    id: control

    property string description: ""
    focusPolicy: Qt.StrongFocus
    hoverEnabled: true
    padding: 10
    leftPadding: 40
    implicitHeight: Math.max(64, contentItem.implicitHeight + topPadding + bottomPadding)
    Accessible.name: text
    Accessible.description: description

    indicator: Rectangle {
        x: 12
        y: 15
        width: 18
        height: 18
        radius: 9
        color: "#fffdf5"
        border.width: 2
        border.color: control.enabled ? "#32674c" : "#9aa99b"
        Rectangle {
            width: 8
            height: 8
            radius: 4
            anchors.centerIn: parent
            visible: control.checked
            color: control.enabled ? "#32674c" : "#9aa99b"
        }
    }

    contentItem: Column {
        spacing: 4
        Text {
            width: parent.width
            text: control.text
            textFormat: Text.PlainText
            font.pixelSize: 14
            font.weight: Font.DemiBold
            color: control.enabled ? "#263e30" : "#7d8c80"
            wrapMode: Text.WordWrap
        }
        Text {
            width: parent.width
            text: control.description
            textFormat: Text.PlainText
            font.pixelSize: 12
            color: "#5e7364"
            wrapMode: Text.WordWrap
        }
    }

    background: Rectangle {
        radius: 10
        color: control.checked ? "#e4eee0" : control.hovered ? "#f0f4e9" : "#fffdf5"
        border.width: control.activeFocus ? 2 : 1
        border.color: control.checked || control.activeFocus ? "#32674c" : "#d7dfd0"
    }
}
