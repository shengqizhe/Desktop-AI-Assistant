"""
音乐模式功能模块 - PyAudio + 立体声混音版
包含：透明悬浮窗、音乐波浪特效、音频监控（PyAudio）、悬浮球光晕动画
"""
import sys
import os
import time
import math
import threading
import numpy as np
from PyQt5.QtWidgets import (QWidget, QLabel, QVBoxLayout, QHBoxLayout,
                             QApplication, QPushButton, QFrame, QSlider,
                             QGraphicsDropShadowEffect, QSystemTrayIcon, QMenu,
                             QAction, QGraphicsView, QGraphicsScene,
                             QGraphicsEllipseItem, QGraphicsItem, QSizePolicy,
                             QDialog)
from PyQt5.QtCore import (Qt, QTimer, pyqtSignal, QObject, QPoint, QRectF,
                          QPropertyAnimation, QEasingCurve, pyqtProperty, QSize,
                          QRect, QThread)
from PyQt5.QtGui import (QColor, QPainter, QPen, QBrush, QPixmap, QIcon,
                         QRadialGradient, QLinearGradient, QFont, QCursor,
                         QPainterPath)
from PyQt5.QtGui import QMovie


# ============ iOS 风格开关控件 ============
class IOSToggleSwitch(QWidget):
    """仿 iOS 风格的开关控件"""
    toggled = pyqtSignal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._checked = False
        self._thumb_x = 3.0
        self._target_x = 3.0
        self.setFixedSize(52, 30)
        self.setCursor(Qt.PointingHandCursor)
        self._anim_timer = QTimer(self)
        self._anim_timer.setInterval(12)
        self._anim_timer.timeout.connect(self._tick_anim)

    def isChecked(self):
        return self._checked

    def setChecked(self, val: bool):
        if val == self._checked:
            return
        self._checked = val
        self._target_x = 25.0 if val else 3.0
        self._anim_timer.start()
        self.toggled.emit(val)

    def _tick_anim(self):
        diff = self._target_x - self._thumb_x
        if abs(diff) < 0.5:
            self._thumb_x = self._target_x
            self._anim_timer.stop()
        else:
            self._thumb_x += diff * 0.25
        self.update()

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self.setChecked(not self._checked)

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        half_h = h / 2

        # 轨道颜色（绿色 ON / 灰色 OFF，平滑过渡）
        t = max(0.0, min(1.0, (self._thumb_x - 3.0) / 22.0))
        on_r, on_g, on_b   = 0x4C, 0xD9, 0x64
        off_r, off_g, off_b = 0xE5, 0xE5, 0xEA
        tr = int(off_r + (on_r - off_r) * t)
        tg = int(off_g + (on_g - off_g) * t)
        tb = int(off_b + (on_b - off_b) * t)
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(QColor(tr, tg, tb)))
        p.drawRoundedRect(0, 0, w, h, half_h, half_h)

        # 白色滑块
        thumb_d = h - 6
        p.setBrush(QBrush(QColor("white")))
        p.setPen(QPen(QColor(0, 0, 0, 30), 1))
        p.drawEllipse(int(self._thumb_x), 3, thumb_d, thumb_d)
        p.end()


