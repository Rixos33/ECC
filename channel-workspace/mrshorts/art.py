"""Flat-vector prop library (skia) for Shorts: two-tone shading, soft glows, simple idle motion.

Every prop is draw(c, t, p, **kw) centred on (0, 0) at unit scale ~ 200 px; the caller
translates/scales. t = seconds since scene start, p = entrance progress 0..1 (already eased).
"""
import math, os
import skia

INK = (20, 16, 40)
PAL = {
    "white": (244, 241, 234), "yellow": (255, 210, 63), "orange": (255, 140, 66), "red": (240, 84, 79),
    "pink": (255, 94, 138), "purple": (140, 90, 230), "violet": (155, 92, 255), "blue": (62, 150, 255),
    "cyan": (62, 198, 255), "teal": (31, 181, 169), "green": (122, 209, 81), "grey": (120, 128, 150),
    "navy": (16, 30, 70), "brown": (150, 96, 60), "skin": (255, 190, 150),
}
FONT_FILES = ["/System/Library/Fonts/Supplemental/Arial Rounded Bold.ttf",
              "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
              "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", "C:/Windows/Fonts/arialbd.ttf"]
FALLBACK_FILES = ["/System/Library/Fonts/Supplemental/Arial Unicode.ttf", "/System/Library/Fonts/Apple Symbols.ttf",
                  "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"]
_tf, _fb = None, None


def typeface(s=""):
    """Rounded bold face; falls back to a wide-coverage font for strings with glyphs it lacks."""
    global _tf, _fb
    if _tf is None:
        path = next((f for f in FONT_FILES if os.path.exists(f)), None)
        _tf = skia.Typeface.MakeFromFile(path) if path else skia.Typeface.MakeDefault()
        path = next((f for f in FALLBACK_FILES if os.path.exists(f)), None)
        _fb = skia.Typeface.MakeFromFile(path) if path else _tf
    if s and any(_tf.unicharToGlyph(ord(ch)) == 0 for ch in s if not ch.isspace()):
        return _fb
    return _tf


def clean(s):
    return str(s).replace("\u03bc", "\u00b5")


def col(c, a=255):
    if isinstance(c, str):
        c = PAL.get(c) or tuple(int(c.lstrip("#")[i:i + 2], 16) for i in (0, 2, 4))
    return skia.Color(int(c[0]), int(c[1]), int(c[2]), int(a))


def rgb(c):
    if isinstance(c, str):
        return PAL.get(c) or tuple(int(c.lstrip("#")[i:i + 2], 16) for i in (0, 2, 4))
    return tuple(c)


def shade(c, k):
    """k<0 darker, k>0 lighter."""
    c = rgb(c)
    return tuple(int(v + (255 - v) * k) if k > 0 else int(v * (1 + k)) for v in c)


def paint(c, a=255, stroke=0, blur=0, cap=True):
    p = skia.Paint(AntiAlias=True, Color=col(c, a))
    if stroke:
        p.setStyle(skia.Paint.kStroke_Style)
        p.setStrokeWidth(stroke)
        if cap:
            p.setStrokeCap(skia.Paint.kRound_Cap)
            p.setStrokeJoin(skia.Paint.kRound_Join)
    if blur:
        p.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, blur))
    return p


def ball(c, x, y, r, color, a=255, light=True):
    """Kurzgesagt-style shaded circle: base, darker lower-right crescent, highlight."""
    c.drawCircle(x, y, r, paint(shade(color, -0.28), a))
    c.drawCircle(x - r * 0.1, y - r * 0.1, r * 0.9, paint(color, a))
    if light:
        c.drawCircle(x - r * 0.38, y - r * 0.38, r * 0.16, paint(shade(color, 0.45), int(a * 0.7)))


def glow(c, x, y, r, color, a=120):
    c.drawCircle(x, y, r, paint(color, a, blur=r * 0.45))


def rrect(c, x, y, w, h, rad, color, a=255):
    c.drawRRect(skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(x, y, w, h), rad, rad), paint(color, a))


def shaded_rrect(c, x, y, w, h, rad, color, a=255):
    rrect(c, x, y, w, h, rad, shade(color, -0.28), a)
    rrect(c, x, y, w - max(6, w * 0.06), h - max(6, h * 0.06), rad, color, a)


def text(c, s, x, y, size, color="white", a=255, stroke=0, stroke_color=INK, align="c"):
    s = clean(s)
    f = skia.Font(typeface(s), size)
    w = f.measureText(s)
    x0 = x - w / 2 if align == "c" else (x - w if align == "r" else x)
    base = y + size * 0.36
    if stroke:
        c.drawString(s, x0, base, f, paint(stroke_color, a, stroke=stroke))
    c.drawString(s, x0, base, f, paint(color, a))
    return w


def measure(s, size):
    s = clean(s)
    return skia.Font(typeface(s), size).measureText(s)


MIN_PX = 50  # smallest on-screen text height after all scaling


def min_size(size, zs):
    return max(size, MIN_PX / max(zs, 0.05))


def fit_size(s, size, maxw, floor=24):
    while size > floor and measure(s, size) > maxw:
        size *= 0.92
    return size


def path(points, close=True):
    pa = skia.Path()
    pa.moveTo(*points[0])
    for pt in points[1:]:
        pa.lineTo(*pt)
    if close:
        pa.close()
    return pa


# ---------------- props ----------------

def p_sun(c, t, p, color="yellow", **_):
    glow(c, 0, 0, 230, color, 90)
    c.save()
    c.rotate(t * 12)
    for i in range(12):
        c.rotate(30)
        c.drawRRect(skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(-12, -195, 24, 55), 12, 12), paint(color, 200))
    c.restore()
    ball(c, 0, 0, 120, color)


def p_planet(c, t, p, color="blue", land="green", atmosphere="cyan", shape="round", pins=0, **_):
    body = skia.Path.Circle(0, 0, 140) if shape != "square" else \
        skia.Path().addRRect(skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(-130, -130, 260, 260), 24, 24))
    if atmosphere:
        glow(c, 0, 0, 175, atmosphere, 110)
        if shape == "square":
            c.drawRRect(skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(-150, -150, 300, 300), 36, 36), paint(atmosphere, 70))
        else:
            c.drawCircle(0, 0, 160, paint(atmosphere, 70))
    c.drawPath(body, paint(color))
    c.save()
    c.clipPath(body, doAntiAlias=True)
    if land:
        off = (t * 22) % 400
        for dx in (off - 400, off, off - 800):
            for bx, by, br in ((-60, -60, 55), (-20, -95, 40), (90, 50, 62), (120, 15, 42), (-110, 75, 40),
                               (230, -70, 50), (270, -30, 38), (300, 90, 45)):
                c.drawCircle(bx + dx, by, br, paint(land))
                c.drawCircle(bx + dx + br * 0.2, by + br * 0.25, br * 0.55, paint(shade(land, -0.18)))
    c.drawCircle(60, 60, 180, paint(INK, 70))  # night side
    c.restore()
    c.drawCircle(-55, -55, 22, paint("white", 60))
    for i in range(int(pins)):  # sample sites, popping in one after another
        if t < 0.15 + i * 0.04:
            break
        a, r = i * 2.399, 115 * math.sqrt((i + 0.5) / max(1, pins))
        x, y = r * math.cos(a), r * math.sin(a)
        c.drawCircle(x, y - 10, 9, paint("red"))
        c.drawLine(x, y - 2, x, y + 6, paint(INK, stroke=3))


def p_moon(c, t, p, color="grey", **_):
    ball(c, 0, 0, 90, color)
    for x, y, r in ((-30, -10, 16), (25, 30, 12), (20, -40, 9)):
        c.drawCircle(x, y, r, paint(shade(color, -0.2)))


def p_photons(c, t, p, colors=("violet", "blue", "green", "red"), **_):
    """Wavy light rays travelling left->right; shorter wavelengths wiggle more."""
    for i, cl in enumerate(colors):
        lam = 18 + i * 14
        pa = skia.Path()
        y0 = -120 + i * 80
        for n, x in enumerate(range(-420, int(-420 + 840 * p), 6)):
            y = y0 + 16 * math.sin((x - t * 260) / lam)
            pa.moveTo(x, y) if n == 0 else pa.lineTo(x, y)
        c.drawPath(pa, paint(cl, 240, stroke=9))
        c.drawPath(pa, paint(cl, 90, stroke=22, blur=6))


