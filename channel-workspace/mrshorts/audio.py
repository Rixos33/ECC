"""Procedural ambient music bed + UI sound effects (numpy), and the final mix.

Everything is synthesised locally, so there are no music-licensing or Content ID issues.
"""
import numpy as np

SR = 48000
MOODS = {  # chord progressions as MIDI notes, 4 beats each
    "wonder": [[53, 60, 64, 69], [48, 55, 64, 67], [45, 52, 60, 64], [43, 50, 59, 62]],   # Fmaj7 C Am G
    "curious": [[50, 57, 60, 65], [46, 53, 57, 62], [48, 55, 60, 64], [45, 52, 57, 60]],  # Dm Bb C Am
    "tense": [[45, 52, 55, 60], [41, 48, 53, 57], [43, 50, 55, 59], [40, 47, 52, 56]],    # Am F G E
    "playful": [[48, 55, 64, 67], [45, 52, 60, 69], [41, 53, 57, 64], [43, 55, 59, 62]],  # C Am F G
}


def hz(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def env(n, a, r):
    e = np.ones(n)
    na, nr = int(a * SR), int(r * SR)
    if na:
        e[:na] = np.linspace(0, 1, na) ** 2
    if nr:
        e[-nr:] *= np.linspace(1, 0, nr) ** 2
    return e


def reverb(x, seconds=2.4, mix=0.35, seed=1):
    rng = np.random.default_rng(seed)
    n = int(seconds * SR)
    ir = rng.standard_normal(n) * np.exp(-np.linspace(0, 7, n))
    ir /= np.sqrt(np.sum(ir ** 2))
    size = 1 << int(np.ceil(np.log2(len(x) + n)))
    wet = np.fft.irfft(np.fft.rfft(x, size) * np.fft.rfft(ir, size), size)[:len(x)]
    return (1 - mix) * x + mix * wet * 0.6


def music(duration, mood="wonder", bpm=96, seed=0):
    rng = np.random.default_rng(seed)
    beat = 60 / bpm
    prog = MOODS.get(mood, MOODS["wonder"])
    n = int((duration + 0.5) * SR)
    out = np.zeros((2, n))
    chord_len = 4 * beat
    tt = np.arange(int((chord_len + 1.2) * SR)) / SR
    k = 0
    while k * chord_len < duration + 0.5:
        chord = prog[k % len(prog)]
        s = int(k * chord_len * SR)
        # pad: detuned soft sines, stereo spread
        for m in chord[1:]:
            f = hz(m)
            for ch, det in ((0, 0.997), (1, 1.003)):
                w = (np.sin(2 * np.pi * f * det * tt) + 0.25 * np.sin(4 * np.pi * f * det * tt)
                     + 0.08 * np.sin(6 * np.pi * f * tt))
                seg = 0.05 * w * env(len(tt), 0.7, 1.1)
                e = min(n, s + len(seg))
                out[ch, s:e] += seg[:e - s]
        # sub bass
        b = 0.09 * np.sin(2 * np.pi * hz(chord[0] - 12) * tt) * env(len(tt), 0.3, 1.0)
        e = min(n, s + len(b))
        out[:, s:e] += b[:e - s]
        # plucked arpeggio, eighth notes
        notes = [m + 12 for m in chord[1:]] + [chord[1] + 24]
        for i in range(8):
            if rng.random() < 0.25:
                continue
            m = notes[rng.integers(len(notes))]
            nl = int(0.6 * SR)
            pt = np.arange(nl) / SR
            pl = (np.sin(2 * np.pi * hz(m) * pt) + 0.3 * np.sin(4 * np.pi * hz(m) * pt)) * np.exp(-pt * 7) * 0.045
            ps = s + int(i * beat / 2 * SR)
            pe = min(n, ps + nl)
            if ps < n:
                pan = rng.uniform(0.3, 0.7)
                out[0, ps:pe] += pl[:pe - ps] * (1 - pan) * 2
                out[1, ps:pe] += pl[:pe - ps] * pan * 2
        k += 1
    out = np.stack([reverb(out[0], seed=seed + 1), reverb(out[1], seed=seed + 2)])
    out = out[:, :int(duration * SR)]
    fade = int(0.4 * SR)
    out[:, -fade:] *= np.linspace(1, 0.3, fade)  # soft tail; loop restarts on the hook
    return out


def whoosh(length=0.45, seed=0):
    rng = np.random.default_rng(seed)
    n = int(length * SR)
    x = rng.standard_normal(n)
    y = np.zeros(n)
    cut = 0.02 + 0.25 * np.sin(np.linspace(0, np.pi, n)) ** 2
    acc = 0.0
    for i in range(n):  # time-varying one-pole low-pass sweep
        acc += cut[i] * (x[i] - acc)
        y[i] = acc
    y *= np.sin(np.linspace(0, np.pi, n)) ** 1.5
    return y / (np.max(np.abs(y)) + 1e-9) * 0.35


def riser(length=1.1, seed=0):
    """Rising filtered-noise swell plus an upward sine sweep, ending on the reveal."""
    rng = np.random.default_rng(seed)
    n = int(length * SR)
    t = np.arange(n) / SR
    x = rng.standard_normal(n)
    y = np.zeros(n)
    acc = 0.0
    cut = 0.01 + 0.2 * (t / length) ** 2
    for i in range(n):
        acc += cut[i] * (x[i] - acc)
        y[i] = acc
    y /= np.max(np.abs(y)) + 1e-9
    sweep = np.sin(2 * np.pi * np.cumsum(200 + 600 * (t / length) ** 2) / SR) * 0.3
    return (0.6 * y + sweep) * (t / length) ** 2 * 0.3


def pop(freq=880, length=0.12):
    t = np.arange(int(length * SR)) / SR
    f = freq * np.exp(-t * 12)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 30) * 0.3


