class_name Player
extends CharacterBody2D
## Nhan vat: di chuyen trai/phai, nhay. Toan bo node con duoc tao bang code.

signal jumped

const SPEED := 150.0
const JUMP_VELOCITY := -370.0
const GRAVITY := 900.0

var enabled := true
var _sprite: Sprite2D


func _ready() -> void:
	_sprite = Sprite2D.new()
	_sprite.texture = load("res://assets/player.png")
	add_child(_sprite)

	var shape := CollisionShape2D.new()
	var rect := RectangleShape2D.new()
	rect.size = Vector2(20, 30)
	shape.shape = rect
	add_child(shape)

	var cam := Camera2D.new()
	cam.limit_left = 0
	cam.limit_right = 1280
	cam.limit_top = 0
	cam.limit_bottom = 360
	add_child(cam)


func _physics_process(delta: float) -> void:
	if not enabled:
		velocity.x = 0.0
		return
	if not is_on_floor():
		velocity.y += GRAVITY * delta
	if Input.is_action_just_pressed("jump") and is_on_floor():
		velocity.y = JUMP_VELOCITY
		jumped.emit()
	var dir := Input.get_axis("move_left", "move_right")
	velocity.x = dir * SPEED
	if dir != 0.0:
		_sprite.flip_h = dir < 0.0
	move_and_slide()
