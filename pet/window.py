import ctypes
import json
import random
import time
from datetime import datetime

from PySide6.QtCore import Qt, QTimer, QPoint, QPointF, QRectF, QSettings
from PySide6.QtGui import QColor, QCursor, QFont, QImage, QPainter
from PySide6.QtWidgets import QApplication, QMenu, QWidget

from .art import FRAME_COUNTS, HEIGHT, STATES, WIDTH, frame
from .dialogue import DialogueLibrary, SpeechBubble
from .paths import resource_path, user_data_file
from .reminders import ReminderCenterDialog, ReminderStore
from .settings_dialog import SettingsDialog
from .voice import VoiceEngine


def system_idle_seconds():
    class LastInput(ctypes.Structure):
        _fields_ = [("cbSize", ctypes.c_uint), ("dwTime", ctypes.c_uint)]

    info = LastInput(); info.cbSize = ctypes.sizeof(info)
    try:
        if ctypes.windll.user32.GetLastInputInfo(ctypes.byref(info)):
            ctypes.windll.kernel32.GetTickCount.restype = ctypes.c_uint
            return ((ctypes.windll.kernel32.GetTickCount() - info.dwTime) & 0xffffffff) / 1000
    except (AttributeError, OSError):
        pass
    return None


class PetWindow(QWidget):
    SCALE_MIN = 0.55
    SCALE_MAX = 2.0
    SCALE_STEP = 0.15
    EDGE_VISIBLE_RATIO = 0.64
    EDGE_BOTTOM_VISIBLE_RATIO = 0.62
    EDGE_PAUSE_SECONDS = 1.4
    EDGE_TRIGGER_DISTANCE = 28
    EDGE_ASSET_ROOT = resource_path("assets", "poses", "edge_v2")
    CHATTER_RANGES = {
        "low": (90, 150),
        "normal": (45, 90),
        "high": (20, 45),
    }
    WALK_RANGES = CHATTER_RANGES
    MOODS = {
        "calm": ("·", QColor("#78a9c7"), "平静"),
        "happy": ("♥", QColor("#ef7770"), "开心"),
        "playful": ("♪", QColor("#f2bd45"), "调皮"),
        "sleepy": ("Z", QColor("#8c83c6"), "困倦"),
        "grumpy": ("!", QColor("#e76e55"), "小生气"),
    }

    def __init__(self):
        super().__init__()
        self.setWindowTitle("小新桌宠")
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint |
                            Qt.WindowType.WindowStaysOnTopHint |
                            Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setMouseTracking(True)
        self.scale_factor = 1.0
        self.setFixedSize(WIDTH, HEIGHT)
        self.frames = {state: [frame(state, i) for i in range(FRAME_COUNTS[state])]
                       for state in STATES}
        self.edge_frames = self.load_edge_frames()
        self.state = "Idle"
        self.state_tick = 0
        self.last_touch = time.monotonic()
        self.until = 0.0
        self.next_walk = 0.0
        self.direction = 1
        self.edge_until = 0.0
        self.edge_side = None
        self.edge_focus_last_second = None
        self.edge_sticky = False
        self.edge_screen = None
        self._edge_candidate_screen = None
        self.press = None
        self.dragging = False
        self.hovered = False
        self.menu_open = False
        self.click_times = []
        self.sleep_after = 60
        self.settings = QSettings("DesktopPet", "CartoonPet")
        self.sleep_after = max(15, self.settings.value("behavior/sleep_after", 60, type=int))
        self.auto_walk_enabled = self.settings.value("behavior/auto_walk", True, type=bool)
        self.walk_frequency = self.settings.value("behavior/walk_frequency", "normal", type=str)
        if self.walk_frequency not in self.WALK_RANGES:
            self.walk_frequency = "normal"
        self.dialogue_enabled = self.settings.value("dialogue/enabled", True, type=bool)
        requested_voice = self.settings.value("voice/enabled", True, type=bool)
        self.voice = VoiceEngine()
        self.voice_enabled = bool(requested_voice and self.voice.available)
        self.chatter_level = self.settings.value("dialogue/frequency", "normal", type=str)
        if self.chatter_level not in self.CHATTER_RANGES:
            self.chatter_level = "normal"
        self.dialogues = DialogueLibrary()
        self.bubble = SpeechBubble()
        self.reminder_store = ReminderStore(user_data_file("reminders.json"))
        self.active_reminder = None
        self.mood = self.settings.value("mood/current", "calm", type=str)
        if self.mood not in self.MOODS:
            self.mood = "calm"
        self.mood_until = 0.0
        self.dialogue_cooldown_until = 0.0
        self.next_chatter = 0.0
        stored_focus_end = self.settings.value("focus/end_epoch", 0.0, type=float)
        self.focus_end_epoch = stored_focus_end if stored_focus_end > time.time() else 0.0
        if not self.focus_end_epoch:
            self.settings.remove("focus/end_epoch")
        self.last_clock_minute = None
        self.last_late_night_date = self.settings.value(
            "time/late_night_date", "", type=str)
        self.schedule_next_walk()
        self.schedule_next_chatter()
        self.reset_position()
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.tick)
        self.timer.start(100)
        QApplication.instance().screenRemoved.connect(lambda _: self.reset_position())
        for screen in QApplication.screens():
            screen.availableGeometryChanged.connect(lambda _: self.keep_visible())
        QTimer.singleShot(700, self.startup_message)

    def schedule_next_chatter(self, now=None):
        low, high = self.CHATTER_RANGES[self.chatter_level]
        self.next_chatter = (time.monotonic() if now is None else now) + random.uniform(low, high)

    def schedule_next_walk(self, now=None):
        low, high = self.WALK_RANGES[self.walk_frequency]
        self.next_walk = (time.monotonic() if now is None else now) + random.uniform(low, high)

    def set_mood(self, mood, duration=0):
        if mood not in self.MOODS:
            return
        self.mood = mood
        self.mood_until = time.monotonic() + max(0, float(duration)) if duration else 0.0
        self.settings.setValue("mood/current", mood)
        self.update()

    def mood_text(self):
        return self.MOODS.get(self.mood, self.MOODS["calm"])[2]

    def open_settings_center(self):
        dialog = SettingsDialog(self, self)
        dialog.exec()
        dialog.deleteLater()

    def apply_user_settings(self, values):
        self.auto_walk_enabled = bool(values.get("auto_walk", self.auto_walk_enabled))
        self.walk_frequency = values.get("walk_frequency", self.walk_frequency)
        if self.walk_frequency not in self.WALK_RANGES:
            self.walk_frequency = "normal"
        self.sleep_after = max(15, int(values.get("sleep_after", self.sleep_after)))
        self.settings.setValue("behavior/auto_walk", self.auto_walk_enabled)
        self.settings.setValue("behavior/walk_frequency", self.walk_frequency)
        self.settings.setValue("behavior/sleep_after", self.sleep_after)
        self.set_dialogue_enabled(bool(values.get("dialogue_enabled", self.dialogue_enabled)))
        self.set_voice_enabled(bool(values.get("voice_enabled", self.voice_enabled)))
        if not self.auto_walk_enabled and self.state == "Walk":
            self.set_state("Idle")
        self.schedule_next_walk()
        self.set_mood("happy", 5)
        self.show_message("设置保存好啦！", force=True)

    def show_message(self, text, force=False, duration_ms=3200):
        if self.active_reminder is not None:
            return None
        if not self.dialogue_enabled:
            return None
        now = time.monotonic()
        if not force and now < self.dialogue_cooldown_until:
            return None
        self.bubble.show_text(text, self.frameGeometry(), self.screen_area(), duration_ms)
        if self.voice_enabled:
            self.voice.speak(text)
        self.dialogue_cooldown_until = now + 3.8
        return text

    def talk(self, event, force=False):
        if not self.dialogue_enabled:
            return None
        if not force and time.monotonic() < self.dialogue_cooldown_until:
            return None
        return self.show_message(self.dialogues.choose(event), force=True)

    def pending_reminder_count(self):
        return len(self.reminder_store.pending())

    def show_active_reminder(self):
        if self.active_reminder is None:
            return
        self.set_mood("grumpy", 4)
        text = f"提醒：{self.active_reminder['text']}\n点击我确认完成"
        self.bubble.show_text(
            text,
            self.frameGeometry(),
            self.screen_area(),
            duration_ms=0,
            emphasis=True,
        )
        if not self.edge_side:
            self.until = time.monotonic() + 2.0
            self.set_state("Click")

    def sync_active_reminder(self):
        if self.active_reminder is None:
            return
        current = self.reminder_store.get(self.active_reminder["id"])
        if (current is None or current.get("status") != "pending" or
                float(current.get("due_at", 0)) > time.time()):
            self.active_reminder = None
            self.bubble.hide()
        else:
            self.active_reminder = current

    def check_reminders(self):
        self.sync_active_reminder()
        if self.active_reminder is None:
            due = self.reminder_store.due()
            if due:
                self.active_reminder = due[0]
                self.show_active_reminder()
        elif not self.bubble.isVisible() or not self.bubble.emphasis:
            self.show_active_reminder()
        return self.active_reminder is not None

    def acknowledge_active_reminder(self):
        if self.active_reminder is None:
            return
        reminder_id = self.active_reminder["id"]
        if self.reminder_store.complete(reminder_id):
            self.set_mood("happy", 8)
            self.active_reminder = None
            self.bubble.hide()
            if not self.edge_side:
                self.until = time.monotonic() + 1.6
                self.set_state("Click")
            self.talk("reminder_done", force=True)

    def reminders_changed(self):
        self.sync_active_reminder()
        self.check_reminders()

    def open_reminder_center(self):
        dialog = ReminderCenterDialog(
            self.reminder_store,
            on_changed=self.reminders_changed,
            parent=self,
        )
        dialog.exec()
        dialog.deleteLater()
        self.reminders_changed()

    def focus_active(self):
        return self.focus_end_epoch > time.time()

    def focus_remaining_seconds(self):
        return max(0, int(self.focus_end_epoch - time.time() + 0.999))

    def focus_remaining_text(self):
        seconds = self.focus_remaining_seconds()
        minutes, seconds = divmod(seconds, 60)
        if minutes:
            return f"专注中，还剩 {minutes} 分 {seconds:02d} 秒。"
        return f"专注中，还剩 {seconds} 秒。"

    def start_focus(self, minutes):
        minutes = max(1, int(minutes))
        self.focus_end_epoch = time.time() + minutes * 60
        self.settings.setValue("focus/end_epoch", self.focus_end_epoch)
        self.next_walk = time.monotonic() + minutes * 60
        if not self.edge_side:
            self.set_state("Idle")
        self.set_mood("calm", minutes * 60)
        self.talk("focus_start", force=True)

    def show_focus_remaining(self):
        if not self.focus_active():
            return None
        if self.edge_side:
            return self.show_edge_focus_countdown(force=True)
        return self.show_message(self.focus_remaining_text(), force=True, duration_ms=4200)

    def show_edge_focus_countdown(self, force=False):
        if (not self.focus_active() or not self.dialogue_enabled or
                self.active_reminder is not None or not self.edge_side):
            return None
        remaining = self.focus_remaining_seconds()
        if (force or remaining != self.edge_focus_last_second or
                not self.bubble.isVisible() or self.bubble.emphasis):
            self.edge_focus_last_second = remaining
            text = self.focus_remaining_text()
            self.bubble.show_text(
                text,
                self.frameGeometry(),
                self.screen_area(),
                duration_ms=0,
                emphasis=False,
            )
            return text
        return self.bubble.text

    def stop_focus(self, completed=False):
        was_active = bool(self.focus_end_epoch)
        self.focus_end_epoch = 0.0
        self.settings.remove("focus/end_epoch")
        self.next_walk = time.monotonic() + 5
        if not was_active:
            return
        if completed:
            self.set_mood("happy", 8)
            if not self.edge_side:
                self.until = time.monotonic() + 2.0
                self.set_state("Click")
            self.talk("focus_complete", force=True)
        else:
            self.talk("focus_cancel", force=True)

    def startup_message(self):
        if self.focus_active():
            self.show_focus_remaining()
            return
        hour = datetime.now().hour
        if 5 <= hour < 11:
            event = "morning"
        elif 11 <= hour < 14:
            event = "noon"
        elif 18 <= hour < 23:
            event = "evening"
        elif hour >= 23 or hour < 5:
            event = "late_night"
        else:
            event = "greeting"
        self.talk(event)

    def maybe_time_reaction(self):
        current = datetime.now()
        minute_key = current.strftime("%Y-%m-%d %H:%M")
        if minute_key == self.last_clock_minute:
            return
        self.last_clock_minute = minute_key
        if self.focus_active():
            return
        today = current.strftime("%Y-%m-%d")
        if (current.hour >= 23 or current.hour < 5) and self.last_late_night_date != today:
            self.last_late_night_date = today
            self.settings.setValue("time/late_night_date", today)
            self.talk("late_night", force=True)
        elif current.minute == 0:
            self.show_message(
                f"现在 {current.hour} 点啦，起来活动一下吧！",
                force=True,
                duration_ms=4500,
            )

    def set_dialogue_enabled(self, enabled):
        self.dialogue_enabled = bool(enabled)
        self.settings.setValue("dialogue/enabled", self.dialogue_enabled)
        if self.dialogue_enabled:
            self.talk("greeting", force=True)
        else:
            if self.active_reminder is not None:
                self.show_active_reminder()
            else:
                self.bubble.hide()
            self.voice.stop()

    def set_voice_enabled(self, enabled):
        requested = bool(enabled)
        self.settings.setValue("voice/enabled", requested)
        self.voice_enabled = bool(requested and self.voice.available)
        if self.voice_enabled:
            self.talk("greeting", force=True)
        else:
            self.voice.stop()

    def set_chatter_level(self, level):
        if level not in self.CHATTER_RANGES:
            return
        self.chatter_level = level
        self.settings.setValue("dialogue/frequency", level)
        self.schedule_next_chatter()

    def maybe_chatter(self, now):
        if now < self.next_chatter:
            return
        event = f"edge_{self.edge_side}" if self.edge_side else "idle"
        if self.state != "Sleep":
            self.talk(event)
        self.schedule_next_chatter(now)

    def load_edge_frames(self):
        root = self.EDGE_ASSET_ROOT
        manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8-sig"))
        self.edge_reference_head_width = float(manifest["reference_head_width"])
        self.edge_poses = manifest["poses"]
        if self.edge_reference_head_width <= 0:
            raise ValueError("边缘素材的基准头宽必须大于零")
        frames = {}
        for side in ("left", "right", "top", "bottom"):
            pose = self.edge_poses[side]
            path = root / pose["file"]
            image = QImage(str(path))
            if image.isNull() or not image.hasAlphaChannel():
                raise RuntimeError(f"边缘动作素材无效或缺失: {path}")
            if float(pose["head_width"]) <= 0 or len(pose["anchor"]) != 2:
                raise ValueError(f"边缘动作锚点或头宽无效: {side}")
            frames[side] = image
        return frames

    def edge_image_scale(self, side):
        return self.edge_reference_head_width / float(self.edge_poses[side]["head_width"]) * self.scale_factor

    def edge_layout(self, side):
        """Keep character scale independent from image whitespace and pose height."""
        image = self.edge_frames[side]
        factor = self.edge_image_scale(side)
        width, height = image.width() * factor, image.height() * factor
        rect = QRectF((self.width() - width) / 2, (self.height() - height) / 2, width, height)
        ax, ay = self.edge_poses[side]["anchor"]
        contact = QPointF(rect.x() + float(ax) * factor, rect.y() + float(ay) * factor)
        return rect, contact

    def edge_contact_global(self, side=None):
        _, contact = self.edge_layout(side or self.edge_side)
        return contact + QPointF(self.pos())

    def clear_edge(self):
        self.edge_side = None
        self.edge_focus_last_second = None
        self.edge_sticky = False
        self.edge_screen = None
        self._edge_candidate_screen = None

    def set_state(self, state):
        if self.edge_side is not None:
            state = "Edge"
        if state != self.state:
            self.state = state
            self.state_tick = 0
        self.update()

    def screen_for_point(self, point):
        screen = QApplication.screenAt(point)
        if screen is not None:
            return screen
        def distance(item):
            rect = item.geometry()
            dx = max(rect.left() - point.x(), 0, point.x() - rect.right())
            dy = max(rect.top() - point.y(), 0, point.y() - rect.bottom())
            return dx * dx + dy * dy
        return min(QApplication.screens(), key=distance)

    def screen_area(self):
        screen = self.edge_screen or self.screen_for_point(self.frameGeometry().center())
        return screen.availableGeometry()

    def visible_margin(self):
        return max(32, round(self.width() * self.EDGE_VISIBLE_RATIO))

    def vertical_visible_margin(self, side):
        if side == "bottom":
            return max(42, round(self.height() * self.EDGE_BOTTOM_VISIBLE_RATIO))
        return max(36, round(self.height() * self.EDGE_VISIBLE_RATIO))

    def horizontal_limits(self):
        area = self.screen_area()
        margin = self.visible_margin()
        return area.left() - self.width() + margin, area.right() + 1 - margin

    def vertical_limits(self):
        area = self.screen_area()
        top_margin = self.vertical_visible_margin("top")
        bottom_margin = self.vertical_visible_margin("bottom")
        return area.top() - self.height() + top_margin, area.bottom() + 1 - bottom_margin

    def keep_visible(self):
        area = self.screen_area()
        if self.edge_side:
            self.snap_to_edge(self.edge_side)
            return
        left_limit, right_limit = self.horizontal_limits()
        top_limit, bottom_limit = self.vertical_limits()
        self.move(max(left_limit, min(self.x(), right_limit)),
                  max(top_limit, min(self.y(), bottom_limit)))

    def snap_to_edge(self, side):
        area = self.screen_area()
        rect, contact = self.edge_layout(side)
        # Keep the contact point at the edge; constrain only the tangent axis.
        x = max(area.left() - rect.left(), min(self.x(), area.right() + 1 - rect.right()))
        y = max(area.top() - rect.top(), min(self.y(), area.bottom() + 1 - rect.bottom()))
        if side == "left":
            x = area.left() - contact.x()
        elif side == "right":
            x = area.right() + 1 - contact.x()
        elif side == "top":
            y = area.top() - contact.y()
        elif side == "bottom":
            y = area.bottom() + 1 - contact.y()
        self.move(round(x), round(y))

    def nearest_edge(self, pointer=None):
        pointer = pointer or self.frameGeometry().center()
        self._edge_candidate_screen = self.screen_for_point(pointer)
        area = self._edge_candidate_screen.availableGeometry()
        # Negative means the dragged window has already crossed the boundary.
        signed_distances = {
            "left": self.x() - area.left(),
            "right": area.right() + 1 - (self.x() + self.width()),
            "top": self.y() - area.top(),
            "bottom": area.bottom() + 1 - (self.y() + self.height()),
        }
        pointer_distances = {
            "left": abs(pointer.x() - area.left()),
            "right": abs(pointer.x() - (area.right() + 1)),
            "top": abs(pointer.y() - area.top()),
            "bottom": abs(pointer.y() - (area.bottom() + 1)),
        }
        candidates = [side for side, distance in signed_distances.items()
                      if distance <= self.EDGE_TRIGGER_DISTANCE]
        return min(candidates, key=lambda side: pointer_distances[side]) if candidates else None

    def perch_on_edge(self, side, now, sticky=False):
        if side not in self.edge_frames:
            raise ValueError(f"未知屏幕边缘: {side}")
        self.edge_screen = (self._edge_candidate_screen or self.edge_screen or
                            self.screen_for_point(self.frameGeometry().center()))
        self._edge_candidate_screen = None
        self.edge_side = side
        self.edge_sticky = sticky
        if side == "left":
            self.direction = 1
        elif side == "right":
            self.direction = -1
        self.snap_to_edge(side)
        self.edge_until = now + self.EDGE_PAUSE_SECONDS
        self.until = self.edge_until
        self.next_walk = self.edge_until + random.uniform(2, 5)
        self.set_state("Edge")
        if self.focus_active() and self.active_reminder is None:
            self.show_edge_focus_countdown(force=True)
        else:
            self.talk(f"edge_{side}", force=True)

    def reset_position(self):
        area = QApplication.primaryScreen().availableGeometry()
        self.clear_edge()
        self.move(area.right() - self.width() - 35, area.bottom() - self.height() + 1)
        self.last_touch = time.monotonic()
        self.set_state("Idle")

    def set_pet_scale(self, value):
        value = max(self.SCALE_MIN, min(self.SCALE_MAX, round(value, 2)))
        if value == self.scale_factor:
            return
        anchor_x = self.x() + self.width() // 2
        anchor_y = self.y() + self.height()
        edge_contact = self.edge_contact_global() if self.edge_side else None
        self.scale_factor = value
        new_width, new_height = round(WIDTH * value), round(HEIGHT * value)
        self.setFixedSize(new_width, new_height)
        if edge_contact is not None:
            _, contact = self.edge_layout(self.edge_side)
            self.move(round(edge_contact.x() - contact.x()), round(edge_contact.y() - contact.y()))
        else:
            self.move(anchor_x - new_width // 2, anchor_y - new_height)
        self.keep_visible()
        if self.bubble.isVisible():
            self.bubble.follow(self.frameGeometry(), self.screen_area())
        self.update()

    def adjust_scale(self, amount):
        self.set_pet_scale(self.scale_factor + amount)

    def reset_scale(self):
        self.set_pet_scale(1.0)

    def tick(self):
        self.state_tick += 1
        now = time.monotonic()
        if self.mood_until and now >= self.mood_until:
            self.set_mood("calm")
        if self.bubble.isVisible():
            self.bubble.follow(self.frameGeometry(), self.screen_area())
        if self.press is not None or self.menu_open:
            self.update(); return

        if self.check_reminders():
            if self.edge_side and (self.edge_sticky or now < self.edge_until):
                self.snap_to_edge(self.edge_side)
                self.set_state("Edge")
            elif self.edge_side:
                self.clear_edge()
                self.set_state("Look" if self.hovered else "Idle")
            elif self.state in ("Click", "Angry") and now >= self.until:
                self.set_state("Look" if self.hovered else "Idle")
            self.update()
            return

        focus_completed = bool(self.focus_end_epoch and not self.focus_active())
        if focus_completed:
            self.stop_focus(completed=True)
        else:
            self.maybe_time_reaction()
        if not self.focus_active():
            self.maybe_chatter(now)

        if self.edge_side and (self.edge_sticky or now < self.edge_until):
            self.snap_to_edge(self.edge_side)
            self.set_state("Edge")
            if self.focus_active():
                self.show_edge_focus_countdown()
            self.update()
            return
        if self.edge_side:
            self.clear_edge()
            self.set_state("Look" if self.hovered else "Idle")
        if self.focus_active():
            if self.state == "Walk" or self.state == "Sleep":
                self.set_state("Look" if self.hovered else "Idle")
            elif self.state in ("Click", "Angry") and now >= self.until:
                self.set_state("Look" if self.hovered else "Idle")
            elif self.hovered and self.state == "Idle":
                self.set_state("Look")
            elif not self.hovered and self.state == "Look":
                self.set_state("Idle")
            self.update()
            return
        system_idle = system_idle_seconds()
        idle = now - self.last_touch if system_idle is None else min(system_idle, now - self.last_touch)
        if idle >= self.sleep_after:
            if self.state != "Sleep":
                self.set_mood("sleepy")
                self.talk("sleep", force=True)
            self.set_state("Sleep")
            return
        if self.state == "Sleep":
            self.set_state("Look" if self.hovered else "Idle")
            self.next_walk = now + 5
            self.set_mood("happy", 8)
            self.talk("wake", force=True)
        elif self.state in ("Click", "Angry"):
            if now >= self.until:
                self.set_state("Look" if self.hovered else "Idle")
        elif self.state == "Walk":
            self.move(self.x() + self.direction * 3, self.y())
            area = self.screen_area()
            if self.direction < 0 and self.x() <= area.left():
                self.perch_on_edge("left", now)
                self.update()
                return
            if self.direction > 0 and self.x() + self.width() >= area.right() + 1:
                self.perch_on_edge("right", now)
                self.update()
                return
            if now >= self.until:
                self.set_state("Look" if self.hovered else "Idle")
                self.schedule_next_walk(now)
        elif self.hovered:
            self.set_state("Look")
        elif self.state == "Look":
            self.set_state("Idle")
        elif self.auto_walk_enabled and now >= self.next_walk:
            self.direction = random.choice((-1, 1))
            self.until = now + random.uniform(2, 5)
            self.set_state("Walk")
            self.set_mood("playful", 8)
            self.talk("walk")
        elif not self.auto_walk_enabled:
            self.next_walk = now + 60
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        if self.edge_side in self.edge_frames:
            # A work-area boundary is not an OS clipping boundary (taskbar, monitors).
            p.setClipRect(self.screen_area().translated(-self.x(), -self.y()))
            rect, _ = self.edge_layout(self.edge_side)
            p.drawImage(rect, self.edge_frames[self.edge_side])
            return
        image = self.frames[self.state][self.state_tick % len(self.frames[self.state])]
        flip = (self.edge_side is None and
                ((self.state == "Walk" and self.direction < 0) or
                (self.state == "Look" and QCursor.pos().x() < self.frameGeometry().center().x())))
        if flip:
            p.translate(self.width(), 0); p.scale(-1, 1)
        p.drawImage(self.rect(), image)
        p.resetTransform()
        if self.state not in ("Sleep", "Edge"):
            symbol, color, _ = self.MOODS.get(self.mood, self.MOODS["calm"])
            badge = QRectF(self.width() - 24, 3, 20, 20)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(color)
            p.drawEllipse(badge)
            p.setPen(QColor("#fffaf0"))
            p.setFont(QFont("Segoe UI Symbol", 11, QFont.Weight.Bold))
            p.drawText(badge, Qt.AlignmentFlag.AlignCenter, symbol)

    def enterEvent(self, event):
        self.hovered = True
        if self.state in ("Idle", "Walk") and self.press is None:
            self.set_state("Look")
            if self.focus_active():
                self.show_focus_remaining()
            else:
                self.talk("hover")
        if event is not None:
            super().enterEvent(event)

    def leaveEvent(self, event):
        self.hovered = False
        if self.state == "Look":
            self.set_state("Idle")
        if event is not None:
            super().leaveEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.press = event.globalPosition().toPoint()
            self.origin = self.pos()
            self.dragging = False
            self.last_touch = time.monotonic()
            if not self.edge_side:
                self.set_state("Look")

    def mouseMoveEvent(self, event):
        if self.press is not None:
            delta = event.globalPosition().toPoint() - self.press
            if delta.manhattanLength() >= QApplication.startDragDistance():
                if not self.dragging:
                    self.dragging = True
                    self.set_mood("playful", 5)
                    if not self.focus_active():
                        self.talk("drag", force=True)
            if self.dragging:
                self.clear_edge()
                self.set_state("Drag")
                self.move(self.origin + delta)

    def mouseReleaseEvent(self, event):
        if event.button() != Qt.MouseButton.LeftButton or self.press is None:
            return
        now = time.monotonic()
        was_dragging = self.dragging
        self.press = None; self.dragging = False
        self.last_touch = now; self.next_walk = now + 5
        if was_dragging:
            side = self.nearest_edge(event.globalPosition().toPoint())
            if side:
                self.perch_on_edge(side, now, sticky=True)
            else:
                self.clear_edge()
                self.set_state("Look" if self.hovered else "Idle")
                if self.focus_active():
                    self.show_focus_remaining()
        elif self.active_reminder is not None:
            self.acknowledge_active_reminder()
        elif self.edge_side:
            self.edge_sticky = True
            self.set_state("Edge")
            if self.focus_active():
                self.show_edge_focus_countdown(force=True)
        elif self.focus_active():
            self.until = now + 1.0
            self.set_state("Click")
            self.show_focus_remaining()
        else:
            self.click_times = [t for t in self.click_times if now - t <= 2.0]
            self.click_times.append(now)
            if len(self.click_times) >= 4:
                self.click_times.clear(); self.until = now + 2.4; self.set_state("Angry")
                self.set_mood("grumpy", 5)
                self.talk("angry", force=True)
            else:
                self.until = now + 1.0; self.set_state("Click")
                self.set_mood("playful", 3)
                self.talk("click", force=True)
        self.keep_visible()

    def contextMenuEvent(self, event):
        self.menu_open = True; self.last_touch = time.monotonic()
        menu = QMenu(self)
        count = self.pending_reminder_count()
        reminder_label = "提醒中心…" if count == 0 else f"提醒中心…（{count}）"
        menu.addAction(reminder_label, self.open_reminder_center)
        menu.addAction(f"设置中心…（当前心情：{self.mood_text()}）", self.open_settings_center)
        menu.addSeparator()
        focus_menu = menu.addMenu("专注计时")
        if self.focus_active():
            remaining = self.focus_remaining_seconds()
            minutes, seconds = divmod(remaining, 60)
            status_action = focus_menu.addAction(
                f"剩余 {minutes:02d}:{seconds:02d}")
            status_action.setEnabled(False)
            focus_menu.addAction("显示剩余时间", self.show_focus_remaining)
            focus_menu.addAction("提前结束专注", lambda: self.stop_focus(False))
        else:
            for minutes in (15, 25, 50):
                focus_menu.addAction(
                    f"开始 {minutes} 分钟",
                    lambda checked=False, value=minutes: self.start_focus(value))
        menu.addSeparator()
        dialogue_action = menu.addAction("显示对话气泡")
        dialogue_action.setCheckable(True)
        dialogue_action.setChecked(self.dialogue_enabled)
        dialogue_action.triggered.connect(self.set_dialogue_enabled)
        voice_action = menu.addAction("顽皮童声")
        voice_action.setCheckable(True)
        voice_action.setChecked(self.voice_enabled)
        voice_action.setEnabled(self.voice.available)
        if not self.voice.available:
            voice_action.setText("顽皮童声（本机不可用）")
        voice_action.triggered.connect(self.set_voice_enabled)
        preview_action = menu.addAction("试听一句")
        preview_action.setEnabled(self.dialogue_enabled and self.voice_enabled)
        preview_action.triggered.connect(lambda: self.talk("greeting", force=True))
        frequency_menu = menu.addMenu("主动说话频率")
        for key, label in (("low", "较少"), ("normal", "正常"), ("high", "较多")):
            action = frequency_menu.addAction(label)
            action.setCheckable(True)
            action.setChecked(self.chatter_level == key)
            action.triggered.connect(
                lambda checked, value=key: checked and self.set_chatter_level(value))
        menu.addSeparator()
        menu.addAction("放大  Ctrl++", lambda: self.adjust_scale(self.SCALE_STEP))
        menu.addAction("缩小  Ctrl+-", lambda: self.adjust_scale(-self.SCALE_STEP))
        menu.addAction("恢复默认大小  Ctrl+0", self.reset_scale)
        menu.addSeparator(); menu.addAction("重置位置", self.reset_position)
        menu.addSeparator(); menu.addAction("退出", QApplication.instance().quit)
        try:
            menu.exec(event.globalPos())
        finally:
            self.menu_open = False; menu.deleteLater()

    def closeEvent(self, event):
        self.voice.close()
        self.bubble.close()
        super().closeEvent(event)

    def keyPressEvent(self, event):
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            if event.key() in (Qt.Key.Key_Plus, Qt.Key.Key_Equal):
                self.adjust_scale(self.SCALE_STEP); event.accept(); return
            if event.key() == Qt.Key.Key_Minus:
                self.adjust_scale(-self.SCALE_STEP); event.accept(); return
            if event.key() == Qt.Key.Key_0:
                self.reset_scale(); event.accept(); return
        super().keyPressEvent(event)
