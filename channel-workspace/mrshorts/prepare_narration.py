#!/usr/bin/env python3
"""Turn a raw narration recording into a clean take for render_short.py --voice-file.

    .venv/bin/python prepare_narration.py "~/Downloads/New Recording 30.m4a" scripts/11-lsd-long-trip.json out/narration/

For every script line it finds the LAST take in the recording (so "take two" retakes win), drops anything
that is not in the script (slates, stage directions, the mascot's line), shortens long pauses, and writes
<id>.wav plus a report of which seconds were used and which words differ from the script.
Options: --tempo 1.08 speeds the voice up slightly without changing pitch.
"""
import argparse, difflib, json, os, re, subprocess
import numpy as np

SR = 48000


def norm(w):
    return re.sub(r"[^a-z0-9]", "", w.lower())


def decode(path, sr):
    pcm = subprocess.run(["ffmpeg", "-nostdin", "-loglevel", "error", "-i", os.path.expanduser(path), "-ac", "1",
                          "-ar", str(sr), "-f", "f32le", "-"], capture_output=True, check=True).stdout
    return np.frombuffer(pcm, np.float32).astype(np.float64)


def find_takes(line_words, heard, min_ratio=0.72):
    """All windows of the transcript that read this line: (start_idx, end_idx, ratio), in time order."""
    n, target, takes = len(line_words), [norm(w) for w in line_words], []
    i = 0
    while i < len(heard):
        best = None
        for span in range(max(2, int(n * 0.6)), int(n * 1.5) + 2):
            win = [norm(h[0]) for h in heard[i:i + span]]
            if len(win) < 2:
                break
            r = difflib.SequenceMatcher(a=target, b=win, autojunk=False).ratio()
            if best is None or r > best[2]:
                best = (i, i + len(win), r)
        if best and best[2] >= min_ratio and norm(heard[i][0]) in target[:3]:
            # tighten the window to the first and last words that really belong to the line
            blocks = [b for b in difflib.SequenceMatcher(a=target, b=[norm(h[0]) for h in heard[best[0]:best[1]]],
                                                         autojunk=False).get_matching_blocks() if b.size]
            end = best[0] + blocks[-1].b + blocks[-1].size
            ext = 0  # keep going to the end of the spoken sentence (e.g. "5-HT2A." heard as one token)
            while end < len(heard) and ext < 4 and heard[end - 1][0][-1:] not in ".?!" \
                    and heard[end][1] - heard[end - 1][2] < 0.8:
                end, ext = end + 1, ext + 1
            takes.append((best[0] + blocks[0].b, end, best[2]))
            i = takes[-1][1]
        else:
            i += 1
    return takes


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("recording")
    ap.add_argument("script")
    ap.add_argument("out_dir")
    ap.add_argument("--tempo", type=float, default=1.0, help="speed-up factor without pitch change, e.g. 1.08")
    ap.add_argument("--max-pause", type=float, default=0.45, help="longest pause kept inside a line (s)")
    ap.add_argument("--line-gap", type=float, default=0.3, help="pause placed between lines (s)")
    ap.add_argument("--model", default="small.en")
    args = ap.parse_args()
    from faster_whisper import WhisperModel
    spec = json.load(open(args.script))
    rec = decode(args.recording, SR)
    segs, _ = WhisperModel(args.model, device="cpu", compute_type="int8").transcribe(
        decode(args.recording, 16000).astype(np.float32), language="en", word_timestamps=True)
    heard = [(w.word.strip(), w.start, w.end) for sg in segs for w in (sg.words or [])]
    model = WhisperModel(args.model, device="cpu", compute_type="int8")
    lo = decode(args.recording, 16000).astype(np.float32)

    def retime(words, t0, t1):
        """Second pass: transcribe just this take. Word times from a long recording drift around slates
        and retakes; a short isolated window gives reliable ones."""
        w0 = max(0.0, t0 - 1.2)
        sg, _ = model.transcribe(lo[int(w0 * 16000):int((t1 + 0.8) * 16000)], language="en", word_timestamps=True,
                                 condition_on_previous_text=False)
        local = [(w.word.strip(), w0 + w.start, w0 + w.end) for x in sg for w in (x.words or [])]
        takes = find_takes(words, local, min_ratio=0.6)
        return (local, takes[-1]) if takes else (None, None)

    # speech/silence envelope, used to snap cut points to real onsets
    hop = int(0.02 * SR)
    rms = np.array([np.sqrt(np.mean(rec[i:i + hop] ** 2)) for i in range(0, len(rec) - hop, hop)])
    quiet = rms < max(np.percentile(rms, 10) * 3.0, np.percentile(rms, 95) * 0.06)

    def snap_start(src, a, b):
        """Where the take really begins. A slate ("take four") or a false start can sit under the first
        words Whisper reports, so look for the last half-second silence before the third word that still
        leaves room for the opening words after it, and start there."""
        t_first, t_third = src[a][1], src[min(a + 2, b - 1)][1]
        best, run_ = None, 0
        for i in range(int(t_first / 0.02), min(int(t_third / 0.02), len(quiet))):
            run_ = run_ + 1 if quiet[i] else 0
            if run_ >= 25:
                best = i
        if best is None:
            return t_first
        while best < len(quiet) and quiet[best]:
            best += 1
        return best * 0.02 if t_third - best * 0.02 >= 0.5 else t_first

    os.makedirs(args.out_dir, exist_ok=True)
    pieces, report, cursor = [], [], 0
    for i, ln in enumerate(spec["lines"]):
        words = ln["text"].split()
        takes = [t for t in find_takes(words, heard) if t[0] >= cursor] or find_takes(words, heard)
        if not takes:
            raise SystemExit(f"line {i + 1} not found in the recording: {ln['text'][:60]}...")
        # the last take before the next line begins wins; takes of one line sit next to each other
        a, b, ratio = takes[-1] if len(takes) == 1 else max(
            (t for t in takes if t[0] - takes[0][1] < 40), key=lambda t: t[0])
        cursor = b
        local, take = retime(words, heard[a][1], heard[b - 1][2])
        src = heard
        if local:
            src, (a, b, ratio) = local, take
        said = " ".join(h[0] for h in src[a:b])
        diff = [f"{' '.join(words[i1:i2])!r} -> {' '.join(x[0] for x in src[a:b][j1:j2])!r}"
                for op, i1, i2, j1, j2 in difflib.SequenceMatcher(
                    a=[norm(w) for w in words], b=[norm(h[0]) for h in src[a:b]], autojunk=False).get_opcodes()
                if op != "equal"]
        # cut the take into runs of speech, closing any pause longer than --max-pause
        runs, start = [], snap_start(src, a, b)
        for k in range(a, b - 1):
            if src[k][2] <= start:  # words Whisper pinned to the slate/false start: already skipped
                continue
            if src[k + 1][1] - src[k][2] > args.max_pause + 0.25:
                runs.append((start, src[k][2]))
                start = src[k + 1][1]
        runs.append((start, src[b - 1][2]))
        for r, (s0, s1) in enumerate(runs):
            seg = rec[int(max(0, s0 - 0.08) * SR):int((s1 + 0.14) * SR)].copy()
            f = int(0.02 * SR)
            seg[:f] *= np.linspace(0, 1, f)
            seg[-f:] *= np.linspace(1, 0, f)
            pieces += [seg, np.zeros(int((args.max_pause if r < len(runs) - 1 else args.line_gap) * SR))]
        report.append({"line": i + 1, "takes_found": len(takes), "used_seconds": [round(runs[0][0], 1), round(src[b - 1][2], 1)],
                       "match": round(ratio, 2), "heard": said, "differences": diff})
    teaser = spec.get("teaser")
    if teaser:  # the owl's closing question, if it was read too
        t_words = f"{teaser['question']} {teaser.get('cta', 'Think it over. The answer is in the next Short.')}".split()
        t_takes = [tk for tk in find_takes(t_words, heard, min_ratio=0.6) if tk[0] >= cursor]
        if t_takes:
            a, b, ratio = t_takes[-1]
            seg = rec[int(max(0, heard[a][1] - 0.1) * SR):int((heard[b - 1][2] + 0.2) * SR)]
            tp = os.path.join(args.out_dir, spec["id"] + ".teaser.f32")
            seg.astype(np.float32).tofile(tp)
            subprocess.run(["ffmpeg", "-nostdin", "-y", "-loglevel", "error", "-f", "f32le", "-ar", str(SR), "-ac", "1",
                            "-i", tp, "-af", "highpass=f=70,afftdn=nr=8,loudnorm=I=-18:TP=-2",
                            os.path.join(args.out_dir, spec["id"] + ".teaser.wav")], check=True)
            os.remove(tp)
            print(f"  owl's closing line: {heard[a][1]:.1f}-{heard[b - 1][2]:.1f}s, match {ratio:.2f}: "
                  + " ".join(h[0] for h in heard[a:b]))
    clean = np.concatenate(pieces)
    raw = os.path.join(args.out_dir, spec["id"] + ".raw.f32")
    clean.astype(np.float32).tofile(raw)
    out = os.path.join(args.out_dir, spec["id"] + ".wav")
    af = "highpass=f=70,afftdn=nr=8,loudnorm=I=-18:TP=-2" + (f",atempo={args.tempo}" if abs(args.tempo - 1) > 1e-3 else "")
    subprocess.run(["ffmpeg", "-nostdin", "-y", "-loglevel", "error", "-f", "f32le", "-ar", str(SR), "-ac", "1", "-i", raw,
                    "-af", af, out], check=True)
    os.remove(raw)
    json.dump(report, open(os.path.join(args.out_dir, spec["id"] + ".report.json"), "w"), indent=1)
    dur = len(clean) / SR / args.tempo
    print(f"{out}  {dur:.1f}s from a {len(rec) / SR:.0f}s recording")
    for r in report:
        flag = "" if not r["differences"] else "  DIFFERS: " + "; ".join(r["differences"])
        print(f"  line {r['line']:>2}: take {r['takes_found']} of {r['takes_found']}, {r['used_seconds'][0]}-{r['used_seconds'][1]}s, "
              f"match {r['match']}{flag}")


if __name__ == "__main__":
    main()
