"""Publish due Instagram posts listed in schedule.json via the Instagram Graph API (Facebook Login, long-lived user token).

Each entry in schedule.json:
  {"id": "2026-11-25-a380", "publish_at": "2026-11-25T12:00:00Z", "type": "carousel"|"image"|"reel"|"story",
   "media": ["posts/.../01.jpg", ...], "caption": "..."}
type "story": exactly one file, JPEG image (1080x1920) or MP4/MOV video (9:16, max 60 s). No caption
(Instagram ignores captions on stories). Polls, quizzes, links, music and mentions are NOT possible
via the API; those stories stay manual in the Instagram app.
Media paths are served publicly from raw.githubusercontent.com. Published ids go to published.json.

Modes:
  (none)          publish every due, non-paused entry
  --check         only verify the token and print the account name (publishes nothing)
  --validate      offline check of schedule.json (fields, files, story formats); no API call
Optional "after": "<other id>" holds an entry back until that entry is in published.json
(e.g. a "new reel" teaser story only goes out once the reel itself is live).

  --test ID       build the Instagram container(s) for entry ID and wait until Instagram accepts the
                  media, but do NOT publish. Unpublished containers expire after 24 h.
"""
import json, os, sys, time, urllib.parse, urllib.request
from datetime import datetime, timezone

API = "https://graph.facebook.com/v23.0"
TOKEN = os.environ.get("IG_TOKEN", "")
REPO = os.environ.get("GITHUB_REPOSITORY", "aneishabouri96/aviationfacts-media")
# Serve media from the exact commit being run, so tests on a branch use that branch's files.
RAW = f"https://raw.githubusercontent.com/{REPO}/{os.environ.get('GITHUB_SHA', 'main')}/"
TYPES = ("image", "carousel", "reel", "story")
IMG_EXT = (".jpg", ".jpeg")
VID_EXT = (".mp4", ".mov")
IG_USER = None


def call(method, path, **params):
    params["access_token"] = TOKEN
    data = urllib.parse.urlencode(params).encode()
    url = f"{API}/{path}"
    if method == "GET":
        req = urllib.request.Request(url + "?" + data.decode())
    else:
        req = urllib.request.Request(url, data=data, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"{method} {path}: {e.code} {e.read().decode()[:500]}")


def resolve_ig_user():
    """Find the Instagram business account linked to the Facebook page(s) the token can see."""
    pages = call("GET", "me/accounts", fields="instagram_business_account{id,username}").get("data", [])
    for pg in pages:
        ig = pg.get("instagram_business_account")
        if ig and ig.get("username") == "aviationfacts_daily":
            return ig["id"], len(pages)
    return None, len(pages)


def wait_ready(cid, tries=40):
    for _ in range(tries):
        s = call("GET", cid, fields="status_code").get("status_code")
        if s == "FINISHED":
            return
        if s in ("ERROR", "EXPIRED"):
            raise RuntimeError(f"container {cid} status {s}")
        time.sleep(10)
    raise RuntimeError(f"container {cid} not ready")


def url(p):
    return p if p.startswith("http") else RAW + p


def is_video(p):
    return p.lower().split("?")[0].endswith(VID_EXT)


def create_container(e):
    """Create (but do not publish) the Instagram media container for entry e; return its id."""
    t, media, cap = e["type"], e["media"], e.get("caption", "")
    if t == "story":
        if is_video(media[0]):
            cid = call("POST", f"{IG_USER}/media", media_type="STORIES", video_url=url(media[0]))["id"]
        else:
            cid = call("POST", f"{IG_USER}/media", media_type="STORIES", image_url=url(media[0]))["id"]
    elif t == "image":
        cid = call("POST", f"{IG_USER}/media", image_url=url(media[0]), caption=cap)["id"]
    elif t == "reel":
        kw = dict(media_type="REELS", video_url=url(media[0]), caption=cap, share_to_feed="true")
        if e.get("cover"):
            kw["cover_url"] = url(e["cover"])
        cid = call("POST", f"{IG_USER}/media", **kw)["id"]
    elif t == "carousel":
        kids = []
        for m in media:
            kid = call("POST", f"{IG_USER}/media", image_url=url(m), is_carousel_item="true")["id"]
            wait_ready(kid)
            kids.append(kid)
        cid = call("POST", f"{IG_USER}/media", media_type="CAROUSEL", children=",".join(kids), caption=cap)["id"]
    else:
        raise ValueError(t)
    wait_ready(cid)
    return cid


