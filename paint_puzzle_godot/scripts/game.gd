class_name PPGame
extends RefCounted
## 对局逻辑(移植自 pygame 版 main.py 的规则部分,不含界面/渲染)

## 26 色板(索引 0 = 空白,1..26 为游戏色),与 pygame 版一致
const COLORS: Array = [
	Color8(230, 55, 60), Color8(35, 100, 235), Color8(255, 213, 0),
	Color8(45, 165, 65), Color8(150, 75, 225), Color8(250, 140, 25),
	Color8(0, 185, 205), Color8(245, 100, 150), Color8(145, 90, 45),
	Color8(25, 45, 125), Color8(165, 220, 40), Color8(0, 125, 115),
	Color8(205, 40, 155), Color8(125, 195, 245), Color8(115, 120, 130),
	Color8(130, 145, 40), Color8(125, 30, 45), Color8(75, 60, 160),
	Color8(250, 110, 90), Color8(110, 220, 170), Color8(190, 160, 240),
	Color8(235, 175, 55), Color8(70, 130, 180), Color8(170, 40, 90),
	Color8(90, 160, 90), Color8(120, 50, 120),
]
const BLANK := Color8(243, 243, 238)

var mode := "easy"          # easy / hard
var level_num := 1
var rows := 0
var cols := 0
var num_colors := 0
var target: Array = []      # rows x cols, 0=空白
var solution: Array = []
var max_steps := 0
var steps_used := 0
var board: Array = []       # 当前棋盘
var row_brushes: Array = [] # 每行画刷颜色(困难模式有意义)
var col_brushes: Array = []
var cur_color := 1          # 简单:染色色;困难:改色目标色
var undo_stack: Array = []
var recolor_total := 0      # 困难:可自选笔刷色次数 = 总步数一半
var recolor_left := 0
var arm_recolor := false
var refresh_total := 0      # 困难:可"刷色"(重随笔刷颜色,不落子)次数
var refresh_left := 0
var arm_refresh := false
var last_hint: Dictionary = {}
var dead_end := false

var _rng := RandomNumberGenerator.new()


func color_of(idx: int) -> Color:
	if idx <= 0 or idx > COLORS.size():
		return BLANK
	return COLORS[idx - 1]


func steps_left() -> int:
	return max_steps - steps_used


func hints_left() -> int:
	return maxi(0, steps_left())


func start(num: int, m: String) -> void:
	mode = m
	level_num = num
	var d := PPLevel.load_level(num)
	rows = int(d.rows)
	cols = int(d.cols)
	num_colors = int(d.num_colors)
	target = d.target
	solution = d.solution
	max_steps = int(d.max_steps)
	reset()


func reset() -> void:
	board = []
	for _r in rows:
		board.append(PPLevel.zeros(cols))
	row_brushes = []
	col_brushes = []
	# 困难模式:初始笔刷颜色只从"本关仍需的颜色"里抽(公平随机)
	for _r in rows:
		row_brushes.append(_fair_color() if mode == "hard" else 1)
	for _c in cols:
		col_brushes.append(_fair_color() if mode == "hard" else 1)
	_ensure_needed_present()
	steps_used = 0
	undo_stack = []
	recolor_total = maxi(1, int(max_steps / 2)) if mode == "hard" else 0
	recolor_left = recolor_total
	refresh_total = maxi(3, num_colors * 2) if mode == "hard" else 0
	refresh_left = refresh_total
	arm_recolor = false
	arm_refresh = false
	last_hint = {}
	dead_end = false
	if cur_color < 1 or cur_color > num_colors:
		cur_color = 1


func _rand_brush() -> int:
	return _rng.randi_range(1, num_colors)


## 当前局面下"仍然需要的颜色"集合(来自反推求解器的剩余步骤)
func needed_colors() -> Array:
	var k := _solution_suffix_index()
	if k < 0:
		return []
	var seen := {}
	for i in range(k, solution.size()):
		seen[int(solution[i].color)] = true
	return seen.keys()


## 从当前棋盘出发,最少还需要 solution 的哪一段(返回起始下标;k==size 表示已完成)
func _solution_suffix_index() -> int:
	var n := solution.size()
	var best := -1
	for k in range(n + 1):
		var b := PPLevel.copy_board(board)
		for i in range(k, n):
			PPLevel.apply_op(b, solution[i])
		if PPLevel.same_board(b, target):
			best = k
	return best


func _fair_color() -> int:
	var pool := needed_colors()
	if pool.is_empty():
		return _rng.randi_range(1, num_colors)
	return int(pool[_rng.randi_range(0, pool.size() - 1)])


func _fair_pool(exclude: int) -> Array:
	var out: Array = []
	for c in needed_colors():
		if int(c) != exclude:
			out.append(int(c))
	return out


