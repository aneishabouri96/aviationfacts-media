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
