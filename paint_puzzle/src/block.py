# -*- coding: utf-8 -*-
"""Block 方块:逻辑颜色 + 渐变染色动画 + 绘制。"""
import os

import pygame

PIC_DIR = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "pic"))

_img_cache = {}


def _load_image(idx, size):
    """pic/block_N.png 存在则优先作为贴图,否则返回 None(回退纯色)。"""
    key = (idx, size)
    if key not in _img_cache:
        path = os.path.join(PIC_DIR, "block_%d.png" % idx)
        if os.path.isfile(path):
            try:
                img = pygame.image.load(path).convert_alpha()
                _img_cache[key] = pygame.transform.smoothscale(img, (size, size))
            except pygame.error:
                _img_cache[key] = None
        else:
            _img_cache[key] = None
    return _img_cache[key]


class Block:
    """棋盘上的一个方块。

    color 是逻辑颜色索引(0 = 空白),染色后立即生效;
    显示层通过 _anim 从旧颜色渐变到新颜色,支持错峰 delay。
    """

    def __init__(self, row, col, rect):
        self.row = row
        self.col = col
        self.rect = rect
        self.color = 0
        self._anim = None  # (delay, t, dur, from_rgb, to_rgb)

    @property
    def busy(self):
        return self._anim is not None

    def set_color(self, idx, delay=0.0, dur=0.2, palette=None):
        if idx == self.color and self._anim is None:
            return
        from_rgb = self.display_rgb(palette)
        to_rgb = palette[idx]
        self.color = idx
        self._anim = [delay, 0.0, dur, from_rgb, to_rgb]

    def display_rgb(self, palette):
        if self._anim is None:
            return palette[self.color]
        delay, t, dur, from_rgb, to_rgb = self._anim
        if delay > 0:
            return from_rgb
        p = min(1.0, t / dur) if dur > 0 else 1.0
        return tuple(int(a + (b - a) * p) for a, b in zip(from_rgb, to_rgb))

    def update(self, dt):
        if self._anim is None:
            return
        if self._anim[0] > 0:
            self._anim[0] -= dt
            return
        self._anim[1] += dt
        if self._anim[1] >= self._anim[2]:
            self._anim = None

    def draw(self, surface, palette, rect=None, rgb=None):
        rect = rect or self.rect
        rgb = rgb or self.display_rgb(palette)
        img = _load_image(self.color, rect.width)
        if img is not None:
            surface.blit(img, rect.topleft)
        else:
            surface.fill(rgb, rect)
        pygame.draw.rect(surface, (60, 60, 60), rect, 2)