# ============ PyAudio 音频监控类 ============
class AudioMonitorThread(QThread):
    """
    PyAudio + 立体声混音 音频监控线程
    后台持续监测系统音频输出音量
    """
    volume_changed = pyqtSignal(float)  # 音量变化信号 (0.0 - 1.0)
    music_status_changed = pyqtSignal(bool)  # 音乐播放状态变化
    error_occurred = pyqtSignal(str)  # 错误信号

    def __init__(self, check_enabled_callback=None, parent=None):
        """
        参数:
            check_enabled_callback: 回调函数，返回音乐模式是否开启
        """
        super().__init__(parent)
        self._check_enabled_callback = check_enabled_callback
        self._is_running = False
        self._pyaudio_available = False
        self._stream = None
        self._pa = None
        self._device_index = None
        self._last_volume = 0.0
        self._music_playing = False
        self._lock = threading.Lock()
        
        # 音频参数
        self.CHUNK = 1024  # 每次读取的采样点数
        self.FORMAT = None  # 将在初始化时设置
        self.CHANNELS = 2  # 立体声
        self.RATE = 44100  # 采样率
        
        # 尝试初始化 PyAudio
        self._init_pyaudio()

    def _init_pyaudio(self):
        """初始化 PyAudio 并查找立体声混音设备"""
        try:
            import pyaudio
            self._pa = pyaudio.PyAudio()
            self.FORMAT = pyaudio.paInt16
            
            # 查找立体声混音设备
            self._device_index = self._find_stereo_mix_device()
            
            if self._device_index is not None:
                self._pyaudio_available = True
                print(f"[AudioMonitor] 找到立体声混音设备，索引: {self._device_index}")
            else:
                print("[AudioMonitor] 警告：未找到立体声混音设备，音频监控不可用")
                print("[AudioMonitor] 请在 Windows 声音设置中启用'立体声混音'")
                
        except ImportError:
            print("[AudioMonitor] 错误：未安装 PyAudio，请运行: pip install pyaudio")
        except Exception as e:
            print(f"[AudioMonitor] 初始化失败: {e}")

    def _find_stereo_mix_device(self):
        """查找立体声混音（Stereo Mix）设备索引"""
        if not self._pa:
            return None
            
        # 尝试多种可能的设备名称
        stereo_mix_names = [
            "立体声混音",
            "Stereo Mix",
            "What U Hear",
            "Waveout Mix",
            "Mixed Output",
            "虚拟",
            "Virtual"
        ]
        
        for i in range(self._pa.get_device_count()):
            try:
                info = self._pa.get_device_info_by_index(i)
                name = str(info.get('name', '')).lower()
                max_channels = int(info.get('maxInputChannels', 0) or 0)
                
                # 检查是否是输入设备（maxInputChannels > 0）且名称匹配
                if max_channels > 0:
                    for mix_name in stereo_mix_names:
                        if mix_name.lower() in name:
                            print(f"[AudioMonitor] 找到设备: {info.get('name')} (索引: {i})")
                            return i
            except Exception:
                continue
        
        # 如果没找到立体声混音，尝试使用默认输入设备（可能不准确）
        try:
            default_input = self._pa.get_default_input_device_info()
            print(f"[AudioMonitor] 使用默认输入设备: {default_input.get('name')}")
            return default_input.get('index')
        except:
            pass
            
        return None

    def _calculate_volume(self, data):
        """计算音频数据的音量（RMS 均方根）"""
        try:
            # 将字节数据转换为 numpy 数组
            audio_data = np.frombuffer(data, dtype=np.int16)
            
            if len(audio_data) == 0:
                return 0.0
            
            # 计算 RMS (Root Mean Square)
            rms = np.sqrt(np.mean(audio_data.astype(np.float32) ** 2))
            
            # 转换为 0-1 范围（16位音频最大值为 32768）
            volume = min(rms / 32768.0, 1.0)
            
            return volume
        except Exception as e:
            print(f"[AudioMonitor] 音量计算错误: {e}")
            return 0.0

    def run(self):
        """后台线程主循环"""
        if not self._pyaudio_available or self._device_index is None:
            print("[AudioMonitor] 音频监控未启动：设备不可用")
            self.error_occurred.emit("立体声混音设备未找到")
            return

        try:
            import pyaudio
            
            if self._pa is None or self.FORMAT is None:
                print("[AudioMonitor] 错误：PyAudio 未正确初始化")
                return
            
            # 打开音频流
            self._stream = self._pa.open(
                format=int(self.FORMAT),
                channels=int(self.CHANNELS),
                rate=int(self.RATE),
                input=True,
                input_device_index=int(self._device_index),
                frames_per_buffer=int(self.CHUNK)
            )
            
            self._is_running = True
            print("[AudioMonitor] 音频监控线程已启动")
            
            # 主循环
            while self._is_running:
                try:
                    # 检查音乐模式是否开启
                    is_enabled = False
                    if self._check_enabled_callback:
                        try:
                            is_enabled = self._check_enabled_callback()
                        except:
                            is_enabled = False
                    
                    # 如果音乐模式未开启，跳过读取以节省 CPU
                    if not is_enabled:
                        time.sleep(0.1)  # 降低检查频率
                        if self._music_playing:
                            self._music_playing = False
                            self.music_status_changed.emit(False)
                        continue
                    
                    # 读取音频数据
                    data = self._stream.read(self.CHUNK, exception_on_overflow=False)
                    
                    # 计算音量
                    volume = self._calculate_volume(data)
                    
                    # 平滑处理（减少抖动）
                    smoothed_volume = float(volume * 0.3 + self._last_volume * 0.7)
                    self._last_volume = smoothed_volume
                    
                    # 发射音量信号
                    self.volume_changed.emit(smoothed_volume)
                    
                    # 检测音乐播放状态（简单阈值：>0 为有声音）
                    is_playing = bool(smoothed_volume > 0.001)  # 只要有声音就认为是播放
                    
                    if is_playing != self._music_playing:
                        self._music_playing = is_playing
                        self.music_status_changed.emit(is_playing)
                        # 控制台输出监测信息
                        if is_playing:
                            print(f"[Music] 监测到音频输出(音量:{smoothed_volume:.4f})，开始播放动画")
                        else:
                            print(f"[Music] 音频停止(音量:{smoothed_volume:.4f})，停止播放动画")
                        
                except Exception as e:
                    if self._is_running:
                        print(f"[AudioMonitor] 读取音频数据错误: {e}")
                        # 出错时确保状态重置为 False
                        if self._music_playing:
                            self._music_playing = False
                            self.music_status_changed.emit(False)
                        time.sleep(0.1)
                    
        except Exception as e:
            print(f"[AudioMonitor] 线程运行错误: {e}")
            self.error_occurred.emit(str(e))
        finally:
            self._cleanup()

    def _cleanup(self):
        """清理资源"""
        try:
            if self._stream:
                self._stream.stop_stream()
                self._stream.close()
                self._stream = None
        except:
            pass
        print("[AudioMonitor] 音频监控线程已停止")

    def stop(self):
        """停止音频监控线程"""
        self._is_running = False
        self._cleanup()
        
        # 发送停止状态
        self.volume_changed.emit(0.0)
        self.music_status_changed.emit(False)
        
        # 等待线程结束
        if not self.wait(2000):  # 等待最多2秒
            print("[AudioMonitor] 警告：线程未能正常结束")
            self.terminate()  # 强制终止

    def is_available(self):
        """检查音频监控是否可用"""
        return self._pyaudio_available and self._device_index is not None


