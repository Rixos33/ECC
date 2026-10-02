"""Mr. Shorts on the move: ten short scenarios the owl performs during a Short.

Props slide in, he does his bit, and they slide away again; between scenarios he is back at his spot with
his usual activity, pointing and gags. All positions are in the 1080x1920 frame and stay inside the area the
YouTube app leaves visible (x 70-1010, y 265-1420), on the strip below the main animation and up the right side.
"""
import math
import skia
import art

HOME, S = (872, 1150), 0.5          # resting spot and scale
ACT_LEN, REST = 6.0, 1.2            # seconds per scenario and the pause between two of them
SCENARIOS = ("computer", "sofa", "jetpack", "skateboard", "detective", "chalkboard", "juggle", "trampoline",
             "parachute", "popcorn")
WOOD, DARK = (150, 96, 60), (60, 40, 80)


def ease(x):
    x = max(0.0, min(1.0, x))
    return x * x * (3 - 2 * x)


def lerp(a, b, k):
    return a + (b - a) * k


def presence(u, T, edge=0.8):
    """0 -> 1 over the first `edge` seconds, back to 0 over the last."""
    return min(ease(u / edge), ease((T - u) / edge))


def owl(c, x, y, s=S, rot=0.0, flip=False, **pose):
    c.save()
    c.translate(x, y)
    c.rotate(rot)
    c.scale(-s if flip else s, s)
    art.PROPS["mascot"](c, pose.pop("t", 0.0), 1.0, **pose)
    c.restore()


def plan(narration_end, acts=None, start=2.6):
    """[(start, duration, name)] spread across the narration."""
    acts = list(acts or SCENARIOS)
    n = min(len(acts), int((narration_end - start) / (ACT_LEN + REST)))
    if n <= 0:
        return []
    period = (narration_end - start) / n
    return [(start + i * period + REST / 2, min(ACT_LEN + 1.0, period - REST), acts[i]) for i in range(n)]


def active(show, ft):
    return next(((ft - a, d, name) for a, d, name in show if a <= ft < a + d), None)


# ---------------- the scenarios ----------------
# each takes (canvas, u seconds in, T total, st) where st has: t (clock), talk 0..1, point 0..1 (an event is
# happening in the main animation right now)

def computer(c, u, T, st):
    """A chair and a desk with a computer glide in; he sits and researches something."""
    k = presence(u, T)
    hx, hy = HOME
    x, y = lerp(hx, 800, k), lerp(hy, 1146, k)
    chair_x, desk_x = lerp(1300, x + 22, k), lerp(-320, 610, k)
    art.rrect(c, chair_x - 44, 1050, 88, 150, 26, (70, 110, 200))                 # chair back
    c.drawLine(chair_x, 1200, chair_x, 1248, art.paint(DARK, stroke=12))
    c.drawLine(chair_x - 46, 1250, chair_x + 46, 1250, art.paint(DARK, stroke=12))
    typing = k > 0.9
    owl(c, x, y, legs="sit" if k > 0.6 else "stand", look=-1.0, talk=st["talk"], t=st["t"], mood="curious",
        wings=(62 + 16 * math.sin(st["t"] * 22), -12) if typing else None)
    art.rrect(c, desk_x - 150, 1206, 300, 22, 8, WOOD)                            # desk
    for dx in (-130, 130):
        c.drawLine(desk_x + dx, 1228, desk_x + dx, 1276, art.paint(WOOD, stroke=14))
    art.rrect(c, desk_x - 104, 1062, 190, 128, 14, DARK)                          # monitor
    glow_a = int(150 + 60 * math.sin(st["t"] * 9))
    art.rrect(c, desk_x - 92, 1074, 166, 104, 8, "cyan", glow_a)
    for i in range(4):                                                            # lines scrolling on the screen
        w = 60 + 70 * abs(math.sin(i * 1.7 + int(st["t"] * 3)))
        c.drawLine(desk_x - 80, 1090 + i * 22, desk_x - 80 + w, 1090 + i * 22, art.paint("white", 220, stroke=6))
    c.drawLine(desk_x - 10, 1190, desk_x - 10, 1206, art.paint(DARK, stroke=14))
    art.rrect(c, desk_x + 40, 1192, 96, 14, 6, (220, 220, 230))                   # keyboard


