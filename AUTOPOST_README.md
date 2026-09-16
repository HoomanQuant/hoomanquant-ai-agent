# Auto-posting to Instagram (free, via Meta's Graph API)

This repo posts queued images to Instagram automatically on a free GitHub
Actions schedule, using Meta's own Instagram Graph API directly — no paid
third-party service required.

## How it works

- `posts/captions.json` is the queue. Each entry under `"posts"` is one image
  + caption, with a `"posted"` flag. `"_meta.last_posted_at"` tracks when the
  last auto-post went out.
- `.github/workflows/auto-post-instagram.yml` runs **daily** at 09:00 UTC.
- `scripts/post_next_to_instagram_graph.py` checks how long it's been since
  `last_posted_at`. If less than `MIN_GAP_DAYS` (default 2), it does nothing.
  Otherwise it takes the next `"posted": false` entry, publishes it straight
  to Instagram via the Graph API, marks it posted, and commits the change.

Net effect: **one new post roughly every 2 days**, fully automatic, for as
long as the queue has unposted entries — for $0.

## One-time setup required

1. **Instagram must be a Professional (Business/Creator) account** linked to
   a Facebook Page. (It already is, since Metricool was connected the same way.)
2. **Create a free Meta developer app** at
   [developers.facebook.com/apps](https://developers.facebook.com/apps) →
   Create App → type "Business".
3. As the app creator you're automatically an Admin, so Instagram publishing
   works on your own account with **no Meta App Review needed**.
4. Generate a token in
   [Graph API Explorer](https://developers.facebook.com/tools/explorer) with
   permissions: `instagram_basic`, `instagram_content_publish`,
   `pages_show_list`, `pages_read_engagement`, `business_management`.
5. Exchange it for a 60-day long-lived token:
   ```
   curl -i -X GET "https://graph.facebook.com/v19.0/oauth/access_token?grant_type=fb_exchange_token&client_id=APP_ID&client_secret=APP_SECRET&fb_exchange_token=SHORT_LIVED_TOKEN"
   ```
6. Find your Instagram Business Account ID:
   ```
   curl -i -X GET "https://graph.facebook.com/v19.0/me/accounts?access_token=LONG_LIVED_TOKEN"
   curl -i -X GET "https://graph.facebook.com/v19.0/PAGE_ID?fields=instagram_business_account&access_token=LONG_LIVED_TOKEN"
   ```
7. In this GitHub repo: **Settings → Secrets and variables → Actions → New
   repository secret**, and add:
   - `IG_ACCESS_TOKEN` — the long-lived token from step 5
   - `IG_BUSINESS_ID` — the numeric ID from step 6

## The one real restriction (why this is free)

Long-lived tokens expire after **~60 days**. When that happens the workflow
will fail with an auth error — just repeat steps 4–7 to get a fresh token and
update the `IG_ACCESS_TOKEN` secret. Takes about 5 minutes.

(To eliminate this entirely, you'd set up a Meta **Business Manager system
user** and generate a token for it — those don't expire — but that requires
a verified Business Manager account, which is extra setup beyond this
starter version.)

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

New entries are picked up in file order (oldest un-posted first). When the
queue runs dry, the workflow just logs "no unposted items" and waits for you
to add more.

## Manual run / testing

Go to the repo's **Actions** tab → "Auto-post to Instagram" → **Run
workflow** to trigger it on demand instead of waiting for the schedule.

## Changing the cadence

Edit `MIN_GAP_DAYS` in `.github/workflows/auto-post-instagram.yml` (e.g. `"1"`
for daily, `"3"` for every 3 days).
