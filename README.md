# aviationfacts-media

Public media and posting schedule for Aviation Facts Daily.

- `posts/<date-topic>/`: finished, approved post media (served via raw.githubusercontent.com)
- `schedule.json`: approved posts with publish time (UTC)
- `published.json`: written by the workflow after each post goes live
- `.github/workflows/publish.yml`: runs every 10 minutes and publishes due posts via the Instagram API. Needs the repository secret `IG_TOKEN`.
