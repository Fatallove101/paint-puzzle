extends Control
## 方块染色解谜 · Android 版主界面(状态机 + 触控 UI + 存档 + 音效)

const SAVE_PATH := "user://save.json"
const WIN_WAIT := 0.6
const FAIL_WAIT := 1.6
const DEADEND_WAIT := 1.4
const MSG_SEC := 3.0

var game := PPGame.new()
var save_data: Dictionary = {"mode": "easy", "level": 1, "sound": true}
var _scene := "menu"
var _state := "play"          # play / win / fail / deadend
var _timer := 0.0
var _msg := ""
var _msg_t := 0.0
var _pending_mode := "easy"
var _screens: Dictionary = {}
var _snd: Dictionary = {}
var _board: PPBoardView
var _lbl_level: Label
var _lbl_steps: Label
var _lbl_msg: Label
var _btn_undo: Button
var _btn_hint: Button
var _btn_recolor: Button
var _overlay: Button


func _toggle_sound(btn: Button) -> void:
	save_data["sound"] = not bool(save_data.get("sound", true))
	btn.text = "开" if bool(save_data.get("sound", true)) else "关"
	_write_save()


func _on_level_button(num: int) -> void:
	_start_level(num, _pending_mode)


func _ready() -> void:
	_load_save()
	_build_theme()
	_build_screens()
	_goto("menu")


# ------------------------------------------------------------------ 存档
func _load_save() -> void:
	if FileAccess.file_exists(SAVE_PATH):
		var f := FileAccess.open(SAVE_PATH, FileAccess.READ)
		if f != null:
			var txt := f.get_as_text()
			f.close()
			var parsed = JSON.parse_string(txt)
			if typeof(parsed) == TYPE_DICTIONARY:
				save_data = parsed
	if not save_data.has("mode"):
		save_data = {"mode": "easy", "level": 1, "sound": true}


func _write_save() -> void:
	if _scene == "play":
		save_data["mode"] = game.mode
	var f := FileAccess.open(SAVE_PATH, FileAccess.WRITE)
	if f != null:
		f.store_string(JSON.stringify(save_data))
		f.close()


func _has_progress() -> bool:
	return FileAccess.file_exists(SAVE_PATH)


# ------------------------------------------------------------------ 音效
func _play(name: String) -> void:
	if not bool(save_data.get("sound", true)):
		return
	var p: AudioStreamPlayer = _snd.get(name)
	if p != null:
		p.play()


func _setup_audio() -> void:
	for n in ["click", "paint", "win", "fail"]:
		var path := "res://snd/%s.wav" % n
		if ResourceLoader.exists(path):
			var p := AudioStreamPlayer.new()
			p.stream = load(path)
			add_child(p)
			_snd[n] = p


# ------------------------------------------------------------------ 主题
func _build_theme() -> void:
	var f := SystemFont.new()
	f.font_names = PackedStringArray(["Microsoft YaHei", "Noto Sans CJK SC",
		"Source Han Sans SC", "sans-serif"])
	f.allow_system_fallback = true
	var th := Theme.new()
	th.default_font = f
	th.default_font_size = 26
	self.theme = th


# ------------------------------------------------------------------ 控件工具
func _mk_button(text: String, size: Vector2) -> Button:
	var b := Button.new()
	b.text = text
	b.custom_minimum_size = size
	b.focus_mode = Control.FOCUS_NONE
	return b


func _mk_label(text: String, size: int = 26) -> Label:
	var l := Label.new()
	l.text = text
	l.add_theme_font_size_override("font_size", size)
	return l


func _mk_screen() -> Control:
	var c := Control.new()
	c.set_anchors_preset(Control.PRESET_FULL_RECT)
	c.visible = false
	add_child(c)
	return c


# ------------------------------------------------------------------ 各界面
func _build_screens() -> void:
	_setup_audio()
	_build_menu()
	_build_difficulty()
	_build_levels()
	_build_settings()
	_build_play()