# ============ 音乐模式 GIF 动画覆盖层 ============
class MusicAuraOverlay(QWidget):
    """
    音乐模式动画覆盖层 - 作为悬浮球子控件显示，和悬浮球同生共死
    """

    def __init__(self, ball_widget=None, parent=None):
        host = ball_widget if ball_widget is not None else parent
        super().__init__(host)
        self._ball = ball_widget
        self._ball_visible = bool(ball_widget is not None and ball_widget.isVisible())
        self._size = 150

        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.setFixedSize(self._size, self._size)
        self.hide()

        # 创建布局
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 创建 QLabel 显示 GIF
        self._label = QLabel(self)
        self._label.setAlignment(Qt.AlignCenter)
        self._label.setFixedSize(self._size, self._size)
        layout.addWidget(self._label)

        # 加载 GIF 动画
        gif_path = os.path.join(os.path.dirname(__file__), "public", "music.gif")
        if os.path.exists(gif_path):
            self._movie = QMovie(gif_path)
            self._movie.setScaledSize(QSize(self._size, self._size))
            self._label.setMovie(self._movie)
            print(f"[MusicAura] GIF 加载成功: {gif_path}")
        else:
            print(f"[MusicAura] 警告: 找不到 GIF 文件: {gif_path}")
            self._movie = None

        self._follow_ball()

    # ---- 公开接口 ----
    def set_ball_visible(self, visible: bool):
        self._ball_visible = bool(visible)
        if self._ball is not None:
            self._follow_ball()
        if not self._ball_visible:
            self.stop()

    def start(self):
        """启动动画 - 跟随悬浮球显示"""
        print("[MusicAura] 开始启动动画...")
        if not self._ball_visible:
            print("[MusicAura] 悬浮球不可见，跳过启动动画")
            self.stop()
            return
        self._follow_ball()
        if self.parentWidget() is not None:
            self.raise_()
        self.show()
        
        if self._movie:
            self._movie.start()
            print(f"[MusicAura] GIF 动画已启动，窗口可见性: {self.isVisible()}")
        else:
            print("[MusicAura] 错误: GIF 未加载，无法启动动画")

    def stop(self):
        """停止动画"""
        print("[MusicAura] 停止动画...")
        if self._movie:
            self._movie.stop()
        self.hide()
        print(f"[MusicAura] GIF 动画已停止，窗口可见性: {self.isVisible()}")

    def follow_ball(self):
        """外部调用：更新位置"""
        self._follow_ball()

    # ---- 内部 ----
    def _follow_ball(self):
        """将动画覆盖到悬浮球中心区域"""
        try:
            if self._ball is None:
                return
            x = int((self._ball.width() - self._size) / 2)
            y = int((self._ball.height() - self._size) / 2)
            self.setGeometry(x, y, self._size, self._size)
            self._label.setFixedSize(self._size, self._size)
            if self._movie:
                self._movie.setScaledSize(QSize(self._size, self._size))
        except Exception as e:
            print(f"[MusicAura] 绑定悬浮球失败: {e}")

