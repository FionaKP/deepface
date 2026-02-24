"""
Chess Companion Full Projection

Combines:
- Avatar face (opponent side of board)
- Chess board highlights/arrows
- Emotion detection

Layout:
    ┌─────────────────────┐
    │     AVATAR FACE     │  ← responds to player emotion
    ├─────────────────────┤
    │    CHESS BOARD      │  ← highlights moves, hints
    │    (calibrated)     │
    └─────────────────────┘

Usage:
    python chess_companion_projection.py

Setup:
1. Drag window to projector
2. Press F for fullscreen
3. Calibrate board corners (arrow keys, ENTER to save)
4. Avatar responds to your expressions!
"""

import sys
import math
import json
import time
import random
import threading
import numpy as np
from pathlib import Path
from typing import List, Tuple, Optional, Dict
from dataclasses import dataclass
from enum import Enum
from queue import Queue, Empty

sys.path.insert(0, str(Path(__file__).parent.parent))

import cv2

try:
    import pygame
except ImportError:
    print("Install pygame: pip install pygame")
    sys.exit(1)

from deepface import DeepFace


FILES = "abcdefgh"
RANKS = "12345678"


class Mode(Enum):
    CALIBRATE = "calibrate"
    PLAY = "play"


@dataclass
class Square:
    file: str
    rank: str
    x: int
    y: int
    size: int


AVATAR_MOODS = ["neutral", "happy", "sad", "thinking", "surprised", "playful", "encouraging"]

EMOTION_TO_MOOD = {
    "happy": "happy",
    "sad": "sad",
    "angry": "encouraging",
    "fear": "surprised",
    "surprise": "surprised",
    "disgust": "playful",
    "neutral": "neutral",
}


