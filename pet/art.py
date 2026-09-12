import math

from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QColor, QFont, QImage, QPainter, QPen
from .paths import resource_path

# Logical window size. Frames stay 4x larger so user scaling remains crisp.
WIDTH, HEIGHT = 110, 130
CANVAS_WIDTH, CANVAS_HEIGHT = WIDTH * 4, HEIGHT * 4
STATES = ("Idle", "Walk", "Turn", "Sleep", "Drag", "Click", "Look", "Angry")
FRAME_COUNTS = {"Idle": 4, "Walk": 8, "Turn": 6, "Sleep": 16, "Drag": 8,
                "Click": 8, "Look": 8, "Angry": 8}


def _load_poses():
    root = resource_path("assets", "poses")
    names = ("idle", "blink", "sleep", "drag",
             "click", "look", "angry")
    poses = {}
    for name in names:
        path = root / f"{name}.png"
        if not path.exists():
            raise RuntimeError(f"缺少动作素材：{path}")
        image = QImage(str(path))
        if image.isNull() or not image.hasAlphaChannel():
            raise RuntimeError(f"动作素材无效或没有透明通道：{path}")
        poses[name] = image
    return poses


_POSES = _load_poses()


def _load_sheet_frames():
    root = resource_path("assets", "sheet_animations")
    groups = {
        "idle": 4,
        "right_walk": 8,
        "turn": 6,
    }
    animations = {}
    for name, count in groups.items():
        frames = []
        for index in range(1, count + 1):
            path = root / name / f"{index:02}.png"
            if not path.exists():
                raise RuntimeError(f"缺少分镜动作素材：{path}")
            image = QImage(str(path))
            if image.isNull() or not image.hasAlphaChannel():
                raise RuntimeError(f"分镜动作素材无效或没有透明通道：{path}")
            frames.append(image)
        animations[name] = frames
    return animations


_SHEET_FRAMES = _load_sheet_frames()


def frame(state, index, direction=1, turn_direction=-1):
    """Return one high-resolution animation frame for a behavior state."""
    sheet_state = state in ("Idle", "Walk", "Turn")
    if state == "Idle":
        source = _SHEET_FRAMES["idle"][index % 4]
    elif state == "Walk":
        source = _SHEET_FRAMES["right_walk"][index % 8]
        if direction < 0:
            source = source.mirrored(True, False)
    elif state == "Turn":
        turn_index = index if turn_direction < 0 else (5 - index)
        source = _SHEET_FRAMES["turn"][turn_index % 6]
    elif state == "Sleep":
        pose_name = "sleep"
        source = _POSES[pose_name]
    elif state == "Drag":
        pose_name = "drag"
        source = _POSES[pose_name]
    elif state == "Click":
        pose_name = "click"
        source = _POSES[pose_name]
    elif state == "Look":
        pose_name = "look"
        source = _POSES[pose_name]
    elif state == "Angry":
        pose_name = "angry"
        source = _POSES[pose_name]
    else:
        raise ValueError(f"未知动画状态：{state}")

    image = QImage(CANVAS_WIDTH, CANVAS_HEIGHT,
                   QImage.Format.Format_ARGB32_Premultiplied)
    image.fill(Qt.GlobalColor.transparent)
    p = QPainter(image)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

    phase = math.sin(index * math.pi / 4)
    x_shift = phase * 5 if state == "Look" else 0
    y_shift = 0
    angle = 0
    scale = 1.0
    if state == "Idle" and not sheet_state:
        y_shift = phase * 2
        scale = 1.0 + phase * 0.004
    elif state == "Walk" and not sheet_state:
        y_shift = -abs(phase) * 9
    elif state == "Sleep":
        y_shift = 24 + phase * 3
    elif state == "Drag":
        angle = phase * 4
        y_shift = phase * 5
    elif state == "Click":
        y_shift = -abs(phase) * 28
        scale = 1.0 + abs(phase) * 0.045
    elif state == "Look":
        angle = phase * 1.5
    elif state == "Angry":
        x_shift = 5 if index % 2 == 0 else -5

    sprite = source.scaled(CANVAS_WIDTH - 24, CANVAS_HEIGHT - 30,
                           Qt.AspectRatioMode.KeepAspectRatio,
                           Qt.TransformationMode.SmoothTransformation)
    p.translate(CANVAS_WIDTH / 2 + x_shift, CANVAS_HEIGHT / 2 + y_shift)
    p.rotate(angle); p.scale(scale, scale)
    p.drawImage(QPointF(-sprite.width() / 2, -sprite.height() / 2), sprite)
    p.resetTransform()

    if state == "Sleep":
        p.setPen(QPen(QColor(45, 67, 130, 180), 5))
        p.setFont(QFont("Arial", 38 + (index % 3) * 5, QFont.Weight.Bold))
        p.drawText(335, 105 - (index % 4) * 8, "Z")
    p.end()
    return image
