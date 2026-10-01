# @mrshorts1737 production kit

Turns a script JSON into a finished vertical Short (1080x1920, 30 fps, H.264/AAC) with:

- flat-vector animated scenes in the style of a science-explainer channel (`art.py`, drawn with skia)
- AI narration (`edge-tts` neural voices by default, ElevenLabs or macOS `say` optional)
- word-synced captions kept clear of the Shorts UI
- a procedurally generated music bed that ducks under the voice, plus whoosh/pop/chime SFX (`audio.py`). No licensed music, so no Content ID claims.
- two-pass loudness normalisation to -14 LUFS and a small file (CRF 24, `-tune animation`, about 2-4 MB per Short)

## Setup

    python3 -m venv .venv && .venv/bin/pip install -r requirements.txt   # needs ffmpeg on PATH
    .venv/bin/python render_short.py "scripts/*.json" out/

Options: `--voice en-US-BrianMultilingualNeural`, `--rate +8%`, `--pitch -2Hz`, `--crf 24`, `--music-db -19`,
`--tts elevenlabs --voice <voice_id>` (needs `ELEVENLABS_API_KEY`), `--tts say`. TTS results are cached in `.tts-cache/`.

## Script schema

```json
{
  "id": "short02_cant_tickle_yourself",      // [A-Za-z0-9_-]+, also the output filename
  "handle": "@mrshorts1737",
  "title": "Why you can't tickle yourself",
  "palette": "violet|blue|teal|green|orange|red|pink|navy",
  "bg": "space|sky|plain",
  "ground": "planet|hill|sea|none",           // optional; default planet for space, hill otherwise
  "mood": "wonder|curious|tense|playful",     // music bed chord progression
  "lines": [
    {
      "text": "Your brain predicts your own touch, so it barely registers.",
      "say": "optional respelling for the TTS only, e.g. 'Arry-ELLY' (captions still show text)",
      "shots": [                                                    // 1-3 shots; each is a hard cut
        {"scene": [{"prop": "brain", "x": 0.5, "y": 0.35, "s": 1.3, "highlight": "cerebellum"}]},
        {"on": "touch",                                             // cut when this word is spoken
         "scene": [{"prop": "person", "x": 0.5, "y": 0.4, "s": 1.3},
                   {"prop": "feather", "x": 0.72, "y": 0.3, "s": 0.8, "on": "barely"}],  // pops in on "barely"
         "cam": {"zoom": [1.0, 1.15]}}
      ],
      "pause": 0.3,                                                 // optional silence after the line (s)
      "sfx": "chime", "sfx_at": 0.5                                 // optional extra cue: whoosh|pop|chime
    }
  ],
  "teaser": {"next": "05", "question": "Why would a shop sell something it hopes nobody buys?",
             "label": "USELESS OPTION?"},     // Mr. Shorts asks this at the end; it is the NEXT Short's hook
  "sources": [{"claim": "", "url": "", "note": ""}],
  "caveats": ""
}
```

A shot may set `"tint": "violet"` to wash the background in a colour (e.g. a violet sky for a hook).

A line may instead use the single-shot short form: `"scene": [...]`, `"visual": {"type": ...}`, `"cam": {...}`.

Placement: `x`, `y` are fractions of the 1080x1920 frame. Keep the focus between y 0.15 and 0.62, because captions
sit at y about 0.69 and the Shorts UI covers the bottom 20% and the right edge. `s` is the scale (props are
about 400 px wide at s=1). `delay` staggers entrances (props pop in with a small overshoot, and a pop SFX is
added automatically). `to: [x, y]` glides a prop across the beat, `rot` / `spin` (deg / deg per s) rotate it,
`flip: true` mirrors it, and `on: "word"` makes it pop in exactly when that word is spoken. `layer: true` marks an
intentional overlap (for example a pin on a phone). Any other keys are passed to the prop.

Each shot is auto-framed: the camera zooms (up to 2.2x) so the shot's content fills the safe area. Check layouts
without rendering using `.venv/bin/python lint_scenes.py "scripts/*.json"`.

## Props (`art.py`)

| prop | params |
|---|---|
| `arrow` | color, length=260, angle=0 |
| `bars` | bars=[[label, 0..1, optional colour]...], sub |
| `big` | big (<= 8 chars), sub, color |
| `brain` | color='pink', highlight=None / 'cerebellum' |
| `bubble` | label, color='white', tail='left'/'right' (speech bubble) |
| `bulb` | lit=True |
| `calendar` | day, label, flip=False |
| `camera` | (CCTV camera) |
| `card` | label, price, color, accent, best=False, strike=False (price card) |
| `check` | ok=True (green tick / red cross) |
| `clock` | color, speed=1.0 |
| `coin` | label='$', color |
| `container` | color, label (shipping container) |
| `crowd` | n=5, colors=[...], mood |
| `eye` | color (iris) |
| `feather` | color |
| `hourglass` | color |
| `label` | label, size=80, color (plain outlined text) |
| `list` | items=[...] (up to 3) |
| `moon` | color |
| `mountain` | color |
| `person` | color, mood=neutral/happy/sad/surprised, look, wave=False (blob character) |
| `phone` | color, notify=True |
| `photons` | colors=[...] (wavy light rays) |
| `pin` | color (map pin) |
| `planet` | color, land, atmosphere (or null), shape='round'/'square', pins=N (sample sites) |
| `question` | big='?', sub |
| `wheel` | values=[8 numbers], stop=index that lands under the pointer |
| `bird` | color='grey', peck=True (pigeon) |
| `robot` | color |
| `heart` | color |
| `speaker` | color (intercom/loudspeaker with sound waves) |
| `newspaper` | headline |
| `thumb` | color (like button) |
| `frame` | label, color (picture frame) |
| `crane` | color (port crane lifting a container) |
| `tv` | label, people=N (CCTV monitor) |
| `package` | color, label (product box) |
| `rain`, `salt`, `satellite`, `slot`, `spectrum` | (no params) |
| `ship` | color, containers=True |
| `sun` | color |
| `timeline` | points=[[when, what]...] (up to 4) |
| `versus` | left, right, sub, lcolor, rcolor |
| `wave` | color (sea surface) |

Colours are palette names (`white yellow orange red pink purple violet blue cyan teal green grey navy brown skin`) or `#rrggbb`.

## The mascot (Mr. Shorts)

A small owl in glasses and red shorts (`mascot` prop). When a script has a `teaser`, he watches from the bottom-left
corner for the whole Short (hopping on the reveal chime), then steps forward at the end, asks the teaser question in
his own voice (`--mascot-voice`, default `en-US-AnaNeural`) with a moving beak, and says the answer is in the next
Short. The teaser must be the hook of the Short published next, so keep `teaser.next` in step with the publishing
order. `--no-mascot` renders without him (and keeps the seamless loop).

## Retention rules baked into the renderer

- Frame 0 already shows the hook visual (no fade-in), and the loop line flows straight back into the hook.
- A new shot every 2-4 s (hard cut with a 0.22 s punch-in and a whoosh), cut on spoken words. Within a shot, a slow camera push-in, handheld drift and idle motion on every prop mean something is always moving.
- Captions are at most 3 words (2 if long) and at most 760 px wide, with the spoken word highlighted. The first caption is already on screen at frame 0.

## Guardrails

Fact-check every script (`sources`, `caveats`) before publishing. Tick YouTube's "altered or synthetic content"
disclosure where it applies. Original visuals and music only.