def p_eye(c, t, p, color="blue", **_):
    blink = 1.0 - max(0.0, 1 - abs(((t + 0.7) % 3.2) - 0.12) / 0.12)
    c.save()
    c.scale(1, max(0.08, blink))
    eye = skia.Path()
    eye.moveTo(-190, 0)
    eye.quadTo(0, -170, 190, 0)
    eye.quadTo(0, 170, -190, 0)
    c.drawPath(eye, paint("white"))
    c.save()
    c.clipPath(eye, doAntiAlias=True)
    lx = 25 * math.sin(t * 0.9)
    ball(c, lx, 0, 88, color, light=False)
    c.drawCircle(lx, 0, 40, paint(INK))
    c.drawCircle(lx - 22, -26, 14, paint("white", 230))
    c.drawRect(skia.Rect.MakeXYWH(-200, 60, 400, 120), paint(INK, 40))
    c.restore()
    c.drawPath(eye, paint(INK, 255, stroke=10))
    c.restore()


def p_brain(c, t, p, color="pink", highlight=None, **_):
    """Side-view brain: cerebrum with folds, cerebellum at the back, brainstem."""
    s = 1 + 0.02 * math.sin(t * 3)
    c.save()
    c.scale(s, s)
    stem = path([(40, 60), (85, 60), (95, 175), (60, 175)])
    c.drawPath(stem, paint(shade(color, -0.25)))
    cb = highlight == "cerebellum"
    ccol = "yellow" if cb else shade(color, -0.12)
    if cb:
        glow(c, 110, 80, 90, "yellow", int(130 + 80 * math.sin(t * 6)))
    cer = skia.Path()
    cer.addOval(skia.Rect.MakeXYWH(40, 30, 150, 95))
    c.drawPath(cer, paint(shade(ccol, -0.25)))
    c.drawOval(skia.Rect.MakeXYWH(43, 30, 140, 85), paint(ccol))
    for k in range(3):
        c.drawArc(skia.Rect.MakeXYWH(55 + k * 8, 45 + k * 18, 120 - k * 16, 60), 200, 140, False,
                  paint(shade(ccol, -0.3), stroke=6))
    brain = skia.Path()
    brain.moveTo(-190, 40)
    brain.cubicTo(-230, -60, -150, -170, -30, -175)
    brain.cubicTo(90, -185, 200, -120, 205, -10)
    brain.cubicTo(210, 50, 160, 80, 90, 75)
    brain.cubicTo(20, 95, -60, 110, -120, 95)
    brain.cubicTo(-170, 85, -185, 65, -190, 40)
    brain.close()
    c.save()
    c.translate(8, 10)
    c.drawPath(brain, paint(shade(color, -0.3)))
    c.restore()
    c.drawPath(brain, paint(color))
    c.save()
    c.clipPath(brain, doAntiAlias=True)
    fold = paint(shade(color, -0.3), stroke=8)
    for pts in (((-160, -40), (-120, -110), (-60, -60)), ((-60, -60), (-20, -140), (40, -90)),
                ((40, -90), (90, -150), (140, -80)), ((-150, 30), (-90, -10), (-40, 40)),
                ((-40, 40), (10, -20), (70, 30)), ((70, 30), (130, -30), (180, 10)),
                ((-100, -130), (-60, -100), (-80, -30))):
        pa = skia.Path()
        pa.moveTo(*pts[0])
        pa.quadTo(*pts[1], *pts[2])
        c.drawPath(pa, fold)
    c.drawCircle(-90, -110, 40, paint(shade(color, 0.35), 90))
    c.restore()
    c.restore()


def p_person(c, t, p, color="orange", mood="neutral", look=0.0, wave=False, **_):
    """Kurzgesagt-ish blob character."""
    rc = rgb(color)
    if 0.3 * rc[0] + 0.59 * rc[1] + 0.11 * rc[2] < 90:
        color = shade(rc, 0.35)
    bob = 5 * math.sin(t * 3 + look)
    c.drawOval(skia.Rect.MakeXYWH(-80, 168, 160, 26), paint(INK, 70))
    c.save()
    c.translate(0, bob)
    # arms behind the body, swinging gently (the waving arm is drawn separately)
    for sd in (-1, 1):
        if wave and sd > 0:
            continue
        c.save()
        c.translate(sd * 66, 0)
        c.rotate(-sd * (24 + 8 * math.sin(t * 2.4 + look + sd)))
        rrect(c, -13, 0, 26, 95, 13, shade(color, -0.22))
        c.drawCircle(0, 95, 15, paint(shade(color, -0.22)))
        c.restore()
    shaded_rrect(c, -75, -20, 150, 190, 70, color)
    ball(c, 0, -95, 80, color)
    c.drawCircle(-48, -68, 13, paint("pink", 90))  # cheeks
    c.drawCircle(48, -68, 13, paint("pink", 90))
    lift, tilt = {"sad": (-4, 7), "surprised": (-14, 0), "happy": (-6, 0)}.get(mood, (0, 0))
    for sd in (-1, 1):  # tilt > 0 raises the inner ends (worried look)
        ex = sd * 28
        c.drawLine(ex - 14, -128 + lift + (-tilt if sd > 0 else tilt) * 0.5, ex + 14,
                   -128 + lift + (tilt if sd > 0 else -tilt) * 0.5, paint(shade(color, -0.5), stroke=6))
    if wave:
        a = 25 * math.sin(t * 8)
        c.save()
        c.translate(70, 10)
        c.rotate(-140 + a)
        rrect(c, -14, 0, 28, 90, 14, shade(color, -0.15))
        c.restore()
    blink = abs(((t + look) % 3.7) - 0.1) < 0.08
    for ex in (-28, 28):
        if blink:
            c.drawLine(ex - 14, -100, ex + 14, -100, paint(INK, stroke=7))
        else:
            c.drawCircle(ex, -100, 18, paint("white"))
            c.drawCircle(ex + 5 * math.cos(look), -98, 9, paint(INK))
    m = skia.Path()
    if mood == "happy":
        m.moveTo(-24, -60)
        m.quadTo(0, -38, 24, -60)
    elif mood == "sad":
        m.moveTo(-20, -48)
        m.quadTo(0, -64, 20, -48)
    elif mood == "surprised":
        c.drawCircle(0, -55, 13, paint(INK))
    else:
        m.moveTo(-18, -55)
        m.lineTo(18, -55)
    c.drawPath(m, paint(INK, stroke=7))
    c.restore()


def p_crowd(c, t, p, n=5, colors=("orange", "teal", "pink", "purple", "green", "yellow", "cyan"), mood="neutral", **_):
    for i in range(n):
        x = (i - (n - 1) / 2) * 150
        y = 40 if i % 2 else 0
        k = max(0.0, min(1.0, p * 2 - i * 0.15))
        if k <= 0:
            continue
        c.save()
        c.translate(x, y + 60 * (1 - k))
        c.scale(0.8, 0.8)
        p_person(c, t, 1, color=colors[i % len(colors)], mood=mood, look=i * 1.3)
        c.restore()


def p_satellite(c, t, p, **_):
    c.save()
    c.rotate(8 * math.sin(t))
    for sx in (-1, 1):
        x0 = sx * 70 if sx > 0 else -190
        rrect(c, x0, -35, 120, 70, 8, "blue")
        for k in range(1, 4):
            c.drawLine(x0 + k * 30, -35, x0 + k * 30, 35, paint("navy", stroke=4))
    shaded_rrect(c, -55, -60, 110, 120, 18, "white")
    c.drawCircle(0, -80, 16, paint("red"))
    c.drawLine(0, -60, 0, -80, paint("grey", stroke=6))
    glow(c, 0, -80, 20, "red", int(110 + 110 * math.sin(t * 5)))
    c.restore()


def p_clock(c, t, p, color="white", speed=1.0, **_):
    ball(c, 0, 0, 150, "orange")
    c.drawCircle(0, 0, 118, paint(color))
    for i in range(12):
        a = i * math.pi / 6
        c.drawLine(95 * math.sin(a), -95 * math.cos(a), 108 * math.sin(a), -108 * math.cos(a), paint(INK, stroke=8))
    for length, w, rate in ((60, 12, 0.5), (90, 7, 6)):
        a = t * rate * speed
        c.drawLine(0, 0, length * math.sin(a), -length * math.cos(a), paint(INK, stroke=w))
    c.drawCircle(0, 0, 12, paint("red"))


