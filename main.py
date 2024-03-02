from __future__ import annotations

from math import ceil, sqrt, cos, radians, copysign
from typing import Literal
from enum import Enum
import pygame as pg


COLORS = (
            pg.Color("#FFFF00"),
            pg.Color("#0000FF"),
            pg.Color("#A020F0"),
            pg.Color("#FFA500"),
            pg.Color("#FF69B4"),
            pg.Color("#00FFFF"),
            pg.Color("#FF00FF"),
            pg.Color("#FF4533"),
            pg.Color("#33FF57"),
            pg.Color("#9370DB")
         )


def sign(x):
    if x == 0:
        return 1
    return copysign(1, x)


class Ray:
    origin: pg.Vector2
    dir: pg.Vector2

    def __init__(self, origin: pg.Vector2, dir_: pg.Vector2) -> None:
        self.origin = origin
        self.dir = dir_.normalize()


def ray_circle(ray: Ray, center: pg.Vector2, radius: float) -> float | Literal[-1]:
    origin = ray.origin - center
    
    b: float = 2*origin.dot(ray.dir)
    c: float = origin.length_squared() - radius**2

    discriminant: float = b**2 - 4*c
    if discriminant < 0:
        return -1
    else:
        t_pos = (-b+sqrt(discriminant))/2
        t_neg = (-b-sqrt(discriminant))/2
        return min(t_pos, t_neg)


def ray_line(ray: Ray, line: tuple[pg.Vector2, pg.Vector2],
             max_dist: float = float("Inf")):
    if (line[0] - ray.origin).dot(ray.dir) < 0 > (line[1] - ray.origin).dot(ray.dir):
        return -1
    temp = ray.dir.rotate(90)
    if sign((line[0] - ray.origin).dot(temp)) == sign((line[1] - ray.origin).dot(temp)) and (line[0] - ray.origin).dot(temp) != 0 and (line[1] - ray.origin).dot(temp) != 0:
        pass
    if line[0] == line[1]:
        return -1
    q = line[0].copy()
    s = (line[1] - q).copy()

    p = ray.origin.copy()
    r = ray.dir.copy().normalize()

    if s.cross(r) == 0:
        return -1
    u = (p - q).cross(r / (s.cross(r)))
    t = (q - p).cross(s / (r.cross(s)))

    if (0 > u or u > 1) or (t < 0 or max_dist < t):
        t = -1
    return t


def ray_rect(ray: Ray, rect: pg.Rect, max_dist: float = float("Inf")):
    temp = pg.Vector2(rect.center).distance_squared_to(pg.Vector2(rect.top_left))
    dot = (pg.Vector2(rect.center)-ray.origin).dot(ray.dir)
    if dot <= -temp:
        return -1
    lines = [(pg.Vector2(rect.bottomleft), pg.Vector2(rect.bottomright)),
             (pg.Vector2(rect.topleft), pg.Vector2(rect.topright)),
             (pg.Vector2(rect.topright), pg.Vector2(rect.bottomright)),
             (pg.Vector2(rect.topleft), pg.Vector2(rect.bottomleft))]
    dist = max_dist
    for i in lines:
        t = ray_line(ray, i, max_dist)
        if t == -1:
            continue
        dist = min(dist, t)
    if dist == float("Inf"):
        dist = -1
    return dist


def rect_sdf(rect: pg.Rect, pos: pg.Vector2):
    if rect.collidepoint(pos):
        return -min(
            abs(pos.x - rect.left),
            abs(pos.x - rect.right),
            abs(pos.y - rect.top),
            abs(pos.y - rect.bottom)
        )
    if rect.left < pos.x < rect.right:
        return min(
            abs(pos.y - rect.top),
            abs(pos.y - rect.bottom)
        )
    if rect.top < pos.y < rect.bottom:
        return min(
            abs(pos.x - rect.left),
            abs(pos.x - rect.right)
        )
    return sqrt(min(
        pos.distance_squared_to(rect.topleft),
        pos.distance_squared_to(rect.topright),
        pos.distance_squared_to(rect.bottomleft),
        pos.distance_squared_to(rect.bottomright)
    ))


def scene_sdf(walls, pos):
    t = float("Inf")
    for i in walls:
        t = min(t, rect_sdf(i.rect, pos))
    return t


