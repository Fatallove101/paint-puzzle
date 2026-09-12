extends SceneTree
## 逻辑自测(移植自 pygame 版 smoke_test.py 的关键用例)
## 运行:godot --headless --path <工程> --script res://tests/logic_test.gd

const LevelLib = preload("res://scripts/level.gd")
const GameLib = preload("res://scripts/game.gd")

var fails: Array = []


func check(label: String, cond: bool) -> void:
	print(("PASS " if cond else "FAIL ") + label)
	if not cond:
		fails.append(label)


func _initialize() -> void:
	test_generator_replay()
	test_level_deterministic()
	test_solution_reaches_target()
	test_hint_following_solves()
	test_easy_paint_and_undo()
	test_hard_mode_and_recolor()
	test_hint_dead_end_detection()
	test_refresh_and_fair_random()
	print("========================================")
	if fails.is_empty():
		print("all logic tests passed")
		quit(0)
	else:
		print("%d test(s) FAILED" % fails.size())
		quit(1)


func _rng(seedv: int) -> RandomNumberGenerator:
	var r := RandomNumberGenerator.new()
	r.seed = seedv
	return r


func test_generator_replay() -> void:
	var r := _rng(42)
	var ok := true
	for _i in 60:
		var rows := r.randi_range(3, 7)
		var cols := r.randi_range(3, 7)
		var colors := r.randi_range(2, 6)
		var seq := r.randi_range(3, 15)
		var gen: Dictionary = LevelLib.generate_level(rows, cols, colors, seq, r)
		var grid: Array = []
		for _x in rows:
			grid.append(LevelLib.zeros(cols))
		for op in gen.ops:
			LevelLib.apply_op(grid, op)
		if not LevelLib.same_board(grid, gen.target):
			ok = false
			break
	check("generator: replay ops reproduces target (60 levels)", ok)


func test_level_deterministic() -> void:
	var a: Dictionary = LevelLib.load_level(3)
	var b: Dictionary = LevelLib.load_level(3)
	check("level: built-in level 3 is deterministic",
		LevelLib.same_board(a.target, b.target))


func test_solution_reaches_target() -> void:
	var ok := true
	for lv in range(1, 26):
		var d: Dictionary = LevelLib.load_level(lv)
		var board: Array = []
		for _r in int(d.rows):
			board.append(LevelLib.zeros(int(d.cols)))
		var used := 0
		for op in d.solution:
			LevelLib.apply_op(board, op)
			used += 1
		if not LevelLib.same_board(board, d.target):
			ok = false
			print("  level %d: solution does not reach target" % lv)
			break
		if used > int(d.max_steps):
			ok = false
			print("  level %d: solution %d > budget %d" % [lv, used, int(d.max_steps)])
			break
	check("level: solution reaches target within budget (levels 1-25)", ok)


func test_hint_following_solves() -> void:
	var ok := true
	for lv in range(1, 26):
		var d: Dictionary = LevelLib.load_level(lv)
		var board: Array = []
		for _r in int(d.rows):
			board.append(LevelLib.zeros(int(d.cols)))
		var steps := 0
		var guard := 0
		while not LevelLib.same_board(board, d.target) and guard < 80:
			var mv = LevelLib.next_hint_move(d.target, d.solution, board)
			if mv == null:
				ok = false
				print("  level %d: no hint while unsolved" % lv)
				break
			LevelLib.apply_op(board, mv)
			steps += 1
			guard += 1
		if not LevelLib.same_board(board, d.target):
			ok = false
			break
		if steps > int(d.max_steps):
			ok = false
			print("  level %d: hints took %d > budget %d" % [lv, steps, int(d.max_steps)])
			break
	check("hint: following hints solves levels 1-25 within budget", ok)


func test_easy_paint_and_undo() -> void:
	var g = GameLib.new()
	g.start(1, "easy")
	g.cur_color = 2
	var ok1: bool = g.paint("row", 1)
	var row_ok := true
	for c in g.cols:
		if g.board[1][c] != 2:
			row_ok = false
	check("easy: paint consumes step and fills row",
		ok1 and g.steps_used == 1 and row_ok)
	var did: bool = g.undo()
	var blank := true
	for r in g.rows:
		for c in g.cols:
			if g.board[r][c] != 0:
				blank = false
	check("easy: undo restores blank board + steps",
		did and g.steps_used == 0 and blank and not g.can_undo())


