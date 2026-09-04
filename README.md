# Stage Watch

Three independent nightly job watches sharing one codebase.

| Board | File | Roster | Artifact |
|---|---|---|---|
| Stage Watch | `board.html` | `COMPANIES` - 20 observability / infra / dev-tools | 92513aa1 |
| French Tech Watch | `board2.html` | `COMPANIES2` - 20 French tech / fintech / scale-ups | 277bfba8 |
| Defence & Finance Watch | `board3.html` | `COMPANIES3` - 9 defence / aerospace / trading / banks | 8f9b34a1 |

Each board has its own hidden state block, so NEW / closed detection is per-board.
They never share results. `make_board.py --roster 2` selects the second roster;
fetchers, filters and the renderer are shared, so a fix lands in both at once.
Doctolib sits in batch 1 only - listing it twice would report one role as new on
two boards.

Nightly sweep for tech internships / PFE in France, read straight from each
company's ATS API. No web search, no scraping, no guessed URLs: every link in
the board came back in a live API response.

## How it runs

| When (Paris) | What |
|---|---|
| 17:00 | GitHub Action runs `make_board.py` once per roster, commits the three boards and `status.json` |
| 18:00 | Claude cloud routine clones this repo, reads `status.json`, publishes each board to its own artifact, and pings only if something changed |

Each roster is its own Action step with `continue-on-error`, so one roster that
stops fetching cannot stop the other two from being built and committed. A final
step still fails the run so the breakage is visible in the Actions tab.

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

`status.json` is the same run summarised per board - counts, run stamp, the new
roles with titles and URLs, what closed today, which companies failed or came
back incomplete. The publish routine reads only this file, so it never has to
pull ~46 KB of HTML through the model to answer "did anything change?".

Three things are deliberately NOT treated as evidence that a role closed:

- a company whose fetch raised
- a company that answered with **zero** roles (several ATSs return HTTP 200 and
  an empty list for a dead slug, so the company looks healthy while being
  invisible)
- a company whose paging hit a ceiling (`WORKDAY_MAX`, the Dassault 2000 cap)

In all three cases the roles are shown but nothing is marked closed, because a
posting that is invisible is not the same as a posting that is gone. A role that
closed and came back is dropped from the closed list rather than being shown in
both.

## Filters

A role is kept when its title says stage / stagiaire / PFE / intern / internship /
fin d'etudes / cesure, its title does *not* say alternance or apprentissage, its
location is in France, and `is_tech(title)` is true.

**Only the first of those four can delete a role.** The other two put it in a
collapsed box on its company card instead:

| Box | What is in it |
|---|---|
| *N non-tech internships filtered out* | in France, title did not read as engineering |
| *N internships with an unrecognised location* | could not be placed as France **or** as anywhere else |

Both boxes are tracked in state and get a **New** chip, and a new entry is
reported to the publish routine in `also_new`, so a filter mistake costs a glance
rather than the job. The box opens itself when it has something new in it.

Workday builds its city from `externalPath`, which is ASCII-folded: the board
really contains `Vlizy-Villacoublay`, `Donauwrth`, `So-Paulo`. An accent class
like `[ée]` cannot match a *missing* letter, so every accented French town was
one URL slug away from being unmatchable - the accent is optional in
`_FR_CITIES` and `_FR_REGIONS` for exactly that reason. Do not "tidy" the `?`
away.

`where(location)` is what makes the second box possible. It answers `fr`,
`foreign` or `unknown` rather than yes/no: `fr` when the city/region list or a
structured country field says France, `foreign` only when the string positively
names somewhere else, and `unknown` otherwise. Only `foreign` is dropped, so an
unlisted French town ends up visible instead of deleted. Filtering by internship
*first* and location *second* is what keeps that box down to a couple of entries
a week instead of every oddly-labelled role on a global board.

`is_tech` is two-stage. `TECH` is deliberately wide - a false positive costs one
glance, a false negative costs an application. `EXCL` then vetoes the
business-function words that match TECH by accident ("Legal Intern - Product &
AI" hits `ai`). But a veto word is often just the *domain* of a real engineering
role - a data engineer on the finance team, a security audit, cloud pre-sales -
so a word in `STRONG` overrides the veto. Only unambiguous words belong in
`STRONG`: `reseau` would let "Marketing & Reseaux Sociaux" straight back in.

Location is the same trap in reverse: a city whitelist can only ever shrink the
result set, and a role in a town nobody listed is invisible with nothing to say
so. Three defences - the city list is long, it also carries regions and
departments (Workday often shows only those), and every fetcher that gets a
structured country field back normalises it through `_fr()` so a bare `FR` still
matches.

## Companies

Per roster: `COMPANIES` / `COMPANIES2` / `COMPANIES3` in `make_board.py` are the
ones with a working public API; `NO_API` / `NO_API2` / `NO_API3` list the ones
probed and rejected, with the reason for each, so nobody re-probes them.

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
`greenhouse`, `lever`, `workable`, `smartrecruiters`, `ashby`, `workday`,
`teamtailor`, `dassault`, `wttj`.

`wttj` is the odd one out: an aggregator rather than an ATS, and the only way
in to the French banks, whose own systems are vendor-locked or refuse a
datacenter IP. It reads the public Algolia index the Welcome to the Jungle site
drives itself from. Two things there are load-bearing and were confirmed by
probe, not assumed: the server-side `contract_type` filter really does narrow,
and the index returns each posting more than once, so the de-duplication is not
optional. Its job URLs are built from two API fields rather than returned whole,
so each one is HEAD-checked before it is recorded - and a URL that fails marks
the company partial rather than dropping the role.

Workday needs `tenant`, `wd` and `site` instead of `slug`, e.g.
`{"name": "Criteo", "ats": "workday", "tenant": "criteo", "wd": "wd3", "site": "Criteo_Career_Site"}`.

## Audit

Every sweep writes `audit.json` and, from it, `audit.md` - everything the filters
dropped, per board. Skim it weekly:

- anything under **unrecognised location** that is really in France belongs in
  `_FR_CITIES`
- anything under **not tech** that is really an engineering role belongs in
  `TECH`, or in `STRONG` if an `EXCL` veto word is what is blocking it

Roles outside France are counted rather than listed - that call is nearly always
right and the list would be hundreds long - but a sample is kept so a systematic
mistake (a French site being read as foreign) is still visible.

This is the feedback loop the word lists never had: they get corrected from
evidence instead of guessed at again.

## Running it by hand

    python make_board.py --prev board.html --out board.html
    python make_board.py --roster 2 --prev board2.html --out board2.html
    python make_board.py --roster 3 --prev board3.html --out board3.html

`ROUTINE.md` holds the prompt the 16:00 UTC publish routine runs, so it can be
kept in step with the `status.json` this code writes.

`ats_scan.py` is an earlier standalone sweeper kept for reference only. It reads
an `ats-state.json` that no longer exists in this repo, so it will not run as-is;
`make_board.py` is the one the Action calls.
