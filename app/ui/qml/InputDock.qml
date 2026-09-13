pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Window
import QtQuick.Layouts

// ② 输入坞：独立窗口，位于灵动岛正下方（方案 4.4.1）。
// Enter 发送、Shift+Enter 换行、Esc 取消；不因灵动岛收起而丢失草稿。
Window {
    id: dock

    property bool focusedInput: false
    property bool submitting: false
    property string errorText: ""
    property string draft: ""

    signal submitted(string text)
    signal cancelled()

    width: focusedInput ? 520 : 360
    height: 46
    color: "transparent"
    flags: Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool
    title: "Desktop AI Coach · 输入"

    Theme { id: theme }

    Behavior on width {
        NumberAnimation {
            duration: theme.springDuration
            easing.type: Easing.Bezier
            easing.bezierCurve: theme.springCurve
        }
    }

    Rectangle {
        anchors.fill: parent
        radius: theme.radiusSmall
        color: theme.glassSurfaceStrong
        border.width: 1
        border.color: dock.errorText.length > 0 ? theme.danger : theme.glassBorder

        Rectangle {
            anchors.top: parent.top
            anchors.left: parent.left
            anchors.right: parent.right
            height: 1
            color: theme.glassHighlight
        }

        RowLayout {
            anchors.fill: parent
            anchors.leftMargin: 12
            anchors.rightMargin: 8
            spacing: 8

        TextInput {
            id: input
            Layout.fillWidth: true
            color: theme.textPrimary
            font.family: theme.fontFamily
            font.pixelSize: 13
            selectByMouse: true
            clip: true

            // 占位文案只表达当前输入用途
            Text {
                anchors.verticalCenter: parent.verticalCenter
                visible: input.text.length === 0
                text: "描述你现在卡住的地方……"
                color: theme.textMuted
                font: input.font
            }

            onTextEdited: dock.draft = text
            onActiveFocusChanged: dock.focusedInput = activeFocus

            Keys.onReturnPressed: (event) => {
                if (event.modifiers & Qt.ShiftModifier) {
                    event.accepted = false
                } else {
                    dock.submit()
                    event.accepted = true
                }
            }
            Keys.onEnterPressed: (event) => {
                dock.submit()
                event.accepted = true
            }
            Keys.onEscapePressed: {
                input.text = ""
                dock.draft = ""
                dock.cancelled()
            }
        }

        Text {
            visible: dock.submitting
            text: "正在理解…"
            color: theme.moonlight
            font.family: theme.fontFamily
            font.pixelSize: 12
        }

        Text {
            visible: dock.errorText.length > 0
            text: dock.errorText
            color: theme.danger
            font.family: theme.fontFamily
            font.pixelSize: 12
        }

        Rectangle {
            width: 56
            height: 30
            radius: theme.radiusSmall
            color: sendHover.containsMouse ? Qt.rgba(0.894, 0.722, 0.388, 0.32) : Qt.rgba(0.894, 0.722, 0.388, 0.18)
            border.width: 1
            border.color: theme.champagne

            Text {
                anchors.centerIn: parent
                text: "发送"
                color: theme.champagne
                font.family: theme.fontFamily
                font.pixelSize: 12
                font.weight: Font.DemiBold
            }

            MouseArea {
                id: sendHover
                anchors.fill: parent
                hoverEnabled: true
                cursorShape: Qt.PointingHandCursor
                onClicked: dock.submit()
            }
        }
        }
    }

    function submit() {
        var text = input.text.trim()
        if (text.length === 0) {
            return
        }
        input.text = ""
        dock.draft = ""
        dock.submitted(text)
    }

    function focusInput() {
        input.forceActiveFocus()
    }
}
