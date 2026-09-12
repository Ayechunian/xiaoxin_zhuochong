"""Finite, silent validation for persistent reminders and alert styling."""
import json
import os
from pathlib import Path
import sys
import tempfile
import time

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DESKTOP_PET_DISABLE_AUDIO", "1")

from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication

sys.path.insert(0, str(Path(__file__).resolve().parent))
from pet.dialogue import DIALOGUES
from pet.reminders import ReminderCenterDialog, ReminderStore
from pet.window import PetWindow


app = QApplication([])
with tempfile.TemporaryDirectory() as folder:
    path = Path(folder) / "reminders.json"
    store = ReminderStore(path)
    due = store.add("提交测试报告", time.time() - 2)
    future = store.add("十分钟后喝水", time.time() + 600)
    recurring = store.add("每天拉伸", time.time() - 2, "daily")
    assert path.exists()
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["version"] == 1 and len(payload["reminders"]) == 3

    reloaded = ReminderStore(path)
    assert [item["id"] for item in reloaded.due()] == [due["id"], recurring["id"]]
    assert len(reloaded.pending()) == 3
    assert reloaded.complete(recurring["id"])
    assert reloaded.get(recurring["id"])["status"] == "pending"
    assert reloaded.get(recurring["id"])["due_at"] > time.time()

    w = PetWindow()
    w.timer.stop()
    w.reminder_store = reloaded
    w.show()
    app.processEvents()
    assert w.check_reminders()
    app.processEvents()
    assert w.active_reminder["id"] == due["id"]
    assert w.bubble.isVisible() and w.bubble.emphasis
    assert w.bubble.font.weight() == QFont.Weight.Bold
    assert not w.bubble.hide_timer.isActive()
    assert "提醒：提交测试报告" in w.bubble.text
    assert "点击我确认完成" in w.bubble.text

    w.acknowledge_active_reminder()
    app.processEvents()
    assert w.active_reminder is None
    assert reloaded.get(due["id"])["status"] == "completed"
    assert w.bubble.text in DIALOGUES["reminder_done"]
    assert not w.bubble.emphasis and w.bubble.hide_timer.isActive()

    assert reloaded.snooze(future["id"], 10)
    assert reloaded.get(future["id"])["due_at"] > time.time()

    added = []
    center = ReminderCenterDialog(reloaded, on_added=added.append)
    assert center.tabs.count() == 2
    assert center.tabs.tabText(0) == "添加提醒"
    assert center.tabs.tabText(1).startswith("管理提醒")
    center.content.setText("页面内新建提醒")
    center.preset.setCurrentIndex(0)
    center.add_reminder()
    assert added and added[0]["text"] == "页面内新建提醒"
    assert "已添加" in center.add_feedback.text()
    assert len(reloaded.pending()) == 3
    center.close()

    assert reloaded.delete(future["id"])
    assert reloaded.get(future["id"]) is None
    w.close()

print("PASS: atomic JSON persistence; due detection; persistent bold dark alert; "
      "click acknowledgement; daily repeat; snooze/delete; single reminder-center page")
