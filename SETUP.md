# Setup checklist

The site works without any of these. Each one switches on a feature that otherwise shows "coming soon" or stays hidden.
Values go in **GitHub → repo Settings → Secrets and variables → Actions → New repository secret**, and are read at build time.

| Secret | Turns on | Where to get it |
|---|---|---|
| `PUBLIC_SUPABASE_URL` | Park voting, 👍/👎 feedback | Supabase project → Settings → API → Project URL |
| `PUBLIC_SUPABASE_ANON_KEY` | (same) | Supabase project → Settings → API → `anon` `public` key |
| `PUBLIC_GA4_ID` | Visitor analytics | Google Analytics → Admin → Data streams → Web → Measurement ID (`G-…`) |
| `PUBLIC_FEEDBACK_FORM_URL` | "Tell us what you think" links | Your Google Form's share link |

After adding or changing secrets, re-run the deploy: **Actions → Deploy site → Run workflow**.

## Supabase (votes + feedback)

1. Create a free project at <https://supabase.com> (any region; Sydney is closest).
2. Open **SQL Editor**, paste all of `supabase/migrations/001_votes_feedback.sql` and click **Run**.
3. Copy the Project URL and the `anon` key into the two secrets above. The anon key is safe to publish: the database
   only lets it *add* votes/feedback and read vote totals.
4. Check it (replace the two values):
   ```bash
   URL=https://YOUR-PROJECT.supabase.co; KEY=YOUR-ANON-KEY
   # a vote is accepted (expect HTTP 201)
   curl -s -o /dev/null -w "%{http_code}\n" -X POST "$URL/rest/v1/park_votes" -H "apikey: $KEY" -H "Authorization: Bearer $KEY" \
     -H "Content-Type: application/json" -d '{"park_id":"setup-test","voter_id":"00000000-0000-4000-8000-000000000000"}'
   # the same vote again is refused as a duplicate (expect 409)
   # raw votes are not readable (expect an empty list or a permission error)
   curl -s "$URL/rest/v1/park_votes?select=*" -H "apikey: $KEY" -H "Authorization: Bearer $KEY"
   # totals are readable
   curl -s "$URL/rest/v1/park_vote_counts?select=*" -H "apikey: $KEY" -H "Authorization: Bearer $KEY"
   ```
5. Delete the test vote in **Table Editor → park_votes**.

To see votes and feedback yourself, use the Supabase **Table Editor** (you're signed in as the owner, so RLS doesn't apply to you).

## GA4 (analytics)

1. <https://analytics.google.com> → Admin → Create property ("Christchurch Projects", New Zealand time zone).
2. Add a **Web** data stream for `https://hyunjinlee0131-wq.github.io/christchurch-projects/`.
3. Copy the Measurement ID (`G-XXXXXXX`) into `PUBLIC_GA4_ID`.

Events sent: `vote`, `reweight`, `near_me`, `share`, `feedback`, `open_park`. Find them under Reports → Engagement → Events.

## Feedback form (Google Forms)

1. <https://forms.google.com> → blank form "Christchurch Projects feedback".
2. Questions: *Which project?* (dropdown: Best Park, …), *What did you like?*, *What's missing or wrong?*, *Email (optional)*.
3. Send → link → copy, and put it in `PUBLIC_FEEDBACK_FORM_URL`. Responses go to a Google Sheet only you can see.

## GitHub Pages

Pages is published by `.github/workflows/deploy.yml` on every push to `main`. If it was never enabled:
Settings → Pages → Build and deployment → Source: **GitHub Actions**.
