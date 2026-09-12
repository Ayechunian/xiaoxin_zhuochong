import json
import os
import time
import uuid
from datetime import datetime, timedelta
from pathlib import Path

from PySide6.QtCore import QDateTime, Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QComboBox,
    QDateTimeEdit,
    QDialog,
    QDialogButtonBox,
    QFrame,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from .paths import resource_path


REMINDER_STYLESHEET = """
QDialog {
    background: #fff7e8;
    color: #4d342d;
    font-family: "Microsoft YaHei UI", "Microsoft YaHei", sans-serif;
    font-size: 13px;
}
QFrame#reminderHeader {
    background: #fff0c8;
    border: 1px solid #f2d28b;
    border-radius: 18px;
}
QFrame#shinBadge {
    background: #ef6657;
    border: 3px solid #f8c94d;
    border-radius: 22px;
}
QLabel#headerTitle { color: #57352a; font-size: 22px; font-weight: 800; }
QLabel#headerSubtitle { color: #89644e; font-size: 12px; }
QLabel#sectionTitle { color: #5a382c; font-size: 15px; font-weight: 800; }
QLabel#summary { color: #6f4b3b; font-weight: 700; padding: 5px 2px; }
QLabel#feedback { color: #806052; padding: 7px 10px; background: #fffdf8; border: 1px solid #f1dfc2; border-radius: 10px; }
QLineEdit, QComboBox, QDateTimeEdit {
    background: #fffdf8;
    color: #49332c;
    border: 1px solid #e8cfa5;
    border-radius: 10px;
    padding: 7px 9px;
    selection-background-color: #f2bd43;
}
QLineEdit:focus, QComboBox:focus, QDateTimeEdit:focus { border: 2px solid #ef9f4d; padding: 6px 8px; }
QComboBox::drop-down { border: 0; width: 24px; }
QListWidget {
    background: #fffdf8;
    color: #49332c;
    border: 1px solid #ecd7b7;
    border-radius: 12px;
    padding: 5px;
    outline: 0;
}
QListWidget::item { padding: 9px 10px; border-radius: 8px; }
QListWidget::item:alternate { background: #fff7e8; }
QListWidget::item:selected { background: #ffe4a1; color: #4d3027; }
QPushButton {
    background: #f6c84e;
    color: #543327;
    border: 0;
    border-radius: 11px;
    padding: 8px 15px;
    font-weight: 700;
}
QPushButton:hover { background: #f4b83e; }
QPushButton:pressed { background: #e9a936; }
QPushButton#secondaryButton { background: #f7e7c7; color: #704b3b; }
QPushButton#dangerButton { background: #f3b2a8; color: #713a32; }
QTabWidget::pane { background: #fffdf8; border: 1px solid #efd9b7; border-radius: 12px; top: -1px; }
QTabBar::tab { background: #f7e7c7; color: #765344; padding: 9px 18px; margin-right: 4px; border-radius: 9px 9px 0 0; }
QTabBar::tab:selected { background: #ef6657; color: white; font-weight: 800; }
QDialogButtonBox QPushButton { min-width: 78px; }
"""


def apply_reminder_theme(dialog):
    dialog.setStyleSheet(REMINDER_STYLESHEET)


