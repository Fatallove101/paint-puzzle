# -*- coding: utf-8 -*-
"""方块染色解谜游戏 主入口。

运行: python src/main.py

界面流程:
  主菜单(开始游戏 / 继续上次关卡 / 设置 / 退出游戏)
  → 选择难度(简单:色板自选颜色;困难:随机笔刷色)
  → 选择关卡(第 1~10 关,第 11 关起打完一关自动随机生成下一关)
  → 在限定步数内把棋盘染成与左侧目标一致即通关。

对局内:点行/列画刷染色;每关可"提示"(次数=剩余步数)、
可"撤销"(Ctrl+Z)退回上一步;步数耗尽或死局自动重置。
"""
import json
import math
import os
import random
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
VERSION = "v2.0"

# 存档路径(项目根目录 save.json,不入 git)
SAVE_PATH = os.path.normpath(os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "save.json"))

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

BG = (32, 36, 44)               # 背景色
PANEL = (46, 52, 62)            # 面板色
BTN = (70, 80, 96)              # 按钮底色
BTN_HI = (92, 106, 128)         # 按钮高亮色(悬停/强调)
TEXT = (240, 240, 240)
TEXT_DIM = (180, 186, 196)
GOLD = (255, 230, 120)

# 设置页玩法说明(手动折行)
HELP_LINES = [
    "目标:在限定步数内,把棋盘染成与左侧目标图案完全一致即通关。",
    "操作:先选颜色(简单难度),再点行/列画刷染色;每步消耗 1 点。",
    "提示:剩余每步都可点一次提示,给出最佳下一步,跟提示可通关。",
    "撤销:点\"撤销\"或按 Ctrl+Z 退回上一步;点\"重试\"本关重来。",
    "死局:留白处被染色后无法还原,会提示并自动重试本关。",
    "难度:简单=色板自选颜色;困难=笔刷随机换色。",
    "困难模式:点[改色]会在其下方弹出颜色,先选色再点画刷换色,次数=总步数一半。",
    "进度:ESC 回到主菜单,下次可从\"继续游戏\"接着上次的难度和关卡。",
]


def make_font(size):
    names = [n for n in pygame.font.get_fonts()
             if n in ("microsoftyahei", "dengxian", "simhei", "simsun")]
    try:
        return pygame.font.SysFont(names or "arial", size)
    except Exception:
        return pygame.font.Font(None, size)


