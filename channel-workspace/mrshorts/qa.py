#!/usr/bin/env python3
"""Automated QA for rendered Shorts: narration accuracy (Whisper transcript vs script), pacing,
loudness, length, file size, and first-frame check.

    .venv/bin/python qa.py scripts/01-sky-not-violet.json [more.json ...] --out out/
"""
import argparse, difflib, glob, json, os, re, subprocess
import numpy as np

TARGETS = {"duration": (20, 75), "wps": (1.6, 3.0), "lufs": (-15.5, -12.5), "size_mb": (0, 8), "max_beat": 7.5}


UNITS = {w: i for i, w in enumerate("zero one two three four five six seven eight nine ten eleven twelve thirteen "
                                    "fourteen fifteen sixteen seventeen eighteen nineteen".split())}
TENS = {w: 10 * i for i, w in enumerate("_ _ twenty thirty forty fifty sixty seventy eighty ninety".split()) if w != "_"}
SCALES = {"hundred": 100, "thousand": 1000, "million": 10 ** 6}
SKIP = {"percent", "km", "kilometers", "kilometres", "dollars", "cents", "and", "a"}


def words_to_digits(tokens):
    """Collapse spelled-out numbers ('thirty eight' -> '38', 'one twenty five' -> '125') so the
    Whisper diff ignores number formatting. Call per punctuation-delimited segment."""
    out, cur, total, active = [], 0, 0, False

    def flush():
        nonlocal cur, total, active
        if active:
            out.append(str(total + cur))
        cur, total, active = 0, 0, False

    prev = None
    for idx, tok in enumerate(tokens):
        nxt = tokens[idx + 1] if idx + 1 < len(tokens) else None
        if tok == "and" and active and prev in SCALES and nxt in UNITS or (tok == "and" and active and prev in SCALES and nxt in TENS):
            prev = tok
            continue  # "one hundred and five"
        if tok == "a" and nxt in SCALES:
            cur, active, prev = 1, True, tok  # "a hundred"
            continue
        prev = tok
        if tok in UNITS:
            if active and (cur % 10 or (UNITS[tok] >= 10 and cur % 100)):
                flush()  # a units digit is already filled: new number
            cur += UNITS[tok]
            active = True
        elif tok in TENS:
            if active and cur % 100:
                if cur < 10 and not total:
                    cur *= 100  # "one twenty five" read as 125
                else:
                    flush()
            cur += TENS[tok]
            active = True
        elif tok in SCALES and active:
            cur = max(cur, 1) * SCALES[tok]
            if SCALES[tok] >= 1000:
                total, cur = total + cur, 0
        else:
            flush()
            out.append(tok)
    flush()
    return out


def norm(s):
    s = s.lower().replace("’", "'").replace("-", " ")
    out = []
    for seg in re.split(r"[.,;:!?]+(?:\s|$)", s):
        toks = words_to_digits(re.findall(r"[a-z0-9']+", seg.replace(",", "")))
        out += [t.strip("'") for t in toks if t.strip("'") and t not in SKIP]
    return out


def probe(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration,size", "-of", "json", path],
                         capture_output=True, text=True, check=True).stdout
    f = json.loads(out)["format"]
    return float(f["duration"]), int(f["size"]) / 1e6


def lufs(path):
    err = subprocess.run(["ffmpeg", "-nostdin", "-hide_banner", "-i", path, "-af", "ebur128", "-f", "null", "-"],
                         capture_output=True, text=True).stderr
    m = re.findall(r"I:\s+(-?[\d.]+) LUFS", err)
    return float(m[-1]) if m else None


