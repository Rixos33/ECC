# @mrshorts1737 - Channel Plan

Channel: new, no stats. Niche: curious science + psychology explainers, Shorts-first, long videos for monetization.
Owner: 15 h/week, narrates or uses AI voice, budget ~$0-50/month. Partner Program thresholds: check YouTube's help pages (they change).

## Steps (status)
1. [x] Skill `youtube-channel-growth` added to ECC.
2. [x] Positioning, pillars, 30 Short topics, 30-day calendar (`calendar.csv`).
3. [x] Renderer v2 (`render_short.py` + `art.py` + `audio.py`): flat-vector animated scenes (skia), word-cued shots,
       neural AI narration (edge-tts, ElevenLabs optional), word-synced captions, procedural music + SFX, -14 LUFS, ~2-5 MB files.
4. [x] Six review rounds with the ECC gan-evaluator against `EVAL.md` (5.31 -> 6.20 -> 6.59 -> 6.69 -> 6.90 -> R6),
       plus python-reviewer code reviews, `lint_scenes.py` layout linter and `qa.py` (Whisper narration check, loudness, size).
5. [x] Neural AI voice (en-US-AndrewMultilingualNeural, +18%); Whisper match 0.96-1.00 on all 10.
6. [x] Scripts 1-10 written and sourced by the marketing agent (primary sources + caveats in each JSON); all 10 rendered in `out/`.
       Owner: listen to each Short once (sound/voice can't be judged automatically) and spot-check `sources`/`caveats`.
7. [ ] Upload + schedule in YouTube Studio (days 14-15) using `metadata.json` + `PUBLISHING.md`. Disclose synthetic voice/imagery where required.
8. [ ] Daily publishing (days 15-30). Sunday review: viewed vs swiped away (>70%), average % viewed (loop target 100%), subs/Short.
9. [ ] Expand top 3 Shorts into first long video ("5 Ways Your Mind Lies to You", 7-9 min, own voice).
10. [ ] Lead magnet ("10 Thinking Traps"), then workbook, then course once 5-10 topics prove out.

## Guardrails
- Original scripts and visuals only; no re-uploaded third-party footage (reused-content policy).
- Human fact-check before every publish; do not fully automate script-to-publish.
- No guaranteed monetization date.

## Running
See README.md. Quick start (needs ffmpeg):
    python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
    ./render_all.sh            # renders scripts/*.json -> out/ and runs QA