def sofa(c, u, T, st):
    """A sofa glides in; he stretches out on it and waves a wing at the main animation."""
    k = presence(u, T)
    hx, hy = HOME
    sx = lerp(1340, 770, k)
    col = (235, 90, 130)
    art.shaded_rrect(c, sx - 210, 1090, 420, 120, 46, art.shade(col, -0.15))      # back
    art.shaded_rrect(c, sx - 230, 1170, 460, 84, 34, col)                         # seat
    for dx in (-200, 200):
        c.drawLine(sx + dx, 1254, sx + dx, 1274, art.paint(DARK, stroke=16))
    lie = ease((u - 0.5) / 0.7) * ease((T - u - 0.3) / 0.7)
    x, y = lerp(hx, sx + 30, k), lerp(hy, 1132, lie)
    jab = 0.75 + 0.25 * st["point"]
    owl(c, x, y, rot=62 * lie, look=-1.0, talk=st["talk"], t=st["t"], mood="smirk", shadow=lie < 0.3,
        point=lie * jab, point_angle=190, legs="stand")
    art.shaded_rrect(c, sx + 150, 1130, 84, 130, 36, col)                         # near armrest, in front of him


def jetpack(c, u, T, st):
    """He straps on a jetpack, flies up beside the title and points a stick at it, then at the animation."""
    hx, hy = HOME
    up = ease(u / 1.3) * ease((T - u) / 1.3)
    x = lerp(hx, 905, up) + 14 * math.sin(st["t"] * 2.1) * up
    y = lerp(hy, 560, up) + 12 * math.sin(st["t"] * 3.3) * up
    on = ease(u / 0.4) * ease((T - u) / 0.3)
    c.save()
    c.translate(x, y)
    c.scale(S, S)
    for dx in (-96, 96):                                                          # tanks and flames behind him
        art.shaded_rrect(c, dx - 34, -70, 68, 170, 30, "grey", int(255 * on))
        fl = 90 + 50 * abs(math.sin(st["t"] * 30 + dx)) * (0.4 + up)
        art.glow(c, dx, 130 + fl / 2, 60, "orange", int(200 * on))
        c.drawPath(art.path([(dx - 26, 100), (dx + 26, 100), (dx, 100 + fl)]), art.paint("yellow", int(255 * on)))
        c.drawPath(art.path([(dx - 14, 100), (dx + 14, 100), (dx, 100 + fl * 0.6)]), art.paint("white", int(255 * on)))
    c.restore()
    at_title = u < T / 2                                                          # first the title, then the scene
    owl(c, x, y, rot=-6 * up, look=-1.0, talk=st["talk"], t=st["t"], mood="curious", legs="dangle" if up > 0.2 else "stand",
        shadow=up < 0.2, point=up, pointer=True, point_angle=104 if at_title else 58)


def skateboard(c, u, T, st):
    """He rolls along the bottom of the picture and back."""
    hx, hy = HOME
    k = presence(u, T, 0.5)
    out = ease(u / (T * 0.46)) if u < T / 2 else 1 - ease((u - T * 0.54) / (T * 0.46))
    x = lerp(hx, 250, out)
    going_left = u < T / 2
    y = hy - 26 * k
    tilt = (-7 if going_left else 7) * k * (0.5 + 0.5 * math.sin(st["t"] * 3))
    c.save()
    c.translate(x, y + 110)
    c.rotate(tilt * 0.4)
    art.rrect(c, -86, 0, 172, 16, 8, (240, 84, 79), int(255 * k))
    for wx in (-56, 56):
        c.drawCircle(wx, 22, 12, art.paint(art.INK, int(255 * k)))
    c.restore()
    owl(c, x, y, rot=tilt, flip=not going_left, look=-1.0, talk=st["talk"], t=st["t"], mood="smirk",
        wings=(48 + 12 * math.sin(st["t"] * 5), -48 - 12 * math.sin(st["t"] * 5)))


