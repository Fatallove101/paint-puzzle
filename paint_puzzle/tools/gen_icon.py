# -*- coding: utf-8 -*-
"""生成游戏图标 icon.ico(纯 pygame 绘制 + 标准库 ICO 封装,无需 Pillow)。

用法: python tools/gen_icon.py
生成 paint_puzzle/icon.ico(256x256),同时用作 exe 图标与游戏窗口图标。
"""
import os
import struct

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame  # noqa: E402

ROOT = os.path.normpath(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))))
ICO = os.path.join(ROOT, "icon.ico")
SIZE = 256

# 2x2 色块用色(取自游戏色板:红/蓝/黄/绿)
COLORS = [(230, 55, 60), (35, 100, 235), (255, 213, 0), (45, 165, 65)]


def make_surface():
    surf = pygame.Surface((SIZE, SIZE), pygame.SRCALPHA)
    # 深色圆角底板
    pygame.draw.rect(surf, (36, 40, 52, 255), (0, 0, SIZE, SIZE),
                     border_radius=44)
    # 2x2 游戏色块
    margin, gap = 26, 12
    cell = (SIZE - 2 * margin - gap) // 2
    for i, rgb in enumerate(COLORS):
        r, c = i // 2, i % 2
        x = margin + c * (cell + gap)
        y = margin + r * (cell + gap)
        pygame.draw.rect(surf, rgb + (255,), (x, y, cell, cell),
                         border_radius=16)
    return surf


def build_ico(png_path):
    with open(png_path, "rb") as f:
        png = f.read()
    # ICO 容器:文件头(0 保留,type=1,数量 1)+ 单条目(尺寸 256 记为 0,PNG 数据)
    header = struct.pack("<HHH", 0, 1, 1)
    entry = struct.pack("<BBBBHHII", 0, 0, 0, 0, 1, 32, len(png), 22)
    with open(ICO, "wb") as f:
        f.write(header + entry + png)


def main():
    pygame.init()
    tmp = os.path.join(ROOT, "_icon256.png")
    pygame.image.save(make_surface(), tmp)
    build_ico(tmp)
    os.remove(tmp)
    print("icon written:", ICO, os.path.getsize(ICO), "bytes")


if __name__ == "__main__":
    main()
