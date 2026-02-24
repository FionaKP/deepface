"""
Avatar Projector Display

Optimized for projection:
- Fullscreen on secondary display (projector)
- High contrast colors for projection
- Larger face for visibility
- Black background (projector-friendly)
- Position controls for alignment

Usage:
    python avatar_projector.py --list-displays     # See available displays
    python avatar_projector.py --display 1         # Use display 1 (projector)
    python avatar_projector.py --fullscreen        # Fullscreen mode

Controls:
    F: Toggle fullscreen
    Arrow keys: Nudge avatar position (for alignment)
    +/-: Scale avatar size
    1-9: Change expression
    C: Toggle camera preview
    Q/ESC: Quit
"""

import sys
import os
import threading
from pathlib import Path
from queue import Queue, Empty

sys.path.insert(0, str(Path(__file__).parent.parent))

# Set SDL to use a specific display before pygame init
# This must happen before importing pygame
def set_display(display_num: int):
    os.environ['SDL_VIDEO_FULLSCREEN_DISPLAY'] = str(display_num)

import cv2

try:
    import pygame
    from pygame.locals import *
except ImportError:
    print("Install pygame: pip install pygame")
    sys.exit(1)

from deepface import DeepFace
from chess_companion_avatar import AvatarMood, AvatarColors


# High contrast colors optimized for projection
PROJECTOR_THEMES = {
    "default": AvatarColors(
        background=(0, 0, 0),           # Pure black (no light)
        face=(80, 180, 255),            # Bright blue
        eyes=(255, 255, 255),           # White
        mouth=(255, 255, 255),          # White
        accent=(120, 200, 255),         # Light blue
    ),
    "warm": AvatarColors(
        background=(0, 0, 0),
        face=(255, 180, 80),            # Orange
        eyes=(255, 255, 255),
        mouth=(255, 255, 255),
        accent=(255, 220, 150),
    ),
    "winning": AvatarColors(
        background=(0, 0, 0),
        face=(80, 255, 120),            # Green
        eyes=(255, 255, 255),
        mouth=(255, 255, 255),
        accent=(150, 255, 180),
    ),
    "losing": AvatarColors(
        background=(0, 0, 0),
        face=(255, 100, 100),           # Red/pink
        eyes=(255, 255, 255),
        mouth=(255, 255, 255),
        accent=(255, 150, 150),
    ),
    "thinking": AvatarColors(
        background=(0, 0, 0),
        face=(180, 150, 255),           # Purple
        eyes=(255, 255, 255),
        mouth=(255, 255, 255),
        accent=(200, 180, 255),
    ),
}

# Emotion mapping
EMOTION_TO_MOOD = {
    "happy": AvatarMood.HAPPY,
    "sad": AvatarMood.SAD,
    "angry": AvatarMood.CONCERNED,
    "fear": AvatarMood.SURPRISED,
    "surprise": AvatarMood.SURPRISED,
    "disgust": AvatarMood.PLAYFUL,
    "neutral": AvatarMood.NEUTRAL,
}


def list_displays():
    """List available displays."""
    pygame.init()
    num_displays = pygame.display.get_num_displays()
    print(f"\nFound {num_displays} display(s):\n")

    for i in range(num_displays):
        try:
            mode = pygame.display.get_desktop_sizes()[i]
            print(f"  Display {i}: {mode[0]}x{mode[1]}")
            if i == 0:
                print("             (primary - probably your laptop)")
            else:
                print("             (secondary - probably projector)")
        except:
            print(f"  Display {i}: (unable to get size)")

    print("\nUse --display N to select a display")
    print("Example: python avatar_projector.py --display 1 --fullscreen\n")
    pygame.quit()


def get_display_position(display_num: int):
    """
    Get the x,y position of a display.
    On macOS, displays are arranged left-to-right typically.
    """
    # This is a workaround since pygame doesn't expose display positions directly
    # We'll estimate based on display sizes
    sizes = pygame.display.get_desktop_sizes()
    x_offset = 0
    for i in range(display_num):
        if i < len(sizes):
            x_offset += sizes[i][0]
    return x_offset, 0


