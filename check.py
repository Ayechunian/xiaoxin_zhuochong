"""Finite interaction and rendering check; no persistent desktop window."""
import hashlib
import os
import time
import sys
from pathlib import Path
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DESKTOP_PET_DISABLE_AUDIO", "1")
from PySide6.QtCore import Qt, QPoint
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication
sys.path.insert(0, str(Path(__file__).resolve().parent))
import pet.window as module
from pet.art import CANVAS_HEIGHT, CANVAS_WIDTH, FRAME_COUNTS
from PySide6.QtGui import QImage

app = QApplication([])
w = module.PetWindow(); w.timer.stop(); w.show(); app.processEvents()
assert w.windowFlags() & Qt.WindowType.WindowStaysOnTopHint
assert w.testAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
assert set(w.edge_frames) == {'left', 'right', 'top', 'bottom'}
assert all(not image.isNull() and image.hasAlphaChannel() for image in w.edge_frames.values())
for state, frames in w.frames.items():
    assert len(frames) == FRAME_COUNTS[state]
    assert all(not im.isNull() and im.hasAlphaChannel() for im in frames)
    assert all(im.width() == CANVAS_WIDTH and im.height() == CANVAS_HEIGHT for im in frames)
    w.state = state; w.repaint(); app.processEvents()
assert w.frames['Idle'][0] != w.frames['Idle'][20]
walk_keyframes = [w.frames['Walk'][index] for index in (0, 2, 4, 6)]
assert all(walk_keyframes[index] != walk_keyframes[(index + 1) % 4] for index in range(4))

pose_root = Path(__file__).resolve().parent / 'assets' / 'poses'
walk_sources = [QImage(str(pose_root / f'walk_fixed_{index}.png')) for index in range(1, 5)]
assert all(not image.isNull() and image.hasAlphaChannel() for image in walk_sources)
walk_hashes = [
    hashlib.sha256((pose_root / f'walk_fixed_{index}.png').read_bytes()).hexdigest()
    for index in range(1, 5)
]
assert len(set(walk_hashes)) == 4
for image in walk_sources:
    transparent_samples = 0
    for x, y in ((0, 0), (image.width() - 1, 0), (0, image.height() - 1), (image.width() - 1, image.height() - 1)):
        transparent_samples += image.pixelColor(x, y).alpha() == 0
    assert transparent_samples == 4

def region_difference(first, second, top_ratio):
    top = round(first.height() * top_ratio)
    different = 0
    total = first.width() * (first.height() - top)
    for y in range(top, first.height(), 3):
        for x in range(0, first.width(), 3):
            a, b = first.pixelColor(x, y), second.pixelColor(x, y)
            delta = (abs(a.red() - b.red()) + abs(a.green() - b.green()) +
                     abs(a.blue() - b.blue()) + abs(a.alpha() - b.alpha()))
            if delta > 90:
                different += 9
    return different / total

walk_leg_differences = [region_difference(walk_keyframes[index], walk_keyframes[(index + 1) % 4], 0.48)
                        for index in range(4)]
assert min(walk_leg_differences) > 0.08
center = QPoint(w.width() // 2, w.height() // 2)
QTest.mouseClick(w, Qt.MouseButton.LeftButton, pos=center)
assert w.state == 'Click'
for _ in range(3):
    QTest.mouseClick(w, Qt.MouseButton.LeftButton, pos=center)
assert w.state == 'Angry'
area = w.screen_area()
w.move(area.center() - QPoint(w.width() // 2, w.height() // 2))
QTest.mousePress(w, Qt.MouseButton.LeftButton, pos=center)
QTest.mouseMove(w, center + QPoint(25, 20))
assert w.state == 'Drag'
QTest.mouseRelease(w, Qt.MouseButton.LeftButton, pos=center + QPoint(25, 20))
assert w.state == 'Idle' and w.press is None
module.system_idle_seconds = lambda: 90
w.last_touch = time.monotonic()-90; w.tick(); assert w.state == 'Sleep'
module.system_idle_seconds = lambda: 0
w.hovered = False; w.tick(); assert w.state == 'Idle'
w.enterEvent(None); assert w.state == 'Look'
w.leaveEvent(None); assert w.state == 'Idle'
w.next_walk = 0; w.tick(); assert w.state == 'Walk'
w.until = 0; w.tick(); assert w.state == 'Idle'
base_size = w.size()
w.adjust_scale(w.SCALE_STEP)
assert w.width() > base_size.width() and w.height() > base_size.height()
w.set_pet_scale(99)
assert w.scale_factor == w.SCALE_MAX
w.set_pet_scale(-99)
assert w.scale_factor == w.SCALE_MIN
w.reset_scale()
assert w.size() == base_size and w.scale_factor == 1.0
w.move(-9999,-9999); w.keep_visible()
area = w.screen_area()
assert w.x() < area.left()
assert w.x() + w.width() >= area.left() + w.visible_margin()
w.move(9999, w.y()); w.keep_visible()
assert w.x() + w.width() > area.right()
assert w.x() <= area.right() + 1 - w.visible_margin()
w.direction = -1
w.move(area.left(), area.bottom() - w.height() + 1)
w.set_state('Walk')
w.until = time.monotonic() + 2
w.edge_until = 0
w.tick()
assert w.state == 'Edge' and w.direction == 1 and w.x() < area.left()
w.clear_edge()
w.edge_until = 0
w.direction = 1
w.move(area.right() - w.width() + 1, area.bottom() - w.height() + 1)
w.set_state('Walk')
w.until = time.monotonic() + 2
w.tick()
assert w.state == 'Edge' and w.direction == -1 and w.x() + w.width() > area.right()
for side in ('left', 'right', 'top', 'bottom'):
    w.clear_edge()
    w.move(area.center() - QPoint(w.width() // 2, w.height() // 2))
    size_before_edge, scale_before_edge = w.size(), w.scale_factor
    w.perch_on_edge(side, time.monotonic(), sticky=True)
    assert w.edge_side == side and w.edge_sticky
    assert w.state == 'Edge' and w.size() == size_before_edge and w.scale_factor == scale_before_edge
    assert abs(w.edge_image_scale(side) * w.edge_poses[side]['head_width'] - 65.0) < 0.01
    if side == 'left':
        assert w.x() < area.left()
    elif side == 'right':
        assert w.x() + w.width() > area.right()
    elif side == 'top':
        assert w.y() < area.top()
    elif side == 'bottom':
        assert w.y() + w.height() > area.bottom()
    w.repaint(); app.processEvents()
w.close()
print('PASS: 80 high-resolution transparent frames; blink; user-provided four-pose gait; hover/look; click/angry; drag; sleep/wake; resize limits; edge PNG poses; edge perch; bounds')