def detective(c, u, T, st):
    """He hops over to the left with a magnifying glass and inspects the main animation."""
    hx, hy = HOME
    go = ease(u / 1.5) * ease((T - u) / 1.5)
    x = lerp(hx, 250, go)
    moving = 0.02 < go < 0.98
    hop = abs(math.sin(u * 7)) if moving else 0.0
    owl(c, x, hy, flip=True, rot=8 * go, look=-1.0, talk=st["talk"], t=st["t"], mood="curious", hop=hop * 0.35,
        activity="magnifier" if go > 0.3 else None)


def chalkboard(c, u, T, st):
    """A chalkboard on an easel glides in; he taps it with a pointer like a teacher."""
    k = presence(u, T)
    hx, hy = HOME
    bx = lerp(-320, 640, k)
    for dx, lean in ((-90, -14), (90, 14)):
        c.drawLine(bx + dx * 0.4, 1090, bx + dx + lean, 1276, art.paint(WOOD, stroke=12))
    art.shaded_rrect(c, bx - 150, 1020, 300, 190, 12, WOOD)
    art.rrect(c, bx - 136, 1032, 272, 166, 6, (30, 70, 60))
    d = ease((u - 0.9) / 2.5)                                                      # the chalk drawing appears
    pa = skia.Path()
    for i in range(int(40 * d) + 1):
        px = bx - 116 + i * 4.6
        py = 1168 - 110 * math.exp(-(((i - 20) / 9.0) ** 2))
        pa.moveTo(px, py) if i == 0 else pa.lineTo(px, py)
    c.drawPath(pa, art.paint("white", 230, stroke=6))
    if d > 0.8:
        art.text(c, "!", bx + 100, 1080, 60, "yellow")
    tap = 0.75 + 0.25 * abs(math.sin(st["t"] * 6))
    owl(c, hx, hy, look=-1.0, talk=st["talk"], t=st["t"], mood="smirk", point=k * tap, pointer=True, point_angle=96)


def juggle(c, u, T, st):
    """He juggles three atoms."""
    k = presence(u, T, 0.5)
    hx, hy = HOME
    owl(c, hx, hy, look=0.3 * math.sin(st["t"] * 4), talk=st["talk"], t=st["t"], mood="happy",
        wings=(lerp(14, 150 + 18 * math.sin(st["t"] * 9), k), lerp(-14, -150 + 18 * math.sin(st["t"] * 9), k)))
    for i, colr in enumerate(("cyan", "pink", "yellow")):
        ph = (st["t"] * 0.9 + i / 3) % 1
        bx = hx + 88 * math.cos(2 * math.pi * ph)
        by = hy - 150 - 110 * abs(math.sin(math.pi * ph)) * 1.0 - 10
        art.glow(c, bx, by, 24, colr, int(160 * k))
        art.ball(c, bx, by, 17, colr, int(255 * k))


def trampoline(c, u, T, st):
    """A trampoline slides under him and he bounces, higher each time."""
    k = presence(u, T)
    hx, hy = HOME
    tx = lerp(1320, hx, k)
    b = abs(math.sin(u * 3.4))
    height = 190 * b * ease((u - 0.8) / 1.5) * ease((T - u - 0.6) / 0.8)
    dip = 10 * (1 - b) * k
    c.drawOval(skia.Rect.MakeXYWH(tx - 120, 1236 + dip, 240, 26), art.paint("cyan", int(255 * k)))
    c.drawOval(skia.Rect.MakeXYWH(tx - 120, 1236 + dip, 240, 26), art.paint(DARK, int(255 * k), stroke=8))
    for dx in (-104, 104):
        c.drawLine(tx + dx, 1250, tx + dx * 1.1, 1280, art.paint(DARK, int(255 * k), stroke=10))
    air = height > 30
    owl(c, hx, hy - 12 * k - height, look=-0.6, talk=st["talk"], t=st["t"], mood="happy", shadow=not air,
        legs="dangle" if air else "stand", wings=(120, -120) if air else None)