class Game:
    """游戏主框架:界面状态机(menu/difficulty/levels/settings/play)+ 对局逻辑。"""

    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((WINDOW_W, WINDOW_H))
        pygame.display.set_caption("方块染色解谜")
        self.clock = pygame.time.Clock()
        self.font = make_font(28)
        self.font_small = make_font(22)
        self.font_title = make_font(58)
        self.font_big = make_font(36)
        self.audio = Audio()
        self.rng = random.Random()

        # 存档 / 设置
        self.save = self._read_save()
        self.audio.enabled = bool(self.save and self.save.get("sound", True))

        # 界面与对局状态
        self.scene = "menu"     # menu / difficulty / levels / settings / play
        self.mode = "easy"      # easy(色板自选) / hard(随机笔刷色)
        self.state = "play"     # 对局内状态: play / win / fail
        self.win_t = 0.0
        self.fail_t = 0.0
        self.soft_reset_t = 0.0  # 提示发现"死局"后的自动重置倒计时(秒)
        self.hint_t = 0.0       # 提示高亮剩余时间
        self.hint_brush = None  # 提示中的画刷
        self.hint_msg = ""
        self.hint_msg_t = 0.0
        self.cur_color = 1      # 当前目标颜色:简单=染色色;困难=改色目标色
        self.palette_rects = []  # [(颜色索引, Rect), ...]
        self.undo_stack = []    # 撤销栈(每次成功染色前压栈)
        self.recolor_total = 0  # 困难模式:本关可自选笔刷色的次数(总步数一半)
        self.recolor_left = 0
        self.arm_recolor = False  # 改色模式开关(开启后点画刷=给它换色)

        # 对局数据(进入关卡后填充;主菜单阶段为空)
        self.level_num = 1
        self.rows = self.cols = self.num_colors = 0
        self.target = []
        self.max_steps = 0
        self.solution = []
        self.blocks = []
        self.row_brushes = []
        self.col_brushes = []

        # 顶栏按钮(宽度按四个排布:撤销/提示/改色/重试)
        self.undo_rect = pygame.Rect(524, 26, 106, 40)
        self.hint_rect = pygame.Rect(634, 26, 106, 40)
        self.recolor_rect = pygame.Rect(744, 26, 106, 40)  # 困难模式:自选笔刷色
        self.retry_rect = pygame.Rect(854, 26, 106, 40)

    # ================================================================ 存档
    def _read_save(self):
        try:
            with open(SAVE_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            if data.get("mode") in ("easy", "hard"):
                return {"mode": data["mode"],
                        "level": max(1, int(data.get("level", 1))),
                        "sound": bool(data.get("sound", True))}
        except Exception:
            pass
        return None

    def _save_progress(self):
        try:
            with open(SAVE_PATH, "w", encoding="utf-8") as f:
                json.dump({"mode": self.mode, "level": self.level_num,
                           "sound": self.audio.enabled}, f,
                          ensure_ascii=False, indent=2)
        except OSError:
            pass

    # ================================================================ 流程
    def _to_menu(self):
        """对局中按 ESC:保存进度后回到主菜单。"""
        self._save_progress()
        self.scene = "menu"

    def _start_new(self):
        self.scene = "difficulty"

    def _choose_difficulty(self, mode):
        self.mode = mode
        self.scene = "levels"

    def _pick_level(self, num):
        self._go_play(num)

    def _continue_game(self):
        if not self.save:
            return
        self.mode = self.save["mode"]
        self._go_play(self.save["level"])

    def _go_play(self, num):
        """正式进入某一关(并保存进度)。"""
        self._load_level(num)
        self._save_progress()

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
        self.scene = "play"
        self._reset_board()

    def _reset_board(self):
        """重置当前关卡:棋盘清空、步数恢复、撤销栈清空。"""
        self.blocks = []
        for r in range(self.rows):
            for c in range(self.cols):
                rect = pygame.Rect(BOARD_X + c * CELL_SIZE,
                                   BOARD_Y + r * CELL_SIZE,
                                   CELL_SIZE, CELL_SIZE)
                self.blocks.append(Block(r, c, rect))
        self.row_brushes = []
        self.col_brushes = []
        for r in range(self.rows):
            rect = pygame.Rect(BOARD_X - BRUSH_W - 8, BOARD_Y + r * CELL_SIZE + 2,
                               BRUSH_W, CELL_SIZE - 4)
            color = self.rng.randint(1, self.num_colors) \
                if self.mode == "hard" else None
            self.row_brushes.append(Brush("row", r, rect, color))
        for c in range(self.cols):
            rect = pygame.Rect(BOARD_X + c * CELL_SIZE + 2,
                               BOARD_Y + self.rows * CELL_SIZE + 8,
                               CELL_SIZE - 4, BRUSH_W)
            color = self.rng.randint(1, self.num_colors) \
                if self.mode == "hard" else None
            self.col_brushes.append(Brush("col", c, rect, color))
        # 色板(简单难度):本关可用颜色 1..num_colors 横排居中
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
        # 困难模式:自选笔刷色次数 = 总步数的一半(每关重新计算)
        if self.mode == "hard":
            self.recolor_total = max(1, self.max_steps // 2)
        else:
            self.recolor_total = 0
        self.recolor_left = self.recolor_total
        self.arm_recolor = False
        self.steps_used = 0
        self.state = "play"
        self.win_t = 0.0
        self.fail_t = 0.0
        self.soft_reset_t = 0.0
        self.hint_t = 0.0
        self.hint_brush = None
        self.hint_msg = ""
        self.hint_msg_t = 0.0
        self.undo_stack = []

    # ================================================================ 状态查询
    @property
    def all_brushes(self):
        return self.row_brushes + self.col_brushes

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

    @property
    def difficulty_name(self):
        return "简单" if self.mode == "easy" else "困难"

    def _matched(self):
        for b in self.blocks:
            if b.color != self.target[b.row][b.col]:
                return False
        return True

    # ================================================================ 对局交互
    def handle_event(self, event):
        """返回 True 表示应退出程序。"""
        if event.type != pygame.MOUSEBUTTONDOWN or event.button != 1:
            return False
        pos = event.pos
        if self.scene == "menu":
            return self._handle_menu(pos)
        if self.scene == "difficulty":
            self._handle_difficulty(pos)
            return False
        if self.scene == "levels":
            self._handle_levels(pos)
            return False
        if self.scene == "settings":
            self._handle_settings(pos)
            return False
        # ---- play ----
        if self.state == "win":
            if self.win_t > 0.9:
                self._go_play(self.level_num + 1)
            return False
        if self.state not in ("play", "fail"):
            return False
        if self.retry_rect.collidepoint(pos):
            self._reset_board()
            self.audio.play("click")
        elif self.hint_rect.collidepoint(pos):
            self.use_hint()
        elif self.undo_rect.collidepoint(pos):
            self.undo()
        elif self.mode == "hard" and self.recolor_rect.collidepoint(pos) \
                and self.state == "play" and self.recolor_left > 0:
            # 困难模式:切换"改色模式"(点画刷=把色板颜色设给它)
            self.arm_recolor = not self.arm_recolor
            self.audio.play("click")
        else:
            if self.mode == "easy":
                # 简单:顶部横排色板 = 当前染色色
                for idx, rect in self.palette_rects:
                    if rect.collidepoint(pos):
                        if idx != self.cur_color:
                            self.cur_color = idx
                            self.audio.play("click")
                        return False
            elif self.arm_recolor:
                # 困难:改色模式下,改色按钮下方的竖排色块 = 换色目标色
                for idx, rect in self._recolor_rects():
                    if rect.collidepoint(pos):
                        if idx != self.cur_color:
                            self.cur_color = idx
                            self.audio.play("click")
                        return False
            for brush in self.all_brushes:
                if brush.hit(pos):
                    if self.mode == "hard" and self.arm_recolor:
                        self.recolor_brush(brush)
                    else:
                        self.paint(brush)
                    return False
        return False

    # ---- 主菜单
    def _menu_buttons(self):
        items = [("start", "开始游戏"), ("continue", "继续游戏"),
                 ("settings", "设置"), ("exit", "退出游戏")]
        out = []
        for i, (key, label) in enumerate(items):
            rect = pygame.Rect(0, 300 + i * 80, 300, 58)
            rect.centerx = WINDOW_W // 2
            enabled = key != "continue" or bool(self.save)
            out.append((key, label, rect, enabled))
        return out

    def _handle_menu(self, pos):
        for key, label, rect, enabled in self._menu_buttons():
            if rect.collidepoint(pos):
                if not enabled:
                    return False
                self.audio.play("click")
                if key == "start":
                    self._start_new()
                elif key == "continue":
                    self._continue_game()
                elif key == "settings":
                    self.scene = "settings"
                elif key == "exit":
                    self._save_progress()
                    return True
                return False
        return False

    # ---- 难度选择
    def _difficulty_buttons(self):
        back = pygame.Rect(40, 34, 120, 46)
        easy = pygame.Rect(0, 300, 380, 150)
        easy.centerx = 250
        hard = pygame.Rect(0, 300, 380, 150)
        hard.centerx = 710
        return [("easy", easy), ("hard", hard), ("back", back)]

    def _handle_difficulty(self, pos):
        for key, rect in self._difficulty_buttons():
            if rect.collidepoint(pos):
                self.audio.play("click")
                if key in ("easy", "hard"):
                    self._choose_difficulty(key)
                elif key == "back":
                    self.scene = "menu"
                return

    # ---- 关卡选择
    def _level_buttons(self):
        back = pygame.Rect(40, 34, 120, 46)
        w = h = 92
        gap = 16
        total = 5 * w + 4 * gap
        x0 = (WINDOW_W - total) // 2
        rects = [("back", back)]
        for i in range(10):
            col, row = i % 5, i // 5
            rects.append(("lv%d" % (i + 1),
                          pygame.Rect(x0 + col * (w + gap),
                                      260 + row * (h + 16), w, h)))
        return rects

    def _handle_levels(self, pos):
        for key, rect in self._level_buttons():
            if rect.collidepoint(pos):
                self.audio.play("click")
                if key == "back":
                    self.scene = "difficulty"
                elif key.startswith("lv"):
                    self._pick_level(int(key[2:]))
                return

    # ---- 设置
    def _sound_rect(self):
        return pygame.Rect(300, 208, 140, 48)

    def _settings_back_rect(self):
        return pygame.Rect(0, 640, 220, 52).move((WINDOW_W - 220) // 2, 0)

    def _handle_settings(self, pos):
        if self._sound_rect().collidepoint(pos):
            self.audio.enabled = not self.audio.enabled
            self.audio.play("click")
            self._save_progress()
        elif self._settings_back_rect().collidepoint(pos):
            self.audio.play("click")
            self.scene = "menu"
        elif pygame.Rect(40, 34, 120, 46).collidepoint(pos):
            self.audio.play("click")
            self.scene = "menu"

    # ================================================================ 染色/提示/撤销
    def paint(self, brush):
        """点击画刷染色:简单=用色板选中色,困难=用笔刷自带随机色。"""
        if self.busy or self.steps_left <= 0 or self.soft_reset_t > 0:
            return
        if self.state != "play":
            return
        self.undo_stack.append(self._snapshot())
        brush.press()
        self.audio.play("click")
        self.audio.play("paint")
        color = brush.color if self.mode == "hard" else self.cur_color
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
        if self.mode == "hard":
            brush.reroll(self.num_colors)

    def recolor_brush(self, brush):
        """困难模式:把一支画刷的颜色改成色板当前选中的颜色。

        需先开启"改色模式";每次成功换色消耗 1 次自选次数(总步数的一半),
        不消耗染色步数。换色成功后**自动收起**改色弹层,防止连点误耗次数;
        需要再改时重新点[改色]即可。颜色相同则不消耗并提示。
        """
        if self.mode != "hard" or self.state != "play" or not self.arm_recolor:
            return
        if self.recolor_left <= 0:
            self.arm_recolor = False
            return
        if brush.color == self.cur_color:
            self.hint_msg = "该画刷已是这个颜色"
            self.hint_msg_t = 1.2
            return
        brush.color = self.cur_color
        brush.press()
        brush.flash()
        self.audio.play("click")
        self.recolor_left -= 1
        self.arm_recolor = False   # 一次一用,自动收起,防误触
        if self.recolor_left > 0:
            self.hint_msg = "已换色,剩余 %d 次(再点[改色]继续)" % self.recolor_left
        else:
            self.hint_msg = "改色次数已用完"
        self.hint_msg_t = 1.6

    # ---- 撤销
    def _snapshot(self):
        colors = tuple(b.color for b in self.blocks)
        bcolors = tuple(br.color for br in self.all_brushes) \
            if self.mode == "hard" else None
        return (colors, bcolors, self.cur_color, self.steps_used)

    def undo(self):
        """撤销最近一次染色:还原棋盘、步数与笔刷颜色,并取消 fail/死局重置。"""
        if self.scene != "play" or not self.undo_stack:
            return False
        if self.busy or self.state not in ("play", "fail"):
            return False
        colors, bcolors, cur, steps = self.undo_stack.pop()
        for b, val in zip(self.blocks, colors):
            b.set_instant(val)
        if bcolors is not None:
            for br, val in zip(self.all_brushes, bcolors):
                br.color = val
                br._press_t = 0.0
                br._flash_t = 0.0
        self.cur_color = cur
        self.steps_used = steps
        self.state = "play"
        self.win_t = 0.0
        self.fail_t = 0.0
        self.soft_reset_t = 0.0
        self.hint_t = 0.0
        self.hint_brush = None
        self.hint_msg = ""
        self.hint_msg_t = 0.0
        self.audio.play("click")
        return True

    def _board_colors(self):
        board = [[0] * self.cols for _ in range(self.rows)]
        for b in self.blocks:
            board[b.row][b.col] = b.color
        return board

    def use_hint(self):
        """提示:反推求解器给出下一步(染哪一行/列 + 所需颜色)。

        简单难度:只把色板选中所需颜色,不改变画刷;
        困难难度:把目标画刷设成所需颜色(玩家无法直接控制随机色)。
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
        where = "第%d行" % (i + 1) if orient == "row" else "第%d列" % (i + 1)
        if self.mode == "hard":
            if brush.color != c:
                brush.color = c
                brush.flash()
            self.hint_msg = "提示:点击%s画刷(颜色已替你调好)" % where
        else:
            self.cur_color = c          # 仅选中色板颜色,不触碰任何画刷
            self.hint_msg = "提示:点击%s画刷(颜色已自动选好)" % where
        self.hint_brush = brush
        self.hint_t = HINT_SHOW_SEC
        self.hint_msg_t = HINT_SHOW_SEC
        self.audio.play("click")

    # ================================================================ 帧更新
    def update(self, dt):
        if self.scene != "play":
            return
        for b in self.blocks:
            b.update(dt)
        for br in self.all_brushes:
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

    def on_key(self, key, mods=0):
        """键盘事件;返回 True 表示应退出程序。"""
        if key == pygame.K_ESCAPE:
            if self.scene == "play":
                self._to_menu()
            elif self.scene == "difficulty":
                self.scene = "menu"
            elif self.scene == "levels":
                self.scene = "difficulty"
            elif self.scene == "settings":
                self.scene = "menu"
            elif self.scene == "menu":
                self._save_progress()
                return True
        elif key == pygame.K_z and (mods & pygame.KMOD_CTRL):
            self.undo()
        return False

    # ================================================================ 渲染
    def draw(self):
        self.screen.fill(BG)
        if self.scene == "menu":
            self._draw_menu()
        elif self.scene == "difficulty":
            self._draw_difficulty()
        elif self.scene == "levels":
            self._draw_levels()
        elif self.scene == "settings":
            self._draw_settings()
        else:
            self._draw_play()

    # ---- 通用按钮
    def _draw_button(self, rect, label, enabled=True, accent=False,
                     label_font=None, fill=None):
        font = label_font or self.font
        if fill is None:
            fill = BTN_HI if accent else BTN
        if not enabled:
            fill = (48, 54, 64)
            edge = (80, 88, 100)
        else:
            edge = (150, 160, 175) if accent else (140, 150, 165)
        pygame.draw.rect(self.screen, fill, rect, border_radius=10)
        pygame.draw.rect(self.screen, edge, rect, 2, border_radius=10)
        color = TEXT if enabled else (110, 118, 130)
        text = font.render(label, True, color)
        self.screen.blit(text, text.get_rect(center=rect.center))

    def _draw_wrapped(self, text, box, y_start):
        """把说明文字按 box 宽度自动折行,从 y_start 起逐行居中绘制。"""
        font = self.font_small
        max_w = box.width - 24
        lines = []
        cur = ""
        for ch in text:
            if font.size(cur + ch)[0] <= max_w:
                cur += ch
            else:
                if cur:
                    lines.append(cur)
                cur = ch
        if cur:
            lines.append(cur)
        y = y_start
        for line in lines:
            surf = font.render(line, True, TEXT_DIM)
            self.screen.blit(surf, surf.get_rect(center=(box.centerx, y)))
            y += surf.get_height() + 4
        return y

    def _draw_menu(self):
        self._draw_title("方块染色解谜", "Paint Puzzle  ·  染色解谜", 210)
        tip = self.font_small.render("第 11 关起自动随机生成 · 进度自动保存",
                                     True, TEXT_DIM)
        self.screen.blit(tip, tip.get_rect(center=(WINDOW_W // 2, 640)))
        ver = self.font_small.render(VERSION, True, (110, 118, 130))
        self.screen.blit(ver, (WINDOW_W - ver.get_width() - 16,
                               WINDOW_H - ver.get_height() - 12))
        for key, label, rect, enabled in self._menu_buttons():
            if key == "continue" and enabled:
                label = "继续游戏(%s·第%d关)" % (
                    "简单" if self.save["mode"] == "easy" else "困难",
                    self.save["level"])
            elif key == "continue":
                label = "继续游戏(暂无进度)"
            self._draw_button(rect, label, enabled, accent=(key == "start"))

    def _draw_title(self, main, sub, y):
        t = self.font_title.render(main, True, TEXT)
        self.screen.blit(t, t.get_rect(center=(WINDOW_W // 2, y - 40)))
        s = self.font.render(sub, True, GOLD)
        self.screen.blit(s, s.get_rect(center=(WINDOW_W // 2, y + 16)))

    def _draw_difficulty(self):
        self._draw_button(pygame.Rect(40, 34, 120, 46), "← 返回",
                          label_font=self.font_small)
        self._draw_title("选择难度", "想怎么控制颜色?", 190)
        easy_desc = "自选颜色:先在色板选中颜色,再点行/列画刷染色"
        hard_desc = "随机笔刷:每支笔刷颜色随机,用后换新,更考验规划"
        easy, hard, back = None, None, None
        for key, rect in self._difficulty_buttons():
            if key == "easy":
                easy = rect
            elif key == "hard":
                hard = rect
            elif key == "back":
                back = rect
        pygame.draw.rect(self.screen, (46, 52, 62), easy, border_radius=12)
        pygame.draw.rect(self.screen, (90, 160, 110), easy, 2, border_radius=12)
        l1 = self.font_big.render("简单", True, TEXT)
        self.screen.blit(l1, l1.get_rect(center=(easy.centerx, easy.top + 46)))
        self._draw_wrapped(easy_desc, easy, easy.top + 100)
        pygame.draw.rect(self.screen, (46, 52, 62), hard, border_radius=12)
        pygame.draw.rect(self.screen, (230, 120, 110), hard, 2, border_radius=12)
        l2 = self.font_big.render("困难", True, TEXT)
        self.screen.blit(l2, l2.get_rect(center=(hard.centerx, hard.top + 46)))
        self._draw_wrapped(hard_desc, hard, hard.top + 100)
        tip = self.font_small.render("两种难度都可通过提示通关", True, GOLD)
        self.screen.blit(tip, tip.get_rect(center=(WINDOW_W // 2, 520)))

    def _draw_levels(self):
        self._draw_button(pygame.Rect(40, 34, 120, 46), "← 返回",
                          label_font=self.font_small)
        title = self.font_title.render("选择关卡", True, TEXT)
        self.screen.blit(title, title.get_rect(center=(WINDOW_W // 2, 110)))
        sub = self.font.render("难度:%s · 第 1~10 关为固定图案"
                               % self.difficulty_name, True, GOLD)
        self.screen.blit(sub, sub.get_rect(center=(WINDOW_W // 2, 158)))
        for key, rect in self._level_buttons():
            if key == "back":
                continue
            num = int(key[2:])
            self._draw_button(rect, str(num), label_font=self.font_big,
                              accent=False)
        note = self.font_small.render(
            "从第 11 关起:通关后自动生成并进入下一关", True, TEXT_DIM)
        self.screen.blit(note, note.get_rect(center=(WINDOW_W // 2, 560)))

    def _draw_settings(self):
        self._draw_title("设置", "音效与玩法说明", 150)
        self._draw_button(pygame.Rect(40, 34, 120, 46), "← 返回",
                          label_font=self.font_small)
        sound_l = self.font.render("音效:", True, TEXT)
        self.screen.blit(sound_l, (190, 218))
        self._draw_button(self._sound_rect(),
                          "开" if self.audio.enabled else "关",
                          label_font=self.font_big,
                          accent=self.audio.enabled)
        y = 320
        head = self.font_small.render("玩法说明", True, GOLD)
        self.screen.blit(head, (120, y - 26))
        for line in HELP_LINES:
            t = self.font_small.render(line, True, (205, 210, 220))
            self.screen.blit(t, (120, y))
            y += 36
        self._draw_button(self._settings_back_rect(), "返回主菜单")

    # ================================================================ 对局渲染
    def _draw_play(self):
        self._draw_top_bar()
        self._draw_target()
        self._draw_board()
        if self.mode == "easy":
            self._draw_palette()          # 简单:顶部横排选染色色
        elif self.arm_recolor:
            self._draw_recolor_popup()    # 困难:改色按钮下方的竖排选色
        self._draw_hint_line()
        for br in self.all_brushes:
            br.draw(self.screen, PALETTE if self.mode == "hard" else None)
        self._draw_hint_brush()
        if self.state == "fail":
            self._draw_fail_overlay()
        elif self.state == "win" and self.win_t > 0.9:
            self._draw_center_text("通关!点击进入下一关", GOLD)
        if self.arm_recolor and self.state == "play":
            self._draw_bottom_text(
                "改色模式:点一支画刷,换成色板选中的颜色(剩 %d 次)"
                % self.recolor_left, (255, 220, 150))
        elif self.hint_msg_t > 0 and self.state == "play":
            self._draw_bottom_text(self.hint_msg, (120, 220, 255),
                                   alpha=self.hint_msg_t / HINT_SHOW_SEC)
        tip = self.font_small.render(
            "ESC 菜单 · Ctrl+Z 撤销 · 困难可用[改色]自选笔刷色", True,
            (110, 118, 130))
        self.screen.blit(tip, (24, WINDOW_H - tip.get_height() - 14))

    def _draw_hint_line(self):
        """提示期间:在建议染色的整行/整列上覆盖脉动高亮。"""
        if self.hint_t <= 0 or self.hint_brush is None:
            return
        alpha = 60 + int(40 * math.sin(self.hint_t * 8))
        if self.hint_brush.orientation == "row":
            rect = pygame.Rect(BOARD_X, BOARD_Y + self.hint_brush.index * CELL_SIZE,
                               self.cols * CELL_SIZE, CELL_SIZE)
        else:
            rect = pygame.Rect(BOARD_X + self.hint_brush.index * CELL_SIZE,
                               BOARD_Y, CELL_SIZE, self.rows * CELL_SIZE)
        overlay = pygame.Surface(rect.size, pygame.SRCALPHA)
        overlay.fill((255, 255, 255, alpha))
        self.screen.blit(overlay, rect.topleft)

    def _draw_hint_brush(self):
        """提示期间:给目标画刷加脉动描边。"""
        if self.hint_t <= 0 or self.hint_brush is None:
            return
        rect = self.hint_brush.rect.inflate(8, 8)
        alpha = 160 + int(80 * math.sin(self.hint_t * 8))
        outline = pygame.Surface((rect.width + 8, rect.height + 8),
                                 pygame.SRCALPHA)
        pygame.draw.rect(outline, (255, 255, 255, alpha),
                         (4, 4, rect.width, rect.height), 4, border_radius=10)
        self.screen.blit(outline, (rect.left - 4, rect.top - 4))

    def _draw_bottom_text(self, text, color, alpha=1.0):
        label = self.font.render(text, True, color)
        bg = pygame.Surface((label.get_width() + 30, label.get_height() + 14),
                            pygame.SRCALPHA)
        bg.fill((20, 22, 28, int(210 * alpha)))
        label.set_alpha(int(255 * alpha))
        pos = (WINDOW_W // 2 - bg.get_width() // 2, WINDOW_H - bg.get_height() - 42)
        self.screen.blit(bg, pos)
        self.screen.blit(label, label.get_rect(center=(WINDOW_W // 2,
                                                       pos[1] + bg.get_height() // 2)))

    def _draw_top_bar(self):
        self.screen.blit(self.font.render("第 %d 关 · %s" % (self.level_num,
                                                             self.difficulty_name),
                                          True, TEXT), (TARGET_BOX_X, 30))
        color = (255, 90, 90) if self.steps_left <= 3 else TEXT
        self.screen.blit(self.font.render("剩余步数:%d" % self.steps_left,
                                          True, color), (290, 30))
        # 撤销按钮:不可用(无记录/动画中/非进行状态)时置灰
        can_undo = self.scene == "play" and bool(self.undo_stack) \
            and not self.busy and self.state in ("play", "fail")
        self._draw_button(self.undo_rect, "撤销", can_undo,
                          label_font=self.font_small)
        # 提示按钮:次数用完后置灰
        enabled_hint = self.hints_left > 0
        self._draw_button(self.hint_rect, "提示 ×%d" % self.hints_left,
                          enabled_hint, accent=enabled_hint,
                          label_font=self.font_small)
        # 困难模式:自选笔刷色按钮
        if self.mode == "hard":
            can_sel = self.recolor_left > 0
            self._draw_button(self.recolor_rect,
                              "改色 ×%d" % self.recolor_left, can_sel,
                              accent=self.arm_recolor, label_font=self.font_small)
        # 重试按钮
        self._draw_button(self.retry_rect, "重试", True,
                          label_font=self.font_small)

    def _recolor_rects(self):
        """困难模式改色弹层:改色按钮下方竖排的颜色块(避开棋盘右侧)。"""
        chip, gap = 36, 8
        x = 792                     # 保证不压到最大棋盘(右缘 <= 778)
        y = 84
        out = []
        for idx in range(1, self.num_colors + 1):
            out.append((idx, pygame.Rect(x, y, chip, chip)))
            y += chip + gap
        return out

    def _draw_recolor_popup(self):
        """在[改色]按钮下方画竖排颜色块;当前选中色画金圈。"""
        rects = self._recolor_rects()
        n = len(rects)
        if n == 0:
            return
        top = rects[0][1].top - 10
        bottom = rects[-1][1].bottom + 10
        panel = pygame.Rect(782, top, 56, bottom - top)
        pygame.draw.rect(self.screen, PANEL, panel, border_radius=10)
        pygame.draw.rect(self.screen, (140, 150, 165), panel, 2,
                         border_radius=10)
        for idx, rect in rects:
            pygame.draw.rect(self.screen, PALETTE[idx], rect, border_radius=8)
            if idx == self.cur_color:
                pygame.draw.rect(self.screen, GOLD, rect, 3, border_radius=8)
            else:
                pygame.draw.rect(self.screen, (70, 70, 70), rect, 2,
                                 border_radius=8)

    def _draw_palette(self):
        """色板(简单难度):本关可用颜色横排;当前选中色画金圈,其余细灰边。"""
        for idx, rect in self.palette_rects:
            pygame.draw.rect(self.screen, PALETTE[idx], rect, border_radius=8)
            if idx == self.cur_color:
                pygame.draw.rect(self.screen, GOLD, rect, 3, border_radius=8)
            else:
                pygame.draw.rect(self.screen, (70, 70, 70), rect, 2,
                                 border_radius=8)

    def _draw_target(self):
        rows, cols = self.rows, self.cols
        cell = min((TARGET_BOX_W - 20) // cols, (TARGET_BOX_W - 20) // rows, 40)
        w, h = cell * cols, cell * rows
        y_center = BOARD_Y + rows * CELL_SIZE // 2
        box = pygame.Rect(TARGET_BOX_X, y_center - h // 2 - 30,
                          TARGET_BOX_W, h + 60)
        pygame.draw.rect(self.screen, PANEL, box, border_radius=10)
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
        self._draw_center_text("步数耗尽,可撤销或等待重置…", (255, 120, 120))

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
                if game.scene == "play":
                    game._save_progress()
                running = False
            elif event.type == pygame.KEYDOWN:
                if game.on_key(event.key, event.mod):
                    running = False
            elif game.handle_event(event):
                running = False
        game.update(dt)
        game.draw()
        pygame.display.flip()
    pygame.quit()
    sys.exit(0)


if __name__ == "__main__":
    main()
