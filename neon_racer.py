import json
import math
import random
import sys
from pathlib import Path

import pygame

pygame.init()

# -------------------- Setup --------------------
WIDTH, HEIGHT = 1000, 700
FPS = 60
TITLE = "Neon Racer"

screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption(TITLE)
clock = pygame.time.Clock()

# -------------------- Colors --------------------
BG = (8, 12, 28)
PANEL = (16, 23, 48)
PANEL_LIGHT = (25, 35, 70)
ROAD = (35, 40, 58)
ROAD_EDGE = (80, 90, 125)
WHITE = (240, 245, 255)
MUTED = (145, 157, 190)
CYAN = (40, 230, 255)
BLUE = (70, 110, 255)
PINK = (255, 65, 165)
RED = (255, 75, 90)
GREEN = (50, 235, 150)
YELLOW = (255, 220, 70)
BLACK = (5, 7, 15)

ROAD_LEFT = 180
ROAD_RIGHT = 820
ROAD_WIDTH = ROAD_RIGHT - ROAD_LEFT
LANES = 4
LANE_WIDTH = ROAD_WIDTH // LANES
CAR_W, CAR_H = 62, 96

SAVE_FILE = Path("neon_racer_data.json")

# -------------------- Fonts --------------------
FONT_CACHE = {}


def font(size, bold=False):
    key = (size, bold)
    if key not in FONT_CACHE:
        FONT_CACHE[key] = pygame.font.SysFont("segoeui", size, bold=bold)
    return FONT_CACHE[key]


def text(surface, message, size, color, position, center=False, bold=False):
    image = font(size, bold).render(str(message), True, color)
    rect = image.get_rect()
    if center:
        rect.center = position
    else:
        rect.topleft = position
    surface.blit(image, rect)
    return rect


def draw_glow(surface, position, radius, color, alpha=45):
    glow = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
    for r in range(radius, 0, -8):
        current_alpha = max(1, int(alpha * (1 - r / radius)))
        pygame.draw.circle(
            glow,
            (*color, current_alpha),
            (radius, radius),
            r,
        )
    surface.blit(glow, (position[0] - radius, position[1] - radius))


def rounded_panel(surface, rect, color=PANEL, border_color=None, radius=18):
    pygame.draw.rect(surface, color, rect, border_radius=radius)
    if border_color:
        pygame.draw.rect(surface, border_color, rect, 2, border_radius=radius)


# -------------------- Data --------------------
def load_high_score():
    try:
        return int(json.loads(SAVE_FILE.read_text()).get("high_score", 0))
    except (FileNotFoundError, ValueError, json.JSONDecodeError):
        return 0


def save_high_score(value):
    try:
        SAVE_FILE.write_text(json.dumps({"high_score": value}))
    except OSError:
        pass


# -------------------- UI Button --------------------
class Button:
    def __init__(self, label, rect, color, hover_color, action):
        self.label = label
        self.rect = pygame.Rect(rect)
        self.color = color
        self.hover_color = hover_color
        self.action = action

    def draw(self, surface):
        mouse_pos = pygame.mouse.get_pos()
        hovered = self.rect.collidepoint(mouse_pos)
        current = self.hover_color if hovered else self.color

        if hovered:
            draw_glow(surface, self.rect.center, 80, current, 35)

        pygame.draw.rect(surface, current, self.rect, border_radius=12)
        pygame.draw.rect(surface, WHITE, self.rect, 2, border_radius=12)
        text(
            surface,
            self.label,
            20,
            WHITE,
            self.rect.center,
            center=True,
            bold=True,
        )

    def clicked(self, event):
        return (
            event.type == pygame.MOUSEBUTTONDOWN
            and event.button == 1
            and self.rect.collidepoint(event.pos)
        )


