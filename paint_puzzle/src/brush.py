# -*- coding: utf-8 -*-
"""Brush 画刷:横向(染行)/竖向(染列)的线选择器。

两种模式由 main.Game.mode 决定:
- 简单难度(easy):笔刷是中性"行/列选择器"(方向箭头),颜色由
  玩家在色板(main.Game.cur_color)中自选,点击即染成该色。
- 困难难度(hard):每支笔刷自带一个随机颜色(1..num_colors),
  点击染成笔刷自己的颜色,用后会随机换新颜色(闪白提示)。
"""
import random

import pygame

PRESS_DUR = 0.15   # 按压缩放动画时长(秒)
FLASH_DUR = 0.25   # 换色闪白时长(秒)

BRUSH_FILL = (208, 212, 220)   # 中性底色(简单模式)
BRUSH_EDGE = (70, 80, 96)
BRUSH_GLYPH = (98, 108, 124)   # 方向箭头颜色


class Brush:
    def __init__(self, orientation, index, rect, color=None, rng=None):
        """orientation: 'row' / 'col';index 行/列号;
        color: 困难模式的笔刷颜色索引(>=1),简单模式为 None。
        """
        self.orientation = orientation
        self.index = index
        self.rect = rect
        self.color = color
        self._rng = rng or random.Random()
        self._press_t = 0.0
        self._flash_t = 0.0

    def hit(self, pos):
        return self.rect.collidepoint(pos)

    def press(self):
        self._press_t = PRESS_DUR

    def flash(self):
        """换色闪白(困难模式使用后 / 提示设色时触发)。"""
        self._flash_t = FLASH_DUR

    def reroll(self, num_colors):
        """困难模式:使用后随机换一个与当前不同的颜色。"""
        choices = [c for c in range(1, num_colors + 1) if c != self.color]
        if choices:
            self.color = self._rng.choice(choices)
            self.flash()

    def update(self, dt):
        if self._press_t > 0:
            self._press_t = max(0.0, self._press_t - dt)
        if self._flash_t > 0:
            self._flash_t = max(0.0, self._flash_t - dt)

    def draw(self, surface, palette=None):
        """palette 非空且 self.color 非空 → 困难模式(彩色笔刷);
        否则 → 简单模式(中性底色 + 方向箭头)。"""
        rect = self.rect
        if self._press_t > 0:  # 按压时向中心缩小
            k = self._press_t / PRESS_DUR
            shrink = int(3 * k)
            rect = rect.inflate(-shrink * 2, -shrink * 2)
        colored = palette is not None and self.color is not None
        if colored:
            pygame.draw.rect(surface, palette[self.color], rect, border_radius=8)
            pygame.draw.rect(surface, BRUSH_EDGE, rect, 2, border_radius=8)
            if self._flash_t > 0:
                flash = pygame.Surface(rect.size, pygame.SRCALPHA)
                flash.fill((255, 255, 255, int(180 * self._flash_t / FLASH_DUR)))
                surface.blit(flash, rect.topleft)
        else:
            pygame.draw.rect(surface, BRUSH_FILL, rect, border_radius=8)
            pygame.draw.rect(surface, BRUSH_EDGE, rect, 2, border_radius=8)
            # 行刷(棋盘左侧)箭头向右;列刷(棋盘底部)箭头向下
            if self.orientation == "row":
                pts = [(rect.left + 9, rect.top + 9),
                       (rect.left + 9, rect.bottom - 9),
                       (rect.right - 7, rect.centery)]
            else:
                pts = [(rect.left + 9, rect.top + 9),
                       (rect.right - 9, rect.top + 9),
                       (rect.centerx, rect.bottom - 7)]
            pygame.draw.polygon(surface, BRUSH_GLYPH, pts)
