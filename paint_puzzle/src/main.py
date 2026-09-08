# -*- coding: utf-8 -*-
"""方块染色解谜游戏 主入口。

运行: python src/main.py
点击棋盘左侧画刷染整行、底部画刷染整列,在限定步数内把棋盘
染成左侧目标图案即可通关;步数耗尽则关卡重置。
"""
import math
import sys

import pygame

from audio import Audio
from block import Block
from brush import Brush
from level import load_level, next_hint_move

# ---------------------------------------------------------------- 全局参数
WINDOW_W, WINDOW_H = 960, 720
FPS = 60
CELL_SIZE = 64          # 方块边长(像素)
PAINT_DELAY = 0.04      # 相邻方块染色的错峰间隔(秒)
PAINT_DUR = 0.18        # 单个方块染色渐变时长(秒)
HINT_SHOW_SEC = 4.0     # 提示高亮与文案的显示时长(秒)

# 26 种游戏颜色:精选高饱和、高区分度色板,按"前缀互异性"排序——
# 任意前 N 个颜色放在一起都容易区分(每关只取前 num_colors 种)。
# 颜色索引 0 表示空白,不在此列。
GAME_COLORS = [
    (230, 55, 60),    # 红
    (35, 100, 235),   # 蓝
    (255, 213, 0),    # 黄
    (45, 165, 65),    # 绿
    (150, 75, 225),   # 紫
    (250, 140, 25),   # 橙
    (0, 185, 205),    # 青
    (245, 100, 150),  # 粉
    (145, 90, 45),    # 棕
    (25, 45, 125),    # 藏青
    (165, 220, 40),   # 青柠
    (0, 125, 115),    # 水鸭色
    (205, 40, 155),   # 品红
    (125, 195, 245),  # 天蓝
    (115, 120, 130),  # 灰
    (130, 145, 40),   # 橄榄
    (125, 30, 45),    # 酒红
    (75, 60, 160),    # 靛蓝
    (250, 110, 90),   # 珊瑚
    (110, 220, 170),  # 薄荷
    (190, 160, 240),  # 淡紫
    (235, 175, 55),   # 琥珀
    (70, 130, 180),   # 钢蓝
    (170, 40, 90),    # 玫红
    (90, 160, 90),    # 苔绿
    (120, 50, 120),   # 李紫
]
BLANK_RGB = (243, 243, 238)
PALETTE = [BLANK_RGB] + GAME_COLORS

BOARD_X, BOARD_Y = 330, 140     # 棋盘左上角
BRUSH_W = 46                    # 画刷厚度
TARGET_BOX_X, TARGET_BOX_W = 50, 210   # 左侧目标图案区域
PALETTE_Y = 94                  # 色板行(色块)顶部 y 坐标
PALETTE_CHIP = 40               # 色块边长(像素)
PALETTE_GAP = 12                # 色块间距


def make_font(size):
    names = [n for n in pygame.font.get_fonts()
             if n in ("microsoftyahei", "dengxian", "simhei", "simsun")]
    try:
        return pygame.font.SysFont(names or "arial", size)
    except Exception:
        return pygame.font.Font(None, size)


