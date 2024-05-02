from __future__ import annotations
from itertools import pairwise
from math import copysign
from typing import Any
import pygame as pg
from sys import exit
from collections import deque
from config import *
from enum import Enum
pg.font.init()
font = pg.font.SysFont("Arial", 24)
UP = pg.Vector2(0, -1)


class Mode(Enum):
    PLAY = 0
    EDIT = 1


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
        self.shorter_dimension = min(self.window_size)

    @property
    def fwd(self):
        return UP.rotate(self.rot)
    
    def transform(self, p: pg.Vector2, /):
        return (p - self.pos).rotate(-self.rot) + self.window_size/2
    
    def reverse_transform(self, p: pg.Vector2, /):
        return p.rotate(self.rot) + self.pos - self.window_size/2
    

class EditorCamera:
    pos: pg.Vector2
    scale: float

    def __init__(self, pos: tuple[float, float] | pg.Vector2, scale: float, window_size: pg.Vector2 | tuple[float, float]):
        self.pos = pg.Vector2(pos)
        self.scale = scale
        self.window_size = pg.Vector2(window_size)
        self.shorter_dimension = min(self.window_size)

    def transform(self, p: pg.Vector2 | float):
        if isinstance(p, pg.Vector2):
            p = p - self.pos
            p *= self.scale*self.shorter_dimension
            return p + self.window_size/2
        else:
            return p*self.scale*self.shorter_dimension


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
    
    def editor_draw(self, window: pg.surface, camera: EditorCamera):
        pg.draw.polygon(window, "#FFFFFF", [camera.transform(p) for p in self.points])

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

        light_a, light_b = player.pos*shorter_window_dimension + camera.fwd.rotate(-45)*0.02*shorter_window_dimension, player.pos*shorter_window_dimension + camera.fwd.rotate(45)*0.02*shorter_window_dimension
        transformed_pos, transformed_dir = player.transform(camera)
        light_a, light_b = camera.transform(light_a), camera.transform(light_b)
        dir_a, dir_b = transformed_dir - 2, transformed_dir + 2
        fwd_a, fwd_b = UP.rotate(dir_a), UP.rotate(dir_b)
        
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

        points = [camera.transform((i+camera.fwd*0.125)*shorter_window_dimension) for i in self.points]
        top_points = [(i-camera.window_size/2) * 1.2 + camera.window_size/2 for i in points]
        
        points = [i - UP*0.125*shorter_window_dimension for i in points]
        top_points = [i - UP*0.125*shorter_window_dimension for i in top_points]

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


class Guard:
    pos: pg.Vector2
    dir: float
    rotate_speed: float
    view_dst: float
    fov: float

    def __init__(self, pos: pg.Vector2 | tuple[float, float], dir_: float, rotate_speed: float, view_dst: float, fov: float):
        self.pos = pg.Vector2(pos)
        self.dir = dir_
        self.rotate_speed = rotate_speed
        self.view_dst = view_dst
        self.fov = fov

    @property
    def fwd(self):
        return UP.rotate(self.dir)
    
    def update(self, ms: float):
        self.dir += self.rotate_speed*(ms/1000)

    def transform(self, camera: Camera):
        return camera.transform(self.pos*camera.shorter_dimension), self.dir - camera.rot

    def draw(self, window: pg.Surface, camera: Camera):
        transformed_pos, _ = self.transform(camera)
        pg.draw.circle(window, "#FF0000", transformed_pos, 0.01*camera.shorter_dimension)

    def draw_shadows(self, light_window: pg.Surface, walls: list[Wall], camera: Camera):
        transformed_pos, transformed_dir = self.transform(camera)
        fwd = UP.rotate(transformed_dir)

        self.shadows = get_shadows(walls, transformed_pos, camera)
        temp = pg.Surface(light_window.get_size())
        temp.fill(0)
        pg.draw.polygon(
            temp,
            "#888888",
            tuple(
                [transformed_pos]
                +[fwd.rotate(-self.fov/2 + i/FOV_RES)*self.view_dst*camera.shorter_dimension + transformed_pos for i in range(self.fov * FOV_RES)]
                )
            )
        pg.draw.circle(temp, "#888888", transformed_pos, 0.02*camera.shorter_dimension)
        for s in self.shadows:
            pg.draw.polygon(temp, 0, s)
        light_window.blit(temp, (0, 0), special_flags=pg.BLEND_ADD)
    
    def editor_light(self, light_window: pg.Surface, camera: EditorCamera):
        transformed_pos = camera.transform(self.pos)
        temp = pg.Surface(light_window.get_size())
        temp.fill(0)
        pg.draw.polygon(
            temp,
            "#222222",
            tuple(
                [transformed_pos]
                +[self.fwd.rotate(-self.fov/2 + i/FOV_RES)*camera.transform(self.view_dst) + transformed_pos for i in range(self.fov * FOV_RES)]
                )
            )
        pg.draw.circle(temp, "#222222", transformed_pos, camera.transform(0.02))
        light_window.blit(temp, (0, 0), special_flags=pg.BLEND_ADD)
    
    def editor_draw(self, window: pg.surface, camera: EditorCamera):
        pg.draw.circle(window, '#FF0000', camera.transform(self.pos), camera.transform(0.01))
        pg.draw.arc(window, ())


