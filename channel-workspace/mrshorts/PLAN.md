# @mrshorts1737 - Channel Plan

Channel: new, no stats. Niche: curious science + psychology explainers, Shorts-first, long videos for monetization.
Owner: 15 h/week, narrates or uses AI voice, budget ~$0-50/month. Partner Program thresholds: check YouTube's help pages (they change).

## Steps (status)
1. [x] Skill `youtube-channel-growth` added to ECC.
2. [x] Positioning, pillars, 30 Short topics, 30-day calendar (`calendar.csv`).
3. [x] Renderer (`render_short.py`) + Short #1 preview (`out/short01_sky_not_violet.mp4`, placeholder espeak voice).
4. [ ] Owner review of Short #1 style (fonts, visuals, pacing). Steer: more/less motion, colours, length.
5. [ ] Swap placeholder voice for neural AI voice or own recording (replace the espeak call in `render_short.py`).
6. [ ] Fact-check scripts 1-10 against primary sources (see `scripts.md`), then render 2-10 (add scene kinds per topic).
7. [ ] Upload + schedule in YouTube Studio (days 14-15). Disclose synthetic voice/imagery where required.
8. [ ] Daily publishing (days 15-30). Sunday review: viewed vs swiped away (>70%), average % viewed (loop target 100%), subs/Short.
9. [ ] Expand top 3 Shorts into first long video ("5 Ways Your Mind Lies to You", 7-9 min, own voice).
10. [ ] Lead magnet ("10 Thinking Traps"), then workbook, then course once 5-10 topics prove out.

## Guardrails
- Original scripts and visuals only; no re-uploaded third-party footage (reused-content policy).
- Human fact-check before every publish; do not fully automate script-to-publish.
- No guaranteed monetization date.

## Running
    sudo apt install ffmpeg espeak-ng fonts-dejavu-core && pip install pillow
    python3 render_short.py scripts/01-sky-not-violet.json out/
