"""
Simple Avatar Projector - macOS Compatible

This version works reliably on macOS with external displays.
Opens a window you can drag to the projector, then maximize.

Usage:
    python avatar_projector_simple.py

Controls:
    F: Toggle fullscreen (after dragging to projector)
    Arrow keys: Move avatar position
    +/-: Scale avatar
    1-9: Change expression
    Q: Quit
"""

import sys
import os
import threading
import math
import time
import random
from pathlib import Path
from queue import Queue, Empty

sys.path.insert(0, str(Path(__file__).parent.parent))

import cv2

try:
    import pygame
except ImportError:
    print("Install pygame: pip install pygame")
    sys.exit(1)

from deepface import DeepFace


# High contrast colors for projection (black background = no light)
COLORS = {
    "background": (0, 0, 0),
    "face": (80, 180, 255),
    "eyes": (255, 255, 255),
    "mouth": (255, 255, 255),
    "glow": (100, 200, 255),
}

MOODS = ["neutral", "happy", "sad", "thinking", "surprised", "playful", "encouraging"]

EMOTION_TO_MOOD = {
    "happy": "happy",
    "sad": "sad",
    "angry": "encouraging",
    "fear": "surprised",
    "surprise": "surprised",
    "disgust": "playful",
    "neutral": "neutral",
}