class Player:
    pos: pg.Vector2
    dir: float

    def __init__(self, pos: pg.Vector2 | tuple[float, float], dir: float):
        self.pos = pg.Vector2(pos)
        self.dir = dir
    
    @property
    def fwd(self):
        return UP.rotate(self.dir)
    
    def move(self, keys, walls, ms):
        player_motion = 0.0002 * ms * (keys[pg.K_w] - keys[pg.K_s])
        player_rot_motion = 0.1 * ms * (keys[pg.K_d] - keys[pg.K_a])
        for _ in range(PLAYER_STEPS):
            motion_vec = self.fwd * player_motion / PLAYER_STEPS
            for wall in walls:
                if wall.sdf(self.pos + pg.Vector2(motion_vec.x, 0)) < 0.02:
                    motion_vec.x = 0
                if wall.sdf(self.pos + pg.Vector2(0, motion_vec.y)) < 0.02:
                    motion_vec.y = 0
            self.pos += motion_vec
            self.dir += player_rot_motion / PLAYER_STEPS

    def transform(self, camera: Camera):
        return camera.transform(self.pos*camera.shorter_dimension), self.dir - camera.rot
    
    def draw(self, window: pg.Surface, camera: Camera):
        transformed_pos, _ = self.transform(camera)
        pg.draw.circle(window, "#FFFF00", transformed_pos, 0.02*camera.shorter_dimension)

    def editor_draw(self, window: pg.surface, camera: EditorCamera):
        pg.draw.circle(window, '#FFFF00', camera.transform(self.pos), camera.transform(0.02))
    
    def editor_light(self, window: pg.surface, camera: EditorCamera):
        light_a, light_b = self.pos + self.fwd.rotate(-45)*0.02, self.pos + self.fwd.rotate(45)*0.02
        light_a, light_b = camera.transform(light_a), camera.transform(light_b)
        dir_a, dir_b = self.dir - 2, self.dir + 2
        fwd_a, fwd_b = UP.rotate(dir_a), UP.rotate(dir_b)

        pos = camera.transform(self.pos)
        temp = pg.Surface(window.get_size())
        temp.fill(0)
        pg.draw.polygon(
            temp,
            "#222222",
            tuple(
                [light_a]
                +[fwd_a.rotate(-FOV/2 + i/FOV_RES)*camera.transform(PLAYER_VIEW_DST) + light_a for i in range(FOV * FOV_RES)]
                )
            )
        window.blit(temp, (0, 0), special_flags=pg.BLEND_ADD)
        
        temp.fill(0)
        pg.draw.polygon(
            temp,
            "#222222",
            tuple(
                [light_b]
                +[fwd_b.rotate(-FOV/2 + i/FOV_RES)*camera.transform(PLAYER_VIEW_DST) + light_b for i in range(FOV * FOV_RES)]
                )
            )
        window.blit(temp, (0, 0), special_flags=pg.BLEND_ADD)

        pg.draw.circle(window, "#222222", pos, camera.transform(0.03))
    
    def draw_shadows(self, light_window: pg.Surface, walls: list[Wall], camera: Camera):
        light_a, light_b = self.pos*camera.shorter_dimension + self.fwd.rotate(-45)*0.02*camera.shorter_dimension, self.pos*camera.shorter_dimension + self.fwd.rotate(45)*0.02*camera.shorter_dimension
        transformed_pos, transformed_dir = self.transform(camera)
        light_a, light_b = camera.transform(light_a), camera.transform(light_b)
        dir_a, dir_b = transformed_dir - 2, transformed_dir + 2
        fwd_a, fwd_b = UP.rotate(dir_a), UP.rotate(dir_b)

        self.shadows_a = get_shadows(walls, light_a, camera)
        temp = pg.Surface(light_window.get_size())
        temp.fill(0)
        pg.draw.polygon(
            temp,
            "#888888",
            tuple(
                [light_a]
                +[fwd_a.rotate(-FOV/2 + i/FOV_RES)*PLAYER_VIEW_DST*camera.shorter_dimension + light_a for i in range(FOV * FOV_RES)]
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
                +[fwd_b.rotate(-FOV/2 + i/FOV_RES)*PLAYER_VIEW_DST*camera.shorter_dimension + light_b for i in range(FOV * FOV_RES)]
                )
            )
        for s in self.shadows_b:
            pg.draw.polygon(temp, 0, s)
        light_window.blit(temp, (0, 0), special_flags=pg.BLEND_ADD)
        
        pg.draw.circle(light_window, "#888888", transformed_pos, 0.03*camera.shorter_dimension)


