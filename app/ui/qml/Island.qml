pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Window
import QtQuick.Layouts
import QtQuick.Controls

// ① 灵动岛：收起态 / 展开态共用同一材质与边界（方案 4.2.2）。
// 本窗口接收鼠标（岛上控件可点）；桌面其余区域由覆盖层负责穿透。
Window {
    id: island

    // ---- Python 侧驱动属性 ----
    property string appState: "idle"
    property string cacheText: "本地缓存 01:00"
    property string stepText: ""
    property bool expanded: false
    property bool lowPerformance: false

    // ---- 由 Python 连接的信号 ----
    signal askRequested()
    signal arrowRequested()
    signal clearRequested()
    signal pauseToggled()
    signal historyRequested()
    signal settingsRequested()

    width: expanded ? theme.islandExpandedWidth : theme.islandCollapsedWidth
    height: expanded ? theme.islandExpandedHeight : theme.islandCollapsedHeight
    color: "transparent"
    flags: Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool
    title: "Desktop AI Coach"

    Theme { id: theme }

    Behavior on width {
        NumberAnimation {
            duration: theme.springDuration
            easing.type: Easing.Bezier
            easing.bezierCurve: theme.springCurve
        }
    }
    Behavior on height {
        NumberAnimation {
            duration: theme.springDuration
            easing.type: Easing.Bezier
            easing.bezierCurve: theme.springCurve
        }
    }

    Rectangle {
        id: shell
        anchors.fill: parent
        radius: theme.radius
        color: theme.glassSurfaceStrong
        border.width: 1
        border.color: theme.glassBorder

        // 顶部内高光 + 底部内暗边，表达层级而非不透明黑板
        Rectangle {
            anchors.top: parent.top
            anchors.left: parent.left
            anchors.right: parent.right
            height: 1
            color: theme.glassHighlight
            radius: parent.radius
        }
        Rectangle {
            anchors.bottom: parent.bottom
            anchors.left: parent.left
            anchors.right: parent.right
            height: 2
            color: theme.glassShade
            radius: parent.radius
        }

        ColumnLayout {
            anchors.fill: parent
            anchors.margins: 12
            spacing: 8

            // ---- 收起态一行：状态点 + 状态文字 + 缓存时长 + 工具按钮 ----
            RowLayout {
                Layout.fillWidth: true
                spacing: 10

                Rectangle {
                    id: statusDot
                    width: 10
                    height: 10
                    radius: 5
                    color: theme.stateColor(island.appState)

                    // 低频呼吸，不做高亮频闪
                    SequentialAnimation on opacity {
                        running: !island.lowPerformance
                        loops: Animation.Infinite
                        NumberAnimation { to: 0.45; duration: 900; easing.type: Easing.InOutSine }
                        NumberAnimation { to: 1.0; duration: 900; easing.type: Easing.InOutSine }
                    }
                }

                Text {
                    text: theme.stateLabel(island.appState)
                    color: theme.textPrimary
                    font.family: theme.fontFamily
                    font.pixelSize: 13
                    font.weight: Font.DemiBold
                }

                Text {
                    text: island.cacheText
                    color: theme.textMuted
                    font.family: theme.fontFamily
                    font.pixelSize: 12
                }

                Item { Layout.fillWidth: true }

                Text {
                    visible: island.stepText.length > 0
                    text: island.stepText
                    color: theme.champagne
                    font.family: theme.fontFamily
                    font.pixelSize: 12
                }

                Repeater {
                    model: [
                        { glyph: "↗", tip: "放置箭头", sig: "arrow" },
                        { glyph: "⏸", tip: "暂停采集", sig: "pause" },
                        { glyph: "⟲", tip: "清空标注", sig: "clear" },
                        { glyph: "☰", tip: "历史", sig: "history" },
                        { glyph: "⚙", tip: "设置", sig: "settings" }
                    ]

                    delegate: Rectangle {
                        id: toolButton
                        required property var modelData

                        // 供 ToolTip 使用：ToolTip 不在 delegate 的绑定作用域内
                        readonly property string tipText: modelData ? modelData.tip : ""
                        readonly property string glyphText: modelData ? modelData.glyph : ""

                        width: 26
                        height: 26
                        radius: 8
                        color: hover.containsMouse ? Qt.rgba(1, 1, 1, 0.14) : "transparent"
                        border.width: 1
                        border.color: hover.containsMouse ? theme.glassBorder : "transparent"

                        Text {
                            anchors.centerIn: parent
                            text: toolButton.glyphText
                            color: theme.textSecondary
                            font.pixelSize: 13
                        }

                        MouseArea {
                            id: hover
                            anchors.fill: parent
                            hoverEnabled: true
                            cursorShape: Qt.PointingHandCursor
                            onClicked: {
                                switch (toolButton.modelData.sig) {
                                case "arrow": island.arrowRequested(); break
                                case "pause": island.pauseToggled(); break
                                case "clear": island.clearRequested(); break
                                case "history": island.historyRequested(); break
                                case "settings": island.settingsRequested(); break
                                }
                            }
                        }

                        // 工具提示：纯图标命令必须可识别（方案 17.3）
                        ToolTip.visible: hover.containsMouse
                        ToolTip.text: toolButton.tipText
                        ToolTip.delay: 400
                    }
                }
            }

            // ---- 展开态内容 ----
            Rectangle {
                Layout.fillWidth: true
                Layout.fillHeight: true
                visible: island.expanded
                radius: theme.radiusSmall
                color: theme.glassSurface
                border.width: 1
                border.color: theme.glassBorder

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 12
                    spacing: 8

                    Text {
                        text: "快捷问题"
                        color: theme.textMuted
                        font.family: theme.fontFamily
                        font.pixelSize: 11
                    }

                    Repeater {
                        model: ["这个界面怎么导出 PDF？", "刚才那个报错是什么意思？", "下一步该点哪里？"]

                        delegate: Rectangle {
                            required property string modelData
                            Layout.fillWidth: true
                            height: 30
                            radius: theme.radiusSmall
                            color: quickHover.containsMouse ? Qt.rgba(1, 1, 1, 0.12) : "transparent"

                            Text {
                                anchors.verticalCenter: parent.verticalCenter
                                anchors.left: parent.left
                                anchors.leftMargin: 10
                                text: parent.modelData
                                color: theme.textSecondary
                                font.family: theme.fontFamily
                                font.pixelSize: 12
                            }

                            MouseArea {
                                id: quickHover
                                anchors.fill: parent
                                hoverEnabled: true
                                cursorShape: Qt.PointingHandCursor
                                onClicked: {
                                    island.askRequested()
                                }
                            }
                        }
                    }

                    Item { Layout.fillHeight: true }

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 8

                        Text {
                            text: "隐私：常驻岛不模糊桌面，采集默认本地缓存"
                            color: theme.textMuted
                            font.family: theme.fontFamily
                            font.pixelSize: 11
                            Layout.fillWidth: true
                            wrapMode: Text.WordWrap
                        }
                    }
                }
            }
        }

        // 拖动抓手：松开后由 Python 吸附到显示器上边缘
        MouseArea {
            id: dragHandle
            anchors.top: parent.top
            anchors.left: parent.left
            anchors.right: parent.right
            height: 20
            cursorShape: Qt.SizeAllCursor
            property real pressX: 0
            property real pressY: 0

            onPressed: (mouse) => {
                pressX = mouse.x
                pressY = mouse.y
            }
            onPositionChanged: (mouse) => {
                if (pressed) {
                    island.x += mouse.x - pressX
                    island.y += mouse.y - pressY
                }
            }
            onDoubleClicked: island.expanded = !island.expanded
        }
    }
}
