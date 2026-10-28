extends Node2D
## Coin Dash: nhat het xu trong 60 giay. Man choi duoc dung hoan toan bang code de de doc, de sua.

const WORLD_W := 1280
const WORLD_H := 360
const TIME_LIMIT := 60.0

# Nen dat va cac bac: [x giua, y giua, rong, cao]
const PLATFORMS := [
	[640, 350, 1280, 20],
	[200, 280, 96, 12], [360, 230, 96, 12], [520, 280, 96, 12],
	[700, 220, 128, 12], [900, 270, 96, 12], [1060, 210, 96, 12],
]
const COINS := [
	Vector2(100, 320), Vector2(200, 260), Vector2(360, 210), Vector2(520, 260),
	Vector2(440, 320), Vector2(660, 200), Vector2(740, 200), Vector2(900, 250),
	Vector2(820, 320), Vector2(1060, 190), Vector2(1000, 320), Vector2(1200, 320),
]

var player: Player
var best: Dictionary = {"score": 0, "time_left": 0.0}
var score := 0
var time_left := TIME_LIMIT
var finished := false
var _label: Label
var _msg: Label
var _sfx_coin: AudioStreamPlayer
var _sfx_jump: AudioStreamPlayer


func _ready() -> void:
	best = Progress.load_best()
	_setup_input()
	_build_background()
	for p in PLATFORMS:
		_add_platform(Vector2(p[0], p[1]), Vector2(p[2], p[3]))
	_add_wall(-8)
	_add_wall(WORLD_W + 8)
	_build_player()
	for pos in COINS:
		var c := Coin.new()
		c.position = pos
		c.collected.connect(_on_coin)
		add_child(c)
	_build_hud()
	_sfx_coin = _make_sfx("res://assets/coin.wav")
	_sfx_jump = _make_sfx("res://assets/jump.wav")
	player.jumped.connect(func(): _sfx_jump.play())


func _process(delta: float) -> void:
	if Input.is_action_just_pressed("restart"):
		get_tree().reload_current_scene()
		return
	if finished:
		return
	time_left = maxf(0.0, time_left - delta)
	_label.text = "Xu: %d/%d   Thoi gian: %d   Ky luc: %d" % [score, COINS.size(), ceili(time_left), best["score"]]
	if time_left <= 0.0:
		_finish("Het gio! Diem: %d/%d\nNhan R de choi lai" % [score, COINS.size()])


func _on_coin() -> void:
	score += 1
	_sfx_coin.play()
	if score >= COINS.size():
		_finish("Chien thang! Con %d giay\nNhan R de choi lai" % ceili(time_left))


func _finish(text: String) -> void:
	finished = true
	player.enabled = false
	var new_record := Progress.record(score, time_left)
	if new_record:
		best = Progress.load_best()
		text += "\nKy luc moi!"
	_msg.text = text
	_msg.visible = true


# ---------- xay dung man choi ----------
func _setup_input() -> void:
	_add_action("move_left", [KEY_LEFT, KEY_A])
	_add_action("move_right", [KEY_RIGHT, KEY_D])
	_add_action("jump", [KEY_SPACE, KEY_UP, KEY_W])
	_add_action("restart", [KEY_R])


func _add_action(action: String, keys: Array) -> void:
	if not InputMap.has_action(action):
		InputMap.add_action(action)
	for k in keys:
		var ev := InputEventKey.new()
		ev.physical_keycode = k
		InputMap.action_add_event(action, ev)


func _build_background() -> void:
	var bg := Sprite2D.new()
	bg.texture = load("res://assets/background.png")
	bg.centered = false
	bg.scale = Vector2(float(WORLD_W) / bg.texture.get_width(), float(WORLD_H) / bg.texture.get_height())
	bg.z_index = -10
	add_child(bg)


func _add_platform(center: Vector2, size: Vector2) -> void:
	var body := StaticBody2D.new()
	body.position = center
	var shape := CollisionShape2D.new()
	var rect := RectangleShape2D.new()
	rect.size = size
	shape.shape = rect
	body.add_child(shape)
	var tile := Sprite2D.new()
	tile.texture = load("res://assets/tile.png")
	tile.texture_repeat = CanvasItem.TEXTURE_REPEAT_ENABLED
	tile.region_enabled = true
	tile.region_rect = Rect2(0, 0, size.x, size.y)
	body.add_child(tile)
	add_child(body)


func _add_wall(x: float) -> void:
	var body := StaticBody2D.new()
	body.position = Vector2(x, WORLD_H / 2.0)
	var shape := CollisionShape2D.new()
	var rect := RectangleShape2D.new()
	rect.size = Vector2(16, WORLD_H * 2)
	shape.shape = rect
	body.add_child(shape)
	add_child(body)


func _build_player() -> void:
	player = Player.new()
	player.position = Vector2(60, 300)
	add_child(player)


func _build_hud() -> void:
	var layer := CanvasLayer.new()
	add_child(layer)
	_label = Label.new()
	_label.position = Vector2(8, 6)
	layer.add_child(_label)
	_msg = Label.new()
	_msg.visible = false
	_msg.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	_msg.set_anchors_and_offsets_preset(Control.PRESET_CENTER)
	_msg.grow_horizontal = Control.GROW_DIRECTION_BOTH
	layer.add_child(_msg)


func _make_sfx(path: String) -> AudioStreamPlayer:
	var p := AudioStreamPlayer.new()
	p.stream = load(path)
	add_child(p)
	return p
