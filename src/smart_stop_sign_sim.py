# traffic_sim.py
import pygame
import sys
import math
import random
from collections import deque

# -------------------------------------------------------------
# Visual theme helpers
def lighten(color, amount):
    return tuple(min(255, c + amount) for c in color)


def create_vertical_gradient(size, top_color, bottom_color):
    width, height = size
    surface = pygame.Surface((width, height))
    if height <= 1:
        surface.fill(top_color)
        return surface

    for y in range(height):
        lerp = y / (height - 1)
        color = tuple(
            int(top_color[i] + (bottom_color[i] - top_color[i]) * lerp)
            for i in range(3)
        )
        pygame.draw.line(surface, color, (0, y), (width, y))
    return surface

# -------------------------------------------------------------
# Constants
WIDTH, HEIGHT = 1100, 720
SIM_WIDTH = 760
PANEL_X = 790
PANEL_WIDTH = WIDTH - PANEL_X - 24
ROAD_WIDTH = 40
LANE_COUNT = 2
INTERSECTION_SIZE = ROAD_WIDTH * LANE_COUNT * 3

STOP_SIGN_RADIUS = 30

CAR_LENGTH, CAR_HEIGHT = 20, 10
CAR_SPEED = 200  # pixels per second

QUEUE_GAP = 8
QUEUE_SPACING = CAR_LENGTH + QUEUE_GAP

STOP_WAIT_MS = 3000
INTERSECTION_HALF = INTERSECTION_SIZE // 2

# -------------------------------------------------------------
# Directions (incoming -> toward intersection)
DIRECTION_VECTORS = {
    'west':  pygame.math.Vector2(1, 0),   # from left -> right
    'east':  pygame.math.Vector2(-1, 0),  # from right -> left
    'north': pygame.math.Vector2(0, 1),   # from top -> down
    'south': pygame.math.Vector2(0, -1),  # from bottom -> up
}

# -------------------------------------------------------------
# Color palette / theme  — clean light mode
COLOR_BG_TOP    = (236, 240, 245)
COLOR_BG_BOTTOM = (218, 224, 232)
CANVAS_TOP      = (210, 218, 228)
CANVAS_BOTTOM   = (195, 204, 215)
ROAD_COLOR      = (88,  92,  98)
ROAD_EDGE       = (68,  72,  78)
LANE_MARKING    = (255, 210, 60)
CROSSWALK_COLOR = (255, 255, 255)
INTERSECTION_BORDER = (140, 150, 162)
BUTTON_COLOR    = (34,  130, 112)
BUTTON_HOVER    = (28,  108,  92)
BUTTON_TEXT     = (255, 255, 255)
BUTTON_PANEL    = (255, 255, 255, 240)
INFO_PANEL      = (250, 251, 253, 250)   # near-white panel
CARD_PANEL      = (240, 243, 248, 255)   # light-grey card
INFO_TEXT       = (24,  32,  46)         # near-black
SECONDARY_TEXT  = (80,  96, 115)
MUTED_TEXT      = (140, 155, 172)
ACCENT_GREEN    = (22,  168, 102)
ACCENT_AMBER    = (210, 130,  20)
WARNING         = (210, 130,  20)
SHADOW          = (0,   0,   0,  28)
DIVIDER         = (218, 224, 232)
# Per-direction palette — cars AND buttons
CAR_COLORS = {
    'west':  (48,  130, 220),
    'east':  (220,  88,  48),
    'north': (190, 145,  10),
    'south': (48,  168,  80),
}
DIR_LIGHT = {          # light tint for button backgrounds
    'west':  (224, 236, 252),
    'east':  (252, 230, 222),
    'north': (252, 244, 210),
    'south': (220, 248, 228),
}

# Keyboard mapping for quick spawning
KEY_DIRECTIONS = {
    pygame.K_a: 'west',
    pygame.K_LEFT: 'west',
    pygame.K_d: 'east',
    pygame.K_RIGHT: 'east',
    pygame.K_w: 'north',
    pygame.K_UP: 'north',
    pygame.K_s: 'south',
    pygame.K_DOWN: 'south',
}