def ray_scene(ray: Ray, walls, guards, max_distance: int = 1000):
    dst = float("Inf")
    for wall in walls:
        t = ray_rect(ray, wall.rect, max_distance)
        if t == -1:
            continue
        dst = min(dst, t)
    for guard in guards:
        t = ray_circle(ray, guard.pos, 5)
        if t == -1:
            continue
    if dst == float("Inf"):
        dst = -1
    return min(dst, max_distance)


class Button:
    def __init__(self, pos: pg.Vector2, id_: int, color: pg.Color | tuple[int, int, int] | None = None):
        if color is None:
            self.color = pg.Color(COLORS[id_])
        else:
            self.color = color
        self.pos = pos
        self.rect = pg.Rect(pos - pg.Vector2(10, 10), (20, 20))
        self.colored_rect = pg.Rect(pos - pg.Vector2(8, 8), (16, 16))
        self.inner_rect = pg.Rect(pos - pg.Vector2(6, 6), (12, 12))
        self.inner_inner_rect = pg.Rect(pos - pg.Vector2(4, 4), (8, 8))
        self.id = id_
        self.status = False
        self.used = False

    def update(self, player, keys):
        if player.pos.distance_squared_to(self.pos) <= 100:
            if not keys[pg.K_e] and self.used:
                self.status = not self.status
                self.used = False
            elif keys[pg.K_e]:
                self.used = True

    def draw(self, window, camera, camera_angle):
        pos = self.pos - (camera - pg.Vector2(window.get_size()) / 2 - pg.Vector2(0, 100).rotate(camera_angle))
        self.rect.center = pos
        self.colored_rect.center = pos
        self.inner_rect.center = pos
        self.inner_inner_rect.center = pos
        pg.draw.rect(window, (200, 200, 200), self.rect, border_radius=5)
        pg.draw.rect(window, (100, 255, 100) if self.status else (255, 100, 100), self.colored_rect, border_radius=3)
        pg.draw.rect(window, (100, 100, 100) if self.used else (200, 200, 200), self.inner_rect, border_radius=2)
        pg.draw.rect(window, self.color, self.inner_inner_rect, border_radius=2)

    def editor_draw(self, window: pg.Surface, camera: pg.Vector2):
        pos = self.pos*2 - camera + pg.Vector2(window.get_size()) / 2
        self.rect.center = pos
        self.colored_rect.center = pos
        self.inner_rect.center = pos
        self.inner_inner_rect.center = pos
        pg.draw.rect(window, (200, 200, 200), self.rect.scale_by(2), border_radius=10)
        pg.draw.rect(window, (100, 255, 100) if self.status else (255, 100, 100), self.colored_rect.scale_by(2), border_radius=6)
        pg.draw.rect(window, (100, 100, 100) if self.used else (200, 200, 200), self.inner_rect.scale_by(2), border_radius=4)
        pg.draw.rect(window, self.color, self.inner_inner_rect.scale_by(2), border_radius=4)


class Wall:
    rect: pg.Rect
    def __init__(self, rect):
        self.rect = rect

    def draw(self, window, cam_pos, cam_angle):
        cam_pos = cam_pos - pg.Vector2(window.get_size()) / 2 - pg.Vector2(0, 100).rotate(cam_angle)
        pg.draw.rect(window, (255, 255, 255), self.rect.move(-cam_pos.x, -cam_pos.y))

    def editor_rect(self, window, camera):
        rect = self.rect.copy()
        rect.center = pg.Vector2(rect.center)*2
        rect.scale_by_ip(2)
        rect.move_ip(-camera+pg.Vector2(window.get_size()) / 2)
        return rect

    def editor_draw(self, window, camera):
        pg.draw.rect(window, (200, 200, 200), self.editor_rect(window, camera))

    def collide_circle(self, circle: tuple[pg.Vector2, float]):
        return rect_sdf(self.rect, circle[0]) < circle[1]

    def update(self, buttons, delta, editor_override):
        pass


class Mode(Enum):
    PLAY = 0
    EDIT = 1


class DoorMovement(Enum):
    STATIC = 0
    OPENING = -1
    CLOSING = 1


