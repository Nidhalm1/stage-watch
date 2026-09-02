# Stage Watch

Nightly sweep for tech internships / PFE in France, read straight from each
company's ATS API. No web search, no scraping, no guessed URLs: every link in
the board came back in a live API response.

## How it runs

| When (Paris) | What |
|---|---|
| 17:45 | GitHub Action runs `make_board.py`, commits `board.html` |
| 18:00 | Claude cloud routine clones this repo and publishes `board.html` as the Stage Watch artifact, which sends the notification email |

The sweep runs here rather than in the Claude sandbox because that sandbox's
egress proxy is default-deny and blocks both `boards-api.greenhouse.io` and
`criteo.wd3.myworkdayjobs.com` (WebFetch included). GitHub runners have full
internet, and `api.github.com` is on the sandbox allowlist, so the repo is the
bridge between the two.

## State

`board.html` is both the output and the state file. Its hidden
`<script type="application/json" id="state">` block records every posting
already seen and when it was first seen, so the next run can mark roles NEW and
detect ones that vanished (= filled or pulled). Git history is the audit trail.

## Adding a company

Never guess a slug — a wrong one fails silently as "0 jobs". Probe it first:

    python ats_scan.py --probe Qonto greenhouse:qonto lever:qonto

Then add a confirmed entry to `COMPANIES` in `make_board.py`. Supported:
`greenhouse`, `lever`, `workable`, `smartrecruiters`, `workday`.

Workday needs `tenant`, `wd` and `site` instead of `slug`, e.g.
`{"name": "Criteo", "ats": "workday", "tenant": "criteo", "wd": "wd3", "site": "Criteo_Career_Site"}`.

## Running it by hand

    python make_board.py --prev board.html --out board.html