# -------------------------------------------------------------
# Drawing helpers
def draw_text(surface, font, text, color, pos, anchor="topleft"):
    rendered = font.render(text, True, color)
    rect = rendered.get_rect()
    setattr(rect, anchor, pos)
    surface.blit(rendered, rect)
    return rect


def draw_panel(surface, rect, color=INFO_PANEL, radius=18, border=(200, 210, 222)):
    shadow_rect = rect.move(0, 5)
    shadow = pygame.Surface(shadow_rect.size, pygame.SRCALPHA)
    pygame.draw.rect(shadow, SHADOW, shadow.get_rect(), border_radius=radius)
    surface.blit(shadow, shadow_rect.topleft)
    panel = pygame.Surface(rect.size, pygame.SRCALPHA)
    pygame.draw.rect(panel, color, panel.get_rect(), border_radius=radius)
    surface.blit(panel, rect.topleft)
    pygame.draw.rect(surface, border, rect, 1, border_radius=radius)


def draw_status_pill(surface, rect, text, active=False):
    fill = (34, 66, 51) if active else (42, 48, 56)
    border = ACCENT_GREEN if active else (78, 88, 98)
    pygame.draw.rect(surface, fill, rect, border_radius=rect.height // 2)
    pygame.draw.rect(surface, border, rect, 1, border_radius=rect.height // 2)
    dot_color = ACCENT_GREEN if active else MUTED_TEXT
    pygame.draw.circle(surface, dot_color, (rect.x + 15, rect.centery), 5)


def draw_stop_sign(surface, center, radius, font, green_on=False, flash_phase=0.0):
    """Octagon + STOP text + bright green light above it (steady ON, slow 1s pulse)."""
    cx, cy = center

    # Octagon
    angles = [22.5 + i * 45 for i in range(8)]
    points = [
        (cx + radius * math.cos(math.radians(a)),
         cy + radius * math.sin(math.radians(a)))
        for a in angles
    ]
    pygame.draw.polygon(surface, (255, 0, 0), points)
    pygame.draw.polygon(surface, (240, 240, 240), points, 2)

    # STOP text
    text = font.render("STOP", True, (255, 255, 255))
    text_rect = text.get_rect(center=(cx, cy))
    surface.blit(text, text_rect)

    # Light directly above the sign (screen-up)
    light_center = (int(cx), int(cy - radius - 16))

    if green_on:
        # Slow 1-second pulse while the light is ON.
        # (It stays green continuously until the car clears the intersection.)
        pulse = 0.75 + 0.25 * math.sin(flash_phase)  # ~0.5..1.0 but gentle
        core_r = int(14 * pulse)                     # ~7..14+ (but never "off")
        core_r = max(core_r, 10)

        glow_r1 = int(30 * pulse)
        glow_r2 = int(48 * pulse)

        glow = pygame.Surface((glow_r2 * 2, glow_r2 * 2), pygame.SRCALPHA)
        pygame.draw.circle(glow, (0, 255, 0, 70),  (glow_r2, glow_r2), glow_r2)
        pygame.draw.circle(glow, (0, 255, 0, 130), (glow_r2, glow_r2), glow_r1)
        pygame.draw.circle(glow, (0, 255, 0, 230), (glow_r2, glow_r2), int(glow_r1 * 0.55))
        surface.blit(glow, (light_center[0] - glow_r2, light_center[1] - glow_r2))

        # Core (steady neon)
        pygame.draw.circle(surface, (0, 255, 0), light_center, core_r)
        pygame.draw.circle(surface, (220, 255, 220), light_center, max(3, core_r // 3))
    else:
        pygame.draw.circle(surface, (20, 40, 20), light_center, 10)

    pygame.draw.circle(surface, (240, 240, 240), light_center, 10, 1)

def draw_car(surface, car):
    pos = car.pos
    if car.direction in ('north', 'south'):
        rect = pygame.Rect(int(pos.x - CAR_HEIGHT // 2), int(pos.y), CAR_HEIGHT, CAR_LENGTH)
    else:
        rect = pygame.Rect(int(pos.x), int(pos.y - CAR_HEIGHT // 2), CAR_LENGTH, CAR_HEIGHT)

    # subtle drop shadow
    shadow = pygame.Surface((rect.width + 8, rect.height + 8), pygame.SRCALPHA)
    pygame.draw.ellipse(shadow, (0, 0, 0, 90), shadow.get_rect())
    surface.blit(shadow, (rect.x - 4, rect.y - 2))

    body_color = getattr(car, 'color', CAR_COLORS.get(car.direction, (0, 128, 255)))
    pygame.draw.rect(surface, (18, 23, 30), rect.inflate(2, 2), border_radius=6)
    pygame.draw.rect(surface, body_color, rect, border_radius=6)

    # dark glass strip
    if car.direction in ('north', 'south'):
        glass_rect = pygame.Rect(rect.x + 2, rect.y + 5, rect.width - 4, 7)
    else:
        glass_rect = pygame.Rect(rect.x + 6, rect.y + 2, 8, rect.height - 4)
    pygame.draw.rect(surface, (25, 40, 55), glass_rect, border_radius=3)

    # headlights / taillights for direction hint
    light_color = (255, 240, 200)
    brake_color = (255, 100, 90)
    if car.direction in ('west', 'east'):
        hx = rect.right - 3 if car.direction == 'west' else rect.left + 1
        bx = rect.left + 1 if car.direction == 'west' else rect.right - 3
        pygame.draw.rect(surface, light_color, (hx - 2, rect.y + 2, 3, rect.height - 4), border_radius=2)
        pygame.draw.rect(surface, brake_color, (bx - 2, rect.y + 2, 3, rect.height - 4), border_radius=2)
    else:
        hy = rect.top + 1 if car.direction == 'south' else rect.bottom - 3
        by = rect.bottom - 3 if car.direction == 'south' else rect.top + 1
        pygame.draw.rect(surface, light_color, (rect.x + 2, hy - 1, rect.width - 4, 3), border_radius=2)
        pygame.draw.rect(surface, brake_color, (rect.x + 2, by - 1, rect.width - 4, 3), border_radius=2)


def draw_button(surface, rect, title, hint, font, font_small, hovered=False, direction=None):
    dir_color = CAR_COLORS.get(direction, BUTTON_COLOR) if direction else BUTTON_COLOR
    dir_bg    = DIR_LIGHT.get(direction, (230, 240, 235)) if direction else (230, 240, 235)

    base = tuple(max(0, c - 12) for c in dir_bg) if hovered else dir_bg

    pygame.draw.rect(surface, base, rect, border_radius=10)
    # Left color accent stripe
    accent_rect = pygame.Rect(rect.x, rect.y, 4, rect.height)
    pygame.draw.rect(surface, dir_color, accent_rect, border_radius=3)
    # Border — slightly darker than bg
    border_col = tuple(max(0, c - 30) for c in dir_bg)
    pygame.draw.rect(surface, border_col, rect, 1, border_radius=10)

    # Direction label in the direction's saturated color
    draw_text(surface, font, title, dir_color, (rect.x + 18, rect.y + 10))

    # Key hint badge
    key_rect = pygame.Rect(rect.right - 44, rect.y + 8, 28, 22)
    pygame.draw.rect(surface, (255, 255, 255), key_rect, border_radius=6)
    pygame.draw.rect(surface, border_col, key_rect, 1, border_radius=6)
    draw_text(surface, font_small, hint, INFO_TEXT, key_rect.center, anchor="center")


def draw_side_panel(surface, fonts, queues, controller, button_rects, mouse_pos, throughput=0, green_elapsed_ms=0):
    font_title, font_medium, font_small, font_button, font_status = fonts
    panel_rect = pygame.Rect(PANEL_X, 16, PANEL_WIDTH, HEIGHT - 32)
    draw_panel(surface, panel_rect, INFO_PANEL, radius=18, border=(210, 218, 228))

    py = panel_rect.y

    # ── Header — single line to avoid overflow ──────────────────
    draw_text(surface, font_medium,  "Intersection Control", INFO_TEXT, (panel_rect.x + 20, py + 20))
    draw_text(surface, font_small,   "4-way stop simulation", MUTED_TEXT, (panel_rect.x + 20, py + 46))

    div_y = py + 68
    pygame.draw.line(surface, DIVIDER, (panel_rect.x + 16, div_y), (panel_rect.right - 16, div_y), 1)

    # ── Right-of-way pill ──────────────────────────────────────
    active_dir   = controller.green_dir
    active_label = active_dir.title() if active_dir else "Waiting"
    pill_y    = div_y + 12
    pill_rect = pygame.Rect(panel_rect.x + 16, pill_y, panel_rect.width - 32, 36)
    pill_color = CAR_COLORS.get(active_dir, MUTED_TEXT) if active_dir else MUTED_TEXT
    # light tinted fill
    if active_dir:
        light_tint = DIR_LIGHT.get(active_dir, (230, 240, 235))
    else:
        light_tint = (230, 234, 240)
    pygame.draw.rect(surface, light_tint, pill_rect, border_radius=pill_rect.height // 2)
    pygame.draw.rect(surface, pill_color, pill_rect, 1, border_radius=pill_rect.height // 2)
    dot_x = pill_rect.x + 14
    pygame.draw.circle(surface, pill_color, (dot_x, pill_rect.centery), 5)
    draw_text(surface, font_status, f"Right of way: {active_label}",
              pill_color if active_dir else SECONDARY_TEXT, (dot_x + 12, pill_rect.y + 9))
    if active_dir and green_elapsed_ms > 0:
        draw_text(surface, font_small, f"{green_elapsed_ms/1000:.1f}s",
                  pill_color, (pill_rect.right - 42, pill_rect.y + 10))

    # ── KPI cards ──────────────────────────────────────────────
    card_y = pill_y + 48
    pygame.draw.line(surface, DIVIDER, (panel_rect.x + 16, card_y - 8), (panel_rect.right - 16, card_y - 8), 1)

    total   = sum(len(q) for q in queues.values())
    moving  = sum(1 for q in queues.values() for car in q if car.state == 'crossing')
    waiting = total - moving
    card_w  = (panel_rect.width - 52) // 3
    kpis = [
        ("QUEUED", str(total),   ACCENT_AMBER),
        ("MOVING", str(moving),  ACCENT_GREEN),
        ("WAITING", str(waiting), SECONDARY_TEXT),
    ]
    for idx, (label, value, color) in enumerate(kpis):
        card = pygame.Rect(panel_rect.x + 16 + idx * (card_w + 10), card_y, card_w, 66)
        draw_panel(surface, card, CARD_PANEL, radius=12, border=(210, 218, 228))
        draw_text(surface, font_small, label, MUTED_TEXT,  (card.x + 8, card.y + 9))
        draw_text(surface, font_medium, value, color,      (card.x + 8, card.y + 31))

    tp_y = card_y + 74
    draw_text(surface, font_small, f"Throughput: {throughput} cars passed",
              MUTED_TEXT, (panel_rect.x + 20, tp_y))

    # ── Queue depth ────────────────────────────────────────────
    queue_top = tp_y + 26
    pygame.draw.line(surface, DIVIDER, (panel_rect.x + 16, queue_top - 4), (panel_rect.right - 16, queue_top - 4), 1)
    draw_text(surface, font_medium, "Queue Depth", INFO_TEXT, (panel_rect.x + 20, queue_top + 4))

    order     = ['west', 'north', 'east', 'south']
    max_len   = max(1, max(len(queues[d]) for d in order))
    bar_x     = panel_rect.x + 72
    bar_right = panel_rect.right - 36
    bar_width = bar_right - bar_x

    for i, d in enumerate(order):
        row_y    = queue_top + 34 + i * 30
        q_len    = len(queues[d])
        is_green = (controller.green_dir == d)
        dir_col  = CAR_COLORS[d]
        label_col = dir_col if is_green else SECONDARY_TEXT

        draw_text(surface, font_small, d.title(), label_col, (panel_rect.x + 18, row_y))

        bar_bg = pygame.Rect(bar_x, row_y + 3, bar_width, 11)
        pygame.draw.rect(surface, DIVIDER, bar_bg, border_radius=6)

        fill_w = int(bar_width * (q_len / max_len)) if q_len else 0
        if fill_w > 0:
            fill_color = dir_col if is_green else tuple(min(255, c + 60) for c in dir_col)
            pygame.draw.rect(surface, fill_color,
                             (bar_bg.x, bar_bg.y, fill_w, bar_bg.height), border_radius=6)

        draw_text(surface, font_small, str(q_len),
                  label_col if q_len else MUTED_TEXT, (bar_right + 6, row_y))

    # ── Dispatch buttons ───────────────────────────────────────
    dispatch_top = queue_top + 34 + 4 * 30 + 14
    pygame.draw.line(surface, DIVIDER, (panel_rect.x + 16, dispatch_top - 6),
                     (panel_rect.right - 16, dispatch_top - 6), 1)
    draw_text(surface, font_medium, "Dispatch", INFO_TEXT, (panel_rect.x + 20, dispatch_top))
    draw_text(surface, font_small, "Buttons · WASD · arrow keys",
              MUTED_TEXT, (panel_rect.x + 20, dispatch_top + 24))

    key_map = {'west': 'A', 'north': 'W', 'south': 'S', 'east': 'D'}
    for d, rect in button_rects.items():
        hovered = rect.collidepoint(mouse_pos)
        draw_button(surface, rect, f"Send {d.title()}", key_map[d],
                    font_button, font_small, hovered=hovered, direction=d)


def draw_roads(surface, center, intersection_rect):
    sim_rect = pygame.Rect(0, 0, SIM_WIDTH, HEIGHT)
    pygame.draw.rect(surface, (188, 200, 210), sim_rect)   # light slate canvas
    # subtle grid texture
    for x in range(0, SIM_WIDTH, 80):
        pygame.draw.line(surface, (178, 190, 202), (x, 0), (x + 100, HEIGHT), 1)

    horiz = pygame.Rect(0, center[1] - ROAD_WIDTH // 2, SIM_WIDTH, ROAD_WIDTH)
    vert = pygame.Rect(center[0] - ROAD_WIDTH // 2, 0, ROAD_WIDTH, HEIGHT)

    pygame.draw.rect(surface, ROAD_EDGE, horiz.inflate(0, 12), border_radius=8)
    pygame.draw.rect(surface, ROAD_EDGE, vert.inflate(12, 0), border_radius=8)
    pygame.draw.rect(surface, ROAD_COLOR, horiz, border_radius=6)
    pygame.draw.rect(surface, ROAD_COLOR, vert, border_radius=6)

    # Double-yellow lane markings
    pygame.draw.line(surface, LANE_MARKING, (0, center[1] - 4), (SIM_WIDTH, center[1] - 4), 2)
    pygame.draw.line(surface, LANE_MARKING, (0, center[1] + 4), (SIM_WIDTH, center[1] + 4), 2)
    pygame.draw.line(surface, LANE_MARKING, (center[0] - 4, 0), (center[0] - 4, HEIGHT), 2)
    pygame.draw.line(surface, LANE_MARKING, (center[0] + 4, 0), (center[0] + 4, HEIGHT), 2)

    # Crosswalk strips
    def crosswalk(y_offset, horizontal=True):
        stripes = 6
        stripe_w = INTERSECTION_SIZE // 8
        gap = 10
        for i in range(stripes):
            if horizontal:
                x = intersection_rect.left + i * (stripe_w + gap)
                rect = pygame.Rect(x, y_offset, stripe_w, 4)
            else:
                y = intersection_rect.top + i * (stripe_w + gap)
                rect = pygame.Rect(y_offset, y, 4, stripe_w)
            pygame.draw.rect(surface, CROSSWALK_COLOR, rect)

    crosswalk(intersection_rect.top - 16)
    crosswalk(intersection_rect.bottom + 12)
    crosswalk(intersection_rect.left - 16, horizontal=False)
    crosswalk(intersection_rect.right + 12, horizontal=False)

    pygame.draw.rect(surface, INTERSECTION_BORDER, intersection_rect, 3)
    pygame.draw.line(surface, (11, 15, 20), (SIM_WIDTH, 0), (SIM_WIDTH, HEIGHT), 2)

# -------------------------------------------------------------
# Car class
class Car:
    """
    States:
      - 'approach': moving toward its queue target
      - 'waiting': front car sitting at stop sign counting stop time
      - 'crossing': allowed to go through intersection
      - 'done': exited screen
    """
    def __init__(self, direction, start_pos, stop_sign):
        self.direction = direction
        self.pos = pygame.math.Vector2(start_pos)
        self.stop_sign = pygame.math.Vector2(stop_sign)
        self.dir_vec = DIRECTION_VECTORS[direction]
        base_color = CAR_COLORS.get(direction, (0, 128, 255))
        self.color = tuple(
            max(25, min(255, c + random.randint(-25, 25)))
            for c in base_color
        )

        self.state = 'approach'
        self.wait_start = None
        self.done = False

    def queue_target(self, queue_index: int) -> pygame.math.Vector2:
        return self.stop_sign - self.dir_vec * (queue_index * QUEUE_SPACING)

    def update_approach_or_wait(self, dt, target: pygame.math.Vector2, is_front: bool):
        to_target = target - self.pos
        dist = to_target.length()

        if dist <= 0.001:
            self.pos = target
            if is_front and self.state != 'waiting':
                self.state = 'waiting'
                self.wait_start = pygame.time.get_ticks()
            return

        step = CAR_SPEED * dt
        if dist <= step:
            self.pos = target
        else:
            self.pos += (to_target / dist) * step

        if is_front and (self.pos - target).length() < 0.5:
            if self.state != 'waiting':
                self.state = 'waiting'
                self.wait_start = pygame.time.get_ticks()

    def update_crossing(self, dt, screen_rect):
        self.pos += self.dir_vec * CAR_SPEED * dt
        if not screen_rect.collidepoint((self.pos.x, self.pos.y)):
            self.done = True
            self.state = 'done'

# -------------------------------------------------------------
# Intersection controller
class StopController:
    """
    One direction green at a time.
    Eligible: front car is waiting AND waited STOP_WAIT_MS.
    Green stays until that released car clears the intersection rectangle.
    """
    def __init__(self, directions):
        self.directions = list(directions)
        self.green_dir = None
        self.last_index = 0

    def choose_next(self, queues):
        n = len(self.directions)
        now = pygame.time.get_ticks()
        for i in range(n):
            d = self.directions[(self.last_index + i) % n]
            if queues[d]:
                car = queues[d][0]
                if car.state == 'waiting' and car.wait_start is not None:
                    if now - car.wait_start >= STOP_WAIT_MS:
                        self.last_index = (self.last_index + i + 1) % n
                        return d
        return None

    def update(self, queues, intersection_rect):
        # Keep green until the released car clears the intersection
        if self.green_dir is not None and queues[self.green_dir]:
            car = queues[self.green_dir][0]
            if car.state == 'crossing':
                if not intersection_rect.collidepoint((car.pos.x, car.pos.y)):
                    self.green_dir = None
            if car.done:
                self.green_dir = None
        else:
            self.green_dir = None

        if self.green_dir is None:
            nxt = self.choose_next(queues)
            if nxt is not None:
                self.green_dir = nxt
                queues[nxt][0].state = 'crossing'

# -------------------------------------------------------------
# Main
def main():
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("4-Way Stop Traffic Simulation")
    clock = pygame.time.Clock()
    simulation_rect = pygame.Rect(0, 0, SIM_WIDTH, HEIGHT)

    center = (SIM_WIDTH // 2, HEIGHT // 2)

    intersection_rect = pygame.Rect(
        center[0] - INTERSECTION_HALF,
        center[1] - INTERSECTION_HALF,
        INTERSECTION_SIZE,
        INTERSECTION_SIZE
    )

    # Even spacing on centerlines
    STOP_OFFSET = INTERSECTION_HALF + STOP_SIGN_RADIUS + 18
    stop_positions = {
        'west':  (center[0] - STOP_OFFSET, center[1]),
        'east':  (center[0] + STOP_OFFSET, center[1]),
        'north': (center[0], center[1] - STOP_OFFSET),
        'south': (center[0], center[1] + STOP_OFFSET),
    }

    start_positions = {
        'west':  (0, center[1]),
        'east':  (SIM_WIDTH, center[1]),
        'north': (center[0], 0),
        'south': (center[0], HEIGHT),
    }

    queues = {d: deque() for d in stop_positions}
    controller = StopController(['west', 'north', 'east', 'south'])

    # Build themed background layers
    background = create_vertical_gradient((WIDTH, HEIGHT), COLOR_BG_TOP, COLOR_BG_BOTTOM)
    road_layer = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    draw_roads(road_layer, center, intersection_rect)
    button_order = ['west', 'north', 'south', 'east']
    button_size = (PANEL_WIDTH - 40, 36)
    button_rects = {}
    for idx, direction in enumerate(button_order):
        bx = PANEL_X + 20
        by = 530 + idx * 42
        button_rects[direction] = pygame.Rect(bx, by, *button_size)

    font_small = pygame.font.SysFont("Avenir Next", 15, bold=True) or pygame.font.SysFont(None, 15, bold=True)
    font_medium = pygame.font.SysFont("Avenir Next", 20, bold=True) or pygame.font.SysFont(None, 20, bold=True)
    font_button = pygame.font.SysFont("Avenir Next", 19, bold=True) or pygame.font.SysFont(None, 19, bold=True)
    font_status = pygame.font.SysFont("Avenir Next", 18, bold=True) or pygame.font.SysFont(None, 18, bold=True)
    font_info_title = pygame.font.SysFont("Avenir Next", 28, bold=True) or pygame.font.SysFont(None, 28, bold=True)
    font_stop = pygame.font.SysFont(None, 18, bold=True)
    fonts = (font_info_title, font_medium, font_small, font_button, font_status)

    def enqueue_car(direction):
        if direction not in start_positions:
            return
        car = Car(direction, start_positions[direction], stop_positions[direction])
        queues[direction].append(car)

    # flash_phase now advances at 2π per second -> 1 second cycle
    flash_phase = 0.0
    throughput   = 0          # cars that have fully exited
    green_start  = None       # when current green phase began

    running = True
    while running:
        dt = clock.tick(60) / 1000.0
        flash_phase += dt * (2.0 * math.pi)  # 1-second pulse cycle

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                for d, rect in button_rects.items():
                    if rect.collidepoint(event.pos):
                        enqueue_car(d)

            elif event.type == pygame.KEYDOWN:
                direction = KEY_DIRECTIONS.get(event.key)
                if direction:
                    enqueue_car(direction)

        prev_green = controller.green_dir
        controller.update(queues, intersection_rect)
        if controller.green_dir != prev_green:
            green_start = pygame.time.get_ticks() if controller.green_dir else None

        # update cars
        for d, q in queues.items():
            for i, car in enumerate(list(q)):
                if car.state == 'crossing':
                    car.update_crossing(dt, simulation_rect)
                elif car.state != 'done':
                    target = car.queue_target(i)
                    car.update_approach_or_wait(dt, target, is_front=(i == 0))

        # remove exited cars + tally throughput
        for d in list(queues.keys()):
            exited = sum(1 for c in queues[d] if c.done)
            throughput += exited
            while queues[d] and queues[d][0].done:
                queues[d].popleft()
            queues[d] = deque([c for c in queues[d] if not c.done])

        green_elapsed = (pygame.time.get_ticks() - green_start) if green_start else 0

        # draw
        screen.blit(background, (0, 0))
        screen.blit(road_layer, (0, 0))
        draw_text(screen, font_info_title, "Live Traffic Lab", (24, 32, 46), (28, 20))
        draw_text(screen, font_small, "Four-way stop controller with timed right-of-way handoff.", (80, 96, 115), (30, 52))

        for d, pos in stop_positions.items():
            draw_stop_sign(
                screen,
                pos,
                STOP_SIGN_RADIUS,
                font_stop,
                green_on=(controller.green_dir == d),
                flash_phase=flash_phase
            )

        for q in queues.values():
            for car in q:
                draw_car(screen, car)

        mouse_pos = pygame.mouse.get_pos()
        draw_side_panel(screen, fonts, queues, controller, button_rects, mouse_pos,
                        throughput=throughput, green_elapsed_ms=green_elapsed)

        pygame.display.flip()

    pygame.quit()
    sys.exit()

# -------------------------------------------------------------
if __name__ == "__main__":
    main()