# -------------------- Cars --------------------
def draw_car(surface, rect, body_color, player=False):
    x, y, w, h = rect

    shadow = pygame.Rect(x + 5, y + 7, w, h)
    pygame.draw.rect(surface, BLACK, shadow, border_radius=15)

    pygame.draw.rect(surface, body_color, rect, border_radius=14)
    pygame.draw.rect(surface, WHITE, rect, 2, border_radius=14)

    window = pygame.Rect(x + 12, y + 15, w - 24, 25)
    pygame.draw.rect(surface, (25, 35, 65), window, border_radius=7)
    pygame.draw.line(
        surface,
        CYAN if player else PINK,
        (x + 16, y + 28),
        (x + w - 16, y + 28),
        2,
    )

    pygame.draw.rect(surface, WHITE, (x + 10, y + 6, 11, 7), border_radius=3)
    pygame.draw.rect(surface, WHITE, (x + w - 21, y + 6, 11, 7), border_radius=3)

    wheel_color = (12, 14, 25)
    for wheel_y in (y + 18, y + h - 30):
        pygame.draw.rect(surface, wheel_color, (x - 6, wheel_y, 9, 22), border_radius=4)
        pygame.draw.rect(surface, wheel_color, (x + w - 3, wheel_y, 9, 22), border_radius=4)

    if player:
        pygame.draw.rect(surface, CYAN, (x + 14, y + h - 12, w - 28, 5), border_radius=2)
    else:
        pygame.draw.rect(surface, RED, (x + 14, y + h - 12, w - 28, 5), border_radius=2)


# -------------------- Background --------------------
def draw_background(surface, time_value):
    surface.fill(BG)

    for i in range(12):
        x = (i * 97 + int(time_value * 15)) % WIDTH
        y = (i * 61 + int(time_value * 8)) % HEIGHT
        pygame.draw.circle(surface, (20, 30, 60), (x, y), 2)

    pygame.draw.rect(surface, ROAD, (ROAD_LEFT, 0, ROAD_WIDTH, HEIGHT))
    pygame.draw.line(surface, ROAD_EDGE, (ROAD_LEFT, 0), (ROAD_LEFT, HEIGHT), 5)
    pygame.draw.line(surface, ROAD_EDGE, (ROAD_RIGHT, 0), (ROAD_RIGHT, HEIGHT), 5)

    pygame.draw.line(
        surface,
        CYAN,
        (ROAD_LEFT + 7, 0),
        (ROAD_LEFT + 7, HEIGHT),
        2,
    )
    pygame.draw.line(
        surface,
        PINK,
        (ROAD_RIGHT - 7, 0),
        (ROAD_RIGHT - 7, HEIGHT),
        2,
    )


def draw_lane_markers(surface, offset):
    marker_h = 65
    gap = 45
    period = marker_h + gap

    for lane in range(1, LANES):
        x = ROAD_LEFT + lane * LANE_WIDTH
        y = -period + int(offset) % period

        while y < HEIGHT:
            pygame.draw.rect(
                surface,
                YELLOW,
                (x - 3, y, 6, marker_h),
                border_radius=3,
            )
            y += period