# ============ 波浪环效果项 ============
class WaveRingItem(QGraphicsEllipseItem):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._radius = 50
        self._opacity = 1.0
        self._width = 2
        self.setPen(QPen(QColor(100, 200, 255, int(255 * self._opacity)), self._width))
        self.setBrush(QBrush(Qt.NoBrush))
        self.setZValue(-1)

    def set_radius(self, radius):
        self._radius = radius
        self._update_rect()

    def set_opacity(self, opacity):
        self._opacity = max(0.0, min(1.0, opacity))
        self.setPen(QPen(QColor(100, 200, 255, int(255 * self._opacity)), self._width))

    def set_width(self, width):
        self._width = width
        self.setPen(QPen(QColor(100, 200, 255, int(255 * self._opacity)), self._width))

    def _update_rect(self):
        rect = QRectF(-self._radius, -self._radius,
                      self._radius * 2, self._radius * 2)
        self.setRect(rect)


# ============ 音乐波浪场景 ============
class MusicWaveScene(QGraphicsScene):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSceneRect(-200, -200, 400, 400)
        self.wave_rings = []
        self.max_rings = 6
        for i in range(self.max_rings):
            ring = WaveRingItem()
            ring.set_radius(60 + i * 15)
            ring.set_opacity(1.0 - i * 0.15)
            ring.set_width(3 - i * 0.3)
            self.addItem(ring)
            self.wave_rings.append({
                'item': ring,
                'base_radius': 60 + i * 15,
                'phase': i * (3.14159 * 2 / self.max_rings)
            })
        self.cat_item = None
        self.anim_timer = QTimer()
        self.anim_timer.timeout.connect(self._update_waves)
        self.anim_time = 0
        self.current_volume = 0.0

    def start_animation(self):
        self.anim_timer.start(30)

    def stop_animation(self):
        self.anim_timer.stop()
        for ring_data in self.wave_rings:
            ring_data['item'].set_radius(ring_data['base_radius'])
            ring_data['item'].set_opacity(0)

    def set_volume(self, volume):
        self.current_volume = volume

    def _update_waves(self):
        self.anim_time += 0.1
        for i, ring_data in enumerate(self.wave_rings):
            ring = ring_data['item']
            base_r = ring_data['base_radius']
            phase = ring_data['phase']
            volume_factor = 0.2 + self.current_volume * 0.8
            wave = (time.time() * 3 + phase) % (3.14159 * 2)
            radius_offset = math.sin(wave) * 10 * volume_factor
            new_radius = base_r + radius_offset + self.current_volume * 30
            ring.set_radius(new_radius)
            opacity = (1.0 - i * 0.15) * volume_factor
            ring.set_opacity(opacity)

    def set_cat_pixmap(self, pixmap):
        if self.cat_item:
            self.removeItem(self.cat_item)
        self.cat_item = self.addPixmap(pixmap)
        self.cat_item.setOffset(-pixmap.width() / 2, -pixmap.height() / 2)
        self.cat_item.setZValue(10)


