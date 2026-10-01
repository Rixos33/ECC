# Short evaluation rubric (used by the gan-evaluator review loop)

Benchmark: Kurzgesagt-level explainer craft, compressed into a 20-40 s vertical Short.
Score each criterion 1-10. Be strict: 7 means it could plausibly sit next to a top science Short.

| # | Criterion | 10 looks like |
|---|-----------|---------------|
| 1 | Hook (first 1.5 s) | Frame 0 is a complete, striking image plus a question or tension. No fade-in and no logo. The viewer knows what the payoff will be. |
| 2 | Visual storytelling | Every beat shows the idea with illustrated objects or characters, not just text. Props match the words being spoken. |
| 3 | Art direction | A cohesive palette, flat-vector shading, depth (background, subject, foreground), a balanced composition that fills the safe area, nothing clipped or overlapping. |
| 4 | Motion and pacing | Something meaningful moves at all times. Visual changes come every 2-4 s. Entrances are timed to the narration. |
| 5 | Captions | 1-3 words, legible on a phone, the current word highlighted, never colliding with visuals or the Shorts UI (bottom 20%, right 12%). |
| 6 | Narration | Natural prosody, good pace (2.5-3.2 words/s), correct pronunciation (Whisper match >= 0.95), breathing room after the hook and the reveal. |
| 7 | Sound | The music bed supports without masking the voice. SFX land on transitions and reveals. Loudness is about -14 LUFS. |
| 8 | Payoff and loop | A clear "aha" reveal. The last line flows back into the first so the Short replays. |
| 9 | Accuracy and honesty | Claims match the sources, uncertainty is stated, and the title is paid off. |
| 10 | Technical | 1080x1920, 30 fps, 20-45 s, file < 8 MB, no artefacts. |

Pass bar for publishing: average >= 7.5, and no criterion below 6.
