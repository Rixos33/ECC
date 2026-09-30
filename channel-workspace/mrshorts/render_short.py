#!/usr/bin/env python3
"""Render a vertical Short from a JSON script: python3 render_short.py scripts/01-sky-not-violet.json out/
Needs ffmpeg, espeak-ng (placeholder voice), Pillow, DejaVu fonts."""
import colorsys, json, math, os, subprocess, sys, tempfile, wave
from PIL import Image, ImageDraw, ImageFont

W, H = 1080, 1920
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
PAD = 0.35


def font(size):
    return ImageFont.truetype(FONT, size)


def spectrum(t):
    r, g, b = colorsys.hsv_to_rgb(0.78 - 0.78 * t, 1, 1)
    return int(r * 255), int(g * 255), int(b * 255)


def wrap(d, text, f, maxw):
    out, cur = [], ""
    for word in text.split():
        trial = (cur + " " + word).strip()
        if d.textlength(trial, font=f) <= maxw:
            cur = trial
        else:
            out.append(cur)
            cur = word
    out.append(cur)
    return out


def scene(kind, text, handle, path):
    img = Image.new("RGB", (W, H))
    d = ImageDraw.Draw(img)
    top, bot = ((20, 60, 140), (130, 190, 240)) if kind in ("blue", "loop") else ((10, 10, 40), (40, 30, 90))
    for y in range(H):
        k = y / H
        d.line([(0, y), (W, y)], fill=tuple(int(top[c] + (bot[c] - top[c]) * k) for c in range(3)))
    cy = 620
    if kind == "hook":
        for x in range(120, 960):
            d.line([(x, cy - 60), (x, cy + 60)], fill=spectrum((x - 120) / 840))
        d.text((W // 2, cy + 130), "violet -> red", font=font(44), fill="white", anchor="mm")
    elif kind == "scatter":
        d.ellipse([W // 2 - 90, cy - 300, W // 2 + 90, cy - 120], fill=(255, 220, 80))
        for n, (c, amp) in enumerate([(spectrum(0), 5), (spectrum(0.25), 3), (spectrum(1), 1)]):
            for x in range(80, 1000, 4):
                y = cy + n * 120 + int(amp * 12 * math.sin(x / (60 / amp)))
                d.ellipse([x - 3, y - 3, x + 3, y + 3], fill=c)
        d.text((W // 2, cy + 420), "short waves bounce around more", font=font(40), fill="white", anchor="mm")
    elif kind == "violet":
        d.rectangle([140, cy - 50, 940, cy + 50], fill=(40, 40, 70))
        d.rectangle([140, cy - 50, 840, cy + 50], fill=spectrum(0))
        d.text((W // 2, cy + 110), "violet: scatters the most", font=font(46), fill="white", anchor="mm")
    elif kind == "eye":
        for n, (lab, v) in enumerate([("sun output", 0.55), ("not absorbed", 0.6), ("eye sensitivity", 0.3)]):
            y = cy - 140 + n * 150
            d.text((100, y - 55), lab, font=font(40), fill="white")
            d.rectangle([100, y, 980, y + 50], fill=(50, 50, 80))
            d.rectangle([100, y, 100 + int(880 * v), y + 50], fill=spectrum(0))
        d.text((W // 2, cy + 380), "less violet reaches your eyes", font=font(42), fill="white", anchor="mm")
    else:
        d.ellipse([W // 2 - 200, cy - 200, W // 2 + 200, cy + 200], fill=(70, 150, 255))
        d.text((W // 2, cy), "BLUE" if kind == "blue" else "?", font=font(110 if kind == "blue" else 200), fill="white", anchor="mm")
    f = font(62)
    y = 1150
    for line in wrap(d, text, f, 940):
        d.text((W // 2, y), line, font=f, fill="white", anchor="mm", stroke_width=4, stroke_fill="black")
        y += 82
    d.text((W // 2, 1800), handle, font=font(36), fill="white", anchor="mm")
    img.save(path)


def duration(path):
    with wave.open(path) as w:
        return w.getnframes() / w.getframerate()


def run(cmd):
    subprocess.run(cmd, check=True)


def main():
    spec = json.load(open(sys.argv[1]))
    out = os.path.abspath(sys.argv[2] if len(sys.argv) > 2 else ".")
    os.makedirs(out, exist_ok=True)
    lines = spec["lines"]
    with tempfile.TemporaryDirectory() as tmp:
        durs = []
        for i, ln in enumerate(lines):
            wav = os.path.join(tmp, f"a{i}.wav")
            run(["espeak-ng", "-v", "en-us", "-s", "150", "-p", "45", "-w", wav, ln["text"]])
            scene(ln["kind"], ln["text"], spec["handle"], os.path.join(tmp, f"f{i}.png"))
            durs.append(duration(wav) + PAD)
        with open(os.path.join(tmp, "list.txt"), "w") as fh:
            for i, s in enumerate(durs):
                fh.write(f"file 'f{i}.png'\nduration {s:.2f}\n")
            fh.write(f"file 'f{len(durs) - 1}.png'\n")
        inputs = [a for i in range(len(lines)) for a in ("-i", os.path.join(tmp, f"a{i}.wav"))]
        graph = "".join(f"[{i}:a]apad=pad_dur={PAD}[p{i}];" for i in range(len(lines)))
        graph += "".join(f"[p{i}]" for i in range(len(lines))) + f"concat=n={len(lines)}:v=0:a=1[a]"
        voice = os.path.join(tmp, "voice.wav")
        run(["ffmpeg", "-y", "-loglevel", "error", *inputs, "-filter_complex", graph, "-map", "[a]", voice])
        target = os.path.join(out, spec["id"] + ".mp4")
        run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", os.path.join(tmp, "list.txt"),
             "-i", voice, "-vf", "fps=30,format=yuv420p", "-c:v", "libx264", "-c:a", "aac", "-shortest", target])
    print(target, f"{sum(durs):.1f}s")


if __name__ == "__main__":
    main()