func _build_menu() -> void:
	var s := _mk_screen()
	_screens["menu"] = s
	var vb := VBoxContainer.new()
	vb.set_anchors_preset(Control.PRESET_FULL_RECT)
	vb.alignment = BoxContainer.ALIGNMENT_CENTER
	vb.add_theme_constant_override("separation", 16)
	s.add_child(vb)

	var title := _mk_label("方块染色解谜", 56)
	title.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	vb.add_child(title)
	var sub := _mk_label("Paint Puzzle · 染色解谜", 24)
	sub.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	vb.add_child(sub)

	vb.add_child(_mk_label("", 10))
	var b_start := _mk_button("开始游戏", Vector2(300, 64))
	b_start.pressed.connect(func(): _goto("difficulty"))
	vb.add_child(b_start)
	var b_cont := _mk_button("继续游戏", Vector2(300, 64))
	b_cont.disabled = not _has_progress()
	b_cont.pressed.connect(_on_continue)
	vb.add_child(b_cont)
	var b_set := _mk_button("设置", Vector2(300, 64))
	b_set.pressed.connect(func(): _goto("settings"))
	vb.add_child(b_set)
	var b_exit := _mk_button("退出游戏", Vector2(300, 64))
	b_exit.pressed.connect(func(): get_tree().quit())
	vb.add_child(b_exit)


func _on_continue() -> void:
	_pending_mode = String(save_data.get("mode", "easy"))
	_start_level(int(save_data.get("level", 1)), _pending_mode)


func _build_difficulty() -> void:
	var s := _mk_screen()
	_screens["difficulty"] = s
	var title := _mk_label("选择难度", 48)
	title.position = Vector2(0, 90)
	title.size = Vector2(960, 60)
	title.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	s.add_child(title)

	var easy := _mk_button("简单\n(先在色板选颜色)", Vector2(360, 150))
	easy.position = Vector2(70, 300)
	easy.pressed.connect(func(): _pending_mode = "easy"; _goto("levels"))
	s.add_child(easy)

	var hard := _mk_button("困难\n(笔刷颜色随机换)", Vector2(360, 150))
	hard.position = Vector2(530, 300)
	hard.pressed.connect(func(): _pending_mode = "hard"; _goto("levels"))
	s.add_child(hard)

	var back := _mk_button("← 返回", Vector2(140, 56))
	back.position = Vector2(40, 40)
	back.pressed.connect(func(): _goto("menu"))
	s.add_child(back)


func _build_levels() -> void:
	var s := _mk_screen()
	_screens["levels"] = s
	var title := _mk_label("选择关卡(第 1~10 关)", 40)
	title.position = Vector2(0, 80)
	title.size = Vector2(960, 50)
	title.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	s.add_child(title)

	var grid := GridContainer.new()
	grid.columns = 5
	grid.add_theme_constant_override("h_separation", 16)
	grid.add_theme_constant_override("v_separation", 16)
	grid.position = Vector2(218, 240)
	s.add_child(grid)
	for i in range(1, 11):
		var b := _mk_button(str(i), Vector2(96, 96))
		b.pressed.connect(_on_level_button.bind(i))
		grid.add_child(b)

	var back := _mk_button("← 返回", Vector2(140, 56))
	back.position = Vector2(40, 40)
	back.pressed.connect(func(): _goto("difficulty"))
	s.add_child(back)

	var note := _mk_label("第 11 关起:通关后自动随机生成下一关", 22)
	note.position = Vector2(0, 560)
	note.size = Vector2(960, 40)
	note.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	s.add_child(note)


