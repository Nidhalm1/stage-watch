# Stage Watch

Nightly sweep for tech internships / PFE in France, read straight from each
company's ATS API. No web search, no scraping, no guessed URLs: every link in
the board came back in a live API response.

## How it runs

| When (Paris) | What |
|---|---|
| 17:00 | GitHub Action runs `make_board.py`, commits `board.html` |
| 18:00 | Claude cloud routine clones this repo and publishes `board.html` as the Stage Watch artifact, and pings only if something changed |

The hour of slack is deliberate - GitHub delays scheduled runs under load, and a
late sweep would mean the routine publishes the previous day's board.

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

## Companies

20 with a working public API (see `COMPANIES` in `make_board.py`), 6 without
(see `NO_API` in the same file, with the reason for each).

## Adding a company

Never guess a slug. Two ways it bites:

1. A wrong slug fails **silently** as "0 jobs" — the company looks healthy and
   watched while actually being invisible.
2. A slug can belong to a **different company of the same name**.
   `workable/kestra` returns 36 real, live jobs — for "Kestra Financial
   Independent Advisor", a US financial advisory firm, not Kestra.io. Always
   confirm the job titles look like the right company before trusting a hit.

Probe candidates in bulk, then check the winner's titles:

    python bulk_probe.py cands.json     # {"Company": ["slug1","slug2"], ...}

A hit only counts if the response actually carries jobs. In particular
SmartRecruiters returns HTTP 200 with an empty `content[]` for ANY bogus slug,
so `totalFound > 0` is the real test.

Then add a confirmed entry to `COMPANIES` in `make_board.py`. Supported:
`greenhouse`, `lever`, `workable`, `smartrecruiters`, `ashby`, `workday`.

Workday needs `tenant`, `wd` and `site` instead of `slug`, e.g.
`{"name": "Criteo", "ats": "workday", "tenant": "criteo", "wd": "wd3", "site": "Criteo_Career_Site"}`.

## Running it by hand

    python make_board.py --prev board.html --out board.html
