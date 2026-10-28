class_name Coin
extends Area2D
## Dong xu: bien mat khi nhan vat cham vao va phat tin hieu "collected".

signal collected

var _t := 0.0
var _sprite: Sprite2D


func _ready() -> void:
	_sprite = Sprite2D.new()
	_sprite.texture = load("res://assets/coin.png")
	add_child(_sprite)
	var shape := CollisionShape2D.new()
	var circle := CircleShape2D.new()
	circle.radius = 8.0
	shape.shape = circle
	add_child(shape)
	body_entered.connect(_on_body_entered)


func _process(delta: float) -> void:
	_t += delta
	_sprite.position.y = sin(_t * 4.0) * 2.0  # nhun nhe


func _on_body_entered(body: Node) -> void:
	if body is Player:
		collected.emit()
		queue_free()
