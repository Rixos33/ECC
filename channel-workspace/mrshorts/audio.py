"""Procedural ambient music bed + sound effects (numpy), and the final mix.

Everything is synthesised locally, so there are no music-licensing or Content ID issues.
A real track can be used instead with `render_short.py --music-file track.mp3`.
"""
import numpy as np

SR = 48000
# chord progressions: (bass note, upper voicing) as MIDI notes, one bar each
MOODS = {
    "wonder": {"bpm": 84, "prog": [(41, [60, 64, 67, 69]), (48, [59, 64, 67, 72]),      # Fmaj9  Cmaj7
                                   (45, [60, 64, 67, 71]), (43, [59, 62, 66, 69])]},     # Am9    Gmaj7
    "curious": {"bpm": 92, "prog": [(50, [60, 65, 69, 72]), (46, [62, 65, 69, 74]),     # Dm7    Bbmaj7
                                    (48, [62, 64, 67, 71]), (45, [60, 64, 67, 72])]},    # Cmaj9  Am7
    "tense": {"bpm": 88, "prog": [(45, [60, 64, 67, 72]), (41, [60, 64, 69, 72]),       # Am7    Fmaj7
                                  (38, [60, 65, 69, 72]), (40, [59, 62, 67, 71])]},      # Dm7    Em7
    "playful": {"bpm": 104, "prog": [(48, [64, 67, 71, 74]), (45, [64, 67, 72, 76]),    # Cmaj9  Am7
                                     (41, [64, 69, 72, 76]), (43, [62, 67, 71, 74])]},   # Fmaj7  G6
}
# "mystic" kit: slow, modal, airy. Minor with a raised-fourth colour and a harmonic-minor pull at the end.
MOODS["mystic"] = {"bpm": 63, "kit": "mystic", "prog": [
    (45, [60, 64, 69, 71]),   # Am(add9)
    (41, [60, 64, 69, 71]),   # Fmaj7(#11): same upper notes, the floor drops away
    (38, [60, 65, 69, 76]),   # Dm9
    (40, [59, 64, 68, 74])]}  # E7sus -> G# leading tone
MOODS["eerie"] = {"bpm": 58, "kit": "mystic", "prog": [
    (40, [59, 64, 67, 71]),   # Em
    (41, [60, 65, 69, 72]),   # F (flat-second colour)
    (45, [60, 64, 69, 72]),   # Am
    (47, [59, 63, 66, 71])]}  # B major: unresolved
BELL_MOTIF = [0, None, 2, None, 3, None, 1, None, None, 2, None, None, 3, None, None, None]  # sixteenth-note grid

ARP = [0, 2, 1, 3, 2, 1, 3, 2]          # repeating motif over the chord tones (eighth notes)
ARP_VEL = [1.0, 0.55, 0.75, 0.6, 0.9, 0.5, 0.7, 0.0]  # 0 = rest; accents give the motif a shape


