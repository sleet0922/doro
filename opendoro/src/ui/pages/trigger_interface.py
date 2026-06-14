from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QScrollArea, QLabel, QGridLayout
from PyQt5.QtCore import Qt, QTimer
from qfluentwidgets import CardWidget, StrongBodyLabel, ScrollArea, FluentIcon, PrimaryPushButton, PushButton
import live2d.v3 as live2d


class ExpressionCard(CardWidget):
    def __init__(self, name: str, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        btn = PrimaryPushButton(name, self)
        btn.clicked.connect(self._trigger)
        layout.addWidget(btn)
        self._name = name
        self._widget = None

    def set_live2d(self, widget):
        self._widget = widget

    def _trigger(self):
        if self._widget and hasattr(self._widget, 'model'):
            try:
                self._widget.makeCurrent()
                self._widget.model.SetExpression(self._name)
                print(f"[手动触发] 表情: {self._name}")
            except Exception as e:
                print(f"[手动触发] 表情错误: {e}")


class MotionCard(CardWidget):
    def __init__(self, group: str, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        btn = PushButton(group, self)
        btn.clicked.connect(self._trigger)
        layout.addWidget(btn)
        self._group = group
        self._widget = None

    def set_live2d(self, widget):
        self._widget = widget

    def _trigger(self):
        if self._widget and hasattr(self._widget, 'play_motion'):
            self._widget.play_motion(self._group)


class TriggerInterface(ScrollArea):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("TriggerInterface")
        self._live2d_widget = None

        scroll_widget = QWidget()
        self.setWidget(scroll_widget)
        self.setWidgetResizable(True)

        layout = QVBoxLayout(scroll_widget)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(20)

        # 表情区域
        exp_label = StrongBodyLabel("😊 表情", self)
        layout.addWidget(exp_label)

        self.exp_grid = QWidget()
        self.exp_layout = QGridLayout(self.exp_grid)
        self.exp_layout.setSpacing(8)
        self.exp_cards = []
        layout.addWidget(self.exp_grid)

        # 动作区域
        motion_label = StrongBodyLabel("🎬 动作", self)
        layout.addWidget(motion_label)

        self.motion_grid = QWidget()
        self.motion_layout = QGridLayout(self.motion_grid)
        self.motion_layout.setSpacing(8)
        self.motion_cards = []
        layout.addWidget(self.motion_grid)

        layout.addStretch()

    def set_live2d_widget(self, widget):
        self._live2d_widget = widget
        # 模型在 show() 后才初始化，延迟轮询等待数据就绪
        self._retry_count = 0
        self._poll_timer = QTimer(self)
        self._poll_timer.timeout.connect(self._poll_and_build)
        self._poll_timer.start(200)

    def _poll_and_build(self):
        self._retry_count += 1
        if self._live2d_widget and self._live2d_widget.expression_ids:
            self._poll_timer.stop()
            self._rebuild()
        elif self._retry_count > 50:
            self._poll_timer.stop()

    def _rebuild(self):
        if not self._live2d_widget:
            return

        widget = self._live2d_widget

        # 清空旧按钮
        while self.exp_layout.count():
            item = self.exp_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        while self.motion_layout.count():
            item = self.motion_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        self.exp_cards.clear()
        self.motion_cards.clear()

        # 表情按钮（5列网格）
        for i, exp_name in enumerate(widget.expression_ids):
            card = ExpressionCard(exp_name)
            card.set_live2d(widget)
            self.exp_layout.addWidget(card, i // 5, i % 5)
            self.exp_cards.append(card)

        # 动作按钮
        for i, group in enumerate(widget.motion_groups.keys()):
            card = MotionCard(group)
            card.set_live2d(widget)
            self.motion_layout.addWidget(card, i // 5, i % 5)
            self.motion_cards.append(card)