def p_hourglass(c, t, p, color="yellow", **_):
    k = (t * 0.25) % 1
    rrect(c, -110, -170, 220, 26, 10, "brown")
    rrect(c, -110, 144, 220, 26, 10, "brown")
    glass = path([(-85, -144), (85, -144), (12, 0), (85, 144), (-85, 144), (-12, 0)])
    c.drawPath(glass, paint("cyan", 70))
    top = path([(-85 * (1 - k) - 8 * k, -144 + 130 * k), (85 * (1 - k) + 8 * k, -144 + 130 * k), (10, -6), (-10, -6)])
    c.drawPath(top, paint(color))
    bot = path([(-85, 144), (85, 144), (85 - 60 * (1 - k), 144 - 120 * k), (-85 + 60 * (1 - k), 144 - 120 * k)])
    c.drawPath(bot, paint(color))
    c.drawLine(0, 0, 0, 144 - 120 * k, paint(color, stroke=5))
    c.drawPath(glass, paint("white", 200, stroke=7))


def p_phone(c, t, p, color="navy", notify=True, **_):
    shaded_rrect(c, -110, -210, 220, 420, 36, INK)
    rrect(c, -95, -185, 190, 370, 22, color)
    for i in range(4):
        rrect(c, -75, -150 + i * 70, 150, 50, 14, "white", 40)
    if notify:
        n = int(t * 1.6) % 4
        k = min(1, (t * 1.6 % 1) * 3)
        rrect(c, -80, -150 + n * 70, 160, 50, 14, "red", int(255 * k))
        ball(c, 95, -200, 34, "red")
        text(c, str(n + 1), 95, -200, 40, "white")


def p_slot(c, t, p, **_):
    shaded_rrect(c, -190, -200, 380, 360, 40, "red")
    rrect(c, -150, -140, 300, 170, 20, "white")
    sym = ["7", "★", "$", "♥", "7"]
    for i in range(3):
        spin = t * (9 - i * 2) if t < 1.2 + i * 0.4 else 0
        idx = int(spin) % len(sym) if spin else (0 if i < 2 else 3)
        text(c, sym[idx], -95 + i * 95, -55, 90, ["red", "orange", "purple"][i], stroke=0)
    rrect(c, -150, 60, 300, 60, 16, "yellow")
    c.drawLine(210, -150, 210, 10, paint("grey", stroke=14))
    pull = math.sin(math.pi * min(1.0, max(0.0, (t - 0.1) / 0.6)))  # one pull, down and back
    c.drawLine(210, -150, 210, -150 + 120 * pull, paint("grey", stroke=14))
    ball(c, 210, -160 + 130 * pull, 34, "red")


def p_ship(c, t, p, color="red", containers=True, **_):
    c.save()
    c.rotate(2.5 * math.sin(t * 1.6))
    c.translate(0, 6 * math.sin(t * 2))
    if containers:
        cols = ["orange", "blue", "green", "yellow", "red", "teal"]
        for r in range(3):
            for i in range(6 - r):
                shaded_rrect(c, -230 + i * 76 + r * 38, -40 - r * 50, 72, 46, 4, cols[(i + r * 2) % 6])
    hull = path([(-300, 10), (320, 10), (260, 110), (-260, 110)])
    c.drawPath(hull, paint(color))
    c.drawRect(skia.Rect.MakeXYWH(-280, 75, 560, 35), paint(shade(color, -0.3)))
    shaded_rrect(c, 230, -120, 70, 130, 8, "white")
    c.restore()
    for i in range(3):
        y = 120 + i * 14
        pa = skia.Path()
        for n, x in enumerate(range(-420, 440, 8)):
            yy = y + 7 * math.sin(x / 40 + t * 3 + i)
            pa.moveTo(x, yy) if n == 0 else pa.lineTo(x, yy)
        c.drawPath(pa, paint("cyan", 200 - i * 60, stroke=8))


def p_container(c, t, p, color="orange", label="", **_):
    shaded_rrect(c, -200, -90, 400, 180, 10, color)
    for i in range(1, 9):
        c.drawLine(-200 + i * 44, -75, -200 + i * 44, 75, paint(shade(color, -0.25), stroke=8))
    if label:
        text(c, label, 0, 0, 64, "white", stroke=10)


def p_wheel(c, t, p, values=(10, 65, 25, 90, 40, 5, 75, 50), stop=0, **_):
    """Wheel of fortune; decelerates so the segment `stop` ends under the pointer."""
    target = 720 + 247.5 - stop * 45  # segment centre at -90 deg (top)
    spin = target * (1 - math.exp(-t * 3.2))  # settles within ~1.2 s
    cols = ["red", "orange", "yellow", "green", "teal", "blue", "purple", "pink"]
    for i, cl in enumerate(cols):
        c.drawArc(skia.Rect.MakeXYWH(-180, -180, 360, 360), i * 45 + spin, 45, True, paint(cl))
    for i in range(8):
        a = math.radians(i * 45 + 22.5 + spin)
        text(c, str(values[i % len(values)]), 118 * math.cos(a), 118 * math.sin(a), 40, "white", stroke=7)
    c.drawCircle(0, 0, 180, paint(INK, stroke=12))
    ball(c, 0, 0, 28, "white")
    c.drawPath(path([(-22, -210), (22, -210), (0, -165)]), paint("white"))


def p_bubble(c, t, p, label="", color="white", tail="left", _zs=1.0, **_):
    fs = min_size(58, _zs)
    w = max(220, measure(label, fs) + 80)
    h = max(140, fs * 2.2)
    shaded_rrect(c, -w / 2, -h / 2, w, h, h * 0.43, color)
    tx = -w / 4 if tail == "left" else w / 4
    c.drawPath(path([(tx - 20, h / 2 - 10), (tx + 30, h / 2 - 10), (tx - 40 if tail == "left" else tx + 60, h / 2 + 45)]), paint(color))
    text(c, label, 0, -2, fs, INK)


def p_card(c, t, p, label="", price="", color="white", accent="orange", best=False, strike=False, _zs=1.0, **_):
    if best:
        glow(c, 0, 0, 190, accent, int(90 + 60 * math.sin(t * 5)))
    shaded_rrect(c, -130, -170, 260, 340, 30, color)
    text(c, label, 0, -95, min_size(fit_size(label, 44, 220), _zs), INK)
    text(c, price, 0, 20, fit_size(price, 90, 230), accent)
    if strike:  # crossed-out old price, drawn on as the card appears
        k = min(1.0, max(0.0, (t - 0.3) / 0.3))
        c.drawLine(-100, 50, -100 + 200 * k, -10, paint("red", stroke=14))
    if best:
        rrect(c, -90, 100, 180, 50, 25, accent)
        text(c, "BEST", 0, 124, 34, "white")


def p_check(c, t, p, ok=True, **_):
    ball(c, 0, 0, 110, "green" if ok else "red")
    pa = skia.Path()
    if ok:
        pa.moveTo(-50, 0)
        pa.lineTo(-12, 40)
        pa.lineTo(55, -40)
    else:
        pa.moveTo(-40, -40)
        pa.lineTo(40, 40)
        pa.moveTo(40, -40)
        pa.lineTo(-40, 40)
    c.drawPath(pa, paint("white", stroke=26))


def p_camera(c, t, p, **_):
    c.save()
    c.rotate(10 * math.sin(t * 0.8))
    shaded_rrect(c, -150, -60, 260, 120, 24, "white")
    ball(c, 130, 0, 55, INK)
    c.drawCircle(130, 0, 30, paint("cyan"))
    c.drawCircle(-110, -30, 12, paint("red", int(150 + 100 * math.sin(t * 6))))
    c.restore()
    rrect(c, -20, 55, 40, 110, 10, "grey")


def p_feather(c, t, p, color="white", **_):
    c.save()
    c.rotate(20 * math.sin(t * 2.5))
    pa = skia.Path()
    pa.moveTo(0, -170)
    pa.cubicTo(90, -80, 70, 80, 0, 170)
    pa.cubicTo(-70, 80, -90, -80, 0, -170)
    c.drawPath(pa, paint(color))
    c.drawLine(0, -150, 0, 200, paint(shade(color, -0.35), stroke=7))
    for i in range(-5, 6):
        y = i * 25
        c.drawLine(0, y, 45, y - 30, paint(shade(color, -0.2), stroke=4))
        c.drawLine(0, y, -45, y - 30, paint(shade(color, -0.2), stroke=4))
    c.restore()


def p_bulb(c, t, p, lit=True, **_):
    if lit:
        glow(c, 0, -30, 200, "yellow", int(110 + 50 * math.sin(t * 4)))
    ball(c, 0, -30, 120, "yellow" if lit else "grey")
    shaded_rrect(c, -55, 80, 110, 80, 16, "grey")


