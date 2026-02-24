"""
Integrated Chess Companion - Emotion Detection + Avatar

This combines:
- Real-time emotion detection from webcam (DeepFace)
- Responsive avatar display (pygame)
- Chess game state integration (simulated for demo)

Usage:
    python chess_companion_integrated.py

Press Q or ESC to quit.
"""

import sys
import time
import random
import threading
from pathlib import Path
from typing import Optional
from queue import Queue, Empty

# Add parent to path for deepface import
sys.path.insert(0, str(Path(__file__).parent.parent))

import cv2

try:
    import pygame
except ImportError:
    print("pygame not installed. Run: pip install pygame")
    sys.exit(1)

from deepface import DeepFace
from chess_companion_avatar import (
    ChessCompanionAvatar,
    ChessCompanion,
    AvatarMood,
)


class EmotionDetectorThread(threading.Thread):
    """
    Background thread for emotion detection.
    Runs independently so avatar stays smooth.
    """

    def __init__(self, emotion_queue: Queue, camera_index: int = 0):
        super().__init__(daemon=True)
        self.emotion_queue = emotion_queue
        self.camera_index = camera_index
        self.running = True
        self.frame_skip = 5
        self.current_frame = None
        self.lock = threading.Lock()

    def _find_camera(self) -> Optional[cv2.VideoCapture]:
        """Find working camera."""
        for i in range(3):
            cap = cv2.VideoCapture(i)
            if cap.isOpened():
                ret, _ = cap.read()
                if ret:
                    print(f"[Emotion] Found camera at index {i}")
                    return cap
                cap.release()
        return None

    def get_current_frame(self):
        """Get the most recent camera frame (thread-safe)."""
        with self.lock:
            return self.current_frame.copy() if self.current_frame is not None else None

    def run(self):
        """Main detection loop."""
        cap = self._find_camera()
        if cap is None:
            print("[Emotion] No camera found!")
            return

        print("[Emotion] Detection started")
        frame_count = 0

        while self.running:
            ret, frame = cap.read()
            if not ret:
                continue

            # Store current frame for display
            with self.lock:
                self.current_frame = frame

            frame_count += 1
            if frame_count % self.frame_skip != 0:
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
                    emotion = result[0]["dominant_emotion"]
                    confidence = result[0]["emotion"][emotion]

                    # Send to main thread
                    self.emotion_queue.put({
                        "emotion": emotion,
                        "confidence": confidence,
                        "all_emotions": result[0]["emotion"],
                        "face_region": result[0].get("region"),
                    })

            except Exception as e:
                pass  # Silently handle detection failures

        cap.release()
        print("[Emotion] Detection stopped")

    def stop(self):
        """Signal thread to stop."""
        self.running = False


