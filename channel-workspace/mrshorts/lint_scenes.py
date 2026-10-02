#!/usr/bin/env python3
"""Layout linter for script scenes (no rendering needed).

    .venv/bin/python lint_scenes.py "scripts/*.json"

Checks every line's scene, in frame pixels after auto-framing, for:
- HERO: the largest prop must be at least 420 px tall or 600 px wide, so one subject dominates.
- CLIP: props must stay inside the frame safe area (x 40-1040, y 200-1250).
- OVERLAP: two props' boxes may not overlap by more than 25% of the smaller box, unless one sets "layer": true.
- SPARSE: content must cover at least 30% of the visual area.
- COUNT: at most 3 props per shot.
- LONE: a shot needs 2+ props unless its hero fills at least 35% of the visual area.
- PACE: lines longer than 60 characters need 2+ shots cut on spoken words.
- HOLD: no shot may run longer than ~3.3 s (estimated at 2.8 words/s).
- TEXT: flags beats that are text-only (no illustrated prop).
"""
import glob, json, sys
import render_short as rs

TEXT_PROPS = {"label", "big", "bars", "list", "versus", "timeline", "question"}
SAFE = (40, 200, 1040, 1250)


def boxes(props, fit):
    z, dx, dy = fit
    cx, cy = (rs.FIT_BOX[0] + rs.FIT_BOX[2]) / 2, (rs.FIT_BOX[1] + rs.FIT_BOX[3]) / 2
    out = []
    for pr in props:
        ex, ey = rs.extent(pr)
        s = pr.get("s", 1.0)
        x, y = pr.get("x", 0.5) * rs.W, pr.get("y", 0.4) * rs.H
        # map through the auto-frame transform: p' = c + z * (p - c + d)
        X = cx + z * (x - cx + dx)
        Y = cy + z * (y - cy + dy)
        out.append((pr["prop"], X - ex * s * z, Y - ey * s * z, X + ex * s * z, Y + ey * s * z, pr.get("layer")))
    return out


def lint(path):
    spec = json.load(open(path))
    rs.set_style(spec)
    issues = []
    area = (rs.FIT_BOX[2] - rs.FIT_BOX[0]) * (rs.FIT_BOX[3] - rs.FIT_BOX[1])
    for i, ln in enumerate(spec["lines"]):
        shots = rs.line_shots(ln)
        if len(" ".join(ln["text"].split())) > 60 and len(shots) < 2:
            issues.append(f"{path.split("/")[-1]} L{i} PACE long line with one shot; split into 2-3 shots cut on words")
        # HOLD: estimate each shot's on-screen time from its word span (~2.8 words/s)
        words = [(w, 0, 0) for w in ln["text"].split()]
        cuts, idx = [0], 0
        for sh in shots[1:]:
            j = rs.find_word(words, sh.get("on", ""), idx) if sh.get("on") else None
            idx = j if j is not None else idx
            cuts.append(idx)
        cuts.append(len(words))
        for k in range(len(shots)):
            secs = (cuts[k + 1] - cuts[k]) / 2.8
            if secs > 3.3:
                issues.append(f"{path.split('/')[-1]} L{i}S{k} HOLD shot lasts ~{secs:.1f}s; cut on a word in the middle")
        for k, sh in enumerate(shots):
            props = rs.scene_props(sh, "yellow")
            if not props:
                issues.append(f"{path.split('/')[-1]} L{i}S{k} EMPTY shot has no props")
                continue
            fit = rs.fit_scene(props, sh.get("cam"))
            bx = boxes(props, fit)
            tag = f"{path.split('/')[-1]} L{i}S{k}"
            if len(props) > 3:
                issues.append(f"{tag} COUNT {len(props)} props (max 3)")
            if not any(p["prop"] not in TEXT_PROPS for p in props):
                issues.append(f"{tag} TEXT text-only beat, add an illustrated hero prop")
            hero = max(bx, key=lambda b: (b[3] - b[1]) * (b[4] - b[2]))
            if hero[4] - hero[2] < 420 and hero[3] - hero[1] < 600:
                issues.append(f"{tag} HERO largest prop '{hero[0]}' only {hero[3]-hero[1]:.0f}x{hero[4]-hero[2]:.0f}px; scale it up")
            for name, x0, y0, x1, y1, _ in bx:
                if x0 < SAFE[0] or x1 > SAFE[2] or y0 < SAFE[1] or y1 > SAFE[3]:
                    issues.append(f"{tag} CLIP '{name}' box ({x0:.0f},{y0:.0f})-({x1:.0f},{y1:.0f}) leaves safe area {SAFE}")
            for a in range(len(bx)):
                for b in range(a + 1, len(bx)):
                    A, B = bx[a], bx[b]
                    if A[5] or B[5]:
                        continue
                    ix = max(0, min(A[3], B[3]) - max(A[1], B[1]))
                    iy = max(0, min(A[4], B[4]) - max(A[2], B[2]))
                    small = min((A[3] - A[1]) * (A[4] - A[2]), (B[3] - B[1]) * (B[4] - B[2]))
                    if small and ix * iy / small > 0.25:
                        issues.append(f"{tag} OVERLAP '{A[0]}' and '{B[0]}' overlap {100 * ix * iy / small:.0f}%")
            ux0, uy0 = min(b[1] for b in bx), min(b[2] for b in bx)
            ux1, uy1 = max(b[3] for b in bx), max(b[4] for b in bx)
            cover = max(0, min(ux1, rs.FIT_BOX[2]) - max(ux0, rs.FIT_BOX[0])) * max(0, min(uy1, rs.FIT_BOX[3]) - max(uy0, rs.FIT_BOX[1])) / area
            if cover < 0.30:
                issues.append(f"{tag} SPARSE content covers {cover:.0%} of the visual area")
            hero_area = (hero[3] - hero[1]) * (hero[4] - hero[2]) / area
            if len(props) < 2 and hero_area < 0.35:
                issues.append(f"{tag} LONE single small prop ({hero_area:.0%} of area); add a supporting prop or scale up")
    return issues


if __name__ == "__main__":
    total = 0
    for pattern in sys.argv[1:] or ["scripts/*.json"]:
        for p in sorted(glob.glob(pattern)):
            iss = lint(p)
            total += len(iss)
            for x in iss:
                print(x)
    print(f"{total} issue(s)")
    sys.exit(1 if total else 0)
