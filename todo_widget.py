import sys
import time
import json
import os
import winreg

from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLineEdit, QLabel,
    QScrollArea, QFrame, QSizeGrip,
    QDialog, QSlider, QCheckBox,
    QGraphicsOpacityEffect
)
from PySide6.QtCore import Qt, QPropertyAnimation


SETTINGS_FILE = "settings.json"
TASK_FILE = "tasks.json"


# ================= SETTINGS DIALOG ================= #

class SettingsDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent_widget = parent

        self.setWindowTitle("Settings")
        self.setFixedSize(240, 200)

        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("Opacity"))
        self.opacity_slider = QSlider(Qt.Horizontal)
        self.opacity_slider.setRange(80, 255)
        self.opacity_slider.setValue(self.parent_widget.opacity_value)
        self.opacity_slider.valueChanged.connect(self.change_opacity)
        layout.addWidget(self.opacity_slider)

        layout.addWidget(QLabel("Font Size"))
        self.font_slider = QSlider(Qt.Horizontal)
        self.font_slider.setRange(10, 18)
        self.font_slider.setValue(self.parent_widget.font_size)
        self.font_slider.valueChanged.connect(self.change_font)
        layout.addWidget(self.font_slider)

        self.auto_checkbox = QCheckBox("Start with Windows")
        self.auto_checkbox.setChecked(self.parent_widget.auto_start)
        self.auto_checkbox.stateChanged.connect(self.toggle_autostart)
        layout.addWidget(self.auto_checkbox)

    def change_opacity(self, value):
        self.parent_widget.opacity_value = value
        self.parent_widget.update_theme()

    def change_font(self, value):
        self.parent_widget.font_size = value
        self.parent_widget.update_theme()

    def toggle_autostart(self, state):
        self.parent_widget.set_autostart(state == Qt.Checked)


# ================= MAIN WIDGET ================= #

