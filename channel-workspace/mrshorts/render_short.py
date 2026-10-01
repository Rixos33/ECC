#!/usr/bin/env python3
"""Render a vertical YouTube Short: flat-vector animated scenes, AI narration, word-synced
captions, procedural music bed + SFX, loudness-normalised, small H.264 file.

    .venv/bin/python render_short.py scripts/02-*.json out/
    .venv/bin/python render_short.py "scripts/*.json" out/ --voice en-US-BrianMultilingualNeural

Voice backends (--tts): edge (default: free Microsoft neural voices, needs network),
elevenlabs (needs ELEVENLABS_API_KEY; --voice is the voice id), say (macOS offline fallback).
Script schema: see README.md in this folder.
"""
import argparse, asyncio, base64, glob, hashlib, json, math, os, random, re, subprocess, sys, tempfile, urllib.request, wave
import numpy as np
import skia
import art, audio

W, H, FPS = 1080, 1920, 30
VIS_CY = 760        # visual focus (above captions, clear of the Shorts UI)
CAP_Y = 1330        # caption baseline block
SAFE_W = 800        # caption width: clear of the Shorts action buttons on the right
PUNCH = 0.22        # hard cut + punch-in duration (s)
PALETTES = {  # bg top, bg bottom, accent: vivid duotone gradients
    "violet": ((30, 14, 70), (110, 50, 170), "yellow"),
    "blue": ((10, 30, 90), (40, 110, 200), "cyan"),
    "teal": ((8, 50, 70), (20, 140, 150), "yellow"),
    "green": ((10, 50, 40), (40, 130, 80), "yellow"),
    "orange": ((70, 25, 80), (235, 110, 70), "yellow"),
    "red": ((60, 10, 50), (200, 50, 70), "yellow"),
    "pink": ((60, 20, 90), (220, 90, 160), "yellow"),
    "navy": ((12, 16, 48), (40, 50, 120), "yellow"),
}
LEGACY = {"big", "question", "bars", "list", "versus", "timeline", "spectrum"}


class RenderError(Exception):
    pass


def run(cmd, **kw):
    return subprocess.run(cmd, check=True, stdin=subprocess.DEVNULL, **kw)


# ---------- voice ----------

def even_words(text, dur):
    words = text.split()
    total = sum(len(w) + 1 for w in words)
    t, out = 0.05, []
    for w in words:
        d = (dur - 0.1) * (len(w) + 1) / total
        out.append((w, t, d))
        t += d
    return out


async def _edge(text, voice, rate, pitch, path):
    import edge_tts
    words = []
    com = edge_tts.Communicate(text, voice, rate=rate, pitch=pitch, boundary="WordBoundary")
    with open(path, "wb") as fh:
        async for ch in com.stream():
            if ch["type"] == "audio":
                fh.write(ch["data"])
            elif ch["type"] == "WordBoundary":
                words.append((ch["text"], ch["offset"] / 1e7, ch["duration"] / 1e7))
    return words


def tts_elevenlabs(text, voice, path):
    req = urllib.request.Request(
        f"https://api.elevenlabs.io/v1/text-to-speech/{voice}/with-timestamps",
        data=json.dumps({"text": text, "model_id": "eleven_multilingual_v2",
                         "voice_settings": {"stability": 0.45, "similarity_boost": 0.75}}).encode(),
        headers={"xi-api-key": os.environ["ELEVENLABS_API_KEY"], "Content-Type": "application/json"})
    res = json.load(urllib.request.urlopen(req, timeout=120))
    with open(path, "wb") as fh:
        fh.write(base64.b64decode(res["audio_base64"]))
    al = res["alignment"]
    words, cur, start, end = [], "", None, 0.0
    for ch, s, e in zip(al["characters"], al["character_start_times_seconds"], al["character_end_times_seconds"]):
        if ch.isspace():
            if cur:
                words.append((cur, start, end - start))
            cur, start = "", None
        else:
            cur, start, end = cur + ch, s if start is None else start, e
    if cur:
        words.append((cur, start, end - start))
    return words


def read_wav(path):
    with wave.open(path) as w:
        return np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float64) / 32768


def synth(text, args, stem, cache_dir, voice=None, rate=None, pitch=None):
    """Return (mono samples @48k, [(word, start, dur)]). Cached by backend/voice/text."""
    if voice or rate or pitch:
        args = argparse.Namespace(**{**vars(args), "voice": voice or args.voice, "rate": rate or args.rate,
                                     "pitch": pitch or args.pitch})
    key = hashlib.sha1(json.dumps([args.tts, args.voice, args.rate, args.pitch, text]).encode()).hexdigest()[:24]
    cache = os.path.join(cache_dir, f"{args.tts}_{key}.json") if cache_dir else None
    wav = stem + ".wav"
    if cache and os.path.exists(cache) and os.path.exists(cache[:-5] + ".wav"):
        words = [tuple(w) for w in json.load(open(cache))]
        return read_wav(cache[:-5] + ".wav"), words
    if args.tts == "edge":
        raw = stem + ".mp3"
        words = asyncio.run(_edge(text, args.voice, args.rate, args.pitch, raw))
    elif args.tts == "elevenlabs":
        raw = stem + ".mp3"
        words = tts_elevenlabs(text, args.voice, raw)
    else:
        raw, txt = stem + ".aiff", stem + ".txt"
        open(txt, "w").write(text)  # -f avoids narration being parsed as `say` options
        run(["say", *(["-v", args.voice] if args.voice else []), "-o", raw, "-f", txt])
        words = None
    run(["ffmpeg", "-nostdin", "-y", "-loglevel", "error", "-i", raw, "-ar", str(audio.SR), "-ac", "1",
         "-sample_fmt", "s16", wav])
    samples = read_wav(wav)
    words = words or even_words(text, len(samples) / audio.SR)
    if cache:  # wav first, json last, each via an atomic rename (parallel renders share the cache)
        os.makedirs(cache_dir, exist_ok=True)
        tmp_wav, tmp_json = f"{cache[:-5]}.{os.getpid()}.tmp.wav", f"{cache}.{os.getpid()}.tmp"
        run(["cp", wav, tmp_wav])
        os.replace(tmp_wav, cache[:-5] + ".wav")
        with open(tmp_json, "w") as fh:
            json.dump(words, fh)
        os.replace(tmp_json, cache)
    return samples, words


