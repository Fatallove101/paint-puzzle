# -*- coding: utf-8 -*-
"""Brush 画刷:横向(染行)/竖向(染列)的"线选择器"。

颜色不属于画刷:玩家先在色板(main.Game 的 cur_color)选中颜色,
再点击画刷,即用该颜色染整行/整列。画刷只负责方向与按压反馈。
"""
import pygame

PRESS_DUR = 0.15   # 按压缩放动画时长(秒)

BRUSH_FILL = (208, 212, 220)   # 中性底色
BRUSH_EDGE = (70, 80, 96)
BRUSH_GLYPH = (98, 108, 124)   # 方向箭头


class Brush:
    def __init__(self, orientation, index, rect):
        """orientation: 'row' 或 'col';index 为行/列号。"""
        self.orientation = orientation
        self.index = index
        self.rect = rect
        self._press_t = 0.0

    def hit(self, pos):
        return self.rect.collidepoint(pos)

    def press(self):
        self._press_t = PRESS_DUR

    def update(self, dt):
        if self._press_t > 0:
            self._press_t = max(0.0, self._press_t - dt)

    def draw(self, surface):
        rect = self.rect
        if self._press_t > 0:  # 按压时向中心缩小
            k = self._press_t / PRESS_DUR
            shrink = int(3 * k)
            rect = rect.inflate(-shrink * 2, -shrink * 2)
        pygame.draw.rect(surface, BRUSH_FILL, rect, border_radius=8)
        pygame.draw.rect(surface, BRUSH_EDGE, rect, 2, border_radius=8)
        # 行刷(棋盘左侧)画向右箭头;列刷(棋盘底部)画向下箭头
        if self.orientation == "row":
            pts = [(rect.left + 9, rect.top + 9),
                   (rect.left + 9, rect.bottom - 9),
                   (rect.right - 7, rect.centery)]
        else:
            pts = [(rect.left + 9, rect.top + 9),
                   (rect.right - 9, rect.top + 9),
                   (rect.centerx, rect.bottom - 7)]
        pygame.draw.polygon(surface, BRUSH_GLYPH, pts)