def p_coin(c, t, p, label="$", color="yellow", _zs=1.0, **_):
    sx = abs(math.cos(t * 2.5))
    c.save()
    c.scale(max(0.15, sx), 1)
    ball(c, 0, 0, 100, color)
    c.drawCircle(0, 0, 72, paint(shade(color, -0.2), stroke=8))
    text(c, label, 0, 0, min_size(fit_size(label, 90, 150), _zs), shade(color, -0.35))
    c.restore()


def p_pin(c, t, p, color="red", **_):
    b = -abs(20 * math.sin(t * 3))
    c.drawOval(skia.Rect.MakeXYWH(-50, 150, 100, 26), paint(INK, 80))
    pa = skia.Path()
    pa.moveTo(0, 160 + b)
    pa.cubicTo(-150, -20 + b, -80, -150 + b, 0, -150 + b)
    pa.cubicTo(80, -150 + b, 150, -20 + b, 0, 160 + b)
    c.drawPath(pa, paint(color))
    c.drawCircle(0, -50 + b, 40, paint("white"))


def p_calendar(c, t, p, day=None, label="", pages=False, _zs=1.0, **_):
    flips = int(t * 1.5) if pages else 0
    shaded_rrect(c, -150, -150, 300, 300, 28, "white")
    rrect(c, -150, -150, 300, 80, 28, "red")
    c.drawRect(skia.Rect.MakeXYWH(-150, -100, 300, 30), paint("red"))
    shown = label or str(((day or 1) - 1 + flips) % 31 + 1)
    text(c, shown, 0, 40, min_size(fit_size(shown, 130, 260), _zs), INK)
    for x in (-80, 80):
        rrect(c, x - 10, -175, 20, 60, 10, "grey")


def p_arrow(c, t, p, color="yellow", length=260, angle=0, **_):
    c.save()
    c.rotate(angle)
    L = length * p
    nudge = 10 * math.sin(t * 5)
    c.drawLine(-length / 2, 0, -length / 2 + L + nudge - 40, 0, paint(color, stroke=26))
    x = -length / 2 + L + nudge
    c.drawPath(path([(x, 0), (x - 60, -45), (x - 60, 45)]), paint(color))
    c.restore()


def p_label(c, t, p, label="", size=80, color="white", _zs=1.0, **_):
    size = min_size(fit_size(label, size, 900), _zs)
    text(c, label, 0, 0, size, color, stroke=max(6, size * 0.12))


def p_spectrum(c, t, p, **_):
    import colorsys
    n = 60
    for i in range(int(n * p)):
        r, g, b = colorsys.hsv_to_rgb(0.78 - 0.78 * i / n, 0.85, 1)
        c.drawRect(skia.Rect.MakeXYWH(-420 + i * 14, -55, 15, 110), paint((r * 255, g * 255, b * 255)))
    c.drawRRect(skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(-420, -55, 840, 110), 20, 20), paint(INK, 255, stroke=8))


def p_mountain(c, t, p, color="teal", **_):
    c.drawPath(path([(-450, 200), (-150, -150), (80, 200)]), paint(shade(color, -0.3)))
    c.drawPath(path([(-100, 200), (180, -220), (460, 200)]), paint(color))
    c.drawPath(path([(180, -220), (125, -150), (160, -160), (190, -130), (225, -160)]), paint("white"))


def p_rain(c, t, p, **_):
    for i in range(24):
        x = (i * 73) % 700 - 350
        y = ((i * 131 + t * 500) % 500) - 250
        c.drawLine(x, y, x - 8, y + 36, paint("cyan", 220, stroke=7))


def p_wave(c, t, p, color="blue", **_):
    for i in range(4):
        pa = skia.Path()
        y0 = -60 + i * 50
        pa.moveTo(-600, 900)
        for x in range(-600, 610, 10):
            pa.lineTo(x, y0 + 18 * math.sin(x / 70 + t * 2 + i))
        pa.lineTo(600, 900)
        pa.close()
        c.drawPath(pa, paint(shade(color, -0.12 * i)))


def p_salt(c, t, p, **_):
    for i in range(14):
        x = (i * 97) % 500 - 250
        y = (i * 53) % 220 - 110 + 10 * math.sin(t * 2 + i)
        c.save()
        c.translate(x, y)
        c.rotate(i * 17 + t * 20)
        rrect(c, -18, -18, 36, 36, 5, "white", 230)
        c.restore()




def p_bird(c, t, p, color="grey", peck=True, **_):
    """Pigeon: body, head bob/peck, wing."""
    bob = (abs(math.sin(t * 5)) * 30) if peck else 0
    c.drawOval(skia.Rect.MakeXYWH(-110, 110, 220, 30), paint(INK, 60))
    c.drawLine(-20, 70, -30, 125, paint("orange", stroke=10))
    c.drawLine(20, 70, 25, 125, paint("orange", stroke=10))
    body = skia.Path()
    body.moveTo(-150, 10)
    body.cubicTo(-120, -60, 60, -70, 90, -10)
    body.cubicTo(110, 60, -40, 100, -150, 10)
    c.drawPath(body, paint(shade(color, -0.25)))
    c.save()
    c.translate(-8, -8)
    c.scale(0.94, 0.94)
    c.drawPath(body, paint(color))
    c.restore()
    wing = skia.Path()
    wing.moveTo(-100, -10)
    wing.cubicTo(-40, -45, 30, -30, 40, 10)
    wing.cubicTo(-10, 30, -70, 25, -100, -10)
    c.drawPath(wing, paint(shade(color, -0.15)))
    c.save()
    c.translate(85, -45 + bob)
    c.drawCircle(0, 0, 48, paint(shade(color, -0.2)))
    c.drawCircle(-4, -4, 44, paint(color))
    c.drawPath(path([(38, -8), (72, 6), (38, 16)]), paint("orange"))
    c.drawCircle(14, -12, 12, paint("white"))
    c.drawCircle(17, -12, 6, paint(INK))
    c.drawArc(skia.Rect.MakeXYWH(-40, 10, 70, 50), 20, 140, False, paint("teal", 200, stroke=10))
    c.restore()


def p_robot(c, t, p, color="grey", **_):
    shaded_rrect(c, -110, -60, 220, 200, 30, color)
    shaded_rrect(c, -90, -200, 180, 130, 36, color)
    c.drawLine(0, -200, 0, -240, paint(INK, stroke=8))
    glow(c, 0, -245, 16, "red", int(120 + 100 * math.sin(t * 6)))
    ball(c, 0, -245, 14, "red")
    for ex in (-40, 40):
        c.drawCircle(ex, -140, 22, paint("cyan"))
        c.drawCircle(ex, -140, 10, paint(INK))
    rrect(c, -50, -105, 100, 14, 7, INK)
    a = 30 * math.sin(t * 6)
    for sd in (-1, 1):
        c.save()
        c.translate(sd * 120, -30)
        c.rotate(sd * (20 + (a if sd > 0 else 0)))
        rrect(c, -16, 0, 32, 120, 16, shade(color, -0.15))
        c.restore()
    rrect(c, -55, -20, 110, 70, 14, INK, 120)


def p_heart(c, t, p, color="red", **_):
    s = 1 + 0.08 * max(0, math.sin(t * 7))
    c.save()
    c.scale(s, s)
    h = skia.Path()
    h.moveTo(0, 130)
    h.cubicTo(-190, 10, -140, -150, 0, -60)
    h.cubicTo(140, -150, 190, 10, 0, 130)
    glow(c, 0, 0, 150, color, 70)
    c.drawPath(h, paint(shade(color, -0.25)))
    c.save()
    c.translate(-6, -6)
    c.scale(0.93, 0.93)
    c.drawPath(h, paint(color))
    c.restore()
    c.drawCircle(-70, -50, 18, paint("white", 150))
    c.restore()


def p_speaker(c, t, p, color="grey", **_):
    shaded_rrect(c, -130, -170, 260, 340, 36, color)
    ball(c, 0, 40, 85, INK, light=False)
    c.drawCircle(0, 40, 35 + 6 * math.sin(t * 12), paint("grey"))
    c.drawCircle(0, -100, 30, paint(INK))
    for i in range(3):
        r = 150 + i * 45 + (t * 80) % 45
        c.drawArc(skia.Rect.MakeXYWH(-r, 40 - r, 2 * r, 2 * r), -35, 70, False,
                  paint("white", max(0, 200 - i * 60), stroke=10))


