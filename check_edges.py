"""Exercise edge gestures through Qt mouse events without moving the user's cursor.

Staged validation:
  runtime/python.exe check_edges.py --project D:/桌宠 --assets path/to/edge_v2
After deployment, run runtime/python.exe check_edges.py in the project directory.
The offscreen Qt platform avoids leaving test windows on the desktop.
"""
import argparse
import importlib.util
import math
import os
from pathlib import Path
import sys
import time

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DESKTOP_PET_DISABLE_AUDIO", "1")
from PySide6.QtCore import QEvent, QPoint, QPointF, Qt
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import QApplication


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument("--assets", type=Path)
    args = parser.parse_args()
    sys.path.insert(0, str(args.project.resolve()))
    module_path = Path(__file__).resolve().parent / "pet" / "window.py"
    spec = importlib.util.spec_from_file_location("pet._edge_validation_window", module_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    if args.assets:
        module.PetWindow.EDGE_ASSET_ROOT = args.assets.resolve()
    app = QApplication([])
    w = module.PetWindow()
    w.timer.stop()
    w.show()
    app.processEvents()
    area = app.primaryScreen().availableGeometry()
    checks = 0

    def center_window():
        w.clear_edge()
        w.set_state("Idle")
        w.move(area.center() - QPoint(w.width() // 2, w.height() // 2))
        w.hovered = False

    def mouse(kind, global_pos, button, buttons):
        local = QPointF(global_pos - w.pos())
        event = QMouseEvent(kind, local, QPointF(global_pos), button, buttons,
                            Qt.KeyboardModifier.NoModifier)
        assert QApplication.sendEvent(w, event)

    def drag_to(position, grip=None):
        # Use a point on the visible window when dragging away from an edge.
        visible = w.geometry().intersected(area)
        start = visible.center() if grip is None else w.pos() + grip
        offset = start - w.pos()
        target = position + offset
        mouse(QEvent.Type.MouseButtonPress, start, Qt.MouseButton.LeftButton,
              Qt.MouseButton.LeftButton)
        mouse(QEvent.Type.MouseMove, target, Qt.MouseButton.NoButton,
              Qt.MouseButton.LeftButton)
        assert w.state == "Drag" and w.edge_side is None
        mouse(QEvent.Type.MouseButtonRelease, target, Qt.MouseButton.LeftButton,
              Qt.MouseButton.NoButton)
        app.processEvents()

    def contact_matches(side, tolerance=0.51):
        point = w.edge_contact_global(side)
        border = w.screen_area()
        expected = {"left": border.left(), "right": border.right() + 1,
                    "top": border.top(), "bottom": border.bottom() + 1}[side]
        actual = point.x() if side in ("left", "right") else point.y()
        assert abs(actual - expected) <= tolerance, (side, actual, expected)

    def target_position(side, outside):
        x = area.center().x() - w.width() // 2
        y = area.center().y() - w.height() // 2
        if side == "left":
            x = area.left() - outside
        elif side == "right":
            x = area.right() + 1 - w.width() + outside
        elif side == "top":
            y = area.top() - outside
        else:
            y = area.bottom() + 1 - w.height() + outside
        return QPoint(x, y)

    try:
        for scale in (w.SCALE_MIN, 1.0, w.SCALE_MAX):
            center_window()
            w.set_pet_scale(scale)
            for side in ("left", "right", "top", "bottom"):
                for outside in (-12, 0, 45):
                    center_window()
                    size_before = w.size()
                    drag_to(target_position(side, outside))
                    assert w.edge_side == side, (scale, side, outside, w.edge_side)
                    assert w.state == "Edge" and w.edge_sticky
                    assert w.size() == size_before and w.scale_factor == scale
                    contact_matches(side)
                    head_width = w.edge_image_scale(side) * w.edge_poses[side]["head_width"]
                    assert math.isclose(head_width, w.edge_reference_head_width * scale, abs_tol=1e-7)
                    screen_before = w.edge_screen
                    w.tick()
                    assert w.edge_screen is screen_before
                    checks += 1

                # Sleep and hover must not replace the edge pose/state.
                module.system_idle_seconds = lambda: 999
                w.last_touch = time.monotonic() - 999
                w.tick()
                w.enterEvent(None)
                w.leaveEvent(None)
                assert w.state == "Edge" and w.edge_side == side
                module.system_idle_seconds = lambda: 0
                w.last_touch = time.monotonic()

                # Clicking holds the pose; dragging back inside exits it.
                point = w.geometry().intersected(area).center()
                mouse(QEvent.Type.MouseButtonPress, point, Qt.MouseButton.LeftButton,
                      Qt.MouseButton.LeftButton)
                mouse(QEvent.Type.MouseButtonRelease, point, Qt.MouseButton.LeftButton,
                      Qt.MouseButton.NoButton)
                assert w.state == "Edge" and w.edge_sticky
                drag_to(area.center() - QPoint(w.width() // 2, w.height() // 2))
                assert w.edge_side is None and not w.edge_sticky
                assert w.state in ("Idle", "Look")

        for side in ("left", "right", "top", "bottom"):
            center_window()
            w.set_pet_scale(1.0)
            drag_to(target_position(side, 0))
            before = w.edge_contact_global()
            for scale in (1.3, 0.7, 2.0, 1.0):
                w.set_pet_scale(scale)
                after = w.edge_contact_global()
                assert abs(after.x() - before.x()) <= 1.1
                assert abs(after.y() - before.y()) <= 1.1
                contact_matches(side)
                before = after
            # Grab includes the entire widget, so we can inspect its off-work-area part.
            image = w.grab().toImage()
            clipped_samples = 0
            visible_samples = 0
            for y in range(0, image.height(), 2):
                for x in range(0, image.width(), 2):
                    if not area.contains(w.pos() + QPoint(x, y)):
                        assert image.pixelColor(x, y).alpha() == 0, (side, x, y)
                        clipped_samples += 1
                    elif image.pixelColor(x, y).alpha() > 0:
                        visible_samples += 1
            assert visible_samples > 8, (side, "pose invisible")
            assert clipped_samples > 0, (side, "no out-of-area clipping tested")

        # At a corner the cursor's nearest edge wins, independently of dict order.
        center_window()
        w.reset_scale()
        drag_to(QPoint(area.left() - 15, area.top() - 15), QPoint(18, 30))
        assert w.edge_side == "left"
        center_window()
        drag_to(QPoint(area.left() - 15, area.top() - 15), QPoint(30, 18))
        assert w.edge_side == "top"
        print(f"PASS: {checks} edge release/overshoot gestures; head and window scale; "
              "four contact anchors; edge hold/click/hover/idle; drag-out; "
              "resize anchors; corner choice; work-area alpha clipping")
    finally:
        w.close()


if __name__ == "__main__":
    main()
