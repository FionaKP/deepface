"""
Chess Board Projection Mapping

Projects highlights, moves, and effects onto a physical chess board.

Setup:
1. Place projector above the chess board, pointing down
2. Run this script and drag window to projector
3. Press F for fullscreen
4. Use calibration mode to align corners with your physical board
5. Then project moves and highlights!

Usage:
    python chess_board_projector.py

Controls:
    CALIBRATION MODE (starts here):
        Click: Select corner to move
        Arrow keys: Move selected corner
        1-4: Select corner directly
        ENTER: Finish calibration
        R: Reset calibration

    PLAY MODE:
        Click on squares to highlight them
        A: Show attack arrows (demo)
        M: Show last move highlight
        H: Show hint arrows
        P: Toggle possible moves display
        C: Clear all highlights
        ESC: Back to calibration
        Q: Quit
"""

import sys
import math
import json
import numpy as np
from pathlib import Path
from typing import List, Tuple, Optional, Dict
from dataclasses import dataclass
from enum import Enum

try:
    import pygame
except ImportError:
    print("Install pygame: pip install pygame")
    sys.exit(1)


# Chess board squares
FILES = "abcdefgh"
RANKS = "12345678"


class Mode(Enum):
    CALIBRATE = "calibrate"
    PLAY = "play"


@dataclass
class Square:
    """A chess square with notation and pixel coordinates."""
    file: str  # a-h
    rank: str  # 1-8
    x: int     # pixel x (center)
    y: int     # pixel y (center)
    size: int  # square size in pixels


