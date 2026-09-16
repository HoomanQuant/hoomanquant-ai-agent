#!/usr/bin/env python3
"""
Posts the next un-posted item from posts/captions.json directly to Instagram
via Meta's official Instagram Graph API (free, no third-party service).

Required environment variables:
  IG_ACCESS_TOKEN   - long-lived User or Page access token with
                       instagram_basic + instagram_content_publish
  IG_BUSINESS_ID    - your Instagram Business Account numeric ID
Optional:
  MIN_GAP_DAYS       - minimum days between auto-posts (default 2)
  GRAPH_API_VERSION  - Graph API version (default v19.0)

Note: long-lived user/page tokens expire after ~60 days and need to be
regenerated manually (see AUTOPOST_README.md) unless upgraded to a
never-expiring Business Manager system-user token.
"""
import datetime
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

CAPTIONS_PATH = "posts/captions.json"


def graph_post(path, params, token):
    url = f"https://graph.facebook.com/{os.environ.get('GRAPH_API_VERSION', 'v19.0')}/{path}"
    params = dict(params)
    params["access_token"] = token
    data = urllib.parse.urlencode(params).encode()
    req = urllib.request.Request(url, data=data, method="POST")
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read().decode())


def git(*args):
    subprocess.run(["git", *args], check=True)


def main():
    token = os.environ["IG_ACCESS_TOKEN"]
    ig_id = os.environ["IG_BUSINESS_ID"]
    min_gap_days = float(os.environ.get("MIN_GAP_DAYS", "2"))
    repo = os.environ["GITHUB_REPOSITORY"]

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

    try:
        # Step 1: create a media container
        container = graph_post(
            f"{ig_id}/media",
            {"image_url": media_url, "caption": entry["caption"]},
            token,
        )
        creation_id = container.get("id")
        if not creation_id:
            print("ERROR: no creation id returned:", container)
            sys.exit(1)
        print("Created media container:", creation_id)

        # Media containers can take a few seconds to process; poll status.
        status = "IN_PROGRESS"
        for _ in range(10):
            status_resp = json.loads(urllib.request.urlopen(
                f"https://graph.facebook.com/{os.environ.get('GRAPH_API_VERSION', 'v19.0')}/"
                f"{creation_id}?fields=status_code&access_token={token}"
            ).read().decode())
            status = status_resp.get("status_code", "IN_PROGRESS")
            if status == "FINISHED":
                break
            time.sleep(3)
        print("Container status:", status)

        # Step 2: publish it
        publish = graph_post(f"{ig_id}/media_publish", {"creation_id": creation_id}, token)
        print("Published:", publish)

    except urllib.error.HTTPError as e:
        print("ERROR calling Instagram Graph API:", e.read().decode())
        sys.exit(1)

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
