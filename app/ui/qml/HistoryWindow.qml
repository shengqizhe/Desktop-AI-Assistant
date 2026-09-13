pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Window
import QtQuick.Controls
import QtQuick.Layouts

// ⑤ 历史窗口：非模态，失焦不关闭，必须明确点击 × 才关闭（方案 4.4.3）。
Window {
    id: history

    property var sessions: []        // [{ id, app, question, updatedAt, completed }]
    property string currentId: ""
    property var currentMessages: [] // [{ role, kind, text, createdAt }]

    signal sessionChosen(string id)
    signal messageRevealed(string text)
    signal closed()

    width: theme.historyWidth
    height: theme.historyHeight
    color: "transparent"
    flags: Qt.FramelessWindowHint | Qt.Window
    title: "Desktop AI Coach · 历史"

    Theme { id: theme }

    Rectangle {
        anchors.fill: parent
        radius: theme.radius
        color: theme.glassSurfaceStrong
        border.width: 1
        border.color: theme.glassBorder

        Rectangle {
            anchors.top: parent.top
            anchors.left: parent.left
            anchors.right: parent.right
            height: 1
            color: theme.glassHighlight
        }

        ColumnLayout {
            anchors.fill: parent
            anchors.margins: 12
            spacing: 10

            RowLayout {
                Layout.fillWidth: true

                Text {
                    text: "历史会话"
                    color: theme.textPrimary
                    font.family: theme.fontFamily
                    font.pixelSize: 14
                    font.weight: Font.DemiBold
                    Layout.fillWidth: true
                }

                Item {
                    implicitWidth: 24
                    implicitHeight: 24

                    Text {
                        anchors.centerIn: parent
                        text: "×"
                        color: theme.textMuted
                        font.pixelSize: 16
                    }

                    MouseArea {
                        anchors.fill: parent
                        cursorShape: Qt.PointingHandCursor
                        onClicked: {
                            history.closed()
                            history.close()
                        }
                    }
                }
            }

            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: 1
                color: theme.glassBorder
            }

            // 会话列表
            ListView {
                id: sessionList
                Layout.fillWidth: true
                Layout.preferredHeight: 160
                clip: true
                spacing: 4
                model: history.sessions

                delegate: Rectangle {
                    required property var modelData
                    width: sessionList.width
                    height: 46
                    radius: theme.radiusSmall
                    color: modelData.id === history.currentId
                           ? Qt.rgba(0.486, 0.612, 0.769, 0.22)
                           : (itemHover.containsMouse ? Qt.rgba(1, 1, 1, 0.08) : "transparent")

                    ColumnLayout {
                        anchors.fill: parent
                        anchors.leftMargin: 10
                        anchors.rightMargin: 10
                        anchors.topMargin: 6
                        anchors.bottomMargin: 6
                        spacing: 2

                        Text {
                            text: (modelData.app ? modelData.app + " · " : "") + modelData.question
                            color: theme.textPrimary
                            font.family: theme.fontFamily
                            font.pixelSize: 12
                            elide: Text.ElideRight
                            Layout.fillWidth: true
                        }
                        Text {
                            text: modelData.updatedAt + (modelData.completed ? "  · 已完成" : "")
                            color: theme.textMuted
                            font.family: theme.fontFamily
                            font.pixelSize: 11
                            Layout.fillWidth: true
                        }
                    }

                    MouseArea {
                        id: itemHover
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: history.sessionChosen(modelData.id)
                    }
                }
            }

            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: 1
                color: theme.glassBorder
            }

            Text {
                text: "会话详情"
                color: theme.textMuted
                font.family: theme.fontFamily
                font.pixelSize: 11
            }

            // 会话详情：可把某条消息重新投到字幕轨，不复制成新消息
            ListView {
                id: messageList
                Layout.fillWidth: true
                Layout.fillHeight: true
                clip: true
                spacing: 6
                model: history.currentMessages

                delegate: ColumnLayout {
                    required property var modelData
                    width: messageList.width
                    spacing: 2

                    Text {
                        text: (modelData.role === "user" ? "你 · " : "AI · ") + modelData.text
                        color: modelData.role === "user" ? theme.textSecondary : theme.textPrimary
                        font.family: theme.fontFamily
                        font.pixelSize: 12
                        wrapMode: Text.WordWrap
                        Layout.fillWidth: true
                    }

                    Text {
                        visible: modelData.role !== "user"
                        text: "显示在屏幕"
                        color: theme.moonlight
                        font.family: theme.fontFamily
                        font.pixelSize: 11

                        MouseArea {
                            anchors.fill: parent
                            anchors.margins: -4
                            cursorShape: Qt.PointingHandCursor
                            onClicked: history.messageRevealed(modelData.text)
                        }
                    }
                }
            }

            Text {
                visible: history.currentMessages.length === 0
                text: "选择上方会话查看详情"
                color: theme.textMuted
                font.family: theme.fontFamily
                font.pixelSize: 12
            }
        }
    }
}
