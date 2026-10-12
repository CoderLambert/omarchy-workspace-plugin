"""Explicit window/process/theme adapters for isolated Qt UI checks.

These simulate shell APIs; real Omarchy loading must be checked separately.
No workspace backend is called and no actual desktop theme is changed.
"""
from pathlib import Path
import re
import shutil


def prepare_ui_fixture(source: Path, check: Path) -> None:
    (check / 'stubs').mkdir(parents=True, exist_ok=True)
    shutil.copytree(source / 'qml', check / 'qml', dirs_exist_ok=True)
    # Explicit qs.Commons adapters: exercise reactive bindings without starting
    # Omarchy or changing the user's actual desktop theme.
    commons = check / 'qs' / 'Commons'
    commons.mkdir(parents=True, exist_ok=True)
    (commons / 'qmldir').write_text('module qs.Commons\nsingleton Color 1.0 Color.qml\nsingleton Style 1.0 Style.qml\nsingleton Util 1.0 Util.qml\nsingleton Border 1.0 Border.qml\n')
    (check / 'stubs' / 'BorderSurface.qml').write_text('''import QtQuick
    Rectangle {
        property var borderSpec: ({})
        border.color: borderSpec.color || "transparent"
        border.width: borderSpec.width || 0
    }
    ''')
    (commons / 'Border.qml').write_text('''pragma Singleton
    import QtQuick
    QtObject {
        function surfaceSpec(section, role, color, width) { return {color: color, width: width} }
    }
    ''')
    (commons / 'Util.qml').write_text('''pragma Singleton
    import QtQuick
    QtObject { function alpha(c, a) { return Qt.rgba(c.r, c.g, c.b, a) } }
    ''')
    (commons / 'Color.qml').write_text('''pragma Singleton
    import QtQuick
    QtObject {
        id: root
        property color foreground: "#cdd6f4"
        property color background: "#1e1e2e"
        property color accent: "#89b4fa"
        property color urgent: "#f38ba8"
        readonly property QtObject menu: QtObject {
            readonly property color text: root.foreground
            readonly property color background: root.background
            readonly property color scrim: Util.alpha(root.background, 0.5)
            readonly property color border: root.accent
        }
        readonly property QtObject tooltip: QtObject {
            readonly property color background: root.background
            readonly property color text: root.foreground
            readonly property color border: root.accent
        }
        function useLight() {
            foreground = "#4c4f69"; background = "#eff1f5";
            accent = "#1e66f5"; urgent = "#d20f39";
        }
        function useDark() {
            foreground = "#cdd6f4"; background = "#1e1e2e";
            accent = "#89b4fa"; urgent = "#f38ba8";
        }
    }
    ''')
    (commons / 'Style.qml').write_text('''pragma Singleton
    import QtQuick
    QtObject {
        id: root
        property int cornerRadius: 8
        property real scale: 1
        function space(n) { return Math.round(n * scale) }
        readonly property QtObject spacing: QtObject {
            readonly property int panelPadding: root.space(18)
            readonly property int controlPaddingX: root.space(10)
            readonly property int controlPaddingY: root.space(6)
        }
        readonly property QtObject font: QtObject {
            readonly property string family: "sans-serif"
            readonly property string menuFamily: family
            readonly property int bodySmall: root.space(11)
            readonly property int body: root.space(12)
            readonly property int subtitle: root.space(13)
            readonly property int title: root.space(14)
            readonly property int heading: root.space(16)
            readonly property int display: root.space(24)
        }
        function normalFillFor(f, a) { return Util.alpha(f, 0.04) }
        function normalBorderFor(f, a) { return Util.alpha(f, 0.20) }
        function hoverFillFor(f, a) { return Util.alpha(f, 0.10) }
        function selectedFillFor(f, a) { return Util.alpha(f, 0.18) }
        function pressedFillFor(f, a) { return Util.alpha(f, 0.24) }
        function controlFill(focus, hover, f, a) {
            return focus ? Util.alpha(a, 0.12) : hover ? hoverFillFor(f, a) : normalFillFor(f, a)
        }
    }
    ''')

    # The source UI remains unchanged except the real host's window/process
    # adapters. This verifies Qt Quick construction and interaction, not Wayland
    # compositor behavior or Quickshell's runtime module implementation.
    qml = (source / 'Panel.qml').read_text()
    qml = qml.replace('import qs.Ui as ShellUi', 'import \"stubs\" as ShellUi')
    qml = re.sub(r'location: .*ui.ini"', 'location: "file://' + str(check / 'ui.ini') + '"', qml)
    qml = qml.replace('import Quickshell\n', 'import "stubs"\n')
    qml = qml.replace('import Quickshell.Io\n', '')
    qml = qml.replace('import Quickshell.Wayland\n', '')
    qml = re.sub(r'^\s*(?:exclusionMode:|WlrLayershell\.).*$', '', qml, flags=re.MULTILINE)
    (check / 'Panel.qml').write_text(qml)
    (check / 'stubs' / 'PanelWindow.qml').write_text('''
    import QtQuick
    import QtQuick.Window
    Window {
        width: 1100
        height: 850
        transientParent: null
        readonly property bool backingWindowVisible: visible
        property PanelAnchors anchors: PanelAnchors {}
    }
    ''')
    (check / 'stubs' / 'PanelAnchors.qml').write_text('''
    import QtQuick
    QtObject {
        property bool top: false
        property bool bottom: false
        property bool left: false
        property bool right: false
    }
    ''')
    (check / 'stubs' / 'Process.qml').write_text('''
    import QtQuick
    QtObject {
        property var environment: ({})
        property var command: []
        property bool running: false
        property QtObject stdout: null
        property QtObject stderr: null
        signal started()
        signal exited(int exitCode, int exitStatus)
    }
    ''')
    (check / 'stubs' / 'StdioCollector.qml').write_text('''
    import QtQuick
    QtObject {
        property string text: ""
        signal streamFinished()
    }
    ''')
