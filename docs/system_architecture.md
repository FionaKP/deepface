# Chess Companion HRI System Architecture

## High-Level System Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              USER (Chess Player)                             │
└──────────────┬───────────────────┬───────────────────┬──────────────────────┘
               │                   │                   │
               ▼                   ▼                   ▼
┌──────────────────────┐ ┌─────────────────┐ ┌────────────────────┐
│    FACE/EMOTION      │ │  VOICE COMMAND  │ │    CHESS BOARD     │
│      CAMERA          │ │   MICROPHONE    │ │   (Physical/UI)    │
│                      │ │                 │ │                    │
│  - Webcam capture    │ │  - Audio input  │ │  - Move detection  │
│  - Face detection    │ │  - Speech-to-   │ │  - Board state     │
│  - Emotion analysis  │ │    text (STT)   │ │                    │
└──────────┬───────────┘ └────────┬────────┘ └─────────┬──────────┘
           │                      │                    │
           ▼                      ▼                    ▼
┌──────────────────────┐ ┌─────────────────┐ ┌────────────────────┐
│     DeepFace         │ │  Voice Command  │ │    Chess API       │
│                      │ │    Parser       │ │    (Stockfish)     │
│  Outputs:            │ │                 │ │                    │
│  - dominant_emotion  │ │  Outputs:       │ │  Outputs:          │
│  - confidence %      │ │  - move (e4,d5) │ │  - legal moves     │
│  - 7 emotion scores  │ │  - commands     │ │  - evaluation      │
│                      │ │    (hint, undo) │ │  - best move       │
└──────────┬───────────┘ └────────┬────────┘ └─────────┬──────────┘
           │                      │                    │
           └──────────────────────┼────────────────────┘
                                  │
                                  ▼
        ┌─────────────────────────────────────────────────────┐
        │                 DECISION ENGINE                      │
        │                                                      │
        │   Inputs:                                            │
        │   - Player emotion (happy, frustrated, confused)     │
        │   - Player confidence level                          │
        │   - Board state (FEN notation)                       │
        │   - Move quality (blunder, good, excellent)          │
        │   - Game phase (opening, middle, endgame)            │
        │                                                      │
        │   Logic:                                             │
        │   - If frustrated + just blundered → encourage       │
        │   - If confident + winning → playful banter          │
        │   - If confused + difficult position → offer hint    │
        │                                                      │
        └──────────────────────┬──────────────────────────────┘
                               │
                               ▼
        ┌─────────────────────────────────────────────────────┐
        │                    LLM MODULE                        │
        │              (Optional Enhancement)                  │
        │                                                      │
        │   Prompt:                                            │
        │   "Board: [FEN], Player emotion: frustrated,         │
        │    Last move was a blunder. Generate supportive      │
        │    message and hint."                                │
        │                                                      │
        │   Output: Natural language advice/banter             │
        └──────────────────────┬──────────────────────────────┘
                               │
                               ▼
        ┌─────────────────────────────────────────────────────┐
        │                 AVATAR RENDERER                      │
        │                                                      │
        │   Inputs:                                            │
        │   - Mood (happy, thinking, encouraging, etc.)        │
        │   - Color theme (winning=green, losing=purple)       │
        │   - Message text                                     │
        │                                                      │
        │   Outputs:                                           │
        │   - Animated face with expression                    │
        │   - Text overlay with tips/banter                    │
        └──────────────────────┬──────────────────────────────┘
                               │
                               ▼
        ┌─────────────────────────────────────────────────────┐
        │              OUTPUT DISPLAY / PROJECTOR              │
        │                                                      │
        │   - Projected avatar face                            │
        │   - Robot display screen                             │
        │   - Could be on robot arm end-effector               │
        └─────────────────────────────────────────────────────┘