class SimpleProjectorAvatar:
    def __init__(self, width=1920, height=1080):
        pygame.init()
        pygame.display.set_caption("Chess Companion - Drag to Projector, then press F")

        self.width = width
        self.height = height
        self.screen = pygame.display.set_mode((width, height), pygame.RESIZABLE)
        self.clock = pygame.time.Clock()
        self.is_fullscreen = False

        # Avatar state
        self.mood = "neutral"
        self.message = ""
        self.message_end = 0

        # Position/scale for alignment
        self.offset_x = 0
        self.offset_y = 0
        self.scale = 1.0

        # Animation
        self.blink = False
        self.blink_time = 0
        self.next_blink = time.time() + random.uniform(2, 4)
        self.breath = 0
        self.eye_x = 0
        self.eye_y = 0

        # Emotion tracking
        self.current_emotion = "neutral"
        self.emotion_confidence = 0
        self.current_frame = None
        self.frame_lock = threading.Lock()
        self.show_camera = True

    @property
    def cx(self):
        return self.width // 2 + self.offset_x

    @property
    def cy(self):
        return self.height // 2 + self.offset_y

    @property
    def radius(self):
        base = min(self.width, self.height) * 0.35
        return int(base * self.scale * (1 + math.sin(self.breath) * 0.01))

    def set_mood(self, mood):
        if mood in MOODS:
            self.mood = mood

    def show_msg(self, text, duration=3):
        self.message = text
        self.message_end = time.time() + duration

    def update(self):
        now = time.time()
        dt = self.clock.tick(60) / 1000.0

        # Breathing
        self.breath += dt * 2

        # Blinking
        if not self.blink and now > self.next_blink:
            self.blink = True
            self.blink_time = now
        if self.blink and now - self.blink_time > 0.12:
            self.blink = False
            self.next_blink = now + random.uniform(2, 5)

        # Eye wander
        if random.random() < 0.02:
            self.eye_x = random.uniform(-12, 12) * self.scale
            self.eye_y = random.uniform(-6, 6) * self.scale

        # Message timeout
        if self.message and now > self.message_end:
            self.message = ""

    def draw(self):
        self.screen.fill(COLORS["background"])

        # Glow
        for i in range(3):
            r = self.radius + 20 + i * 10
            surf = pygame.Surface((r*2, r*2), pygame.SRCALPHA)
            pygame.draw.circle(surf, (*COLORS["glow"], 50 - i*15), (r, r), r)
            self.screen.blit(surf, (self.cx - r, self.cy - r))

        # Face
        pygame.draw.circle(self.screen, COLORS["face"], (self.cx, self.cy), self.radius)

        # Eyes
        self._draw_eyes()

        # Mouth
        self._draw_mouth()

        # Message
        if self.message:
            font = pygame.font.Font(None, 48)
            text = font.render(self.message, True, COLORS["glow"])
            rect = text.get_rect(center=(self.cx, self.height - 80))
            pygame.draw.rect(self.screen, (20, 20, 20), rect.inflate(30, 20), border_radius=10)
            self.screen.blit(text, rect)

        # Camera preview
        if self.show_camera:
            self._draw_camera()

        # Info
        self._draw_info()

        pygame.display.flip()

    def _draw_eyes(self):
        ey = self.cy - self.radius * 0.15
        spacing = self.radius * 0.35
        er = self.radius * 0.13
        pr = er * 0.5

        left_x = self.cx - spacing
        right_x = self.cx + spacing

        if self.blink:
            for ex in [left_x, right_x]:
                pygame.draw.line(self.screen, COLORS["eyes"],
                    (ex - er, ey), (ex + er, ey), 4)
            return

        if self.mood == "happy":
            for ex in [left_x, right_x]:
                rect = pygame.Rect(ex - er, ey - er/2, er*2, er)
                pygame.draw.arc(self.screen, COLORS["eyes"], rect, 0, math.pi, 4)

        elif self.mood == "sad":
            for i, ex in enumerate([left_x, right_x]):
                pygame.draw.ellipse(self.screen, COLORS["eyes"],
                    (ex - er, ey - er*0.7, er*2, er*1.4))
                d = 1 if i == 0 else -1
                pygame.draw.line(self.screen, COLORS["face"],
                    (ex - er*d, ey - er*1.3), (ex + er*d, ey - er*0.9), 4)

        elif self.mood == "surprised":
            for ex in [left_x, right_x]:
                pygame.draw.circle(self.screen, COLORS["eyes"], (int(ex), int(ey)), int(er*1.3))
                pygame.draw.circle(self.screen, (0,0,0), (int(ex), int(ey)), int(pr*0.8))

        elif self.mood == "thinking":
            for ex in [left_x, right_x]:
                pygame.draw.circle(self.screen, COLORS["eyes"], (int(ex), int(ey)), int(er))
                pygame.draw.circle(self.screen, (0,0,0),
                    (int(ex + 8*self.scale), int(ey - 5*self.scale)), int(pr))

        elif self.mood == "playful":
            # Left eye normal
            pygame.draw.circle(self.screen, COLORS["eyes"], (int(left_x), int(ey)), int(er))
            pygame.draw.circle(self.screen, (0,0,0),
                (int(left_x + self.eye_x*0.5), int(ey + self.eye_y*0.5)), int(pr))
            # Right eye wink
            rect = pygame.Rect(right_x - er, ey - er/2, er*2, er)
            pygame.draw.arc(self.screen, COLORS["eyes"], rect, 0, math.pi, 4)

        else:  # neutral, encouraging
            for ex in [left_x, right_x]:
                pygame.draw.circle(self.screen, COLORS["eyes"], (int(ex), int(ey)), int(er))
                pygame.draw.circle(self.screen, (0,0,0),
                    (int(ex + self.eye_x*0.5), int(ey + self.eye_y*0.5)), int(pr))

    def _draw_mouth(self):
        my = self.cy + self.radius * 0.32
        mw = self.radius * 0.4

        if self.mood == "happy":
            rect = pygame.Rect(self.cx - mw, my - mw*0.4, mw*2, mw*1.2)
            pygame.draw.arc(self.screen, COLORS["mouth"], rect, math.pi, 2*math.pi, 5)

        elif self.mood == "sad":
            rect = pygame.Rect(self.cx - mw, my + mw*0.2, mw*2, mw*0.8)
            pygame.draw.arc(self.screen, COLORS["mouth"], rect, 0, math.pi, 5)

        elif self.mood == "surprised":
            pygame.draw.circle(self.screen, COLORS["mouth"],
                (self.cx, int(my + 12*self.scale)), int(mw*0.3), 4)

        elif self.mood == "thinking":
            pygame.draw.circle(self.screen, COLORS["mouth"],
                (int(self.cx + 15*self.scale), int(my)), int(mw*0.12), 4)

        elif self.mood == "playful":
            pts = [(self.cx - mw*0.5, my),
                   (self.cx + mw*0.3, my - 12*self.scale),
                   (self.cx + mw*0.5, my - 20*self.scale)]
            pygame.draw.lines(self.screen, COLORS["mouth"], False, pts, 4)

        elif self.mood == "encouraging":
            rect = pygame.Rect(self.cx - mw*0.6, my - mw*0.2, mw*1.2, mw*0.5)
            pygame.draw.arc(self.screen, COLORS["mouth"], rect, math.pi, 2*math.pi, 4)

        else:  # neutral
            pygame.draw.line(self.screen, COLORS["mouth"],
                (self.cx - mw*0.4, my), (self.cx + mw*0.4, my), 4)

    def _draw_camera(self):
        with self.frame_lock:
            if self.current_frame is None:
                return
            frame = self.current_frame.copy()

        pw, ph = 180, 135
        frame = cv2.resize(frame, (pw, ph))
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB).swapaxes(0, 1)

        surf = pygame.surfarray.make_surface(frame)
        x, y = self.width - pw - 15, self.height - ph - 15

        pygame.draw.rect(self.screen, COLORS["glow"], (x-2, y-2, pw+4, ph+4), 2)
        self.screen.blit(surf, (x, y))

        font = pygame.font.Font(None, 24)
        label = f"{self.current_emotion} ({self.emotion_confidence:.0f}%)"
        text = font.render(label, True, COLORS["glow"])
        self.screen.blit(text, (x, y - 20))

    def _draw_info(self):
        font = pygame.font.Font(None, 24)
        lines = [
            f"Mood: {self.mood}  |  Offset: ({self.offset_x}, {self.offset_y})  |  Scale: {self.scale:.1f}",
            "Arrows: move  |  +/-: scale  |  F: fullscreen  |  C: camera  |  1-7: mood  |  Q: quit",
        ]
        if not self.is_fullscreen:
            lines.insert(0, ">>> DRAG THIS WINDOW TO PROJECTOR, THEN PRESS F <<<")

        for i, line in enumerate(lines):
            color = (255, 200, 0) if i == 0 and not self.is_fullscreen else (100, 100, 100)
            text = font.render(line, True, color)
            self.screen.blit(text, (10, 10 + i * 22))

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False

            elif event.type == pygame.VIDEORESIZE:
                self.width, self.height = event.w, event.h
                if not self.is_fullscreen:
                    self.screen = pygame.display.set_mode((self.width, self.height), pygame.RESIZABLE)

            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_q or event.key == pygame.K_ESCAPE:
                    return False

                elif event.key == pygame.K_f:
                    self.is_fullscreen = not self.is_fullscreen
                    if self.is_fullscreen:
                        self.screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
                        info = pygame.display.Info()
                        self.width, self.height = info.current_w, info.current_h
                    else:
                        self.width, self.height = 1280, 720
                        self.screen = pygame.display.set_mode((self.width, self.height), pygame.RESIZABLE)

                elif event.key == pygame.K_c:
                    self.show_camera = not self.show_camera

                elif event.key == pygame.K_LEFT:
                    self.offset_x -= 20
                elif event.key == pygame.K_RIGHT:
                    self.offset_x += 20
                elif event.key == pygame.K_UP:
                    self.offset_y -= 20
                elif event.key == pygame.K_DOWN:
                    self.offset_y += 20

                elif event.key in (pygame.K_PLUS, pygame.K_EQUALS):
                    self.scale = min(2.0, self.scale + 0.1)
                elif event.key == pygame.K_MINUS:
                    self.scale = max(0.3, self.scale - 0.1)

                elif event.key == pygame.K_1:
                    self.set_mood("neutral")
                elif event.key == pygame.K_2:
                    self.set_mood("happy")
                elif event.key == pygame.K_3:
                    self.set_mood("sad")
                elif event.key == pygame.K_4:
                    self.set_mood("thinking")
                elif event.key == pygame.K_5:
                    self.set_mood("surprised")
                elif event.key == pygame.K_6:
                    self.set_mood("playful")
                elif event.key == pygame.K_7:
                    self.set_mood("encouraging")

        return True

    def quit(self):
        pygame.quit()