func _all_colors_except(exclude: int) -> Array:
	var out: Array = []
	for c in range(1, num_colors + 1):
		if c != exclude:
			out.append(c)
	return out


func _assign_brush(orient: String, index: int, color: int) -> void:
	if orient == "row":
		row_brushes[index] = color
	else:
		col_brushes[index] = color


func _brush_keys() -> Array:
	var out: Array = []
	for r in rows:
		out.append(["row", r])
	for c in cols:
		out.append(["col", c])
	return out


## 保证"仍需要的每种颜色"至少出现在一支笔刷上,避免运气死局
func _ensure_needed_present() -> void:
	if mode != "hard":
		return
	var need := needed_colors()
	var keys := _brush_keys()
	if need.is_empty() or keys.size() < need.size():
		return
	var present := {}
	for k in keys:
		present[brush_color(k[0], k[1])] = true
	for c in need:
		if present.has(int(c)):
			continue
		var target = null
		for k in keys:
			if not need.has(brush_color(k[0], k[1])):
				target = k
				break
		if target == null:
			target = keys[0]
		_assign_brush(target[0], target[1], int(c))
		present[int(c)] = true


func brush_color(orient: String, index: int) -> int:
	return row_brushes[index] if orient == "row" else col_brushes[index]


func matched() -> bool:
	return PPLevel.same_board(board, target)


func can_act() -> bool:
	return steps_left() > 0


func paint(orient: String, index: int) -> bool:
	if not can_act():
		return false
	_snapshot()
	var color := cur_color
	if mode == "hard":
		color = brush_color(orient, index)
	if orient == "row":
		for c in cols:
			board[index][c] = color
	else:
		for r in rows:
			board[r][index] = color
	steps_used += 1
	if mode == "hard":
		_reroll(orient, index)
	last_hint = {}
	return true


func _reroll(orient: String, index: int) -> void:
	var cur := brush_color(orient, index)
	# 公平随机:优先从"当前仍需的颜色"里抽,抽不到再退回全色板
	var pool := _fair_pool(cur)
	if pool.is_empty():
		pool = _all_colors_except(cur)
	if pool.is_empty():
		return
	_assign_brush(orient, index,
		int(pool[_rng.randi_range(0, pool.size() - 1)]))


## 困难模式"刷色":重随某支笔刷的颜色,不染色、不消耗步数(消耗 1 次刷色次数)
func refresh_brush(orient: String, index: int) -> bool:
	if mode != "hard" or not arm_refresh or refresh_left <= 0:
		return false
	var cur := brush_color(orient, index)
	var pool := _fair_pool(cur)
	if pool.is_empty():
		pool = _all_colors_except(cur)
	if pool.is_empty():
		return false
	_assign_brush(orient, index,
		int(pool[_rng.randi_range(0, pool.size() - 1)]))
	refresh_left -= 1
	arm_refresh = false
	return true


func _snapshot() -> void:
	undo_stack.append({
		"board": PPLevel.copy_board(board),
		"row": row_brushes.duplicate(),
		"col": col_brushes.duplicate(),
		"cur": cur_color,
		"steps": steps_used,
	})


func can_undo() -> bool:
	return not undo_stack.is_empty()


func undo() -> bool:
	if undo_stack.is_empty():
		return false
	var s: Dictionary = undo_stack.pop_back()
	board = s.board
	row_brushes = s.row
	col_brushes = s.col
	cur_color = int(s.cur)
	steps_used = int(s.steps)
	last_hint = {}
	dead_end = false
	return true


## 提示:返回 {"move": op} / {"dead_end": true} / {}
func use_hint() -> Dictionary:
	if steps_left() <= 0:
		return {}
	var mv = PPLevel.next_hint_move(target, solution, board)
	if mv == null:
		if not matched():
			dead_end = true
			return {"dead_end": true}
		return {}
	var op: Dictionary = mv
	if mode == "hard":
		if op.orient == "row":
			row_brushes[op.index] = op.color
		else:
			col_brushes[op.index] = op.color
	else:
		cur_color = int(op.color)
	last_hint = op
	dead_end = false
	return {"move": op}


## 困难模式:把某条线画刷改成色板当前色(消耗 1 次,成功后自动收起)
func recolor(orient: String, index: int) -> bool:
	if mode != "hard" or not arm_recolor or recolor_left <= 0:
		return false
	if brush_color(orient, index) == cur_color:
		return false
	if orient == "row":
		row_brushes[index] = cur_color
	else:
		col_brushes[index] = cur_color
	recolor_left -= 1
	arm_recolor = false
	return true


## 关卡是否需要按"死局"处理(棋盘已不可能变成目标)
func is_dead_end_state() -> bool:
	if matched():
		return false
	return PPLevel.next_hint_move(target, solution, board) == null