# -------------------- Screens --------------------
def draw_title(surface):
    draw_glow(surface, (WIDTH // 2, 150), 180, CYAN, 40)
    draw_glow(surface, (WIDTH // 2, 150), 130, PINK, 25)

    text(surface, "NEON", 76, CYAN, (WIDTH // 2, 115), center=True, bold=True)
    text(surface, "RACER", 76, PINK, (WIDTH // 2, 185), center=True, bold=True)
    text(
        surface,
        "DODGE • SURVIVE • DOMINATE",
        18,
        MUTED,
        (WIDTH // 2, 235),
        center=True,
        bold=True,
    )


def draw_hud(surface, score, dodged, level, high_score):
    rounded_panel(surface, (25, 22, 300, 92), PANEL, (45, 60, 105))

    text(surface, "SCORE", 13, MUTED, (45, 37), bold=True)
    text(surface, score, 27, YELLOW, (45, 55), bold=True)

    text(surface, "DODGED", 13, MUTED, (150, 37), bold=True)
    text(surface, dodged, 27, GREEN, (150, 55), bold=True)

    text(surface, "LEVEL", 13, MUTED, (245, 37), bold=True)
    text(surface, level, 27, CYAN, (245, 55), bold=True)

    text(surface, f"BEST {high_score}", 16, WHITE, (WIDTH - 145, 32), bold=True)


def draw_pause_overlay(surface):
    overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    overlay.fill((4, 7, 20, 190))
    surface.blit(overlay, (0, 0))

    rounded_panel(
        surface,
        (300, 190, 400, 300),
        PANEL,
        CYAN,
        22,
    )
    text(surface, "PAUSED", 55, YELLOW, (WIDTH // 2, 245), center=True, bold=True)
    text(
        surface,
        "Take a breath, racer.",
        18,
        MUTED,
        (WIDTH // 2, 285),
        center=True,
    )


# -------------------- Game --------------------
def countdown():
    for value in ("3", "2", "1", "GO!"):
        start = pygame.time.get_ticks()
        while pygame.time.get_ticks() - start < 700:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()

            draw_background(screen, 0)
            draw_lane_markers(screen, 0)
            text(
                screen,
                value,
                120,
                CYAN if value == "GO!" else YELLOW,
                (WIDTH // 2, HEIGHT // 2),
                center=True,
                bold=True,
            )
            pygame.display.flip()
            clock.tick(FPS)


def play_game(high_score):
    player = pygame.Rect(
        ROAD_LEFT + ROAD_WIDTH // 2 - CAR_W // 2,
        HEIGHT - 145,
        CAR_W,
        CAR_H,
    )

    obstacle = pygame.Rect(0, -CAR_H - 30, CAR_W, CAR_H)
    obstacle_lane = random.randrange(LANES)
    obstacle.x = ROAD_LEFT + obstacle_lane * LANE_WIDTH + (LANE_WIDTH - CAR_W) // 2

    score = 0
    dodged = 0
    level = 1
    speed = 330.0
    road_offset = 0.0
    paused = False
    running = True
    last_time = pygame.time.get_ticks()

    countdown()

    while running:
        now = pygame.time.get_ticks()
        dt = min((now - last_time) / 1000, 0.05)
        last_time = now

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_p, pygame.K_ESCAPE):
                    paused = not paused

                if event.key == pygame.K_r and paused:
                    return play_game(high_score)

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if paused:
                    paused = False

        keys = pygame.key.get_pressed()

        if not paused:
            direction = 0
            if keys[pygame.K_LEFT] or keys[pygame.K_a]:
                direction -= 1
            if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
                direction += 1

            player.x += int(direction * 450 * dt)
            player.left = max(player.left, ROAD_LEFT + 12)
            player.right = min(player.right, ROAD_RIGHT - 12)

            current_speed = speed
            if keys[pygame.K_UP] or keys[pygame.K_w]:
                current_speed += 130
            if keys[pygame.K_DOWN] or keys[pygame.K_s]:
                current_speed -= 100

            obstacle.y += int(current_speed * dt)
            road_offset += current_speed * dt

            if obstacle.top > HEIGHT:
                dodged += 1
                score = dodged * 10
                level = 1 + dodged // 5
                speed = min(330 + level * 28, 760)

                obstacle_lane = random.randrange(LANES)
                obstacle.x = (
                    ROAD_LEFT
                    + obstacle_lane * LANE_WIDTH
                    + (LANE_WIDTH - CAR_W) // 2
                )
                obstacle.y = random.randint(-260, -150)

                if score > high_score:
                    high_score = score
                    save_high_score(high_score)

            if player.colliderect(obstacle.inflate(-12, -10)):
                return "crash", score, high_score

        draw_background(screen, now / 1000)
        draw_lane_markers(screen, road_offset)
        draw_car(screen, obstacle, RED)
        draw_car(screen, player, CYAN, player=True)
        draw_hud(screen, score, dodged, level, high_score)

        text(
            screen,
            "P / ESC  PAUSE",
            15,
            MUTED,
            (WIDTH - 170, HEIGHT - 35),
            bold=True,
        )

        if paused:
            draw_pause_overlay(screen)
            text(
                screen,
                "Press P, ESC, or click to continue",
                18,
                WHITE,
                (WIDTH // 2, 360),
                center=True,
            )

        pygame.display.flip()
        clock.tick(FPS)

    return "menu", score, high_score


def crash_screen(score, high_score):
    start = pygame.time.get_ticks()

    while pygame.time.get_ticks() - start < 1800:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

        draw_background(screen, pygame.time.get_ticks() / 1000)
        draw_lane_markers(screen, 0)

        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((70, 0, 20, 130))
        screen.blit(overlay, (0, 0))

        draw_glow(screen, (WIDTH // 2, 260), 180, RED, 60)
        text(screen, "CRASH!", 90, RED, (WIDTH // 2, 245), center=True, bold=True)
        text(screen, f"Score: {score}", 32, YELLOW, (WIDTH // 2, 335), center=True)
        text(
            screen,
            f"Best Score: {high_score}",
            20,
            WHITE,
            (WIDTH // 2, 375),
            center=True,
        )
        pygame.display.flip()
        clock.tick(FPS)


# -------------------- Menu --------------------
def menu(high_score):
    buttons = [
        Button("START RACE", (350, 355, 300, 58), BLUE, CYAN, "start"),
        Button("HOW TO PLAY", (350, 430, 300, 58), (85, 45, 155), PINK, "help"),
        Button("QUIT", (350, 505, 300, 58), (120, 35, 55), RED, "quit"),
    ]

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            for button in buttons:
                if button.clicked(event):
                    if button.action == "start":
                        result = play_game(high_score)
                        if isinstance(result, tuple):
                            status, score, high_score = result
                            if status == "crash":
                                crash_screen(score, high_score)
                        break

                    if button.action == "help":
                        help_screen()
                        break

                    if button.action == "quit":
                        pygame.quit()
                        sys.exit()

            if event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN:
                result = play_game(high_score)
                if isinstance(result, tuple):
                    status, score, high_score = result
                    if status == "crash":
                        crash_screen(score, high_score)

        draw_background(screen, pygame.time.get_ticks() / 1000)
        draw_title(screen)

        rounded_panel(screen, (330, 275, 340, 52), PANEL, (50, 70, 125))
        text(
            screen,
            f"ALL-TIME BEST: {high_score}",
            20,
            YELLOW,
            (WIDTH // 2, 301),
            center=True,
            bold=True,
        )

        for button in buttons:
            button.draw(screen)

        text(
            screen,
            "Press ENTER to start",
            16,
            MUTED,
            (WIDTH // 2, 605),
            center=True,
        )

        pygame.display.flip()
        clock.tick(FPS)


def help_screen():
    back = Button("BACK TO MENU", (350, 560, 300, 58), BLUE, CYAN, "back")

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            if back.clicked(event):
                return

            if event.type == pygame.KEYDOWN and event.key in (
                pygame.K_ESCAPE,
                pygame.K_BACKSPACE,
            ):
                return

        draw_background(screen, pygame.time.get_ticks() / 1000)

        rounded_panel(screen, (230, 75, 540, 490), PANEL, CYAN, 24)
        text(screen, "HOW TO PLAY", 45, YELLOW, (WIDTH // 2, 125), center=True, bold=True)

        instructions = [
            ("← / A", "Move left"),
            ("→ / D", "Move right"),
            ("↑ / W", "Boost speed"),
            ("↓ / S", "Brake"),
            ("P / ESC", "Pause the game"),
            ("R", "Restart while paused"),
        ]

        y = 190
        for key, description in instructions:
            rounded_panel(screen, (285, y, 150, 42), PANEL_LIGHT, BLUE, 9)
            text(screen, key, 17, CYAN, (360, y + 21), center=True, bold=True)
            text(screen, description, 19, WHITE, (465, y + 21), center=False)
            y += 54

        back.draw(screen)
        pygame.display.flip()
        clock.tick(FPS)


# -------------------- Start --------------------
if __name__ == "__main__":
    menu(load_high_score())