func _build_settings() -> void:
	var s := _mk_screen()
	_screens["settings"] = s
	var title := _mk_label("设置", 48)
	title.position = Vector2(0, 80)
	title.size = Vector2(960, 60)
	title.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	s.add_child(title)

	var lbl := _mk_label("音效:", 30)
	lbl.position = Vector2(300, 220)
	s.add_child(lbl)
	var toggle := _mk_button("", Vector2(120, 56))
	toggle.position = Vector2(420, 212)
	toggle.text = "开" if bool(save_data.get("sound", true)) else "关"
	toggle.pressed.connect(_toggle_sound.bind(toggle))
	s.add_child(toggle)

	var tips := [
		"目标:在限定步数内,把棋盘染成与左侧目标图案完全一致即通关。",
		"操作:先选颜色(简单难度),再点行/列画刷染色;每步消耗 1 点。",
		"提示:每步都可点一次提示,给出最佳下一步,跟提示可通关。",
		"撤销:点\"撤销\"退回上一步。",
		"难度:简单=色板自选颜色;困难=笔刷随机换色。",
		"困难模式:点[改色]弹出颜色,先选色再点画刷换色,次数=总步数一半。",
	]
	var y := 320.0
	for t in tips:
		var l := _mk_label(t, 22)
		l.position = Vector2(90, y)
		s.add_child(l)
		y += 38.0

	var back := _mk_button("← 返回", Vector2(140, 56))
	back.position = Vector2(40, 40)
	back.pressed.connect(func(): _goto("menu"))
	s.add_child(back)


func _build_play() -> void:
	var s := _mk_screen()
	_screens["play"] = s

	# 先加棋盘视图(会被后加的上层按钮覆盖命中)
	_board = PPBoardView.new()
	_board.set_anchors_preset(Control.PRESET_FULL_RECT)
	_board.paint_requested.connect(_on_paint)
	_board.recolor_requested.connect(_on_recolor)
	_board.color_selected.connect(_on_color_selected)
	s.add_child(_board)

	_lbl_level = _mk_label("", 26)
	_lbl_level.position = Vector2(50, 28)
	s.add_child(_lbl_level)
	_lbl_steps = _mk_label("", 26)
	_lbl_steps.position = Vector2(290, 28)
	s.add_child(_lbl_steps)

	_btn_undo = _mk_button("撤销", Vector2(106, 44))
	_btn_undo.position = Vector2(524, 24)
	_btn_undo.pressed.connect(_on_undo)
	s.add_child(_btn_undo)

	_btn_hint = _mk_button("提示", Vector2(106, 44))
	_btn_hint.position = Vector2(634, 24)
	_btn_hint.pressed.connect(_on_hint)
	s.add_child(_btn_hint)

	_btn_recolor = _mk_button("改色", Vector2(106, 44))
	_btn_recolor.position = Vector2(744, 24)
	_btn_recolor.pressed.connect(_on_recolor_button)
	s.add_child(_btn_recolor)

	var b_retry := _mk_button("重试", Vector2(106, 44))
	b_retry.position = Vector2(854, 24)
	b_retry.pressed.connect(func(): _reset_level())
	s.add_child(b_retry)

	var b_menu := _mk_button("菜单", Vector2(90, 44))
	b_menu.position = Vector2(420, 24)
	b_menu.pressed.connect(_to_menu)
	s.add_child(b_menu)

	_lbl_msg = _mk_label("", 24)
	_lbl_msg.position = Vector2(0, 640)
	_lbl_msg.size = Vector2(960, 40)
	_lbl_msg.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	s.add_child(_lbl_msg)

	_overlay = _mk_button("", Vector2(960, 720))
	_overlay.position = Vector2.ZERO
	_overlay.visible = false
	_overlay.pressed.connect(_on_overlay)
	s.add_child(_overlay)


# ------------------------------------------------------------------ 场景切换
func _goto(name: String) -> void:
	_scene = name
	for k in _screens.keys():
		(_screens[k] as Control).visible = (k == name)
	if name == "play":
		_refresh_play()


func _to_menu() -> void:
	if _scene == "play":
		save_data["mode"] = game.mode
		save_data["level"] = game.level_num
		_write_save()
	_goto("menu")
	# 继续游戏按钮可用性
	var menu: Control = _screens["menu"]
	for c in menu.get_children():
		if c is VBoxContainer:
			for b in c.get_children():
				if b is Button and (b as Button).text == "继续游戏":
					(b as Button).disabled = not _has_progress()


# ------------------------------------------------------------------ 对局
func _start_level(num: int, mode: String) -> void:
	game.start(num, mode)
	_state = "play"
	_timer = 0.0
	_msg = ""
	_msg_t = 0.0
	save_data["mode"] = mode
	save_data["level"] = num
	_write_save()
	_board.set_game(game)
	_goto("play")


