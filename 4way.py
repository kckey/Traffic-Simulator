#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import tkinter as tk
import math
from dataclasses import dataclass, field
from typing import Tuple, Optional

# ----------------------------------------------------------------------
# Configuration
# ----------------------------------------------------------------------
CANVAS_W = 800          # width of the window
CANVAS_H = 600          # height of the window
ROAD_THICKNESS = 120    # width of each road
CAR_SIZE = 30           # square car size
CAR_SPEED = 4           # pixels per frame (frame ≈ 50 ms)
RED_LIGHT_DURATION = 2000   # milliseconds
FRAME_RATE = 20          # ms between frames

# ----------------------------------------------------------------------
def rotate_point(cx, cy, x, y, angle_deg):
    """Rotate point (x,y) around (cx,cy)."""
    ang = math.radians(angle_deg)
    cos_a, sin_a = math.cos(ang), math.sin(ang)
    nx = cos_a * (x - cx) - sin_a * (y - cy) + cx
    ny = sin_a * (x - cx) + cos_a * (y - cy) + cy
    return nx, ny

# ----------------------------------------------------------------------
@dataclass
class Car:
    """A moving car."""
    canvas: tk.Canvas
    direction: str              # "N", "S", "E", "W"
    id: int = field(init=False)
    pos: Tuple[float, float] = field(init=False)
    heading: float = field(init=False)   # degrees (0=East, 90=South)
    color: str = field(default="#00A8FF")
    red_light_id: Optional[int] = field(default=None)

    def __post_init__(self):
        # Starting position depends on direction
        if self.direction == "N":
            self.pos = (CANVAS_W/2, -CAR_SIZE)
            self.heading = 90          # pointing south
        elif self.direction == "S":
            self.pos = (CANVAS_W/2, CANVAS_H + CAR_SIZE)
            self.heading = 270         # pointing north
        elif self.direction == "E":
            self.pos = (CANVAS_W + CAR_SIZE, CANVAS_H/2)
            self.heading = 180         # pointing west
        else:                         # "W"
            self.pos = (-CAR_SIZE, CANVAS_H/2)
            self.heading = 0           # pointing east

        x, y = self.pos
        half = CAR_SIZE / 2
        self.id = self.canvas.create_rectangle(
            x - half, y - half, x + half, y + half,
            fill=self.color, outline="black"
        )

    def move(self):
        """Move the car one frame forward."""
        dx = CAR_SPEED * math.cos(math.radians(self.heading))
        dy = CAR_SPEED * math.sin(math.radians(self.heading))
        self.pos = (self.pos[0] + dx, self.pos[1] + dy)
        self.canvas.move(self.id, dx, dy)

    def stop_at_sign(self):
        """Show a red circle over the car to emulate a stop sign."""
        x, y = self.pos
        r = CAR_SIZE * 2
        if self.red_light_id is None:
            self.red_light_id = self.canvas.create_oval(
                x - r, y - r, x + r, y + r,
                fill="red", outline=""
            )
            # schedule removal after RED_LIGHT_DURATION
            self.canvas.after(RED_LIGHT_DURATION, self.clear_red)

    def clear_red(self):
        if self.red_light_id is not None:
            self.canvas.delete(self.red_light_id)
            self.red_light_id = None