class ChessCompanionProjection:
    """Full chess companion with avatar + board projection."""

    COLORS = {
        "background": (0, 0, 0),
        "face": (80, 180, 255),
        "eyes": (255, 255, 255),
        "glow": (100, 200, 255),
        "calibration": (255, 255, 0),
        "grid": (40, 40, 40),
        "highlight_move": (80, 200, 80, 150),
        "highlight_select": (80, 80, 255, 150),
        "highlight_possible": (255, 255, 80, 100),
        "highlight_hint": (80, 255, 200, 150),
        "highlight_danger": (255, 80, 80, 150),
        "arrow": (255, 150, 50),
        "text": (255, 255, 255),
    }

    def __init__(self, width=1280, height=720):
        pygame.init()
        pygame.display.set_caption("Chess Companion - Drag to projector, press F")

        self.width = width
        self.height = height
        self.screen = pygame.display.set_mode((width, height), pygame.RESIZABLE)
        self.clock = pygame.time.Clock()
        self.is_fullscreen = False
        self.mode = Mode.CALIBRATE

        # Layout: avatar takes top portion, board takes bottom
        self.avatar_height_ratio = 0.35  # Avatar uses top 35%
        self._update_layout()

        # Avatar position/scale (user adjustable)
        self.avatar_offset_x = 0
        self.avatar_offset_y = 0
        self.avatar_scale = 1.0

        # Calibration mode: what's selected (0-3 = corners, 4 = avatar)
        self.selected_item = 4  # Start with avatar selected
        self.AVATAR_ITEM = 4

        # Calibration corners (for board area only)
        self._init_corners()
        self.squares: Dict[str, Square] = {}
        self._compute_squares()

        # Board state
        self.highlighted_squares: Dict[str, str] = {}
        self.arrows: List[Tuple[str, str, str]] = []

        # Avatar state
        self.mood = "neutral"
        self.avatar_message = ""
        self.message_end = 0
        self.blink = False
        self.blink_time = 0
        self.next_blink = time.time() + random.uniform(2, 4)
        self.breath = 0
        self.eye_x = 0
        self.eye_y = 0

        # Emotion detection
        self.current_emotion = "neutral"
        self.emotion_confidence = 0
        self.current_frame = None
        self.frame_lock = threading.Lock()
        self.show_camera = True

        # Load calibration
        self._load_calibration()

    def _update_layout(self):
        """Update layout dimensions based on window size."""
        self.avatar_area_height = int(self.height * self.avatar_height_ratio)
        self.board_area_top = self.avatar_area_height
        self.board_area_height = self.height - self.avatar_area_height

        # Avatar base position (before user offset)
        self.avatar_base_cx = self.width // 2
        self.avatar_base_cy = self.avatar_area_height // 2
        self.avatar_base_radius = int(min(self.width, self.avatar_area_height) * 0.30)

    @property
    def avatar_cx(self):
        return self.avatar_base_cx + self.avatar_offset_x

    @property
    def avatar_cy(self):
        return self.avatar_base_cy + self.avatar_offset_y

    @property
    def avatar_radius(self):
        return int(self.avatar_base_radius * self.avatar_scale)

    def _init_corners(self):
        """Initialize board corner positions."""
        margin_x = self.width * 0.1
        margin_y = self.board_area_height * 0.1
        top = self.board_area_top + margin_y
        bottom = self.height - margin_y

        self.corners = [
            [margin_x, top],                    # a8
            [self.width - margin_x, top],       # h8
            [self.width - margin_x, bottom],    # h1
            [margin_x, bottom],                 # a1
        ]

    def _compute_squares(self):
        """Compute square positions from corners."""
        self.squares.clear()
        tl, tr, br, bl = [np.array(c) for c in self.corners]

        for fi, f in enumerate(FILES):
            for ri, r in enumerate(RANKS):
                u = (fi + 0.5) / 8
                v = 1 - (ri + 0.5) / 8
                top = tl + (tr - tl) * u
                bottom = bl + (br - bl) * u
                pos = top + (bottom - top) * v
                size = int(np.linalg.norm(tr - tl) / 8)
                self.squares[f"{f}{r}"] = Square(f, r, int(pos[0]), int(pos[1]), size)

    def _save_calibration(self):
        path = Path(__file__).parent / "calibration_combined.json"
        data = {
            "corners": self.corners,
            "avatar_offset_x": self.avatar_offset_x,
            "avatar_offset_y": self.avatar_offset_y,
            "avatar_scale": self.avatar_scale,
        }
        with open(path, "w") as f:
            json.dump(data, f)
        print(f"Calibration saved")

    def _load_calibration(self):
        path = Path(__file__).parent / "calibration_combined.json"
        if path.exists():
            try:
                with open(path) as f:
                    data = json.load(f)
                    self.corners = data.get("corners", self.corners)
                    self.avatar_offset_x = data.get("avatar_offset_x", 0)
                    self.avatar_offset_y = data.get("avatar_offset_y", 0)
                    self.avatar_scale = data.get("avatar_scale", 1.0)
                    self._compute_squares()
                    print("Loaded calibration")
            except:
                pass

    # ─────────────────────────────────────────────────────────────────
    # AVATAR DRAWING
    # ─────────────────────────────────────────────────────────────────

    def _update_avatar(self, dt):
        self.breath += dt * 2
        if not self.blink and time.time() > self.next_blink:
            self.blink = True
            self.blink_time = time.time()
        if self.blink and time.time() - self.blink_time > 0.12:
            self.blink = False
            self.next_blink = time.time() + random.uniform(2, 5)
        if random.random() < 0.02:
            self.eye_x = random.uniform(-10, 10)
            self.eye_y = random.uniform(-5, 5)
        if self.avatar_message and time.time() > self.message_end:
            self.avatar_message = ""

    def _draw_avatar(self):
        cx, cy = self.avatar_cx, self.avatar_cy
        r = int(self.avatar_radius * (1 + math.sin(self.breath) * 0.01))

        # Glow
        for i in range(3):
            gr = r + 15 + i * 8
            surf = pygame.Surface((gr*2, gr*2), pygame.SRCALPHA)
            pygame.draw.circle(surf, (*self.COLORS["glow"], 50 - i*15), (gr, gr), gr)
            self.screen.blit(surf, (cx - gr, cy - gr))

        # Face
        pygame.draw.circle(self.screen, self.COLORS["face"], (cx, cy), r)

        # Eyes
        self._draw_avatar_eyes(cx, cy, r)

        # Mouth
        self._draw_avatar_mouth(cx, cy, r)

        # Message
        if self.avatar_message:
            font = pygame.font.Font(None, 36)
            text = font.render(self.avatar_message, True, self.COLORS["glow"])
            rect = text.get_rect(center=(cx, self.avatar_area_height - 30))
            pygame.draw.rect(self.screen, (20, 20, 20), rect.inflate(20, 10), border_radius=8)
            self.screen.blit(text, rect)

    def _draw_avatar_eyes(self, cx, cy, r):
        ey = cy - r * 0.15
        sp = r * 0.35
        er = r * 0.12
        pr = er * 0.5

        if self.blink:
            for ex in [cx - sp, cx + sp]:
                pygame.draw.line(self.screen, self.COLORS["eyes"],
                    (ex - er, ey), (ex + er, ey), 3)
            return

        if self.mood == "happy":
            for ex in [cx - sp, cx + sp]:
                rect = pygame.Rect(ex - er, ey - er/2, er*2, er)
                pygame.draw.arc(self.screen, self.COLORS["eyes"], rect, 0, math.pi, 4)
        elif self.mood == "sad":
            for i, ex in enumerate([cx - sp, cx + sp]):
                pygame.draw.ellipse(self.screen, self.COLORS["eyes"],
                    (ex - er, ey - er*0.7, er*2, er*1.4))
        elif self.mood == "surprised":
            for ex in [cx - sp, cx + sp]:
                pygame.draw.circle(self.screen, self.COLORS["eyes"], (int(ex), int(ey)), int(er*1.3))
                pygame.draw.circle(self.screen, (0,0,0), (int(ex), int(ey)), int(pr*0.8))
        elif self.mood == "playful":
            pygame.draw.circle(self.screen, self.COLORS["eyes"], (int(cx-sp), int(ey)), int(er))
            pygame.draw.circle(self.screen, (0,0,0), (int(cx-sp+self.eye_x*0.3), int(ey)), int(pr))
            rect = pygame.Rect(cx+sp - er, ey - er/2, er*2, er)
            pygame.draw.arc(self.screen, self.COLORS["eyes"], rect, 0, math.pi, 4)
        else:
            for ex in [cx - sp, cx + sp]:
                pygame.draw.circle(self.screen, self.COLORS["eyes"], (int(ex), int(ey)), int(er))
                pygame.draw.circle(self.screen, (0,0,0),
                    (int(ex + self.eye_x*0.3), int(ey + self.eye_y*0.3)), int(pr))

    def _draw_avatar_mouth(self, cx, cy, r):
        my = cy + r * 0.3
        mw = r * 0.35

        if self.mood == "happy":
            rect = pygame.Rect(cx - mw, my - mw*0.3, mw*2, mw)
            pygame.draw.arc(self.screen, self.COLORS["eyes"], rect, math.pi, 2*math.pi, 4)
        elif self.mood == "sad":
            rect = pygame.Rect(cx - mw, my + mw*0.1, mw*2, mw*0.6)
            pygame.draw.arc(self.screen, self.COLORS["eyes"], rect, 0, math.pi, 4)
        elif self.mood == "surprised":
            pygame.draw.circle(self.screen, self.COLORS["eyes"], (cx, int(my + 8)), int(mw*0.25), 3)
        elif self.mood == "playful":
            pts = [(cx - mw*0.4, my), (cx + mw*0.2, my - 8), (cx + mw*0.4, my - 15)]
            pygame.draw.lines(self.screen, self.COLORS["eyes"], False, pts, 3)
        else:
            pygame.draw.line(self.screen, self.COLORS["eyes"],
                (cx - mw*0.3, my), (cx + mw*0.3, my), 3)

    # ─────────────────────────────────────────────────────────────────
    # BOARD DRAWING
    # ─────────────────────────────────────────────────────────────────

    def _draw_board_grid(self):
        tl, tr, br, bl = [np.array(c) for c in self.corners]
        for i in range(9):
            t = i / 8
            left = tl + (bl - tl) * t
            right = tr + (br - tr) * t
            pygame.draw.line(self.screen, self.COLORS["grid"],
                (int(left[0]), int(left[1])), (int(right[0]), int(right[1])), 1)
            top = tl + (tr - tl) * t
            bottom = bl + (br - bl) * t
            pygame.draw.line(self.screen, self.COLORS["grid"],
                (int(top[0]), int(top[1])), (int(bottom[0]), int(bottom[1])), 1)

    def _draw_highlights(self):
        for sq_name, hl_type in self.highlighted_squares.items():
            if sq_name not in self.squares:
                continue
            sq = self.squares[sq_name]
            colors = {
                "move": self.COLORS["highlight_move"],
                "select": self.COLORS["highlight_select"],
                "possible": self.COLORS["highlight_possible"],
                "hint": self.COLORS["highlight_hint"],
                "danger": self.COLORS["highlight_danger"],
            }
            color = colors.get(hl_type, self.COLORS["highlight_select"])
            half = sq.size // 2
            surf = pygame.Surface((sq.size, sq.size), pygame.SRCALPHA)
            surf.fill(color)
            self.screen.blit(surf, (sq.x - half, sq.y - half))
            pygame.draw.rect(self.screen, color[:3], (sq.x-half, sq.y-half, sq.size, sq.size), 2)

    def _draw_arrows(self):
        for from_sq, to_sq, arrow_type in self.arrows:
            if from_sq not in self.squares or to_sq not in self.squares:
                continue
            s1, s2 = self.squares[from_sq], self.squares[to_sq]
            color = self.COLORS["arrow"]
            pygame.draw.line(self.screen, color, (s1.x, s1.y), (s2.x, s2.y), 4)
            angle = math.atan2(s2.y - s1.y, s2.x - s1.x)
            size = 12
            p1 = (s2.x - size * math.cos(angle - 0.4), s2.y - size * math.sin(angle - 0.4))
            p2 = (s2.x - size * math.cos(angle + 0.4), s2.y - size * math.sin(angle + 0.4))
            pygame.draw.polygon(self.screen, color, [(s2.x, s2.y), p1, p2])

    def _draw_calibration_overlay(self):
        # Draw board corner markers
        labels = ["a8", "h8", "h1", "a1"]
        for i, (c, label) in enumerate(zip(self.corners, labels)):
            color = (255, 100, 100) if i == self.selected_item else self.COLORS["calibration"]
            pygame.draw.circle(self.screen, color, (int(c[0]), int(c[1])), 12)
            font = pygame.font.Font(None, 24)
            text = font.render(f"{i+1}:{label}", True, color)
            self.screen.blit(text, (int(c[0]) + 15, int(c[1]) - 8))

        points = [(int(c[0]), int(c[1])) for c in self.corners]
        pygame.draw.lines(self.screen, self.COLORS["calibration"], True, points, 2)

        # Draw avatar selection indicator
        avatar_selected = self.selected_item == self.AVATAR_ITEM
        avatar_color = (255, 100, 100) if avatar_selected else self.COLORS["calibration"]

        # Draw circle around avatar to show it's selectable
        pygame.draw.circle(self.screen, avatar_color,
            (self.avatar_cx, self.avatar_cy), self.avatar_radius + 15, 3)

        # Label for avatar
        font = pygame.font.Font(None, 24)
        label = "5:AVATAR" if avatar_selected else "5:avatar"
        text = font.render(label, True, avatar_color)
        self.screen.blit(text, (self.avatar_cx - 30, self.avatar_cy - self.avatar_radius - 35))

    def _draw_camera_preview(self):
        if not self.show_camera:
            return
        with self.frame_lock:
            if self.current_frame is None:
                return
            frame = self.current_frame.copy()
        pw, ph = 120, 90
        frame = cv2.resize(frame, (pw, ph))
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB).swapaxes(0, 1)
        surf = pygame.surfarray.make_surface(frame)
        x, y = self.width - pw - 10, 10
        pygame.draw.rect(self.screen, self.COLORS["glow"], (x-2, y-2, pw+4, ph+4), 2)
        self.screen.blit(surf, (x, y))
        font = pygame.font.Font(None, 20)
        label = f"{self.current_emotion}"
        text = font.render(label, True, self.COLORS["glow"])
        self.screen.blit(text, (x, y + ph + 5))

    def _draw_instructions(self):
        font = pygame.font.Font(None, 22)
        if self.mode == Mode.CALIBRATE:
            # Show what's selected
            if self.selected_item == self.AVATAR_ITEM:
                selected = "AVATAR"
            else:
                selected = f"Corner {self.selected_item + 1}"

            lines = [
                f"Selected: {selected} | Arrows=move | +/-=avatar size | 1-4=corners | 5=avatar | ENTER=save | R=reset",
                f"Avatar: pos=({self.avatar_offset_x}, {self.avatar_offset_y}) scale={self.avatar_scale:.2f}"
            ]
            for i, text in enumerate(lines):
                color = (150, 150, 80) if i == 0 else (80, 80, 80)
                surf = font.render(text, True, color)
                self.screen.blit(surf, (10, self.height - 45 + i * 20))
        else:
            text = "M=move H=hint C=clear ESC=calibrate Q=quit"
            surf = font.render(text, True, (80, 80, 80))
            self.screen.blit(surf, (10, self.height - 25))

    # ─────────────────────────────────────────────────────────────────
    # PUBLIC API
    # ─────────────────────────────────────────────────────────────────

    def set_mood(self, mood):
        if mood in AVATAR_MOODS:
            self.mood = mood

    def show_msg(self, text, duration=3):
        self.avatar_message = text
        self.message_end = time.time() + duration

    def highlight(self, square, hl_type="select"):
        if square in self.squares:
            self.highlighted_squares[square] = hl_type

    def show_move(self, from_sq, to_sq):
        self.highlighted_squares.clear()
        self.arrows.clear()
        self.highlight(from_sq, "move")
        self.highlight(to_sq, "move")

    def show_hint(self, from_sq, to_sq):
        self.arrows.append((from_sq, to_sq, "hint"))
        self.highlight(to_sq, "hint")

    def clear_board(self):
        self.highlighted_squares.clear()
        self.arrows.clear()

    # ─────────────────────────────────────────────────────────────────
    # MAIN LOOP
    # ─────────────────────────────────────────────────────────────────

    def handle_events(self) -> bool:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False

            elif event.type == pygame.VIDEORESIZE:
                if not self.is_fullscreen:
                    self.width, self.height = event.w, event.h
                    self.screen = pygame.display.set_mode((self.width, self.height), pygame.RESIZABLE)
                    self._update_layout()
                    self._init_corners()
                    self._compute_squares()

            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_q:
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
                    self._update_layout()
                    self._init_corners()
                    self._load_calibration()
                    self._compute_squares()

                elif self.mode == Mode.CALIBRATE:
                    self._handle_calibrate_key(event.key)
                else:
                    self._handle_play_key(event.key)

            elif event.type == pygame.MOUSEBUTTONDOWN and self.mode == Mode.CALIBRATE:
                pos = event.pos
                # Check if clicked on avatar
                avatar_dist = math.hypot(pos[0] - self.avatar_cx, pos[1] - self.avatar_cy)
                if avatar_dist < self.avatar_radius + 20:
                    self.selected_item = self.AVATAR_ITEM
                else:
                    # Select nearest corner
                    dists = [math.hypot(pos[0]-c[0], pos[1]-c[1]) for c in self.corners]
                    self.selected_item = dists.index(min(dists))

        return True

    def _handle_calibrate_key(self, key):
        amt = 5

        if key == pygame.K_LEFT:
            if self.selected_item == self.AVATAR_ITEM:
                self.avatar_offset_x -= amt
            else:
                self.corners[self.selected_item][0] -= amt
        elif key == pygame.K_RIGHT:
            if self.selected_item == self.AVATAR_ITEM:
                self.avatar_offset_x += amt
            else:
                self.corners[self.selected_item][0] += amt
        elif key == pygame.K_UP:
            if self.selected_item == self.AVATAR_ITEM:
                self.avatar_offset_y -= amt
            else:
                self.corners[self.selected_item][1] -= amt
        elif key == pygame.K_DOWN:
            if self.selected_item == self.AVATAR_ITEM:
                self.avatar_offset_y += amt
            else:
                self.corners[self.selected_item][1] += amt

        # Scale avatar with +/-
        elif key in (pygame.K_PLUS, pygame.K_EQUALS):
            self.avatar_scale = min(2.5, self.avatar_scale + 0.05)
        elif key == pygame.K_MINUS:
            self.avatar_scale = max(0.2, self.avatar_scale - 0.05)

        # Select items: 1-4 for corners, 5 or A for avatar
        elif key in [pygame.K_1, pygame.K_2, pygame.K_3, pygame.K_4]:
            self.selected_item = key - pygame.K_1
        elif key == pygame.K_5 or key == pygame.K_a:
            self.selected_item = self.AVATAR_ITEM

        elif key == pygame.K_RETURN:
            self._compute_squares()
            self._save_calibration()
            self.mode = Mode.PLAY
            self.show_msg("Calibration saved!", 2)
        elif key == pygame.K_r:
            self._init_corners()
            self.avatar_offset_x = 0
            self.avatar_offset_y = 0
            self.avatar_scale = 1.0

        self._compute_squares()

    def _handle_play_key(self, key):
        if key == pygame.K_ESCAPE:
            self.mode = Mode.CALIBRATE
        elif key == pygame.K_c:
            self.clear_board()
        elif key == pygame.K_m:
            self.show_move("e2", "e4")
            self.set_mood("happy")
            self.show_msg("e2 to e4!", 2)
        elif key == pygame.K_h:
            self.clear_board()
            self.show_hint("g1", "f3")
            self.set_mood("thinking")
            self.show_msg("Try knight to f3!", 2)

    def render(self):
        dt = self.clock.tick(60) / 1000.0
        self._update_avatar(dt)

        self.screen.fill(self.COLORS["background"])

        # Draw avatar
        self._draw_avatar()

        # Draw separator line
        pygame.draw.line(self.screen, (40, 40, 40),
            (0, self.avatar_area_height), (self.width, self.avatar_area_height), 1)

        # Draw board
        self._draw_board_grid()
        self._draw_highlights()
        self._draw_arrows()

        if self.mode == Mode.CALIBRATE:
            self._draw_calibration_overlay()

        self._draw_camera_preview()
        self._draw_instructions()

        pygame.display.flip()

    def quit(self):
        pygame.quit()