class ProjectorAvatar:
    """Avatar optimized for projector display."""

    def __init__(
        self,
        display_num: int = 0,
        fullscreen: bool = False,
        width: int = 1280,
        height: int = 720,
    ):
        pygame.init()
        pygame.display.set_caption("Chess Companion - Projector")

        self.display_num = display_num

        # Get display info
        try:
            displays = pygame.display.get_desktop_sizes()
            if display_num < len(displays):
                disp_size = displays[display_num]
                print(f"Target display {display_num}: {disp_size[0]}x{disp_size[1]}")
                if fullscreen:
                    width, height = disp_size
            else:
                print(f"Display {display_num} not found, using display 0")
                display_num = 0
        except Exception as e:
            print(f"Display detection error: {e}")
            print(f"Using default size: {width}x{height}")

        self.width = width
        self.height = height
        self.fullscreen = fullscreen

        # For secondary displays on macOS, use positioned borderless window
        # instead of true fullscreen (which always captures primary display)
        if fullscreen and display_num > 0:
            # Position window on the secondary display
            display_x, display_y = get_display_position(display_num)
            os.environ['SDL_VIDEO_WINDOW_POS'] = f"{display_x},{display_y}"

            # Create borderless window (fake fullscreen)
            self.screen = pygame.display.set_mode((width, height), pygame.NOFRAME)
            print(f"Positioned borderless window at ({display_x}, {display_y})")

        elif fullscreen:
            # Primary display can use real fullscreen
            self.screen = pygame.display.set_mode((width, height), pygame.FULLSCREEN)

        else:
            # Windowed mode
            if display_num > 0:
                display_x, display_y = get_display_position(display_num)
                os.environ['SDL_VIDEO_WINDOW_POS'] = f"{display_x + 50},{display_y + 50}"
            self.screen = pygame.display.set_mode((width, height))

        self.clock = pygame.time.Clock()

        # Avatar properties
        self.colors = PROJECTOR_THEMES["default"]
        self.mood = AvatarMood.NEUTRAL
        self.message = ""
        self.message_timer = 0

        # Position and scale (for projector alignment)
        self.offset_x = 0
        self.offset_y = 0
        self.scale = 1.0

        # Animation state
        self.blink_timer = 0
        self.is_blinking = False
        self.next_blink = 0
        self.breath_phase = 0
        self.eye_offset_x = 0
        self.eye_offset_y = 0

        # Face size
        self.base_face_radius = min(width, height) * 0.35

        # Camera/emotion state
        self.show_camera = False
        self.current_frame = None
        self.frame_lock = threading.Lock()
        self.current_emotion = "neutral"
        self.emotion_confidence = 0

        import time
        import random
        self.time = time
        self.random = random
        self.next_blink = time.time() + random.uniform(2, 4)

    @property
    def face_radius(self):
        return self.base_face_radius * self.scale

    @property
    def center_x(self):
        return self.width // 2 + self.offset_x

    @property
    def center_y(self):
        return self.height // 2 + self.offset_y

    def set_mood(self, mood: AvatarMood):
        self.mood = mood

    def set_theme(self, theme_name: str):
        if theme_name in PROJECTOR_THEMES:
            self.colors = PROJECTOR_THEMES[theme_name]

    def show_message(self, message: str, duration: float = 3.0):
        self.message = message
        self.message_timer = self.time.time() + duration

    def _update_animations(self, dt: float):
        """Update animation states."""
        current_time = self.time.time()

        # Blinking
        if not self.is_blinking and current_time >= self.next_blink:
            self.is_blinking = True
            self.blink_timer = current_time

        if self.is_blinking and current_time - self.blink_timer > 0.15:
            self.is_blinking = False
            self.next_blink = current_time + self.random.uniform(2, 5)

        # Eye drift
        if self.random.random() < 0.02:
            self.eye_offset_x = self.random.uniform(-15, 15) * self.scale
            self.eye_offset_y = self.random.uniform(-8, 8) * self.scale

        # Breathing
        import math
        self.breath_phase += dt * 1.5
        if self.breath_phase > 2 * math.pi:
            self.breath_phase -= 2 * math.pi

        # Message timeout
        if self.message and current_time > self.message_timer:
            self.message = ""

    def _draw_face(self):
        """Draw the avatar face."""
        import math

        breath_scale = 1 + math.sin(self.breath_phase) * 0.015
        radius = int(self.face_radius * breath_scale)

        # Glow effect (multiple circles)
        for i in range(4):
            glow_radius = radius + 15 + i * 8
            alpha = 60 - i * 15
            glow_surface = pygame.Surface((glow_radius * 2, glow_radius * 2), pygame.SRCALPHA)
            pygame.draw.circle(
                glow_surface,
                (*self.colors.accent, alpha),
                (glow_radius, glow_radius),
                glow_radius
            )
            self.screen.blit(
                glow_surface,
                (self.center_x - glow_radius, self.center_y - glow_radius)
            )

        # Main face
        pygame.draw.circle(
            self.screen,
            self.colors.face,
            (self.center_x, self.center_y),
            radius
        )

    def _draw_eyes(self):
        """Draw eyes based on mood."""
        import math

        eye_y = self.center_y - self.face_radius * 0.15
        eye_spacing = self.face_radius * 0.35
        eye_radius = self.face_radius * 0.14
        pupil_radius = eye_radius * 0.5

        left_eye_x = self.center_x - eye_spacing
        right_eye_x = self.center_x + eye_spacing

        if self.is_blinking:
            # Closed eyes
            for eye_x in [left_eye_x, right_eye_x]:
                pygame.draw.line(
                    self.screen,
                    self.colors.eyes,
                    (eye_x - eye_radius, eye_y),
                    (eye_x + eye_radius, eye_y),
                    max(3, int(4 * self.scale))
                )
            return

        line_width = max(3, int(4 * self.scale))

        if self.mood in (AvatarMood.HAPPY, AvatarMood.CELEBRATING):
            # Happy curved eyes
            for eye_x in [left_eye_x, right_eye_x]:
                rect = pygame.Rect(
                    eye_x - eye_radius,
                    eye_y - eye_radius // 2,
                    eye_radius * 2,
                    eye_radius
                )
                pygame.draw.arc(self.screen, self.colors.eyes, rect, 0, math.pi, line_width)

        elif self.mood in (AvatarMood.SAD, AvatarMood.CONCERNED):
            # Sad droopy eyes
            for i, eye_x in enumerate([left_eye_x, right_eye_x]):
                pygame.draw.ellipse(
                    self.screen,
                    self.colors.eyes,
                    (eye_x - eye_radius, eye_y - eye_radius * 0.7,
                     eye_radius * 2, eye_radius * 1.4)
                )
                # Sad eyebrow
                brow_dir = 1 if i == 0 else -1
                pygame.draw.line(
                    self.screen,
                    self.colors.face,
                    (eye_x - eye_radius * brow_dir, eye_y - eye_radius * 1.4),
                    (eye_x + eye_radius * brow_dir, eye_y - eye_radius),
                    line_width
                )

        elif self.mood == AvatarMood.SURPRISED:
            # Big round eyes
            for eye_x in [left_eye_x, right_eye_x]:
                pygame.draw.circle(
                    self.screen, self.colors.eyes,
                    (int(eye_x), int(eye_y)), int(eye_radius * 1.4)
                )
                pygame.draw.circle(
                    self.screen, (0, 0, 0),
                    (int(eye_x + self.eye_offset_x * 0.3),
                     int(eye_y + self.eye_offset_y * 0.3)),
                    int(pupil_radius)
                )

        elif self.mood == AvatarMood.THINKING:
            # Looking up/sideways
            for eye_x in [left_eye_x, right_eye_x]:
                pygame.draw.circle(
                    self.screen, self.colors.eyes,
                    (int(eye_x), int(eye_y)), int(eye_radius)
                )
                pygame.draw.circle(
                    self.screen, (0, 0, 0),
                    (int(eye_x + 10 * self.scale), int(eye_y - 6 * self.scale)),
                    int(pupil_radius)
                )

        elif self.mood == AvatarMood.PLAYFUL:
            # Winking
            pygame.draw.circle(
                self.screen, self.colors.eyes,
                (int(left_eye_x), int(eye_y)), int(eye_radius)
            )
            pygame.draw.circle(
                self.screen, (0, 0, 0),
                (int(left_eye_x + self.eye_offset_x * 0.5),
                 int(eye_y + self.eye_offset_y * 0.5)),
                int(pupil_radius)
            )
            # Wink
            rect = pygame.Rect(
                right_eye_x - eye_radius,
                eye_y - eye_radius // 2,
                eye_radius * 2,
                eye_radius
            )
            pygame.draw.arc(self.screen, self.colors.eyes, rect, 0, math.pi, line_width)

        else:
            # Neutral eyes
            for eye_x in [left_eye_x, right_eye_x]:
                pygame.draw.circle(
                    self.screen, self.colors.eyes,
                    (int(eye_x), int(eye_y)), int(eye_radius)
                )
                pygame.draw.circle(
                    self.screen, (0, 0, 0),
                    (int(eye_x + self.eye_offset_x * 0.5),
                     int(eye_y + self.eye_offset_y * 0.5)),
                    int(pupil_radius)
                )

    def _draw_mouth(self):
        """Draw mouth based on mood."""
        import math

        mouth_y = self.center_y + self.face_radius * 0.32
        mouth_width = self.face_radius * 0.45
        line_width = max(3, int(5 * self.scale))

        if self.mood in (AvatarMood.HAPPY, AvatarMood.CELEBRATING):
            rect = pygame.Rect(
                self.center_x - mouth_width,
                mouth_y - mouth_width * 0.4,
                mouth_width * 2,
                mouth_width * 1.2
            )
            pygame.draw.arc(self.screen, self.colors.mouth, rect, math.pi, 2 * math.pi, line_width)

        elif self.mood == AvatarMood.SAD:
            rect = pygame.Rect(
                self.center_x - mouth_width,
                mouth_y + mouth_width * 0.2,
                mouth_width * 2,
                mouth_width * 0.8
            )
            pygame.draw.arc(self.screen, self.colors.mouth, rect, 0, math.pi, line_width)

        elif self.mood == AvatarMood.SURPRISED:
            pygame.draw.circle(
                self.screen, self.colors.mouth,
                (self.center_x, int(mouth_y + 15 * self.scale)),
                int(mouth_width * 0.35), line_width
            )

        elif self.mood == AvatarMood.THINKING:
            pygame.draw.circle(
                self.screen, self.colors.mouth,
                (int(self.center_x + 20 * self.scale), int(mouth_y)),
                int(mouth_width * 0.15), line_width
            )

        elif self.mood == AvatarMood.PLAYFUL:
            points = [
                (self.center_x - mouth_width * 0.5, mouth_y),
                (self.center_x + mouth_width * 0.3, mouth_y - 15 * self.scale),
                (self.center_x + mouth_width * 0.5, mouth_y - 25 * self.scale),
            ]
            pygame.draw.lines(self.screen, self.colors.mouth, False, points, line_width)

        elif self.mood == AvatarMood.ENCOURAGING:
            rect = pygame.Rect(
                self.center_x - mouth_width * 0.6,
                mouth_y - mouth_width * 0.2,
                mouth_width * 1.2,
                mouth_width * 0.6
            )
            pygame.draw.arc(self.screen, self.colors.mouth, rect, math.pi, 2 * math.pi, line_width - 1)

        elif self.mood == AvatarMood.CONCERNED:
            points = [
                (self.center_x - mouth_width * 0.4, mouth_y),
                (self.center_x - mouth_width * 0.15, mouth_y + 8 * self.scale),
                (self.center_x + mouth_width * 0.15, mouth_y - 8 * self.scale),
                (self.center_x + mouth_width * 0.4, mouth_y),
            ]
            pygame.draw.lines(self.screen, self.colors.mouth, False, points, line_width - 1)

        else:
            pygame.draw.line(
                self.screen, self.colors.mouth,
                (self.center_x - mouth_width * 0.4, mouth_y),
                (self.center_x + mouth_width * 0.4, mouth_y),
                line_width
            )

    def _draw_message(self):
        """Draw message text."""
        if not self.message:
            return

        font_size = max(32, int(48 * self.scale))
        font = pygame.font.Font(None, font_size)
        text = font.render(self.message, True, self.colors.accent)
        rect = text.get_rect(center=(self.center_x, self.height - 80))

        # Background
        padding = 20
        bg_rect = rect.inflate(padding * 2, padding)
        pygame.draw.rect(self.screen, (20, 20, 20), bg_rect, border_radius=15)
        pygame.draw.rect(self.screen, self.colors.accent, bg_rect, 2, border_radius=15)

        self.screen.blit(text, rect)

    def _draw_debug_info(self):
        """Draw position/scale info for alignment."""
        font = pygame.font.Font(None, 24)
        info = [
            f"Offset: ({self.offset_x}, {self.offset_y})",
            f"Scale: {self.scale:.2f}",
            f"Mood: {self.mood.value}",
            f"Emotion: {self.current_emotion} ({self.emotion_confidence:.0f}%)",
            "",
            "Arrow keys: move | +/-: scale | F: fullscreen",
        ]
        for i, line in enumerate(info):
            text = font.render(line, True, (80, 80, 80))
            self.screen.blit(text, (10, 10 + i * 20))

    def _draw_camera_preview(self):
        """Draw camera preview in corner."""
        if not self.show_camera:
            return

        with self.frame_lock:
            if self.current_frame is None:
                return
            frame = self.current_frame.copy()

        # Small preview
        preview_w, preview_h = 160, 120
        frame = cv2.resize(frame, (preview_w, preview_h))
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        frame = frame.swapaxes(0, 1)

        surface = pygame.surfarray.make_surface(frame)
        x, y = self.width - preview_w - 10, 10

        pygame.draw.rect(self.screen, self.colors.accent, (x-2, y-2, preview_w+4, preview_h+4), 2)
        self.screen.blit(surface, (x, y))

    def render(self):
        """Render one frame."""
        dt = self.clock.tick(60) / 1000.0
        self._update_animations(dt)

        self.screen.fill(self.colors.background)
        self._draw_face()
        self._draw_eyes()
        self._draw_mouth()
        self._draw_message()
        self._draw_debug_info()
        self._draw_camera_preview()

        pygame.display.flip()

    def handle_events(self) -> bool:
        """Handle input events. Returns False to quit."""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False

            elif event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_q, pygame.K_ESCAPE):
                    return False

                # Position adjustment
                elif event.key == pygame.K_LEFT:
                    self.offset_x -= 20
                elif event.key == pygame.K_RIGHT:
                    self.offset_x += 20
                elif event.key == pygame.K_UP:
                    self.offset_y -= 20
                elif event.key == pygame.K_DOWN:
                    self.offset_y += 20

                # Scale
                elif event.key in (pygame.K_PLUS, pygame.K_EQUALS):
                    self.scale = min(2.0, self.scale + 0.1)
                elif event.key == pygame.K_MINUS:
                    self.scale = max(0.3, self.scale - 0.1)

                # Fullscreen toggle
                elif event.key == pygame.K_f:
                    self.fullscreen = not self.fullscreen
                    if self.fullscreen:
                        if self.display_num > 0:
                            # Secondary display: use borderless
                            display_x, _ = get_display_position(self.display_num)
                            os.environ['SDL_VIDEO_WINDOW_POS'] = f"{display_x},0"
                            self.screen = pygame.display.set_mode(
                                (self.width, self.height), pygame.NOFRAME
                            )
                        else:
                            self.screen = pygame.display.set_mode(
                                (self.width, self.height), pygame.FULLSCREEN
                            )
                    else:
                        self.screen = pygame.display.set_mode(
                            (self.width, self.height)
                        )

                # Camera toggle
                elif event.key == pygame.K_c:
                    self.show_camera = not self.show_camera

                # Mood shortcuts (for testing)
                elif event.key == pygame.K_1:
                    self.set_mood(AvatarMood.NEUTRAL)
                elif event.key == pygame.K_2:
                    self.set_mood(AvatarMood.HAPPY)
                elif event.key == pygame.K_3:
                    self.set_mood(AvatarMood.SAD)
                elif event.key == pygame.K_4:
                    self.set_mood(AvatarMood.THINKING)
                elif event.key == pygame.K_5:
                    self.set_mood(AvatarMood.SURPRISED)
                elif event.key == pygame.K_6:
                    self.set_mood(AvatarMood.PLAYFUL)
                elif event.key == pygame.K_7:
                    self.set_mood(AvatarMood.ENCOURAGING)
                elif event.key == pygame.K_8:
                    self.set_mood(AvatarMood.CONCERNED)
                elif event.key == pygame.K_9:
                    self.set_mood(AvatarMood.CELEBRATING)

                # Theme shortcuts
                elif event.key == pygame.K_t:
                    themes = list(PROJECTOR_THEMES.keys())
                    current = [k for k, v in PROJECTOR_THEMES.items()
                              if v == self.colors][0]
                    idx = (themes.index(current) + 1) % len(themes)
                    self.set_theme(themes[idx])
                    self.show_message(f"Theme: {themes[idx]}", 1.5)

        return True

    def quit(self):
        pygame.quit()


