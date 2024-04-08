import pygame as pg
from main import Ray, ray_line
from sys import exit

window = pg.display.set_mode(size=(800, 600))
a = pg.Vector2(-100, 100)
b = pg.Vector2(200, 300)
center = pg.Vector2(400, 300)
up = pg.Vector2(0, -1)
t = 0
ms = 1
clock = pg.time.Clock()
while True:
    for event in pg.event.get():
        if event.type == pg.QUIT:
            exit()
    t += 0.1 / (1000/60)
    t %= 1
    window.fill(0)

    pg.draw.circle(window, 0xFF0000, center, 2)
    pg.draw.line(window, 0xFFFFFF, a + center, b + center)
    pg.draw.circle(window, 0x00FF00, a.lerp(b, (-(b-a)*a)/a.distance_squared_to(b)) + center, 2)
    print((-(b-a)*a)/a.distance_squared_to(b))

    pg.display.flip()
    ms = clock.tick(60)