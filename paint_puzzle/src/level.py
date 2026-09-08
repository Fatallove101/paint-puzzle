# -*- coding: utf-8 -*-
"""关卡:内置关卡参数 + 程序化关卡生成器。

生成器从空白棋盘出发反向模拟随机"整行/整列染色"序列,
最终棋盘即目标图案;按同样顺序重放操作必然可复现目标,
因此每关必然可解,最优步数不超过序列长度。
"""
import random

# 内置关卡参数:(行数, 列数, 颜色数, 染色序列长度)
# 前 10 关使用固定随机种子生成,保证每次进入同一关图案一致。
BUILT_IN_LEVELS = [
    (4, 4, 3, 4),
    (4, 4, 3, 5),
    (4, 4, 3, 6),
    (5, 5, 4, 6),
    (5, 5, 4, 7),
    (5, 5, 4, 8),
    (6, 6, 5, 9),
    (6, 6, 5, 10),
    (6, 6, 5, 11),
    (6, 6, 5, 12),
]

BUILT_IN_SEED_BASE = 20260000  # 第 n 关种子 = base + n


def generate_level(rows, cols, num_colors, seq_len, rng=None):
    """生成一关,返回 (target_grid, ops)。

    target_grid[r][c] 为颜色索引(0 = 空白,1..num_colors 为游戏色);
    ops 为重放即可通关的操作列表,元素 (orientation, index, color)。
    """
    if rng is None:
        rng = random.Random()
    while True:
        grid = [[0] * cols for _ in range(rows)]
        ops = []
        for _ in range(seq_len):
            placed = False
            for _attempt in range(30):
                if rng.random() < 0.5:
                    orient, i = "row", rng.randrange(rows)
                    cells = grid[i]
                else:
                    orient, i = "col", rng.randrange(cols)
                    cells = [grid[r][i] for r in range(rows)]
                c = rng.randint(1, num_colors)
                if all(v == c for v in cells):
                    continue  # 无效操作(染后不变),换一个重试
                if orient == "row":
                    grid[i] = [c] * cols
                else:
                    for r in range(rows):
                        grid[r][i] = c
                ops.append((orient, i, c))
                placed = True
                break
            if not placed:  # 极端情况下兜底:强制染第一行
                c = rng.randint(1, num_colors)
                grid[0] = [c] * cols
                ops.append(("row", 0, c))
        distinct = {v for row in grid for v in row}
        if len(distinct) >= 2:  # 至少两种颜色,图案才有意义
            return grid, ops


def solution_from_ops(gen_ops):
    """从关卡生成序列提炼完整解法:每条线只保留最后一次染色,按时间升序。

    正确性:任一格子的最终颜色由覆盖它的最后一次染色决定,而一条线的
    最后一次染色必然晚于该线更早的染色,所以"每线取最后一次"之后,
    每格的最终染色者与原序列完全一致——从空白棋盘按序执行仍得到目标。
    解法只含真实颜色(>=1)、长度不超过原序列,且被线染色覆盖的格子
    结果与起始棋盘无关(整线覆盖、后染者胜)。
    """
    last = {}
    for t, (orient, i, c) in enumerate(gen_ops):
        last[(orient, i)] = (t, c)
    return [orient_i + (c,)
            for orient_i, (t, c) in sorted(last.items(), key=lambda kv: kv[1][0])]


def next_hint_move(target, ops, board):
    """给定目标、完整解法 ops 和当前棋盘,返回建议的下一步操作。

    找出最大的前缀 k:从当前棋盘执行 ops[k:] 恰好得到目标,
    则建议执行 ops[k]。棋盘与目标一致时返回 None。
    """
    rows, cols = len(board), len(board[0])
    n = len(ops)

    def apply_to(b, op):
        orient, i, c = op
        if orient == "row":
            b[i] = [c] * cols
        else:
            for r in range(rows):
                b[r][i] = c

    best_k = None
    for k in range(n + 1):
        b = [row[:] for row in board]
        for op in ops[k:]:
            apply_to(b, op)
        if b == target:
            best_k = k
    if best_k is None or best_k >= n:
        return None
    return ops[best_k]


STEP_MARGIN = 2  # 步数余量(在生成序列长度之上额外赠送)


def load_level(level_num):
    """按关卡号取参数并生成关卡。返回 dict。

    max_steps 取 max(生成序列长度 + 余量, 求解器解法长度),
    保证从头跟着提示走也一定能在步数预算内通关。
    """
    if level_num <= len(BUILT_IN_LEVELS):
        rows, cols, num_colors, seq_len = BUILT_IN_LEVELS[level_num - 1]
        rng = random.Random(BUILT_IN_SEED_BASE + level_num)
    else:
        # 无限关卡:尺寸、颜色、序列长度随进度缓慢增长(设上限)
        k = level_num - len(BUILT_IN_LEVELS)
        rows = cols = min(7, 6 + k // 8)
        num_colors = min(6, 5 + k // 10)
        seq_len = min(18, 12 + k // 2)
        rng = random.Random()
    grid, ops = generate_level(rows, cols, num_colors, seq_len, rng)
    solution = solution_from_ops(ops)
    max_steps = seq_len + STEP_MARGIN
    if solution:
        max_steps = max(max_steps, len(solution))
    return {
        "rows": rows,
        "cols": cols,
        "num_colors": num_colors,
        "target": grid,
        "ops": ops,
        "solution": solution,
        "max_steps": max_steps,
    }
