import os
import random
import live2d.v3 as live2d
from live2d.v3 import clearBuffer
from live2d.utils.canvas import Canvas
from PyQt5.QtCore import Qt, QTimer, QPoint
from PyQt5.QtGui import QMouseEvent, QWheelEvent, QCursor
from PyQt5.QtWidgets import QOpenGLWidget, QMenu, QAction, QApplication
from src.resource_utils import resource_path


class Live2DWidget(QOpenGLWidget):
    def __init__(self, *args, path: str, parent=None, **kwargs) -> None:
        self.path = path
        if not os.path.exists(self.path):
            self.path = resource_path("models/Doro/Doro.model3.json")

        super().__init__(parent)

        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint | Qt.Window)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, True)
        self.setMouseTracking(True)

        fmt = self.format()
        fmt.setAlphaBufferSize(8)
        self.setFormat(fmt)

        self.main_window = None
        self.expression_ids = []
        self.motion_groups = {}
        self.is_mirrored = False

        self.resize(200, 200)

        # 15 秒自动随机切换表情/动作
        self.auto_switch_timer = QTimer(self)
        self.auto_switch_timer.timeout.connect(self._auto_switch)
        self.auto_switch_timer.setInterval(15000)

        # 滑动动画
        self._slide_steps = 0
        self._slide_dx = 0
        self._slide_timer = QTimer(self)
        self._slide_timer.timeout.connect(self._slide_tick)
        self._slide_timer.setInterval(20)

    def initializeGL(self) -> None:
        self.makeCurrent()

        live2d.init()
        live2d.glInit()

        self.model = live2d.LAppModel()
        self.model.LoadModelJson(self.path)
        self.model.Resize(self.width(), self.height())

        self.canvas = Canvas()
        self.canvas.SetSize(self.width(), self.height())

        self.expression_ids = self.model.GetExpressionIds()
        self.motion_groups = self.model.GetMotionGroups()

        self.refresh = self.startTimer(15)

        if hasattr(self, 'auto_switch_timer'):
            self.auto_switch_timer.start()

    def paintGL(self) -> None:
        self.model.Update()

        def on_draw():
            clearBuffer()
            self.model.Draw()

        clearBuffer(0.0, 0.0, 0.0, 0.0)
        self.canvas.Draw(on_draw)

    def resizeGL(self, w: int, h: int) -> None:
        if hasattr(self, 'model'):
            self.model.Resize(w, h)
        if hasattr(self, 'canvas'):
            self.canvas.SetSize(w, h)

    def timerEvent(self, event) -> None:
        if event.timerId() == self.refresh:
            global_pos = QCursor.pos()
            center_local = QPoint(self.width() // 2, self.height() // 2)
            center_global = self.mapToGlobal(center_local)

            dx = global_pos.x() - center_global.x()
            dy = global_pos.y() - center_global.y()

            screen = QApplication.screenAt(global_pos)
            if not screen:
                screen = QApplication.primaryScreen()
            screen_geo = screen.geometry()

            max_dx = screen_geo.width() / 2
            max_dy = screen_geo.height() / 2

            ratio_x = max(-1.0, min(1.0, dx / max_dx))
            ratio_y = max(-1.0, min(1.0, dy / max_dy))

            mirror_factor = -1.0 if self.is_mirrored else 1.0
            target_x = center_local.x() + ratio_x * (self.width() / 2) * mirror_factor
            target_y = center_local.y() + ratio_y * (self.height() / 2)

            self.model.Drag(target_x, target_y)
            self.update()

    def play_motion(self, group: str):
        """播放指定动作组，跑动作触发滑动"""
        try:
            self.makeCurrent()
            self.model.StartRandomMotion(group, live2d.MotionPriority.FORCE)
            print(f"[动作] 播放: {group}")
        except Exception as e:
            print(f"[动作] 错误: {e}")
            return

        if group == "跑":
            if random.random() < 0.5:
                # 左移：恢复朝右（不镜像）
                self._start_slide(-80, mirrored=False)
            else:
                # 右移：Y轴翻转（镜像）
                self._start_slide(80, mirrored=True)

    def _auto_switch(self):
        """每 15 秒自动随机切换表情和动作，附带 50% 概率滑动"""
        group = None

        # 表情（手动随机，避免 SetRandomExpression 的 UTF-8 解码 bug）
        try:
            self.makeCurrent()
            if self.expression_ids:
                exp = random.choice(self.expression_ids)
                self.model.SetExpression(exp)
                print(f"[AutoSwitch] 表情: {exp}")
        except Exception as e:
            print(f"[AutoSwitch] 表情错误: {e}")

        # 动作
        if self.motion_groups:
            group = random.choice(list(self.motion_groups.keys()))
            self.play_motion(group)

    def _start_slide(self, total_dx: int, mirrored: bool):
        """开始滑动动画，mirrored=True 则 Y 轴翻转朝左"""
        if not hasattr(self, '_slide_timer'):
            return

        # 边界反弹
        screen = QApplication.primaryScreen().availableGeometry()
        new_x = self.x() + total_dx
        if new_x < screen.x() or new_x + self.width() > screen.x() + screen.width():
            total_dx = -total_dx
            mirrored = not mirrored

        # 设置镜像方向
        self.is_mirrored = mirrored
        scale_x = -1.0 if mirrored else 1.0
        self.model.SetScaleX(scale_x)

        print(f"[滑动] dx={total_dx}, mirrored={mirrored}")
        self._slide_steps = 15
        self._slide_dx = total_dx / 15.0
        self._slide_timer.start()

    def _slide_tick(self):
        """滑动动画每帧"""
        if self._slide_steps <= 0:
            self._slide_timer.stop()
            return
        self._slide_steps -= 1
        x, y = self.x(), self.y()
        self.move(int(x + self._slide_dx), y)
        if self._slide_steps == 0:
            self._slide_timer.stop()

    def show_context_menu(self, global_pos):
        menu = QMenu(self)

        action_quit = QAction("❌ 退出", self)
        action_quit.triggered.connect(QApplication.instance().quit)
        menu.addAction(action_quit)

        menu.exec_(global_pos)

    def open_main_window(self):
        try:
            if self.main_window is None:
                from src.ui.main_window import MainWindow
                self.main_window = MainWindow()
                self.main_window.set_live2d_widget(self)
            if self.main_window.isMinimized():
                self.main_window.showNormal()
            if not self.main_window.isVisible():
                self.main_window.show()
            self.main_window.raise_()
            self.main_window.activateWindow()
        except Exception as e:
            import traceback
            traceback.print_exc()

    def mousePressEvent(self, event: QMouseEvent | None):
        if event and event.button() == Qt.LeftButton:
            self.drag_position = event.globalPos() - self.frameGeometry().topLeft()
            self.drag_start_global = event.globalPos()
        event.accept()

    def mouseMoveEvent(self, event: QMouseEvent | None):
        if event:
            if event.buttons() & Qt.LeftButton and hasattr(self, "drag_position"):
                self.move(event.globalPos() - self.drag_position)
        event.accept()

    def mouseReleaseEvent(self, event: QMouseEvent | None):
        if not event:
            return

        if hasattr(self, "drag_start_global"):
            del self.drag_start_global
        if hasattr(self, "drag_position"):
            del self.drag_position

        if event.button() == Qt.MiddleButton:
            self.open_main_window()
        elif event.button() == Qt.RightButton:
            self.show_context_menu(event.globalPos())

        event.accept()

    def closeEvent(self, event):
        super().closeEvent(event)
        if hasattr(self, 'auto_switch_timer'):
            self.auto_switch_timer.stop()
        if hasattr(self, '_slide_timer'):
            self._slide_timer.stop()
        if hasattr(self, 'model'):
            live2d.glRelease()
        live2d.dispose()

    def wheelEvent(self, event: QWheelEvent):
        pass

    def mouseDoubleClickEvent(self, event: QMouseEvent | None):
        pass
