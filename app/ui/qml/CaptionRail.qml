pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Window
import QtQuick.Layouts

// ③ 字幕轨：AI 回复以无卡片容器字幕呈现（方案 4.4.2）。
// 从右侧 spring settle 进入，不自动收回；单条 × 只关闭这一条。
// 本窗口不使用 WindowTransparentForInput：普通区域穿透由 platform/windows
// 的命中测试（WM_NCHITTEST）统一处理，否则单条 × 将无法点击。
Window {
    id: rail

    property var captions: []      // [{ id, kind, text, visible }]
    property bool reduceMotion: false
    property var hitRects: []      // 由 Python 按字幕实际边界写入的屏幕矩形

    signal captionDismissed(string id)

    width: theme.captionMaxWidth
    height: theme.captionRailHeight
    color: "transparent"
    flags: Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool
    title: "Desktop AI Coach · 字幕"

    Theme { id: theme }

    ListView {
        id: list
        anchors.fill: parent
        anchors.margins: 8
        spacing: 8
        interactive: false
        model: rail.captions

        delegate: Item {
            required property var modelData
            width: list.width
            height: row.implicitHeight

            RowLayout {
                id: row
                width: parent.width
                spacing: 6

                // 左侧细短光标线，代替卡片容器
                Rectangle {
                    Layout.alignment: Qt.AlignTop
                    width: 2
                    height: Math.max(14, textItem.implicitHeight)
                    radius: 1
                    color: {
                        switch (modelData.kind) {
                        case "warning": return theme.danger
                        case "complete": return theme.champagne
                        case "analysis":
                        case "instruction": return theme.moonlight
                        default: return theme.glassBorder
                        }
                    }
                }

                Text {
                    id: textItem
                    Layout.fillWidth: true
                    text: "AI · " + modelData.text
                    color: theme.textPrimary
                    font.family: theme.fontFamily
                    font.pixelSize: 13
                    wrapMode: Text.WordWrap
                    // 轻微文字阴影保证任意桌面上可读，不使用渐变文字或发光背景
                    style: Text.Raised
                    styleColor: Qt.rgba(0.008, 0.024, 0.063, 0.85)
                }

                Item {
                    id: closeHit
                    Layout.alignment: Qt.AlignTop
                    implicitWidth: 20
                    implicitHeight: 20

                    Text {
                        anchors.centerIn: parent
                        text: "×"
                        color: theme.textMuted
                        font.pixelSize: 15
                    }

                    MouseArea {
                        anchors.fill: parent
                        cursorShape: Qt.PointingHandCursor
                        onClicked: rail.captionDismissed(row.parent.modelData.id)
                    }

                    // 上报命中矩形，供 Win32 分层命中测试放行该区域
                    function publishHitRect() {
                        var p = closeHit.mapToItem(null, 0, 0)
                        rail.registerHitRect(p.x, p.y, width, height)
                    }

                    Component.onCompleted: publishHitRect()
                }
            }
        }

        add: Transition {
            enabled: !rail.reduceMotion
            NumberAnimation { properties: "x"; from: 60; duration: theme.springDuration; easing.type: Easing.Bezier; easing.bezierCurve: theme.springCurve }
            NumberAnimation { properties: "opacity"; from: 0; to: 1; duration: theme.springDuration }
        }
        addDisplaced: Transition {
            NumberAnimation { properties: "y"; duration: theme.springDuration; easing.type: Easing.Bezier; easing.bezierCurve: theme.springCurve }
        }
    }

    // 避免 × 命中区在重排后失效
    signal hitRectRegistered(real x, real y, real w, real h)

    function registerHitRect(x, y, w, h) {
        var next = rail.hitRects.slice()
        next.push({ x: x, y: y, w: w, h: h })
        rail.hitRects = next
        rail.hitRectRegistered(x, y, w, h)
    }

    function resetHitRects() {
        rail.hitRects = []
    }
}