def publish(e):
    cid = create_container(e)
    return call("POST", f"{IG_USER}/media_publish", creation_id=cid)["id"]


def validate(sched):
    """Offline sanity check of schedule.json. Returns a list of problems (empty = fine)."""
    probs, seen = [], set()
    seen_all = {x.get("id") for x in sched}
    for e in sched:
        i = e.get("id", "?")
        if i in seen:
            probs.append(f"{i}: duplicate id")
        seen.add(i)
        t, media = e.get("type"), e.get("media") or []
        if t not in TYPES:
            probs.append(f"{i}: unknown type {t!r}")
            continue
        try:
            datetime.fromisoformat(e["publish_at"].replace("Z", "+00:00"))
        except Exception:
            probs.append(f"{i}: bad or missing publish_at")
        if not media:
            probs.append(f"{i}: no media")
        for m in media + ([e["cover"]] if e.get("cover") else []):
            if not m.startswith("http") and not os.path.exists(m):
                probs.append(f"{i}: missing file {m}")
        if t == "story":
            if len(media) != 1:
                probs.append(f"{i}: a story needs exactly one file")
            elif not media[0].lower().endswith(IMG_EXT + VID_EXT):
                probs.append(f"{i}: story file must be .jpg (image) or .mp4/.mov (video)")
            if e.get("caption"):
                probs.append(f"{i}: stories have no caption on Instagram, remove it")
        if e.get("after") and e["after"] not in seen_all:
            probs.append(f"{i}: 'after' points to unknown id {e['after']}")
        if t == "image" and media and not media[0].lower().endswith(IMG_EXT):
            probs.append(f"{i}: Instagram API only takes JPEG images")
        if t == "carousel" and not 2 <= len(media) <= 10:
            probs.append(f"{i}: carousel needs 2-10 files")
    return probs


def main():
    global IG_USER
    sched = json.load(open("schedule.json"))
    probs = validate(sched)
    for p in probs:
        print("SCHEDULE PROBLEM", p)
    if "--validate" in sys.argv:
        print(f"{len(sched)} entries checked, {len(probs)} problems")
        sys.exit(1 if probs else 0)
    if not TOKEN:
        print("IG_TOKEN secret not set yet, nothing to do")
        sys.exit(0)
    IG_USER, npages = resolve_ig_user()
    if not IG_USER:
        print(f"Token works, but no linked Instagram account aviationfacts_daily found ({npages} pages visible)")
        sys.exit(1)
    if "--check" in sys.argv:
        print("Token OK, publishing as", call("GET", IG_USER, fields="username")["username"])
        sys.exit(0)
    if "--test" in sys.argv:
        tid = sys.argv[sys.argv.index("--test") + 1]
        e = next((x for x in sched if x["id"] == tid), None)
        if not e:
            print("TEST: no schedule entry", tid)
            sys.exit(1)
        try:
            create_container(e)
            print(f"TEST OK: Instagram accepted {e['type']} {tid}. Nothing was published.")
            sys.exit(0)
        except Exception as ex:
            print("TEST FAILED", tid, ex)
            sys.exit(1)
    done = json.load(open("published.json")) if os.path.exists("published.json") else {}
    now = datetime.now(timezone.utc)
    changed, failed = False, False
    for e in sched:
        if e["id"] in done or e.get("paused") or e.get("type") not in TYPES:
            continue
        at = datetime.fromisoformat(e["publish_at"].replace("Z", "+00:00"))
        if at > now:
            continue
        if e.get("after") and e["after"] not in done:
            print("waiting for", e["after"], "before", e["id"])
            continue
        try:
            mid = publish(e)
            done[e["id"]] = {"media_id": mid, "published_at": now.isoformat()}
            print("published", e["id"], mid)
            changed = True
        except Exception as ex:
            print("FAILED", e["id"], ex)
            failed = True
    if changed:
        json.dump(done, open("published.json", "w"), indent=2)
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
