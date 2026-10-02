#!/usr/bin/env python3
"""Channel branding for @mrshorts1737, drawn with the same art library as the Shorts.

    .venv/bin/python branding.py branding/

Writes logo.png (1024x1024, safe inside YouTube's circle crop), logo_small.png (98x98 preview),
banner.png (2560x1440 with the text inside the 1546x423 area every device shows) and watermark.png.
"""
import math, os, random, sys
import skia
import art

NAME, TAGLINE = "MR. SHORTS", "Big questions. Short answers."
RINGS = ((-30, "cyan"), (30, "pink"), (0, "yellow"))  # front halves pass below the face, never across the eyes


def surface(w, h):
    return skia.Surface.MakeRaster(skia.ImageInfo.Make(w, h, skia.kRGBA_8888_ColorType, skia.kPremul_AlphaType))


def cosmos(c, w, h, seed, cx=None, cy=None):
    """Deep violet space with a warm glow behind the subject, soft nebula clouds and stars."""
    cx, cy = cx or w / 2, cy or h / 2
    c.drawPaint(skia.Paint(Shader=skia.GradientShader.MakeRadial(
        skia.Point(cx, cy), max(w, h) * 0.75,
        [art.col((120, 60, 200)), art.col((52, 22, 120)), art.col((14, 10, 46))], [0.0, 0.45, 1.0])))
    rnd = random.Random(seed)
    for colr in ("pink", "cyan", "violet", "orange"):
        for _ in range(2):
            c.drawCircle(rnd.uniform(0, w), rnd.uniform(0, h), rnd.uniform(0.18, 0.34) * max(w, h),
                         art.paint(colr, 26, blur=max(w, h) * 0.09))
    for _ in range(int(w * h / 9000)):
        x, y, r = rnd.uniform(0, w), rnd.uniform(0, h), rnd.uniform(1.2, 4.2)
        c.drawCircle(x, y, r, art.paint("white", rnd.randint(90, 230)))
        if r > 3.6:  # a few four-point sparkles
            for a in (0, 90):
                c.save()
                c.translate(x, y)
                c.rotate(a)
                c.drawLine(-r * 4, 0, r * 4, 0, art.paint("white", 200, stroke=2))
                c.restore()


def orbits(c, r, t=0.6):
    """Three tilted orbits with glowing electrons, drawn half behind and half in front for depth."""
    def ring(rot, colr, front):
        c.save()
        c.rotate(rot)
        rect = skia.Rect.MakeXYWH(-r, -r * 0.34, 2 * r, r * 0.68)
        start, sweep = (0, 180) if front else (180, 180)
        c.drawArc(rect, start, sweep, False, art.paint(colr, 235 if front else 130, stroke=r * 0.03))
        if front:
            a = math.radians(40 + rot)
            x, y = r * math.cos(a), r * 0.34 * math.sin(a)
            art.glow(c, x, y, r * 0.09, colr, 200)
            art.ball(c, x, y, r * 0.055, colr)
        c.restore()
    return ring


def owl(c, x, y, s, **kw):
    c.save()
    c.translate(x, y)
    c.scale(s, s)
    c.saveLayer(None, skia.Paint(ImageFilter=skia.ImageFilters.DropShadow(10, 22, 18, 18, skia.Color(8, 4, 40, 130))))
    art.PROPS["mascot"](c, 1.7, 1.0, **kw)
    c.restore()
    c.restore()


def lettering(c, s, x, y, size, fill="white", accent="yellow"):
    """Chunky rounded lettering with a dark outline and an offset colour shadow."""
    art.text(c, s, x + size * 0.05, y + size * 0.07, size, art.shade(art.rgb(accent), -0.5))
    art.text(c, s, x, y, size, fill, stroke=size * 0.14, stroke_color=art.INK)
    art.text(c, s, x, y, size, fill)


def logo(path, size=1024):
    sf = surface(size, size)
    c = sf.getCanvas()
    cosmos(c, size, size, "logo")
    c.save()
    c.translate(size / 2, size / 2 + 10)
    art.glow(c, 0, 0, size * 0.33, "yellow", 70)
    ring = orbits(c, size * 0.44)
    for rot, colr in RINGS:
        ring(rot, colr, False)
    c.restore()
    owl(c, size / 2, size / 2 + 34, size / 520, look=0.0, mood="smirk")
    c.save()
    c.translate(size / 2, size / 2 + 10)
    for rot, colr in RINGS:
        ring(rot, colr, True)
    c.restore()
    sf.makeImageSnapshot().save(path, skia.kPNG)


def banner(path, w=2560, h=1440):
    sf = surface(w, h)
    c = sf.getCanvas()
    cosmos(c, w, h, "banner")
    sx0, sy0, sw, sh = (w - 1546) / 2, (h - 423) / 2, 1546, 423  # area shown on every device
    # scenery outside the safe area (seen on desktop and TV)
    deco = [("planet", 300, 330, 1.5, {}), ("brain", 2230, 1090, 1.3, {}), ("molecule", 2180, 300, 1.1, {"mood": "happy"}),
            ("neuron", 380, 1120, 0.9, {"fire": 1.0, "mood": "stars"}), ("molecule", 1280, 1230, 0.8, {"color": "cyan", "mood": "smug"}),
            ("hourglass", 1700, 210, 0.9, {}), ("network", 860, 240, 0.75, {"links": 0.6})]
    for name, x, y, s, kw in deco:
        c.save()
        c.translate(x, y)
        c.scale(s, s)
        c.saveLayer(None, skia.Paint(ImageFilter=skia.ImageFilters.DropShadow(10, 18, 16, 16, skia.Color(8, 4, 40, 120))))
        art.PROPS[name](c, 1.3, 1.0, **kw)
        if name == "brain":
            c.translate(-20, -20)
            art.face(c, 1.3, "stars", 1.3)
        c.restore()
        c.restore()
    # safe area: owl + name + tagline
    art.glow(c, sx0 + 160, sy0 + sh / 2, 230, "yellow", 60)
    owl(c, sx0 + 160, sy0 + sh / 2 + 6, 0.95, look=0.8, mood="smirk", activity=None)
    lettering(c, NAME, sx0 + 930, sy0 + 150, 180)
    art.text(c, TAGLINE, sx0 + 930, sy0 + 312, 72, "white", stroke=12)
    art.text(c, TAGLINE, sx0 + 930, sy0 + 312, 72, "yellow")
    sf.makeImageSnapshot().save(path, skia.kPNG)


def watermark(path, size=300):
    sf = surface(size, size)
    c = sf.getCanvas()
    c.clear(skia.Color(0, 0, 0, 0))
    owl(c, size / 2, size / 2 + 8, size / 470, look=0.0, mood="smirk")
    sf.makeImageSnapshot().save(path, skia.kPNG)


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else "branding"
    os.makedirs(out, exist_ok=True)
    logo(os.path.join(out, "logo.png"))
    img = skia.Image.open(os.path.join(out, "logo.png")).resize(98, 98)
    img.save(os.path.join(out, "logo_small.png"), skia.kPNG)
    banner(os.path.join(out, "banner.png"))
    watermark(os.path.join(out, "watermark.png"))
    print("wrote", ", ".join(sorted(os.listdir(out))))


if __name__ == "__main__":
    main()