class IntegratedChessCompanion:
    """
    Full integrated system combining:
    - Emotion detection (background thread)
    - Avatar rendering (main thread)
    - Chess state simulation (for demo)
    """

    def __init__(self, show_camera: bool = True):
        # Initialize avatar
        self.avatar = ChessCompanionAvatar(width=800, height=600)
        self.companion = ChessCompanion(self.avatar)

        # Emotion detection
        self.emotion_queue = Queue()
        self.emotion_thread = EmotionDetectorThread(self.emotion_queue)
        self.current_emotion = "neutral"
        self.emotion_confidence = 0.0

        # Camera preview
        self.show_camera = show_camera

        # Chess simulation state
        self.game_state = "even"
        self.last_move_quality = "normal"
        self.move_count = 0
        self.last_move_time = time.time()

        # Response timing
        self.last_emotion_response = 0
        self.emotion_stable_count = 0
        self.last_stable_emotion = "neutral"

    def _simulate_chess_events(self):
        """Simulate chess game events for demo."""
        current_time = time.time()

        # Simulate a move every 8-15 seconds
        if current_time - self.last_move_time > random.uniform(8, 15):
            self.move_count += 1
            self.last_move_time = current_time

            # Random move quality
            roll = random.random()
            if roll < 0.1:
                self.last_move_quality = "blunder"
                self.avatar.show_message("Oops, that might be a mistake...")
            elif roll < 0.3:
                self.last_move_quality = "good"
                self.avatar.show_message(random.choice([
                    "Excellent move!", "Well played!", "Nice!"
                ]))
            else:
                self.last_move_quality = "normal"

            # Update game state occasionally
            if self.move_count % 5 == 0:
                self.game_state = random.choice(["winning", "losing", "even"])
                if self.game_state == "winning":
                    self.avatar.set_theme("winning")
                elif self.game_state == "losing":
                    self.avatar.set_theme("losing")
                else:
                    self.avatar.set_theme("default")

    def _process_emotions(self):
        """Process emotion updates from the detection thread."""
        try:
            while True:  # Drain the queue
                data = self.emotion_queue.get_nowait()
                self.current_emotion = data["emotion"]
                self.emotion_confidence = data["confidence"]

                # Track emotion stability
                if self.current_emotion == self.last_stable_emotion:
                    self.emotion_stable_count += 1
                else:
                    self.emotion_stable_count = 0
                    self.last_stable_emotion = self.current_emotion

        except Empty:
            pass

        # Only respond to stable emotions (detected 3+ times in a row)
        current_time = time.time()
        if (self.emotion_stable_count >= 3 and
            current_time - self.last_emotion_response > 4.0):

            self._respond_to_emotion()
            self.last_emotion_response = current_time
            self.emotion_stable_count = 0

    def _respond_to_emotion(self):
        """Update avatar based on detected emotion."""
        emotion = self.current_emotion

        # Map player emotion to avatar response
        emotion_responses = {
            "happy": (AvatarMood.HAPPY, "You seem to be enjoying the game!"),
            "sad": (AvatarMood.ENCOURAGING, "Keep your head up! It's just a game."),
            "angry": (AvatarMood.CONCERNED, "Take a breath. You've got this!"),
            "fear": (AvatarMood.ENCOURAGING, "Don't worry, I'm here to help!"),
            "surprise": (AvatarMood.SURPRISED, "Unexpected position, huh?"),
            "disgust": (AvatarMood.PLAYFUL, "Was that move that bad?"),
            "neutral": (AvatarMood.NEUTRAL, None),
        }

        if emotion in emotion_responses:
            mood, message = emotion_responses[emotion]
            self.avatar.set_mood(mood)
            if message and self.emotion_confidence > 50:
                self.avatar.show_message(message)

    def _draw_camera_preview(self):
        """Draw small camera preview in corner."""
        if not self.show_camera:
            return

        frame = self.emotion_thread.get_current_frame()
        if frame is None:
            return

        # Resize for preview
        preview_width = 160
        preview_height = 120
        frame = cv2.resize(frame, (preview_width, preview_height))
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        # Convert to pygame surface
        frame = frame.swapaxes(0, 1)
        surface = pygame.surfarray.make_surface(frame)

        # Position in bottom-right
        x = self.avatar.width - preview_width - 10
        y = self.avatar.height - preview_height - 10

        # Draw border
        border_rect = pygame.Rect(x - 2, y - 2, preview_width + 4, preview_height + 4)
        pygame.draw.rect(self.avatar.screen, (100, 100, 100), border_rect, 2)

        self.avatar.screen.blit(surface, (x, y))

        # Draw emotion label
        font = pygame.font.Font(None, 20)
        label = f"{self.current_emotion} ({self.emotion_confidence:.0f}%)"
        text = font.render(label, True, (200, 200, 200))
        self.avatar.screen.blit(text, (x, y - 18))

    def _draw_instructions(self):
        """Draw control instructions."""
        font = pygame.font.Font(None, 20)
        instructions = [
            "Q/ESC: Quit",
            "C: Toggle camera preview",
            "SPACE: Trigger random event",
        ]
        for i, text in enumerate(instructions):
            surface = font.render(text, True, (80, 80, 80))
            self.avatar.screen.blit(surface, (10, 30 + i * 18))

    def run(self):
        """Main loop."""
        # Start emotion detection thread
        self.emotion_thread.start()
        print("\n[Main] Chess Companion started!")
        print("[Main] Press Q or ESC to quit\n")

        # Pre-load emotion model in main thread context
        print("[Main] Warming up emotion model...")
        DeepFace.build_model(task="facial_attribute", model_name="Emotion")
        print("[Main] Ready!\n")

        self.avatar.show_message("Hello! Let's play chess!", duration=3.0)

        running = True
        while running:
            # Handle events
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key in (pygame.K_ESCAPE, pygame.K_q):
                        running = False
                    elif event.key == pygame.K_c:
                        self.show_camera = not self.show_camera
                    elif event.key == pygame.K_SPACE:
                        # Trigger random event for testing
                        self._simulate_chess_events()

            # Update emotion processing
            self._process_emotions()

            # Simulate chess game
            self._simulate_chess_events()

            # Render avatar (without flip so we can add overlays)
            self.avatar.render(flip=False)

            # Draw overlays
            self._draw_camera_preview()
            self._draw_instructions()

            # Now flip
            pygame.display.flip()

        # Cleanup
        print("\n[Main] Shutting down...")
        self.emotion_thread.stop()
        self.emotion_thread.join(timeout=2.0)
        self.avatar.quit()
        print("[Main] Goodbye!")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Integrated Chess Companion")
    parser.add_argument(
        "--no-camera-preview",
        action="store_true",
        help="Hide camera preview window"
    )
    args = parser.parse_args()

    companion = IntegratedChessCompanion(show_camera=not args.no_camera_preview)
    companion.run()
