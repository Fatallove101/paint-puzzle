class_name PPBoardView
extends Control
## 对局棋盘视图:绘制目标图案、棋盘、行/列画刷、色板、提示高亮;处理触控点击
## 坐标与 pygame 版一致(设计分辨率 960x720,横屏)

signal paint_requested(orient: String, index: int)
signal recolor_requested(orient: String, index: int)
signal refresh_requested(orient: String, index: int)
signal color_selected(idx: int)

const BOARD_X := 330.0
const BOARD_Y := 140.0
const CELL := 64.0
const BRUSH_W := 46.0
const TARGET_X := 50.0
const TARGET_W := 210.0
const PALETTE_Y := 94.0
const CHIP := 40.0
const CHIP_GAP := 12.0
const POPUP_X := 792.0
const POPUP_Y := 84.0

var game: PPGame = null
var _font: Font
var _t := 0.0


func _ready() -> void:
	_font = ThemeDB.fallback_font
	set_process(true)


func _process(delta: float) -> void:
	_t += delta
	if game != null and not game.last_hint.is_empty():
		queue_redraw()   # 提示高亮需要脉动


func set_game(g: PPGame) -> void:
	game = g
	queue_redraw()


func _chip_rects() -> Array:
	var out: Array = []
	if game == null:
		return out
	var total: float = game.num_colors * CHIP + (game.num_colors - 1) * CHIP_GAP
	var x: float = (960.0 - total) / 2.0
	for i in range(1, game.num_colors + 1):
		out.append([i, Rect2(x, PALETTE_Y, CHIP, CHIP)])
		x += CHIP + CHIP_GAP
	return out


func _popup_rects() -> Array:
	var out: Array = []
	if game == null:
		return out
	var y := POPUP_Y
	for i in range(1, game.num_colors + 1):
		out.append([i, Rect2(POPUP_X, y, 36, 36)])
		y += 44
	return out


func row_brush_rect(r: int) -> Rect2:
	return Rect2(BOARD_X - BRUSH_W - 8.0, BOARD_Y + r * CELL + 2.0,
		BRUSH_W, CELL - 4.0)


func col_brush_rect(c: int) -> Rect2:
	return Rect2(BOARD_X + c * CELL + 2.0, BOARD_Y + game.rows * CELL + 8.0,
		CELL - 4.0, BRUSH_W)


func _gui_input(event: InputEvent) -> void:
	if game == null:
		return
	# 只处理"触摸"事件:桌面端鼠标会通过 emulate_touch_from_mouse 转成触摸,
	# 手机端触摸也不会再产生模拟鼠标事件(已在 project.godot 关闭),
	# 这样一次点击只会染色一次,不会出现"填涂颜色与笔刷颜色不一致"。
	if not (event is InputEventScreenTouch):
		return
	var touch := event as InputEventScreenTouch
	if not touch.pressed:
		return
	accept_event()
	_handle_tap(touch.position)


func _handle_tap(pos: Vector2) -> void:
	# 色板(简单模式恒显示)
	if game.mode == "easy":
		for item in _chip_rects():
			if (item[1] as Rect2).has_point(pos):
				color_selected.emit(int(item[0]))
				return
	# 困难模式:改色弹层(仅改色模式显示)
	if game.mode == "hard" and game.arm_recolor:
		for item in _popup_rects():
			if (item[1] as Rect2).has_point(pos):
				color_selected.emit(int(item[0]))
				return
	# 画刷
	for r in game.rows:
		if row_brush_rect(r).has_point(pos):
			_tap_brush("row", r)
			return
	for c in game.cols:
		if col_brush_rect(c).has_point(pos):
			_tap_brush("col", c)
			return


func _tap_brush(orient: String, index: int) -> void:
	if game.mode == "hard" and game.arm_refresh:
		refresh_requested.emit(orient, index)
	elif game.mode == "hard" and game.arm_recolor:
		recolor_requested.emit(orient, index)
	else:
		paint_requested.emit(orient, index)


# ------------------------------------------------------------------ 绘制
func _draw() -> void:
	if game == null:
		return
	_draw_target()
	_draw_board()
	if game.mode == "easy":
		_draw_palette()
	elif game.arm_recolor:
		_draw_popup()
	_draw_hint_line()
	_draw_brushes()


