pragma ComponentBehavior: Bound
import QtQuick

// 设计令牌（方案 4.1.1）。所有 QML 组件从这里取色，禁止硬编码。
QtObject {
    id: theme

    // 内层底色与展开面板背景
    readonly property color ink900: "#060A13"
    readonly property color ink800: "#0B1322"

    // 玻璃材质
    readonly property color glassSurface: Qt.rgba(0.043, 0.075, 0.133, 0.72)
    readonly property color glassSurfaceStrong: Qt.rgba(0.043, 0.075, 0.133, 0.85)
    readonly property color glassBorder: Qt.rgba(0.608, 0.722, 0.847, 0.30)
    readonly property color glassHighlight: Qt.rgba(1, 1, 1, 0.32)
    readonly property color glassShade: Qt.rgba(0.008, 0.024, 0.063, 0.30)

    // 语义色
    readonly property color moonlight: "#7C9CC4"
    readonly property color champagne: "#E4B863"
    readonly property color userMark: "#E6A46A"
    readonly property color danger: "#D98282"
    readonly property color textPrimary: "#F5F7FF"
    readonly property color textSecondary: "#DCE9FF"
    readonly property color textMuted: "#9FB2CC"

    // 尺寸
    readonly property int islandCollapsedWidth: 380
    readonly property int islandCollapsedHeight: 52
    readonly property int islandExpandedWidth: 520
    readonly property int islandExpandedHeight: 320
    readonly property int captionMaxWidth: 360
    readonly property int captionRailHeight: 200
    readonly property int historyWidth: 440
    readonly property int historyHeight: 560
    readonly property int radius: 18
    readonly property int radiusSmall: 12

    // 动效：统一 spring easing，禁止 bounce/elastic 过冲
    readonly property int springDuration: 450
    readonly property var springCurve: [0.16, 1.0, 0.3, 1.0]

    readonly property string fontFamily: "Microsoft YaHei UI"

    // 状态 -> 视觉（方案 4.2.1）。状态不能只靠颜色，需配合文字。
    function stateColor(state) {
        switch (state) {
        case "arrow_placement":
        case "guiding":
        case "completed":
            return theme.champagne
        case "privacy_paused":
        case "error":
            return theme.danger
        default:
            return theme.moonlight
        }
    }

    function stateLabel(state) {
        switch (state) {
        case "idle": return "就绪"
        case "monitoring": return "本地缓存"
        case "arrow_placement": return "放置箭头"
        case "analyzing": return "正在理解"
        case "guiding": return "指导中"
        case "waiting_for_user": return "等待你操作"
        case "privacy_paused": return "已暂停"
        case "completed": return "已完成"
        case "error": return "出错了"
        default: return "就绪"
        }
    }
}
