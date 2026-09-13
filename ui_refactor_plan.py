"""
皮皮桌面助手 - 界面重构实现说明
================================

## 核心改动概览

### 1. 新增气泡式历史消息组件 (HistoryBubbleWidget)
文件位置：在 desktop_pet_fluent.py 中新增类

### 2. ChatPage布局重构
- 默认：左侧主区显示气泡式历史对话，隐藏右侧面板
- 切换：点击历史按钮切换布局模式

### 3. 布局模式存储
设置键：chat_layout_mode
值："left" (历史在左，默认) 或 "right" (历史在右)

## 具体实现步骤：

### 步骤1：新增气泡消息组件（在HistoryItemWidget之前插入）

```python
class HistoryBubbleWidget(QWidget):
    '''气泡式历史消息组件'''
    delete_requested = pyqtSignal(int)
    load_requested = pyqtSignal(int)
    
    def __init__(self, conv_id: int, text: str, is_user: bool, created_at: str, parent=None):
        super().__init__(parent)
        self.conv_id = conv_id
        self.is_user = is_user
        self.setMaximumWidth(600)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 6, 12, 6)
        
        # 时间戳
        time_str = str(created_at or "")[11:16] if created_at else ""
        self.timeLabel = QLabel(time_str)
        self.timeLabel.setFont(QFont("Microsoft YaHei", 8))
        
        # 气泡内容
        self.contentLabel = QLabel(str(text or ""))
        self.contentLabel.setFont(QFont("Microsoft YaHei", 10))
        self.contentLabel.setWordWrap(True)
        self.contentLabel.setMaximumWidth(400)
        self.contentLabel.setMinimumWidth(60)
        self.contentLabel.setTextInteractionFlags(Qt.TextSelectableByMouse)
        
        is_dark = db.get_setting("dark_mode", "False") == "True"
        self._update_style(is_dark)
        
        # 布局：用户消息右对齐，AI消息左对齐
        if is_user:
            layout.addStretch(1)
            layout.addWidget(self.contentLabel)
            layout.addSpacing(8)
            layout.addWidget(self.timeLabel, 0, Qt.AlignBottom)
        else:
            layout.addWidget(self.timeLabel, 0, Qt.AlignBottom)
            layout.addSpacing(8)
            layout.addWidget(self.contentLabel)
            layout.addStretch(1)
    
    def _update_style(self, is_dark: bool):
        '''更新样式'''
        if self.is_user:
            # 用户消息：右侧浅蓝
            if is_dark:
                bubble_style = '''
                    QLabel {
                        background: rgba(64,158,255,0.85);
                        color: white;
                        border-radius: 12px;
                        padding: 8px 12px;
                        border-top-right-radius: 4px;
                    }
                '''
                time_style = "color: rgba(180,180,180,180);"
            else:
                bubble_style = '''
                    QLabel {
                        background: rgba(64,158,255,0.75);
                        color: white;
                        border-radius: 12px;
                        padding: 8px 12px;
                        border-top-right-radius: 4px;
                    }
                '''
                time_style = "color: rgba(120,120,120,180);"
        else:
            # AI消息：左侧浅灰
            if is_dark:
                bubble_style = '''
                    QLabel {
                        background: rgba(255,255,255,0.15);
                        color: white;
                        border-radius: 12px;
                        padding: 8px 12px;
                        border-top-left-radius: 4px;
                    }
                '''
                time_style = "color: rgba(180,180,180,180);"
            else:
                bubble_style = '''
                    QLabel {
                        background: rgba(240,240,240,0.85);
                        color: #333;
                        border-radius: 12px;
                        padding: 8px 12px;
                        border-top-left-radius: 4px;
                    }
                '''
                time_style = "color: rgba(120,120,120,180);"
        
        self.contentLabel.setStyleSheet(bubble_style)
        self.timeLabel.setStyleSheet(f"background: transparent; {time_style}")
    
    def update_theme(self, is_dark: bool):
        self._update_style(is_dark)
    
    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self.load_requested.emit(self.conv_id)
        super().mousePressEvent(e)
```

### 步骤2：修改ChatPage类

在__init__方法中修改布局：

```python
def __init__(self, parent=None):
    super().__init__(parent)
    self.setObjectName("ChatPage")
    self.layout = QVBoxLayout(self)
    
    # 读取布局模式
    self.layout_mode = db.get_setting("chat_layout_mode", "left")
    
    # 顶部工具栏（保持不变）
    self.statusLayout = QHBoxLayout()
    # ... 原有代码 ...
    
    # 修改：历史按钮现在用于切换布局
    self.historyBtn.setToolTip("切换历史对话布局")
    self.historyBtn.setCheckable(True)
    self.historyBtn.setChecked(self.layout_mode == "right")
    
    # 主内容区布局（改为可切换）
    self.contentLayout = QHBoxLayout()
    self.contentLayout.setContentsMargins(0, 0, 0, 0)
    self.contentLayout.setSpacing(0)
    
    # 左侧区域：根据模式显示不同内容
    self.leftWidget = QFrame()
    self.leftLayout = QVBoxLayout(self.leftWidget)
    self.leftLayout.setContentsMargins(0, 0, 0, 0)
    
    # 创建滚动区域（用于显示对话）
    self.scrollArea = ScrollArea()
    self.scrollWidget = QWidget()
    self.scrollLayout = QVBoxLayout(self.scrollWidget)
    self.scrollLayout.setAlignment(Qt.AlignTop)
    self.scrollLayout.setSpacing(4)
    self.scrollArea.setWidget(self.scrollWidget)
    self.scrollArea.setWidgetResizable(True)
    
    # 隐藏默认滚动条，使用自定义样式
    self.scrollArea.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
    self.scrollArea.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
    
    self.leftLayout.addWidget(self.scrollArea)
    
    # 右侧历史面板
    self.historyPanel = HistoryPanel(self)
    
    # 根据布局模式设置显示
    self._apply_layout_mode()
    
    self.contentLayout.addWidget(self.leftWidget, 1)
    self.contentLayout.addWidget(self.historyPanel)
    
    self.layout.addLayout(self.contentLayout)
    
    # 输入区域（保持不变）
    # ... 原有输入框代码 ...

def _apply_layout_mode(self):
    '''应用布局模式'''
    if self.layout_mode == "left":
        # 默认：左侧显示历史，右侧隐藏
        self.historyPanel.hide()
        self._load_history_to_left()
    else:
        # 右侧布局：左侧显示背景+交互，右侧显示历史
        self.historyPanel.show()
        self._clear_left_history()

def _load_history_to_left(self):
    '''加载历史对话到左侧区域'''
    # 清空现有内容
    self._clear_left_history()
    
    # 从数据库加载历史
    try:
        pairs = db.get_chat_pairs(limit=50, offset=0)
        # 反转顺序（最新的在底部）
        pairs = list(reversed(pairs))
        
        for user_text, ai_text, created_at, user_type, _ in pairs:
            # 添加用户消息
            if user_text:
                self._add_history_bubble(user_text, True, created_at)
            # 添加AI回复
            if ai_text:
                self._add_history_bubble(ai_text, False, created_at)
    except Exception as e:
        print(f"[ChatPage] 加载历史失败: {e}")

def _add_history_bubble(self, text: str, is_user: bool, created_at: str):
    '''添加历史气泡'''
    # 使用现有ChatMessageWidget或创建新的
    msg = ChatMessageWidget(text, is_user)
    self.scrollLayout.addWidget(msg, 0, Qt.AlignRight if is_user else Qt.AlignLeft)

def _clear_left_history(self):
    '''清空左侧历史显示'''
    # 保留欢迎界面或其他内容
    while self.scrollLayout.count():
        item = self.scrollLayout.takeAt(0)
        if item.widget():
            item.widget().deleteLater()

def toggle_layout_mode(self):
    '''切换布局模式'''
    self.layout_mode = "right" if self.layout_mode == "left" else "left"
    db.set_setting("chat_layout_mode", self.layout_mode)
    
    # 添加过渡动画
    self._animate_layout_change()
    
    self._apply_layout_mode()
    self.historyBtn.setChecked(self.layout_mode == "right")

def _animate_layout_change(self):
    '''布局切换动画'''
    from PyQt5.QtCore import QPropertyAnimation, QRect
    
    # 创建淡出效果
    self.animation = QPropertyAnimation(self.leftWidget, b"geometry")
    self.animation.setDuration(200)
    
    current_geo = self.leftWidget.geometry()
    if self.layout_mode == "right":
        # 切换到右侧面板模式
        self.animation.setStartValue(current_geo)
        self.animation.setEndValue(current_geo)
    else:
        # 切换到左侧历史模式
        self.animation.setStartValue(current_geo)
        self.animation.setEndValue(current_geo)
    
    self.animation.start()
```

### 步骤3：修改MainWindow中的连接

找到open_history_panel方法并修改：

```python
def open_history_panel(self):
    '''切换历史对话布局模式'''
    self.chatPage.toggle_layout_mode()
```

### 步骤4：添加样式表

在ChatPage的__init__末尾添加：

```python
# 应用样式
self._apply_chat_styles()

def _apply_chat_styles(self):
    '''应用聊天区域样式'''
    is_dark = db.get_setting("dark_mode", "False") == "True"
    
    if is_dark:
        scroll_style = """
            QScrollArea {
                background: transparent;
                border: none;
            }
            QScrollBar:vertical {
                background: transparent;
                width: 6px;
                margin: 0px;
            }
            QScrollBar::handle:vertical {
                background: rgba(255,255,255,40);
                border-radius: 3px;
                min-height: 30px;
            }
            QScrollBar::handle:vertical:hover {
                background: rgba(255,255,255,60);
            }
        """
    else:
        scroll_style = """
            QScrollArea {
                background: transparent;
                border: none;
            }
            QScrollBar:vertical {
                background: transparent;
                width: 6px;
                margin: 0px;
            }
            QScrollBar::handle:vertical {
                background: rgba(0,0,0,20);
                border-radius: 3px;
                min-height: 30px;
            }
            QScrollBar::handle:vertical:hover {
                background: rgba(0,0,0,35);
            }
        """
    
    self.scrollArea.setStyleSheet(scroll_style)
```

### 步骤5：修改发送消息逻辑

在handle_send方法中，发送后添加到历史显示：

```python
def handle_send(self, text=None):
    # ... 原有代码 ...
    
    # 如果当前是左侧历史模式，添加到显示
    if self.layout_mode == "left":
        # 添加用户消息
        self._add_history_bubble(text, True, datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    
    # ... 发送逻辑 ...

def on_ai_response(self, full_text, action_json):
    # ... 原有代码 ...
    
    # 如果当前是左侧历史模式，添加AI回复到显示
    if self.layout_mode == "left":
        self._add_history_bubble(reply, False, datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
```

## 注意事项

1. 背景图保持：确保壁纸透明度设置正确（当前为0.55）
2. 性能考虑：历史记录过多时可能需要分页加载
3. 主题切换：记得在主题切换时更新气泡样式
4. 数据库：聊天记录表需要包含user_type字段用于区分消息类型

## 需要修改的文件位置

主要修改 desktop_pet_fluent.py：
- 约第1995行后插入 HistoryBubbleWidget 类
- 约第3066行开始修改 ChatPage 类
- 约第4653行的 open_history_panel 方法
- 添加新的样式应用方法

如需我实际执行这些修改，请告知，我会逐步完成具体代码编辑。
"""
