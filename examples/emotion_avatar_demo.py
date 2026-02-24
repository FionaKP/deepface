"""
Emotion-Reactive Avatar Demo

Simple demo: Your facial expression controls the avatar.
No chess logic - just emotion mirroring.

Usage:
    python emotion_avatar_demo.py

Press Q or ESC to quit.
"""

import sys
import time
import threading
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
from chess_companion_avatar import ChessCompanionAvatar, AvatarMood


# Map detected emotions to avatar moods
EMOTION_TO_MOOD = {
    "happy": AvatarMood.HAPPY,
    "sad": AvatarMood.SAD,
    "angry": AvatarMood.CONCERNED,
    "fear": AvatarMood.SURPRISED,
    "surprise": AvatarMood.SURPRISED,
    "disgust": AvatarMood.PLAYFUL,
    "neutral": AvatarMood.NEUTRAL,
}

# Messages the avatar says when mirroring your emotion
EMOTION_MESSAGES = {
    "happy": ["You look happy!", "Great mood!", "Love the smile!"],
    "sad": ["Feeling down?", "Everything okay?", "I'm here for you"],
    "angry": ["Take a deep breath", "Let's stay calm", "What's wrong?"],
    "fear": ["Don't worry!", "It's okay!", "I've got you"],
    "surprise": ["Whoa!", "Didn't expect that!", "Surprised?"],
    "disgust": ["Yikes!", "Not a fan?", "I see that face..."],
    "neutral": ["Ready when you are", "Listening...", "What's on your mind?"],
}


class EmotionMirrorDemo:
    """Simple demo: avatar mirrors your facial expressions."""

    def __init__(self):
        self.avatar = ChessCompanionAvatar(width=800, height=600)
        self.emotion_queue = Queue()
        self.running = True

        # State
        self.current_emotion = "neutral"
        self.emotion_confidence = 0.0
        self.last_message_time = 0
        self.face_region = None
        self.current_frame = None
        self.frame_lock = threading.Lock()

    def _find_camera(self):
        """Find working camera."""
        for i in range(3):
            cap = cv2.VideoCapture(i)
            if cap.isOpened():
                ret, _ = cap.read()
                if ret:
                    print(f"Camera found at index {i}")
                    return cap
                cap.release()
        return None

    def _emotion_thread(self):
        """Background thread for emotion detection."""
        cap = self._find_camera()
        if not cap:
            print("No camera found!")
            return

        frame_count = 0
        print("Emotion detection running...")

        while self.running:
            ret, frame = cap.read()
            if not ret:
                continue

            # Store frame for preview
            with self.frame_lock:
                self.current_frame = frame.copy()

            frame_count += 1
            if frame_count % 5 != 0:  # Analyze every 5th frame
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
                    self.emotion_queue.put({
                        "emotion": result[0]["dominant_emotion"],
                        "confidence": result[0]["emotion"][result[0]["dominant_emotion"]],
                        "region": result[0].get("region"),
                    })
            except:
                pass

        cap.release()

    def _draw_camera_preview(self):
        """Draw camera feed with face highlight."""
        with self.frame_lock:
            if self.current_frame is None:
                return
            frame = self.current_frame.copy()

        # Draw face rectangle if detected
        if self.face_region:
            r = self.face_region
            cv2.rectangle(
                frame,
                (r["x"], r["y"]),
                (r["x"] + r["w"], r["y"] + r["h"]),
                (0, 255, 0), 2
            )

        # Resize for preview
        preview_w, preview_h = 200, 150
        frame = cv2.resize(frame, (preview_w, preview_h))
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        frame = frame.swapaxes(0, 1)

        surface = pygame.surfarray.make_surface(frame)
        x = self.avatar.width - preview_w - 10
        y = self.avatar.height - preview_h - 10

        # Border
        pygame.draw.rect(
            self.avatar.screen,
            self.avatar.colors.accent,
            (x - 2, y - 2, preview_w + 4, preview_h + 4),
            2
        )
        self.avatar.screen.blit(surface, (x, y))

        # Emotion label
        font = pygame.font.Font(None, 24)
        label = f"{self.current_emotion.upper()} ({self.emotion_confidence:.0f}%)"
        text = font.render(label, True, self.avatar.colors.accent)
        self.avatar.screen.blit(text, (x, y - 22))

    def _draw_instructions(self):
        """Draw help text."""
        font = pygame.font.Font(None, 24)
        lines = [
            "Your expression controls the avatar!",
            "",
            "Try: smiling, frowning, looking surprised",
            "",
            "Press Q to quit",
        ]
        for i, line in enumerate(lines):
            color = self.avatar.colors.accent if i == 0 else (100, 100, 100)
            text = font.render(line, True, color)
            self.avatar.screen.blit(text, (10, 10 + i * 22))

    def run(self):
        """Main loop."""
        import random

        # Start emotion detection in background
        emotion_thread = threading.Thread(target=self._emotion_thread, daemon=True)
        emotion_thread.start()

        # Warm up model
        print("Loading emotion model...")
        DeepFace.build_model(task="facial_attribute", model_name="Emotion")
        print("Ready! Make faces at the camera.\n")

        self.avatar.show_message("Hello! Mirror my expressions!", duration=3.0)

        while self.running:
            # Handle events
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key in (pygame.K_q, pygame.K_ESCAPE):
                        self.running = False

            # Process emotion updates
            try:
                while True:
                    data = self.emotion_queue.get_nowait()
                    new_emotion = data["emotion"]
                    self.emotion_confidence = data["confidence"]
                    self.face_region = data.get("region")

                    # Update avatar if emotion changed
                    if new_emotion != self.current_emotion:
                        self.current_emotion = new_emotion

                        # Set matching mood
                        mood = EMOTION_TO_MOOD.get(new_emotion, AvatarMood.NEUTRAL)
                        self.avatar.set_mood(mood)

                        # Show message (with cooldown)
                        now = time.time()
                        if now - self.last_message_time > 2.0:
                            messages = EMOTION_MESSAGES.get(new_emotion, [])
                            if messages:
                                self.avatar.show_message(random.choice(messages))
                                self.last_message_time = now

            except Empty:
                pass

            # Render
            self.avatar.render(flip=False)
            self._draw_camera_preview()
            self._draw_instructions()
            pygame.display.flip()

        self.avatar.quit()
        print("Bye!")


if __name__ == "__main__":
    demo = EmotionMirrorDemo()
    demo.run()
