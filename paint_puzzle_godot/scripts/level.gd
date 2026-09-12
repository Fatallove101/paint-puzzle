class_name PPLevel
extends RefCounted
## 关卡模块(移植自 pygame 版 level.py)
## - 前 10 关:固定参数 + 固定随机种子(每次进入图案一致)
## - 第 11 关起:程序化无限生成(反向模拟染色序列,保证必然可解)
## - 反推求解器:剥掉"单色线"倒推出完整解法;提示基于它实时计算

const BUILT_IN := [
	[4, 4, 3, 4], [4, 4, 3, 5], [4, 4, 3, 6],
	[5, 5, 4, 6], [5, 5, 4, 7], [5, 5, 4, 8],
	[6, 6, 5, 9], [6, 6, 5, 10], [6, 6, 5, 11], [6, 6, 5, 12],
]
const SEED_BASE := 20260000
const STEP_MARGIN := 2


static func _filled(n: int, v: int) -> Array:
	var a: Array = []
	a.resize(n)
	a.fill(v)
	return a


static func zeros(n: int) -> Array:
	return _filled(n, 0)


static func copy_board(board: Array) -> Array:
	var out: Array = []
	for row in board:
		out.append((row as Array).duplicate())
	return out


static func same_board(a: Array, b: Array) -> bool:
	if a.size() != b.size():
		return false
	for r in a.size():
		for c in (a[r] as Array).size():
			if a[r][c] != b[r][c]:
				return false
	return true


## 生成一关,返回 {target, ops};ops 为重放即可得到 target 的操作序列
static func generate_level(rows: int, cols: int, num_colors: int,
		seq_len: int, rng: RandomNumberGenerator) -> Dictionary:
	while true:
		var grid: Array = []
		for _r in rows:
			grid.append(zeros(cols))
		var ops: Array = []
		for _s in seq_len:
			var placed := false
			for _attempt in 30:
				var is_row := rng.randf() < 0.5
				var idx := rng.randi_range(0, (rows if is_row else cols) - 1)
				var c := rng.randi_range(1, num_colors)
				var all_same := true
				if is_row:
					for v in grid[idx]:
						if v != c:
							all_same = false
							break
				else:
					for r in rows:
						if grid[r][idx] != c:
							all_same = false
							break
				if all_same:
					continue
				if is_row:
					grid[idx] = _filled(cols, c)
				else:
					for r in rows:
						grid[r][idx] = c
				ops.append({"orient": "row" if is_row else "col",
					"index": idx, "color": c})
				placed = true
				break
			if not placed:
				var c2 := rng.randi_range(1, num_colors)
				grid[0] = _filled(cols, c2)
				ops.append({"orient": "row", "index": 0, "color": c2})
		var distinct := {}
		for row in grid:
			for v in row:
				distinct[v] = true
		if distinct.size() >= 2:
			return {"target": grid, "ops": ops}
	return {}


## 每一条线只保留最后一次染色,按时间升序 = 完整解法
static func solution_from_ops(ops: Array) -> Array:
	var last := {}
	var keys: Array = []
	for t in ops.size():
		var op: Dictionary = ops[t]
		var key := "%s:%d" % [op.orient, op.index]
		if not last.has(key):
			keys.append(key)
		last[key] = {"t": t, "color": op.color}
	keys.sort_custom(func(a, b): return last[a].t < last[b].t)
	var out: Array = []
	for k in keys:
		var parts: PackedStringArray = String(k).split(":")
		out.append({"orient": parts[0], "index": int(parts[1]),
			"color": last[k].color})
	return out


static func apply_op(board: Array, op: Dictionary) -> void:
	if op.orient == "row":
		for c in (board[op.index] as Array).size():
			board[op.index][c] = op.color
	else:
		for r in board.size():
			board[r][op.index] = op.color


## 给出当前局面的下一步建议;无法达成目标时返回 null
static func next_hint_move(target: Array, ops: Array, board: Array) -> Variant:
	var n := ops.size()
	var best := -1
	for k in range(n + 1):
		var b := copy_board(board)
		for i in range(k, n):
			apply_op(b, ops[i])
		if same_board(b, target):
			best = k
	if best < 0 or best >= n:
		return null
	return ops[best]


## 按关卡号生成关卡数据
static func load_level(num: int) -> Dictionary:
	var rows: int
	var cols: int
	var num_colors: int
	var seq_len: int
	var rng := RandomNumberGenerator.new()
	if num <= BUILT_IN.size():
		var p: Array = BUILT_IN[num - 1]
		rows = p[0]
		cols = p[1]
		num_colors = p[2]
		seq_len = p[3]
		rng.seed = SEED_BASE + num
	else:
		var k: int = num - BUILT_IN.size()
		rows = mini(7, 6 + int(k / 8))
		cols = rows
		num_colors = mini(6, 5 + int(k / 10))
		seq_len = mini(18, 12 + int(k / 2))
		rng.randomize()
	var gen := generate_level(rows, cols, num_colors, seq_len, rng)
	var solution := solution_from_ops(gen.ops)
	var max_steps: int = seq_len + STEP_MARGIN
	if solution.size() > max_steps:
		max_steps = solution.size()
	return {
		"rows": rows, "cols": cols, "num_colors": num_colors,
		"target": gen.target, "ops": gen.ops, "solution": solution,
		"max_steps": max_steps,
	}
