class_name Progress
extends RefCounted
## Luu tien trinh (ky luc) vao user://. Logic thuan, de kiem thu headless.

const DEFAULT_PATH := "user://coin_dash.cfg"


## Ky luc moi neu nhieu xu hon, hoac bang xu nhung con nhieu thoi gian hon.
static func is_better(score: int, time_left: float, best_score: int, best_time_left: float) -> bool:
	if score != best_score:
		return score > best_score
	return time_left > best_time_left


static func load_best(path: String = DEFAULT_PATH) -> Dictionary:
	var cfg := ConfigFile.new()
	if cfg.load(path) != OK:
		return {"score": 0, "time_left": 0.0}
	return {
		"score": int(cfg.get_value("progress", "best_score", 0)),
		"time_left": float(cfg.get_value("progress", "best_time_left", 0.0)),
	}


## Tra ve true neu da ghi ky luc moi.
static func record(score: int, time_left: float, path: String = DEFAULT_PATH) -> bool:
	var best := load_best(path)
	if not is_better(score, time_left, best["score"], best["time_left"]):
		return false
	var cfg := ConfigFile.new()
	cfg.set_value("progress", "best_score", score)
	cfg.set_value("progress", "best_time_left", time_left)
	return cfg.save(path) == OK