func _draw_target() -> void:
	var cell: float = minf((TARGET_W - 20.0) / float(game.cols),
		(TARGET_W - 20.0) / float(game.rows))
	cell = minf(cell, 40.0)
	var w: float = cell * game.cols
	var h: float = cell * game.rows
	var y_center: float = BOARD_Y + float(game.rows) * CELL / 2.0
	var box := Rect2(TARGET_X, y_center - h / 2.0 - 30.0, TARGET_W, h + 60.0)
	draw_rect(box, Color(0.18, 0.20, 0.24), true)
	draw_rect(box, Color(0.35, 0.39, 0.45), false, 2.0)
	draw_string(_font, Vector2(TARGET_X + 10.0, box.position.y + 26.0), "目标",
		HORIZONTAL_ALIGNMENT_LEFT, -1, 20, Color(0.78, 0.80, 0.84))
	var ox: float = box.position.x + (TARGET_W - w) / 2.0
	var oy: float = box.position.y + 40.0
	for r in game.rows:
		for c in game.cols:
			var rc := Rect2(ox + c * cell, oy + r * cell, cell, cell)
			draw_rect(rc, game.color_of(int(game.target[r][c])), true)
			draw_rect(rc, Color(0.24, 0.24, 0.24), false, 1.0)


func _draw_board() -> void:
	var bw: float = float(game.cols) * CELL
	var bh: float = float(game.rows) * CELL
	draw_rect(Rect2(BOARD_X - 4.0, BOARD_Y - 4.0, bw + 8.0, bh + 8.0),
		Color(0.82, 0.82, 0.80), true)
	for r in game.rows:
		for c in game.cols:
			var rc := Rect2(BOARD_X + c * CELL, BOARD_Y + r * CELL, CELL, CELL)
			draw_rect(rc, game.color_of(int(game.board[r][c])), true)
			draw_rect(rc, Color(0.24, 0.24, 0.24), false, 2.0)


func _draw_palette() -> void:
	for item in _chip_rects():
		var idx := int(item[0])
		var rc: Rect2 = item[1]
		draw_rect(rc, game.color_of(idx), true)
		if idx == game.cur_color:
			draw_rect(rc, Color(1.0, 0.90, 0.47), false, 3.0)
		else:
			draw_rect(rc, Color(0.27, 0.27, 0.27), false, 2.0)


func _draw_popup() -> void:
	var rects := _popup_rects()
	if rects.is_empty():
		return
	var top: float = (rects[0][1] as Rect2).position.y - 10.0
	var bottom: float = (rects[-1][1] as Rect2).end.y + 10.0
	var panel := Rect2(POPUP_X - 10.0, top, 56.0, bottom - top)
	draw_rect(panel, Color(0.18, 0.20, 0.24), true)
	draw_rect(panel, Color(0.55, 0.59, 0.65), false, 2.0)
	for item in rects:
		var idx := int(item[0])
		var rc: Rect2 = item[1]
		draw_rect(rc, game.color_of(idx), true)
		if idx == game.cur_color:
			draw_rect(rc, Color(1.0, 0.90, 0.47), false, 3.0)
		else:
			draw_rect(rc, Color(0.27, 0.27, 0.27), false, 2.0)


func _draw_hint_line() -> void:
	if game.last_hint.is_empty():
		return
	var a: float = 0.28 + 0.16 * sin(_t * 8.0)
	var orient := String(game.last_hint.orient)
	var index := int(game.last_hint.index)
	var rc: Rect2
	if orient == "row":
		rc = Rect2(BOARD_X, BOARD_Y + index * CELL, game.cols * CELL, CELL)
	else:
		rc = Rect2(BOARD_X + index * CELL, BOARD_Y, CELL, game.rows * CELL)
	draw_rect(rc, Color(1.0, 1.0, 1.0, a), true)


func _draw_brushes() -> void:
	for r in game.rows:
		_draw_brush(row_brush_rect(r), true, r)
	for c in game.cols:
		_draw_brush(col_brush_rect(c), false, c)


func _draw_brush(rc: Rect2, is_row: bool, index: int) -> void:
	var color := Color(0.82, 0.84, 0.87)
	var edge := Color(0.28, 0.31, 0.38)
	if game.mode == "hard":
		color = game.color_of(game.brush_color("row" if is_row else "col", index))
	draw_rect(rc, color, true)
	draw_rect(rc, edge, false, 2.0)
	# 方向箭头
	var pts := PackedVector2Array()
	if is_row:
		pts.append(Vector2(rc.position.x + 9.0, rc.position.y + 9.0))
		pts.append(Vector2(rc.position.x + 9.0, rc.end.y - 9.0))
		pts.append(Vector2(rc.end.x - 7.0, rc.position.y + rc.size.y / 2.0))
	else:
		pts.append(Vector2(rc.position.x + 9.0, rc.position.y + 9.0))
		pts.append(Vector2(rc.end.x - 9.0, rc.position.y + 9.0))
		pts.append(Vector2(rc.position.x + rc.size.x / 2.0, rc.end.y - 7.0))
	draw_colored_polygon(pts, Color(0.38, 0.42, 0.49))