func test_hard_mode_and_recolor() -> void:
	var g = GameLib.new()
	g.start(1, "hard")
	check("hard: recolor quota is half of total steps",
		g.recolor_total == maxi(1, int(g.max_steps / 2))
		and g.recolor_left == g.recolor_total)
	var c0: int = g.brush_color("row", 2)
	var ok: bool = g.paint("row", 2)
	var painted := true
	for c in g.cols:
		if g.board[2][c] != c0:
			painted = false
	check("hard: paint uses brush color", ok and painted)
	check("hard: brush rerolled after use", g.brush_color("row", 2) != c0)
	g.undo()
	check("hard: undo restores brush color and board",
		g.brush_color("row", 2) == c0 and g.steps_used == 0)
	# 提示应把目标画刷设成所需颜色
	var g2 = GameLib.new()
	g2.start(3, "hard")
	var r: Dictionary = g2.use_hint()
	check("hard: hint returns a move", r.has("move"))
	if r.has("move"):
		var op: Dictionary = r.move
		var col: int = g2.brush_color(op.orient, int(op.index))
		check("hard: hint set brush to needed color", col == int(op.color))
	# 自选笔刷色:用一次后自动收起,不消耗染色步数
	var g3 = GameLib.new()
	g3.start(1, "hard")
	var steps0: int = g3.steps_used
	g3.arm_recolor = true
	g3.cur_color = (g3.brush_color("row", 0) % g3.num_colors) + 1
	var done: bool = g3.recolor("row", 0)
	check("recolor: one use works, auto-closes, no step cost",
		done and not g3.arm_recolor
		and g3.recolor_left == g3.recolor_total - 1
		and g3.steps_used == steps0)


func test_hint_dead_end_detection() -> void:
	# 造一个死局:把目标为空白、且行列都不会再被染色的格子涂上颜色
	var g = GameLib.new()
	g.start(1, "hard")
	var row_ops := {}
	var col_ops := {}
	for op in g.solution:
		if op.orient == "row":
			row_ops[int(op.index)] = true
		else:
			col_ops[int(op.index)] = true
	var found := Vector2i(-1, -1)
	for r in g.rows:
		for c in g.cols:
			if int(g.target[r][c]) == 0 and not row_ops.has(r) and not col_ops.has(c):
				found = Vector2i(r, c)
				break
		if found.x >= 0:
			break
	if found.x < 0:
		check("dead-end: (no suitable level, skipped)", true)
		return
	g.cur_color = g.num_colors
	g.paint("row", found.x)
	check("dead-end: detected after painting a must-stay-blank line",
		g.is_dead_end_state())
	var r2: Dictionary = g.use_hint()
	check("dead-end: hint reports dead end", r2.has("dead_end"))


func test_refresh_and_fair_random() -> void:
	# 刷色:不消耗步数、一次一用、颜色必定变化
	var g = GameLib.new()
	g.start(1, "hard")
	check("refresh: quota exists",
		g.refresh_total > 0 and g.refresh_left == g.refresh_total)
	var steps0: int = g.steps_used
	var c0: int = g.brush_color("row", 0)
	g.arm_refresh = true
	var ok: bool = g.refresh_brush("row", 0)
	check("refresh: works, auto-closes, no step cost",
		ok and not g.arm_refresh and g.refresh_left == g.refresh_total - 1
		and g.steps_used == steps0 and g.brush_color("row", 0) != c0)
	# 公平随机:刷出来的颜色属于"当前仍需的颜色"
	var need: Array = g.needed_colors()
	check("fair random: refreshed color comes from needed set",
		need.is_empty() or need.has(g.brush_color("row", 0)))
	# 初始笔刷颜色也只来自需求集合,且每种需求颜色至少出现在一支笔刷上
	var g2 = GameLib.new()
	g2.start(2, "hard")
	var need2: Array = g2.needed_colors()
	var keys: Array = g2._brush_keys()
	var all_ok := true
	for k in keys:
		if not need2.has(g2.brush_color(k[0], k[1])):
			all_ok = false
	check("fair random: initial brush colors are needed colors", all_ok)
	var present := {}
	for k in keys:
		present[g2.brush_color(k[0], k[1])] = true
	var covered := true
	for c in need2:
		if not present.has(int(c)):
			covered = false
	check("fair random: every needed color is on some brush", covered)
	# 刷色之后仍可按提示通关(不会因刷色陷入死局)
	var ok2 := true
	var guard := 0
	while not g.matched() and guard < 40:
		var r: Dictionary = g.use_hint()
		if r.is_empty() or r.has("dead_end"):
			ok2 = false
			break
		var op: Dictionary = r.move
		g.paint(op.orient, int(op.index))
		guard += 1
	check("hard: still solvable via hints after refreshes",
		ok2 and g.matched())
