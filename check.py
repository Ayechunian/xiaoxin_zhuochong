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
assert w.ANIMATION_TICK_MS == 20
assert w.FRAME_DURATIONS_MS["Walk"] == 125
assert sum(w.WALK_FRAME_DURATIONS_MS) == 1000
assert w.WALK_SPEED_PX_PER_SECOND == 48
assert w.IDLE_BLINK_CLOSED_MS == 95
assert w.IDLE_BLINK_OPEN_MS == 110
assert w.timer.interval() == w.ANIMATION_TICK_MS
assert w.windowFlags() & Qt.WindowType.WindowStaysOnTopHint
assert w.testAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
assert set(w.edge_frames) == {'left', 'right', 'top', 'bottom'}
assert all(not image.isNull() and image.hasAlphaChannel() for image in w.edge_frames.values())
for state, frames in w.frames.items():
    assert len(frames) == FRAME_COUNTS[state]
    assert all(not im.isNull() and im.hasAlphaChannel() for im in frames)
    assert all(im.width() == CANVAS_WIDTH and im.height() == CANVAS_HEIGHT for im in frames)
    w.state = state; w.repaint(); app.processEvents()
assert w.frames['Idle'][0] != w.frames['Idle'][1]
old_choice = module.random.choice
module.random.choice = lambda choices: 1
w.set_state('Idle')
w.next_idle_blink = 0
w.update_idle_blink(1.0)
assert w.idle_blink_phase == 1
w.idle_blink_until = 1.0
w.update_idle_blink(1.0)
assert w.idle_blink_phase == 0
module.random.choice = old_choice
walk_keyframes = w.frames['Walk']
assert len(walk_keyframes) == 8
assert len(w.walk_left_frames) == 8
assert len(w.turn_right_frames) == 6
assert all(walk_keyframes[index] != walk_keyframes[(index + 1) % 8] for index in range(8))
assert all(w.walk_left_frames[index] != w.walk_left_frames[(index + 1) % 8]
           for index in range(8))
assert all(w.frames['Turn'][index] != w.frames['Turn'][(index + 1) % 6]
           for index in range(6))

pose_root = Path(__file__).resolve().parent / 'assets' / 'poses'
sheet_root = Path(__file__).resolve().parent / 'assets' / 'sheet_animations'
sheet_groups = {'right_walk': 8, 'turn': 6, 'idle': 4}
for group, count in sheet_groups.items():
    paths = [sheet_root / group / f'{index:02}.png' for index in range(1, count + 1)]
    assert all(path.exists() for path in paths)
    images = [QImage(str(path)) for path in paths]
    assert all(not image.isNull() and image.hasAlphaChannel() for image in images)
    assert all(image.size() == images[0].size() for image in images)
    hashes = [hashlib.sha256(path.read_bytes()).hexdigest() for path in paths]
    assert len(set(hashes)) == count

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

walk_leg_differences = [region_difference(walk_keyframes[index], walk_keyframes[(index + 1) % 8], 0.48)
                        for index in range(8)]
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
w.direction = 1
old_choice = module.random.choice
module.random.choice = lambda sequence: 1
w.next_walk = 0; w.tick(); assert w.state == 'Walk'
module.random.choice = old_choice
w.until = 0; w.tick(); assert w.state == 'Idle'
w.turn_target = -1
w.set_state('Turn'); w.state_tick = FRAME_COUNTS['Turn']; w.tick()
assert w.state == 'Walk' and w.direction == -1
w.set_state('Idle')
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
print('PASS: 26 extracted sheet frames; canonical 8-frame walk with coordinated timing; mirrored direction; turn transition; idle blink; hover/look; click/angry; drag; sleep/wake; resize limits; edge PNG poses; edge perch; bounds')
