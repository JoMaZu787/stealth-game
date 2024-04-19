from abc import ABCMeta
from dataclasses import dataclass
import pygame as pg
from sys import exit


@dataclass
class EditorCamera:
    pos: pg.Vector2

    def transform(self, p: pg.Vector2, /):
        return p - self.pos
    
    def reverse_transform(self, p: pg.Vector2, /):
        return p + self.pos


class MapObject(metaclass=ABCMeta):
    pass


def main():
    window: pg.Surface = pg.display.set_mode(flags=pg.FULLSCREEN)
    clock = pg.time.Clock()
    ms = 1000//60

    while True:
        for event in pg.event.get():
            if event.type == pg.QUIT or event.type == pg.KEYDOWN and event.key == pg.K_ESCAPE:
                exit()
        
        window.fill("#555555")
        pg.draw.rect(window, "#FFFFFF", pg.Rect(20, 40, 40, 40))

        pg.display.flip()
        ms = clock.tick(60)


if __name__ == "__main__":
    main()
