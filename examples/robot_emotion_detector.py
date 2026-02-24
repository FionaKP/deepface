"""
Real-time Emotion Detection for Human-Robot Communication

This prototype demonstrates how to use DeepFace for real-time emotion detection
that can be integrated with a robot communication system.

Usage:
    python robot_emotion_detector.py

Press 'q' to quit the application.
"""

import cv2
import time
from typing import Callable, Optional, Dict, Any, List
from dataclasses import dataclass
from collections import deque

# Ensure deepface can be imported from parent directory
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from deepface import DeepFace


@dataclass
class EmotionState:
    """Represents the current emotional state detected from a face."""
    dominant_emotion: str
    confidence: float
    all_emotions: Dict[str, float]
    face_region: Dict[str, int]
    timestamp: float


class RobotEmotionDetector:
    """
    Real-time emotion detector designed for human-robot interaction.

    Features:
    - Continuous webcam capture with emotion analysis
    - Configurable analysis frequency (skip frames for performance)
    - Emotion smoothing to reduce noise
    - Callback system for robot integration
    - Thread-safe emotion state access
    """

    # Emotion categories available
    EMOTIONS = ["angry", "disgust", "fear", "happy", "sad", "surprise", "neutral"]

    def __init__(
        self,
        camera_source: int = 0,
        detector_backend: str = "opencv",  # Fast detector for real-time
        analyze_every_n_frames: int = 5,   # Analyze every N frames
        smoothing_window: int = 3,          # Average over N detections
        on_emotion_change: Optional[Callable[[EmotionState], None]] = None,
        on_emotion_detected: Optional[Callable[[EmotionState], None]] = None,
    ):
        """
        Initialize the emotion detector.

        Args:
            camera_source: Camera index or video file path
            detector_backend: Face detector to use ('opencv', 'ssd', 'mtcnn', 'retinaface')
                            'opencv' and 'ssd' are fastest for real-time
            analyze_every_n_frames: Skip frames to improve performance
            smoothing_window: Number of detections to average for stability
            on_emotion_change: Callback when dominant emotion changes
            on_emotion_detected: Callback on every emotion detection
        """
        self.camera_source = camera_source
        self.detector_backend = detector_backend
        self.analyze_every_n_frames = analyze_every_n_frames
        self.smoothing_window = smoothing_window

        # Callbacks for robot integration
        self.on_emotion_change = on_emotion_change
        self.on_emotion_detected = on_emotion_detected

        # State tracking
        self.current_emotion: Optional[EmotionState] = None
        self.previous_dominant_emotion: Optional[str] = None
        self.emotion_history: deque = deque(maxlen=smoothing_window)

        # Performance tracking
        self.frame_count = 0
        self.fps = 0.0
        self.last_fps_time = time.time()
        self.fps_frame_count = 0

        # Pre-load the emotion model for faster first inference
        print("Loading emotion detection model...")
        DeepFace.build_model(task="facial_attribute", model_name="Emotion")
        print("Model loaded successfully!")

    def _smooth_emotions(self, emotions: Dict[str, float]) -> Dict[str, float]:
        """Average emotions over recent detections for stability."""
        self.emotion_history.append(emotions)

        if len(self.emotion_history) == 0:
            return emotions

        smoothed = {emotion: 0.0 for emotion in self.EMOTIONS}
        for hist in self.emotion_history:
            for emotion, score in hist.items():
                smoothed[emotion] += score

        count = len(self.emotion_history)
        return {k: v / count for k, v in smoothed.items()}

    def _analyze_frame(self, frame) -> Optional[EmotionState]:
        """Analyze a single frame for emotion detection."""
        try:
            results = DeepFace.analyze(
                img_path=frame,
                actions=["emotion"],
                detector_backend=self.detector_backend,
                enforce_detection=False,  # Don't raise error if no face
                silent=True,
            )

            if not results or len(results) == 0:
                return None

            # Use first detected face
            result = results[0]

            # Apply smoothing
            smoothed_emotions = self._smooth_emotions(result["emotion"])

            # Find dominant emotion from smoothed values
            dominant = max(smoothed_emotions, key=smoothed_emotions.get)
            confidence = smoothed_emotions[dominant]

            return EmotionState(
                dominant_emotion=dominant,
                confidence=confidence,
                all_emotions=smoothed_emotions,
                face_region=result["region"],
                timestamp=time.time(),
            )

        except Exception as e:
            # Silently handle detection failures
            return None

    def _draw_overlay(self, frame, emotion_state: Optional[EmotionState]) -> None:
        """Draw emotion information on the frame."""
        # Draw FPS
        cv2.putText(
            frame,
            f"FPS: {self.fps:.1f}",
            (10, 30),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (0, 255, 0),
            2,
        )

        if emotion_state is None:
            cv2.putText(
                frame,
                "No face detected",
                (10, 60),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (0, 0, 255),
                2,
            )
            return

        # Draw face rectangle
        region = emotion_state.face_region
        cv2.rectangle(
            frame,
            (region["x"], region["y"]),
            (region["x"] + region["w"], region["y"] + region["h"]),
            (0, 255, 0),
            2,
        )

        # Draw dominant emotion
        emotion_text = f"{emotion_state.dominant_emotion.upper()} ({emotion_state.confidence:.1f}%)"
        cv2.putText(
            frame,
            emotion_text,
            (region["x"], region["y"] - 10),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.9,
            (0, 255, 0),
            2,
        )

        # Draw emotion bars on the side
        bar_x = 10
        bar_y = 100
        bar_width = 150
        bar_height = 20

        for i, emotion in enumerate(self.EMOTIONS):
            score = emotion_state.all_emotions.get(emotion, 0)

            # Background bar
            cv2.rectangle(
                frame,
                (bar_x, bar_y + i * 25),
                (bar_x + bar_width, bar_y + i * 25 + bar_height),
                (50, 50, 50),
                -1,
            )

            # Score bar
            fill_width = int(bar_width * score / 100)
            color = (0, 255, 0) if emotion == emotion_state.dominant_emotion else (200, 200, 200)
            cv2.rectangle(
                frame,
                (bar_x, bar_y + i * 25),
                (bar_x + fill_width, bar_y + i * 25 + bar_height),
                color,
                -1,
            )

            # Label
            cv2.putText(
                frame,
                f"{emotion}: {score:.0f}%",
                (bar_x + 5, bar_y + i * 25 + 15),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.4,
                (255, 255, 255),
                1,
            )

    def _update_fps(self) -> None:
        """Update FPS calculation."""
        self.fps_frame_count += 1
        current_time = time.time()
        elapsed = current_time - self.last_fps_time

        if elapsed >= 1.0:
            self.fps = self.fps_frame_count / elapsed
            self.fps_frame_count = 0
            self.last_fps_time = current_time

    def _find_working_camera(self) -> Optional[cv2.VideoCapture]:
        """Find a working camera, trying multiple indices."""
        # If source is explicitly set (not default 0), use it directly
        if self.camera_source != 0:
            cap = cv2.VideoCapture(self.camera_source)
            if cap.isOpened():
                ret, _ = cap.read()
                if ret:
                    return cap
                cap.release()
            return None

        # Auto-detect working camera
        for i in range(3):
            cap = cv2.VideoCapture(i)
            if cap.isOpened():
                ret, _ = cap.read()
                if ret:
                    print(f"Found working camera at index {i}")
                    return cap
                cap.release()
        return None

    def run(self, show_video: bool = True) -> None:
        """
        Start the emotion detection loop.

        Args:
            show_video: Whether to display the video feed with overlays
        """
        cap = self._find_working_camera()

        if cap is None:
            print("ERROR: No working camera found!")
            print("Try: System Settings -> Privacy & Security -> Camera -> Enable for Terminal")
            return

        print("\nEmotion detection started!")
        print("Press 'q' to quit\n")

        try:
            while True:
                ret, frame = cap.read()
                if not ret:
                    break

                self.frame_count += 1
                self._update_fps()

                # Analyze every N frames for performance
                if self.frame_count % self.analyze_every_n_frames == 0:
                    emotion_state = self._analyze_frame(frame)

                    if emotion_state:
                        self.current_emotion = emotion_state

                        # Fire callback on every detection
                        if self.on_emotion_detected:
                            self.on_emotion_detected(emotion_state)

                        # Check for emotion change
                        if emotion_state.dominant_emotion != self.previous_dominant_emotion:
                            self.previous_dominant_emotion = emotion_state.dominant_emotion

                            # Fire callback on emotion change
                            if self.on_emotion_change:
                                self.on_emotion_change(emotion_state)

                # Display video with overlays
                if show_video:
                    self._draw_overlay(frame, self.current_emotion)
                    cv2.imshow("Robot Emotion Detector", frame)

                    if cv2.waitKey(1) & 0xFF == ord("q"):
                        break

        finally:
            cap.release()
            cv2.destroyAllWindows()
            print("\nEmotion detection stopped.")

    def get_current_emotion(self) -> Optional[EmotionState]:
        """Get the most recently detected emotion state."""
        return self.current_emotion