class Door(Wall):
    def __init__(self, rect: pg.Rect, id_, horizontal: bool, flipped: bool,
                 color: pg.Color | tuple[int, int, int] = pg.Color(200, 200, 200)):
        super().__init__(rect)
        self.pos = pg.Vector2(rect.x, rect.y)
        self.color = pg.Color(color)
        self.size = rect.size
        self.door_position = 1.0
        self.ID = id_
        self.horizontal = horizontal
        self.flipped = flipped
        self.movement = DoorMovement.STATIC

    def update(self, buttons: list[Button], delta: int, editor_override: list[bool]):
        if self.movement == DoorMovement.CLOSING:
            self.door_position += delta / 1000
            if self.door_position >= 1:
                self.door_position = 1
                self.movement = DoorMovement.STATIC
        elif self.movement == DoorMovement.OPENING:
            self.door_position -= delta / 1000
            if self.door_position <= 0:
                self.door_position = 0
                self.movement = DoorMovement.STATIC

        if self.horizontal:
            self.rect.width = self.size[0] * self.door_position
            if self.flipped:
                self.rect.x = self.pos.x + self.size[0] * (1-self.door_position)
                self.rect.width += 2
        else:
            self.rect.height = self.size[1] * self.door_position
            if self.flipped:
                self.rect.y = self.pos.y + self.size[1] * (1-self.door_position)
                self.rect.height += 2

        t: list[Button] = []
        for i in buttons:
            if i.id == self.ID:
                t.append(i)
                override: bool = editor_override[i.id]
        for i in t:
            if not (i.status or override):
                break
        else:
            if self.movement != DoorMovement.OPENING and self.door_position != 0:
                self.movement = DoorMovement.OPENING
            return
        if self.movement != DoorMovement.CLOSING and self.door_position != 1:
            self.movement = DoorMovement.CLOSING
    
    def editor_draw(self, window, camera):
        super().editor_draw(window, camera)
        rect = self.editor_rect(window, camera)
        points = [
            pg.Vector2(rect.right if self.flipped else rect.left, rect.top if self.flipped else rect.bottom),
            pg.Vector2(rect.left if (self.flipped != self.horizontal) else rect.right, rect.top if (self.flipped != self.horizontal) else rect.bottom)
        ]
        points.append(points[0].lerp(points[1], 0.5) + pg.Vector2(-1 if self.horizontal else 0, 0 if self.horizontal else -1) * (-1 if self.flipped else 1) * 5)
        pg.draw.polygon(window, COLORS[self.ID], tuple(points))


class Player:
    shape: list[pg.Vector2] = [
        pg.Vector2(0, -5),
        pg.Vector2(-4, 4),
        pg.Vector2(0, 2),
        pg.Vector2(4, 4)
    ]

    def __init__(self, pos, speed, xray):
        self.pos = pos
        self.speed = speed
        self.dir = pg.Vector2(0, -1)
        self.xray = xray
        self.moved = False
        self.distances = None

    def update(self, keys, walls, delta):

        # dir_ = pg.Vector2(0, 0)
        # dir_.x -= keys[pg.K_a]
        # dir_.x += keys[pg.K_d]
        # dir_.y -= keys[pg.K_w]
        # dir_.y += keys[pg.K_s]
        # self.dir.rotate_ip(keys[pg.K_RIGHT] * delta / 10)
        # self.dir.rotate_ip(-keys[pg.K_LEFT] * delta / 10)

        # if dir_.length() > 0:
        #     dir_.scale_to_length(self.speed * (delta * 30 / 1000))

        self.dir.rotate_ip(keys[pg.K_d] * delta / 20)
        self.dir.rotate_ip(-keys[pg.K_a] * delta / 20)

        dir_ = self.dir * (keys[pg.K_w] - keys[pg.K_s]) * self.speed * (delta * 30 / 1000)

        self.pos.x += dir_.x

        self.moved = False
        if keys[pg.K_d] != keys[pg.K_a] or keys[pg.K_w] != keys[pg.K_s]:
            self.moved = True

        for i in walls:
            while i.collide_circle((self.pos, 5)):
                self.pos.x -= sign(dir_.x)

        self.pos.y += dir_.y

        for i in walls:
            while i.collide_circle((self.pos, 5)):
                self.pos.y -= sign(dir_.y)

    def draw(self, window, cam_pos, overlay, walls: list[Wall], guards: list[Guard], cam_angle, door_changed):
        cam_pos = cam_pos - pg.Vector2(window.get_size()) / 2 - pg.Vector2(0, 100).rotate(cam_angle)
        transformed_pos = self.pos - cam_pos
        pg.draw.polygon(
            window,
            (100, 255, 100), tuple(transformed_pos + i.rotate(pg.Vector2(0, -1).angle_to(self.dir)) for i in self.shape)
        )
        arc_a = self.dir.rotate(-45 / 2)
        rays = [Ray(self.pos, arc_a.rotate(i)) for i in range(45)]
        if self.xray:
            self.distances = [300 for _ in range(45)]
        elif self.moved or door_changed or self.distances is None:
            self.distances = [ray_scene(ray, walls, guards, 300) for ray in rays]
        points = [transformed_pos] + [transformed_pos + arc_a.rotate(i) * j for i, j in enumerate(self.distances)]
        pg.draw.polygon(overlay, (100, 255, 100), points)
        pg.draw.circle(overlay, (100, 255, 100), transformed_pos, 10)
    
    def editor_draw(self, window, cam_pos):
        cam_pos = cam_pos - pg.Vector2(window.get_size()) / 2
        transformed_pos = self.pos*2 - cam_pos
        pg.draw.polygon(
            window,
            (255, 255, 100),
            tuple(transformed_pos + (i*2).rotate(pg.Vector2(0, -1).angle_to(self.dir)) for i in self.shape)
        )


