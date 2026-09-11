"""Finite, silent validation for focus mode and time-based reactions."""
import os
from datetime import datetime as RealDatetime
from pathlib import Path
import sys
import time

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DESKTOP_PET_DISABLE_AUDIO", "1")

from PySide6.QtCore import QSettings, QTemporaryDir
from PySide6.QtWidgets import QApplication

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pet.window as module
from pet.dialogue import DIALOGUES


app = QApplication([])
w = module.PetWindow()
w.timer.stop()
w.show()
app.processEvents()
temporary = QTemporaryDir()
assert temporary.isValid()
w.settings = QSettings(temporary.filePath("focus-test.ini"), QSettings.Format.IniFormat)
w.focus_end_epoch = 0.0
w.last_late_night_date = ""
real_datetime = module.datetime

try:
    w.start_focus(25)
    assert w.focus_active()
    assert 1498 <= w.focus_remaining_seconds() <= 1500
    assert w.bubble.text in DIALOGUES["focus_start"]
    assert w.settings.contains("focus/end_epoch")

    w.hovered = False
    w.next_walk = 0
    w.set_state("Idle")
    w.tick()
    assert w.state == "Idle", "focus mode must suppress random walking"

    remaining = w.show_focus_remaining()
    assert remaining and "专注中" in remaining and "分" in remaining

    for side in ("left", "right", "top", "bottom"):
        w.clear_edge()
        w.perch_on_edge(side, time.monotonic(), sticky=True)
        app.processEvents()
        assert w.state == "Edge" and w.edge_side == side
        assert "专注中" in w.bubble.text
        assert not w.bubble.emphasis and not w.bubble.hide_timer.isActive()
        previous = w.focus_remaining_seconds()
        w.focus_end_epoch -= 1.1
        w.tick()
        assert w.focus_remaining_seconds() < previous
        assert w.edge_focus_last_second == w.focus_remaining_seconds()
        assert "专注中" in w.bubble.text

    w.clear_edge()
    w.show_focus_remaining()
    assert w.bubble.hide_timer.isActive()

    w.focus_end_epoch = time.time() - 1
    w.tick()
    assert not w.focus_active() and not w.settings.contains("focus/end_epoch")
    assert w.state == "Click"
    assert w.bubble.text in DIALOGUES["focus_complete"]

    class FakeDatetime:
        current = RealDatetime(2026, 9, 11, 23, 17)

        @classmethod
        def now(cls):
            return cls.current

    module.datetime = FakeDatetime
    w.last_clock_minute = None
    w.last_late_night_date = ""
    w.maybe_time_reaction()
    assert w.bubble.text in DIALOGUES["late_night"]
    assert w.last_late_night_date == "2026-09-11"

    FakeDatetime.current = RealDatetime(2026, 9, 11, 14, 0)
    w.last_clock_minute = None
    w.maybe_time_reaction()
    assert "14 点" in w.bubble.text

    FakeDatetime.current = RealDatetime(2026, 9, 11, 8, 30)
    w.dialogue_cooldown_until = 0.0
    w.startup_message()
    assert w.bubble.text in DIALOGUES["morning"]

    w.start_focus(15)
    w.stop_focus(completed=False)
    assert not w.focus_active()
    assert w.bubble.text in DIALOGUES["focus_cancel"]
    print("PASS: focus presets; persisted deadline; quiet mode; remaining time; "
          "four-edge live countdown; completion/cancel; morning greeting; "
          "hourly and late-night reactions")
finally:
    module.datetime = real_datetime
    w.close()
