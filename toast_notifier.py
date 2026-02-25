import sys
import threading
import time
from collections import deque

from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QVBoxLayout, QHBoxLayout, 
    QGraphicsDropShadowEffect, QDesktopWidget
)
from PyQt5.QtCore import (
    Qt, QTimer, QPoint, QPropertyAnimation, QEasingCurve, 
    pyqtSignal, QObject, QThread
)
from PyQt5.QtGui import QColor


class ToastWindow(QWidget):
    """单个通知窗口"""
    
    closed = pyqtSignal(object)  # 发送自身引用
    
    def __init__(self, title, message, duration=5000):
        super().__init__()
        
        self.duration = duration
        self.dragging = False
        self.drag_position = QPoint()
        self.target_y = 0
        
        self._setup_window()
        self._setup_ui(title, message)
        self._setup_animation()
        
        self.close_timer = QTimer(self)
        self.close_timer.timeout.connect(self._start_hide_animation)
        self.close_timer.setSingleShot(True)
        
        self._paused = False
        
    def _setup_window(self):
        self.setWindowFlags(
            Qt.FramelessWindowHint |      
            Qt.WindowStaysOnTopHint |     
            Qt.Tool |                     
            Qt.WindowDoesNotAcceptFocus   
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        
        self.toast_width = 360
        self.toast_height = 100
        self.setFixedSize(self.toast_width, self.toast_height)
        
    def _setup_ui(self, title, message):
        self.container = QWidget(self)
        self.container.setGeometry(0, 0, self.toast_width, self.toast_height)
        self.container.setStyleSheet("""
            QWidget {
                background-color: #2B2B2B;
                border-radius: 8px;
                border: 1px solid #3C3C3C;
            }
        """)
        
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 180))
        shadow.setOffset(0, 4)
        self.container.setGraphicsEffect(shadow)
        
        layout = QHBoxLayout(self.container)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(12)
        
        icon_label = QLabel()
        icon_label.setFixedSize(32, 32)
        icon_label.setStyleSheet("""
            QLabel {
                background-color: #0078D4;
                border-radius: 16px;
                color: white;
                font-size: 16px;
                font-weight: bold;
            }
        """)
        icon_label.setAlignment(Qt.AlignCenter)
        icon_label.setText("⚙")
        layout.addWidget(icon_label)
        
        text_layout = QVBoxLayout()
        text_layout.setSpacing(4)
        text_layout.setContentsMargins(0, 0, 0, 0)
        
        title_label = QLabel(title)
        title_label.setStyleSheet("""
            QLabel {
                color: #FFFFFF;
                font-size: 14px;
                font-weight: 600;
                font-family: "Segoe UI", "Microsoft YaHei", sans-serif;
            }
        """)
        title_label.setWordWrap(True)
        text_layout.addWidget(title_label)
        
        msg_label = QLabel(message)
        msg_label.setStyleSheet("""
            QLabel {
                color: #CCCCCC;
                font-size: 12px;
                font-family: "Segoe UI", "Microsoft YaHei", sans-serif;
            }
        """)
        msg_label.setWordWrap(True)
        text_layout.addWidget(msg_label)
        
        layout.addLayout(text_layout, 1)
        
    def _setup_animation(self):
        self.show_animation = QPropertyAnimation(self, b"pos")
        self.show_animation.setDuration(300)
        self.show_animation.setEasingCurve(QEasingCurve.OutCubic)
        
        self.hide_animation = QPropertyAnimation(self, b"pos")
        self.hide_animation.setDuration(300)
        self.hide_animation.setEasingCurve(QEasingCurve.InCubic)
        self.hide_animation.finished.connect(self._do_close)
        
    def show_at(self, x, y):
        """在指定位置显示（带滑入动画）"""
        self.target_y = y
        
        # 从屏幕右侧外滑入
        start_x = QDesktopWidget().availableGeometry().width() + 50
        self.move(start_x, y)
        
        end_pos = QPoint(x, y)
        start_pos = QPoint(start_x, y)
        
        self.show_animation.setStartValue(start_pos)
        self.show_animation.setEndValue(end_pos)
        
        self.show()
        self.show_animation.start()
        self.close_timer.start(self.duration)
        
    def move_to(self, y, animate=True):
        """移动到新的Y坐标"""
        self.target_y = y
        if animate:
            anim = QPropertyAnimation(self, b"pos")
            anim.setDuration(200)
            anim.setEasingCurve(QEasingCurve.OutCubic)
            anim.setStartValue(self.pos())
            anim.setEndValue(QPoint(self.x(), y))
            anim.start()
        else:
            self.move(self.x(), y)
            
    def _start_hide_animation(self):
        """开始滑出"""
        if self._paused:
            return
            
        screen_width = QDesktopWidget().availableGeometry().width()
        end_pos = QPoint(screen_width + 50, self.y())
        
        self.hide_animation.setStartValue(self.pos())
        self.hide_animation.setEndValue(end_pos)
        self.hide_animation.start()
        
    def _do_close(self):
        """真正关闭"""
        self.closed.emit(self)
        self.close()
        
    def enterEvent(self, event):
        """鼠标进入暂停"""
        self._paused = True
        self.close_timer.stop()
        super().enterEvent(event)
        
    def leaveEvent(self, event):
        """鼠标离开恢复"""
        self._paused = False
        self.close_timer.start(2000)
        super().leaveEvent(event)
        
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.dragging = True
            self.drag_position = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()
            
    def mouseMoveEvent(self, event):
        if self.dragging and event.buttons() == Qt.LeftButton:
            self.move(event.globalPos() - self.drag_position)
            self.target_y = self.y()
            event.accept()
            
    def mouseReleaseEvent(self, event):
        self.dragging = False
        event.accept()