# ---------- visuals ----------

def ease_out_back(x):
    x = max(0.0, min(1.0, x))
    return 1 + 2.70158 * (x - 1) ** 3 + 1.70158 * (x - 1) ** 2


def ease_io(x):
    x = max(0.0, min(1.0, x))
    return x * x * (3 - 2 * x)


class Background:
    def __init__(self, palette, style, seed, total, ground=None):
        self.top, self.bot, self.accent = palette
        self.style, self.total = style, total
        self.ground = ground or {"space": "planet", "sky": "hill"}.get(style, "hill")
        if style == "sky":  # daytime: saturated blue sky, light at the horizon
            self.top, self.bot = (40, 110, 210), (150, 205, 245)
        rnd = random.Random(seed)
        self.craters = [(rnd.uniform(0, W + 400), rnd.uniform(1330, 1850), rnd.uniform(25, 70)) for _ in range(9)]
        self.stars = [(rnd.uniform(0, W), rnd.uniform(0, H * 1.3), rnd.uniform(1.5, 4.5), rnd.uniform(0, 6.3),
                       rnd.choice((0.3, 0.6, 1.0))) for _ in range(110)]
        self.blobs = [(rnd.uniform(0, W), rnd.uniform(200, H - 300), rnd.uniform(260, 420), rnd.uniform(0, 6.3))
                      for _ in range(3)]
        self.bokeh = [(rnd.uniform(0, W), rnd.uniform(0, H), rnd.uniform(18, 46), rnd.uniform(30, 70),
                       rnd.choice(("white", self.accent))) for _ in range(7)]
        self.shader = skia.GradientShader.MakeLinear(
            [skia.Point(0, 0), skia.Point(0, H)], [art.col(self.top), art.col(self.bot)])

    def draw(self, c, t):
        c.drawPaint(skia.Paint(Shader=self.shader))
        for x, y, r, ph in self.blobs:
            c.drawCircle(x + 90 * math.sin(t * 0.2 + ph), y + 70 * math.cos(t * 0.17 + ph), r,
                         art.paint(self.accent, 26, blur=r * 0.5))
        if self.style == "space":
            for x, y, r, ph, depth in self.stars:
                yy = (y - t * 18 * depth) % (H * 1.3) - H * 0.15
                a = int(120 + 110 * math.sin(t * 2 + ph)) * depth
                c.drawCircle(x, yy, r * depth, art.paint("white", a))
        elif self.style == "sky":
            for i, (x, y, r, ph) in enumerate(self.blobs[:2]):
                cx = (x + t * 14 * (i + 1)) % (W + 500) - 250
                cy = 150 + i * 90
                for dx, dy, rr in ((0, 0, 60), (65, 12, 48), (-65, 14, 46), (30, -30, 48)):
                    c.drawCircle(cx + dx, cy + dy + 8, rr, art.paint((200, 225, 245), 230))
                for dx, dy, rr in ((0, 0, 60), (65, 12, 48), (-65, 14, 46), (30, -30, 48)):
                    c.drawCircle(cx + dx, cy + dy, rr, art.paint((250, 252, 255), 240))


    def draw_ground(self, c, t, gy=1250.0, dock=False):
        """Ground plane whose horizon sits at screen y `gy` (follows the shot's grounded props)."""
        g = self.ground
        dy = gy - 1250
        if g == "planet":
            R, cy = 2100, gy + 20 + 2100
            c.drawCircle(W / 2, cy, R + 40, art.paint(self.accent, 70, blur=40))
            c.drawCircle(W / 2, cy, R, art.paint(art.shade(self.bot, -0.35)))
            c.save()
            c.clipPath(skia.Path.Circle(W / 2, cy, R), doAntiAlias=True)
            for x, y, r in self.craters:
                xx = (x + t * 14) % (W + 400) - 200
                c.drawCircle(xx, y + dy, r, art.paint(art.shade(self.bot, -0.5)))
                c.drawCircle(xx + r * 0.15, y + dy + r * 0.1, r * 0.8, art.paint(art.shade(self.bot, -0.42)))
            c.drawCircle(W / 2, cy + 30, R, art.paint(art.shade(self.bot, -0.6), 90))
            c.restore()
        elif g in ("hill", "sea"):
            if g == "sea":
                back, front = (40, 120, 200), (20, 80, 160)
            elif self.style == "sky":
                back, front = (70, 160, 90), (40, 120, 70)
            else:
                back, front = art.shade(self.bot, -0.25), art.shade(self.bot, -0.45)
            for yb, amp, colr, ph, sp in ((gy - 20, 40, back, 0.0, 6), (gy + 70, 30, front, 1.7, 12)):
                pa = skia.Path()
                pa.moveTo(0, H)
                for x in range(0, W + 20, 20):
                    wob = amp * math.sin(x / 190 + ph) + 0.4 * amp * math.sin(x / 70 + ph * 2)
                    if g == "sea":
                        wob = 14 * math.sin(x / 60 + t * 2 * (sp / 6) + ph)
                    pa.lineTo(x, yb + wob)
                pa.lineTo(W, H)
                pa.close()
                c.drawPath(pa, art.paint(colr))
            if g == "sea" and dock:  # wooden pier for people/cranes/boxes standing "on the sea"
                d0, d1 = max(0, dock[0]), min(W, dock[1])
                c.drawRect(skia.Rect.MakeXYWH(d0, gy - 6, d1 - d0, 34), art.paint((150, 96, 60)))
                c.drawRect(skia.Rect.MakeXYWH(d0, gy - 6, d1 - d0, 10), art.paint((190, 130, 85)))
                for x in range(int(d0) + 40, int(d1) - 20, 160):
                    c.drawRect(skia.Rect.MakeXYWH(x, gy + 28, 26, 120), art.paint((110, 70, 45)))
            if g == "hill":
                for x, y, r in self.craters[:5]:
                    tx = (x * 1.3) % W
                    c.drawLine(tx, gy + 5 - 20, tx, gy - 35 - 20, art.paint(art.shade(self.bot, -0.55), stroke=10))
                    c.drawCircle(tx, gy - 50 - 20, 28, art.paint(art.shade(self.accent, -0.35)))
        # floor vignette keeps captions readable
        c.drawRect(skia.Rect.MakeXYWH(0, H * 0.6, W, H * 0.4), skia.Paint(Shader=skia.GradientShader.MakeLinear(
            [skia.Point(0, H * 0.6), skia.Point(0, H)], [skia.Color(0, 0, 0, 0), skia.Color(0, 0, 0, 110)])))

    def foreground(self, c, t):
        """Out-of-focus particles drifting in front of the scene for depth."""
        for x, y, r, sp, cl in self.bokeh:
            yy = (y - t * sp) % (H + 200) - 100
            c.drawCircle(x + 30 * math.sin(t * 0.5 + y), yy, r, art.paint(cl, 40, blur=r * 0.35))


