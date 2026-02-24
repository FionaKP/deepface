# Chess Companion HRI Project - Status Summary

## Team Roles

| Member | Responsibility | Status |
|--------|---------------|--------|
| **Fiona** | Emotion/gaze detection, Avatar display | ✅ Working prototype |
| **Alec** | Emotion detection support, Robot hardware (3001) | 🔄 In progress |
| **Khyat** | Voice commands → chess moves | 🔄 In progress |
| **Myrrh** | Robot actuation | 📋 Planned |

---

## Completed Work (C-term Efforts)

### Emotion Detection System
- [x] Real-time webcam face detection
- [x] 7-emotion classification (happy, sad, angry, fear, surprise, disgust, neutral)
- [x] Confidence scores for each emotion
- [x] Runs at ~20+ FPS with frame skipping
- [x] Background thread processing (non-blocking)

### Avatar Display System
- [x] Animated face with 9 expression states
- [x] Smooth animations (blinking, breathing, eye movement)
- [x] 4 color themes (default, warm, winning, losing)
- [x] Text message overlay system
- [x] Keyboard controls for testing
- [x] Camera preview integration

### Integration
- [x] Emotion detection → Avatar response pipeline
- [x] Emotion-to-mood mapping
- [x] Response messages based on detected emotion
- [x] Demo mode for presentations

---

## Simple Architecture (for slides)

```
┌─────────────────────────────────────────────────────────┐
│                        INPUTS                            │
├─────────────────┬─────────────────┬─────────────────────┤
│   📷 Camera     │   🎤 Voice      │   ♟️ Chess Board    │
│   (emotions)    │   (commands)    │   (game state)      │
└────────┬────────┴────────┬────────┴──────────┬──────────┘
         │                 │                   │
         ▼                 ▼                   ▼
┌─────────────────────────────────────────────────────────┐
│                   DECISION ENGINE                        │
│                                                          │
│  "Player is frustrated + just made a bad move"          │
│           → Show encouraging expression                  │
│           → Offer a helpful hint                         │
└────────────────────────┬────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────┐
│                       OUTPUT                             │
│                                                          │
│     😊 Animated Avatar  +  "You've got this!"           │
│     (projected on robot / display)                       │
└─────────────────────────────────────────────────────────┘
```

---

## Emotion → Response Mapping

| Detected Emotion | Avatar Mood | Example Response |
|-----------------|-------------|------------------|
| 😊 Happy | Happy | "You're in the zone!" |
| 😢 Sad | Encouraging | "Keep your head up!" |
| 😠 Angry | Concerned | "Take a breath, you've got this" |
| 😨 Fear | Encouraging | "Don't worry, I'm here to help" |
| 😲 Surprise | Surprised | "Unexpected move, huh?" |
| 😐 Neutral | Neutral | "Ready when you are" |

---

## Demo Commands

```bash
# Run the emotion-reactive avatar demo
cd ~/coding_projects/deepface
python3 examples/emotion_avatar_demo.py
```

**Controls:**
- Face the camera and make expressions
- Avatar mirrors your emotions
- Press Q to quit

---

## Next Steps

### Integration Tasks
- [ ] Connect voice command module (Khyat)
- [ ] Connect chess API (team)
- [ ] Add LLM for natural language tips
- [ ] Physical robot mounting (Myrrh, Alec)

### Enhancements
- [ ] Gaze direction tracking (looking at board vs. looking away)
- [ ] Confidence estimation from multiple signals
- [ ] Calibration for individual users
- [ ] Projector output formatting

---

## Technical Requirements

```
Python 3.10+
tensorflow
opencv-python
pygame
deepface (this repo)
```

Install: `pip install -r requirements.txt && pip install pygame`

---

## HRI Contribution

This project addresses the **emotional gap in human-computer chess**:

1. **Traditional chess AI**: Cold, no feedback, discouraging for beginners
2. **Our system**: Reads player emotions, adapts responses, feels like a supportive coach

**Key HRI concepts demonstrated:**
- Emotion recognition in real-time
- Adaptive robot behavior based on human state
- Multimodal interaction (voice + vision + display)
- Social presence through expressive avatar