def add_header(layout, compact=False):
    """Add a warm, character-led header without depending on external artwork."""
    header = QFrame()
    header.setObjectName("reminderHeader")
    header_layout = QHBoxLayout(header)
    header_layout.setContentsMargins(12, 8, 14, 8)
    avatar = QLabel()
    avatar.setFixedSize(58 if not compact else 46, 66 if not compact else 52)
    avatar.setAlignment(Qt.AlignmentFlag.AlignCenter)
    avatar.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
    pixmap = QPixmap(str(resource_path("assets", "character.png")))
    if not pixmap.isNull():
        avatar.setPixmap(pixmap.scaled(avatar.size(), Qt.AspectRatioMode.KeepAspectRatio,
                                       Qt.TransformationMode.SmoothTransformation))
    header_layout.addWidget(avatar)
    text_column = QVBoxLayout()
    title = QLabel("小新提醒小站" if not compact else "小新提醒")
    title.setObjectName("headerTitle")
    subtitle = QLabel("今天也要记得按时完成哦！  ✦  📌" if not compact else "把要记住的事情写下来吧")
    subtitle.setObjectName("headerSubtitle")
    text_column.addWidget(title)
    text_column.addWidget(subtitle)
    header_layout.addLayout(text_column, 1)
    badge = QFrame()
    badge.setObjectName("shinBadge")
    badge.setFixedSize(58 if not compact else 48, 44 if not compact else 38)
    badge_label = QLabel("小新", badge)
    badge_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    badge_label.setStyleSheet("color: #fffdf2; font-size: 16px; font-weight: 900;")
    badge_layout = QVBoxLayout(badge)
    badge_layout.setContentsMargins(0, 0, 0, 0)
    badge_layout.addWidget(badge_label)
    header_layout.addWidget(badge)
    layout.addWidget(header)


class ReminderStore:
    """Small JSON reminder store with atomic writes."""

    def __init__(self, path):
        self.path = Path(path)
        self.items = []
        self.load_error = None
        self.load()

    def load(self):
        if not self.path.exists():
            return
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
            raw_items = payload.get("reminders", []) if isinstance(payload, dict) else []
            self.items = [item for item in raw_items
                          if isinstance(item, dict) and item.get("id") and item.get("text")]
        except (OSError, ValueError, TypeError) as exc:
            self.load_error = str(exc)
            self.items = []

    def save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(self.path.suffix + ".tmp")
        payload = {"version": 1, "reminders": self.items}
        temporary.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        os.replace(temporary, self.path)

    def add(self, text, due_at, repeat="none"):
        repeat = repeat if repeat in {"none", "daily", "weekly"} else "none"
        item = {
            "id": uuid.uuid4().hex,
            "text": text.strip()[:120],
            "due_at": float(due_at),
            "created_at": time.time(),
            "status": "pending",
            "repeat": repeat,
        }
        if not item["text"]:
            raise ValueError("提醒内容不能为空")
        self.items.append(item)
        self.save()
        return item

    def pending(self):
        return sorted(
            (item for item in self.items if item.get("status") == "pending"),
            key=lambda item: float(item.get("due_at", 0)),
        )

    def due(self, now=None):
        now = time.time() if now is None else float(now)
        return [item for item in self.pending() if float(item.get("due_at", 0)) <= now]

    def get(self, reminder_id):
        return next((item for item in self.items if item.get("id") == reminder_id), None)

    def complete(self, reminder_id):
        item = self.get(reminder_id)
        if item is None:
            return False
        repeat = item.get("repeat", "none")
        if repeat in {"daily", "weekly"}:
            interval = 86400 if repeat == "daily" else 7 * 86400
            next_due = float(item.get("due_at", time.time())) + interval
            now = time.time()
            while next_due <= now:
                next_due += interval
            item["due_at"] = next_due
            item["last_completed_at"] = now
            item["status"] = "pending"
            self.save()
            return True
        item["status"] = "completed"
        item["completed_at"] = time.time()
        self.save()
        return True

    def snooze(self, reminder_id, minutes=10):
        item = self.get(reminder_id)
        if item is None:
            return False
        item["status"] = "pending"
        item["due_at"] = time.time() + max(1, int(minutes)) * 60
        item.pop("completed_at", None)
        self.save()
        return True

    def delete(self, reminder_id):
        before = len(self.items)
        self.items = [item for item in self.items if item.get("id") != reminder_id]
        if len(self.items) == before:
            return False
        self.save()
        return True