def scene_props(line, accent):
    """Normalise a line's scene into a list of prop dicts (supports the legacy `visual` field)."""
    props = [dict(p) for p in line.get("scene", [])]
    vis = line.get("visual")
    if vis:
        v = dict(vis)
        typ = v.pop("type", "big")
        v.setdefault("y", 0.60 if props and typ == "big" else 0.40)
        props.append({"prop": typ, **v})
    for p in props:
        p.setdefault("accent", accent)
        if p["prop"] == "calendar" and "flip" in p:
            p["pages"] = p.pop("flip")
    return props


# approximate half-extents (px at s=1) used to auto-frame each scene
EXTENTS = {
    "sun": (200, 200), "planet": (175, 175), "moon": (90, 90), "photons": (420, 150), "eye": (190, 110),
    "brain": (200, 170), "person": (115, 180), "satellite": (190, 95), "clock": (150, 150), "hourglass": (110, 170),
    "phone": (110, 210), "slot": (230, 200), "ship": (320, 150), "container": (200, 90), "wheel": (190, 210),
    "card": (130, 170), "check": (110, 110), "camera": (150, 165), "feather": (90, 170), "bulb": (120, 160),
    "coin": (100, 100), "pin": (150, 170), "calendar": (150, 175), "spectrum": (420, 60), "mountain": (450, 220),
    "rain": (350, 250), "wave": (460, 200), "salt": (250, 110), "big": (430, 190), "question": (200, 260),
    "versus": (430, 220), "timeline": (400, 190), "bird": (150, 130), "robot": (150, 250), "heart": (170, 140),
    "speaker": (130, 170), "newspaper": (200, 240), "thumb": (130, 130), "frame": (180, 210), "crane": (200, 270),
    "tv": (230, 230), "package": (150, 170), "mascot": (135, 205),
}
FIT_BOX = (110, 230, 970, 1230)  # x0, y0, x1, y1: visual safe area above the captions


def extent(pr):
    typ = pr["prop"]
    if typ == "crowd":
        return 75 * pr.get("n", 5) + 20, 200
    if typ == "bubble":
        return max(110, art.measure(pr.get("label", ""), 58) / 2 + 40), 110
    if typ == "label":
        size = pr.get("size", 80)
        return min(460, art.measure(pr.get("label", ""), size) / 2), size * 0.6
    if typ == "arrow":
        return pr.get("length", 260) / 2 + 20, 50
    if typ == "bars":
        return 430, 95 * len(pr.get("bars", [])) + 60
    if typ == "list":
        return 440, 100 * len(pr.get("items", [])) + 20
    return EXTENTS.get(typ, (200, 200))


def fit_scene(props, cam=None):
    """Zoom + offset that frames the scene's content in FIT_BOX, allowing for the shot's camera push-in (max 1.6x)."""
    xs, ys = [], []
    for pr in props:
        ex, ey = extent(pr)
        s = pr.get("s", 1.0)
        for fx, fy in [(pr.get("x", 0.5), pr.get("y", 0.4))] + ([tuple(pr["to"])] if "to" in pr else []):
            xs += [fx * W - ex * s, fx * W + ex * s]
            ys += [fy * H - ey * s, fy * H + ey * s]
    if not xs:
        return 1.0, 0.0, 0.0
    bx0, bx1, by0, by1 = min(xs), max(xs), min(ys), max(ys)
    x0, y0, x1, y1 = FIT_BOX
    cam_max = max((cam or {}).get("zoom", (1.0, 1.1))) * 1.07  # end of push-in + punch
    z = min((x1 - x0) / max(1, bx1 - bx0), (y1 - y0) / max(1, by1 - by0)) / cam_max
    z = max(1.0 / cam_max, min(z, 1.6))
    # move the content centre to the box centre (in pre-zoom coordinates)
    return z, (x0 + x1) / 2 - (bx0 + bx1) / 2, (y0 + y1) / 2 - (by0 + by1) / 2


FOOT = {"person": 175, "crowd": 190, "robot": 140, "bird": 125, "ship": 70, "crane": 180, "package": 170,
        "mountain": 200, "camera": 165, "speaker": 170, "slot": 160, "tv": 200, "wave": -60, "mascot": 172}


def camera(tl, dur, cam, fit, punch):
    z0, z1 = cam.get("zoom", (1.0, 1.1))
    k = ease_io(tl / max(dur, 0.1))
    z = z0 + (z1 - z0) * k
    if punch:  # hard cut lands slightly zoomed in and settles
        z *= 1 + 0.07 * (1 - ease_io(tl / PUNCH))
    pan = cam.get("pan", (0, 0))
    return z * fit[0], pan[0] * k, pan[1] * k