# ----------------------------------------------------------------------
class IntersectionApp(tk.Tk):
    """Main application window."""
    def __init__(self):
        super().__init__()
        self.title("4‑Way Stop‑Sign Intersection")
        self.resizable(False, False)

        # Canvas that holds everything
        self.canvas = tk.Canvas(self, width=CANVAS_W, height=CANVAS_H, bg="#B0E0E6")
        self.canvas.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        # Draw the static intersection (roads + stop signs)
        self.draw_road()
        self.draw_stop_signs()

        # Buttons for spawning cars
        btn_frame = tk.Frame(self)
        btn_frame.pack(side=tk.BOTTOM, pady=10)

        tk.Button(btn_frame, text="North →", command=lambda: self.spawn_car("N")).grid(row=0, column=1, padx=5)
        tk.Button(btn_frame, text="South ←", command=lambda: self.spawn_car("S")).grid(row=0, column=3, padx=5)
        tk.Button(btn_frame, text="West →", command=lambda: self.spawn_car("W")).grid(row=1, column=0, padx=5)
        tk.Button(btn_frame, text="East ←", command=lambda: self.spawn_car("E")).grid(row=1, column=4, padx=5)

        # Keep track of cars
        self.cars = []

        # Start animation loop
        self.after(FRAME_RATE, self.update)

    # ------------------------------------------------------------------
    def draw_road(self):
        """Draw the two perpendicular roads."""
        w = ROAD_THICKNESS
        h = CANVAS_H
        self.canvas.create_rectangle(
            (CANVAS_W - w) / 2, 0,
            (CANVAS_W + w) / 2, h,
            fill="#708090", outline=""
        )
        w = CANVAS_W
        h = ROAD_THICKNESS
        self.canvas.create_rectangle(
            0, (CANVAS_H - h) / 2,
            w, (CANVAS_H + h) / 2,
            fill="#708090", outline=""
        )

    def draw_stop_signs(self):
        """Draw a red stop‑sign at the corner of each road."""
        size = 30
        offset = ROAD_THICKNESS/2 + 10

        # North‑East corner
        self.canvas.create_polygon(
            CANVAS_W - offset, offset,
            CANVAS_W, offset + size/2,
            CANVAS_W - offset, offset + size,
            fill="red", outline=""
        )
        # South‑East
        self.canvas.create_polygon(
            CANVAS_W - offset, CANVAS_H - offset,
            CANVAS_W, CANVAS_H - offset - size/2,
            CANVAS_W - offset, CANVAS_H - offset - size,
            fill="red", outline=""
        )
        # South‑West
        self.canvas.create_polygon(
            offset, CANVAS_H - offset,
            0, CANVAS_H - offset - size/2,
            offset, CANVAS_H - offset - size,
            fill="red", outline=""
        )
        # North‑West
        self.canvas.create_polygon(
            offset, offset,
            0, offset + size/2,
            offset, offset + size,
            fill="red", outline=""
        )

    # ------------------------------------------------------------------
    def spawn_car(self, direction: str):
        """Create a car object and add it to the animation loop."""
        car = Car(canvas=self.canvas, direction=direction)
        self.cars.append(car)

    # ------------------------------------------------------------------
    def update(self):
        """Main animation loop – called every FRAME_RATE ms."""
        for car in list(self.cars):   # copy list because we may delete
            car.move()
            if not car.red_light_id and self.is_at_stop_line(car):
                car.stop_at_sign()

            # If the car has passed beyond the canvas, drop it
            x, y = car.pos
            if (x < -CAR_SIZE or x > CANVAS_W + CAR_SIZE or
                y < -CAR_SIZE or y > CANVAS_H + CAR_SIZE):
                self.canvas.delete(car.id)
                if car.red_light_id is not None:
                    self.canvas.delete(car.red_light_id)
                self.cars.remove(car)

        # Schedule next frame
        self.after(FRAME_RATE, self.update)

    def is_at_stop_line(self, car: Car) -> bool:
        """Return True when the car reaches the stop line."""
        x, y = car.pos
        margin = CAR_SIZE  # stop a bit before center

        if car.direction == "N":
            return y >= CANVAS_H/2 - ROAD_THICKNESS/4
        if car.direction == "S":
            return y <= CANVAS_H/2 + ROAD_THICKNESS/4
        if car.direction == "E":
            return x <= CANVAS_W/2 + ROAD_THICKNESS/4
        if car.direction == "W":
            return x >= CANVAS_W/2 - ROAD_THICKNESS/4
        return False

# ----------------------------------------------------------------------
if __name__ == "__main__":
    app = IntersectionApp()
    app.mainloop()