```

---

## Component Details

### 1. Emotion Detection Module (Fiona, Alec)
**Status: ✅ Implemented**

| Component | Technology | Purpose |
|-----------|------------|---------|
| Camera Input | OpenCV | Capture video frames |
| Face Detection | DeepFace (OpenCV backend) | Locate faces in frame |
| Emotion Analysis | DeepFace Emotion Model | Classify 7 emotions |

**Detected Emotions:**
- happy, sad, angry, fear, surprise, disgust, neutral

**Output Format:**
```python
{
    "dominant_emotion": "happy",
    "confidence": 87.3,
    "emotion": {
        "happy": 87.3,
        "neutral": 10.2,
        "sad": 1.5,
        ...
    },
    "face_region": {"x": 120, "y": 80, "w": 200, "h": 200}
}
```

---

### 2. Voice Command Module (Khyat)
**Status: 🔄 In Progress**

| Component | Technology Options | Purpose |
|-----------|-------------------|---------|
| Audio Input | PyAudio / sounddevice | Capture microphone |
| Speech-to-Text | Whisper / Google STT / Vosk | Convert speech to text |
| Command Parser | Rule-based / NLP | Extract chess moves/commands |

**Expected Commands:**
- Move commands: "e4", "knight to f3", "castle kingside"
- Game commands: "hint", "undo", "new game"
- System commands: "louder", "repeat"

---

### 3. Chess Engine Module (Khyat + Team)
**Status: 🔄 In Progress**

| Component | Technology | Purpose |
|-----------|------------|---------|
| Chess Logic | python-chess | Board state, legal moves |
| AI Opponent | Stockfish | Move generation, evaluation |
| Difficulty | Stockfish depth/ELO limit | Adjust AI strength |

**Difficulty Implementation:**
```python
# Stockfish difficulty via ELO limiting
stockfish.set_elo_rating(800)   # Beginner
stockfish.set_elo_rating(1500)  # Intermediate
stockfish.set_elo_rating(2500)  # Expert
```

---

### 4. Decision Engine
**Status: 📋 Planned**

Maps inputs to avatar responses:

| Player State | Game State | Avatar Response |
|-------------|------------|-----------------|
| Frustrated | Blundered | Encouraging + hint offer |
| Happy | Winning | Playful banter |
| Confused | Complex position | Thinking + suggestion |
| Neutral | Normal play | Engaged, watching |
| Angry | Losing badly | Calming + support |

---

### 5. Avatar Display Module (Fiona)
**Status: ✅ Implemented**

| Feature | Implementation |
|---------|---------------|
| Face rendering | pygame geometric shapes |
| Expressions | 9 moods (happy, sad, thinking, etc.) |
| Animations | Blinking, breathing, eye movement |
| Color themes | 4 themes (default, warm, winning, losing) |
| Messages | Timed text display |

---

### 6. Physical Robot Integration (Myrrh, Alec)
**Status: 📋 Planned**

| Component | Purpose |
|-----------|---------|
| Robot arm (3001) | Physical presence |
| Projector/Display | Show avatar face |
| Positioning | Face user during game |

---

## Data Flow Summary

```
Camera → DeepFace → Emotion
                          ↘
Microphone → STT → Parser → Command    →  Decision  →  Avatar  →  Display
                          ↗               Engine      Renderer
Chess Board → python-chess → State
```

---

## HRI Problem Addressed

**Problem:** Chess can be intimidating for beginners. Playing against a computer feels cold and discouraging, especially when losing.

**Solution:** An emotionally-aware chess companion that:
1. **Detects player frustration** before they quit
2. **Offers encouragement** at the right moments
3. **Provides hints** when the player seems stuck
4. **Celebrates successes** to reinforce learning
5. **Uses natural interaction** (voice, expressions) instead of buttons

**Key HRI Principles Applied:**
- Emotional intelligence in robots
- Natural multimodal interaction (voice + vision)
- Adaptive assistance based on user state
- Social presence through expressive avatar

---

## Files Implemented

```
deepface/examples/
├── emotion_avatar_demo.py      # ✅ Emotion → Avatar (working demo)
├── chess_companion_avatar.py   # ✅ Avatar renderer with expressions
├── chess_companion_integrated.py # ✅ Full integration prototype
├── robot_emotion_detector.py   # ✅ Emotion detection for robot
└── minimal_emotion_example.py  # ✅ Simple emotion example
```

---

## How to Run Current Demos

```bash
# 1. Simple emotion mirror (your face → avatar)
cd /path/to/deepface
python3 examples/emotion_avatar_demo.py

# 2. Avatar expression demo (keyboard controls)
python3 examples/chess_companion_avatar.py --demo

# 3. Interactive avatar testing
python3 examples/chess_companion_avatar.py
# Keys: 1-9 moods, WASD themes, SPACE message
```