def ground_y(props, tl, dur, cam, fit, punch):
    """Screen y of the horizon: under the lowest grounded prop's feet, else the default line."""
    def foot(pr):  # a rotated (lying) prop rests on its side
        r = math.radians(pr.get("rot", 0))
        side = 80 if pr["prop"] == "person" else extent(pr)[0]
        return FOOT[pr["prop"]] * abs(math.cos(r)) + side * abs(math.sin(r))
    feet = [pr.get("y", 0.4) * H + foot(pr) * pr.get("s", 1.0) for pr in props if pr["prop"] in FOOT
            and not pr.get("float")]
    if not feet:
        return 1250.0
    zt, px, py = camera(tl, dur, cam, fit, punch)
    cy = (FIT_BOX[1] + FIT_BOX[3]) / 2
    return max(820.0, min(1400.0, cy + py + zt * (max(feet) - cy + fit[2])))


def dock_span(sc, tl, punch):
    """Screen x-range of the pier: under grounded props other than ships (None = no pier)."""
    xs = [(pr.get("x", 0.5) * W, extent(pr)[0] * pr.get("s", 1.0)) for pr in sc["props"]
          if pr["prop"] in FOOT and pr["prop"] not in ("ship", "wave") and not pr.get("float")]
    if not xs:
        return None
    zt, px, _ = camera(tl, sc["dur"], sc["cam"], sc["fit"], punch)
    cx = (FIT_BOX[0] + FIT_BOX[2]) / 2
    to_screen = lambda x: cx + px + zt * (x - cx + sc["fit"][1])
    x0 = min(to_screen(x - e) for x, e in xs) - 60
    x1 = max(to_screen(x + e) for x, e in xs) + 60
    ships = [to_screen(pr.get("x", 0.5) * W) for pr in sc["props"] if pr["prop"] == "ship"]
    if not ships:
        return 0, W
    return (0, x1) if ships[0] > (x0 + x1) / 2 else (x0, W)


def draw_scene(c, props, tl, dur, cam, fit=(1.0, 0.0, 0.0), punch=True):
    zt, px, py = camera(tl, dur, cam, fit, punch)
    fz, fdx, fdy = fit
    z = zt / fz
    cx, cy = (FIT_BOX[0] + FIT_BOX[2]) / 2, (FIT_BOX[1] + FIT_BOX[3]) / 2
    c.save()
    c.translate(cx + px + 5 * math.sin(tl * 0.9), cy + py + 4 * math.cos(tl * 0.7))
    c.rotate(0.5 * math.sin(tl * 0.6))
    c.scale(zt, zt)
    c.translate(-cx + fdx, -cy + fdy)
    # one soft, consistent drop shadow (light from top-left) separates subjects from the background
    c.saveLayer(None, skia.Paint(ImageFilter=skia.ImageFilters.DropShadow(12, 20, 16, 16, skia.Color(10, 5, 40, 100))))
    for pr in props:
        fn = art.PROPS[pr["prop"]]
        delay = pr.get("delay", 0.0)
        te = tl - delay
        if punch and delay <= 0.05:
            pe = 1.0  # on a hard cut the shot's main props are already there; the punch-in supplies the motion
        else:
            pe = ease_out_back(te / 0.4) if te > 0 else 0
        if pe <= 0:
            continue
        x, y = pr.get("x", 0.5) * W, pr.get("y", 0.4) * H
        if "to" in pr:
            m = ease_io(te / max(0.1, pr.get("move_time", dur - delay)))
            x += (pr["to"][0] * W - x) * m
            y += (pr["to"][1] * H - y) * m
        grounded = pr["prop"] in FOOT and not pr.get("float")
        breathe = 1 + 0.018 * math.sin(tl * 2.1 + x * 0.01)
        s = pr.get("s", 1.0) * pe * (1 if grounded else breathe)
        c.save()
        c.translate(x, y + (0 if grounded else 10 * math.sin(tl * 1.6 + x)))
        c.rotate(pr.get("rot", 0) + pr.get("spin", 0) * tl + (0 if grounded else 1.6 * math.sin(tl * 1.3 + x)))
        c.scale(s * (-1 if pr.get("flip") else 1), s)
        if grounded:  # squash-and-stretch breathing from the feet keeps standing props alive
            f = FOOT[pr["prop"]]
            c.translate(0, f)
            c.scale(1 - 0.012 * math.sin(tl * 2.3 + x), 1 + 0.025 * math.sin(tl * 2.3 + x))
            c.translate(0, -f)
        kw = {k2: v for k2, v in pr.items() if k2 not in ("prop", "x", "y", "s", "delay", "to", "move_time", "rot",
                                                           "spin", "flip", "on", "layer", "float")}
        fn(c, te, min(1.0, te / 0.5), _zs=max(0.05, pr.get("s", 1.0) * fz * z), **kw)
        c.restore()
    c.restore()
    c.restore()


STOP_END = {"the", "a", "an", "of", "to", "and", "in", "on", "at", "for", "by", "your", "my", "their", "our", "its",
            "is", "was", "are", "were", "be", "can", "can't", "should", "would", "will", "that", "than", "with", "from",
            "as", "or", "but", "so", "if", "it's", "this", "these", "those", "his", "her", "not", "no", "very",
            "why", "do", "does", "did", "when", "who", "what", "how", "because", "which", "where", "while", "just",
            "also", "into", "onto", "about", "you", "we", "they", "i", "he", "she", "has", "have", "had", "been",
            "random", "false", "fake", "real", "simple", "single", "whole", "same", "other", "every", "each", "more",
            "most", "less", "few", "many", "much", "own", "new", "old", "big", "small", "little", "first", "last",
            "next", "only", "tiny", "huge", "famous", "classic", "blue", "violet", "better", "worse", "useless",
            "bigger", "smaller", "faster", "slower", "great", "good", "bad", "best", "worst", "same", "whole"}
