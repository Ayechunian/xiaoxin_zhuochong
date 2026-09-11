"""Render the actual widget poses, never capture the user's desktop."""
import argparse
import importlib.util
import os
from pathlib import Path
import sys
import time
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PySide6.QtCore import QPoint, QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QFontDatabase, QImage, QPainter, QPen
from PySide6.QtWidgets import QApplication

parser = argparse.ArgumentParser()
parser.add_argument("--project", type=Path, default=Path(__file__).resolve().parent)
args = parser.parse_args()
root = Path(__file__).resolve().parent
sys.path.insert(0, str(args.project.resolve()))
spec = importlib.util.spec_from_file_location("pet._edge_preview_window", root / "pet" / "window.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
module.PetWindow.EDGE_ASSET_ROOT = root / "assets" / "poses" / "edge_v2"
app = QApplication([])
QFontDatabase.addApplicationFont("C:/Windows/Fonts/msyh.ttc")
QFontDatabase.addApplicationFont("C:/Windows/Fonts/msyhbd.ttc")
w = module.PetWindow()
w.timer.stop()
w.show()
app.processEvents()
area = w.screen_area()
image = QImage(1800, 680, QImage.Format.Format_ARGB32_Premultiplied)
image.fill(QColor("#edf1f5"))
p = QPainter(image)
p.setRenderHint(QPainter.RenderHint.Antialiasing)
p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
p.setPen(QColor("#152334"))
p.setFont(QFont("Microsoft YaHei", 22, QFont.Weight.Bold))
p.drawText(QRectF(28, 16, 1740, 54), "屏幕边缘互动 · 实际绘制预览")
p.setFont(QFont("Microsoft YaHei", 11))
p.setPen(QColor("#556477"))
p.drawText(QRectF(28, 78, 1740, 30), "统一用户缩放 100%，画面放大 3 倍对比。深色边线表示屏幕边缘，使用程序真实锚点和裁切。")

labels = [(None, "普通待机", "角色大小对照"), ("left", "左侧探头", "手扶左边缘，脸朝屏幕内"),
          ("right", "右侧探头", "手扶右边缘，脸朝屏幕内"), ("top", "顶部倒挂", "双手抓住顶边，脑袋垂下"),
          ("bottom", "底部扒边", "双手搭在下边缘，抬头看")]
for index, (side, title, subtitle) in enumerate(labels):
    left = 18 + index * 357
    viewport = QRectF(left + 17, 198, 305, 356)
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor("#ffffff"))
    p.drawRoundedRect(QRectF(left, 124, 340, 526), 12, 12)
    p.setPen(QColor("#152334"))
    p.setFont(QFont("Microsoft YaHei", 14, QFont.Weight.Bold))
    p.drawText(QRectF(left + 15, 143, 310, 32), Qt.AlignmentFlag.AlignCenter, title)
    p.fillRect(viewport, QColor("#f5f7fa"))
    w.clear_edge()
    w.move(area.center() - QPoint(w.width() // 2, w.height() // 2))
    if side:
        w.perch_on_edge(side, time.monotonic(), sticky=True)
        _, contact = w.edge_layout(side)
        if side == "left":
            target = QPointF(viewport.left(), viewport.center().y())
        elif side == "right":
            target = QPointF(viewport.right(), viewport.center().y())
        elif side == "top":
            target = QPointF(viewport.center().x(), viewport.top())
        else:
            target = QPointF(viewport.center().x(), viewport.bottom())
        position = target - contact * 3
    else:
        w.set_state("Idle")
        w.state_tick = 0
        position = viewport.center() - QPointF(w.width() * 1.5, w.height() * 1.5)
    app.processEvents()
    capture = QImage(w.width() * 3, w.height() * 3, QImage.Format.Format_ARGB32_Premultiplied)
    capture.setDevicePixelRatio(3)
    capture.fill(Qt.GlobalColor.transparent)
    widget_painter = QPainter(capture)
    w.render(widget_painter, QPoint())
    widget_painter.end()
    p.save()
    p.setClipRect(viewport)
    p.drawImage(QRectF(position.x(), position.y(), w.width() * 3, w.height() * 3), capture)
    p.restore()
    p.setPen(QPen(QColor("#334155"), 3))
    if side == "left":
        p.drawLine(viewport.topLeft(), viewport.bottomLeft())
    elif side == "right":
        p.drawLine(viewport.topRight(), viewport.bottomRight())
    elif side == "top":
        p.drawLine(viewport.topLeft(), viewport.topRight())
    elif side == "bottom":
        p.drawLine(viewport.bottomLeft(), viewport.bottomRight())
    p.setFont(QFont("Microsoft YaHei", 10))
    p.setPen(QColor("#556477"))
    p.drawText(QRectF(left + 10, 585, 320, 34), Qt.AlignmentFlag.AlignCenter, subtitle)
p.end()
w.close()
output = root / "edge_preview.png"
assert image.save(str(output))
print(output)
