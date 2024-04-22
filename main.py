from __future__ import annotations
from itertools import pairwise
from math import copysign
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


def get_shadows(walls: list[Wall], pos: pg.Vector2, camera: Camera) -> list[list[pg.Vector2]]:
    shadows = []
    for wall in walls:
        lines = wall.transform_lines(camera)
        points = deque(wall.transform(camera))
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


class Wall:
    x: float
    y: float
    width: float
    height: float

    def __init__(self, x, y, width, height):
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.temp = None
        self.light_overlay = None
        self.temp_window = None

    def scale_by(self, x, y):
        return type(self)(self.x*x, self.y*y, self.width*x, self.height*y)

    @property
    def bottomleft(self):
        return self.x, self.y + self.height
    

    @property
    def bottomright(self):
        return self.x + self.width, self.y + self.height
    
    @property
    def topright(self):
        return self.x + self.width, self.y
    
    @property
    def topleft(self):
        return self.x, self.y

    @property
    def center(self):
        return pg.Vector2(self.x + self.width/2, self.y + self.height/2)

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

    def sdf(self, p: pg.Vector2):
        p = pg.Vector2(abs((p-self.center).x), abs((p-self.center).y))
        x_dist =  p.x - self.width/2
        y_dist =  p.y - self.height/2
        c_dist = p.distance_to(pg.Vector2(self.width, self.height)/2)
        return c_dist if x_dist > 0 and y_dist > 0 else max(x_dist, y_dist)

    def transform(self, camera: Camera):
        shorter_window_dimension: float = min(camera.window_size.x, camera.window_size.y)
        transformed = self.scale_by(shorter_window_dimension, shorter_window_dimension)
        points = transformed.points
        points = [camera.transform(i) for i in points]
        return points
    
    def transform_lines(self, camera: Camera):
        points = self.transform(camera)
        return list(pairwise(points)) + [(points[len(points)-1], points[0])]
    
    def draw(self, window: pg.Surface, camera: Camera, player: Player, walls: list[Wall]):
        shorter_window_dimension: float = min(camera.window_size.x, camera.window_size.y)
        transformed_pos, transformed_dir = player.transform(camera)
        if self.light_overlay is None:
            self.light_overlay = pg.Surface(window.get_size())
        if self.temp_window is None:
            self.temp_window = pg.Surface(window.get_size(), flags=pg.SRCALPHA)
        self.temp_window.fill(pg.Color(0, 0, 0, 0))
        self.light_overlay.fill(0)
        shadows_a, shadows_b = player.shadows_a.copy(), player.shadows_b.copy()
        shadows_a.remove(shadows_a[walls.index(self)])
        shadows_b.remove(shadows_b[walls.index(self)])

        light_a, light_b = player.pos*shorter_window_dimension + player.fwd.rotate(-45)*0.02*shorter_window_dimension, player.pos*shorter_window_dimension + player.fwd.rotate(45)*0.02*shorter_window_dimension
        transformed_pos, transformed_dir = player.transform(camera)
        light_a, light_b = camera.transform(light_a), camera.transform(light_b)
        dir_a, dir_b = transformed_dir - 2, transformed_dir + 2
        fwd_a, fwd_b = pg.Vector2(0, -1).rotate(dir_a), pg.Vector2(0, -1).rotate(dir_b)
        
        if self.temp is None:
            self.temp = pg.Surface(self.light_overlay.get_size())
        self.temp.fill(0)
        pg.draw.polygon(
            self.temp,
            "#888888",
            tuple(
                [light_a]
                +[fwd_a.rotate(-45/2 + i/FOV_RES)*PLAYER_VIEW_DST*shorter_window_dimension + light_a for i in range(FOV * FOV_RES)]
                )
            )
        for s in shadows_a:
            pg.draw.polygon(self.temp, 0, s)
        self.light_overlay.blit(self.temp, (0, 0), special_flags=pg.BLEND_ADD)
        
        self.temp.fill(0)
        pg.draw.polygon(
            self.temp,
            "#888888",
            tuple(
                [light_b]
                +[fwd_b.rotate(-45/2 + i/FOV_RES)*PLAYER_VIEW_DST*shorter_window_dimension + light_b for i in range(FOV * FOV_RES)]
                )
            )
        for s in shadows_b:
            pg.draw.polygon(self.temp, 0, s)
        self.light_overlay.blit(self.temp, (0, 0), special_flags=pg.BLEND_ADD)

        pg.draw.circle(self.light_overlay, "#888888", transformed_pos, 0.03*shorter_window_dimension)

        points = self.transform(camera)
        top_points = [(i-camera.window_size/2) * 1.2 + camera.window_size/2 for i in points]
        wall_polys = []
        poly_light_levels = []

        for poly in list(pairwise(zip(points, top_points))) + [(list(zip(points, top_points))[len(list(zip(points, top_points)))-1], list(zip(points, top_points))[0])]:
            vline_a, vline_b = poly
            a, b = vline_a
            c, d = vline_b

            og_normal = (c - a).normalize().rotate(90)
            center = (c + a)/2

            if og_normal.dot(center - transformed_pos) < 0:
                wall_polys.append((a, b, d, c))
                poly_light_levels.append(pg.math.clamp(og_normal.dot((transformed_pos - center).normalize()), 0, 1))

        for a, b in zip(wall_polys, poly_light_levels):
            col = pg.Color(int(b*200), int(b*200), int(b*200))
            pg.draw.polygon(self.temp_window, col, a)
        
        self.temp_window.blit(self.light_overlay, (0, 0), special_flags=pg.BLEND_MULT)
        window.blit(self.temp_window, (0, 0))