def p_newspaper(c, t, p, headline="NEWS", _zs=1.0, **_):
    c.save()
    c.rotate(-4 + 2 * math.sin(t))
    shaded_rrect(c, -200, -240, 400, 480, 12, "white")
    words = headline.split()
    size = min_size(fit_size(headline, 64, 340), _zs)
    rule_y = -120
    if measure(headline, size) > 350 and len(words) > 1:  # wrap onto two lines rather than overflow
        h = (len(words) + 1) // 2
        lines = [" ".join(words[:h]), " ".join(words[h:])]
        size = min(size, min(fit_size(ln, size, 350) for ln in lines))
        text(c, lines[0], 0, -200, size, INK)
        text(c, lines[1], 0, -200 + size * 1.05, size, INK)
        rule_y = -200 + size * 1.05 + size * 0.75  # the rule always sits below the headline
    else:
        text(c, headline, 0, -170, fit_size(headline, size, 350), INK)
        rule_y = max(rule_y, -170 + size * 0.75)
    c.drawLine(-170, rule_y, 170, rule_y, paint(INK, stroke=6))
    c.save()  # fit the body (y -95..190) between the rule and the bottom of the paper
    k = min(1.0, (225 - (rule_y + 25)) / 285)
    c.translate(0, rule_y + 25)
    c.scale(1, k)
    c.translate(0, 95)
    rrect(c, -170, -95, 160, 130, 8, "grey", 160)
    for i in range(6):
        c.drawLine(10, -85 + i * 22, 170, -85 + i * 22, paint("grey", stroke=8))
    for i in range(5):
        c.drawLine(-170, 70 + i * 30, 170 - (i % 2) * 60, 70 + i * 30, paint("grey", stroke=8))
    c.restore()
    c.restore()


def p_thumb(c, t, p, color="blue", **_):
    """Thumbs-up 'like' badge: fist with stacked fingers on the right, thumb up from the left edge."""
    ball(c, 0, 0, 130, color)
    c.save()
    c.rotate(-6 * math.sin(t * 6))
    c.translate(10, 15)
    skin = "white"
    rrect(c, -78, -30, 34, 100, 12, skin)                     # cuff
    rrect(c, -40, -30, 100, 104, 22, skin)                    # palm/fist
    for i in range(4):                                         # finger segments on the right
        rrect(c, 30, -28 + i * 26, 46, 26, 13, skin)
        c.drawLine(36, -2 + i * 26, 70, -2 + i * 26, paint(shade(color, -0.2), stroke=3))
    c.save()                                                   # thumb from the fist's top-left, pointing up
    c.translate(-30, -26)
    c.rotate(-8)
    rrect(c, -4, -78, 40, 92, 20, skin)
    c.restore()
    c.drawLine(-40, -30, 28, -30, paint(shade(color, -0.2), stroke=3))
    c.restore()

def p_frame(c, t, p, label="", color="brown", _zs=1.0, **_):
    shaded_rrect(c, -180, -150, 360, 300, 16, color)
    rrect(c, -150, -120, 300, 240, 8, "cyan")
    c.drawPath(path([(-150, 120), (-60, 0), (10, 70), (70, 20), (150, 120)]), paint("green"))
    c.drawCircle(80, -60, 30, paint("yellow"))
    if label:
        text(c, label, 0, 200, min_size(fit_size(label, 50, 360), _zs), "white", stroke=8)


def p_crane(c, t, p, color="yellow", **_):
    sw = 30 * math.sin(t * 1.2)
    rrect(c, -30, -250, 60, 450, 6, color)
    for i in range(8):
        c.drawLine(-30, -240 + i * 55, 30, -210 + i * 55, paint(shade(color, -0.3), stroke=6))
    rrect(c, -200, -270, 420, 36, 6, color)
    x = 150 + sw
    c.drawLine(x, -234, x, -40, paint(INK, stroke=5))
    shaded_rrect(c, x - 70, -40, 140, 65, 6, "blue")



def p_tv(c, t, p, label="", people=3, **_):
    """CCTV monitor showing figures; scanlines and a REC dot."""
    shaded_rrect(c, -230, -170, 460, 320, 26, "grey")
    rrect(c, -205, -145, 410, 250, 12, (20, 40, 36))
    c.save()
    c.clipRect(skia.Rect.MakeXYWH(-205, -145, 410, 250))
    for i in range(people):
        x = -140 + i * (280 / max(1, people - 1)) + 10 * math.sin(t * 2 + i)
        c.drawCircle(x, -40, 26, paint((120, 220, 160), 220))
        rrect(c, x - 26, -10, 52, 90, 22, (120, 220, 160), 220)
    for y in range(-145, 105, 10):
        c.drawLine(-205, y + (t * 40) % 10, 205, y + (t * 40) % 10, paint((0, 0, 0), 50, stroke=3))
    c.restore()
    c.drawCircle(-175, -120, 10, paint("red", int(150 + 100 * math.sin(t * 6))))
    text(c, "REC", -130, -120, 26, "red")
    rrect(c, -40, 150, 80, 50, 8, "grey")
    if label:
        text(c, label, 0, 240, fit_size(label, 50, 440), "white", stroke=8)


def p_package(c, t, p, color="orange", label="", **_):
    """Product box with a tag."""
    c.drawOval(skia.Rect.MakeXYWH(-150, 150, 300, 36), paint(INK, 70))
    top = path([(-150, -60), (0, -130), (150, -60), (0, 10)])
    c.drawPath(top, paint(shade(color, 0.25)))
    c.drawPath(path([(-150, -60), (0, 10), (0, 170), (-150, 100)]), paint(color))
    c.drawPath(path([(150, -60), (0, 10), (0, 170), (150, 100)]), paint(shade(color, -0.25)))
    c.drawPath(path([(-75, -95), (75, -25), (75, 10), (-75, -60)]), paint("white", 120))
    if label:
        rrect(c, 40, -10, 150, 64, 14, "white")
        text(c, label, 115, 22, fit_size(label, 40, 130), INK)


ACTIVITIES = ("telescope", "book", "globe", "puzzle", "abacus", "magnifier", "chess", "notebook", "flask", "cube")


