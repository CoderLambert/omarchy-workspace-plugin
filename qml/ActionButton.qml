import QtQuick
import QtQuick.Controls
import qs.Commons

Button {
    id: control

    Theme { id: theme }
    property bool primary: false
    property bool danger: false
    property string hint: ""
    readonly property color actionColor: danger ? theme.danger : theme.accent

    font.family: theme.family
    font.pixelSize: Style.font.subtitle
    font.weight: Font.DemiBold
    focusPolicy: Qt.StrongFocus
    hoverEnabled: true
    leftPadding: Style.spacing.controlPaddingX
    rightPadding: Style.spacing.controlPaddingX
    topPadding: Style.spacing.controlPaddingY
    bottomPadding: Style.spacing.controlPaddingY
    implicitHeight: Math.max(Style.space(34), implicitContentHeight + topPadding + bottomPadding)
    implicitWidth: implicitContentWidth + leftPadding + rightPadding
    Accessible.name: text
    Accessible.description: hint

    contentItem: Text {
        text: control.text
        textFormat: Text.PlainText
        font: control.font
        color: !control.enabled ? theme.muted : control.primary ? theme.paper : control.danger ? theme.danger : theme.ink
        horizontalAlignment: Text.AlignHCenter
        verticalAlignment: Text.AlignVCenter
        elide: Text.ElideRight
    }

    background: Rectangle {
        radius: theme.radius
        color: !control.enabled ? theme.surface : control.primary ? (control.down ? Qt.darker(control.actionColor, 1.15) : control.hovered ? Qt.lighter(control.actionColor, 1.12) : control.actionColor) : control.down ? Style.pressedFillFor(theme.ink, theme.accent) : Style.controlFill(control.activeFocus, control.hovered, theme.ink, theme.accent)
        border.width: control.activeFocus ? 2 : 1
        border.color: control.activeFocus || control.primary ? control.actionColor : theme.line
    }

    ToolTip {
        implicitWidth: Math.min(Style.space(340), contentItem.implicitWidth + leftPadding + rightPadding)
        visible: control.hovered && control.hint !== ""
        delay: 650
        text: control.hint
        padding: Style.spacing.controlPaddingX
        background: Rectangle {
            color: Color.tooltip.background
            radius: theme.radius
            border.color: Color.tooltip.border
        }
        contentItem: Text {
            text: control.hint
            wrapMode: Text.WordWrap
            color: Color.tooltip.text
            font.family: theme.family
            font.pixelSize: Style.font.bodySmall
        }
    }
}