class TodoWidget(QWidget):
    def __init__(self):
        super().__init__()

        self.tasks = []
        self.opacity_value = 160
        self.font_size = 13
        self.auto_start = False
        self.locked = False

        self.load_settings()
        self.load_tasks()
        self.init_ui()
        self.refresh_tasks()
        self.startup_animation()

    # ---------------- UI ---------------- #

    def init_ui(self):
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)

        self.resize(260, 340)
        self.setMinimumSize(220, 260)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(8, 8, 8, 8)

        self.container = QFrame()
        self.container.setObjectName("container")

        container_layout = QVBoxLayout(self.container)
        container_layout.setContentsMargins(12, 12, 12, 12)
        container_layout.setSpacing(6)

        # Top bar
        top_bar = QHBoxLayout()

        self.input = QLineEdit()
        self.input.setPlaceholderText("Add task...")
        self.input.returnPressed.connect(self.add_task)

        self.settings_btn = QPushButton("⚙")
        self.settings_btn.setFixedWidth(30)
        self.settings_btn.clicked.connect(self.open_settings)

        self.close_btn = QPushButton("✖")
        self.close_btn.setFixedWidth(30)
        self.close_btn.clicked.connect(self.close)

        top_bar.addWidget(self.input)
        top_bar.addWidget(self.settings_btn)
        top_bar.addWidget(self.close_btn)

        container_layout.addLayout(top_bar)

        # Scroll area
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.NoFrame)

        self.task_widget = QWidget()
        self.task_layout = QVBoxLayout(self.task_widget)
        self.task_layout.setSpacing(4)
        self.task_layout.setContentsMargins(0, 0, 0, 0)

        self.scroll.setWidget(self.task_widget)
        container_layout.addWidget(self.scroll)

        main_layout.addWidget(self.container)

        # Resize grip
        self.size_grip = QSizeGrip(self)
        self.size_grip.setFixedSize(14, 14)

        self.update_theme()

    def resizeEvent(self, event):
        grip_size = self.size_grip.size()
        self.size_grip.move(
            self.width() - grip_size.width() - 4,
            self.height() - grip_size.height() - 4
        )

    # ---------------- STARTUP ANIMATION ---------------- #

    def startup_animation(self):
        effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(effect)

        self.anim = QPropertyAnimation(effect, b"opacity")
        self.anim.setDuration(400)
        self.anim.setStartValue(0)
        self.anim.setEndValue(1)
        self.anim.start()

    # ---------------- THEME ---------------- #

    def update_theme(self):
        bg = f"rgba(0,0,0,{self.opacity_value})"

        self.setStyleSheet(f"""
            #container {{
                background-color: {bg};
                border-radius: 14px;
            }}

            QLineEdit {{
                padding: 6px;
                border-radius: 7px;
                border: none;
                background-color: rgba(255,255,255,40);
                color: white;
                font-size: {self.font_size}px;
            }}

            QPushButton {{
                background: transparent;
                border: none;
                color: white;
                text-align: left;
                padding: 5px;
                font-size: {self.font_size}px;
            }}

            QPushButton:hover {{
                background-color: rgba(255,255,255,25);
                border-radius: 6px;
            }}
        """)

        self.save_settings()

    # ---------------- SETTINGS ---------------- #

    def open_settings(self):
        dialog = SettingsDialog(self)
        dialog.exec()

    def save_settings(self):
        settings = {
            "opacity": self.opacity_value,
            "font_size": self.font_size,
            "auto_start": self.auto_start
        }
        with open(SETTINGS_FILE, "w") as f:
            json.dump(settings, f)

    def load_settings(self):
        if os.path.exists(SETTINGS_FILE):
            with open(SETTINGS_FILE, "r") as f:
                data = json.load(f)
                self.opacity_value = data.get("opacity", 160)
                self.font_size = data.get("font_size", 13)
                self.auto_start = data.get("auto_start", False)

    # ---------------- AUTOSTART ---------------- #

    def set_autostart(self, enabled):
        self.auto_start = enabled
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0, winreg.KEY_SET_VALUE
        )
        if enabled:
            winreg.SetValueEx(key, "TodoWidget", 0, winreg.REG_SZ, sys.argv[0])
        else:
            try:
                winreg.DeleteValue(key, "TodoWidget")
            except:
                pass
        winreg.CloseKey(key)
        self.save_settings()

    # ---------------- TASKS ---------------- #

    def add_task(self):
        text = self.input.text().strip()
        if not text:
            return

        self.tasks.append({
            "text": text,
            "completed": False,
            "created_at": time.time()
        })

        self.input.clear()
        self.refresh_tasks()
        self.save_tasks()

    def toggle_task(self, task):
        task["completed"] = not task["completed"]
        self.refresh_tasks()
        self.save_tasks()

    def delete_task(self, task):
        self.tasks.remove(task)
        self.refresh_tasks()
        self.save_tasks()

    def refresh_tasks(self):
        while self.task_layout.count():
            item = self.task_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        self.tasks.sort(key=lambda x: (x["completed"], x["created_at"]))

        added_separator = False

        for task in self.tasks:

            if task["completed"] and not added_separator:
                sep = QLabel("Completed")
                sep.setStyleSheet("color: rgba(255,255,255,120); font-size:10px;")
                self.task_layout.addWidget(sep)
                added_separator = True

            btn = QPushButton(
                ("● " if task["completed"] else "○ ") + task["text"]
            )

            if task["completed"]:
                btn.setStyleSheet(f"""
                    color: rgba(255,255,255,120);
                    text-decoration: line-through;
                    font-size: {self.font_size}px;
                """)

            btn.clicked.connect(lambda _, t=task: self.toggle_task(t))
            btn.setContextMenuPolicy(Qt.CustomContextMenu)
            btn.customContextMenuRequested.connect(lambda _, t=task: self.delete_task(t))

            self.task_layout.addWidget(btn)

        self.task_layout.addStretch()

    def save_tasks(self):
        with open(TASK_FILE, "w") as f:
            json.dump(self.tasks, f)

    def load_tasks(self):
        if os.path.exists(TASK_FILE):
            with open(TASK_FILE, "r") as f:
                self.tasks = json.load(f)

    # ---------------- DRAG + LOCK ---------------- #

    def mousePressEvent(self, event):
        if self.locked:
            return
        if event.button() == Qt.LeftButton:
            self.old_pos = event.globalPosition().toPoint()

    def mouseMoveEvent(self, event):
        if self.locked:
            return
        if event.buttons() == Qt.LeftButton:
            delta = event.globalPosition().toPoint() - self.old_pos
            self.move(self.x() + delta.x(), self.y() + delta.y())
            self.old_pos = event.globalPosition().toPoint()

    def mouseDoubleClickEvent(self, event):
        self.locked = not self.locked


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = TodoWidget()
    window.show()
    sys.exit(app.exec())