def _activity(c, t, kind):
    """One 'thinking' prop for Mr. Shorts, drawn to his left (he sits in the right-hand corner)."""
    brass, wood, navy = (230, 180, 70), (150, 96, 60), (40, 50, 110)
    if kind == "telescope":
        for dx in (-50, 0, 50):  # tripod
            c.drawLine(-175, 20, -175 + dx, 172, paint(wood, stroke=10))
        c.save()
        c.translate(-175, 20)
        c.rotate(-28 + 3 * math.sin(t * 0.8))
        rrect(c, -170, -24, 250, 48, 10, navy)
        rrect(c, -190, -32, 40, 64, 8, brass)
        rrect(c, 60, -18, 60, 36, 8, brass)
        c.restore()
        tw = 0.5 + 0.5 * math.sin(t * 5)
        for a in range(4):
            c.save()
            c.translate(-360, -150)
            c.rotate(a * 45)
            c.drawLine(-22 * tw - 8, 0, 22 * tw + 8, 0, paint("yellow", stroke=6))
            c.restore()
    elif kind == "book":
        flip = (t % 3.6) / 0.5  # a page turns every few seconds
        c.drawPath(path([(-150, 40), (-20, 60), (-20, 150), (-150, 128)]), paint("white"))
        c.drawPath(path([(110, 40), (-20, 60), (-20, 150), (110, 128)]), paint("white"))
        for i in range(4):
            c.drawLine(-135, 62 + i * 18, -40, 76 + i * 18, paint("grey", 170, stroke=5))
            c.drawLine(95, 62 + i * 18, 0, 76 + i * 18, paint("grey", 170, stroke=5))
        if flip < 1:
            x = 110 - 260 * flip
            c.drawPath(path([(x, 40 - 30 * math.sin(math.pi * flip)), (-20, 60), (-20, 150), (x, 128 - 30 * math.sin(math.pi * flip))]),
                       paint((235, 232, 222)))
        c.drawPath(path([(-158, 46), (-20, 68), (118, 46), (118, 136), (-20, 158), (-158, 136)]), paint(wood, stroke=12))
    elif kind == "globe":
        rrect(c, -230, 150, 110, 22, 8, wood)
        c.drawLine(-175, 150, -175, 110, paint(wood, stroke=12))
        c.drawArc(skia.Rect.MakeXYWH(-262, -62, 174, 174), 60, 200, False, paint(brass, stroke=10))
        c.save()
        c.translate(-175, 25)
        c.scale(0.5, 0.5)
        p_planet(c, t * 2.2, 1.0, atmosphere=None)
        c.restore()
    elif kind == "puzzle":
        cols = ("teal", "orange", "pink", "yellow")
        drop = abs(math.sin(t * 1.4))
        for i, (x, y) in enumerate(((-250, 110), (-180, 110), (-250, 40), (-180, 40))):
            yy = y - (70 * drop if i == 3 else 0)
            rrect(c, x, yy, 66, 66, 10, cols[i])
            c.drawCircle(x + 33, yy - 4, 13, paint(cols[i]))
            c.drawCircle(x + 70, yy + 33, 13, paint(shade(cols[i], -0.2)))
    elif kind == "abacus":
        rrect(c, -270, -10, 170, 180, 12, wood)
        rrect(c, -256, 4, 142, 152, 6, (60, 40, 30))
        for r in range(3):
            y = 30 + r * 50
            c.drawLine(-256, y, -114, y, paint(brass, stroke=5))
            shift = 34 * (0.5 + 0.5 * math.sin(t * 1.6 + r * 2.1))
            for b in range(3):
                c.drawCircle(-240 + b * 26 + (shift if b == 2 else 0), y, 13, paint(("red", "yellow", "cyan")[r]))
    elif kind == "magnifier":
        c.save()
        c.translate(-70 + 10 * math.sin(t * 1.2), -52)
        c.drawLine(-50, 50, -130, 150, paint(wood, stroke=20))
        c.drawCircle(0, 0, 78, paint("cyan", 70))
        c.drawCircle(4, 4, 30, paint(INK))            # the eye, magnified
        c.drawCircle(-8, -8, 11, paint("white"))
        c.drawCircle(0, 0, 78, paint(brass, stroke=14))
        c.restore()
    elif kind == "chess":
        rrect(c, -290, 120, 200, 50, 8, wood)
        for i in range(4):
            c.drawRect(skia.Rect.MakeXYWH(-282 + i * 46, 126, 46, 20), paint("white" if i % 2 else INK))
        slide = 46 * (0.5 + 0.5 * math.sin(t * 1.1))
        for x, col, king in ((-260, "white", False), (-168 - slide, INK, True)):
            c.drawPath(path([(x - 16, 126), (x + 16, 126), (x + 9, 86), (x - 9, 86)]), paint(col))
            c.drawCircle(x, 76, 14, paint(col))
            if king:
                c.drawLine(x, 52, x, 66, paint(col, stroke=6))
                c.drawLine(x - 7, 58, x + 7, 58, paint(col, stroke=6))
    elif kind == "notebook":
        c.save()
        c.translate(-170, 70)
        c.rotate(-10)
        rrect(c, -75, -95, 150, 190, 10, wood)
        rrect(c, -62, -80, 124, 162, 4, "white")
        n_lines = 1 + int(t * 1.2) % 5
        for i in range(n_lines):
            w = 96 if i < n_lines - 1 else 96 * ((t * 1.2) % 1)
            c.drawLine(-50, -58 + i * 28, -50 + w, -58 + i * 28, paint(navy, stroke=5))
        c.restore()
        px, py = -215 + 96 * ((t * 1.2) % 1), 20 + 28 * (int(t * 1.2) % 5)
        c.drawLine(px, py, px + 50, py - 70, paint("yellow", stroke=12))
        c.drawLine(px, py, px + 7, py - 10, paint(INK, stroke=12))
    elif kind == "flask":
        fl = path([(-205, -20), (-165, -20), (-165, 50), (-110, 165), (-260, 165), (-205, 50)])
        c.drawPath(fl, paint("white", 70))
        c.drawPath(path([(-190, 80), (-180, 80), (-118, 160), (-252, 160)]), paint("green"))
        for i in range(4):
            yy = 150 - ((t * 60 + i * 37) % 150)
            c.drawCircle(-185 + 14 * math.sin(i * 2 + t * 2), yy, 6 + i % 3 * 2, paint("green", 200))
        c.drawPath(fl, paint("white", 230, stroke=8))
    elif kind == "cube":
        cols = ("red", "yellow", "blue", "green", "orange", "white")
        step = int(t * 1.3)
        c.save()
        c.translate(-175, 60)
        c.rotate(8 * math.sin(t * 1.3))
        rrect(c, -78, -78, 156, 156, 14, INK)
        for r in range(3):
            for q in range(3):
                rrect(c, -70 + q * 48, -70 + r * 48, 44, 44, 8, cols[(r * 3 + q + (step if r == step % 3 else 0)) % 6])
        c.restore()


def p_mascot(c, t, p, talk=0.0, look=0.0, mood="smirk", wave=False, hop=0.0, activity=None, **_):
    """Mr. Shorts: a small round owl with big glasses, a raised eyebrow and red shorts.
    talk 0..1 opens the beak, look -1..1 moves the pupils, hop 0..1 lifts him off the ground."""
    body_c, wing_c, beak_c = (246, 240, 228), (124, 92, 214), (255, 150, 60)
    lift = -70 * math.sin(math.pi * max(0.0, min(1.0, hop)))
    c.drawOval(skia.Rect.MakeXYWH(-95 + abs(lift) * 0.2, 168, 190 - abs(lift) * 0.4, 28), paint(INK, 70))
    c.save()
    c.translate(0, lift)
    sq = 1 + 0.02 * math.sin(t * 2.6)  # breathing
    c.scale(1 / sq, sq)
    for sx in (-1, 1):  # feet
        c.drawOval(skia.Rect.MakeXYWH(sx * 48 - 30, 150, 60, 26), paint(beak_c))
    for sx in (-1, 1):  # ear tufts
        c.drawPath(path([(sx * 40, -150), (sx * 112, -205), (sx * 104, -110)]), paint(wing_c))
    body = skia.Path()
    body.addOval(skia.Rect.MakeXYWH(-125, -160, 250, 320))
    c.drawPath(body, paint(shade(body_c, -0.2)))
    c.save()
    c.clipPath(body, doAntiAlias=True)
    c.drawOval(skia.Rect.MakeXYWH(-135, -172, 250, 320), paint(body_c))
    c.drawRect(skia.Rect.MakeXYWH(-140, 62, 280, 120), paint("red"))          # the shorts
    c.drawRect(skia.Rect.MakeXYWH(-140, 62, 280, 18), paint(shade(PAL["red"], -0.3)))  # waistband
    c.drawLine(0, 78, 0, 170, paint(shade(PAL["red"], -0.3), stroke=6))
    c.drawOval(skia.Rect.MakeXYWH(40, -150, 160, 330), paint(INK, 22))       # soft side shading
    c.restore()
    for sx in (-1, 1):  # wings; the right one waves when asked
        c.save()
        c.translate(sx * 118, -10)
        ang = sx * 14 + (sx * 4 * math.sin(t * 2.2))
        if wave and sx > 0:
            ang = -152 + 18 * math.sin(t * 9)
        c.rotate(ang)
        c.drawOval(skia.Rect.MakeXYWH(-26, -8, 52, 118), paint(wing_c))
        c.drawOval(skia.Rect.MakeXYWH(-18, -2, 34, 96), paint(shade(wing_c, 0.18)))
        c.restore()
    # eyes behind big round glasses
    blink = abs(((t + 0.4) % 3.4) - 0.1) < 0.07
    for sx in (-1, 1):
        ex = sx * 56
        c.drawCircle(ex, -52, 50, paint("white"))
        if blink:
            c.drawLine(ex - 26, -50, ex + 26, -50, paint(INK, stroke=8))
        else:
            px = ex + 14 * max(-1.0, min(1.0, look))
            c.drawCircle(px, -48, 22, paint(INK))
            c.drawCircle(px - 8, -57, 8, paint("white"))
        c.drawCircle(ex, -52, 52, paint(INK, stroke=10))
    c.drawLine(-8, -56, 8, -56, paint(INK, stroke=10))                       # bridge
    # eyebrows: the right one is cocked, which is where the wit lives
    lift_b = {"smirk": 16, "curious": 22, "happy": 6}.get(mood, 12)
    c.drawLine(-88, -120, -30, -116, paint(wing_c, stroke=11))
    c.drawLine(30, -118 - lift_b * 0.4, 90, -124 - lift_b, paint(wing_c, stroke=11))
    # beak opens with speech
    op = 16 * max(0.0, min(1.0, talk))
    c.drawPath(path([(-22, 6 - op * 0.3), (22, 6 - op * 0.3), (0, 26 - op * 0.3)]), paint(beak_c))
    if op > 1:
        c.drawPath(path([(-16, 12 + op * 0.4), (16, 12 + op * 0.4), (0, 22 + op)]), paint(shade(beak_c, -0.25)))
    elif mood in ("smirk", "happy"):
        sm = skia.Path()
        sm.moveTo(6, 34)
        sm.quadTo(26, 44, 40, 28)
        c.drawPath(sm, paint(INK, stroke=6))
    c.restore()
    if activity:
        _activity(c, t, activity)