func _reset_level() -> void:
	game.reset()
	_state = "play"
	_timer = 0.0
	_msg = ""
	_msg_t = 0.0
	_board.set_game(game)
	_refresh_play()


func _refresh_play() -> void:
	_lbl_level.text = "第 %d 关 · %s" % [game.level_num,
		"简单" if game.mode == "easy" else "困难"]
	_lbl_steps.text = "剩余步数:%d" % game.steps_left()
	_btn_undo.disabled = not game.can_undo()
	_btn_hint.disabled = game.hints_left() <= 0
	_btn_hint.text = "提示 ×%d" % game.hints_left()
	_btn_recolor.visible = (game.mode == "hard")
	_btn_recolor.disabled = game.recolor_left <= 0
	_btn_recolor.text = "改色 ×%d" % game.recolor_left
	_overlay.visible = false
	_board.queue_redraw()


func _on_paint(orient: String, index: int) -> void:
	if _state != "play":
		return
	if not game.paint(orient, index):
		return
	_play("click")
	_play("paint")
	_after_action()


func _on_recolor(orient: String, index: int) -> void:
	if _state != "play":
		return
	if game.recolor(orient, index):
		_play("click")
		_show_msg("已换色,剩余 %d 次(再点[改色]继续)" % game.recolor_left)
		_refresh_play()
	else:
		_show_msg("该画刷已是这个颜色")


func _on_color_selected(idx: int) -> void:
	game.cur_color = idx
	_play("click")
	_board.queue_redraw()


func _on_recolor_button() -> void:
	if game.mode != "hard" or game.recolor_left <= 0:
		return
	game.arm_recolor = not game.arm_recolor
	_play("click")
	if game.arm_recolor:
		_show_msg("改色模式:先点颜色,再点要改的画刷")
	_refresh_play()


func _on_undo() -> void:
	if _state not in ["play", "fail"]:
		return
	if game.undo():
		_state = "play"
		_timer = 0.0
		_play("click")
		_show_msg("已撤销上一步")
		_refresh_play()


func _on_hint() -> void:
	if _state != "play":
		return
	var r := game.use_hint()
	if r.is_empty():
		return
	if r.has("dead_end"):
		_state = "deadend"
		_timer = DEADEND_WAIT
		_play("fail")
		_show_msg("当前局面已无法达成目标,即将自动重试…")
		return
	var op: Dictionary = r.move
	var where := ""
	if op.orient == "row":
		where = "第%d行" % (int(op.index) + 1)
	else:
		where = "第%d列" % (int(op.index) + 1)
	_play("click")
	_show_msg("提示:点击%s画刷(颜色已选好)" % where)
	_refresh_play()


func _after_action() -> void:
	_refresh_play()
	if game.matched():
		_state = "win"
		_timer = WIN_WAIT
		_play("win")
	elif game.steps_left() <= 0:
		_state = "fail"
		_timer = FAIL_WAIT
		_play("fail")


func _on_overlay() -> void:
	if _state == "win":
		_start_level(game.level_num + 1, game.mode)


func _show_msg(t: String) -> void:
	_msg = t
	_msg_t = MSG_SEC


func _process(delta: float) -> void:
	if _scene != "play":
		return
	if _msg_t > 0.0:
		_msg_t = maxf(0.0, _msg_t - delta)
	_lbl_msg.text = _msg
	_lbl_msg.modulate.a = clampf(_msg_t / MSG_SEC * 1.6, 0.0, 1.0)

	if _state == "win":
		_timer -= delta
		_overlay.visible = true
		_overlay.text = "通关!点击进入下一关"
	elif _state == "fail":
		_timer -= delta
		_overlay.visible = true
		_overlay.text = "步数耗尽,即将重置…"
		if _timer <= 0.0:
			_reset_level()
	elif _state == "deadend":
		_timer -= delta
		_overlay.visible = true
		_overlay.text = "当前局面已无法达成目标,即将自动重试…"
		if _timer <= 0.0:
			_reset_level()
	else:
		_overlay.visible = false
	_lbl_steps.text = "剩余步数:%d" % game.steps_left()
