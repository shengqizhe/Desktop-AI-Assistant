pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Window
// ④ 覆盖层：全屏透明窗口，绘制用户箭头、AI 目标框与虚拟鼠标（方案 4.5 / 4.6）。
// 本窗口不接收鼠标：穿透由 platform/windows 的命中测试决定，
// 需要交互时由 Python 切换窗口的 WS_EX_TRANSPARENT 样式。
Window {
    id: overlay

    // [{ id, owner, start:[x,y], end:[x,y], style, color, z_index }]，坐标为 0..1
    property var annotations: []
    property var targetBox: null          // { x, y, w, h, confidence }
    property var virtualCursor: null      // { x, y, opacity, ripple, action }
    property bool arrowMode: false
    property string guideAction: "arrow"
    property bool reduceMotion: false

    // 由 Python 写入的参考分辨率，用于把归一化坐标换算成像素
    property real refWidth: width
    property real refHeight: height

    // 采集用：箭头放置/拖拽时由本区域接收鼠标
    signal arrowDrawn(real x1, real y1, real x2, real y2)

    color: "transparent"
    flags: Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool
    title: "Desktop AI Coach · 覆盖层"

    Theme { id: theme }

    // 普通区域穿透由 platform/windows 切换 WS_EX_TRANSPARENT 实现。
    // 本 MouseArea 只在 arrowMode 期间启用，其余时间窗口对被穿透。
    MouseArea {
        id: drawArea
        anchors.fill: parent
        enabled: overlay.arrowMode
        acceptedButtons: Qt.LeftButton
        cursorShape: overlay.arrowMode ? Qt.CrossCursor : Qt.ArrowCursor
        property real startX: 0
        property real startY: 0
        property bool drawing: false

        onPressed: (mouse) => {
            startX = mouse.x
            startY = mouse.y
            drawing = true
        }
        onReleased: (mouse) => {
            if (!drawing) {
                return
            }
            drawing = false
            var dx = mouse.x - startX
            var dy = mouse.y - startY
            if (Math.abs(dx) < 8 && Math.abs(dy) < 8) {
                // 单击：生成一支默认长度、指向右上的箭头
                overlay.arrowDrawn(startX / overlay.width,
                                   startY / overlay.height,
                                   (startX + 120) / overlay.width,
                                   (startY - 80) / overlay.height)
            } else {
                overlay.arrowDrawn(startX / overlay.width,
                                   startY / overlay.height,
                                   mouse.x / overlay.width,
                                   mouse.y / overlay.height)
            }
        }
    }

    // Esc 退出箭头模式（由 Python 侧同步 arrowMode）
    Shortcut {
        sequence: "Escape"
        enabled: overlay.arrowMode
        onActivated: overlay.arrowMode = false
    }

    function px(nx) { return nx * overlay.refWidth }
    function py(ny) { return ny * overlay.refHeight }

    // ---- 目标框 + 高亮描边 ----
    Rectangle {
        visible: overlay.targetBox !== null
        x: overlay.targetBox ? overlay.px(overlay.targetBox.x) : 0
        y: overlay.targetBox ? overlay.py(overlay.targetBox.y) : 0
        width: overlay.targetBox ? overlay.px(overlay.targetBox.w) : 0
        height: overlay.targetBox ? overlay.py(overlay.targetBox.h) : 0
        color: "transparent"
        border.width: 2
        border.color: theme.moonlight
        radius: 6

        // 低置信度不播放误导性指向（方案 9.4 / 阶段 4 验收）
        opacity: overlay.targetBox && overlay.targetBox.confidence >= 0.6 ? 1.0 : 0.35

        Rectangle {
            anchors.fill: parent
            anchors.margins: -6
            color: "transparent"
            border.width: 1
            border.color: Qt.rgba(0.486, 0.612, 0.769, 0.35)
            radius: 10
        }
    }

    // ---- 标注：用户箭头（暖橙）与 AI 箭头（月光蓝）分层 ----
    Repeater {
        model: overlay.annotations

        delegate: Item {
            required property var modelData
            visible: modelData.visible !== false
            // 必须显式给出尺寸：Repeater 的 delegate Item 默认是 0x0，
            // 否则 Canvas 的 anchors.fill 会被撑成 0x0 而画不出任何内容。
            width: overlay.width
            height: overlay.height

            Canvas {
                id: arrowCanvas
                // 不使用 anchors.fill：父 Item 的尺寸依赖本画布绘制，
                // 显式绑定窗口尺寸更直接，也避免锚定循环。
                x: 0
                y: 0
                width: overlay.width
                height: overlay.height

                Component.onCompleted: requestPaint()
                onWidthChanged: requestPaint()
                onHeightChanged: requestPaint()

                Connections {
                    target: overlay
                    function onAnnotationsChanged() { arrowCanvas.requestPaint() }
                }

                onPaint: {
                    var ctx = getContext("2d")
                    ctx.reset()
                    var a = modelData
                    if (!a || !a.start || !a.end) {
                        return
                    }
                    var x1 = overlay.px(a.start[0]), y1 = overlay.py(a.start[1])
                    var x2 = overlay.px(a.end[0]), y2 = overlay.py(a.end[1])

                    var isUser = a.owner === "user"
                    var stroke = isUser ? theme.userMark : theme.moonlight
                    ctx.strokeStyle = stroke
                    ctx.fillStyle = stroke
                    ctx.lineWidth = isUser ? 3 : 2.5
                    ctx.lineCap = "round"

                    if (a.style === "rectangle") {
                        ctx.strokeRect(x1, y1, x2 - x1, y2 - y1)
                        return
                    }
                    if (a.style === "highlight") {
                        ctx.lineWidth = 6
                        ctx.globalAlpha = 0.35
                        ctx.beginPath()
                        ctx.moveTo(x1, y1)
                        ctx.lineTo(x2, y2)
                        ctx.stroke()
                        ctx.globalAlpha = 1.0
                        return
                    }

                    ctx.beginPath()
                    ctx.moveTo(x1, y1)
                    ctx.lineTo(x2, y2)
                    ctx.stroke()

                    // 箭头头部
                    var angle = Math.atan2(y2 - y1, x2 - x1)
                    var head = isUser ? 13 : 11
                    ctx.beginPath()
                    ctx.moveTo(x2, y2)
                    ctx.lineTo(x2 - head * Math.cos(angle - Math.PI / 7),
                               y2 - head * Math.sin(angle - Math.PI / 7))
                    ctx.lineTo(x2 - head * Math.cos(angle + Math.PI / 7),
                               y2 - head * Math.sin(angle + Math.PI / 7))
                    ctx.closePath()
                    ctx.fill()
                }
            }
        }
    }

    // ---- 虚拟鼠标 + 点击波纹（绝不移动真实系统鼠标） ----
    Item {
        id: pseudoCursor
        visible: overlay.virtualCursor !== null
        x: overlay.virtualCursor ? overlay.px(overlay.virtualCursor.x) - 9 : 0
        y: overlay.virtualCursor ? overlay.py(overlay.virtualCursor.y) - 9 : 0
        width: 18
        height: 18
        opacity: overlay.virtualCursor ? (overlay.virtualCursor.opacity !== undefined ? overlay.virtualCursor.opacity : 1.0) : 1.0

        Behavior on x {
            enabled: !overlay.reduceMotion
            NumberAnimation { duration: 700; easing.type: Easing.Bezier; easing.bezierCurve: theme.springCurve }
        }
        Behavior on y {
            enabled: !overlay.reduceMotion
            NumberAnimation { duration: 700; easing.type: Easing.Bezier; easing.bezierCurve: theme.springCurve }
        }

        Canvas {
            anchors.fill: parent
            Component.onCompleted: requestPaint()
            onPaint: {
                var ctx = getContext("2d")
                ctx.reset()
                ctx.fillStyle = "#F5F7FF"
                ctx.strokeStyle = "#060A13"
                ctx.lineWidth = 1.5
                ctx.beginPath()
                ctx.arc(9, 9, 6, 0, Math.PI * 2)
                ctx.fill()
                ctx.stroke()
            }
        }

        // 点击波纹：颜色按动作区分，不产生真实点击
        Rectangle {
            id: ripple
            anchors.centerIn: parent
            width: 8
            height: 8
            radius: 4
            color: "transparent"
            border.width: 2
            border.color: overlay.guideAction === "right_click" ? theme.champagne : theme.moonlight
            opacity: 0

            SequentialAnimation {
                running: overlay.virtualCursor !== null
                         && overlay.virtualCursor.ripple === true
                         && !overlay.reduceMotion
                loops: Animation.Infinite
                NumberAnimation { target: ripple; property: "width"; from: 8; to: 44; duration: 620 }
                NumberAnimation { target: ripple; property: "height"; from: 8; to: 44; duration: 620 }
                NumberAnimation { target: ripple; property: "opacity"; from: 0.9; to: 0.0; duration: 620 }
            }
        }
    }
}