NUM_WORDS = {"eleven", "twelve", "thirteen", "fourteen", "fifteen", "sixteen", "seventeen", "eighteen", "nineteen",
             "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten", "twenty", "thirty", "forty",
             "fifty", "sixty", "seventy", "eighty", "ninety", "hundred", "thousand", "million", "percent", "dollars",
             "cents", "km", "kilometers", "microseconds", "seconds"}
CAP_SIZE, CAP_MIN = 78, 58


def _numeric(w):
    return bool(re.search(r"\d", w)) or any(_norm(p) in NUM_WORDS for p in w.split("-"))


def _fits(ws):
    labels = " ".join(art.clean(w[0]).upper() for w in ws)
    return art.measure(labels, CAP_MIN) + CAP_MIN * 0.22 * (len(ws) - 1) <= SAFE_W


def _chunk_cost(ws, nxt):
    """Lower is better: prefer 2-3 word phrases, never end on a function word, never split a number."""
    if not _fits(ws):
        return 1e9
    cost = 1.5 + (1.5 if len(ws) == 1 else 0) + (1.2 if len(ws) == 4 else 0) + (2.5 if len(ws) >= 5 else 0)
    last = _norm(ws[-1][0])
    if (last in {_norm(x) for x in STOP_END} or ws[-1][0].lower().endswith(("'s", "’s"))) \
            and ws[-1][0][-1:] not in ",.?!;:":
        cost += 6
    if any(w[0][-1:] in ".?!" for w in ws[:-1]):
        cost += 50  # never run a caption across a sentence break
    if nxt is not None and _numeric(ws[-1][0]) and _numeric(nxt[0]):
        cost += 8
    if len(" ".join(w[0] for w in ws)) > 18:
        cost += 0.8
    return cost


def _split_segment(seg):
    """Optimal split of one pause/punctuation-delimited segment into caption chunks (DP)."""
    n = len(seg)
    best = [0.0] + [1e18] * n
    back = [0] * (n + 1)
    for j in range(1, n + 1):
        for i in range(max(0, j - 5), j):
            c = best[i] + _chunk_cost(seg[i:j], seg[j] if j < n else None)
            if c < best[j]:
                best[j], back[j] = c, i
    out, j = [], n
    while j > 0:
        out.append(seg[back[j]:j])
        j = back[j]
    return out[::-1]


NUMBER_ONLY = NUM_WORDS - {"percent", "dollars", "cents", "km", "kilometers", "microseconds", "seconds"}


UNIT_WORDS = {"percent", "dollars", "cents", "km", "kilometers", "microseconds", "seconds", "minutes", "hours",
              "days", "years", "people", "times", "clips", "containers"}


def digits_for_captions(words):
    """Show spelled-out numbers as digits ('two hundred nineteen' -> '219', 'thirty percent' -> '30%',
    'five dollars eighty-three' -> '$5.83'). A lone small number word ('one hand') stays a word."""
    import qa

    def num_run(i):
        j = i
        while j < len(words):
            w = words[j][0].rstrip(",.?!;:")
            if _norm(w) == "and" and j > i and _norm(words[j - 1][0]) in ("hundred", "thousand", "million") \
                    and j + 1 < len(words) and all(_norm(p) in NUMBER_ONLY for p in words[j + 1][0].rstrip(",.?!;:").split("-")):
                j += 1
                continue
            if not w or not all(_norm(p) in NUMBER_ONLY for p in w.split("-")):
                break
            j += 1
            if words[j - 1][0][-1:] in ",.?!;:":
                break
        return j

    def value(run_):
        spoken = [x for x in " ".join(w[0].rstrip(",.?!;:") for w in run_).replace("-", " ").lower().split()
                  if x != "and"]
        out_ = qa.words_to_digits(spoken)
        return " ".join(f"{int(d):,}" if d.isdigit() and int(d) >= 10000 else d for d in out_)

    out, i = [], 0
    while i < len(words):
        j = num_run(i)
        if j == i:
            out.append(words[i])
            i += 1
            continue
        run_, label = words[i:j], value(words[i:j])
        if " " in label:  # e.g. a year said as "nineteen eighty-four": keep the words
            out.extend(run_)
            i = j
            continue
        punct = run_[-1][0][-1:] if run_[-1][0][-1:] in ",.?!;:" else ""
        nxt = words[j] if j < len(words) and not punct else None
        unit = _norm(nxt[0]) if nxt else ""
        if unit == "percent":
            run_, label, j = run_ + [nxt], label + "%", j + 1
            punct = nxt[0][-1:] if nxt[0][-1:] in ",.?!;:" else ""
        elif unit == "dollars":
            run_, label, j = run_ + [nxt], "$" + label, j + 1
            punct = nxt[0][-1:] if nxt[0][-1:] in ",.?!;:" else ""
            k = num_run(j) if not punct else j
            if k > j:  # "five dollars eighty-three" -> "$5.83"
                cents = value(words[j:k])
                if cents.isdigit() and int(cents) < 100:
                    label += f".{int(cents):02d}"
                    run_ = run_ + words[j:k]
                    punct = words[k - 1][0][-1:] if words[k - 1][0][-1:] in ",.?!;:" else ""
                    j = k
        elif len(run_) == 1 and label.isdigit() and int(label) < 10 and unit not in UNIT_WORDS:
            out.append(words[i])  # "one hand", "two ideas": keep as words
            i += 1
            continue
        out.append((label + punct, run_[0][1], run_[-1][1] + run_[-1][2] - run_[0][1]))
        i = j
    return out