class Game:
    """游戏框架:改 load_level 的参数即可生成不同大小的棋盘。"""

    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((WINDOW_W, WINDOW_H))
        pygame.display.set_caption("方块染色解谜")
        self.clock = pygame.time.Clock()
        self.font = make_font(28)
        self.font_small = make_font(22)
        self.audio = Audio()
        self.retry_rect = pygame.Rect(800, 26, 110, 40)
        self.hint_rect = pygame.Rect(670, 26, 110, 40)
        self.state = "play"     # play / win / fail
        self.win_t = 0.0
        self.fail_t = 0.0
        self.soft_reset_t = 0.0  # 提示发现"死局"后的自动重置倒计时(秒)
        self.hint_t = 0.0       # 提示高亮剩余时间
        self.hint_brush = None  # 提示中的画刷
        self.hint_msg = ""
        self.hint_msg_t = 0.0
        self.cur_color = 1      # 当前选中的染色颜色(色板)
        self.palette_rects = []  # [(颜色索引, Rect), ...],由 _reset_board 构建
        self.level_num = 1
        self._load_level(1)

    # ------------------------------------------------ 关卡装载
    def _load_level(self, num):
        data = load_level(num)
        self.level_num = num
        self.rows = data["rows"]
        self.cols = data["cols"]
        self.num_colors = data["num_colors"]
        self.target = data["target"]
        self.max_steps = data["max_steps"]
        self.solution = data["solution"]
        self._reset_board()

    def _reset_board(self):
        """重置当前关卡:棋盘清空、步数恢复;选中颜色保留(超范围则取 1)。"""
        self.blocks = []
        for r in range(self.rows):
            for c in range(self.cols):
                rect = pygame.Rect(BOARD_X + c * CELL_SIZE, BOARD_Y + r * CELL_SIZE,
                                   CELL_SIZE, CELL_SIZE)
                self.blocks.append(Block(r, c, rect))
        self.row_brushes = []
        self.col_brushes = []
        for r in range(self.rows):
            rect = pygame.Rect(BOARD_X - BRUSH_W - 8, BOARD_Y + r * CELL_SIZE + 2,
                               BRUSH_W, CELL_SIZE - 4)
            self.row_brushes.append(Brush("row", r, rect))
        for c in range(self.cols):
            rect = pygame.Rect(BOARD_X + c * CELL_SIZE + 2,
                               BOARD_Y + self.rows * CELL_SIZE + 8,
                               CELL_SIZE - 4, BRUSH_W)
            self.col_brushes.append(Brush("col", c, rect))
        # 色板:本关可用颜色 1..num_colors 横排居中,点击即切换当前染色色
        if not (1 <= self.cur_color <= self.num_colors):
            self.cur_color = 1
        total_w = self.num_colors * PALETTE_CHIP \
            + (self.num_colors - 1) * PALETTE_GAP
        x = (WINDOW_W - total_w) // 2
        self.palette_rects = []
        for idx in range(1, self.num_colors + 1):
            self.palette_rects.append(
                (idx, pygame.Rect(x, PALETTE_Y, PALETTE_CHIP, PALETTE_CHIP)))
            x += PALETTE_CHIP + PALETTE_GAP
        self.steps_used = 0
        self.state = "play"
        self.win_t = 0.0
        self.fail_t = 0.0
        self.soft_reset_t = 0.0
        self.hint_t = 0.0
        self.hint_brush = None
        self.hint_msg = ""
        self.hint_msg_t = 0.0

    # ------------------------------------------------ 状态查询
    @property
    def steps_left(self):
        return self.max_steps - self.steps_used

    @property
    def hints_left(self):
        """提示次数与剩余步数一致:每一步都可以要一次提示。"""
        return self.steps_left

    @property
    def busy(self):
        return any(b.busy for b in self.blocks)

    def _matched(self):
        for b in self.blocks:
            if b.color != self.target[b.row][b.col]:
                return False
        return True

    # ------------------------------------------------ 交互
    def handle_event(self, event):
        if event.type != pygame.MOUSEBUTTONDOWN or event.button != 1:
            return
        pos = event.pos
        if self.state == "win":
            if self.win_t > 0.9:
                self._load_level(self.level_num + 1)
            return
        if self.state != "play":
            return
        if self.retry_rect.collidepoint(pos):
            self._reset_board()
            self.audio.play("click")
            return
        if self.hint_rect.collidepoint(pos):
            self.use_hint()
            return
        for idx, rect in self.palette_rects:   # 色板:切换当前染色颜色
            if rect.collidepoint(pos):
                if idx != self.cur_color:
                    self.cur_color = idx
                    self.audio.play("click")
                return
        for brush in self.row_brushes + self.col_brushes:
            if brush.hit(pos):
                self.paint(brush)
                return

    def paint(self, brush):
        """点击画刷:用当前选中的颜色整行/整列错峰染色,消耗 1 步。"""
        if self.busy or self.steps_left <= 0 or self.soft_reset_t > 0:
            return
        brush.press()
        self.audio.play("click")
        self.audio.play("paint")
        color = self.cur_color
        if brush.orientation == "row":
            line = [b for b in self.blocks if b.row == brush.index]
            line.sort(key=lambda b: b.col)
        else:
            line = [b for b in self.blocks if b.col == brush.index]
            line.sort(key=lambda b: b.row)
        for i, block in enumerate(line):
            block.set_color(color, delay=i * PAINT_DELAY, dur=PAINT_DUR,
                            palette=PALETTE)
        self.steps_used += 1

    def _board_colors(self):
        board = [[0] * self.cols for _ in range(self.rows)]
        for b in self.blocks:
            board[b.row][b.col] = b.color
        return board

    def use_hint(self):
        """提示:反推求解器给出下一步(染哪一行/列 + 所需颜色)。

        只做两件事:①在色板中自动选中所需颜色;②高亮对应画刷。
        绝不改变任何画刷——颜色选择权始终在玩家手中,玩家可随时改选。
        提示次数与剩余步数一致,不单独扣减——染色落子时步数自然消耗。
        """
        if self.hints_left <= 0 or self.busy or self.state != "play" \
                or self.soft_reset_t > 0:
            return
        ops = self.solution
        move = next_hint_move(self.target, ops, self._board_colors())
        if move is None:
            if not self._matched():  # 棋盘已无法变成目标(某条空白线被染色)
                self.hint_brush = None
                self.hint_t = 0.0
                self.hint_msg = "当前局面已无法达成目标,即将自动重试…"
                self.hint_msg_t = HINT_SHOW_SEC
                self.soft_reset_t = 1.4
                self.audio.play("fail")
            return
        orient, i, c = move
        brush = self.row_brushes[i] if orient == "row" else self.col_brushes[i]
        self.cur_color = c          # 仅选中色板颜色,不触碰任何笔刷
        self.hint_brush = brush
        self.hint_t = HINT_SHOW_SEC
        where = "第%d行" % (i + 1) if orient == "row" else "第%d列" % (i + 1)
        self.hint_msg = "提示:点击%s画刷(颜色已自动选好)" % where
        self.hint_msg_t = HINT_SHOW_SEC
        self.audio.play("click")

    # ------------------------------------------------ 帧更新
    def update(self, dt):
        for b in self.blocks:
            b.update(dt)
        for br in self.row_brushes + self.col_brushes:
            br.update(dt)

        if self.soft_reset_t > 0:
            # 提示发现死局:先展示提示文案,倒计时结束后自动重置本关
            self.soft_reset_t = max(0.0, self.soft_reset_t - dt)
            if self.soft_reset_t <= 0:
                self._reset_board()
        else:
            if self.state == "play" and not self.busy:
                if self._matched():
                    self.state = "win"
                    self.win_t = 0.0
                    self.audio.play("win")
                elif self.steps_left <= 0:
                    self.state = "fail"
                    self.fail_t = 0.0
                    self.audio.play("fail")
            elif self.state == "win":
                self.win_t += dt
            elif self.state == "fail":
                self.fail_t += dt
                if self.fail_t > 1.6:
                    self._reset_board()

            if self.hint_t > 0:
                self.hint_t = max(0.0, self.hint_t - dt)
            if self.hint_msg_t > 0:
                self.hint_msg_t = max(0.0, self.hint_msg_t - dt)

    # ------------------------------------------------ 渲染
    def draw(self):
        self.screen.fill((32, 36, 44))
        self._draw_top_bar()
        self._draw_target()
        self._draw_board()
        self._draw_palette()
        self._draw_hint_line()
        for br in self.row_brushes + self.col_brushes:
            br.draw(self.screen)
        self._draw_hint_brush()
        if self.state == "fail":
            self._draw_fail_overlay()
        elif self.state == "win" and self.win_t > 0.9:
            self._draw_center_text("通关!点击进入下一关", (255, 230, 120))
        if self.hint_msg_t > 0 and self.state == "play":
            self._draw_bottom_text(self.hint_msg, (120, 220, 255),
                                   alpha=self.hint_msg_t / HINT_SHOW_SEC)

    def _draw_hint_line(self):
        """提示期间:在建议染色的整行/整列上覆盖脉动高亮。"""
        if self.hint_t <= 0 or self.hint_brush is None:
            return
        alpha = 60 + int(40 * math.sin(self.hint_t * 8))
        if self.hint_brush.orientation == "row":
            rect = pygame.Rect(BOARD_X, BOARD_Y + self.hint_brush.index * CELL_SIZE,
                               self.cols * CELL_SIZE, CELL_SIZE)
        else:
            rect = pygame.Rect(BOARD_X + self.hint_brush.index * CELL_SIZE, BOARD_Y,
                               CELL_SIZE, self.rows * CELL_SIZE)
        overlay = pygame.Surface(rect.size, pygame.SRCALPHA)
        overlay.fill((255, 255, 255, alpha))
        self.screen.blit(overlay, rect.topleft)

    def _draw_hint_brush(self):
        """提示期间:给目标画刷加脉动描边。"""
        if self.hint_t <= 0 or self.hint_brush is None:
            return
        rect = self.hint_brush.rect.inflate(8, 8)
        alpha = 160 + int(80 * math.sin(self.hint_t * 8))
        outline = pygame.Surface((rect.width + 8, rect.height + 8), pygame.SRCALPHA)
        pygame.draw.rect(outline, (255, 255, 255, alpha),
                         (4, 4, rect.width, rect.height), 4, border_radius=10)
        self.screen.blit(outline, (rect.left - 4, rect.top - 4))

    def _draw_bottom_text(self, text, color, alpha=1.0):
        label = self.font.render(text, True, color)
        bg = pygame.Surface((label.get_width() + 30, label.get_height() + 14),
                            pygame.SRCALPHA)
        bg.fill((20, 22, 28, int(210 * alpha)))
        label.set_alpha(int(255 * alpha))
        pos = (WINDOW_W // 2 - bg.get_width() // 2, WINDOW_H - bg.get_height() - 24)
        self.screen.blit(bg, pos)
        self.screen.blit(label, label.get_rect(center=(WINDOW_W // 2,
                                                       pos[1] + bg.get_height() // 2)))

    def _draw_top_bar(self):
        self.screen.blit(self.font.render("第 %d 关" % self.level_num,
                                          True, (240, 240, 240)), (TARGET_BOX_X, 30))
        color = (255, 90, 90) if self.steps_left <= 3 else (240, 240, 240)
        self.screen.blit(self.font.render("剩余步数:%d" % self.steps_left,
                                          True, color), (280, 30))
        pygame.draw.rect(self.screen, (70, 80, 96), self.retry_rect, border_radius=8)
        pygame.draw.rect(self.screen, (140, 150, 165), self.retry_rect, 2,
                         border_radius=8)
        label = self.font_small.render("重试", True, (240, 240, 240))
        self.screen.blit(label, label.get_rect(center=self.retry_rect.center))
        # 提示按钮:次数用完后置灰
        enabled = self.hints_left > 0
        pygame.draw.rect(self.screen, (70, 80, 96) if enabled else (48, 54, 64),
                         self.hint_rect, border_radius=8)
        pygame.draw.rect(self.screen, (140, 150, 165) if enabled else (80, 88, 100),
                         self.hint_rect, 2, border_radius=8)
        hint_label = self.font_small.render("提示 ×%d" % self.hints_left, True,
                                            (120, 220, 255) if enabled
                                            else (110, 118, 130))
        self.screen.blit(hint_label, hint_label.get_rect(center=self.hint_rect.center))

    def _draw_palette(self):
        """色板:本关可用颜色横排;当前选中色画金圈,其余画细灰边。"""
        for idx, rect in self.palette_rects:
            pygame.draw.rect(self.screen, PALETTE[idx], rect, border_radius=8)
            if idx == self.cur_color:
                pygame.draw.rect(self.screen, (255, 230, 120), rect, 3,
                                 border_radius=8)
            else:
                pygame.draw.rect(self.screen, (70, 70, 70), rect, 2,
                                 border_radius=8)

    def _draw_target(self):
        rows, cols = self.rows, self.cols
        cell = min((TARGET_BOX_W - 20) // cols, (TARGET_BOX_W - 20) // rows, 40)
        w, h = cell * cols, cell * rows
        y_center = BOARD_Y + rows * CELL_SIZE // 2
        box = pygame.Rect(TARGET_BOX_X, y_center - h // 2 - 30, TARGET_BOX_W, h + 60)
        pygame.draw.rect(self.screen, (46, 52, 62), box, border_radius=10)
        pygame.draw.rect(self.screen, (90, 100, 115), box, 2, border_radius=10)
        label = self.font_small.render("目标", True, (200, 205, 215))
        self.screen.blit(label, (TARGET_BOX_X + 10, box.top + 8))
        ox = box.left + (TARGET_BOX_W - w) // 2
        oy = box.top + 40 + (h + 10 - h) // 2
        for r in range(rows):
            for c in range(cols):
                rect = pygame.Rect(ox + c * cell, oy + r * cell, cell, cell)
                self.screen.fill(PALETTE[self.target[r][c]], rect)
                pygame.draw.rect(self.screen, (60, 60, 60), rect, 1)

    def _draw_board(self):
        board_w = self.cols * CELL_SIZE
        board_h = self.rows * CELL_SIZE
        pygame.draw.rect(self.screen, (210, 210, 205),
                         pygame.Rect(BOARD_X - 4, BOARD_Y - 4,
                                     board_w + 8, board_h + 8))
        win = self.state == "win"
        for b in self.blocks:
            rect = b.rect
            rgb = b.display_rgb(PALETTE)
            if win and self.win_t < 1.4:
                # 胜利波浪:按对角线次序弹跳
                phase = self.win_t * 7 - (b.row + b.col) * 0.45
                bounce = max(0.0, math.sin(phase)) * 10
                rect = rect.move(0, -int(bounce))
                rgb = tuple(min(255, v + int(bounce * 4)) for v in rgb)
            b.draw(self.screen, PALETTE, rect=rect, rgb=rgb)

    def _draw_fail_overlay(self):
        board_w = self.cols * CELL_SIZE
        board_h = self.rows * CELL_SIZE
        overlay = pygame.Surface((board_w, board_h), pygame.SRCALPHA)
        overlay.fill((180, 30, 30, 140))
        self.screen.blit(overlay, (BOARD_X, BOARD_Y))
        self._draw_center_text("步数耗尽,关卡重置…", (255, 120, 120))

    def _draw_center_text(self, text, color):
        label = self.font.render(text, True, color)
        bg = pygame.Surface((label.get_width() + 30, label.get_height() + 16),
                            pygame.SRCALPHA)
        bg.fill((20, 22, 28, 210))
        pos = (WINDOW_W // 2 - bg.get_width() // 2,
               BOARD_Y + self.rows * CELL_SIZE // 2 - bg.get_height() // 2)
        self.screen.blit(bg, pos)
        self.screen.blit(label, label.get_rect(center=(WINDOW_W // 2,
                                                       pos[1] + bg.get_height() // 2)))


def main():
    game = Game()
    running = True
    while running:
        dt = game.clock.tick(FPS) / 1000.0
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                running = False
            else:
                game.handle_event(event)
        game.update(dt)
        game.draw()
        pygame.display.flip()
    pygame.quit()
    sys.exit(0)


if __name__ == "__main__":
    main()