class Player:
    pos: pg.Vector2
    dir: float

    def __init__(self, pos: pg.Vector2 | tuple[float, float], dir: float):
        self.pos = pg.Vector2(pos)
        self.dir = dir
    
    @property
    def fwd(self):
        return pg.Vector2(0, -1).rotate(self.dir)
    
    def move(self, keys, walls, ms):
        player_motion = 0.0002 * ms * (keys[pg.K_w] - keys[pg.K_s])
        player_rot_motion = 0.1 * ms * (keys[pg.K_d] - keys[pg.K_a])
        prev_pos = self.pos.copy()
        self.pos += self.fwd * player_motion
        for wall in walls:
            if wall.sdf(self.pos) < 0.02:
                self.pos = prev_pos
        self.dir += player_rot_motion

    def transform(self, camera: Camera):
        shorter_window_dimension: float = min(camera.window_size.x, camera.window_size.y)
        return camera.transform(self.pos*shorter_window_dimension), self.dir - camera.rot
    
    def draw(self, window: pg.Surface, camera: Camera):
        shorter_window_dimension: float = min(camera.window_size.x, camera.window_size.y)
        transformed_pos, _ = self.transform(camera)
        pg.draw.circle(window, "#FFFF00", transformed_pos, 0.02*shorter_window_dimension)
    
    def draw_shadows(self, light_window: pg.Surface, walls: list[Wall], camera: Camera):
        shorter_window_dimension: float = min(camera.window_size.x, camera.window_size.y)
        light_a, light_b = self.pos*shorter_window_dimension + self.fwd.rotate(-45)*0.02*shorter_window_dimension, self.pos*shorter_window_dimension + self.fwd.rotate(45)*0.02*shorter_window_dimension
        transformed_pos, transformed_dir = self.transform(camera)
        light_a, light_b = camera.transform(light_a), camera.transform(light_b)
        dir_a, dir_b = transformed_dir - 2, transformed_dir + 2
        fwd_a, fwd_b = pg.Vector2(0, -1).rotate(dir_a), pg.Vector2(0, -1).rotate(dir_b)

        self.shadows_a = get_shadows(walls, light_a, camera)
        temp = pg.Surface(light_window.get_size())
        temp.fill(0)
        pg.draw.polygon(
            temp,
            "#888888",
            tuple(
                [light_a]
                +[fwd_a.rotate(-45/2 + i/FOV_RES)*PLAYER_VIEW_DST*shorter_window_dimension + light_a for i in range(FOV * FOV_RES)]
                )
            )
        for s in self.shadows_a:
            pg.draw.polygon(temp, 0, s)
        light_window.blit(temp, (0, 0), special_flags=pg.BLEND_ADD)
        
        self.shadows_b = get_shadows(walls, light_b, camera)
        temp.fill(0)
        pg.draw.polygon(
            temp,
            "#888888",
            tuple(
                [light_b]
                +[fwd_b.rotate(-45/2 + i/FOV_RES)*PLAYER_VIEW_DST*shorter_window_dimension + light_b for i in range(FOV * FOV_RES)]
                )
            )
        for s in self.shadows_b:
            pg.draw.polygon(temp, 0, s)
        light_window.blit(temp, (0, 0), special_flags=pg.BLEND_ADD)
        
        pg.draw.circle(light_window, "#888888", transformed_pos, 0.03*shorter_window_dimension)


def main():
    window = pg.display.set_mode(flags=pg.FULLSCREEN)
    walls = [Wall(0.1, 0.1, 0.1, 0.1)]

    player = Player(pg.Vector2(0.5, 0.5), 0)

    shorter_window_dimension: float = min(window.get_size()[0], window.get_size()[1])
    camera = Camera(player.pos*shorter_window_dimension, player.dir, window.get_size())

    player_light = pg.Surface(window.get_size())

    clock = pg.time.Clock()
    ms = 1
    while True:
        for event in pg.event.get():
            if event.type == pg.QUIT or event.type == pg.KEYDOWN and event.key == pg.K_ESCAPE:
                exit()
        
        keys = pg.key.get_pressed()
        player.move(keys, walls, ms)

        shorter_window_dimension: float = min(camera.window_size.x, camera.window_size.y)
        camera.pos = player.pos*shorter_window_dimension
        camera.rot = player.dir

        window.fill("#555555")
        player_light.fill(0)

        player.draw(window, camera)

        player.draw_shadows(player_light, walls, camera)
        window.blit(player_light, (0, 0), special_flags=pg.BLEND_MULT)

        for wall in walls:
            wall.draw(window, camera, player, walls)

        pg.display.flip()
        ms = clock.tick(60)


if __name__ == "__main__":
    main()
