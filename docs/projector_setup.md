# Projector Setup Guide

## Quick Start

### 1. Connect Projector
Connect your projector to your Mac via HDMI/USB-C. macOS should detect it as a second display.

### 2. Check Displays
```bash
cd ~/coding_projects/deepface
python3 examples/avatar_projector.py --list-displays
```

Output example:
```
Found 2 display(s):

  Display 0: 2560x1600
             (primary - probably your laptop)
  Display 1: 1920x1080
             (secondary - probably projector)
```

### 3. Run on Projector
```bash
# Run on secondary display (projector) in fullscreen
python3 examples/avatar_projector.py --display 1 --fullscreen
```

---

## Controls

| Key | Action |
|-----|--------|
| **Arrow keys** | Move avatar position (for alignment) |
| **+/-** | Scale avatar bigger/smaller |
| **F** | Toggle fullscreen |
| **T** | Cycle color themes |
| **C** | Toggle camera preview |
| **1-9** | Change expression manually |
| **Q/ESC** | Quit |

---

## Projector Alignment Tips

1. **Position the avatar** using arrow keys so it appears centered on your projection surface
2. **Scale** with +/- to fit your projection area
3. The avatar responds to your facial expressions via the webcam

---

## macOS Display Settings

If the projector isn't detected:

1. Go to **System Settings → Displays**
2. Click **Arrange** to see both displays
3. You can set the projector as "Mirror" or "Extend"
   - **Extend** (recommended): Avatar on projector, controls on laptop
   - **Mirror**: Same content on both

---

## Physical Setup for Chess

```
        PROJECTOR (ceiling/stand mount)
              │
              │ projects down
              ▼
    ┌─────────────────────┐
    │                     │
    │    AVATAR FACE      │  ← projected onto table/surface
    │       😊            │     across from player
    │                     │
    ├─────────────────────┤
    │                     │
    │    CHESS BOARD      │  ← physical board (or also projected)
    │    ♜ ♞ ♝ ♛ ♚ ♝ ♞ ♜  │
    │                     │
    └─────────────────────┘
              │
           PLAYER sits here
              │
           CAMERA (facing player)
```

---

## Projection Surfaces

| Surface | Notes |
|---------|-------|
| White table/paper | Best contrast |
| Wall | Good for large avatar |
| Translucent screen | Can project from behind |
| 3D printed face form | Advanced: gives avatar depth |

---

## Color Themes for Projection

The projector version uses high-contrast colors optimized for projection:

| Theme | Face Color | When to Use |
|-------|-----------|-------------|
| default | Bright blue | Normal state |
| warm | Orange | Encouraging moments |
| winning | Green | Player doing well |
| losing | Red/pink | Player struggling |
| thinking | Purple | Avatar analyzing |

Cycle themes with **T** key.

---

## Troubleshooting

**Avatar on wrong display:**
```bash
# Try different display numbers
python3 examples/avatar_projector.py --display 0
python3 examples/avatar_projector.py --display 1
```

**Projector not detected:**
- Check cable connection
- Try unplugging and reconnecting
- Restart the script after connecting

**Avatar too small/large:**
- Use +/- keys to scale
- Or adjust projector zoom/position

**Black screen:**
- Make sure projector is on the correct input
- Try windowed mode first: `python3 examples/avatar_projector.py --display 1` (no --fullscreen)
