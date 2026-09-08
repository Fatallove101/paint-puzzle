# -*- coding: utf-8 -*-
"""冒烟测试:不打开真实窗口,用 SDL dummy 驱动验证核心逻辑。

运行: python tools/smoke_test.py
"""
import os
import random
import sys

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"

ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "src"))

import pygame  # noqa: E402  (需在设置 SDL 环境变量之后导入)

import main as game_mod  # noqa: E402
from level import (generate_level, load_level, next_hint_move,  # noqa: E402
                   solution_from_ops)

FAILURES = []


def check(name, cond):
    print(("PASS " if cond else "FAIL ") + name)
    if not cond:
        FAILURES.append(name)


def settle(game, max_sec=10.0):
    """推进更新直到染色动画全部结束。"""
    t = 0.0
    while game.busy and t < max_sec:
        game.update(1 / 60)
        t += 1 / 60
    game.update(1 / 60)


def test_generator_solvability():
    rng = random.Random(42)
    ok = True
    for _ in range(60):
        rows = rng.randint(3, 7)
        cols = rng.randint(3, 7)
        colors = rng.randint(2, 6)
        seq = rng.randint(3, 15)
        target, ops = generate_level(rows, cols, colors, seq, rng)
        grid = [[0] * cols for _ in range(rows)]
        for orient, i, c in ops:
            if orient == "row":
                grid[i] = [c] * cols
            else:
                for r in range(rows):
                    grid[r][i] = c
        if grid != target:
            ok = False
            break
    check("generator: replay ops reproduces target (60 levels)", ok)


def test_paint_row_and_steps():
    game = game_mod.Game()
    brush = game.row_brushes[1]
    game.cur_color = 2
    game.paint(brush)
    check("paint: step consumed", game.steps_used == 1)
    check("paint: selected color kept after paint", game.cur_color == 2)
    settle(game)
    ok = all(b.color == 2 for b in game.blocks if b.row == 1)
    check("paint: entire row painted with selected color", ok)
    game.paint(brush)  # busy 已结束,应可再次染色
    settle(game)
    check("paint: second paint consumes another step", game.steps_used == 2)
    pygame_quit(game)


def test_win_by_replaying_solution():
    data = load_level(3)  # 内置关,固定种子,与 Game 内生成一致
    game = game_mod.Game()
    game._load_level(3)
    check("win: same deterministic target as load_level",
          game.target == data["target"])
    for orient, i, c in data["ops"]:
        brush = game.row_brushes[i] if orient == "row" else game.col_brushes[i]
        game.cur_color = c
        game.paint(brush)
        settle(game)
    check("win: state is win after replaying all ops", game.state == "win")
    # 通关后点击进入下一关
    game.win_t = 1.0
    game.handle_event(make_click(game.retry_rect.center))
    check("win: click advances to next level", game.level_num == 4)
    pygame_quit(game)


def test_fail_and_reset():
    game = game_mod.Game()
    game._load_level(2)
    rng = random.Random(7)
    while game.steps_left > 0:
        brush = rng.choice(game.row_brushes + game.col_brushes)
        game.cur_color = rng.randint(1, game.num_colors)
        game.paint(brush)
        settle(game)
        if game.state == "win":  # 意外通关则强制破坏再耗步
            game.row_brushes[0].color = 1
            break
    game.update(1 / 60)
    ok = game.state in ("fail", "win")
    check("fail: level ends when steps exhausted", ok)
    if game.state == "fail":
        game.update(2.0)  # 超过重置等待时间
        check("fail: auto reset clears board and restores steps",
              game.state == "play" and game.steps_used == 0
              and all(b.color == 0 for b in game.blocks))
    pygame_quit(game)


def test_solver_from_any_state():
    """从任意"玩家可达"状态(随机真实涂色)出发,提示必须合法:

    next_hint_move 要么给出颜色 1..N 的合法建议且跟着走能通关,
    要么返回 None(该局面已无法达成目标——目标空白处被涂色)。
    """
    rng = random.Random(99)
    ok = True
    solved = stuck = 0
    for _ in range(40):
        rows = rng.randint(3, 7)
        cols = rng.randint(3, 7)
        colors = rng.randint(2, 6)
        target, gen_ops = generate_level(rows, cols, colors,
                                         rng.randint(4, 14), rng)
        ops = solution_from_ops(gen_ops)
        if ops is None:
            ok = False
            break
        # 构造可达状态:从空盘随机做若干次真实涂色
        board = [[0] * cols for _ in range(rows)]
        for _ in range(rng.randint(0, 6)):
            if rng.random() < 0.5:
                board[rng.randrange(rows)] = [rng.randint(1, colors)] * cols
            else:
                i = rng.randrange(cols)
                c = rng.randint(1, colors)
                for r in range(rows):
                    board[r][i] = c
        finished = False
        for _step in range(len(ops) + 5):
            if board == target:
                solved += 1
                finished = True
                break
            move = next_hint_move(target, ops, board)
            if move is None:
                stuck += 1
                finished = True
                break
            orient, i, c = move
            if not (1 <= c <= colors):
                ok = False
                print("  illegal hint color %d (allowed 1..%d)" % (c, colors))
                break
            if orient == "row":
                board[i] = [c] * cols
            else:
                for r in range(rows):
                    board[r][i] = c
        if not ok:
            break
        if not finished:  # 有限步内既没通关也没判定无解,视为缺陷
            ok = False
            print("  hints neither solved nor declared stuck")
            break
    check("solver: legal hints from reachable states (40 levels)", ok)
    print("  (solved=%d, stuck=%d)" % (solved, stuck))