def main():
    global global_timer_ms

    window = pg.display.set_mode(flags=pg.FULLSCREEN, vsync=1)
    window_size = window.get_size()
    mode = Mode.EDIT

    walls = [Wall(0.1, 0.1, 0.1, 0.1), Wall(1, 1.1, 0.1, 0.1)]
    guards = [Guard(pg.Vector2(1, 1), 180.0, 10, 0.4, 20)]

    player = Player(pg.Vector2(0.5, 0.5), 0)

    shorter_window_dimension: float = min(window_size)
    camera = Camera(player.pos*shorter_window_dimension + 0.125*shorter_window_dimension*player.fwd, player.dir, window_size)
    editor_camera = EditorCamera(player.pos, 1,window_size)

    player_light = pg.Surface(window_size)
    guards_light = pg.Surface(window_size)
    temp_guards_light = pg.Surface(window_size)
    editor_light = pg.Surface(window_size)

    clock = pg.time.Clock()
    ms = 1

    pg.event.set_allowed((pg.QUIT, pg.KEYDOWN, pg.MOUSEWHEEL))
    while True:
        for event in pg.event.get():
            if event.type == pg.QUIT or event.type == pg.KEYDOWN and event.key == pg.K_ESCAPE:
                exit()
            elif event.type == pg.KEYDOWN:
                if event.key == pg.K_m:
                    if mode == Mode.EDIT:
                        mode = Mode.PLAY
                    elif mode == Mode.PLAY:
                        mode = Mode.EDIT
            elif event.type == pg.MOUSEWHEEL and mode == Mode.EDIT:
                if event.y > 0:
                    editor_camera.scale *= 1 + abs(event.y) * 0.1
                else:
                    editor_camera.scale /= 1 + abs(event.y) * 0.1
                editor_camera.scale = pg.math.clamp(editor_camera.scale, 0.5, 5)
        
        keys = pg.key.get_pressed()
        if mode == Mode.PLAY:
            player.move(keys, walls, ms)
            for guard in guards:
                guard.update(ms)

            pos_d = (player.pos*camera.shorter_dimension + 0.125*camera.shorter_dimension*player.fwd) - camera.pos
            rot_d = player.dir - camera.rot
            camera.pos += pos_d * 0.5
            camera.rot += rot_d * 0.75

            window.fill("#555555")
            player_light.fill(0)
            guards_light.fill((200, 200, 200))

            player.draw(window, camera)

            for guard in guards:
                guard.draw(window, camera)

            for guard in guards:
                temp_guards_light.fill(0)
                guard.draw_shadows(temp_guards_light, walls, camera)
                guards_light.blit(temp_guards_light, (0, 0), special_flags=pg.BLEND_ADD)
            window.blit(guards_light, (0, 0), special_flags=pg.BLEND_MULT)

            player.draw_shadows(player_light, walls, camera)
            window.blit(player_light, (0, 0), special_flags=pg.BLEND_MULT)

            for wall in walls:
                wall.draw(window, camera, player, walls)
        elif mode == Mode.EDIT:
            editor_camera.pos += pg.Vector2((keys[pg.K_d] - keys[pg.K_a]) * (ms/2000), (keys[pg.K_s] - keys[pg.K_w]) * (ms/2000)) / editor_camera.scale

            window.fill('#555555')
            editor_light.fill(0)
            player.editor_draw(window, editor_camera)
            player.editor_light(editor_light, editor_camera)
            for wall in walls:
                wall.editor_draw(window, editor_camera)
            for guard in guards:
                guard.update(ms)
                guard.editor_draw(window, editor_camera)
                guard.editor_light(editor_light, editor_camera)
            window.blit(editor_light, (0, 0), special_flags=pg.BLEND_ADD)

        pg.display.flip()
        ms = clock.tick()


if __name__ == "__main__":
    main()
