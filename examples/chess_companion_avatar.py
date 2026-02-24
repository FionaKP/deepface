"""
Chess Companion Avatar - Lightweight Expressive Face

A simple, projectable avatar that responds to:
- Player emotions (from DeepFace)
- Chess game state (moves, position evaluation)
- Voice commands

Uses pygame for smooth rendering. Designed for projection.

Usage:
    python chess_companion_avatar.py [--fullscreen] [--demo]
"""

import math
import time
import random
from dataclasses import dataclass
from enum import Enum
from typing import Optional, Tuple

try:
    import pygame
    PYGAME_AVAILABLE = True
except ImportError:
    PYGAME_AVAILABLE = False
    print("pygame not installed. Run: pip install pygame")


class AvatarMood(Enum):
    """Avatar expression states."""
    NEUTRAL = "neutral"
    HAPPY = "happy"
    THINKING = "thinking"
    ENCOURAGING = "encouraging"
    SURPRISED = "surprised"
    PLAYFUL = "playful"      # Friendly competitive banter
    CONCERNED = "concerned"   # Player struggling
    CELEBRATING = "celebrating"
    SAD = "sad"


@dataclass
class AvatarColors:
    """Color scheme for the avatar."""
    background: Tuple[int, int, int]
    face: Tuple[int, int, int]
    eyes: Tuple[int, int, int]
    mouth: Tuple[int, int, int]
    accent: Tuple[int, int, int]  # Glow/highlight color


# Predefined color themes
THEMES = {
    "default": AvatarColors(
        background=(20, 20, 30),
        face=(100, 180, 255),
        eyes=(255, 255, 255),
        mouth=(255, 255, 255),
        accent=(150, 220, 255),
    ),
    "warm": AvatarColors(
        background=(30, 20, 20),
        face=(255, 180, 100),
        eyes=(255, 255, 255),
        mouth=(255, 255, 255),
        accent=(255, 220, 150),
    ),
    "winning": AvatarColors(
        background=(20, 30, 20),
        face=(100, 255, 150),
        eyes=(255, 255, 255),
        mouth=(255, 255, 255),
        accent=(150, 255, 200),
    ),
    "losing": AvatarColors(
        background=(30, 20, 30),
        face=(200, 150, 255),
        eyes=(255, 255, 255),
        mouth=(255, 255, 255),
        accent=(220, 180, 255),
    ),
}