class Guard:
    def __init__(self, pos, dir_, rotate_frames):
        self.pos = pos
        self.dir = dir_.normalize()
        self.start_dir = self.dir.copy()
        self.rotate_frames = rotate_frames
        self.timer = 0
        self.sees_player = False
        self.bounds = pg.Rect(0, 0, 300, 300)
        self.bounds.center = pos
        self.distances = None
        self.editor_distances = None

    def update(self, player, walls, guards, delta):
        self.bounds.center = self.pos
        self.timer += delta
        if self.timer >= self.rotate_frames:
            if self.rotate_frames != 0:
                self.dir.rotate_ip(2)
            self.timer = 0

        dif = player.pos - self.pos
        dist = dif.length()
        dif.normalize_ip()

        self.sees_player = (
                (self.dir * dif >= cos(radians(45 / 2))
                 and 150 >= dist == ray_scene(Ray(self.pos, dif), walls, guards, max_distance=dist))
                or dist <= 10
        )
        return self.sees_player

    def draw(self, window, light_overlay, walls, guards, cam_pos, cam_angle, door_changed):
        pos = self.pos - (cam_pos - pg.Vector2(window.get_size()) / 2 - pg.Vector2(0, 100).rotate(cam_angle))
        arc_a = self.dir.rotate(-45 / 2)
        rays = [Ray(self.pos, arc_a.rotate(i)) for i in range(0, 45, 2)]
        if self.rotate_frames != 0 or self.distances is None or door_changed:
            self.distances = [ray_scene(ray, walls, guards, 150) for ray in rays]
        points = [pos] + [pos + arc_a.rotate(j) * self.distances[i] for i, j in enumerate(range(0, 45, 2))]
        pg.draw.polygon(light_overlay, pg.Color(255, 255, 255), points)
        pg.draw.circle(window, (255, 100, 100), pos, 5)
        pg.draw.circle(light_overlay, (255, 255, 255), pos, 10)
    
    def editor_draw(self, window, overlay, camera, walls, guards):
        pos = self.pos*2-camera+pg.Vector2(window.get_size())/2
        pg.draw.circle(window, (255, 100, 100), pos, 10)
        arc_a = self.dir.rotate(-45/2)
        if self.rotate_frames == 0:
            if self.distances is None:
                rays = [Ray(self.pos, arc_a.rotate(i)) for i in range(0, 45, 2)]
                self.distances = [ray_scene(ray, walls, guards, 150) for ray in rays]
            points = [pos] + [pos + arc_a.rotate(j) * self.distances[i]*2 for i, j in enumerate(range(0, 45, 2))]
            pg.draw.polygon(overlay, (255, 255, 255, 100), points)
        else:
            if self.editor_distances is None:
                rays = [Ray(self.pos, self.dir.rotate(i)) for i in range(0, 359)]
                self.editor_distances = [ray_scene(ray, walls, guards, 150) for ray in rays]
            points = [pos + self.dir.rotate(j) * self.editor_distances[i]*2 for i, j in enumerate(range(0, 359))]
            pg.draw.polygon(overlay, (255, 255, 255, 100), points)
        pg.draw.circle(overlay, (255, 255, 255, 100), pos, 20)


