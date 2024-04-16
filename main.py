from dataclasses import dataclass
from itertools import pairwise
from math import copysign
import pygame as pg
from sys import exit
from collections import deque
from config import *
pg.font.init()
font = pg.font.SysFont("Arial", 24)


@dataclass
class Polygon:
    points: list[pg.Vector2]

    @property
    def convex(self):
        def cross_product(p1, p2, p3):
            return (p2.x - p1.x) * (p3.y - p2.y) - (p2.y - p1.y) * (p3.x - p2.x)

        n = len(self.points)
        if n < 3:
            return False
        
        sign = None
        for i in range(n):
            p1, p2, p3 = self.points[i], self.points[(i + 1) % n], self.points[(i + 2) % n]
            cp = cross_product(p1, p2, p3)
            if cp != 0:
                if sign is None:
                    sign = cp > 0
                elif sign != (cp > 0):
                    return False
        return True
    
    @property
    def lines(self):
        return list(pairwise(self.points)) + [(self.points[len(self.points)-1], self.points[0])]

    def draw(self, window):
        pg.draw.polygon(window, "#FFFFFF", tuple(self.points))
    
    def to_convex_polygons(self):
        if self.convex:
            return [self.points]
        else:
            raise NotImplementedError


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


def draw_shadows(window: pg.Surface, walls: list[Polygon], pos: pg.Vector2):
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
                        shadow.append(pg.Vector2(i) + (pg.Vector2(i) - pos).normalize() * 10000)
                    if i in points_on_illuminated_lines:
                        shadow.append(pg.Vector2(i))
                else:
                    if i in points_on_illuminated_lines:
                        shadow.append(pg.Vector2(i))
                    if i in points_on_non_illuminated_lines:
                        shadow.append(pg.Vector2(i) + (pg.Vector2(i) - pos).normalize() * 10000)
                if i in points_on_illuminated_lines and i in points_on_non_illuminated_lines:
                    in_shadow = not in_shadow
            
            done = False
            for a, b in (list(pairwise(shadow)) + [(shadow[len(shadow)-1], shadow[0])]):
                if a in points and b in points:
                    done = True
            if done:
                break 

        pg.draw.polygon(window, 0, shadow)


def main():
    window = pg.display.set_mode(flags=pg.FULLSCREEN)
    walls = [Polygon([pg.Vector2(100, 200), pg.Vector2(200, 300), pg.Vector2(200, 100), pg.Vector2(100, 100)])]

    player_pos = pg.Vector2(600, 600)
    player_dir = 0

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

        window.fill("#555555")
        player_light.fill(0)

        for wall in walls:
            wall.draw(window)

        pg.draw.circle(window, "#FFFF00", player_pos, 10)
        pg.draw.circle(player_light, "#FFFFFF", player_pos, 20)
        pg.draw.polygon(player_light, "#FFFFFF", tuple([player_pos] + [player_fwd.rotate(-45/2 + i/FOV_RES)*PLAYER_VIEW_DST + player_pos for i in range(FOV * FOV_RES)]))
        draw_shadows(player_light, walls, player_pos)

        window.blit(player_light, (0, 0), special_flags=pg.BLEND_MULT)

        pg.display.flip()
        ms = clock.tick()


if __name__ == "__main__":
    main()