# ---------------- v3: faces for any object, and brain-science props ----------------

def face(c, t, mood="happy", s=1.0, ink=INK):
    """A simple face that can sit on any prop, so every object can be a character."""
    c.save()
    c.scale(s, s)
    blink = abs(((t + 0.3) % 3.1) - 0.1) < 0.07 and mood not in ("dizzy", "stars", "shocked")
    for sx in (-1, 1):
        ex = sx * 34
        if mood == "dizzy":
            for a in (45, -45):
                c.save()
                c.translate(ex, -8)
                c.rotate(a)
                c.drawLine(-13, 0, 13, 0, paint(ink, stroke=7))
                c.restore()
        elif mood == "sleepy" or blink:
            c.drawArc(skia.Rect.MakeXYWH(ex - 15, -18, 30, 22), 20, 140, False, paint(ink, stroke=7))
        else:
            r = 21 if mood == "shocked" else 17
            c.drawCircle(ex, -8, r, paint("white"))
            if mood == "stars":
                for a in range(4):
                    c.save()
                    c.translate(ex, -8)
                    c.rotate(a * 45 + t * 60)
                    c.drawLine(-12, 0, 12, 0, paint("yellow", stroke=6))
                    c.restore()
            else:
                c.drawCircle(ex + 4 * math.sin(t * 1.3), -7, 9 if mood != "shocked" else 7, paint(ink))
        if mood == "angry":
            c.drawLine(ex - sx * 20, -40, ex + sx * 14, -28, paint(ink, stroke=7))
        elif mood == "worried":
            c.drawLine(ex - sx * 18, -32, ex + sx * 14, -40, paint(ink, stroke=6))
    m = skia.Path()
    if mood in ("happy", "stars"):
        m.moveTo(-20, 22)
        m.quadTo(0, 44, 20, 22)
        c.drawPath(m, paint(ink, stroke=7))
    elif mood == "shocked":
        c.drawOval(skia.Rect.MakeXYWH(-10, 20, 20, 26), paint(ink))
    elif mood in ("worried", "dizzy", "angry"):
        m.moveTo(-18, 36)
        m.quadTo(0, 20, 18, 36)
        c.drawPath(m, paint(ink, stroke=7))
    elif mood == "smug":
        m.moveTo(-14, 28)
        m.quadTo(8, 38, 22, 22)
        c.drawPath(m, paint(ink, stroke=7))
    else:
        c.drawLine(-14, 30, 14, 30, paint(ink, stroke=7))
    c.restore()


def p_molecule(c, t, p, color="yellow", mood="smug", atoms=5, **_):
    """A small molecule character: a cluster of glowing atoms with a face on the biggest one."""
    glow(c, 0, 0, 150, color, 110)
    for i in range(int(atoms)):
        a = i * 2.4 + 0.5
        r = 78 + 10 * math.sin(t * 2 + i)
        x, y = r * math.cos(a), r * math.sin(a) * 0.85
        c.drawLine(0, 0, x, y, paint(shade(color, -0.35), stroke=14))
        ball(c, x, y, 34 + (i % 2) * 8, shade(color, 0.25 if i % 2 else -0.1))
    ball(c, 0, 0, 78, color)
    face(c, t, mood, 0.95)


def p_receptor(c, t, p, color="purple", lid=0.0, mood=None, **_):
    """A cell-surface receptor: a cup embedded in a membrane. `lid` 0..1 folds a flap over the pocket."""
    for i in range(-5, 6):  # membrane: two rows of lipid beads
        for y in (70, 118):
            ball(c, i * 62 + 8 * math.sin(t * 1.5 + i), y, 26, shade(color, -0.45), light=False)
    cup = skia.Path()
    cup.moveTo(-150, -150)
    cup.cubicTo(-150, 20, -110, 150, 0, 150)
    cup.cubicTo(110, 150, 150, 20, 150, -150)
    cup.lineTo(84, -150)
    cup.cubicTo(84, -20, 60, 40, 0, 40)
    cup.cubicTo(-60, 40, -84, -20, -84, -150)
    cup.close()
    c.save()
    c.translate(8, 10)
    c.drawPath(cup, paint(shade(color, -0.3)))
    c.restore()
    c.drawPath(cup, paint(color))
    c.drawPath(cup, paint(shade(color, 0.3), stroke=6))
    k = max(0.0, min(1.0, float(lid)))  # the lid swings down from the right rim
    c.save()
    c.translate(150, -150)
    c.rotate(-150 + 150 * k)
    c.drawRRect(skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(-300, -26, 300, 52), 26, 26), paint(shade(color, 0.25)))
    c.drawRRect(skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(-300, -26, 300, 52), 26, 26), paint(shade(color, -0.3), stroke=6))
    c.restore()
    if mood:
        c.save()
        c.translate(0, 100)
        face(c, t, mood, 0.8)
        c.restore()


def p_neuron(c, t, p, color="cyan", mood="happy", fire=0.0, **_):
    """A nerve cell with branching arms; `fire` 0..1 lights it up."""
    f = max(0.0, min(1.0, float(fire)))
    if f > 0:
        glow(c, 0, 0, 230, "yellow", int(170 * f))
    for i in range(7):
        a = i * 0.9 + 0.3
        pa = skia.Path()
        pa.moveTo(0, 0)
        x1, y1 = 150 * math.cos(a), 150 * math.sin(a)
        x2 = 250 * math.cos(a + 0.3 * math.sin(t * 1.4 + i))
        y2 = 250 * math.sin(a + 0.3 * math.sin(t * 1.4 + i))
        pa.quadTo(x1 * 1.2, y1 * 0.8, x2, y2)
        c.drawPath(pa, paint(shade(color, -0.2), stroke=24 - i % 3 * 5))
        ball(c, x2, y2, 16, shade(color, 0.3))
    ball(c, 0, 0, 110, color)
    c.drawCircle(0, 0, 60, paint(shade(color, -0.25)))
    face(c, t, mood, 1.0)


def p_network(c, t, p, color="pink", links=0.0, **_):
    """Brain regions as nodes. `links` 0..1 draws more and more connections between them."""
    pts = [(-170, -150), (0, -210), (170, -150), (-220, 20), (-60, -20), (90, 10), (220, 40), (-130, 180), (30, 170), (170, 190)]
    cols = ("pink", "cyan", "yellow", "green", "orange", "violet")
    pairs = [(i, j) for i in range(len(pts)) for j in range(i + 1, len(pts))]
    near = [pr for pr in pairs if math.hypot(pts[pr[0]][0] - pts[pr[1]][0], pts[pr[0]][1] - pts[pr[1]][1]) < 200]
    far = [pr for pr in pairs if pr not in near]
    k = max(0.0, min(1.0, float(links)))
    for n, (i, j) in enumerate(near + far[:int(len(far) * k)]):
        hot = n >= len(near)
        a = 150 + 100 * math.sin(t * 4 + n) if hot else 130
        c.drawLine(*pts[i], *pts[j], paint(cols[n % 6] if hot else "white", int(a), stroke=9 if hot else 6))
    for i, (x, y) in enumerate(pts):
        r = 30 + 5 * math.sin(t * 3 + i) * (1 + k)
        glow(c, x, y, r * 1.6, cols[i % 6], int(60 + 120 * k))
        ball(c, x, y, r, cols[i % 6])


def p_rays(c, t, p, color="yellow", n=14, **_):
    """Rotating burst of rays, for a reveal behind a subject."""
    c.save()
    c.rotate(t * 14)
    for i in range(int(n)):
        c.save()
        c.rotate(i * 360 / n)
        c.drawPath(path([(0, 0), (-40, -520), (40, -520)]), paint(color, 70 if i % 2 else 120))
        c.restore()
    c.restore()


def p_rings(c, t, p, colors=("pink", "yellow", "cyan", "violet", "orange", "green"), **_):
    """Concentric rings drifting outward with cycling colours: a stylised 'altered perception' pattern."""
    for i in range(9, 0, -1):
        r = (i * 60 + t * 55) % 540 + 20
        wob = 1 + 0.06 * math.sin(t * 3 + i)
        c.drawOval(skia.Rect.MakeXYWH(-r * wob, -r / wob, 2 * r * wob, 2 * r / wob),
                   paint(colors[(i + int(t * 2)) % len(colors)], 215, stroke=26))


