#!/usr/bin/env python3
"""
Posts the next un-posted item from posts/captions.json to Instagram via the
Metricool API, but only if at least MIN_GAP_DAYS have passed since the last
auto-post. Designed to run daily from a GitHub Actions cron job; the gap
check is what actually spaces the posts out every few days.

Required environment variables:
  METRICOOL_API_TOKEN  - personal API token (Metricool > Account Settings > API)
  METRICOOL_USER_ID    - your Metricool numeric user id
  METRICOOL_BLOG_ID    - the numeric id of the brand/profile to post as
Optional:
  MIN_GAP_DAYS         - minimum days between auto-posts (default 2)
  PUBLISH_DELAY_MIN    - minutes from now to schedule the post (default 20)
  TIMEZONE             - IANA timezone for the publication date (default Europe/London)
"""
import datetime
import json
import os
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request

CAPTIONS_PATH = "posts/captions.json"
API_BASE = "https://app.metricool.com/api"


def api_get(url, token):
    req = urllib.request.Request(url, headers={"X-Mc-Auth": token})
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read().decode())


def api_post(url, body, token):
    data = json.dumps(body).encode()
    req = urllib.request.Request(
        url, data=data, method="POST",
        headers={"X-Mc-Auth": token, "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read().decode())


def git(*args):
    subprocess.run(["git", *args], check=True)


def main():
    token = os.environ["METRICOOL_API_TOKEN"]
    user_id = os.environ["METRICOOL_USER_ID"]
    blog_id = os.environ["METRICOOL_BLOG_ID"]
    min_gap_days = float(os.environ.get("MIN_GAP_DAYS", "2"))
    publish_delay_min = int(os.environ.get("PUBLISH_DELAY_MIN", "20"))
    timezone = os.environ.get("TIMEZONE", "Europe/London")
    repo = os.environ["GITHUB_REPOSITORY"]  # e.g. HoomanQuant/hoomanquant-ai-agent

    with open(CAPTIONS_PATH, encoding="utf-8") as f:
        data = json.load(f)

    meta = data.setdefault("_meta", {})
    posts = data.setdefault("posts", {})

    now = datetime.datetime.utcnow()
    last_posted_at = meta.get("last_posted_at")
    if last_posted_at:
        last_dt = datetime.datetime.fromisoformat(last_posted_at)
        elapsed = now - last_dt
        if elapsed.total_seconds() < min_gap_days * 86400:
            remaining = datetime.timedelta(days=min_gap_days) - elapsed
            print(f"Only {elapsed} since last auto-post; waiting "
                  f"{remaining} more before the next one. Nothing to do.")
            return

    next_item = None
    for filename, entry in posts.items():
        if not entry.get("posted"):
            next_item = (filename, entry)
            break

    if not next_item:
        print("No unposted items left in captions.json. Add more to the queue!")
        return

    filename, entry = next_item
    media_url = f"https://raw.githubusercontent.com/{repo}/main/posts/{filename}"
    print(f"Next up: {filename} ({entry.get('topic', 'untitled')})")

    # Normalize the media so Metricool hosts it and gives us a mediaId.
    media_ref = None
    try:
        norm_url = (f"{API_BASE}/actions/normalize/image/url"
                    f"?url={urllib.parse.quote(media_url, safe='')}")
        norm = api_get(norm_url, token)
        media_id = norm.get("mediaId") or norm.get("id")
        if media_id:
            media_ref = [{"mediaId": media_id}]
        else:
            print("Normalize response had no mediaId, falling back to raw URL:", norm)
    except urllib.error.HTTPError as e:
        print("Normalize call failed, falling back to raw URL:", e.read().decode())

    if media_ref is None:
        media_ref = [media_url]

    publish_at = now + datetime.timedelta(minutes=publish_delay_min)
    body = {
        "autoPublish": True,
        "text": entry["caption"],
        "media": media_ref,
        "providers": [{"network": "instagram"}],
        "instagramData": {"type": "POST"},
        "publicationDate": {
            "dateTime": publish_at.strftime("%Y-%m-%dT%H:%M:%S"),
            "timezone": timezone,
        },
    }

    post_url = f"{API_BASE}/v2/scheduler/posts?blogId={blog_id}&userId={user_id}"
    try:
        result = api_post(post_url, body, token)
    except urllib.error.HTTPError as e:
        print("ERROR scheduling post:", e.read().decode())
        sys.exit(1)

    print("Scheduled successfully:", json.dumps(result)[:500])

    entry["posted"] = True
    meta["last_posted_at"] = now.isoformat()
    with open(CAPTIONS_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")

    git("config", "user.email", "actions@github.com")
    git("config", "user.name", "auto-poster-bot")
    git("add", CAPTIONS_PATH)
    git("commit", "-m", f"Auto-post: mark {filename} as posted")
    git("push")


if __name__ == "__main__":
    main()
