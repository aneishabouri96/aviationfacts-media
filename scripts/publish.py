"""Publish due Instagram posts listed in schedule.json via the Instagram API (Instagram Login).

Each entry in schedule.json:
  {"id": "2026-11-25-a380", "publish_at": "2026-11-25T12:00:00Z", "type": "carousel"|"image"|"reel",
   "media": ["posts/.../01.jpg", ...], "caption": "..."}
Media paths are served publicly from raw.githubusercontent.com. Published ids go to published.json.
"""
import json, os, sys, time, urllib.parse, urllib.request
from datetime import datetime, timezone

API = "https://graph.instagram.com/v23.0"
TOKEN = os.environ.get("IG_TOKEN", "")
if not TOKEN:
    print("IG_TOKEN secret not set yet, nothing to do")
    sys.exit(0)
REPO = os.environ["GITHUB_REPOSITORY"]
RAW = f"https://raw.githubusercontent.com/{REPO}/main/"


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


def publish(e):
    t, media, cap = e["type"], e["media"], e.get("caption", "")
    if t == "image":
        cid = call("POST", "me/media", image_url=url(media[0]), caption=cap)["id"]
    elif t == "reel":
        kw = dict(media_type="REELS", video_url=url(media[0]), caption=cap, share_to_feed="true")
        if e.get("cover"):
            kw["cover_url"] = url(e["cover"])
        cid = call("POST", "me/media", **kw)["id"]
    elif t == "carousel":
        kids = []
        for m in media:
            kid = call("POST", "me/media", image_url=url(m), is_carousel_item="true")["id"]
            wait_ready(kid)
            kids.append(kid)
        cid = call("POST", "me/media", media_type="CAROUSEL", children=",".join(kids), caption=cap)["id"]
    else:
        raise ValueError(t)
    wait_ready(cid)
    return call("POST", "me/media_publish", creation_id=cid)["id"]


def main():
    sched = json.load(open("schedule.json"))
    done = json.load(open("published.json")) if os.path.exists("published.json") else {}
    now = datetime.now(timezone.utc)
    changed, failed = False, False
    for e in sched:
        if e["id"] in done or e.get("paused"):
            continue
        at = datetime.fromisoformat(e["publish_at"].replace("Z", "+00:00"))
        if at > now:
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
    if "--check" in sys.argv:
        print(call("GET", "me", fields="user_id,username"))
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
