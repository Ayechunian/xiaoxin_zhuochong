"""Finite, silent validation for speech bubbles and dialogue state triggers."""
import os
from pathlib import Path
import sys
import time

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DESKTOP_PET_DISABLE_AUDIO", "1")

from PySide6.QtCore import QPoint
from PySide6.QtWidgets import QApplication

sys.path.insert(0, str(Path(__file__).resolve().parent))
from pet.dialogue import DIALOGUES, DialogueLibrary
from pet.window import PetWindow


app = QApplication([])
w = PetWindow()
w.timer.stop()
w.show()
app.processEvents()
had_dialogue_setting = w.settings.contains("dialogue/enabled")
previous_dialogue_setting = w.settings.value("dialogue/enabled")

assert not w.voice.available and not w.voice_enabled
assert set(DIALOGUES) >= {
    "greeting", "idle", "hover", "click", "angry", "drag", "sleep",
    "wake", "walk", "edge_left", "edge_right", "edge_top", "edge_bottom",
}

library = DialogueLibrary()
for event, choices in DIALOGUES.items():
    first = library.choose(event)
    second = library.choose(event)
    assert first in choices and second in choices
    if len(choices) > 1:
        assert first != second

text = w.talk("click", force=True)
app.processEvents()
assert text in DIALOGUES["click"]
assert w.bubble.isVisible() and w.bubble.text == text
area = w.screen_area()
assert area.contains(w.bubble.frameGeometry())

for side in ("left", "right", "top", "bottom"):
    w.clear_edge()
    w.move(area.center() - QPoint(w.width() // 2, w.height() // 2))
    w.perch_on_edge(side, time.monotonic(), sticky=True)
    app.processEvents()
    assert w.bubble.text in DIALOGUES[f"edge_{side}"]
    assert area.contains(w.bubble.frameGeometry()), (side, w.bubble.frameGeometry(), area)

w.set_dialogue_enabled(False)
app.processEvents()
assert not w.bubble.isVisible()
assert w.talk("click", force=True) is None
w.dialogue_enabled = True
if had_dialogue_setting:
    w.settings.setValue("dialogue/enabled", previous_dialogue_setting)
else:
    w.settings.remove("dialogue/enabled")
w.close()
print("PASS: event dialogue library; repeat avoidance; bubble display; four-edge placement; silent test mode")
