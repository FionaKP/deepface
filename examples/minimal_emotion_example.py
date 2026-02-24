"""
Minimal example: Real-time emotion detection with DeepFace

This is the simplest possible integration for human-robot communication.
Copy and adapt this pattern for your robot system.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import cv2
from deepface import DeepFace

def get_emotion_from_frame(frame):
    """Analyze a frame and return the dominant emotion."""
    try:
        result = DeepFace.analyze(
            img_path=frame,
            actions=["emotion"],
            detector_backend="opencv",  # Fast detector
            enforce_detection=False,
            silent=True,
        )
        if result:
            return result[0]["dominant_emotion"], result[0]["emotion"]
    except:
        pass
    return None, {}


def find_working_camera():
    """Find the first working camera index."""
    for i in range(3):
        cap = cv2.VideoCapture(i)
        if cap.isOpened():
            ret, _ = cap.read()
            if ret:
                print(f"Found working camera at index {i}")
                return cap
            cap.release()
    return None


def main():
    # Open webcam - auto-detect working camera
    cap = find_working_camera()
    if cap is None:
        print("ERROR: No working camera found!")
        print("Grant camera permission: System Settings -> Privacy & Security -> Camera")
        return

    frame_count = 0
    current_emotion = "unknown"

    print("Starting emotion detection... Press 'q' to quit")

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        frame_count += 1

        # Analyze every 5 frames for performance
        if frame_count % 5 == 0:
            emotion, scores = get_emotion_from_frame(frame)
            if emotion:
                current_emotion = emotion

                # === YOUR ROBOT INTEGRATION HERE ===
                # Send emotion to your robot controller:
                # robot.set_emotional_response(emotion)
                # ros_publisher.publish(emotion)
                # serial_port.write(emotion.encode())

                print(f"Detected: {emotion}")

        # Display
        cv2.putText(frame, f"Emotion: {current_emotion}", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        cv2.imshow("Emotion Detection", frame)

        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
