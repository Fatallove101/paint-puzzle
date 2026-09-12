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
	for _r in rows:
		row_brushes.append(_rand_brush() if mode == "hard" else 1)
	for _c in cols:
		col_brushes.append(_rand_brush() if mode == "hard" else 1)
	steps_used = 0
	undo_stack = []
	recolor_total = maxi(1, int(max_steps / 2)) if mode == "hard" else 0
	recolor_left = recolor_total
	arm_recolor = false
	last_hint = {}
	dead_end = false
	if cur_color < 1 or cur_color > num_colors:
		cur_color = 1


func _rand_brush() -> int:
	return _rng.randi_range(1, num_colors)


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
	var choices: Array = []
	for c in range(1, num_colors + 1):
		if c != cur:
			choices.append(c)
	if choices.is_empty():
		return
	var v: int = choices[_rng.randi_range(0, choices.size() - 1)]
	if orient == "row":
		row_brushes[index] = v
	else:
		col_brushes[index] = v


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