def chunk_words(words, gap=0.2):
    """Caption chunks: split at punctuation and pauses, then split each segment into readable phrases."""
    words = digits_for_captions(words)
    segs, cur = [], []
    for i, w in enumerate(words):
        cur.append(w)
        nxt = words[i + 1] if i + 1 < len(words) else None
        dangling = _norm(w[0]) in {_norm(x) for x in STOP_END}
        if nxt is None or w[0][-1:] in ".?!;:," or (nxt[1] - (w[1] + w[2]) > gap and not dangling):
            segs.append(cur)
            cur = []
    chunks = []
    for sg in segs:
        chunks += _split_segment(sg)
    return chunks


def draw_captions(c, chunks, t, accent):
    active = chunks[0] if chunks else None  # frame 0 already shows the first caption
    for ch in chunks:
        if ch[0][1] - 0.05 <= t:
            active = ch
    if not active or t > active[-1][1] + active[-1][2] + 0.5:
        return
    labels = [art.clean(w[0]).upper().rstrip(",;:") or art.clean(w[0]) for w in active]  # no trailing commas
    size = CAP_SIZE
    while size > CAP_MIN and art.measure(" ".join(labels), size) + size * 0.22 * (len(labels) - 1) > SAFE_W:
        size -= 2
    pop = ease_out_back((t - active[0][1] + 0.05) / 0.16)
    size *= 0.88 + 0.12 * pop
    space = art.measure(" ", size) + size * 0.22  # room for the stroke and the enlarged current word
    widths = [art.measure(lb, size) for lb in labels]
    x = W / 2 - (sum(widths) + space * (len(labels) - 1)) / 2
    for (w, s, d), lb, wd in zip(active, labels, widths):
        cur = s - 0.03 <= t < s + max(d, 0.12) + 0.04
        color = accent if cur else ("white" if s <= t else (215, 215, 225))
        fs = size * (1.05 if cur else 1)
        f = skia.Font(art.typeface(lb), fs)
        lx = x + wd / 2 - f.measureText(lb) / 2
        base = CAP_Y + fs * 0.36
        c.drawString(lb, lx, base + 6, f, art.paint((0, 0, 0), 120, blur=6))
        c.drawString(lb, lx, base, f, art.paint(art.INK, 255, stroke=14))
        c.drawString(lb, lx, base, f, art.paint(color))
        x += wd + space


# ---------- assembly ----------

def _norm(w):
    return re.sub(r"[^a-z0-9]", "", w.lower())


def align_words(text, ws):
    """Caption words in the script's own spelling and punctuation, timed by aligning their letters to the
    TTS word boundaries (which carry no punctuation and may split or merge words)."""
    shown = text.split()
    out, j = [], 0
    for w in shown:
        target = _norm(w)
        if not target:
            if re.search(r"\w", w):
                return None  # e.g. non-Latin script: fall back to proportional timing
            continue
        if j >= len(ws):
            return None
        start, acc, k = ws[j][1], "", j
        while k < len(ws) and len(acc) < len(target):
            acc += _norm(ws[k][0])
            k += 1
        if acc != target:
            return None
        end = ws[k - 1][1] + ws[k - 1][2]
        out.append((w, start, end - start))
        j = k
    return out if j == len(ws) else None


def display_words(text, ws):
    """Caption words: the script's own spelling, timed by the TTS word boundaries."""
    aligned = align_words(text, ws)
    if aligned:
        return aligned
    shown = text.split()
    if not ws:
        return []
    t0, t1 = ws[0][1], ws[-1][1] + ws[-1][2]
    total = sum(len(w) + 1 for w in shown)
    out, t = [], t0
    for w in shown:
        d = (t1 - t0) * (len(w) + 1) / total
        out.append((w, t, d))
        t += d
    return out


def find_word(words, key, start_idx=0):
    """Index of the first word at/after start_idx whose normalised form starts with key."""
    k = _norm(key)
    if not k:
        return None
    for exact in (True, False):  # an exact word match wins over a prefix match ("nine" vs "nineteen")
        for j in range(start_idx, len(words)):
            w = _norm(words[j][0])
            if w == k or (not exact and w.startswith(k)):
                return j
    return None


def line_shots(ln):
    shots = ln.get("shots")
    if shots:
        return [dict(sh) for sh in shots]
    return [{"scene": ln.get("scene", []), "visual": ln.get("visual"), "cam": ln.get("cam", {})}]

def validate(spec, path):
    if not re.fullmatch(r"[\w-]+", str(spec.get("id", ""))):
        raise RenderError(f"{path}: id must match [A-Za-z0-9_-]+")
    lines = spec.get("lines") or []
    if not lines:
        raise RenderError(f"{path}: no lines")
    teaser = spec.get("teaser")
    if teaser is not None and not (isinstance(teaser, dict) and str(teaser.get("question", "")).strip()):
        raise RenderError(f"{path}: teaser must be an object with a non-empty 'question'")
    for i, ln in enumerate(lines):
        if not str(ln.get("text", "")).strip():
            raise RenderError(f"{path}: line {i} has empty text")
        words = [(w, 0, 0) for w in str(ln["text"]).split()]
        for k, sh in enumerate(line_shots(ln)):
            zoom = sh.get("cam", {}).get("zoom", (1.0, 1.1))
            if not (isinstance(zoom, (list, tuple)) and len(zoom) == 2):
                raise RenderError(f"{path}: line {i} shot {k} cam.zoom must be [start, end]")
            for item in [sh] + sh.get("scene", []):
                cue = item.get("on")
                if cue is None or (item is sh and k == 0):
                    continue
                if not isinstance(cue, str) or find_word(words, cue) is None:
                    raise RenderError(f"{path}: line {i} shot {k} cue word {cue!r} not found in the line text")
        for p in [p for sh in line_shots(ln) for p in scene_props(sh, "yellow")]:
            if p["prop"] not in art.PROPS:
                raise RenderError(f"{path}: line {i} unknown prop/visual '{p['prop']}'")
            for b in p.get("bars", []):
                float(b[1])