def p_bike(c, t, p, color="orange", rider="white", mood="dizzy", **_):
    """A wobbling cyclist: two spinning wheels, a simple frame and a blob rider."""
    c.save()
    c.rotate(5 * math.sin(t * 4))
    for wx in (-130, 130):
        c.drawCircle(wx, 110, 78, paint(INK, stroke=16))
        c.drawCircle(wx, 110, 62, paint("white", 60))
        for k in range(4):
            a = t * 6 + k * math.pi / 2
            c.drawLine(wx, 110, wx + 62 * math.cos(a), 110 + 62 * math.sin(a), paint("white", 200, stroke=5))
    for a, b in (((-130, 110), (-30, -10)), ((-30, -10), (90, -10)), ((90, -10), (130, 110)), ((-30, -10), (10, 110)), ((10, 110), (-130, 110))):
        c.drawLine(*a, *b, paint(color, stroke=16))
    c.drawLine(90, -10, 96, -60, paint(INK, stroke=12))
    c.drawLine(70, -62, 122, -58, paint(INK, stroke=12))
    c.save()
    c.translate(-30, -150)
    c.scale(0.85, 0.85)
    p_person(c, t, 1.0, color=rider, mood=mood)
    c.restore()
    c.restore()


def p_hat(c, t, p, color="violet", **_):
    """A pointy witch hat (put it above a character)."""
    c.save()
    c.rotate(4 * math.sin(t * 3))
    c.drawPath(path([(-70, 40), (10, -170), (40, -150), (70, 40)]), paint(color))
    c.drawPath(path([(10, -170), (40, -150), (60, -175)]), paint(shade(color, -0.25)))
    c.drawOval(skia.Rect.MakeXYWH(-150, 20, 300, 60), paint(shade(color, -0.25)))
    c.drawRect(skia.Rect.MakeXYWH(-66, 4, 132, 26), paint("yellow"))
    c.restore()


def p_scanner(c, t, p, color="white", **_):
    """A brain scanner: a big ring with a glowing bore and a bed."""
    shaded_rrect(c, -230, -210, 460, 420, 90, color)
    glow(c, 0, 0, 150, "cyan", int(120 + 60 * math.sin(t * 4)))
    c.drawCircle(0, 0, 135, paint(INK))
    c.drawCircle(0, 0, 135, paint("cyan", 200, stroke=10))
    for i in range(3):
        c.drawCircle(-170 + i * 36, -170, 9, paint(("green", "yellow", "red")[i], int(150 + 100 * math.sin(t * 5 + i))))
    rrect(c, -150, 160, 300, 46, 18, shade(rgb(color), -0.2))


def p_xray(c, t, p, **_):
    """An X-ray source firing a beam at a small crystal that sparkles."""
    shaded_rrect(c, -330, -70, 170, 140, 22, "grey")
    c.drawCircle(-170, 0, 26, paint("cyan"))
    beam = path([(-160, -14), (150, -46), (150, 46), (-160, 14)])
    c.drawPath(beam, paint("cyan", int(110 + 70 * math.sin(t * 14))))
    c.save()
    c.translate(200, 0)
    c.rotate(t * 30)
    gem = path([(0, -80), (70, -20), (44, 70), (-44, 70), (-70, -20)])
    glow(c, 0, 0, 110, "white", 110)
    c.drawPath(gem, paint("cyan"))
    c.drawPath(path([(0, -80), (70, -20), (0, 0)]), paint("white", 150))
    c.drawPath(gem, paint("white", 230, stroke=6))
    c.restore()


def p_stream(c, t, p, color="red", riders=4, rider_color="yellow", **_):
    """A blood vessel seen from the side: cells drift along, with a few small molecules riding the flow."""
    rrect(c, -520, -170, 1040, 340, 150, shade(color, -0.35))
    rrect(c, -520, -140, 1040, 280, 130, color)
    for i in range(9):
        x = ((i * 137 + t * 90) % 1100) - 550
        y = -90 + (i * 53) % 180
        c.drawOval(skia.Rect.MakeXYWH(x - 44, y - 30, 88, 60), paint(shade(color, -0.2)))
        c.drawOval(skia.Rect.MakeXYWH(x - 26, y - 16, 52, 32), paint(shade(color, -0.35)))
    n = max(0.0, float(riders))
    for i in range(int(math.ceil(n))):
        a = min(1.0, n - i)
        x = ((i * 251 + t * 120) % 1100) - 550
        y = -70 + (i * 71) % 150
        glow(c, x, y, 34, rider_color, int(120 * a))
        ball(c, x, y, 24, rider_color, int(255 * a))

# ---------------- infographic props (text-led beats) ----------------

def p_big(c, t, p, big="?", sub="", color=None, accent="yellow", _zs=1.0, **_):
    size = fit_size(big, 230, 860)
    text(c, big, 0, -30, size, color or accent, stroke=14)
    if sub:
        text(c, sub, 0, size * 0.55 + 30, min_size(fit_size(sub, 64, 860), _zs), "white", stroke=9)


def p_question(c, t, p, big="?", sub="", accent="yellow", _zs=1.0, **_):
    glow(c, 0, -40, 230, accent, 70)
    ball(c, 0, -40, 200, accent)
    text(c, big, 0, -40, fit_size(big, 260, 330), "white", stroke=14)
    if sub:
        text(c, sub, 0, 250, min_size(fit_size(sub, 60, 860), _zs), "white", stroke=9)


def p_bars(c, t, p, bars=(), sub="", accent="yellow", _zs=1.0, **_):
    bars = list(bars)[:4]
    top = -95 * len(bars) + 40
    for i, (lab, v, *cl) in enumerate(bars):
        k = max(0.0, min(1.0, (t * 1.6 - i * 0.25)))
        k = 1 - (1 - k) ** 3
        y = top + i * 180
        text(c, str(lab), -430, y - 42, min_size(fit_size(str(lab), 50, 860), _zs), "white", stroke=8, align="l")
        rrect(c, -430, y, 860, 68, 34, INK, 110)
        w = 860 * max(0.0, min(1.0, float(v))) * k
        if k > 0 and float(v) > 0:
            shaded_rrect(c, -430, y, max(68, w), 68, 34, cl[0] if cl else accent)  # small values: a short pill
    if sub:
        text(c, sub, 0, top + len(bars) * 180 + 20, min_size(fit_size(sub, 52, 860), _zs), "white", stroke=8)


def p_list(c, t, p, items=(), accent="yellow", _zs=1.0, **_):
    items = list(items)[:3]
    top = -100 * (len(items) - 1)
    for i, it in enumerate(items):
        k = max(0.0, min(1.0, t * 2 - i * 0.35))
        k = 1 - (1 - k) ** 3
        if k <= 0:
            continue
        y = top + i * 200
        x = -440 - 80 * (1 - k)
        rrect(c, x, y - 72, 880, 144, 40, INK, int(120 * k))
        ball(c, x + 75, y, 44, accent, int(255 * k))
        text(c, str(i + 1), x + 75, y, 54, INK, int(255 * k))
        text(c, it, x + 145, y, min_size(fit_size(it, 60, 700), _zs), "white", int(255 * k), align="l")


def p_versus(c, t, p, left="", right="", sub="", accent="yellow", lcolor=None, rcolor="white", _zs=1.0, **_):
    k = min(1.0, t * 2.2)
    k = 1 - (1 - k) ** 3
    for sd, lab, cl in ((-1, left, lcolor or accent), (1, right, rcolor)):
        x = sd * 230 + sd * 300 * (1 - k)
        shaded_rrect(c, x - 200, -170, 400, 280, 44, cl)
        text(c, lab, x, -30, fit_size(lab, 84, 350), INK if cl in ("white", "yellow") else "white")
    ball(c, 0, -30, 70 * k, INK)
    text(c, "VS", 0, -30, 56 * k + 1, "yellow")
    if sub:
        text(c, sub, 0, 200, min_size(fit_size(sub, 56, 860), _zs), "white", stroke=8)


def p_timeline(c, t, p, points=(), accent="yellow", _zs=1.0, **_):
    pts = list(points)[:4]
    k = min(1.0, t * 1.4)
    c.drawLine(-400, 0, -400 + 800 * (1 - (1 - k) ** 3), 0, paint(accent, stroke=12))
    for i, (when, what) in enumerate(pts):
        x = -400 + 800 * (i / max(1, len(pts) - 1))
        ki = max(0.0, min(1.0, t * 2 - i * 0.35))
        if ki <= 0:
            continue
        ball(c, x, 0, 30 * ki, accent)
        up = i % 2 == 0
        text(c, when, x, -95 if up else 95, fit_size(when, 66, 300), accent, stroke=9)
        text(c, what, x, -170 if up else 170, min_size(fit_size(what, 42, 260), _zs), "white", stroke=7)


PROPS = {k[2:]: v for k, v in globals().items() if k.startswith("p_")}