class Level:
    player: Player
    guards: list[Guard]
    walls: list[Wall]
    buttons: list[Button]
    camera: pg.Vector2
    camera_angle: float
    camera_rect:pg.Rect
    editor_override: list[bool]
    def __init__(self, player_pos, player_speed,window_size: pg.Vector2 | tuple[int, int]):
        self.player = Player(player_pos, player_speed, False)
        self.camera = self.player.pos.copy()
        self.camera_angle = 0.0
        self.camera_rect= pg.Rect((0, 0), window_size)
        self.editor_override = [False for _ in range(10)]

    def update(self, keys, delta):
        self.player.update(keys, self.walls, delta)
        self.camera_rect.center = self.camera.copy()

        heading = self.player.pos - self.camera
        self.camera += heading * 0.05

        for i in self.buttons:
            i.update(self.player, keys)

        for wall in self.walls:
            wall.update(self.buttons, delta, self.editor_override)

        camera_angle_diff = (-self.player.dir.angle_to(pg.Vector2(0, -1))) - self.camera_angle
        if abs(camera_angle_diff) > 300:
            camera_angle_diff += 360
        self.camera_angle += camera_angle_diff * 0.5

        if self.camera_angle > 360:
            self.camera_angle -= 360

        for guard in self.guards:
            self.seen = guard.update(self.player, self.walls, self.guards, delta) or self.seen