def test_hint_following_solves():
    """从头到尾跟着 next_hint_move 的建议走,必须在有限步内通关。"""
    ok = True
    for lv in range(1, 16):  # 内置 10 关 + 5 个随机生成关
        if lv <= 10:
            data = load_level(lv)
            target = data["target"]
            ops = data["solution"]
        else:
            rng = random.Random(1000 + lv)
            rows = rng.randint(4, 6)
            target, gen_ops = generate_level(rows, rows, rng.randint(3, 5),
                                             rng.randint(6, 12), rng)
            ops = solution_from_ops(gen_ops)
            data = {"target": target, "solution": ops,
                    "max_steps": max(rng.randint(6, 12) + 2, len(ops))}
        rows, cols = len(target), len(target[0])
        board = [[0] * cols for _ in range(rows)]
        steps = 0
        for _step in range(len(ops) + 2):
            if board == target:
                break
            move = next_hint_move(target, ops, board)
            if move is None:  # 未通关却没有建议,视为缺陷
                ok = False
                break
            orient, i, c = move
            if orient == "row":
                board[i] = [c] * cols
            else:
                for r in range(rows):
                    board[r][i] = c
            steps += 1
        if board != target:
            ok = False
            print("  level %d: hints failed to reach target" % lv)
            break
        budget = data.get("max_steps", len(ops) + 2)
        if steps > budget:
            ok = False
            print("  level %d: %d steps exceeds budget %d" % (lv, steps, budget))
            break
    check("hint: following suggestions solves levels 1-15 within budget", ok)


def test_full_level_via_game_hints():
    """游戏级端到端:每关只用提示+点击提示画刷,必须通关且不超步数。"""
    ok = True
    for lv in range(1, 11):
        game = game_mod.Game()
        game._load_level(lv)
        used = 0
        while game.state == "play" and used <= game.max_steps:
            game.use_hint()
            assert game.hint_brush is not None, "level %d: no hint given" % lv
            # 提示画刷颜色必须是本关合法游戏色(不允许建议"染空白")
            assert 1 <= game.cur_color <= game.num_colors
            game.paint(game.hint_brush)
            used += 1
            settle(game)
        if game.state != "win":
            ok = False
            print("  level %d: not won via hints (used %d/%d)"
                  % (lv, used, game.max_steps))
            break
        if used > game.max_steps:
            ok = False
            print("  level %d: %d steps exceeds budget %d"
                  % (lv, used, game.max_steps))
            break
        # 提示次数与剩余步数一致
        if game.hints_left != game.steps_left:
            ok = False
            break
        pygame_quit(game)
    check("game: levels 1-10 clearable purely by hints within budget", ok)


def test_generated_levels_hint_clear():
    """程序生成关(11~25):全程只用"提示+点击提示画刷",必须全部通关、
    不超步数、且不触发死局自动重置(干净开局跟提示不应出现死局)。"""
    ok = True
    for lv in range(11, 26):
        game = game_mod.Game()
        game._load_level(lv)
        used = 0
        while game.state == "play" and used <= game.max_steps:
            if game.soft_reset_t > 0:
                ok = False
                print("  level %d: unexpected dead-end reset" % lv)
                break
            game.use_hint()
            assert game.hint_brush is not None, "level %d: no hint given" % lv
            assert 1 <= game.cur_color <= game.num_colors
            game.paint(game.hint_brush)
            used += 1
            settle(game)
        if game.state != "win":
            ok = False
            print("  level %d: not won via hints (used %d/%d)"
                  % (lv, used, game.max_steps))
            break
        if used > game.max_steps:
            ok = False
            print("  level %d: %d steps exceeds budget %d"
                  % (lv, used, game.max_steps))
            break
        pygame_quit(game)
    check("game: generated levels 11-25 clearable purely by hints", ok)


def test_dead_end_auto_reset():
    """把棋盘涂成不可还原的"死局"后点提示:
    应给出"自动重试"提示,并在倒计时结束后自动重置本关。"""
    ok = False
    for lv in range(1, 26):
        game = game_mod.Game()
        game._load_level(lv)
        row_ops = {op[1] for op in game.solution if op[0] == "row"}
        col_ops = {op[1] for op in game.solution if op[0] == "col"}
        cell = None
        for r in range(game.rows):
            for c in range(game.cols):
                # 目标为空白、且其行列都不会再被涂色 → 一旦染色即成死局
                if game.target[r][c] == 0 and r not in row_ops \
                        and c not in col_ops:
                    cell = (r, c)
                    break
            if cell:
                break
        if cell is None:
            pygame_quit(game)
            continue
        r, c = cell
        brush = game.row_brushes[r]
        game.cur_color = game.num_colors
        game.paint(brush)
        settle(game)
        game.use_hint()
        if game.soft_reset_t <= 0:
            ok = False
            pygame_quit(game)
            break
        game.update(2.0)  # 超过自动重置倒计时
        if game.state == "play" and game.steps_used == 0 \
                and all(b.color == 0 for b in game.blocks):
            ok = True
        pygame_quit(game)
        break
    check("hint: dead-end auto-resets the level", ok)


def make_click(pos):
    e = pygame.event.Event(pygame.MOUSEBUTTONDOWN, {"button": 1, "pos": pos})
    return e


def pygame_quit(game):
    game.audio.sounds = {}
    pygame.display.quit()


def main():
    test_generator_solvability()
    test_paint_row_and_steps()
    test_win_by_replaying_solution()
    test_fail_and_reset()
    test_solver_from_any_state()
    test_hint_following_solves()
    test_full_level_via_game_hints()
    test_generated_levels_hint_clear()
    test_dead_end_auto_reset()
    print("=" * 40)
    if FAILURES:
        print("%d test(s) FAILED" % len(FAILURES))
        sys.exit(1)
    print("all tests passed")


if __name__ == "__main__":
    main()