def main():
    projector = ChessCompanionProjection(1280, 720)
    emotion_queue = Queue()
    running = True

    def detect_emotions():
        cap = None
        for i in range(3):
            cap = cv2.VideoCapture(i)
            if cap.isOpened() and cap.read()[0]:
                print(f"Camera at index {i}")
                break
            if cap:
                cap.release()
            cap = None
        if not cap:
            print("No camera")
            return

        count = 0
        while running:
            ret, frame = cap.read()
            if not ret:
                continue
            with projector.frame_lock:
                projector.current_frame = frame.copy()
            count += 1
            if count % 6 != 0:
                continue
            try:
                result = DeepFace.analyze(frame, actions=["emotion"],
                    detector_backend="opencv", enforce_detection=False, silent=True)
                if result:
                    e = result[0]["dominant_emotion"]
                    emotion_queue.put(e)
            except:
                pass
        cap.release()

    print("\n=== Chess Companion Projection ===")
    print("1. Drag to projector")
    print("2. Press F for fullscreen")
    print("3. Calibrate board corners")
    print("4. ENTER to save and play!\n")

    print("Loading emotion model...")
    DeepFace.build_model(task="facial_attribute", model_name="Emotion")
    print("Ready!\n")

    thread = threading.Thread(target=detect_emotions, daemon=True)
    thread.start()

    projector.show_msg("Drag me to projector!", 4)
    last_mood_change = 0

    while projector.handle_events():
        try:
            while True:
                e = emotion_queue.get_nowait()
                projector.current_emotion = e
                mood = EMOTION_TO_MOOD.get(e, "neutral")
                if mood != projector.mood and time.time() - last_mood_change > 2:
                    projector.set_mood(mood)
                    last_mood_change = time.time()
        except Empty:
            pass

        projector.render()

    running = False
    projector.quit()


if __name__ == "__main__":
    main()
