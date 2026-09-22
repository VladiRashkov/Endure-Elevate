# Endure & Elevate

A running tracker that connects to Strava, syncs your activities into its own
database, and shows them back to you as a pace planner, a running-progress
dashboard, and a per-run breakdown with route map, pace splits, elevation,
heart rate, and estimated VO2 max.

**[Live demo →](#)** *(add your Render URL here once deployed)*
*First load can take ~30s to wake up — it's on a free tier that sleeps when idle.*

No Strava account needed to look around — there's a demo login pre-loaded
with sample runs. *(link it here once demo mode is added)*

---

## What it does

- **Auth** — register / log in, session-based, passwords hashed with `pbkdf2:sha256`
- **Strava OAuth2** — connects your account, pulls your run history, stores it locally so the app isn't re-fetching from Strava on every page load
- **Home panel** — jumps into your most recent run, or into progress/pace/all-time views
- **Daily Activity** — one run in detail: route map, pace-per-km chart, elevation profile, heart rate, VO2 max estimate
- **Running Progress** — last three runs, plus a month-by-month distance breakdown for the year
- **All-Time Runs** — every logged run in one sortable table
- **Pace Planner** — pick a distance and goal time, get a full km-by-km pace table you can edit by hand

## Stack

`Flask` · `SQLAlchemy` · `SQLite` · Strava OAuth2 · `pytest`

Charts and the elevation/VO2 visuals are hand-built inline SVG — no
`matplotlib`, no external chart library, no CDN dependency. More on why
below.

---

## Try it yourself

```bash
git clone https://github.com/VladiRashkov/Endure-Elevate.git
cd Endure-Elevate
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Create a `.env` file in the project root:
```
STRAVA_CLIENT_ID=your_strava_client_id
STRAVA_CLIENT_SECRET=your_strava_client_secret
FLASK_SECRET_KEY=any_random_string
```

You'll need your own [Strava API application](https://www.strava.com/settings/api)
to get a client ID and secret — set its Authorization Callback Domain to
`127.0.0.1`.

```bash
python app.py
```

Then open `http://127.0.0.1:5000`.

**Run the tests:**
```bash
pip install pytest geopy polyline
pytest tests/ -v
```

---

## Screenshots

*(drop a few images into a `docs/` folder and reference them here, e.g.)*

`![Login](docs/screenshot-login.png)` &nbsp;
`![Daily Activity](docs/screenshot-daily-activity.png)` &nbsp;
`![Pace Planner](docs/screenshot-pace-planner.png)`

---

## Challenges I ran into

**Strava's rate limit was hit almost immediately.**
Every page — the home panel, Running Progress, even the Pace Planner —
was calling Strava's API and re-fetching the user's *entire* activity
history from page 1, on every single request. A user with a year of
running history could trigger dozens of Strava API calls just from
clicking around for a minute, well past Strava's 100-requests-per-15-minutes
limit. The fix was to sync with Strava in exactly one place — right after
OAuth authorization — and have every other page read from the local
SQLite database instead. Pages that don't touch activity data (like the
Pace Planner) shouldn't call Strava at all, and now don't.

**The same database column held two different types.**
`start_date` was stored as a real `datetime` for newer rows, but as a plain
string for rows written before the save logic changed — and several routes
(`all_time_runs`, `Running Progress`, the Daily Activity header) each
assumed only one of the two. I wrote a small `_as_datetime()` normalizer
that accepts either and used it everywhere the column gets read, instead
of patching each call site with its own guess at the format.

**A chart could render blank with zero errors, and there was no way to
tell why from inside the app.** The heart-rate comparison chart used
`matplotlib` → `mpld3`, which converts a plot into HTML that loads `d3.js`
and its own JS bundle from a CDN at render time. If that CDN request was
slow, blocked, or the page was viewed offline, the chart div was just...
empty. No exception, no log line — it *looked* like the data was missing.
Rewriting the four data charts as plain inline SVG (numbers in, an SVG
string out, no network call, no external script) removed the entire
failure class. I proved it by loading the page with the browser's network
fully disabled and confirming every chart still rendered.

**Writing tests for two "obviously correct" functions found two real
bugs.** `calculate_vo2_max` divides by the recorded distance with no
zero-check — a manually logged activity with 0m distance crashes the
whole page. `take_the_seconds` parses an `H:MM:SS` string but only reads
the minutes and seconds, silently dropping the hour — a pace slower than
60 min/km comes back wrong with no error at all. Both are caught by
tests marked `xfail` in the suite, so they fail loudly and specifically
if anyone "fixes" them without updating the test, rather than passing
silently.

## What I'd do next

- Cache the daily-activity charts per run instead of regenerating them on
  every view (the map is already cached this way — the charts aren't yet)
- Move the Strava sync out of the request cycle entirely and into a
  scheduled background job, so a page load never waits on an external API
- Swap SQLite for Postgres before any real multi-user load

---

## License

MIT — see `LICENSE`.