def chime(length=1.0):
    t = np.arange(int(length * SR)) / SR
    y = sum(np.sin(2 * np.pi * hz(m) * t) * a for m, a in ((84, 0.3), (88, 0.2), (91, 0.15)))
    return reverb(y * np.exp(-t * 4), 1.5, 0.4) * 0.5


def place(buf, clip, at):
    s = int(at * SR)
    if s >= buf.shape[-1] or s < 0:
        return
    e = min(buf.shape[-1], s + clip.shape[-1])
    buf[..., s:e] += clip[..., :e - s]


def _moving_avg(x, n):
    """Centred moving average via cumulative sums (O(len(x)), same length as x)."""
    c = np.cumsum(np.concatenate([np.zeros(n // 2 + 1), x, np.zeros(n - n // 2)]))
    return (c[n:n + len(x)] - c[:len(x)]) / n


def mixdown(voice, duration, cues, mood="wonder", seed=0, music_db=-17.0, sfx_db=-8.0):
    """voice: mono float array at SR. cues: list of (time, kind). Returns stereo float array."""
    n = int(duration * SR)
    v = np.zeros(n)
    v[:min(n, len(voice))] = voice[:n]
    bed = music(duration, mood, seed=seed)
    # duck the bed under the narration (smoothed voice envelope)
    win = int(0.05 * SR)
    envv = np.sqrt(np.maximum(_moving_avg(v ** 2, win), 0))
    envv = _moving_avg(envv, int(0.25 * SR))
    envv /= (envv.max() + 1e-9)
    duck = 1 - 0.45 * np.clip(envv * 3, 0, 1)
    bed *= duck * 10 ** (music_db / 20) / (np.max(np.abs(bed)) + 1e-9)
    fx = np.zeros(n)
    for at, kind in cues:
        clip = {"whoosh": lambda: whoosh(seed=int(at * 10)), "pop": pop, "chime": chime,
                "riser": lambda: riser(seed=int(at * 10))}[kind]()
        place(fx, clip, at)
    fx *= 10 ** (sfx_db / 20)
    return np.stack([v + fx, v + fx]) + bed
