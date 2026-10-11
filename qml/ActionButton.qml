import QtQuick
import QtQuick.Controls

Button {
    id: control

    property bool primary: false
    property bool danger: false
    property string hint: ""
    readonly property color actionColor: danger ? "#993f32" : "#286449"

    font.pixelSize: 13
    font.weight: Font.DemiBold
    focusPolicy: Qt.StrongFocus
    hoverEnabled: true
    leftPadding: 13
    rightPadding: 13
    topPadding: 9
    bottomPadding: 9
    implicitHeight: Math.max(38, implicitContentHeight + topPadding + bottomPadding)
    implicitWidth: implicitContentWidth + leftPadding + rightPadding
    Accessible.name: text
    Accessible.description: hint

    contentItem: Text {
        text: control.text
        textFormat: Text.PlainText
        font: control.font
        color: !control.enabled ? "#8a998d" : control.primary ? "#fffdf5" : control.actionColor
        horizontalAlignment: Text.AlignHCenter
        verticalAlignment: Text.AlignVCenter
        elide: Text.ElideRight
    }

    background: Rectangle {
        radius: 9
        color: !control.enabled ? "#e8ebe1" : control.primary ? (control.down ? "#1d4d36" : control.hovered ? "#317756" : control.actionColor) : control.down ? "#d6e4d6" : control.hovered ? "#e4eee0" : "#fffdf5"
        border.width: control.activeFocus ? 2 : 1
        border.color: control.activeFocus ? control.actionColor : "#cbd8c9"
    }

    ToolTip.visible: hovered && hint !== ""
    ToolTip.delay: 650
    ToolTip.text: hint
}