class ChessCompanionAvatar:
    """
    Lightweight animated avatar for chess companion system.

    Features:
    - Simple geometric face (easy to render, clear expressions)
    - Smooth animations (blinking, breathing, expressions)
    - Color themes based on game state
    - Message display for tips/banter
    """

    def __init__(
        self,
        width: int = 800,
        height: int = 600,
        fullscreen: bool = False,
    ):
        if not PYGAME_AVAILABLE:
            raise RuntimeError("pygame required. Install with: pip install pygame")

        pygame.init()
        pygame.display.set_caption("Chess Companion")

        flags = pygame.FULLSCREEN if fullscreen else 0
        self.screen = pygame.display.set_mode((width, height), flags)
        self.width = width
        self.height = height
        self.clock = pygame.time.Clock()

        # Avatar state
        self.mood = AvatarMood.NEUTRAL
        self.colors = THEMES["default"]
        self.message = ""
        self.message_timer = 0

        # Animation state
        self.blink_timer = 0
        self.blink_duration = 0.15
        self.next_blink = time.time() + random.uniform(2, 5)
        self.is_blinking = False

        # Eye tracking (subtle movement)
        self.eye_offset_x = 0
        self.eye_offset_y = 0
        self.target_eye_x = 0
        self.target_eye_y = 0

        # Breathing animation
        self.breath_phase = 0

        # Face dimensions (relative to screen)
        self.face_radius = min(width, height) * 0.35
        self.center_x = width // 2
        self.center_y = height // 2

    def set_mood(self, mood: AvatarMood) -> None:
        """Set the avatar's current mood/expression."""
        self.mood = mood

    def set_theme(self, theme_name: str) -> None:
        """Set color theme by name."""
        if theme_name in THEMES:
            self.colors = THEMES[theme_name]

    def set_colors(self, colors: AvatarColors) -> None:
        """Set custom colors."""
        self.colors = colors

    def show_message(self, message: str, duration: float = 3.0) -> None:
        """Display a message below the avatar."""
        self.message = message
        self.message_timer = time.time() + duration

    def _update_animations(self, dt: float) -> None:
        """Update all animation states."""
        current_time = time.time()

        # Blinking
        if not self.is_blinking and current_time >= self.next_blink:
            self.is_blinking = True
            self.blink_timer = current_time

        if self.is_blinking and current_time - self.blink_timer > self.blink_duration:
            self.is_blinking = False
            self.next_blink = current_time + random.uniform(2, 5)

        # Eye drift (subtle random movement)
        if random.random() < 0.02:
            self.target_eye_x = random.uniform(-10, 10)
            self.target_eye_y = random.uniform(-5, 5)

        self.eye_offset_x += (self.target_eye_x - self.eye_offset_x) * 0.1
        self.eye_offset_y += (self.target_eye_y - self.eye_offset_y) * 0.1

        # Breathing
        self.breath_phase += dt * 2
        if self.breath_phase > 2 * math.pi:
            self.breath_phase -= 2 * math.pi

        # Message timeout
        if self.message and current_time > self.message_timer:
            self.message = ""

    def _draw_face_base(self) -> None:
        """Draw the main face circle with glow effect."""
        breath_scale = 1 + math.sin(self.breath_phase) * 0.01

        # Outer glow
        for i in range(3):
            glow_radius = int(self.face_radius * breath_scale + 10 + i * 5)
            glow_alpha = 50 - i * 15
            glow_color = (*self.colors.accent, glow_alpha)
            glow_surface = pygame.Surface((glow_radius * 2, glow_radius * 2), pygame.SRCALPHA)
            pygame.draw.circle(glow_surface, glow_color, (glow_radius, glow_radius), glow_radius)
            self.screen.blit(
                glow_surface,
                (self.center_x - glow_radius, self.center_y - glow_radius)
            )

        # Main face
        radius = int(self.face_radius * breath_scale)
        pygame.draw.circle(
            self.screen,
            self.colors.face,
            (self.center_x, self.center_y),
            radius
        )

    def _draw_eyes(self) -> None:
        """Draw eyes based on current mood."""
        eye_y = self.center_y - self.face_radius * 0.15
        eye_spacing = self.face_radius * 0.35
        eye_radius = self.face_radius * 0.12
        pupil_radius = eye_radius * 0.5

        left_eye_x = self.center_x - eye_spacing
        right_eye_x = self.center_x + eye_spacing

        if self.is_blinking:
            # Closed eyes (horizontal lines)
            for eye_x in [left_eye_x, right_eye_x]:
                pygame.draw.line(
                    self.screen,
                    self.colors.eyes,
                    (eye_x - eye_radius, eye_y),
                    (eye_x + eye_radius, eye_y),
                    3
                )
            return

        # Eye shape based on mood
        if self.mood == AvatarMood.HAPPY or self.mood == AvatarMood.CELEBRATING:
            # Happy curved eyes (^_^)
            for eye_x in [left_eye_x, right_eye_x]:
                pygame.draw.arc(
                    self.screen,
                    self.colors.eyes,
                    (eye_x - eye_radius, eye_y - eye_radius // 2, eye_radius * 2, eye_radius),
                    0, math.pi,
                    4
                )

        elif self.mood == AvatarMood.SAD or self.mood == AvatarMood.CONCERNED:
            # Sad eyes (droopy)
            for i, eye_x in enumerate([left_eye_x, right_eye_x]):
                pygame.draw.ellipse(
                    self.screen,
                    self.colors.eyes,
                    (eye_x - eye_radius, eye_y - eye_radius * 0.7, eye_radius * 2, eye_radius * 1.4)
                )
                # Droopy eyebrow
                brow_dir = 1 if i == 0 else -1
                pygame.draw.line(
                    self.screen,
                    self.colors.face,
                    (eye_x - eye_radius * brow_dir, eye_y - eye_radius * 1.3),
                    (eye_x + eye_radius * brow_dir, eye_y - eye_radius * 0.9),
                    4
                )

        elif self.mood == AvatarMood.SURPRISED:
            # Big round eyes
            for eye_x in [left_eye_x, right_eye_x]:
                pygame.draw.circle(
                    self.screen,
                    self.colors.eyes,
                    (int(eye_x), int(eye_y)),
                    int(eye_radius * 1.3)
                )
                pygame.draw.circle(
                    self.screen,
                    self.colors.face,
                    (int(eye_x + self.eye_offset_x), int(eye_y + self.eye_offset_y)),
                    int(pupil_radius * 0.8)
                )

        elif self.mood == AvatarMood.THINKING:
            # Looking up/to the side
            for eye_x in [left_eye_x, right_eye_x]:
                pygame.draw.circle(
                    self.screen,
                    self.colors.eyes,
                    (int(eye_x), int(eye_y)),
                    int(eye_radius)
                )
                pygame.draw.circle(
                    self.screen,
                    self.colors.face,
                    (int(eye_x + 8), int(eye_y - 5)),
                    int(pupil_radius)
                )

        elif self.mood == AvatarMood.PLAYFUL:
            # Winking / mischievous
            # Left eye normal
            pygame.draw.circle(
                self.screen,
                self.colors.eyes,
                (int(left_eye_x), int(eye_y)),
                int(eye_radius)
            )
            pygame.draw.circle(
                self.screen,
                self.colors.face,
                (int(left_eye_x + self.eye_offset_x), int(eye_y + self.eye_offset_y)),
                int(pupil_radius)
            )
            # Right eye winking
            pygame.draw.arc(
                self.screen,
                self.colors.eyes,
                (right_eye_x - eye_radius, eye_y - eye_radius // 2, eye_radius * 2, eye_radius),
                0, math.pi,
                4
            )

        else:
            # Default/neutral eyes
            for eye_x in [left_eye_x, right_eye_x]:
                pygame.draw.circle(
                    self.screen,
                    self.colors.eyes,
                    (int(eye_x), int(eye_y)),
                    int(eye_radius)
                )
                # Pupil with offset
                pygame.draw.circle(
                    self.screen,
                    self.colors.face,
                    (int(eye_x + self.eye_offset_x), int(eye_y + self.eye_offset_y)),
                    int(pupil_radius)
                )

    def _draw_mouth(self) -> None:
        """Draw mouth based on current mood."""
        mouth_y = self.center_y + self.face_radius * 0.3
        mouth_width = self.face_radius * 0.4

        if self.mood == AvatarMood.HAPPY or self.mood == AvatarMood.CELEBRATING:
            # Big smile
            rect = pygame.Rect(
                self.center_x - mouth_width,
                mouth_y - mouth_width * 0.3,
                mouth_width * 2,
                mouth_width
            )
            pygame.draw.arc(self.screen, self.colors.mouth, rect, math.pi, 2 * math.pi, 4)

        elif self.mood == AvatarMood.SAD:
            # Frown
            rect = pygame.Rect(
                self.center_x - mouth_width,
                mouth_y,
                mouth_width * 2,
                mouth_width * 0.6
            )
            pygame.draw.arc(self.screen, self.colors.mouth, rect, 0, math.pi, 4)

        elif self.mood == AvatarMood.SURPRISED:
            # O mouth
            pygame.draw.circle(
                self.screen,
                self.colors.mouth,
                (self.center_x, int(mouth_y + 10)),
                int(mouth_width * 0.3),
                3
            )

        elif self.mood == AvatarMood.THINKING:
            # Small pursed mouth, offset
            pygame.draw.circle(
                self.screen,
                self.colors.mouth,
                (int(self.center_x + 15), int(mouth_y)),
                int(mouth_width * 0.15),
                3
            )

        elif self.mood == AvatarMood.PLAYFUL:
            # Smirk
            points = [
                (self.center_x - mouth_width * 0.5, mouth_y),
                (self.center_x + mouth_width * 0.3, mouth_y - 10),
                (self.center_x + mouth_width * 0.5, mouth_y - 20),
            ]
            pygame.draw.lines(self.screen, self.colors.mouth, False, points, 4)

        elif self.mood == AvatarMood.ENCOURAGING:
            # Gentle smile
            rect = pygame.Rect(
                self.center_x - mouth_width * 0.7,
                mouth_y - mouth_width * 0.2,
                mouth_width * 1.4,
                mouth_width * 0.5
            )
            pygame.draw.arc(self.screen, self.colors.mouth, rect, math.pi, 2 * math.pi, 3)

        elif self.mood == AvatarMood.CONCERNED:
            # Worried mouth (wavy)
            points = [
                (self.center_x - mouth_width * 0.5, mouth_y),
                (self.center_x - mouth_width * 0.2, mouth_y + 5),
                (self.center_x + mouth_width * 0.2, mouth_y - 5),
                (self.center_x + mouth_width * 0.5, mouth_y),
            ]
            pygame.draw.lines(self.screen, self.colors.mouth, False, points, 3)

        else:
            # Neutral - simple line
            pygame.draw.line(
                self.screen,
                self.colors.mouth,
                (self.center_x - mouth_width * 0.5, mouth_y),
                (self.center_x + mouth_width * 0.5, mouth_y),
                3
            )

    def _draw_message(self) -> None:
        """Draw the current message below the avatar."""
        if not self.message:
            return

        font = pygame.font.Font(None, 36)
        text_surface = font.render(self.message, True, self.colors.accent)
        text_rect = text_surface.get_rect(center=(self.center_x, self.height - 60))

        # Background for readability
        padding = 15
        bg_rect = text_rect.inflate(padding * 2, padding)
        pygame.draw.rect(self.screen, (0, 0, 0, 180), bg_rect, border_radius=10)
        pygame.draw.rect(self.screen, self.colors.accent, bg_rect, 2, border_radius=10)

        self.screen.blit(text_surface, text_rect)

    def _draw_mood_indicator(self) -> None:
        """Draw small mood indicator in corner (for debugging)."""
        font = pygame.font.Font(None, 24)
        text = f"Mood: {self.mood.value}"
        text_surface = font.render(text, True, (100, 100, 100))
        self.screen.blit(text_surface, (10, 10))

    def render(self, flip: bool = True) -> None:
        """Render a single frame.

        Args:
            flip: Whether to flip the display. Set to False if you want to
                  draw additional elements before flipping.
        """
        dt = self.clock.tick(60) / 1000.0  # Delta time in seconds
        self._update_animations(dt)

        # Clear screen
        self.screen.fill(self.colors.background)

        # Draw avatar components
        self._draw_face_base()
        self._draw_eyes()
        self._draw_mouth()
        self._draw_message()
        self._draw_mood_indicator()

        if flip:
            pygame.display.flip()

    def handle_events(self) -> bool:
        """Handle pygame events. Returns False if should quit."""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE or event.key == pygame.K_q:
                    return False
        return True

    def quit(self) -> None:
        """Clean up pygame."""
        pygame.quit()


# =============================================================================
# Chess Companion Logic
# =============================================================================

class ChessCompanion:
    """
    Combines avatar with game logic to create responses.

    This is the "brain" that decides what mood/message to show
    based on player emotion + chess state.
    """

    # Message templates
    MESSAGES = {
        "good_move": [
            "Nice move!",
            "Well played!",
            "I see what you did there!",
            "Clever!",
        ],
        "blunder": [
            "Hmm, are you sure about that?",
            "That's a bold choice...",
            "Interesting strategy!",
        ],
        "player_frustrated": [
            "Take your time, no rush!",
            "Chess is hard, you've got this!",
            "Want a hint?",
        ],
        "player_happy": [
            "You're in the zone!",
            "Confidence looks good on you!",
        ],
        "winning": [
            "Looking good!",
            "You're crushing it!",
        ],
        "losing": [
            "It's not over yet!",
            "Time for a comeback!",
        ],
        "playful_taunt": [
            "Is that your final answer?",
            "Oh, you think you're clever?",
            "Challenge accepted!",
        ],
    }

    def __init__(self, avatar: ChessCompanionAvatar):
        self.avatar = avatar
        self.last_response_time = 0
        self.response_cooldown = 3.0  # Minimum seconds between responses

    def respond(
        self,
        player_emotion: Optional[str] = None,
        move_quality: Optional[str] = None,  # "good", "blunder", "normal"
        game_state: Optional[str] = None,    # "winning", "losing", "even"
    ) -> None:
        """
        Generate avatar response based on inputs.

        Args:
            player_emotion: Detected emotion from DeepFace
            move_quality: Quality of the last chess move
            game_state: Current game evaluation
        """
        current_time = time.time()
        if current_time - self.last_response_time < self.response_cooldown:
            return

        mood = AvatarMood.NEUTRAL
        message = ""
        theme = "default"

        # Priority 1: React to player emotion if strong
        if player_emotion in ("sad", "angry", "fear"):
            mood = AvatarMood.ENCOURAGING
            message = random.choice(self.MESSAGES["player_frustrated"])
            theme = "warm"

        elif player_emotion == "happy":
            mood = AvatarMood.HAPPY
            message = random.choice(self.MESSAGES["player_happy"])

        # Priority 2: React to move quality
        elif move_quality == "blunder":
            mood = AvatarMood.CONCERNED
            message = random.choice(self.MESSAGES["blunder"])

        elif move_quality == "good":
            mood = AvatarMood.HAPPY
            message = random.choice(self.MESSAGES["good_move"])

        # Priority 3: React to game state
        elif game_state == "winning":
            mood = AvatarMood.PLAYFUL
            message = random.choice(self.MESSAGES["winning"])
            theme = "winning"

        elif game_state == "losing":
            mood = AvatarMood.ENCOURAGING
            message = random.choice(self.MESSAGES["losing"])
            theme = "losing"

        # Apply response
        self.avatar.set_mood(mood)
        self.avatar.set_theme(theme)
        if message:
            self.avatar.show_message(message)
            self.last_response_time = current_time


# =============================================================================
# Demo Mode
# =============================================================================

def run_demo():
    """Run a demo cycling through all moods and features."""
    avatar = ChessCompanionAvatar(width=800, height=600)
    companion = ChessCompanion(avatar)

    demo_sequence = [
        (AvatarMood.NEUTRAL, "default", "Hello! I'm your chess companion."),
        (AvatarMood.HAPPY, "default", "Let's play some chess!"),
        (AvatarMood.THINKING, "default", "Hmm, analyzing the position..."),
        (AvatarMood.SURPRISED, "default", "Wow, unexpected move!"),
        (AvatarMood.PLAYFUL, "default", "Think you can beat me?"),
        (AvatarMood.ENCOURAGING, "warm", "You've got this!"),
        (AvatarMood.CONCERNED, "losing", "That was a tricky spot..."),
        (AvatarMood.CELEBRATING, "winning", "Checkmate! Great game!"),
        (AvatarMood.SAD, "default", "Good game, you won!"),
    ]

    current_idx = 0
    last_change = time.time()
    change_interval = 2.5

    print("\nDemo mode - cycling through expressions")
    print("Press Q or ESC to quit\n")

    running = True
    while running:
        running = avatar.handle_events()

        # Cycle through demo sequence
        if time.time() - last_change > change_interval:
            mood, theme, message = demo_sequence[current_idx]
            avatar.set_mood(mood)
            avatar.set_theme(theme)
            avatar.show_message(message, duration=change_interval - 0.5)

            current_idx = (current_idx + 1) % len(demo_sequence)
            last_change = time.time()

        avatar.render()

    avatar.quit()


def run_interactive():
    """Run interactive mode with keyboard controls."""
    avatar = ChessCompanionAvatar(width=800, height=600)

    print("\nInteractive mode - keyboard controls:")
    print("  1-9: Change mood")
    print("  W/A/S/D: Change theme")
    print("  SPACE: Show random message")
    print("  Q/ESC: Quit\n")

    mood_keys = {
        pygame.K_1: AvatarMood.NEUTRAL,
        pygame.K_2: AvatarMood.HAPPY,
        pygame.K_3: AvatarMood.SAD,
        pygame.K_4: AvatarMood.THINKING,
        pygame.K_5: AvatarMood.SURPRISED,
        pygame.K_6: AvatarMood.PLAYFUL,
        pygame.K_7: AvatarMood.ENCOURAGING,
        pygame.K_8: AvatarMood.CONCERNED,
        pygame.K_9: AvatarMood.CELEBRATING,
    }

    theme_keys = {
        pygame.K_w: "default",
        pygame.K_a: "warm",
        pygame.K_s: "winning",
        pygame.K_d: "losing",
    }

    messages = [
        "Nice move!", "Interesting...", "You've got this!",
        "Checkmate incoming?", "Bold strategy!", "Well played!",
    ]

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_ESCAPE, pygame.K_q):
                    running = False
                elif event.key in mood_keys:
                    avatar.set_mood(mood_keys[event.key])
                elif event.key in theme_keys:
                    avatar.set_theme(theme_keys[event.key])
                elif event.key == pygame.K_SPACE:
                    avatar.show_message(random.choice(messages))

        avatar.render()

    avatar.quit()


# =============================================================================
# Main
# =============================================================================

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Chess Companion Avatar")
    parser.add_argument("--demo", action="store_true", help="Run demo mode")
    parser.add_argument("--fullscreen", "-f", action="store_true", help="Fullscreen mode")
    args = parser.parse_args()

    if not PYGAME_AVAILABLE:
        print("Please install pygame: pip install pygame")
        exit(1)

    if args.demo:
        run_demo()
    else:
        run_interactive()
