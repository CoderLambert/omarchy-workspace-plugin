import QtQuick
import qs.Commons

// Bind to the shared shell singletons; no independent theme reader or cache.
QtObject {
    readonly property color ink: Color.menu.text
    readonly property color paper: Color.menu.background
    readonly property color accent: Color.accent
    readonly property color danger: Color.urgent
    readonly property color muted: Util.alpha(ink, 0.68)
    readonly property color line: Style.normalBorderFor(ink, accent)
    readonly property color surface: Style.normalFillFor(ink, accent)
    readonly property color hover: Style.hoverFillFor(ink, accent)
    readonly property color selected: Style.selectedFillFor(ink, accent)
    readonly property color notice: Util.alpha(accent, 0.10)
    readonly property color error: Util.alpha(danger, 0.10)
    readonly property color scrim: Color.menu.scrim
    readonly property color border: Color.menu.border
    readonly property int radius: Style.cornerRadius
    readonly property string family: Style.font.menuFamily
}
