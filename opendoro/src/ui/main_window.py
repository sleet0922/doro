import os
import ctypes
from ctypes import wintypes
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt, QSettings
from PyQt5.QtGui import QIcon

from qfluentwidgets import (FluentWindow, NavigationItemPosition, FluentTranslator,
                            TransparentToolButton, setTheme, Theme, isDarkTheme, setThemeColor)
from qfluentwidgets import FluentIcon as FIF

from src.resource_utils import resource_path
from src.core.logger import logger
from src.core.font_scale_utils import apply_font_scale
from src.core.app_theme import THEME_COLOR

from src.ui.pages.trigger_interface import TriggerInterface

class MainWindow(FluentWindow):
    """简化的控制台窗口"""

    def __init__(self, version_manager=None):
        super().__init__()
        logger.info("Initializing MainWindow...")
        self.setObjectName("MainWindow")
        self._version_manager = version_manager

        self.setWindowTitle("Doro Pet")
        self.resize(1024, 800)

        # 创建页面
        self.trigger_interface = TriggerInterface(self)
        QApplication.processEvents()

        # 导航
        self.addSubInterface(self.trigger_interface, FIF.EMOJI_TAB_SYMBOLS, "互动")
        QApplication.processEvents()

        # 主题
        setThemeColor(THEME_COLOR)
        if isDarkTheme():
            setTheme(Theme.DARK)
            self.load_stylesheet(resource_path("themes/dark.qss"))
        else:
            setTheme(Theme.LIGHT)
            self.load_stylesheet(resource_path("themes/light.qss"))
        QApplication.processEvents()

        self.init_window()

    def init_window(self):
        icon_path = resource_path("data/icons/app.png")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        desktop = QApplication.desktop().availableGeometry()
        w, h = desktop.width(), desktop.height()
        self.move(w//2 - self.width()//2, h//2 - self.height()//2)

    def load_stylesheet(self, path):
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                qss = f.read()
            settings = QSettings("DoroPet", "Settings")
            font_scale = settings.value("font_scale", 1.0, type=float)
            qss = apply_font_scale(qss, font_scale)
            QApplication.instance().setStyleSheet(qss)
        else:
            logger.warning(f"Stylesheet not found: {path}")

    def set_live2d_widget(self, widget):
        self.live2d_widget = widget
        if hasattr(self, 'trigger_interface'):
            self.trigger_interface.set_live2d_widget(widget)

    def set_version_manager(self, version_manager):
        self._version_manager = version_manager

    def closeEvent(self, event):
        logger.info("MainWindow hidden to tray.")
        self.hide()
        event.ignore()