# ============ 透明悬浮窗 ============
class FloatingWindow(QWidget):
    closed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(
            Qt.FramelessWindowHint |
            Qt.WindowStaysOnTopHint |
            Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, False)
        self.setFixedSize(400, 400)
        self._drag_pos = None
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self.wave_view = QGraphicsView()
        self.wave_view.setRenderHint(QPainter.Antialiasing)
        self.wave_view.setStyleSheet("background: transparent; border: none;")
        self.wave_view.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.wave_view.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.wave_scene = MusicWaveScene()
        self.wave_view.setScene(self.wave_scene)
        layout.addWidget(self.wave_view)
        self._load_cat_image()
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)

    def _load_cat_image(self):
        cat_paths = [
            os.path.join(os.path.dirname(__file__), "app_data", "cat.png"),
            os.path.join(os.path.dirname(__file__), "resources", "cat.png"),
            os.path.join(os.path.dirname(__file__), "assets", "cat.png"),
        ]
        pixmap = None
        for path in cat_paths:
            if os.path.exists(path):
                pixmap = QPixmap(path)
                break
        if pixmap and not pixmap.isNull():
            pixmap = pixmap.scaled(100, 100, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.wave_scene.set_cat_pixmap(pixmap)
        else:
            pix = QPixmap(100, 100)
            pix.fill(Qt.transparent)
            painter = QPainter(pix)
            painter.setRenderHint(QPainter.Antialiasing)
            painter.setBrush(QBrush(QColor(255, 182, 193)))
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(0, 0, 100, 100)
            painter.setPen(QPen(QColor(255, 255, 255), 2))
            painter.setFont(QFont("Microsoft YaHei", 24))
            painter.drawText(pix.rect(), Qt.AlignCenter, "🐱")
            painter.end()
            self.wave_scene.set_cat_pixmap(pix)

    def start_wave_animation(self):
        self.wave_scene.start_animation()

    def stop_wave_animation(self):
        self.wave_scene.stop_animation()

    def set_volume(self, volume):
        self.wave_scene.set_volume(volume)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_pos = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if self._drag_pos and event.buttons() == Qt.LeftButton:
            self.move(event.globalPos() - self._drag_pos)
            event.accept()

    def mouseReleaseEvent(self, event):
        self._drag_pos = None

    def _show_context_menu(self, pos):
        menu = QMenu(self)
        close_action = QAction("关闭悬浮窗", self)
        close_action.triggered.connect(self.close)
        menu.addAction(close_action)
        menu.exec_(self.mapToGlobal(pos))

    def closeEvent(self, event):
        self.stop_wave_animation()
        self.closed.emit()
        event.accept()


# ============ 音乐模式主界面 ============
class MusicModeWidget(QFrame):
    """音乐模式主界面 - 带顶部开关"""
    aura_toggled = pyqtSignal(bool)  # 光晕开关信号

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("MusicModeWidget")
        self.floating_window = None
        self.audio_monitor = AudioMonitorThread()
        self.audio_monitor.volume_changed.connect(self._on_volume_changed)
        self.audio_monitor.music_status_changed.connect(self._on_music_status_changed)
        self.is_music_enabled = False
        self.is_floating = False
        self.is_aura_enabled = False
        self._setup_ui()

    def _setup_ui(self):
        """设置界面"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # 顶部标题栏（带开关）
        header_layout = QHBoxLayout()
        title = QLabel("🎵 音乐模式")
        title.setStyleSheet("font-size: 18px; font-weight: bold;")
        header_layout.addWidget(title)
        header_layout.addStretch()

        # 光晕开关（iOS 风格）
        aura_label = QLabel("光晕效果:")
        aura_label.setStyleSheet("font-size: 12px;")
        self.aura_switch = IOSToggleSwitch()
        self.aura_switch.toggled.connect(self._on_aura_toggled)
        header_layout.addWidget(aura_label)
        header_layout.addWidget(self.aura_switch)

        layout.addLayout(header_layout)

        # 说明文字
        desc = QLabel("开启音乐捕捉后，系统将自动检测音乐播放并显示波浪特效")
        desc.setStyleSheet("color: gray; font-size: 12px;")
        desc.setWordWrap(True)
        layout.addWidget(desc)

        # 分割线
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet("background-color: rgba(0,0,0,0.1);")
        line.setFixedHeight(1)
        layout.addWidget(line)

        # 音乐开关
        switch_layout = QHBoxLayout()
        switch_label = QLabel("音乐捕捉:")
        switch_layout.addWidget(switch_label)
        self.music_switch = QPushButton("OFF")
        self.music_switch.setFixedSize(50, 26)
        self.music_switch.setCheckable(True)
        self.music_switch.setStyleSheet("""
            QPushButton {
                background-color: #ccc;
                border: none;
                border-radius: 13px;
                color: white;
                font-weight: bold;
                font-size: 10px;
            }
            QPushButton:checked {
                background-color: #4CAF50;
            }
        """)
        self.music_switch.toggled.connect(self._on_music_switch_toggled)
        switch_layout.addWidget(self.music_switch)
        switch_layout.addStretch()
        layout.addLayout(switch_layout)

        # 悬浮窗控制区
        floating_layout = QHBoxLayout()
        floating_label = QLabel("悬浮窗模式:")
        floating_layout.addWidget(floating_label)
        self.floating_btn = QPushButton("打开悬浮窗")
        self.floating_btn.setFixedSize(100, 32)
        self.floating_btn.setStyleSheet("""
            QPushButton {
                background-color: #409eff;
                color: white;
                border: none;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #66b1ff;
            }
        """)
        self.floating_btn.clicked.connect(self._toggle_floating_window)
        floating_layout.addWidget(self.floating_btn)
        floating_layout.addStretch()
        layout.addLayout(floating_layout)

        # 状态显示
        self.status_label = QLabel("状态: 未开启音乐捕捉")
        self.status_label.setStyleSheet("color: #666; font-size: 13px;")
        layout.addWidget(self.status_label)

        # 音量显示
        self.volume_label = QLabel("音量: 0%")
        self.volume_label.setStyleSheet("color: #999; font-size: 11px;")
        layout.addWidget(self.volume_label)

        layout.addStretch()

    def _on_aura_toggled(self, checked):
        """光晕开关切换"""
        self.is_aura_enabled = checked
        self.aura_toggled.emit(checked)

    def _on_music_switch_toggled(self, checked):
        """音乐开关切换"""
        self.is_music_enabled = checked
        if checked:
            self.music_switch.setText("ON")
            self.audio_monitor.start()
            self.status_label.setText("状态: 正在监听音乐...")
            if self.floating_window and self.floating_window.isVisible():
                self.floating_window.start_wave_animation()
        else:
            self.music_switch.setText("OFF")
            self.audio_monitor.stop()
            self.status_label.setText("状态: 音乐捕捉已关闭")
            self.volume_label.setText("音量: 0%")
            if self.floating_window:
                self.floating_window.stop_wave_animation()

    def _on_volume_changed(self, volume):
        """音量变化回调"""
        self.volume_label.setText(f"音量: {int(volume * 100)}%")
        if self.floating_window and self.floating_window.isVisible():
            self.floating_window.set_volume(volume)

    def _on_music_status_changed(self, is_playing):
        """音乐状态变化"""
        if is_playing:
            self.status_label.setText("状态: 检测到音乐播放 🎶")
        else:
            self.status_label.setText("状态: 等待音乐播放...")

    def _toggle_floating_window(self):
        """切换悬浮窗显示"""
        if self.floating_window and self.floating_window.isVisible():
            self.floating_window.close()
            self.floating_window = None
            self.floating_btn.setText("打开悬浮窗")
            self.is_floating = False
        else:
            self.floating_window = FloatingWindow()
            self.floating_window.closed.connect(self._on_floating_closed)
            screen = QApplication.primaryScreen().geometry()
            self.floating_window.move(
                screen.width() - 420,
                screen.height() - 450
            )
            self.floating_window.show()
            self.floating_btn.setText("关闭悬浮窗")
            self.is_floating = True
            if self.is_music_enabled:
                self.floating_window.start_wave_animation()

    def _on_floating_closed(self):
        """悬浮窗关闭回调"""
        self.floating_window = None
        self.floating_btn.setText("打开悬浮窗")
        self.is_floating = False

    def closeEvent(self, event):
        """关闭时清理"""
        if self.floating_window:
            self.floating_window.close()
        self.audio_monitor.stop()
        event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MusicModeWidget()
    window.setWindowTitle("音乐模式")
    window.resize(400, 300)
    window.show()
    sys.exit(app.exec_())
