from __future__ import annotations
from dataclasses import dataclass
from functools import reduce
from itertools import pairwise
from math import copysign
import operator
from typing import Any
import pygame as pg
from sys import exit
from collections import deque
from config import *
pg.font.init()
font = pg.font.SysFont("Arial", 24)


def rect_lines(rect: pg.Rect, /):
    return [
        (pg.Vector2(rect.bottomleft), pg.Vector2(rect.bottomright)),
        (pg.Vector2(rect.bottomright), pg.Vector2(rect.topright)),
        (pg.Vector2(rect.topright), pg.Vector2(rect.topleft)),
        (pg.Vector2(rect.topleft), pg.Vector2(rect.bottomleft))
    ]


def rect_points(rect: pg.Rect, /):
    return [pg.Vector2(rect.bottomleft), pg.Vector2(rect.bottomright), pg.Vector2(rect.topright), pg.Vector2(rect.topleft)]


class WallGrid(dict[tuple[int, int], bool]):
    def __missing__(self, _):
        return False


def sign(x):
    if x == 0:
        return 1
    return copysign(1, x)


def remove_duplicates(l: list, /):
    found = []
    dup = []
    for i in l:
        if i in found:
            if i not in dup:
                dup.append(i)
        else:
            found.append(i)
    for i in dup:
        l.remove(i)


def draw_shadows(walls: list[Wall], pos: pg.Vector2) -> list[list[pg.Vector2]]:
    shadows = []
    for wall in walls:
        lines = wall.lines
        points = deque(wall.points)
        points_on_illuminated_lines = []
        points_on_non_illuminated_lines = []
        for line in lines:
            a, b = line
            midpoint = (a+b)/2
            tangent = (b - a).normalize()
            normal = tangent.rotate(90)
            dir_to_light = (pos - midpoint).normalize()
            dot = normal * dir_to_light
            if dot > 0:
                points_on_illuminated_lines.extend([a, b])
            else:
                points_on_non_illuminated_lines.extend([a, b])
        remove_duplicates(points_on_illuminated_lines)
        remove_duplicates(points_on_non_illuminated_lines)
        if len(points_on_illuminated_lines) == 0:
            continue
        points.rotate(-points.index(points_on_illuminated_lines[0]))
        
        points = list(points)
        for i in range(2):
            shadow = []
            in_shadow = bool(i)

            for i in points:
                if not in_shadow:
                    if i in points_on_non_illuminated_lines:
                        shadow.append(i + (i - pos).normalize() * 10000)
                    if i in points_on_illuminated_lines:
                        shadow.append(i)
                else:
                    if i in points_on_illuminated_lines:
                        shadow.append(i)
                    if i in points_on_non_illuminated_lines:
                        shadow.append(i + (i - pos).normalize() * 10000)
                if i in points_on_illuminated_lines and i in points_on_non_illuminated_lines:
                    in_shadow = not in_shadow
            
            done = False
            for a, b in (list(pairwise(shadow)) + [(shadow[len(shadow)-1], shadow[0])]):
                if a in points and b in points:
                    done = True
            if done:
                break 
        shadows.append(shadow)
    return shadows


class Camera:
    pos: pg.Vector2
    rot: float
    window_size: pg.Vector2

    def __init__(self, pos: pg.Vector2 | tuple[float, float], rot: float, window_size: pg.Vector2 | tuple[int, int]):
        self.pos = pg.Vector2(pos)
        self.rot = rot
        self.window_size = pg.Vector2(window_size)

    @property
    def fwd(self):
        up = pg.Vector2(0, -1)
        return up.rotate(self.rot)
    
    def transform(self, p: pg.Vector2, /):
        return (p - self.pos).rotate(-self.rot) + self.window_size/2
    
    def reverse_transform(self, p: pg.Vector2, /):
        return p.rotate(self.rot) + self.pos - self.window_size/2


class Wall(pg.Rect):
    @property
    def points(self):
        return [
            pg.Vector2(self.bottomleft),
            pg.Vector2(self.bottomright),
            pg.Vector2(self.topright),
            pg.Vector2(self.topleft)
        ]
    
    @property
    def lines(self):
        return [
            (pg.Vector2(self.bottomleft), pg.Vector2(self.bottomright)),
            (pg.Vector2(self.bottomright), pg.Vector2(self.topright)),
            (pg.Vector2(self.topright), pg.Vector2(self.topleft)),
            (pg.Vector2(self.topleft), pg.Vector2(self.bottomleft))
        ]

    def transform(self, camera: Camera) -> list[pg.Vector2]:
        shorter_window_dimension: float = min(camera.window_size.x, camera.window_size.y)
        transformed = self.scale_by(1/shorter_window_dimension, 1/shorter_window_dimension)
        points = transformed.points
        points = [camera.transform(i) for i in points]
        return points


def main():
    window = pg.display.set_mode(flags=pg.FULLSCREEN)
    walls = [Wall(0.25, 0.25, 0.25, 0.5)]

    player_pos = pg.Vector2(600, 600)
    player_dir = 0

    camera = Camera(player_pos, player_dir, window.get_size())

    up = pg.Vector2(0, -1)

    player_light = pg.Surface(window.get_size())

    clock = pg.time.Clock()
    ms = 1
    while True:
        for event in pg.event.get():
            if event.type == pg.QUIT or event.type == pg.KEYDOWN and event.key == pg.K_ESCAPE:
                exit()
        player_fwd = up.rotate(player_dir)

        keys = pg.key.get_pressed()
        player_motion = 0.1 * ms * (keys[pg.K_w] - keys[pg.K_s])
        player_rot_motion = 0.1 * ms * (keys[pg.K_d] - keys[pg.K_a])
        player_pos += player_fwd * player_motion
        player_dir += player_rot_motion

        camera.pos = player_pos
        camera.rot = player_dir

        window.fill("#555555")
        player_light.fill(0)

        for wall in walls:
            wall.draw(window, camera)

        pg.draw.circle(window, "#FFFF00", player_pos, 15)
        pg.draw.circle(player_light, "#FFFFFF", player_pos, 20)
        pg.draw.polygon(player_light, "#FFFFFF", tuple([player_pos] + [player_fwd.rotate(-45/2 + i/FOV_RES)*PLAYER_VIEW_DST + player_pos for i in range(FOV * FOV_RES)]))
        draw_shadows(player_light, walls, player_pos)

        window.blit(player_light, (0, 0), special_flags=pg.BLEND_MULT)

        pg.display.flip()
        ms = clock.tick()


if __name__ == "__main__":
    main()
