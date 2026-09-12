from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QSpinBox,
    QVBoxLayout,
)

from .reminders import apply_reminder_theme


class SettingsDialog(QDialog):
    """Cute, single-page settings editor for the desktop pet."""

    def __init__(self, pet, parent=None):
        super().__init__(parent or pet)
        self.pet = pet
        self.setWindowTitle("小新设置中心")
        self.setMinimumWidth(440)
        apply_reminder_theme(self)

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 14, 16, 14)
        root.setSpacing(12)

        header = QLabel("小新设置中心\n调整他的日常节奏和小脾气")
        header.setObjectName("headerTitle")
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root.addWidget(header)

        form = QFormLayout()
        form.setVerticalSpacing(11)
        self.walk_enabled = QCheckBox("允许自动散步")
        self.walk_enabled.setChecked(pet.auto_walk_enabled)
        form.addRow("桌面巡逻", self.walk_enabled)

        self.walk_interval = QComboBox()
        for label, key in (("较少（约 90 秒）", "low"),
                           ("正常（约 45 秒）", "normal"),
                           ("较多（约 20 秒）", "high")):
            self.walk_interval.addItem(label, key)
        current = pet.walk_frequency if pet.walk_frequency in {"low", "normal", "high"} else "normal"
        self.walk_interval.setCurrentIndex(max(0, self.walk_interval.findData(current)))
        form.addRow("散步频率", self.walk_interval)

        self.sleep_after = QSpinBox()
        self.sleep_after.setRange(15, 600)
        self.sleep_after.setSingleStep(15)
        self.sleep_after.setSuffix(" 秒")
        self.sleep_after.setValue(int(pet.sleep_after))
        form.addRow("进入睡眠", self.sleep_after)

        self.dialogue_enabled = QCheckBox("显示对话气泡")
        self.dialogue_enabled.setChecked(pet.dialogue_enabled)
        form.addRow("对话", self.dialogue_enabled)

        self.voice_enabled = QCheckBox("启用顽皮童声")
        self.voice_enabled.setChecked(pet.voice_enabled)
        self.voice_enabled.setEnabled(pet.voice.available)
        form.addRow("声音", self.voice_enabled)

        self.chatter_frequency = QComboBox()
        for label, key in (("较少（约 90 秒）", "low"),
                           ("正常（约 45 秒）", "normal"),
                           ("较多（约 20 秒）", "high")):
            self.chatter_frequency.addItem(label, key)
        chatter = pet.chatter_level if pet.chatter_level in {"low", "normal", "high"} else "normal"
        self.chatter_frequency.setCurrentIndex(max(0, self.chatter_frequency.findData(chatter)))
        form.addRow("主动说话", self.chatter_frequency)
        root.addLayout(form)

        hint = QLabel("设置会自动保存。心情会根据你的点击、提醒完成和休息情况变化。")
        hint.setObjectName("feedback")
        hint.setWordWrap(True)
        root.addWidget(hint)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("保存设置")
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("取消")
        buttons.accepted.connect(self.apply_and_accept)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

    def apply_and_accept(self):
        self.pet.apply_user_settings({
            "auto_walk": self.walk_enabled.isChecked(),
            "walk_frequency": self.walk_interval.currentData(),
            "sleep_after": self.sleep_after.value(),
            "dialogue_enabled": self.dialogue_enabled.isChecked(),
            "voice_enabled": self.voice_enabled.isChecked(),
            "chatter_level": self.chatter_frequency.currentData(),
        })
        self.accept()