class AddReminderDialog(QDialog):
    PRESETS = (
        ("10 分钟后", "minutes", 10),
        ("30 分钟后", "minutes", 30),
        ("1 小时后", "minutes", 60),
        ("下一个 18:00", "next_18", None),
        ("自定义时间", "custom", None),
    )

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("添加提醒")
        self.setMinimumWidth(410)
        apply_reminder_theme(self)
        layout = QVBoxLayout(self)
        add_header(layout, compact=True)
        form = QFormLayout()
        form.setContentsMargins(4, 8, 4, 2)
        form.setVerticalSpacing(10)
        self.content = QLineEdit()
        self.content.setPlaceholderText("例如：提交报告、起来喝水")
        self.content.setMaxLength(120)
        form.addRow("提醒内容", self.content)
        self.preset = QComboBox()
        for label, kind, value in self.PRESETS:
            self.preset.addItem(label, (kind, value))
        form.addRow("提醒时间", self.preset)
        self.repeat = QComboBox()
        for label, key in (("不重复", "none"), ("每天", "daily"), ("每周", "weekly")):
            self.repeat.addItem(label, key)
        form.addRow("重复提醒", self.repeat)
        self.custom_time = QDateTimeEdit(QDateTime.currentDateTime().addSecs(3600))
        self.custom_time.setDisplayFormat("yyyy-MM-dd HH:mm")
        self.custom_time.setCalendarPopup(True)
        self.custom_time.setMinimumDateTime(QDateTime.currentDateTime().addSecs(60))
        self.custom_time.setEnabled(False)
        form.addRow("自定义", self.custom_time)
        layout.addLayout(form)
        hint = QLabel("提醒到点后会持续显示，点击桌宠即可确认。")
        hint.setObjectName("feedback")
        layout.addWidget(hint)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("添加")
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("取消")
        buttons.accepted.connect(self.validate_and_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self.preset.currentIndexChanged.connect(self.update_custom_state)
        self.content.setFocus()

    def update_custom_state(self):
        kind, _ = self.preset.currentData()
        self.custom_time.setEnabled(kind == "custom")

    def due_epoch(self):
        kind, value = self.preset.currentData()
        if kind == "minutes":
            return time.time() + int(value) * 60
        if kind == "next_18":
            now = datetime.now()
            target = now.replace(hour=18, minute=0, second=0, microsecond=0)
            if target <= now:
                target += timedelta(days=1)
            return target.timestamp()
        return self.custom_time.dateTime().toSecsSinceEpoch()

    def validate_and_accept(self):
        if not self.content.text().strip():
            QMessageBox.information(self, "缺少内容", "请先填写提醒内容。")
            return
        if self.due_epoch() <= time.time():
            QMessageBox.information(self, "时间无效", "提醒时间需要晚于现在。")
            return
        self.accept()


class ReminderManagerDialog(QDialog):
    def __init__(self, store, parent=None):
        super().__init__(parent)
        self.store = store
        self.changed = False
        self.setWindowTitle("管理提醒")
        self.resize(470, 310)
        self.setMinimumWidth(430)
        apply_reminder_theme(self)
        layout = QVBoxLayout(self)
        add_header(layout, compact=True)
        self.summary = QLabel()
        self.summary.setObjectName("summary")
        layout.addWidget(self.summary)
        self.list = QListWidget()
        self.list.setAlternatingRowColors(True)
        layout.addWidget(self.list)
        controls = QHBoxLayout()
        complete = QPushButton("标记完成")
        delete = QPushButton("删除")
        close = QPushButton("关闭")
        delete.setObjectName("dangerButton")
        close.setObjectName("secondaryButton")
        controls.addWidget(complete)
        controls.addWidget(delete)
        controls.addStretch(1)
        controls.addWidget(close)
        layout.addLayout(controls)
        complete.clicked.connect(self.complete_selected)
        delete.clicked.connect(self.delete_selected)
        close.clicked.connect(self.accept)
        self.list.itemDoubleClicked.connect(lambda _: self.complete_selected())
        self.refresh()

    def selected_id(self):
        item = self.list.currentItem()
        return item.data(Qt.ItemDataRole.UserRole) if item else None

    def refresh(self):
        self.list.clear()
        pending = self.store.pending()
        self.summary.setText(f"共有 {len(pending)} 条待处理提醒")
        for reminder in pending:
            due = datetime.fromtimestamp(float(reminder["due_at"])).strftime("%m-%d %H:%M")
            repeat_label = {"daily": " · 每天", "weekly": " · 每周"}.get(reminder.get("repeat", "none"), "")
            item = QListWidgetItem(f"{due}{repeat_label}   {reminder['text']}")
            item.setData(Qt.ItemDataRole.UserRole, reminder["id"])
            self.list.addItem(item)
        if not pending:
            self.list.addItem("目前没有待处理提醒")
            self.list.item(0).setFlags(Qt.ItemFlag.NoItemFlags)

    def complete_selected(self):
        reminder_id = self.selected_id()
        if reminder_id and self.store.complete(reminder_id):
            self.changed = True
            self.refresh()

    def delete_selected(self):
        reminder_id = self.selected_id()
        if reminder_id and self.store.delete(reminder_id):
            self.changed = True
            self.refresh()


class ReminderCenterDialog(QDialog):
    """Single-page entry point for creating and managing reminders."""

    PRESETS = AddReminderDialog.PRESETS

    def __init__(self, store, on_added=None, on_changed=None, parent=None):
        super().__init__(parent)
        self.store = store
        self.on_added = on_added
        self.on_changed = on_changed
        self.setWindowTitle("提醒中心")
        self.resize(560, 500)
        self.setMinimumSize(520, 450)
        apply_reminder_theme(self)
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 14, 16, 14)
        root.setSpacing(12)
        add_header(root)
        self.tabs = QTabWidget()
        root.addWidget(self.tabs)
        self.build_add_page()
        self.build_manage_page()
        close_buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        close_buttons.button(QDialogButtonBox.StandardButton.Close).setText("关闭")
        close_buttons.button(QDialogButtonBox.StandardButton.Close).setObjectName("secondaryButton")
        close_buttons.rejected.connect(self.reject)
        root.addWidget(close_buttons)
        self.refresh()

    def build_add_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(14, 16, 14, 14)
        section = QLabel("写下要记住的事")
        section.setObjectName("sectionTitle")
        layout.addWidget(section)
        form = QFormLayout()
        form.setVerticalSpacing(10)
        self.content = QLineEdit()
        self.content.setPlaceholderText("例如：提交报告、起来喝水")
        self.content.setMaxLength(120)
        form.addRow("提醒内容", self.content)
        self.preset = QComboBox()
        for label, kind, value in self.PRESETS:
            self.preset.addItem(label, (kind, value))
        form.addRow("提醒时间", self.preset)
        self.repeat = QComboBox()
        for label, key in (("不重复", "none"), ("每天", "daily"), ("每周", "weekly")):
            self.repeat.addItem(label, key)
        form.addRow("重复提醒", self.repeat)
        self.custom_time = QDateTimeEdit(QDateTime.currentDateTime().addSecs(3600))
        self.custom_time.setDisplayFormat("yyyy-MM-dd HH:mm")
        self.custom_time.setCalendarPopup(True)
        self.custom_time.setMinimumDateTime(QDateTime.currentDateTime().addSecs(60))
        self.custom_time.setEnabled(False)
        form.addRow("自定义", self.custom_time)
        layout.addLayout(form)
        self.add_feedback = QLabel("提醒到点后会持续显示，点击桌宠即可确认。")
        self.add_feedback.setObjectName("feedback")
        layout.addWidget(self.add_feedback)
        add_button = QPushButton("添加提醒")
        add_button.setDefault(True)
        add_button.clicked.connect(self.add_reminder)
        layout.addWidget(add_button)
        layout.addStretch(1)
        self.preset.currentIndexChanged.connect(self.update_custom_state)
        self.content.returnPressed.connect(self.add_reminder)
        self.tabs.addTab(page, "添加提醒")

    def build_manage_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(14, 16, 14, 14)
        self.summary = QLabel()
        self.summary.setObjectName("summary")
        layout.addWidget(self.summary)
        self.list = QListWidget()
        self.list.setAlternatingRowColors(True)
        layout.addWidget(self.list)
        controls = QHBoxLayout()
        complete = QPushButton("标记完成")
        snooze = QPushButton("延后 10 分钟")
        delete = QPushButton("删除")
        snooze.setObjectName("secondaryButton")
        delete.setObjectName("dangerButton")
        controls.addWidget(complete)
        controls.addWidget(snooze)
        controls.addWidget(delete)
        controls.addStretch(1)
        layout.addLayout(controls)
        complete.clicked.connect(self.complete_selected)
        snooze.clicked.connect(self.snooze_selected)
        delete.clicked.connect(self.delete_selected)
        self.list.itemDoubleClicked.connect(lambda _: self.complete_selected())
        self.tabs.addTab(page, "管理提醒")

    def update_custom_state(self):
        kind, _ = self.preset.currentData()
        self.custom_time.setEnabled(kind == "custom")

    def selected_id(self):
        item = self.list.currentItem()
        return item.data(Qt.ItemDataRole.UserRole) if item else None

    def due_epoch(self):
        kind, value = self.preset.currentData()
        if kind == "minutes":
            return time.time() + int(value) * 60
        if kind == "next_18":
            now = datetime.now()
            target = now.replace(hour=18, minute=0, second=0, microsecond=0)
            if target <= now:
                target += timedelta(days=1)
            return target.timestamp()
        return self.custom_time.dateTime().toSecsSinceEpoch()

    def add_reminder(self):
        text = self.content.text().strip()
        if not text:
            self.add_feedback.setText("请先填写提醒内容。")
            self.add_feedback.setStyleSheet("color: #9b3f43; font-weight: 600;")
            return
        due_at = self.due_epoch()
        if due_at <= time.time():
            self.add_feedback.setText("提醒时间需要晚于现在。")
            self.add_feedback.setStyleSheet("color: #9b3f43; font-weight: 600;")
            return
        reminder = self.store.add(text, due_at, self.repeat.currentData())
        due_text = datetime.fromtimestamp(due_at).strftime("%m-%d %H:%M")
        self.add_feedback.setText(f"已添加：{due_text}  {text}")
        self.add_feedback.setStyleSheet("color: #47735b; font-weight: 600;")
        self.content.clear()
        self.refresh()
        if self.on_added:
            self.on_added(reminder)

    def refresh(self):
        self.list.clear()
        pending = self.store.pending()
        self.summary.setText(f"共有 {len(pending)} 条待处理提醒")
        self.tabs.setTabText(1, f"管理提醒（{len(pending)}）")
        for reminder in pending:
            due = datetime.fromtimestamp(float(reminder["due_at"])).strftime("%m-%d %H:%M")
            repeat_label = {"daily": " · 每天", "weekly": " · 每周"}.get(reminder.get("repeat", "none"), "")
            item = QListWidgetItem(f"{due}{repeat_label}   {reminder['text']}")
            item.setData(Qt.ItemDataRole.UserRole, reminder["id"])
            self.list.addItem(item)
        if not pending:
            empty = QListWidgetItem("目前没有待处理提醒")
            empty.setFlags(Qt.ItemFlag.NoItemFlags)
            self.list.addItem(empty)

    def notify_changed(self):
        self.refresh()
        if self.on_changed:
            self.on_changed()

    def complete_selected(self):
        reminder_id = self.selected_id()
        if reminder_id and self.store.complete(reminder_id):
            self.notify_changed()

    def snooze_selected(self):
        reminder_id = self.selected_id()
        if reminder_id and self.store.snooze(reminder_id, 10):
            self.notify_changed()

    def delete_selected(self):
        reminder_id = self.selected_id()
        if reminder_id and self.store.delete(reminder_id):
            self.notify_changed()