def hz(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def env(n, a, r):
    e = np.ones(n)
    na, nr = min(n, int(a * SR)), min(n, int(r * SR))
    if na:
        e[:na] = np.sin(np.linspace(0, np.pi / 2, na)) ** 2
    if nr:
        e[-nr:] *= np.cos(np.linspace(0, np.pi / 2, nr)) ** 2
    return e


def _moving_avg(x, n):
    """Centred moving average via cumulative sums (O(len(x)), same length as x)."""
    n = max(1, int(n))
    c = np.cumsum(np.concatenate([np.zeros(n // 2 + 1), x, np.zeros(n - n // 2)]))
    return (c[n:n + len(x)] - c[:len(x)]) / n


def lowpass(x, cutoff):
    """Cheap smooth low-pass: three cascaded moving averages (close to a Gaussian)."""
    w = max(1, int(SR / cutoff * 0.45))
    for _ in range(3):
        x = _moving_avg(x, w)
    return x


def _ir(seconds, seed, tone=2600):
    """Hall-like impulse response: short bright early part plus a long tail (dark by default), after a pre-delay."""
    rng = np.random.default_rng(seed)
    n = int(seconds * SR)
    t = np.arange(n) / SR
    early = rng.standard_normal(n) * np.exp(-t * 9)
    tail = lowpass(rng.standard_normal(n), tone) * np.exp(-t * 2.2) * 2.2
    ir = np.concatenate([np.zeros(int(0.018 * SR)), early * 0.5 + tail])
    return ir / np.sqrt(np.sum(ir ** 2))


def reverb(x, seconds=3.2, mix=0.35, seed=1, tone=2600):
    ir = _ir(seconds, seed, tone)
    size = 1 << int(np.ceil(np.log2(len(x) + len(ir))))
    wet = np.fft.irfft(np.fft.rfft(x, size) * np.fft.rfft(ir, size), size)[:len(x)]
    return (1 - mix) * x + mix * wet * 0.7


def pad_note(freq, n, seed):
    """Warm string-like pad: band-limited saw harmonics, three detuned voices, slow shimmer."""
    rng = np.random.default_rng(seed)
    t = np.arange(n) / SR
    out = np.zeros(n)
    for det in (-0.0035, 0.0, 0.0041):
        ph = rng.uniform(0, 6.28)
        f = freq * (1 + det)
        for h in range(1, 7):
            if f * h > 5000:
                break
            out += np.sin(2 * np.pi * f * h * t + ph * h) * (1 / h) * np.exp(-h * 0.3)
    shimmer = 1 + 0.12 * np.sin(2 * np.pi * rng.uniform(0.12, 0.3) * t + rng.uniform(0, 6.28))
    return out * shimmer / 3


def keys_note(freq, vel=1.0, length=1.6):
    """Soft felt-piano / electric-piano tone: a few partials that decay at different rates, soft attack."""
    n = int(length * SR)
    t = np.arange(n) / SR
    y = np.zeros(n)
    for h, amp, dec in ((1, 1.0, 2.6), (2, 0.5, 3.6), (3, 0.26, 5.5), (4.02, 0.13, 8.0), (5.03, 0.06, 11.0)):
        y += amp * np.sin(2 * np.pi * freq * h * t) * np.exp(-t * dec)
    tine = 0.10 * vel * np.sin(2 * np.pi * freq * 7.0 * t) * np.exp(-t * 28)  # tiny bell-like onset
    attack = np.minimum(1.0, t / 0.012)
    return (y + tine) * attack * vel


def thump(length=0.22):
    """Very soft, round kick-like pulse."""
    t = np.arange(int(length * SR)) / SR
    f = 46 + 44 * np.exp(-t * 30)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 16) * np.minimum(1, t / 0.004)


def shaker(seed, length=0.07):
    rng = np.random.default_rng(seed)
    n = int(length * SR)
    x = rng.standard_normal(n)
    x = x - lowpass(x, 5000)  # keep only the airy top
    return x * np.exp(-np.arange(n) / SR * 60)


def choir_note(freq, n, seed):
    """Soft wordless 'ooh': harmonics shaped by two vowel formants, with slow vibrato."""
    rng = np.random.default_rng(seed)
    t = np.arange(n) / SR
    vib = 1 + 0.004 * np.sin(2 * np.pi * rng.uniform(4.6, 5.4) * t + rng.uniform(0, 6.28))
    phase = 2 * np.pi * np.cumsum(freq * vib) / SR
    out = np.zeros(n)
    for h in range(1, 14):
        fh = freq * h
        if fh > 5200:
            break
        amp = (np.exp(-((fh - 420) / 260) ** 2) + 0.55 * np.exp(-((fh - 900) / 320) ** 2)
               + 0.12 * np.exp(-((fh - 2900) / 600) ** 2)) / h ** 0.35
        out += amp * np.sin(h * phase + rng.uniform(0, 6.28))
    return out


def swell(length=1.6, seed=0):
    """Airy reversed swell that rises into a chord change."""
    rng = np.random.default_rng(seed)
    n = int(length * SR)
    x = rng.standard_normal(n)
    x = lowpass(x, 6000) - lowpass(x, 900)
    return x * (np.arange(n) / n) ** 3


def music_mystic(duration, cfg, seed=0):
    """Mysterious bed: deep drone, glassy pad + choir, sparse bells with long echoes, chime sparkles, swells."""
    rng = np.random.default_rng(seed)
    beat = 60 / cfg["bpm"]
    bar = 4 * beat
    n = int((duration + 6.0) * SR)
    pad, bells, drone, air = np.zeros((2, n)), np.zeros((2, n)), np.zeros(n), np.zeros((2, n))
    k = 0
    while k * bar < duration + 1.0:
        bass, tones = cfg["prog"][k % len(cfg["prog"])]
        t0 = k * bar
        pn = int((bar + 3.0) * SR)
        tp = np.arange(pn) / SR
        # drone: root and fifth, slow beating between two slightly detuned voices
        for m, g in ((bass, 1.0), (bass + 7, 0.45), (bass + 12, 0.3)):
            f = hz(m)
            dr = (np.sin(2 * np.pi * f * tp) + np.sin(2 * np.pi * f * 1.004 * tp)) * 0.5
            dr += 0.2 * np.sin(4 * np.pi * f * tp)
            place(drone, dr * env(pn, 1.6, 2.4), t0 - 0.8, 0.16 * g)
        # glass pad + choir, each voice swelling in slowly
        for i, m in enumerate(tones):
            pan = 0.2 + 0.6 * i / (len(tones) - 1)
            place(pad, pad_note(hz(m), pn, seed * 31 + k * 7 + i) * env(pn, 2.0, 2.6), t0 - 1.0, 0.045, pan)
            place(pad, choir_note(hz(m - 12 if i < 2 else m), pn, seed * 17 + k * 5 + i) * env(pn, 2.2, 2.6),
                  t0 - 1.0, 0.05, 1 - pan)
            place(pad, pad_note(hz(m + 12), pn, seed * 13 + k * 3 + i) * env(pn, 2.6, 2.8), t0 - 1.0, 0.03, pan)
            sh = np.sin(2 * np.pi * hz(m + 24) * tp) * (1 + 0.5 * np.sin(2 * np.pi * 0.3 * tp + i))  # glassy shimmer
            place(pad, sh * env(pn, 3.0, 3.0), t0 - 1.0, 0.012, 1 - pan)
        # bell motif: sparse, same shape each bar, last bar of the cycle answers an octave up
        step = bar / len(BELL_MOTIF)
        for i, idx in enumerate(BELL_MOTIF):
            if idx is None:
                continue
            m = tones[idx] + 12 + (12 if (k % 4 == 3 and i >= 9) else 0)
            place(bells, bell(hz(m), 2.6), t0 + i * step + rng.normal(0, 0.008), 0.2 * rng.uniform(0.75, 1.0),
                  pan=0.3 + 0.4 * (i % 3) / 2)
        # chime sparkles: one or two very high bells at loose times
        for _ in range(int(rng.integers(1, 3))):
            m = tones[int(rng.integers(len(tones)))] + 24 + (7 if rng.random() < 0.3 else 0)
            place(bells, bell(hz(m), 1.8), t0 + rng.uniform(0, bar), 0.1 * rng.uniform(0.6, 1.0), pan=rng.uniform(0.15, 0.85))
        # airy swell rising into the next chord
        sw = swell(1.6, seed + k)
        place(air, np.stack([sw, np.roll(sw, 211)]), t0 + bar - 1.6, 0.11)
        # distant heartbeat on the downbeat
        place(air, thump(0.3), t0, 0.07)
        k += 1
    # long dotted echo on the bells, then a big hall
    d = int(0.75 * beat * SR)
    echo = np.zeros_like(bells)
    echo[0, d:] += bells[1, :-d] * 0.42
    echo[1, 2 * d:] += bells[0, :-2 * d] * 0.3
    echo[0, 3 * d:] += bells[1, :-3 * d] * 0.18
    bells = bells + echo
    # a breath of high "air" that slowly comes and goes
    tn = np.arange(n) / SR
    for ch in (0, 1):
        hiss = rng.standard_normal(n)
        hiss = lowpass(hiss, 9000) - lowpass(hiss, 3500)
        air[ch] += hiss * 0.02 * (0.55 + 0.45 * np.sin(2 * np.pi * tn / (bar * 2) + ch * 1.3))
    wet = pad + bells + air
    wet = np.stack([reverb(wet[0], 4.6, 0.5, seed + 11, tone=8000), reverb(wet[1], 4.6, 0.5, seed + 12, tone=8000)])
    out = wet + drone[None, :] * 0.8
    out = np.tanh(out * 1.5) / 1.5
    out = out[:, :int(duration * SR)]
    fade = int(0.8 * SR)
    out[:, -fade:] *= np.linspace(1, 0.35, fade)
    return out


def chord_at(time, mood):
    cfg = MOODS.get(mood, MOODS["wonder"])
    bar = 4 * 60 / cfg["bpm"]
    return cfg["prog"][int(max(0.0, time) // bar) % len(cfg["prog"])]


def place(buf, clip, at, gain=1.0, pan=0.5):
    """Add a mono or stereo clip into a stereo (or mono) buffer at time `at` (s)."""
    s = int(at * SR)
    n = buf.shape[-1]
    if s >= n or s + clip.shape[-1] <= 0:
        return
    c0 = max(0, -s)
    s = max(0, s)
    e = min(n, s + clip.shape[-1] - c0)
    seg = clip[..., c0:c0 + e - s] * gain
    if buf.ndim == 1:
        buf[s:e] += seg if seg.ndim == 1 else seg.mean(axis=0)
    elif seg.ndim == 1:
        buf[0, s:e] += seg * np.cos(pan * np.pi / 2) * 1.414
        buf[1, s:e] += seg * np.sin(pan * np.pi / 2) * 1.414
    else:
        buf[:, s:e] += seg


def music(duration, mood="wonder", seed=0):
    """Ambient bed: pad + bass + a repeating keys motif with a ping-pong echo + a soft pulse."""
    rng = np.random.default_rng(seed)
    cfg = MOODS.get(mood, MOODS["wonder"])
    if cfg.get("kit") == "mystic":
        return music_mystic(duration, cfg, seed)
    beat = 60 / cfg["bpm"]
    bar = 4 * beat
    n = int((duration + 4.0) * SR)
    pad, keys, low, perc = np.zeros((2, n)), np.zeros((2, n)), np.zeros(n), np.zeros((2, n))
    k = 0
    while k * bar < duration + 1.0:
        bass, tones = cfg["prog"][k % len(cfg["prog"])]
        t0 = k * bar
        # pad: long overlapping notes so chords melt into each other
        pn = int((bar + 2.2) * SR)
        for i, m in enumerate(tones):
            note = pad_note(hz(m - 12 if i < 2 else m), pn, seed * 31 + k * 7 + i) * env(pn, 1.3, 2.0)
            place(pad, note, t0 - 0.6, 0.06 if i < 2 else 0.075, pan=0.25 + 0.5 * i / (len(tones) - 1))
        # bass: root on beat 1, a soft pickup before the next bar
        for at, length, g in ((0.0, 2.6 * beat, 1.0), (3.5 * beat, 0.6 * beat, 0.6)):
            bn = int(length * SR)
            tb = np.arange(bn) / SR
            b = (np.sin(2 * np.pi * hz(bass) * tb) + 0.3 * np.sin(4 * np.pi * hz(bass) * tb)) * env(bn, 0.03, 0.35)
            place(low, b, t0 + at, 0.12 * g)
        # keys motif: same shape every bar, so it reads as a melody instead of random notes
        for i, (idx, vel) in enumerate(zip(ARP, ARP_VEL)):
            if not vel or (k % 4 == 3 and i > 5):
                continue
            m = tones[idx] + (12 if (i == 4 and k % 2) else 0)
            at = t0 + i * beat / 2 + rng.normal(0, 0.006)
            note = keys_note(hz(m), vel * rng.uniform(0.85, 1.0))
            place(keys, note, at, 0.19, pan=0.35 + 0.3 * (i % 2))
        # pulse: round thump on 1 and 3, airy shaker on the off-beats (kept very quiet)
        for b_i in (0, 2):
            place(perc, thump(), t0 + b_i * beat, 0.11)
        for e_i in range(8):
            if e_i % 2:
                place(perc, shaker(seed + k * 8 + e_i), t0 + e_i * beat / 2 + rng.normal(0, 0.004),
                      0.16 * (1.0 if e_i % 4 == 3 else 0.6), pan=0.3 + 0.4 * ((e_i // 2) % 2))
        k += 1
    # dotted-eighth ping-pong echo on the keys
    d = int(0.75 * beat * SR)
    echo = np.zeros_like(keys)
    echo[0, d:] += keys[1, :-d] * 0.34
    echo[1, 2 * d:] += keys[0, :-2 * d] * 0.20
    keys = keys + echo
    wet = pad * 1.0 + keys * 1.0
    wet = np.stack([reverb(wet[0], 3.4, 0.42, seed + 11), reverb(wet[1], 3.4, 0.42, seed + 12)])
    out = wet + low[None, :] + np.stack([reverb(perc[0], 1.2, 0.18, seed + 13), reverb(perc[1], 1.2, 0.18, seed + 14)])
    out = np.stack([lowpass(out[0], 9000), lowpass(out[1], 9000)])  # take the digital edge off
    out = np.tanh(out * 1.6) / 1.6                                  # gentle glue
    out = out[:, :int(duration * SR)]
    fade = int(0.5 * SR)
    out[:, -fade:] *= np.linspace(1, 0.35, fade)  # soft tail; the loop restarts on the hook
    return out


def whoosh(length=0.38, seed=0):
    """Soft airy transition: band-passed noise that brightens then darkens, sweeping left to right."""
    rng = np.random.default_rng(seed)
    n = int(length * SR)
    x = rng.standard_normal(n)
    shape = np.sin(np.linspace(0, np.pi, n))
    lo, hi = np.zeros(n), np.zeros(n)
    a_hi = 0.05 + 0.30 * shape ** 2      # upper edge of the band opens up mid-sweep
    a_lo = 0.012 + 0.03 * shape ** 2     # lower edge: removes rumble so it never sounds like hiss on a boom
    acc1 = acc2 = 0.0
    for i in range(n):
        acc1 += a_hi[i] * (x[i] - acc1)
        acc2 += a_lo[i] * (acc1 - acc2)
        hi[i], lo[i] = acc1, acc2
    y = (hi - lo) * shape ** 2.2
    y = y / (np.max(np.abs(y)) + 1e-9)
    pan = np.linspace(0.2, 0.8, n) if seed % 2 == 0 else np.linspace(0.8, 0.2, n)
    st = np.stack([y * np.cos(pan * np.pi / 2), y * np.sin(pan * np.pi / 2)])
    return np.stack([reverb(st[0], 0.9, 0.25, seed + 3), reverb(st[1], 0.9, 0.25, seed + 4)]) * 0.5


def bell(freq, length=1.6):
    """Glockenspiel-like tone: slightly inharmonic partials with fast-decaying upper ones."""
    t = np.arange(int(length * SR)) / SR
    y = sum(a * np.sin(2 * np.pi * freq * r * t) * np.exp(-t * d)
            for r, a, d in ((1.0, 1.0, 3.2), (2.76, 0.42, 5.0), (5.4, 0.2, 9.0), (8.93, 0.08, 15.0)))
    return y * np.minimum(1.0, t / 0.003)


def chime(tones=(72, 76, 79, 84), length=2.2):
    """Reveal sparkle: a quick upward bell arpeggio in the current chord, with a hall tail."""
    n = int(length * SR)
    buf = np.zeros((2, n))
    for i, m in enumerate(tones):
        place(buf, bell(hz(m)), i * 0.075, 0.5 * (0.75 + 0.25 * (i == len(tones) - 1)), pan=0.3 + 0.4 * i / max(1, len(tones) - 1))
    return np.stack([reverb(buf[0], 2.4, 0.45, 21), reverb(buf[1], 2.4, 0.45, 22)]) * 0.45


def riser(length=1.2, seed=0):
    """Soft swell into the reveal: airy noise that opens up, like a reversed cymbal (no siren tone)."""
    rng = np.random.default_rng(seed)
    n = int(length * SR)
    t = np.arange(n) / SR / length
    x = rng.standard_normal(n)
    y = np.zeros(n)
    a = 0.02 + 0.35 * t ** 3
    acc = 0.0
    for i in range(n):
        acc += a[i] * (x[i] - acc)
        y[i] = acc
    y = (y - lowpass(y, 500)) * t ** 2.5
    y = y / (np.max(np.abs(y)) + 1e-9)
    y[-int(0.02 * SR):] *= np.linspace(1, 0, int(0.02 * SR))
    return np.stack([y, np.roll(y, 37)]) * 0.32


def pop(freq=660.0, length=0.22):
    """Soft mallet 'tick' for elements appearing (pitched to the music, never a sharp click)."""
    t = np.arange(int(length * SR)) / SR
    y = (np.sin(2 * np.pi * freq * t) + 0.25 * np.sin(2 * np.pi * freq * 3 * t) * np.exp(-t * 40)) * np.exp(-t * 26)
    return y * np.minimum(1.0, t / 0.004) * 0.5


SFX_GAIN = {"whoosh": 0.42, "pop": 0.30, "chime": 0.80, "riser": 0.55}


def mixdown(voice, duration, cues, mood="wonder", seed=0, music_db=-19.0, sfx_db=-6.0, bed=None):
    """voice: mono float array at SR. cues: list of (time, kind). bed: optional stereo music array.
    Returns a stereo float array."""
    n = int(duration * SR)
    v = np.zeros(n)
    v[:min(n, len(voice))] = voice[:n]
    if bed is None:
        bed = music(duration, mood, seed=seed)
    else:
        reps = int(np.ceil(n / bed.shape[-1]))
        bed = np.tile(bed, reps)[:, :n].copy()
        fade = int(0.5 * SR)
        bed[:, -fade:] *= np.linspace(1, 0.35, fade)
    # duck the bed under the narration (smoothed voice envelope)
    envv = np.sqrt(np.maximum(_moving_avg(v ** 2, int(0.05 * SR)), 0))
    envv = _moving_avg(envv, int(0.3 * SR))
    envv /= (envv.max() + 1e-9)
    duck = 1 - 0.45 * np.clip(envv * 3, 0, 1)
    bed = bed * duck * 10 ** (music_db / 20) / (np.max(np.abs(bed)) + 1e-9)
    fx = np.zeros((2, n))
    for i, (at, kind) in enumerate(cues):
        _, tones = chord_at(at, mood)
        if kind == "whoosh":
            clip = whoosh(seed=i)
        elif kind == "chime":
            clip = chime([m + 12 for m in tones])
        elif kind == "riser":
            clip = riser(seed=i)
        else:
            clip = pop(hz(tones[i % len(tones)] + 12))
        place(fx, clip, at, SFX_GAIN.get(kind, 0.4))
    fx *= 10 ** (sfx_db / 20)
    return np.stack([v, v]) + fx + bed
