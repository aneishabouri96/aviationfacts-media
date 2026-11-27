# aviationfacts-media

Public media and posting schedule for Aviation Facts Daily.

- `posts/<date-topic>/`: finished, approved post media (served via raw.githubusercontent.com)
- `schedule.json`: approved posts with publish time (UTC)
- `published.json`: written by the workflow after each post goes live
- `.github/workflows/publish.yml`: runs every 10 minutes and publishes due posts via the Instagram API. Needs the repository secret `IG_TOKEN`.

## Stories

- `"type": "story"` with exactly one file: JPEG 1080x1920 (image story) or MP4/MOV 9:16, max 60 s (video story). No caption.
- `"after": "<id>"` holds a story back until that post is live (used for "new reel" teasers).
- Not possible via the API, stays manual in the Instagram app: polls, quizzes, question box, link and music stickers, mentions, adding to highlights, sharing a feed post into a story.
- Story graphics are built with `posts/src/story.py` (project files) from `stories.json`.
- Dry run without publishing: run the workflow manually with `test_id` = schedule id. Offline check: `python3 scripts/publish.py --validate`.

## Timing
GitHub's cron often runs only about once an hour. So each run waits for entries due within the next 65 minutes and publishes them on time (public repo: Actions minutes are free). Stories that are more than 12 hours late are skipped, because a "this day" or teaser story no longer makes sense then (override with `max_late_h`). published.json is committed right after each post.

## Posting slots (US prime time, from Mon 30.11.2026)
Main audience is the US (Eastern Time). Berlin = ET + 6 h (UTC+1 / UTC-5 in winter).
- Reels (IG) + YouTube Shorts: 00:30 Berlin = 18:30 ET = `23:30Z` (the evening of the US calendar day)
- Carousels: 18:00 Berlin = 12:00 ET = `17:00Z`
- Teaser story for a reel: 30 min after the reel (`after` = reel id)
- Other stories ("this day", profiles): 15:00 Berlin = 09:00 ET = `14:00Z`
- YouTube long videos: 23:00 Berlin = 17:00 ET = `22:00Z`
Watch out for DST: from 8.3.2027 (US) / 28.3.2027 (EU) the offsets shift; recheck then.