def first_frame_std(path):
    raw = subprocess.run(["ffmpeg", "-nostdin", "-loglevel", "error", "-i", path, "-frames:v", "1", "-vf",
                          "scale=108:192,format=gray", "-f", "rawvideo", "-"], capture_output=True, check=True).stdout
    vals = list(raw)
    mean = sum(vals) / len(vals)
    return (sum((v - mean) ** 2 for v in vals) / len(vals)) ** 0.5


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("scripts", nargs="+")
    ap.add_argument("--out", default="out")
    ap.add_argument("--model", default="base.en")
    args = ap.parse_args()
    from faster_whisper import WhisperModel
    model = WhisperModel(args.model, device="cpu", compute_type="int8")
    report = []
    for pattern in args.scripts:
        for sp in sorted(glob.glob(pattern)):
            spec = json.load(open(sp))
            video = os.path.join(args.out, spec["id"] + ".mp4")
            if not os.path.exists(video):
                print(f"MISSING {video}")
                continue
            dur, size = probe(video)
            here = os.path.dirname(os.path.abspath(__file__))
            newest = max(os.path.getmtime(f) for f in [sp] + [os.path.join(here, m) for m in ("render_short.py", "art.py", "audio.py")])
            stale = os.path.getmtime(video) < newest
            pcm = subprocess.run(["ffmpeg", "-nostdin", "-loglevel", "error", "-i", video, "-ac", "1", "-ar", "16000",
                                  "-f", "f32le", "-"], capture_output=True, check=True).stdout
            segs, _ = model.transcribe(np.frombuffer(pcm, np.float32), language="en", beam_size=5, word_timestamps=True)
            segs = list(segs)
            heard = norm(" ".join(s.text for s in segs))
            # caption sync: caption word start minus the time Whisper hears that word (negative = caption early)
            sync_med = sync_early = None
            timing = os.path.join(args.out, "timing", spec["id"] + ".json")
            if os.path.exists(timing):
                key = lambda w: re.sub(r"[^a-z0-9]", "", w.lower())
                cap = [(key(w), a) for w, a, _ in json.load(open(timing))]
                hw = [(key(w.word), w.start) for sg in segs for w in (sg.words or [])]
                m2 = difflib.SequenceMatcher(a=[x[0] for x in cap], b=[x[0] for x in hw], autojunk=False)
                offs = [cap[b.a + k][1] - hw[b.b + k][1] for b in m2.get_matching_blocks() for k in range(b.size)]
                if len(offs) > 10:
                    sync_med, sync_early = float(np.median(offs)), float(np.percentile(offs, 5))
            teaser = spec.get("teaser") or {}
            outro = f"{teaser['question']} {teaser.get('cta', 'Think it over. The answer is in the next Short.')}" if teaser else ""
            said = norm(" ".join([ln["text"] for ln in spec["lines"]] + [outro]))
            sm = difflib.SequenceMatcher(a=said, b=heard, autojunk=False)
            diffs = [f"{' '.join(said[i1:i2])!r} -> {' '.join(heard[j1:j2])!r}"
                     for op, i1, i2, j1, j2 in sm.get_opcodes() if op != "equal"]
            wps = (sum(len(ln["text"].split()) for ln in spec["lines"]) + len(outro.split())) / dur
            loud = lufs(video)
            ff = first_frame_std(video)
            flags = []
            lo, hi = TARGETS["duration"]
            if not lo <= dur <= hi:
                flags.append(f"duration {dur:.1f}s outside {lo}-{hi}")
            lo, hi = TARGETS["wps"]
            if not lo <= wps <= hi:
                flags.append(f"pace {wps:.2f} w/s outside {lo}-{hi}")
            lo, hi = TARGETS["lufs"]
            if loud is None or not lo <= loud <= hi:
                flags.append(f"loudness {loud} LUFS")
            if size > TARGETS["size_mb"][1]:
                flags.append(f"size {size:.1f} MB")
            if ff < 12:
                flags.append("first frame looks empty")
            if stale:
                flags.append("STALE: video is older than its script or the renderer; re-render")
            if sync_med is not None and (abs(sync_med) > 0.12 or sync_early < -0.3):
                flags.append(f"caption sync: median {sync_med * 1000:+.0f} ms, earliest 5% {sync_early * 1000:+.0f} ms")
            if sm.ratio() < 0.95:
                flags.append(f"narration match {sm.ratio():.2f}")
            row = {"id": spec["id"], "duration": round(dur, 1), "size_mb": round(size, 2), "lufs": loud,
                   "wps": round(wps, 2), "narration_match": round(sm.ratio(), 3),
                   "caption_sync_ms": None if sync_med is None else round(sync_med * 1000), "first_frame_std": round(ff, 1),
                   "diffs": diffs, "flags": flags}
            report.append(row)
            sync_txt = "" if sync_med is None else f"sync={sync_med * 1000:+.0f}ms "
            print(f"{spec['id']:<34} {dur:5.1f}s {size:4.1f}MB {loud}LUFS {wps:.2f}w/s match={sm.ratio():.3f} {sync_txt}"
                  f"{'OK' if not flags else 'FLAGS: ' + '; '.join(flags)}")
            for d in diffs:
                print("    heard:", d)
    json.dump(report, open(os.path.join(args.out, "qa_report.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