class ChessBoardProjector:
    """
    Projects graphics onto a physical chess board.
    Uses 4-corner calibration to map projector pixels to board squares.
    """

    # Colors (high contrast for projection)
    COLORS = {
        "background": (0, 0, 0),          # Black = no projection
        "calibration": (255, 255, 0),     # Yellow calibration points
        "grid": (50, 50, 50),             # Faint grid lines
        "highlight_move": (80, 200, 80, 150),    # Green - last move
        "highlight_select": (80, 80, 255, 150),  # Blue - selected
        "highlight_possible": (255, 255, 80, 100),  # Yellow - possible moves
        "highlight_danger": (255, 80, 80, 150),  # Red - danger/attack
        "highlight_hint": (80, 255, 200, 150),   # Cyan - hint
        "arrow": (255, 150, 50),           # Orange arrows
        "text": (255, 255, 255),
    }

    def __init__(self, width: int = 1280, height: int = 720):
        pygame.init()
        pygame.display.set_caption("Chess Board Projector - Drag to projector, press F")

        self.width = width
        self.height = height
        self.screen = pygame.display.set_mode((width, height), pygame.RESIZABLE)
        self.clock = pygame.time.Clock()
        self.is_fullscreen = False

        # Mode
        self.mode = Mode.CALIBRATE

        # Calibration: 4 corners of the chess board
        # Order: top-left (a8), top-right (h8), bottom-right (h1), bottom-left (a1)
        # Initialize with default positions
        margin = 100
        self.corners = [
            [margin, margin],                           # a8 (top-left)
            [width - margin, margin],                   # h8 (top-right)
            [width - margin, height - margin],         # h1 (bottom-right)
            [margin, height - margin],                 # a1 (bottom-left)
        ]
        self.selected_corner = 0  # Currently selected corner for adjustment

        # Computed squares (after calibration)
        self.squares: Dict[str, Square] = {}
        self._compute_squares()

        # Highlight state
        self.highlighted_squares: Dict[str, str] = {}  # square -> highlight type
        self.arrows: List[Tuple[str, str, str]] = []   # (from, to, color_type)

        # Load saved calibration if exists
        self._load_calibration()

    def _compute_squares(self):
        """Compute pixel positions for all 64 squares based on corner calibration."""
        self.squares.clear()

        # Get corners as numpy arrays
        tl = np.array(self.corners[0])  # a8
        tr = np.array(self.corners[1])  # h8
        br = np.array(self.corners[2])  # h1
        bl = np.array(self.corners[3])  # a1

        # For each square, interpolate position
        for file_idx, file in enumerate(FILES):
            for rank_idx, rank in enumerate(RANKS):
                # rank 8 is at top (rank_idx=7), rank 1 at bottom (rank_idx=0)
                # file a is at left (file_idx=0), file h at right (file_idx=7)

                # Normalized coordinates (0-1)
                u = (file_idx + 0.5) / 8  # horizontal
                v = 1 - (rank_idx + 0.5) / 8  # vertical (flip because rank 8 is top)

                # Bilinear interpolation
                top = tl + (tr - tl) * u
                bottom = bl + (br - bl) * u
                pos = top + (bottom - top) * v

                # Estimate square size
                square_width = np.linalg.norm(tr - tl) / 8
                square_height = np.linalg.norm(bl - tl) / 8
                size = int((square_width + square_height) / 2)

                self.squares[f"{file}{rank}"] = Square(
                    file=file,
                    rank=rank,
                    x=int(pos[0]),
                    y=int(pos[1]),
                    size=size
                )

    def _save_calibration(self):
        """Save calibration to file."""
        path = Path(__file__).parent / "calibration.json"
        with open(path, "w") as f:
            json.dump({"corners": self.corners}, f)
        print(f"Calibration saved to {path}")

    def _load_calibration(self):
        """Load calibration from file if exists."""
        path = Path(__file__).parent / "calibration.json"
        if path.exists():
            try:
                with open(path) as f:
                    data = json.load(f)
                    self.corners = data["corners"]
                    self._compute_squares()
                    print("Loaded saved calibration")
            except:
                print("Could not load calibration, using defaults")

    def _draw_calibration(self):
        """Draw calibration interface."""
        self.screen.fill(self.COLORS["background"])

        # Draw corner points and labels
        labels = ["a8 (top-left)", "h8 (top-right)", "h1 (bottom-right)", "a1 (bottom-left)"]

        for i, (corner, label) in enumerate(zip(self.corners, labels)):
            x, y = int(corner[0]), int(corner[1])

            # Draw point
            color = (255, 100, 100) if i == self.selected_corner else self.COLORS["calibration"]
            pygame.draw.circle(self.screen, color, (x, y), 15)
            pygame.draw.circle(self.screen, (255, 255, 255), (x, y), 15, 2)

            # Draw label
            font = pygame.font.Font(None, 28)
            text = font.render(f"{i+1}: {label}", True, color)
            self.screen.blit(text, (x + 20, y - 10))

        # Draw board outline
        points = [(int(c[0]), int(c[1])) for c in self.corners]
        pygame.draw.lines(self.screen, self.COLORS["calibration"], True, points, 2)

        # Draw grid preview
        self._draw_grid_preview()

        # Instructions
        self._draw_instructions_calibration()

        pygame.display.flip()

    def _draw_grid_preview(self):
        """Draw a preview of the chess grid based on current calibration."""
        tl = np.array(self.corners[0])
        tr = np.array(self.corners[1])
        br = np.array(self.corners[2])
        bl = np.array(self.corners[3])

        # Draw horizontal lines
        for i in range(9):
            t = i / 8
            left = tl + (bl - tl) * t
            right = tr + (br - tr) * t
            pygame.draw.line(
                self.screen, self.COLORS["grid"],
                (int(left[0]), int(left[1])),
                (int(right[0]), int(right[1])), 1
            )

        # Draw vertical lines
        for i in range(9):
            t = i / 8
            top = tl + (tr - tl) * t
            bottom = bl + (br - bl) * t
            pygame.draw.line(
                self.screen, self.COLORS["grid"],
                (int(top[0]), int(top[1])),
                (int(bottom[0]), int(bottom[1])), 1
            )

    def _draw_instructions_calibration(self):
        """Draw calibration mode instructions."""
        font = pygame.font.Font(None, 28)
        lines = [
            "=== CALIBRATION MODE ===",
            "",
            f"Selected corner: {self.selected_corner + 1} (use 1-4 or click to select)",
            "Arrow keys: Move selected corner",
            "ENTER: Finish calibration & save",
            "R: Reset to defaults",
            "",
            "Align the yellow corners with your physical chess board!"
        ]

        y = 20
        for line in lines:
            color = (255, 200, 0) if "===" in line else self.COLORS["text"]
            text = font.render(line, True, color)
            self.screen.blit(text, (20, y))
            y += 28

    def _draw_play_mode(self):
        """Draw play mode with highlights and arrows."""
        self.screen.fill(self.COLORS["background"])

        # Draw square highlights
        for square_name, highlight_type in self.highlighted_squares.items():
            self._draw_square_highlight(square_name, highlight_type)

        # Draw arrows
        for from_sq, to_sq, arrow_type in self.arrows:
            self._draw_arrow(from_sq, to_sq, arrow_type)

        # Draw faint grid for reference
        self._draw_grid_preview()

        # Instructions
        self._draw_instructions_play()

        pygame.display.flip()

    def _draw_square_highlight(self, square_name: str, highlight_type: str):
        """Draw a highlight on a square."""
        if square_name not in self.squares:
            return

        sq = self.squares[square_name]

        # Get color based on type
        color_map = {
            "move": self.COLORS["highlight_move"],
            "select": self.COLORS["highlight_select"],
            "possible": self.COLORS["highlight_possible"],
            "danger": self.COLORS["highlight_danger"],
            "hint": self.COLORS["highlight_hint"],
        }
        color = color_map.get(highlight_type, self.COLORS["highlight_select"])

        # Draw filled rectangle with transparency
        half = sq.size // 2
        surf = pygame.Surface((sq.size, sq.size), pygame.SRCALPHA)
        surf.fill(color)
        self.screen.blit(surf, (sq.x - half, sq.y - half))

        # Draw border
        border_color = tuple(min(255, c + 50) for c in color[:3])
        pygame.draw.rect(
            self.screen, border_color,
            (sq.x - half, sq.y - half, sq.size, sq.size), 3
        )

    def _draw_arrow(self, from_sq: str, to_sq: str, arrow_type: str = "default"):
        """Draw an arrow between two squares."""
        if from_sq not in self.squares or to_sq not in self.squares:
            return

        sq1 = self.squares[from_sq]
        sq2 = self.squares[to_sq]

        color = self.COLORS["arrow"]
        if arrow_type == "hint":
            color = self.COLORS["highlight_hint"][:3]
        elif arrow_type == "danger":
            color = self.COLORS["highlight_danger"][:3]

        # Draw line
        pygame.draw.line(self.screen, color, (sq1.x, sq1.y), (sq2.x, sq2.y), 4)

        # Draw arrowhead
        angle = math.atan2(sq2.y - sq1.y, sq2.x - sq1.x)
        arrow_size = 15

        p1 = (sq2.x - arrow_size * math.cos(angle - 0.4),
              sq2.y - arrow_size * math.sin(angle - 0.4))
        p2 = (sq2.x - arrow_size * math.cos(angle + 0.4),
              sq2.y - arrow_size * math.sin(angle + 0.4))

        pygame.draw.polygon(self.screen, color, [(sq2.x, sq2.y), p1, p2])

    def _draw_instructions_play(self):
        """Draw play mode instructions."""
        font = pygame.font.Font(None, 24)
        lines = [
            "PLAY MODE | Click squares to highlight | A:arrows M:move H:hint C:clear ESC:calibrate Q:quit"
        ]

        text = font.render(lines[0], True, (100, 100, 100))
        self.screen.blit(text, (10, 10))

    def _get_square_at_pos(self, x: int, y: int) -> Optional[str]:
        """Get the chess square at a pixel position."""
        for name, sq in self.squares.items():
            half = sq.size // 2
            if (sq.x - half <= x <= sq.x + half and
                sq.y - half <= y <= sq.y + half):
                return name
        return None

    def highlight_square(self, square: str, highlight_type: str = "select"):
        """Add or update a square highlight."""
        if square in self.squares:
            self.highlighted_squares[square] = highlight_type

    def clear_highlight(self, square: str):
        """Remove a square highlight."""
        if square in self.highlighted_squares:
            del self.highlighted_squares[square]

    def clear_all(self):
        """Clear all highlights and arrows."""
        self.highlighted_squares.clear()
        self.arrows.clear()

    def add_arrow(self, from_sq: str, to_sq: str, arrow_type: str = "default"):
        """Add an arrow between squares."""
        self.arrows.append((from_sq, to_sq, arrow_type))

    def show_move(self, from_sq: str, to_sq: str):
        """Highlight a move (from and to squares)."""
        self.highlight_square(from_sq, "move")
        self.highlight_square(to_sq, "move")

    def show_possible_moves(self, square: str, moves: List[str]):
        """Highlight possible moves for a piece."""
        self.highlight_square(square, "select")
        for move in moves:
            self.highlight_square(move, "possible")

    def handle_events(self) -> bool:
        """Handle input events. Returns False to quit."""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False

            elif event.type == pygame.VIDEORESIZE:
                if not self.is_fullscreen:
                    self.width, self.height = event.w, event.h
                    self.screen = pygame.display.set_mode(
                        (self.width, self.height), pygame.RESIZABLE
                    )

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
                        self.screen = pygame.display.set_mode(
                            (self.width, self.height), pygame.RESIZABLE
                        )

                elif self.mode == Mode.CALIBRATE:
                    self._handle_calibration_key(event.key)

                elif self.mode == Mode.PLAY:
                    self._handle_play_key(event.key)

            elif event.type == pygame.MOUSEBUTTONDOWN:
                if self.mode == Mode.CALIBRATE:
                    self._handle_calibration_click(event.pos)
                elif self.mode == Mode.PLAY:
                    self._handle_play_click(event.pos)

        return True

    def _handle_calibration_key(self, key):
        """Handle keyboard input in calibration mode."""
        move_amount = 5

        if key == pygame.K_LEFT:
            self.corners[self.selected_corner][0] -= move_amount
        elif key == pygame.K_RIGHT:
            self.corners[self.selected_corner][0] += move_amount
        elif key == pygame.K_UP:
            self.corners[self.selected_corner][1] -= move_amount
        elif key == pygame.K_DOWN:
            self.corners[self.selected_corner][1] += move_amount

        elif key == pygame.K_1:
            self.selected_corner = 0
        elif key == pygame.K_2:
            self.selected_corner = 1
        elif key == pygame.K_3:
            self.selected_corner = 2
        elif key == pygame.K_4:
            self.selected_corner = 3

        elif key == pygame.K_RETURN:
            self._compute_squares()
            self._save_calibration()
            self.mode = Mode.PLAY
            print("Calibration complete! Entering play mode.")

        elif key == pygame.K_r:
            # Reset calibration
            margin = 100
            self.corners = [
                [margin, margin],
                [self.width - margin, margin],
                [self.width - margin, self.height - margin],
                [margin, self.height - margin],
            ]
            self._compute_squares()

        # Recompute after any change
        self._compute_squares()

    def _handle_calibration_click(self, pos):
        """Handle mouse click in calibration mode - select nearest corner."""
        min_dist = float('inf')
        for i, corner in enumerate(self.corners):
            dist = math.sqrt((pos[0] - corner[0])**2 + (pos[1] - corner[1])**2)
            if dist < min_dist:
                min_dist = dist
                self.selected_corner = i

    def _handle_play_key(self, key):
        """Handle keyboard input in play mode."""
        if key == pygame.K_ESCAPE:
            self.mode = Mode.CALIBRATE

        elif key == pygame.K_c:
            self.clear_all()

        elif key == pygame.K_m:
            # Demo: show a last move
            self.clear_all()
            self.show_move("e2", "e4")

        elif key == pygame.K_a:
            # Demo: show attack arrows
            self.clear_all()
            self.add_arrow("d4", "e5", "danger")
            self.add_arrow("f3", "e5", "danger")
            self.highlight_square("e5", "danger")

        elif key == pygame.K_h:
            # Demo: show hint
            self.clear_all()
            self.add_arrow("g1", "f3", "hint")
            self.highlight_square("f3", "hint")

        elif key == pygame.K_p:
            # Demo: show possible moves for a knight on g1
            self.clear_all()
            self.show_possible_moves("g1", ["f3", "h3"])

    def _handle_play_click(self, pos):
        """Handle mouse click in play mode - toggle square highlight."""
        square = self._get_square_at_pos(pos[0], pos[1])
        if square:
            if square in self.highlighted_squares:
                self.clear_highlight(square)
            else:
                self.highlight_square(square, "select")

    def render(self):
        """Render current frame."""
        self.clock.tick(60)

        if self.mode == Mode.CALIBRATE:
            self._draw_calibration()
        else:
            self._draw_play_mode()

    def quit(self):
        pygame.quit()


def main():
    print("\n=== Chess Board Projector ===")
    print("1. Drag window to your projector")
    print("2. Press F for fullscreen")
    print("3. Align corners with your physical board")
    print("4. Press ENTER to save and start projecting!\n")

    projector = ChessBoardProjector(1280, 720)

    while projector.handle_events():
        projector.render()

    projector.quit()


if __name__ == "__main__":
    main()