def run_with_emotion_detection(avatar: ProjectorAvatar):
    """Run avatar with emotion detection."""
    emotion_queue = Queue()
    running = True

    def emotion_thread():
        """Background emotion detection."""
        cap = None
        for i in range(3):
            cap = cv2.VideoCapture(i)
            if cap.isOpened():
                ret, _ = cap.read()
                if ret:
                    print(f"Camera found at index {i}")
                    break
                cap.release()
                cap = None

        if not cap:
            print("No camera found - avatar will respond to keyboard only")
            return

        frame_count = 0
        while running:
            ret, frame = cap.read()
            if not ret:
                continue

            with avatar.frame_lock:
                avatar.current_frame = frame.copy()

            frame_count += 1
            if frame_count % 5 != 0:
                continue

            try:
                result = DeepFace.analyze(
                    img_path=frame,
                    actions=["emotion"],
                    detector_backend="opencv",
                    enforce_detection=False,
                    silent=True,
                )
                if result:
                    emotion_queue.put({
                        "emotion": result[0]["dominant_emotion"],
                        "confidence": result[0]["emotion"][result[0]["dominant_emotion"]],
                    })
            except:
                pass

        cap.release()

    # Start emotion detection
    import time
    import random

    print("Loading emotion model...")
    DeepFace.build_model(task="facial_attribute", model_name="Emotion")
    print("Ready!")

    thread = threading.Thread(target=emotion_thread, daemon=True)
    thread.start()

    avatar.show_message("Hello! I'm your chess companion.", 3.0)
    last_emotion_change = 0

    while avatar.handle_events():
        # Process emotions
        try:
            while True:
                data = emotion_queue.get_nowait()
                avatar.current_emotion = data["emotion"]
                avatar.emotion_confidence = data["confidence"]

                # Update mood
                mood = EMOTION_TO_MOOD.get(data["emotion"], AvatarMood.NEUTRAL)
                if mood != avatar.mood:
                    avatar.set_mood(mood)

                    # Occasional message
                    if time.time() - last_emotion_change > 3.0:
                        messages = {
                            "happy": "You seem happy!",
                            "sad": "Everything okay?",
                            "angry": "Take a breath...",
                            "surprise": "Surprised?",
                            "neutral": "",
                        }
                        msg = messages.get(data["emotion"], "")
                        if msg:
                            avatar.show_message(msg, 2.0)
                        last_emotion_change = time.time()
        except Empty:
            pass

        avatar.render()

    running = False
    avatar.quit()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Avatar Projector Display")
    parser.add_argument("--list-displays", action="store_true",
                       help="List available displays and exit")
    parser.add_argument("--display", "-d", type=int, default=0,
                       help="Display number to use (0=primary, 1=secondary/projector)")
    parser.add_argument("--fullscreen", "-f", action="store_true",
                       help="Start in fullscreen mode")
    parser.add_argument("--width", type=int, default=1280,
                       help="Window width (if not fullscreen)")
    parser.add_argument("--height", type=int, default=720,
                       help="Window height (if not fullscreen)")
    parser.add_argument("--no-emotion", action="store_true",
                       help="Disable emotion detection (keyboard only)")

    args = parser.parse_args()

    if args.list_displays:
        list_displays()
        sys.exit(0)

    print(f"\nStarting avatar on display {args.display}")
    print("Controls:")
    print("  Arrow keys: Move avatar position")
    print("  +/-: Scale avatar size")
    print("  F: Toggle fullscreen")
    print("  T: Cycle color themes")
    print("  C: Toggle camera preview")
    print("  1-9: Change expression")
    print("  Q/ESC: Quit\n")

    avatar = ProjectorAvatar(
        display_num=args.display,
        fullscreen=args.fullscreen,
        width=args.width,
        height=args.height,
    )

    if args.no_emotion:
        # Simple loop without emotion detection
        while avatar.handle_events():
            avatar.render()
        avatar.quit()
    else:
        run_with_emotion_detection(avatar)