def parachute(c, u, T, st):
    """He shoots up out of sight, then drifts back down under a parachute, pointing as he falls."""
    hx, hy = HOME
    if u < 0.6:                                                                    # launch
        y = lerp(hy, 520, ease(u / 0.6))
        x, canopy = hx, 0.0
    else:
        d = (u - 0.6) / (T - 0.6)
        y = lerp(520, hy, ease(d))
        x = hx - 40 + 60 * math.sin(u * 1.6) * (1 - d)
        canopy = ease((u - 0.6) / 0.5) * ease((T - u) / 0.6)
    if canopy > 0:
        c.save()
        c.translate(x, y - 150)
        c.rotate(6 * math.sin(u * 1.6))
        c.scale(canopy, canopy)
        for sx_ in (-90, -30, 30, 90):
            c.drawLine(sx_, 0, sx_ * 0.3, 120, art.paint("white", 200, stroke=3))
        c.drawArc(skia.Rect.MakeXYWH(-110, -70, 220, 140), 180, 180, True, art.paint("orange"))
        for i, colr in enumerate(("yellow", "pink", "cyan")):
            c.drawArc(skia.Rect.MakeXYWH(-110, -70, 220, 140), 180 + i * 60 + 8, 44, True, art.paint(colr, 200))
        c.restore()
    owl(c, x, y, look=-1.0, talk=st["talk"], t=st["t"], mood="curious", legs="dangle" if canopy > 0.2 else "stand",
        shadow=canopy < 0.2 and u > 0.6, point=canopy, point_angle=70)


def popcorn(c, u, T, st):
    """A cinema seat glides in; he settles down with popcorn and watches the main animation."""
    k = presence(u, T)
    hx, hy = HOME
    sx = lerp(1320, hx + 4, k)
    art.shaded_rrect(c, sx - 80, 1040, 160, 190, 40, (190, 40, 60))                # seat back
    owl(c, hx - 6 * k, hy, look=-1.0, talk=st["talk"], t=st["t"], mood="curious", legs="sit" if k > 0.6 else "stand",
        wings=(30 + 26 * abs(math.sin(st["t"] * 3.2)), -14) if k > 0.9 else None)
    art.shaded_rrect(c, sx - 96, 1196, 192, 48, 20, (150, 30, 50))                 # seat cushion
    bx, by = hx - 96, 1150                                                          # the bucket, held in front
    c.drawPath(art.path([(bx - 34, by), (bx + 34, by), (bx + 26, by + 74), (bx - 26, by + 74)]), art.paint("white", int(255 * k)))
    for i in (-1, 1):
        c.drawPath(art.path([(bx + i * 17 - 7, by), (bx + i * 17 + 7, by), (bx + i * 13 + 5, by + 74), (bx + i * 13 - 5, by + 74)]),
                   art.paint("red", int(255 * k)))
    for i in range(5):
        c.drawCircle(bx - 24 + i * 12, by - 6 - (i % 2) * 8, 11, art.paint((255, 244, 200), int(255 * k)))
    if k > 0.9:                                                                    # a kernel arcs up to his beak
        ph = (st["t"] * 1.1) % 1
        c.drawCircle(lerp(bx, hx - 6, ph), lerp(by - 10, hy + 8, ph) - 70 * math.sin(math.pi * ph), 9, art.paint((255, 244, 200)))


RUN = {"computer": computer, "sofa": sofa, "jetpack": jetpack, "skateboard": skateboard, "detective": detective,
       "chalkboard": chalkboard, "juggle": juggle, "trampoline": trampoline, "parachute": parachute, "popcorn": popcorn}
