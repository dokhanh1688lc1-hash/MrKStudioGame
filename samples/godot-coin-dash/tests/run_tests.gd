extends SceneTree
## Chay: godot --headless --path . --script tests/run_tests.gd
## Thoat voi ma 0 neu tat ca dat, 1 neu co test that bai.

var _failed := 0


func _check(name: String, ok: bool) -> void:
	if ok:
		print("PASS  ", name)
	else:
		print("FAIL  ", name)
		_failed += 1


func _init() -> void:
	_check("nhieu xu hon la ky luc", Progress.is_better(5, 10.0, 4, 50.0))
	_check("it xu hon khong phai ky luc", not Progress.is_better(3, 50.0, 4, 1.0))
	_check("bang xu, con nhieu thoi gian hon la ky luc", Progress.is_better(12, 30.0, 12, 20.0))
	_check("bang het khong phai ky luc", not Progress.is_better(12, 20.0, 12, 20.0))

	var path := "user://coin_dash_test.cfg"
	DirAccess.remove_absolute(ProjectSettings.globalize_path(path))
	_check("chua co file -> ky luc 0", Progress.load_best(path)["score"] == 0)
	_check("ghi ky luc dau tien", Progress.record(7, 12.5, path))
	var b := Progress.load_best(path)
	_check("doc lai dung diem", b["score"] == 7)
	_check("doc lai dung thoi gian", is_equal_approx(b["time_left"], 12.5))
	_check("khong ghi de ky luc tot hon", not Progress.record(5, 40.0, path))
	_check("ky luc van la 7", Progress.load_best(path)["score"] == 7)
	DirAccess.remove_absolute(ProjectSettings.globalize_path(path))

	var main_script: GDScript = load("res://scripts/main.gd")
	_check("main.gd nap duoc", main_script != null)
	for res in ["player.png", "coin.png", "tile.png", "background.png", "coin.wav", "jump.wav"]:
		_check("co tai san " + res, ResourceLoader.exists("res://assets/" + res))

	print("Tong so test that bai: ", _failed)
	quit(1 if _failed > 0 else 0)
