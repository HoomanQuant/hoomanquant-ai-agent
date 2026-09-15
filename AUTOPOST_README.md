# Auto-posting to Instagram

This repo can post queued images to Instagram (`data.analytics` via Metricool)
automatically, on a free GitHub Actions schedule — no external server needed.

## How it works

- `posts/captions.json` is the queue. Each entry under `"posts"` is one image
  + caption, with a `"posted"` flag. `"_meta.last_posted_at"` tracks when the
  last auto-post went out.
- `.github/workflows/auto-post-instagram.yml` runs **daily** at 09:00 UTC.
- `scripts/post_next_to_instagram.py` checks how long it's been since
  `last_posted_at`. If less than `MIN_GAP_DAYS` (default 2), it does nothing.
  Otherwise it takes the next `"posted": false` entry, uploads it to
  Instagram via the Metricool API, marks it posted, and commits the change.

Net effect: **one new post roughly every 2 days**, fully automatic, for as
long as the queue has unposted entries.

## One-time setup required

The workflow needs a Metricool **API token** (different from an OAuth/MCP
connection — this is a raw API key for direct HTTP calls):

1. Go to Metricool → **Account Settings → API** and copy your token.
2. In this GitHub repo: **Settings → Secrets and variables → Actions → New
   repository secret**.
3. Name it `METRICOOL_API_TOKEN`, paste the token, save.

That's it — no other secrets needed. `METRICOOL_USER_ID` (5292696) and
`METRICOOL_BLOG_ID` (6873592, the `data.analytics` brand) are already set as
plain env vars in the workflow file since they aren't sensitive.

## Adding more posts to the queue

Add a new PNG to `posts/` and a matching entry under `"posts"` in
`captions.json`:

```json
"2026-10-01-my-new-topic.png": {
  "topic": "My New Topic",
  "caption": "Caption text with hashtags...",
  "posted": false
}
```

New entries are picked up in the order they appear in the file (oldest
un-posted first). When the queue runs dry, the workflow just logs "no
unposted items" and does nothing until you add more.

## Manual run / testing

Go to the repo's **Actions** tab → "Auto-post to Instagram" → **Run
workflow** to trigger it on demand instead of waiting for the schedule.

## Changing the cadence

Edit `MIN_GAP_DAYS` in `.github/workflows/auto-post-instagram.yml` (e.g. `"1"`
for daily, `"3"` for every 3 days).
