import random

from PySide6.QtCore import QRect, QRectF, Qt, QTimer
from PySide6.QtGui import QColor, QFont, QFontMetrics, QPainter, QPainterPath
from PySide6.QtWidgets import QWidget


DIALOGUES = {
    "greeting": ("嘿嘿，我来啦！", "今天也要陪我玩哦！", "桌面巡逻开始！"),
    "morning": ("早上好呀，今天也要加油！", "早呀，先伸个懒腰吧！", "新的一天开始啦！"),
    "noon": ("中午啦，记得好好吃饭！", "肚子是不是咕咕叫啦？", "休息一下再继续吧！"),
    "evening": ("晚上好，今天辛苦啦！", "忙了一天，休息一会儿吧！", "今晚也要开心哦！"),
    "late_night": ("已经很晚啦，该休息了。", "还不睡吗？眼睛会累哦！", "夜深啦，明天再继续吧！"),
    "idle": ("你怎么不动啦？", "要不要休息一下？", "我发现了一个秘密……算啦！",
             "桌面这么大，我去逛一圈。", "嘿嘿，我可没有偷懒。"),
    "hover": ("被我发现啦！", "鼠标在看我吗？", "想跟我玩吗？"),
    "click": ("哎哟！", "干嘛点我呀？", "嘿嘿，抓不到我！", "再点一下试试看？"),
    "angry": ("不要一直戳我啦！", "我真的要生气喽！", "哼，我记住你了！"),
    "drag": ("慢一点，我要晕啦！", "哇，我飞起来了！", "轻一点嘛！"),
    "sleep": ("我先睡一小会儿……", "呼……不要吵我哦。", "眼睛自己关上啦……"),
    "wake": ("我醒啦！", "刚才谁叫我？", "精神满满！"),
    "walk": ("去那边看看！", "散步时间到！", "桌面巡逻中。"),
    "edge_left": ("我从左边看到你啦！", "这里藏得住我吗？", "偷偷看一眼……"),
    "edge_right": ("右边也能探头哦！", "嘿嘿，在找我吗？", "我躲在这里！"),
    "edge_top": ("倒着看也很有趣！", "下面发生什么啦？", "我可抓得很牢！"),
    "edge_bottom": ("拉我一把嘛！", "我扒住啦！", "这里的风景不错哦。"),
    "focus_start": ("专注时间开始，我先安静一会儿。", "你认真忙吧，我会乖乖待着！", "开始专注，我来帮你看时间。"),
    "focus_cancel": ("专注提前结束啦。", "先停一下也没关系。", "好吧，休息一会儿！"),
    "focus_complete": ("专注完成啦，起来活动一下！", "时间到！做得很好哦！", "任务完成，休息一下吧！"),
    "reminder_done": ("收到，已经完成啦！", "好耶，这件事处理完啦！", "记下来啦，继续加油！"),
}


class DialogueLibrary:
    def __init__(self):
        self.last = {}

    def choose(self, event):
        choices = DIALOGUES.get(event, DIALOGUES["idle"])
        previous = self.last.get(event)
        available = [text for text in choices if text != previous] or list(choices)
        text = random.choice(available)
        self.last[event] = text
        return text


class SpeechBubble(QWidget):
    MAX_TEXT_WIDTH = 190

    def __init__(self):
        super().__init__(None)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint |
                            Qt.WindowType.WindowStaysOnTopHint |
                            Qt.WindowType.Tool |
                            Qt.WindowType.WindowTransparentForInput |
                            Qt.WindowType.WindowDoesNotAcceptFocus)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.normal_font = QFont("Microsoft YaHei UI", 10, QFont.Weight.Normal)
        self.reminder_font = QFont("Microsoft YaHei UI", 10, QFont.Weight.Bold)
        self.font = self.normal_font
        self.emphasis = False
        self.text = ""
        self.tail_down = True
        self.tail_x = 30
        self._pet_rect = QRect()
        self._area = QRect()
        self.hide_timer = QTimer(self)
        self.hide_timer.setSingleShot(True)
        self.hide_timer.timeout.connect(self.hide)

    def show_text(self, text, pet_rect, area, duration_ms=3200, emphasis=False):
        self.text = text
        self.emphasis = bool(emphasis)
        self.font = self.reminder_font if self.emphasis else self.normal_font
        metrics = QFontMetrics(self.font)
        text_width = 220 if self.emphasis else self.MAX_TEXT_WIDTH
        bounds = metrics.boundingRect(QRect(0, 0, text_width, 1000),
                                      Qt.TextFlag.TextWordWrap, text)
        self.setFixedSize(max(98, bounds.width() + 40), max(55, bounds.height() + 34))
        self.follow(pet_rect, area)
        self.show()
        self.raise_()
        if duration_ms > 0:
            self.hide_timer.start(duration_ms)
        else:
            self.hide_timer.stop()
        self.update()

    def follow(self, pet_rect, area):
        if pet_rect.isNull() or area.isNull():
            return
        self._pet_rect, self._area = QRect(pet_rect), QRect(area)
        gap = 3
        above_y = pet_rect.top() - self.height() - gap
        self.tail_down = above_y >= area.top()
        y = above_y if self.tail_down else pet_rect.bottom() + 1 + gap
        x = pet_rect.center().x() - self.width() // 2
        x = max(area.left(), min(x, area.right() - self.width() + 1))
        y = max(area.top(), min(y, area.bottom() - self.height() + 1))
        self.move(x, y)
        pet_center = pet_rect.center().x() - x
        self.tail_x = max(19, min(pet_center, self.width() - 19))
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        tail = 10
        body = QRectF(3, 2 if self.tail_down else tail + 1,
                      self.width() - 6, self.height() - tail - 4)
        bubble = QPainterPath()
        bubble.addRoundedRect(body, 14, 14)
        arrow = QPainterPath()
        if self.tail_down:
            arrow.moveTo(self.tail_x - 9, body.bottom() - 3)
            arrow.lineTo(self.tail_x, self.height() - 1)
            arrow.lineTo(self.tail_x + 8, body.bottom() - 3)
        else:
            arrow.moveTo(self.tail_x - 9, body.top() + 3)
            arrow.lineTo(self.tail_x, 1)
            arrow.lineTo(self.tail_x + 8, body.top() + 3)
        arrow.closeSubpath()
        # Union removes the join between the rounded body and its pointer.
        shape = bubble.united(arrow).simplified()
        painter.setPen(Qt.PenStyle.NoPen)
        fill = QColor(255, 229, 171, 252) if self.emphasis else QColor(255, 237, 232, 250)
        painter.setBrush(fill)
        painter.drawPath(shape)
        painter.setPen(QColor(72, 48, 42) if self.emphasis else QColor(121, 99, 103))
        painter.setFont(self.font)
        painter.drawText(body.adjusted(14, 7, -14, -7),
                         Qt.AlignmentFlag.AlignCenter | Qt.TextFlag.TextWordWrap,
                         self.text)
