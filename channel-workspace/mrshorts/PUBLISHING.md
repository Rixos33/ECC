# Publishing checklist: @mrshorts1737 Shorts

Metadata per Short lives in `metadata.json` (title, 2 A/B alt titles, description, tags, pinned comment, playlist).
Rules below were checked against current guidance (see Sources). Re-check the disclosure help page before each batch; policies change.

## Before upload (per Short)
- [ ] Script fact-checked: `sources` and `caveats` in `scripts/<id>.json` resolved (e.g. 05 Ariely attribution, 09 on-screen time spans, 10 Brichter quote).
- [ ] Final render is vertical 9:16 and 3 minutes or less (ours run ~35-60 s). The hook line is spoken in the first 1-2 s.
- [ ] The title's promise is paid off in the video. Only use an alt title if it is equally true.

## YouTube Studio upload settings
- [ ] Title: from `metadata.json`. Keep the hook in the first ~40 characters (the Shorts feed truncates longer titles). No hashtags in the title.
- [ ] Description: paste as-is. The first 3 hashtags show as links above the title; use 3, always including #shorts.
- [ ] Tags: paste them, but expect little effect. YouTube says tags play a minimal role (mostly for misspellings).
- [ ] Playlist: "Science" or "Psychology" per `metadata.json`. Create both playlists once.
- [ ] Audience: "No, it's not made for kids".
- [ ] Altered or synthetic content: select **No** for these 10 (see below).
- [ ] Category: Education. Language: English. Caption certification: none needed.
- [ ] Comments: on, set to "Hold potentially inappropriate comments".
- [ ] Remixing: allowed (it can bring discovery).
- [ ] Related video: link the Short to a relevant video on the channel once one exists, e.g. link 06/07 to the planned long video.
- [ ] Visibility: Schedule (see cadence). Do not publish as Unlisted and then flip to Public.

## Synthetic-content disclosure
- The "Altered or synthetic content" toggle is for **realistic** content that could mislead: a real person
  saying or doing something they didn't, a real event or place altered, or a realistic scene that never happened.
- It is not needed for: AI voice narration that doesn't impersonate a real person, AI help with the script, or clearly
  animated or non-realistic visuals. Our flat-vector animation with a stock neural TTS voice falls in this group, so select **No**.
- Switch to **Yes** if any Short ever: clones a real person's voice (including a celebrity or "Einstein"),
  uses photorealistic AI footage of real events (e.g. fake "CCTV" for 08), or makes a real scientist appear to speak.
- Optional transparency: add "Narration: AI voice" to the channel About section.
  The calendar marks the psychology Shorts as voice "You". If you record those yourself, nothing changes.

## Scheduling cadence (matches calendar.csv)
- Day 14: upload all ready Shorts and schedule them. Day 15-30: **1 Short per day**, alternating science and psychology.
- Order for this batch: 1, 5, 3, 6, 4, 7, 2, 8, (15, 16, 19, 11, 14 from batch 2), 10, 9.
- Publish at one fixed time each day. Start at 1-2 hours before your audience's evening peak. After 2 weeks, use Analytics >
  Audience > "When your viewers are on YouTube".
- Note: calendar.csv labels Short 09 (time perception) as `science`, but its playlist is Psychology.
- Change one variable at a time (title or hook, not both) so you can learn from it.

## First 24 hours after each Short goes live
- [ ] Pin the `pinned_comment` right away.
- [ ] Reply to early comments within the first few hours. Real replies only, no engagement pods, no bought views or likes.
- [ ] Correct factual pushback openly. If a commenter is right, pin a correction and note it for the script template.
- [ ] Share natively once where it fits (a community post, relevant subreddits that allow it). Don't spam.
- [ ] Log in a sheet: publish time, title used, 1-hour and 24-hour views, viewed vs swiped away.

## Analytics after 48 hours (Studio > Content > Short > Analytics)
- **Viewed vs swiped away**: the share of feed impressions where people stayed.
  This mostly measures the first frame and first line. Many creators aim for about 70%+.
  If it's low, rework the opening visual and first sentence for the next Short. Don't re-upload.
- **Average percentage viewed / retention curve**: look for the drop point. A cliff at 0-3 s means the hook failed.
  A mid-video dip means a slow or dense line, so cut it in future scripts. Over 100% means people rewatch or loop, which is good.
- **Traffic source**: check that most views come from the Shorts feed.
  If views are near zero with 0 impressions, check the Short isn't restricted and "made for kids" is off.
- Title A/B: if Studio offers "Test & compare" for Shorts titles on your account, test `alt_titles`.
  Otherwise, try alt titles on future similar topics rather than editing live Shorts repeatedly.

## Analytics after 7 days
- Compare all Shorts on: views, viewed vs swiped away, average % viewed, likes per 1k views,
  **subscribers gained**, comments.
- Split by lane (science vs psychology) and by voice (AI vs own). Did either lane or voice clearly win on swipe-away or retention?
- Channel > Audience: returning vs new viewers, and top geographies (adjust publish time).
- Write one learning per Short, e.g. "question hooks beat statement hooks", and apply it to batch 2 scripts.
- Top 3 Shorts by retention + subs are candidates to expand into the first long video (PLAN.md step 9).
- Treat all benchmarks as hypotheses. No reach or monetization outcome is guaranteed.

## Sources
- YouTube Help, "Disclosing use of altered or synthetic content": support.google.com/youtube/answer/14328491
  (exempts AI script help, cloning your own voice, and animated or non-realistic scenes; requires disclosure for realistic misleading content).
- YouTube Help, tags: support.google.com/youtube/answer/146402 ("tags play a minimal role in your video's discovery").
- Shorts hashtag display, first 3 above the title: hashtagtools.io/blog/youtube-shorts-hashtags-title-vs-description-2026
- Feed title truncation, ~40-50 characters: vidiq.com/blog/post/youtube-shorts-titles ; hashtagtools.io Shorts character limits 2026.
- Viewed vs swiped away metric: YouTube Community video, support.google.com/youtube/community-video/273390203 ; buffer.com Shorts analytics guide.

## Mascot teaser chain (publish in this order)

Each Short ends with Mr. Shorts asking the question that the NEXT Short answers, so the order matters:

01 sky -> 05 decoy -> 03 GPS -> 06 illusory truth -> 04 shipping container -> 07 anchoring -> 02 tickle -> 08 bystander -> 10 phone -> 09 time

09 teases "Why do planes fly a curve when a straight line looks shorter?" (topic 15, curved flight routes), which
is not made yet: render it before publishing 09, or change 09's `teaser`. If you reorder the schedule, update each
script's `teaser` and re-render. Put the next Short's link in the pinned comment once it is live.