class ToastManager(QObject):
    """
    在主线程运行的通知管理器
    通过信号接收来自其他线程的请求
    """
    
    # 信号：请求显示通知 (title, message, channel_id, duration, cooldown)
    show_signal = pyqtSignal(str, str, str, int, int)
    
    def __init__(self):
        super().__init__()
        
        self.MARGIN_RIGHT = 20
        self.MARGIN_BOTTOM = 60
        self.SPACING = 10
        self.MAX_TOASTS = 5
        
        self._toasts = deque()  # 通知队列，新的在左侧（底部）
        self._last_time = {}
        self._screen = QDesktopWidget().availableGeometry()
        
        # 连接信号
        self.show_signal.connect(self._on_show_notification)
        
        # 定时清理
        self._cleanup_timer = QTimer(self)
        self._cleanup_timer.timeout.connect(self._cleanup_closed)
        self._cleanup_timer.start(500)  # 每500ms清理一次
        
    def _calculate_positions(self):
        """计算所有通知的位置（从底部向上堆叠）"""
        base_x = self._screen.width() - 360 - self.MARGIN_RIGHT
        base_y = self._screen.height() - self.toast_height - self.MARGIN_BOTTOM
        
        positions = []
        for i in range(len(self._toasts)):
            x = base_x
            y = base_y - i * (self.toast_height + self.SPACING)
            positions.append((x, y))
        return positions
        
    def _rearrange_toasts(self, animate=True):
        """重新排列所有通知位置"""
        positions = self._calculate_positions()
        for i, toast in enumerate(self._toasts):
            if i < len(positions):
                x, y = positions[i]
                # 如果正在拖拽，不强制移动
                if not toast.dragging:
                    # 只有位置变化较大时才移动
                    if abs(toast.y() - y) > 5:
                        toast.move_to(y, animate=animate)
                        
    def _cleanup_closed(self):
        """清理已关闭的通知"""
        closed = [t for t in self._toasts if not t.isVisible()]
        if closed:
            for t in closed:
                self._toasts.remove(t)
            self._rearrange_toasts(animate=True)
            
    def _remove_toast(self, toast):
        """移除指定通知"""
        if toast in self._toasts:
            self._toasts.remove(toast)
            self._rearrange_toasts(animate=True)
            
    def _on_show_notification(self, title, message, channel_id, duration, cooldown):
        """处理显示通知请求（在主线程执行）"""
        # 冷却检查
        now = time.time()
        if channel_id in self._last_time:
            if now - self._last_time[channel_id] < cooldown:
                return
        self._last_time[channel_id] = now
        
        # 限制数量
        while len(self._toasts) >= self.MAX_TOASTS:
            oldest = self._toasts.pop()  # 移除最旧的（最上面）
            oldest.close()
            
        # 创建新通知
        toast = ToastWindow(title, message, duration)
        toast.closed.connect(lambda: self._remove_toast(toast))
        
        # 添加到队列（新的在索引0，即最底部）
        self._toasts.appendleft(toast)
        
        # 显示新通知（最底部）
        positions = self._calculate_positions()
        if positions:
            x, y = positions[0]
            toast.show_at(x, y)
            
        # 重新排列其他通知（向上移动）
        if len(self._toasts) > 1:
            self._rearrange_toasts(animate=True)
            
    @property
    def toast_height(self):
        return 100


class ToastNotifier:
    """
    线程安全的通知管理器（单例）
    首次调用必须在主线程进行初始化
    """
    
    _instance = None
    _lock = threading.Lock()
    _manager = None
    _app = None
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def _ensure_initialized(self):
        """确保在主线程初始化"""
        if ToastNotifier._app is None:
            # 检查是否在主线程
            if threading.current_thread() is not threading.main_thread():
                raise RuntimeError(
                    "ToastNotifier 首次初始化必须在主线程进行！\n"
                    "请在主线程先调用：notifier = ToastNotifier()"
                )
            
            # 创建 QApplication
            ToastNotifier._app = QApplication.instance()
            if ToastNotifier._app is None:
                ToastNotifier._app = QApplication(sys.argv)
                
            # 创建管理器（在主线程）
            ToastNotifier._manager = ToastManager()
            
    def show(self, title, message, channel_id="default", duration=5000, cooldown=3):
        """
        显示通知（线程安全）
        
        注意：首次调用必须在主线程！
        """
        try:
            self._ensure_initialized()
        except RuntimeError as e:
            return False

        ToastNotifier._manager.show_signal.emit(
            title, message, channel_id, duration, cooldown
        )
        return True
        
    def run(self):
        """启动事件循环（阻塞）"""
        if ToastNotifier._app:
            sys.exit(ToastNotifier._app.exec_())


# 兼容旧接口
class QtToastNotifier(ToastNotifier):
    pass
