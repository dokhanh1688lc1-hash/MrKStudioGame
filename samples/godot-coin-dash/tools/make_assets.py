"""Tao toan bo tai san cua Coin Dash bang code (khong dung tai san ben thu ba).
Chay: python tools/make_assets.py   (can Pillow)  ->  ghi vao ../assets/
Ket qua duoc phat hanh theo CC0 1.0."""
import math
import struct
import wave
from pathlib import Path

from PIL import Image, ImageDraw

OUT = Path(__file__).resolve().parent.parent / "assets"
OUT.mkdir(exist_ok=True)


def player():
    im = Image.new("RGBA", (24, 32), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rectangle([4, 10, 19, 29], fill=(59, 130, 246, 255), outline=(30, 64, 175, 255))      # than
    d.rectangle([5, 2, 18, 12], fill=(253, 224, 171, 255), outline=(146, 101, 54, 255))     # dau
    d.rectangle([8, 5, 9, 7], fill=(20, 20, 20, 255))
    d.rectangle([14, 5, 15, 7], fill=(20, 20, 20, 255))
    d.rectangle([4, 0, 19, 3], fill=(220, 38, 38, 255))                                      # mu
    d.rectangle([5, 29, 10, 31], fill=(40, 40, 40, 255))
    d.rectangle([13, 29, 18, 31], fill=(40, 40, 40, 255))
    im.save(OUT / "player.png")


def coin():
    im = Image.new("RGBA", (16, 16), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.ellipse([1, 1, 14, 14], fill=(250, 204, 21, 255), outline=(161, 98, 7, 255))
    d.ellipse([4, 4, 11, 11], outline=(202, 138, 4, 255))
    d.line([6, 3, 6, 5], fill=(254, 240, 138, 255))
    im.save(OUT / "coin.png")


def tile():
    im = Image.new("RGBA", (32, 32), (120, 78, 45, 255))
    d = ImageDraw.Draw(im)
    d.rectangle([0, 0, 31, 7], fill=(74, 163, 84, 255))
    d.line([0, 8, 31, 8], fill=(52, 120, 62, 255))
    for x, y in ((6, 16), (20, 22), (12, 27), (27, 14)):
        d.rectangle([x, y, x + 2, y + 1], fill=(92, 58, 32, 255))
    im.save(OUT / "tile.png")


def background():
    w, h = 320, 180
    im = Image.new("RGBA", (w, h))
    px = im.load()
    for y in range(h):
        t = y / (h - 1)
        c = (int(135 + 90 * t), int(190 + 40 * t), int(235 + 10 * t), 255)
        for x in range(w):
            px[x, y] = c
    d = ImageDraw.Draw(im)
    for cx, cy in ((50, 40), (150, 28), (250, 52)):
        for dx, dy, r in ((0, 0, 14), (14, 4, 11), (-14, 5, 10)):
            d.ellipse([cx + dx - r, cy + dy - r, cx + dx + r, cy + dy + r], fill=(255, 255, 255, 235))
    d.polygon([(0, 180), (60, 120), (120, 180)], fill=(110, 160, 130, 255))
    d.polygon([(90, 180), (170, 105), (250, 180)], fill=(96, 146, 118, 255))
    d.polygon([(200, 180), (270, 125), (320, 180)], fill=(110, 160, 130, 255))
    im.save(OUT / "background.png")


def tone(name, notes, vol=0.4, rate=22050):
    frames = bytearray()
    for freq, dur in notes:
        n = int(rate * dur)
        for i in range(n):
            env = min(1.0, i / 200) * (1 - i / n)
            frames += struct.pack("<h", int(32767 * vol * env * math.sin(2 * math.pi * freq * i / rate)))
    with wave.open(str(OUT / name), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(bytes(frames))


if __name__ == "__main__":
    player(); coin(); tile(); background()
    tone("coin.wav", [(988, 0.07), (1319, 0.12)])
    tone("jump.wav", [(330, 0.05), (440, 0.05), (587, 0.07)], vol=0.3)
    print("OK:", sorted(p.name for p in OUT.iterdir()))