def render(spec_path, out_dir, args):
    spec = json.load(open(spec_path))
    validate(spec, spec_path)
    top, bot, accent = PALETTES.get(spec.get("palette", "violet"), PALETTES["violet"])
    lines = spec["lines"]
    with tempfile.TemporaryDirectory() as tmp:
        scenes, words, voice, cues, t = [], [], [], [], 0.0
        for i, ln in enumerate(lines):
            samples, ws = synth(ln.get("say", ln["text"]), args, os.path.join(tmp, f"a{i}"), args.cache)
            ws = display_words(ln["text"], ws)
            last = i == len(lines) - 1
            reveal = bool(ln.get("sfx"))
            pause = ln.get("pause", 0.1 if last else (0.45 if reveal else (0.4 if i == 0 or ln["text"].rstrip().endswith("?") else 0.2)))
            dur = len(samples) / audio.SR + pause
            # split the line into shots that cut on spoken words
            shots, widx = line_shots(ln), 0
            starts = []
            for k, sh in enumerate(shots):
                j = find_word(ws, sh["on"], widx) if k and sh.get("on") else None
                if j is not None:
                    widx = j
                starts.append((t + max(0.0, ws[j][1] - 0.06) if j is not None and k else
                               (t if k == 0 else starts[-1][0] + 1.5), widx))
            for k, sh in enumerate(shots):
                st, wi = starts[k]
                end = starts[k + 1][0] if k + 1 < len(shots) else t + dur
                props = scene_props(sh, accent)
                for pr in props:
                    if pr.get("on"):
                        j = find_word(ws, pr["on"], wi)
                        if j is not None:
                            pr["delay"] = max(0.0, t + ws[j][1] - st - 0.05)
                    if i == 0 and k == 0:  # the hook frame must be complete from frame 0 to stop the scroll
                        pr["delay"] = 0.0
                scenes.append({"start": st, "dur": end - st, "props": props, "cam": sh.get("cam", {}), "tint": sh.get("tint"),
                               "fit": fit_scene(props, sh.get("cam")) if sh.get("autofit", spec.get("autofit", True)) else (1.0, 0, 0)})
                if scenes[-1]["start"] > 0 and k == 0:  # whoosh on sentence-level cuts only
                    cues.append((max(0, st - 0.12), "whoosh"))
                for pr in props[:3]:
                    if pr.get("delay", 0) > 0.2:
                        cues.append((st + pr["delay"] + 0.05, "pop"))
            words += [(w, t + s0, d) for w, s0, d in ws]
            voice.append(samples)
            voice.append(np.zeros(int(pause * audio.SR)))
            if last and not ln.get("sfx"):
                cues.append((t + 0.05, "pop"))  # soft marker for the payoff / loop line
            if ln.get("sfx"):
                cues.append((t + ln.get("sfx_at", 0.0), ln["sfx"]))
                if ln["sfx"] == "chime" and i:
                    cues.append((max(0.0, t - 1.1), "riser"))  # build-up into the reveal
            t += dur
        outro_at, talk_env, chime_times = None, None, [at for at, kind in cues if kind == "chime"]
        teaser = spec.get("teaser")
        if teaser and not args.no_mascot:
            gap = 0.3  # breath between the narrator's last line and the mascot
            scenes[-1]["dur"] += gap
            voice.append(np.zeros(int(gap * audio.SR)))
            t += gap
            cta = teaser.get("cta", "The answer is in the next Short!")
            samples, ws = synth(f"{teaser['question']} {cta}", args, os.path.join(tmp, "mascot"), args.cache,
                                voice=args.mascot_voice, rate=args.mascot_rate, pitch=args.mascot_pitch)
            ws = display_words(f"{teaser['question']} {cta}", ws)
            dur = len(samples) / audio.SR + 0.35
            n_q = len(teaser["question"].split())
            cta_at = t + (ws[n_q][1] - 0.08 if n_q < len(ws) else dur * 0.7)
            frame = int(audio.SR / FPS)
            env_ = np.array([np.sqrt(np.mean(samples[i:i + frame] ** 2)) for i in range(0, len(samples), frame)])
            talk_env = np.clip(env_ / (np.percentile(env_, 90) + 1e-9), 0, 1)
            owl = {"prop": "mascot", "x": 0.5, "y": 0.47, "s": 2.0, "accent": accent}
            for st, end, label, extra in (
                    (t, cta_at, teaser.get("label", "NEXT TIME?"), {"mood": "curious"}),
                    (cta_at, t + dur, "ANSWER: NEXT SHORT", {"mood": "happy", "wave": True})):
                props = [{**owl, **extra}, {"prop": "label", "label": label, "x": 0.5, "y": 0.2, "size": 110,
                                            "color": "yellow", "accent": accent}]
                scenes.append({"start": st, "dur": end - st, "props": props, "cam": {"zoom": (1.0, 1.06)},
                               "tint": None, "fit": fit_scene(props, {"zoom": (1.0, 1.06)}), "outro": True})
            cues += [(max(0, t - 0.12), "whoosh"), (t + 0.02, "pop"), (cta_at, "pop")]
            words += [(w, t + s0, d) for w, s0, d in ws]
            voice += [samples, np.zeros(int(0.35 * audio.SR))]
            outro_at = t
            t += dur
        total = t
        chunks = chunk_words(words)

        mix = audio.mixdown(np.concatenate(voice), total, cues, spec.get("mood", "wonder"),
                            seed=sum(map(ord, spec["id"])), music_db=args.music_db, bed=args.bed)
        raw = os.path.join(tmp, "mix.wav")
        with wave.open(raw, "w") as w:
            w.setnchannels(2)
            w.setsampwidth(2)
            w.setframerate(audio.SR)
            w.writeframes((np.clip(mix.T, -1, 1) * 32767).astype(np.int16).tobytes())
        stats = run(["ffmpeg", "-nostdin", "-hide_banner", "-i", raw, "-af", "loudnorm=I=-14:TP=-1.5:LRA=11:print_format=json",
                     "-f", "null", "-"], capture_output=True, text=True).stderr
        m = json.loads(stats[stats.rindex("{"):stats.rindex("}") + 1])
        ln_filter = (f"loudnorm=I=-14:TP=-1.5:LRA=11:measured_I={m['input_i']}:measured_TP={m['input_tp']}:"
                     f"measured_LRA={m['input_lra']}:measured_thresh={m['input_thresh']}:offset={m['target_offset']}:linear=true")
        final_audio = os.path.join(tmp, "final.wav")
        run(["ffmpeg", "-nostdin", "-y", "-loglevel", "error", "-i", raw, "-af", ln_filter, "-ar", str(audio.SR), final_audio])

        os.makedirs(out_dir, exist_ok=True)
        target = os.path.join(out_dir, spec["id"] + ".mp4")
        enc = subprocess.Popen(
            ["ffmpeg", "-nostdin", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgba", "-s", f"{W}x{H}",
             "-r", str(FPS), "-i", "-", "-i", final_audio, "-c:v", "libx264", "-preset", "slow", "-tune", "animation",
             "-crf", str(args.crf), "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "128k", "-shortest",
             "-movflags", "+faststart", target], stdin=subprocess.PIPE)
        bg = Background((top, bot, accent), spec.get("bg", "space"), spec["id"], total, spec.get("ground"))
        surface = skia.Surface.MakeRaster(skia.ImageInfo.Make(W, H, skia.kRGBA_8888_ColorType, skia.kPremul_AlphaType))
        c = surface.getCanvas()
        try:
            for n in range(int(math.ceil(total * FPS))):
                ft = n / FPS
                idx = max(i for i, s in enumerate(scenes) if s["start"] <= ft + 1e-6)
                sc = scenes[idx]
                tl = ft - sc["start"]
                bg.draw(c, ft)
                if sc.get("tint"):
                    c.drawRect(skia.Rect.MakeWH(W, H), art.paint(sc["tint"], 120))
                # hard cuts with a punch-in; the very first scene is fully built on frame 0 (loop seam)
                tl_draw = tl + (0.6 if idx == 0 else 0)
                if sc.get("outro"):
                    k_env = int((ft - outro_at) * FPS)
                    talk = float(talk_env[k_env]) if 0 <= k_env < len(talk_env) else 0.0
                    for pr in sc["props"]:
                        if pr["prop"] == "mascot":
                            pr["talk"] = talk
                dock = dock_span(sc, tl_draw, idx > 0)
                bg.draw_ground(c, ft, ground_y(sc["props"], tl_draw, sc["dur"], sc["cam"], sc["fit"], idx > 0), dock)
                draw_scene(c, sc["props"], tl_draw, sc["dur"], sc["cam"], sc["fit"], punch=idx > 0)
                if teaser and not args.no_mascot and not sc.get("outro"):
                    # Mr. Shorts watches from the corner (below the captions, clear of the Shorts UI)
                    hop = max((1 - abs((ft - tc) / 0.45 - 0.5) * 2 for tc in chime_times if 0 <= ft - tc <= 0.45),
                              default=0.0)
                    c.save()
                    c.translate(155, 1492)
                    c.scale(0.62, 0.62)
                    art.PROPS["mascot"](c, ft, 1.0, look=math.sin(ft * 0.7) + 0.4, hop=hop / 2,
                                        mood="curious" if hop else "smirk")
                    c.restore()
                bg.foreground(c, ft)
                draw_captions(c, chunks, ft, art.rgb(accent))
                enc.stdin.write(surface.makeImageSnapshot().tobytes())
        except BrokenPipeError:
            pass
        finally:
            enc.stdin.close()
            rc = enc.wait()
        if rc:
            raise RenderError(f"ffmpeg encoder failed ({rc}) for {spec_path}")
    size = os.path.getsize(target) / 1e6
    print(f"{target}  {total:.1f}s  {sum(len(ln['text'].split()) for ln in lines)} words  {size:.1f} MB")
    return target


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("scripts", nargs="+", help="script JSON files (globs ok)")
    ap.add_argument("out", help="output directory")
    ap.add_argument("--tts", choices=["edge", "elevenlabs", "say"], default="edge")
    ap.add_argument("--voice", default=None)
    ap.add_argument("--rate", default="+8%", help="edge speaking rate")
    ap.add_argument("--pitch", default="-2Hz", help="edge pitch shift")
    ap.add_argument("--crf", type=int, default=24, help="x264 quality (lower = bigger, sharper)")
    ap.add_argument("--music-db", type=float, default=-19.0, help="music bed peak level before ducking")
    ap.add_argument("--mascot-voice", default="en-US-AnaNeural", help="voice for the mascot's end question")
    ap.add_argument("--mascot-rate", default="+12%")
    ap.add_argument("--mascot-pitch", default="+0Hz")
    ap.add_argument("--no-mascot", action="store_true", help="skip the mascot and its end question")
    ap.add_argument("--music-file", default=None, help="use this audio file as the music bed instead of the generated one")
    ap.add_argument("--cache", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), ".tts-cache"))
    args = ap.parse_args()
    if args.voice is None:
        args.voice = {"edge": "en-US-AndrewMultilingualNeural", "elevenlabs": "pNInz6obpgDQGcFMJqyk"}.get(args.tts)
    args.bed = None
    if args.music_file:  # decode once: stereo float at the mix sample rate
        pcm = run(["ffmpeg", "-nostdin", "-loglevel", "error", "-i", args.music_file, "-ac", "2", "-ar", str(audio.SR),
                   "-f", "f32le", "-"], capture_output=True).stdout
        args.bed = np.frombuffer(pcm, np.float32).astype(np.float64).reshape(-1, 2).T
    failed = []
    for pattern in args.scripts:
        for path in sorted(glob.glob(pattern)) or [pattern]:
            try:
                render(path, args.out, args)
            except Exception as e:  # one bad script must not stop the batch
                if isinstance(e, KeyboardInterrupt):
                    raise
                print(f"FAILED {path}: {e}", file=sys.stderr)
                failed.append(path)
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