def main():
    avatar = SimpleProjectorAvatar(1280, 720)
    emotion_queue = Queue()
    running = True

    def detect_emotions():
        cap = None
        for i in range(3):
            cap = cv2.VideoCapture(i)
            if cap.isOpened():
                ret, _ = cap.read()
                if ret:
                    print(f"Camera at index {i}")
                    break
                cap.release()
                cap = None

        if not cap:
            print("No camera - keyboard control only")
            return

        count = 0
        while running:
            ret, frame = cap.read()
            if not ret:
                continue

            with avatar.frame_lock:
                avatar.current_frame = frame.copy()

            count += 1
            if count % 5 != 0:
                continue

            try:
                result = DeepFace.analyze(frame, actions=["emotion"],
                    detector_backend="opencv", enforce_detection=False, silent=True)
                if result:
                    e = result[0]["dominant_emotion"]
                    c = result[0]["emotion"][e]
                    emotion_queue.put((e, c))
            except:
                pass

        cap.release()

    # Load model
    print("Loading emotion model...")
    DeepFace.build_model(task="facial_attribute", model_name="Emotion")
    print("\nReady!")
    print("1. Drag this window to your PROJECTOR")
    print("2. Press F for fullscreen")
    print("3. Your expressions control the avatar!\n")

    # Start detection thread
    thread = threading.Thread(target=detect_emotions, daemon=True)
    thread.start()

    avatar.show_msg("Drag me to the projector!", 5)
    last_change = 0

    while avatar.handle_events():
        # Process emotions
        try:
            while True:
                e, c = emotion_queue.get_nowait()
                avatar.current_emotion = e
                avatar.emotion_confidence = c

                mood = EMOTION_TO_MOOD.get(e, "neutral")
                if mood != avatar.mood:
                    avatar.set_mood(mood)
                    if time.time() - last_change > 3:
                        msgs = {
                            "happy": "You look happy!",
                            "sad": "Everything okay?",
                            "surprised": "Surprised?",
                        }
                        if e in msgs:
                            avatar.show_msg(msgs[e], 2)
                        last_change = time.time()
        except Empty:
            pass

        avatar.update()
        avatar.draw()

    running = False
    avatar.quit()


if __name__ == "__main__":
    main()