# =============================================================================
# Robot Integration Examples
# =============================================================================

def example_emotion_change_handler(emotion_state: EmotionState) -> None:
    """
    Example callback for when emotion changes.

    In a real robot system, this would send commands to the robot controller.
    """
    print(f"\n[EMOTION CHANGED] -> {emotion_state.dominant_emotion.upper()}")
    print(f"  Confidence: {emotion_state.confidence:.1f}%")

    # Example robot responses based on emotion
    robot_responses = {
        "happy": "Robot: I see you're happy! That makes me happy too!",
        "sad": "Robot: You seem sad. Is there anything I can help with?",
        "angry": "Robot: I notice you might be frustrated. Let me try to help.",
        "surprise": "Robot: Oh! Something surprised you!",
        "fear": "Robot: Don't worry, I'm here to help.",
        "disgust": "Robot: I sense some displeasure. What's wrong?",
        "neutral": "Robot: Ready and listening.",
    }

    response = robot_responses.get(emotion_state.dominant_emotion, "Robot: I'm observing...")
    print(f"  {response}\n")


def example_continuous_emotion_handler(emotion_state: EmotionState) -> None:
    """
    Example callback for continuous emotion monitoring.

    Useful for logging or real-time telemetry.
    """
    # Print compact status line (overwrites previous)
    emotions_str = " | ".join(
        f"{e[:3]}:{emotion_state.all_emotions[e]:.0f}"
        for e in ["happy", "sad", "angry", "neutral"]
    )
    print(f"\r[{emotion_state.dominant_emotion:>8}] {emotions_str}", end="", flush=True)


# =============================================================================
# Main Entry Point
# =============================================================================

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Real-time emotion detection for human-robot communication"
    )
    parser.add_argument(
        "--camera", "-c",
        type=int,
        default=0,
        help="Camera index (default: 0)"
    )
    parser.add_argument(
        "--detector", "-d",
        type=str,
        default="opencv",
        choices=["opencv", "ssd", "mtcnn", "retinaface", "mediapipe"],
        help="Face detector backend (default: opencv)"
    )
    parser.add_argument(
        "--skip-frames", "-s",
        type=int,
        default=3,
        help="Analyze every N frames (default: 3, lower = more CPU)"
    )
    parser.add_argument(
        "--no-video",
        action="store_true",
        help="Run without video display (headless mode)"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Print continuous emotion updates"
    )

    args = parser.parse_args()

    # Create detector with example callbacks
    detector = RobotEmotionDetector(
        camera_source=args.camera,
        detector_backend=args.detector,
        analyze_every_n_frames=args.skip_frames,
        smoothing_window=3,
        on_emotion_change=example_emotion_change_handler,
        on_emotion_detected=example_continuous_emotion_handler if args.verbose else None,
    )

    # Run the detector
    detector.run(show_video=not args.no_video)