def main():
    os_window = pg.display.set_mode(flags=pg.FULLSCREEN)
    scale_factor: int = 2
    diagonal = ceil((pg.Vector2(os_window.get_size()) / 2).length())
    window = pg.Surface((diagonal, diagonal))
    guard_light_overlay = pg.Surface(window.get_size())
    low_res_guard_overlay = pg.Surface(pg.Vector2(window.get_size()) / 2)
    blurred_guard_light_overlay = pg.Surface(window.get_size())

    player_light_overlay = pg.Surface(window.get_size())
    low_res_player_overlay = pg.Surface(pg.Vector2(window.get_size()) / 2)
    blurred_player_light_overlay = pg.Surface(window.get_size())

    mode: Mode = Mode.EDIT

    clock = pg.time.Clock()
    pg.font.init()
    font = pg.font.SysFont("Arial", 12)

    walls: list[Wall] = [Wall(pg.Rect(140, 200, 400, 20)), Wall(pg.Rect(340, 240, 20, 100)), Wall(pg.Rect(440, 240, 20, 100)), Wall(pg.Rect(340, 320, 100, 20)),
             Door(pg.Rect(345, 220, 10, 20), 0, False, True), Door(pg.Rect(445, 220, 10, 20), 1, False, True)]
    guards = [Guard(pg.Vector2(300, 300), pg.Vector2(0, -1), 8), Guard(pg.Vector2(550, 180), pg.Vector2(0, 1), 0)]
    buttons = [Button(pg.Vector2(150, 230), 1), Button(pg.Vector2(370, 310), 0)]
    player = Player(pg.Vector2(10, 10), 3, False)

    camera: pg.Vector2 = player.pos.copy()
    camera_angle: float = 0.0
    camera_rect: pg.Rect = pg.Rect((0, 0), window.get_size())
    ms = 1

    editor_camera: pg.Vector2 = pg.Vector2(0, 0)
    grid_square_overlay = pg.Surface((40, 40), pg.SRCALPHA)
    grid_square_overlay.fill((255, 255, 255, 100))
    pg.draw.rect(grid_square_overlay, (255, 255, 255, 255), grid_square_overlay.get_rect(), 2)
    
    editor_override: list[bool] = [False for _ in range(10)]
    editor_guard_overlay: pg.Surface = pg.Surface(os_window.get_size(), flags=pg.SRCALPHA)

    while True:
        events = pg.event.get()
        for event in events:
            if event.type == pg.QUIT or event.type == pg.KEYDOWN and event.key == pg.K_ESCAPE:
                pg.quit()
                return
        if mode == Mode.PLAY:
            for event in events:
                if event.type == pg.KEYDOWN and event.key == pg.K_m:
                    mode = Mode.EDIT
                    editor_camera = player.pos.copy()
                    pg.mouse.set_visible(True)

            camera_rect.center = camera
            keys = pg.key.get_pressed()

            player.update(keys, walls, ms)

            for i in buttons:
                i.update(player, keys)

            for wall in walls:
                wall.update(buttons, ms, editor_override)

            door_changed = False
            for i in walls:
                if isinstance(i, Door) and i.movement != DoorMovement.STATIC:
                    door_changed = True

            heading = player.pos - camera
            camera += heading * 0.1

            camera_angle_diff = (-player.dir.angle_to(pg.Vector2(0, -1))) - camera_angle
            if abs(camera_angle_diff) > 300:
                camera_angle_diff += 360
            camera_angle += camera_angle_diff * 0.5

            if camera_angle > 360:
                camera_angle -= 360

            window.fill((75, 75, 75))
            guard_light_overlay.fill((100, 100, 100))
            player_light_overlay.fill(0)

            for wall in walls:
                wall.draw(window, camera, camera_angle)

            for i in buttons:
                i.draw(window, camera, camera_angle)

            seen = False
            for guard in guards:
                seen = guard.update(player, walls, guards, ms) or seen
                if camera_rect.colliderect(guard.bounds):
                    guard.draw(window, guard_light_overlay, walls, guards, camera, camera_angle, door_changed)

            player.draw(window, camera, player_light_overlay, walls, guards, camera_angle, door_changed)
            pg.transform.smoothscale_by(guard_light_overlay, 0.5, dest_surface=low_res_guard_overlay)
            pg.transform.smoothscale(low_res_guard_overlay, blurred_guard_light_overlay.get_size(),
                                     dest_surface=blurred_guard_light_overlay)

            pg.transform.smoothscale_by(player_light_overlay, 0.5, dest_surface=low_res_player_overlay)
            pg.transform.smoothscale(low_res_player_overlay, blurred_guard_light_overlay.get_size(),
                                     dest_surface=blurred_player_light_overlay)

            window.blit(blurred_guard_light_overlay, (0, 0), special_flags=pg.BLEND_MULT)
            window.blit(blurred_player_light_overlay, (0, 0), special_flags=pg.BLEND_MULT)

            os_window.fill((255, 0, 255))

            rotated_window = pg.transform.rotate(window, camera_angle)
            rotated_window_rect = pg.Rect((0, 0), pg.Vector2(os_window.get_size()) / 2)
            rotated_window_rect.center = pg.Vector2(rotated_window.get_size()) / 2
            pg.transform.scale_by(rotated_window.subsurface(rotated_window_rect), scale_factor, dest_surface=os_window)
            if seen:
                os_window.blit(font.render("spotted!", False, (255, 255, 255)), (0, 0))
            os_window.blit(font.render("[M]: Edit Level", False, (255, 255, 255)), (0, 12))
        elif mode == Mode.EDIT:
            for event in events:
                if event.type == pg.KEYDOWN:
                    if event.key == pg.K_m:
                        mode = Mode.PLAY
                        editor_override = [False for _ in range(10)]
                        pg.mouse.set_visible(False)
                    elif 47 < event.key < 58:
                        pressed_number = event.key - 48
                        pressed_number -= 1
                        pressed_number %= 10
                        editor_override[pressed_number] = not editor_override[pressed_number]
            os_window.fill((50, 50, 50))
            editor_guard_overlay.fill((0, 0, 0, 0))

            keys = pg.key.get_pressed()
            editor_camera.x += keys[pg.K_d] - keys[pg.K_a]
            editor_camera.y += keys[pg.K_s] - keys[pg.K_w]

            mouse_pos = pg.Vector2(pg.mouse.get_pos()) - pg.Vector2(os_window.get_size())/2 + editor_camera
            hovered_grid_square = mouse_pos // 40

            os_window.blit(font.render(str(hovered_grid_square), False, (255, 255, 255)), (0, 0))

            for wall in walls:
                wall.update(buttons, ms, editor_override)
                wall.editor_draw(os_window, editor_camera)

            for button in buttons:
                button.editor_draw(os_window, editor_camera)

            for guard in guards:
                guard.editor_draw(os_window, editor_guard_overlay, editor_camera, walls, guards)

            player.editor_draw(os_window, editor_camera)

            os_window.blit(
                grid_square_overlay,
                (hovered_grid_square*40 - editor_camera + pg.Vector2(os_window.get_size())/2)
            )

            for i, j in enumerate(editor_override):
                color = COLORS[i]
                color = color.lerp(pg.Color(0), 0 if j else 0.5)
                pg.draw.rect(os_window, color, pg.Rect(i * 14 + 2, os_window.get_height() - 14, 12, 12))
                pg.draw.rect(os_window, 0xFFFFFF, pg.Rect(
                    i * 14,
                    os_window.get_height() - 16,
                    16,
                    16
                ), 2)
            
            os_window.blit(editor_guard_overlay, (0, 0))
            
        pg.display.flip()
        ms = clock.tick()


if __name__ == "__main__":
    main()
