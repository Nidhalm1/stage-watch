#!/usr/bin/env python3
"""Stage Watch - build the internship board from ATS APIs.

  python make_board.py                      -> board.html (fresh, no diff)
  python make_board.py --prev prev.html     -> board.html, diffed against the
                                               previous artifact for NEW/CLOSED

Self-contained on purpose: the nightly cloud run has no access to any other
file, so config + fetchers + template all live here.
"""
import json, re, sys, html, urllib.request, time
from datetime import datetime, timezone, timedelta

# ---------------------------------------------------------------- config ----
# Every slug below was confirmed against a live API response. Never add one
# that has not been probed - a wrong slug fails silently as "0 jobs".
COMPANIES = [
    {"name": "Datadog",  "ats": "greenhouse", "slug": "datadog",
     "careers": "https://careers.datadoghq.com/"},
    {"name": "Doctolib", "ats": "greenhouse", "slug": "doctolib",
     "careers": "https://careers.doctolib.com/"},
    {"name": "Criteo",   "ats": "workday", "tenant": "criteo", "wd": "wd3",
     "site": "Criteo_Career_Site", "careers": "https://careers.criteo.com/en/jobs/"},
]

LOC    = re.compile(r"\b(france|paris|lyon|nantes|lille|bordeaux|toulouse|grenoble|sophia|montpellier|nice|rennes|strasbourg)\b", re.I)
INTERN = re.compile(r"\b(stage|stagiaire|pfe|intern|internship)\b", re.I)
ALT    = re.compile(r"\b(alternance|alternant|apprenti|apprentissage|apprentice)\b", re.I)
TECH   = re.compile(r"(software|swe|engineer|engineering|developer|d[\u00e9e]veloppeur|backend|back-end|frontend|front-end|fullstack|full.stack|sre|site reliability|devops|platform|infra|infrastructure|cloud|kubernetes|data|\bml\b|machine learning|\bai\b|security|s[\u00e9e]curit[\u00e9e]|network|system)", re.I)

def _paris_now():
    """Paris wall clock. zoneinfo where tzdata exists (Linux cloud), else the
    EU rule by hand - Windows ships no tzdata and the naive UTC+1 fallback is
    an hour wrong all summer."""
    try:
        from zoneinfo import ZoneInfo
        return datetime.now(ZoneInfo("Europe/Paris"))
    except Exception:
        u = datetime.now(timezone.utc)
        mar = datetime(u.year, 3, 31, 1, tzinfo=timezone.utc)   # last Sun of March 01:00 UTC
        mar -= timedelta(days=(mar.weekday() + 1) % 7)
        oct_ = datetime(u.year, 10, 31, 1, tzinfo=timezone.utc)  # last Sun of October 01:00 UTC
        oct_ -= timedelta(days=(oct_.weekday() + 1) % 7)
        off = timedelta(hours=2) if mar <= u < oct_ else timedelta(hours=1)
        return u.astimezone(timezone(off))

NOW   = _paris_now()
TZLABEL = "CEST" if NOW.utcoffset().total_seconds() == 7200 else "CET"
TODAY = NOW.date().isoformat()
UA    = {"User-Agent": "Mozilla/5.0", "Accept": "application/json"}


def get(url, body=None):
    req = urllib.request.Request(
        url, data=json.dumps(body).encode() if body else None,
        headers={**UA, **({"Content-Type": "application/json"} if body else {})})
    with urllib.request.urlopen(req, timeout=40) as r:
        return json.load(r)


# ------------------------------------------------------------- fetchers ----
# each returns [(title, shown_location, url, text_to_match_location_against)]
def f_greenhouse(c):
    d = get("https://boards-api.greenhouse.io/v1/boards/%s/jobs?content=false" % c["slug"])
    out = []
    for j in d.get("jobs", []):
        loc = (j.get("location") or {}).get("name", "")
        out.append((j.get("title", ""), loc, j.get("absolute_url", ""), loc))
    return out


def f_lever(c):
    d = get("https://api.lever.co/v0/postings/%s?mode=json" % c["slug"])
    out = []
    for j in d:
        loc = (j.get("categories") or {}).get("location", "") or ""
        out.append((j.get("text", ""), loc, j.get("hostedUrl", ""), loc))
    return out


def f_workable(c):
    d = get("https://apply.workable.com/api/v1/widget/accounts/%s" % c["slug"])
    out = []
    for j in d.get("jobs", []):
        loc = ", ".join(x for x in [j.get("city"), j.get("country")] if x)
        out.append((j.get("title", ""), loc, j.get("url", ""), loc))
    return out


def f_smartrecruiters(c):
    out, off = [], 0
    while True:
        d = get("https://api.smartrecruiters.com/v1/companies/%s/postings?limit=100&offset=%d" % (c["slug"], off))
        for j in d.get("content", []):
            lo = j.get("location") or {}
            loc = ", ".join(x for x in [lo.get("city"), lo.get("country")] if x)
            out.append((j.get("name", ""), loc,
                        "https://jobs.smartrecruiters.com/%s/%s" % (c["slug"], j.get("id", "")), loc))
        off += 100
        if off >= d.get("totalFound", 0):
            return out


def f_workday(c):
    host = "https://%s.%s.myworkdayjobs.com" % (c["tenant"], c["wd"])
    api  = "%s/wday/cxs/%s/%s/jobs" % (host, c["tenant"], c["site"])
    pub  = "%s/en-US/%s" % (host, c["site"])
    out, off, total = [], 0, None
    while True:
        d = get(api, {"appliedFacets": {}, "limit": 20, "offset": off, "searchText": ""})
        page = d.get("jobPostings", [])
        if total is None:
            total = d.get("total", 0)
        for j in page:
            path = j.get("externalPath", "")
            blob = "%s %s %s" % (j.get("locationsText", ""),
                                 "; ".join(j.get("bulletFields") or []),
                                 path.replace("/", " ").replace("-", " "))
            city = path.split("/job/")[-1].split("/")[0] if "/job/" in path else j.get("locationsText", "")
            show = ", ".join(x for x in [city, "; ".join(j.get("bulletFields") or [])] if x)
            out.append((j.get("title", ""), show, pub + path, blob))
        off += 20
        if not page or off >= total:
            return out
        time.sleep(0.3)


FETCH = {"greenhouse": f_greenhouse, "lever": f_lever, "workable": f_workable,
         "smartrecruiters": f_smartrecruiters, "workday": f_workday}

ENDPOINT = {
    "greenhouse":      lambda c: "boards-api.greenhouse.io/v1/boards/%s/jobs" % c["slug"],
    "lever":           lambda c: "api.lever.co/v0/postings/%s" % c["slug"],
    "workable":        lambda c: "apply.workable.com/api/v1/widget/accounts/%s" % c["slug"],
    "smartrecruiters": lambda c: "api.smartrecruiters.com/v1/companies/%s/postings" % c["slug"],
    "workday":         lambda c: "%s.%s.myworkdayjobs.com/wday/cxs/%s/%s/jobs" % (c["tenant"], c["wd"], c["tenant"], c["site"]),
}


def scan():
    results = []
    for c in COMPANIES:
        row = {"name": c["name"], "ats": c["ats"], "careers": c.get("careers", ""),
               "endpoint": ENDPOINT[c["ats"]](c), "error": None,
               "total": 0, "france": 0, "hits": [], "other": []}
        try:
            jobs = FETCH[c["ats"]](c)
        except Exception as e:
            row["error"] = "%s: %s" % (type(e).__name__, e)
            results.append(row)
            continue
        fr  = [j for j in jobs if LOC.search(j[3])]
        itn = [j for j in fr if INTERN.search(j[0]) and not ALT.search(j[0])]
        row["total"]  = len(jobs)
        row["france"] = len(fr)
        row["hits"]   = [{"title": t, "location": l, "url": u} for t, l, u, _ in itn if TECH.search(t)]
        row["other"]  = [{"title": t, "location": l, "url": u} for t, l, u, _ in itn if not TECH.search(t)]
        results.append(row)
    return results


def load_prev(path):
    """Pull the state block out of the previously published artifact."""
    if not path:
        return {"postings": {}, "closed": []}
    try:
        raw = open(path, encoding="utf-8").read()
        m = re.search(r'<script type="application/json" id="state">(.*?)</script>', raw, re.S)
        return json.loads(m.group(1)) if m else {"postings": {}, "closed": []}
    except Exception:
        return {"postings": {}, "closed": []}


CSS = """
<title>Stage Watch</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Archivo:wght@500;600;700&family=Public+Sans:ital,wght@0,400;0,500;1,400&family=JetBrains+Mono:wght@400;500&display=swap">
<style>
:root{
  --bg:#F6F7F9; --surface:#FFFFFF; --sunk:#F0F2F5;
  --ink:#14181F; --muted:#5C6472; --line:#E2E6EC;
  --accent:#10695A; --accent-soft:#E4F0EC;
  --new:#9A5B00; --new-soft:#FBEEDB;
  --closed:#A03A30; --closed-soft:#F7E7E4;
  --shadow:0 1px 2px rgba(20,24,31,.05),0 8px 24px -16px rgba(20,24,31,.25);
}
@media (prefers-color-scheme:dark){
  :root:not([data-theme="light"]){
    --bg:#0E1117; --surface:#161A22; --sunk:#12161D;
    --ink:#E6EAF1; --muted:#939CAC; --line:#242A35;
    --accent:#43C9A7; --accent-soft:#12302A;
    --new:#D9A052; --new-soft:#31250F;
    --closed:#DE8074; --closed-soft:#331A17;
    --shadow:0 1px 2px rgba(0,0,0,.4),0 8px 24px -16px rgba(0,0,0,.8);
  }
}
:root[data-theme="dark"]{
  --bg:#0E1117; --surface:#161A22; --sunk:#12161D;
  --ink:#E6EAF1; --muted:#939CAC; --line:#242A35;
  --accent:#43C9A7; --accent-soft:#12302A;
  --new:#D9A052; --new-soft:#31250F;
  --closed:#DE8074; --closed-soft:#331A17;
  --shadow:0 1px 2px rgba(0,0,0,.4),0 8px 24px -16px rgba(0,0,0,.8);
}
*{box-sizing:border-box}
body{
  background:var(--bg); color:var(--ink);
  font-family:"Public Sans",-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;
  line-height:1.55; -webkit-font-smoothing:antialiased;
}
.wrap{max-width:60rem;margin:0 auto;padding:2.75rem 1.5rem 4rem;display:flex;flex-direction:column;gap:2rem}
a{color:inherit}
:focus-visible{outline:2px solid var(--accent);outline-offset:3px;border-radius:3px}

/* masthead */
.head{display:flex;flex-direction:column;gap:.5rem}
.eyebrow{
  font-family:"JetBrains Mono",ui-monospace,monospace;font-size:.7rem;letter-spacing:.14em;
  text-transform:uppercase;color:var(--accent);margin:0;
}
h1{
  font-family:Archivo,sans-serif;font-weight:700;font-size:clamp(1.9rem,5vw,2.6rem);
  letter-spacing:-.02em;margin:0;text-wrap:balance;
}
.tagline{margin:0;color:var(--muted);max-width:48ch}
.statusline{
  font-family:"JetBrains Mono",ui-monospace,monospace;font-size:.8rem;color:var(--muted);
  margin:.35rem 0 0;padding-top:.85rem;border-top:1px solid var(--line);
  display:flex;flex-wrap:wrap;gap:.35rem 1rem;font-variant-numeric:tabular-nums;
}
.statusline b{color:var(--ink);font-weight:500}
.statusline .live{color:var(--accent);font-weight:500}

/* company cards */
.cards{display:flex;flex-direction:column;gap:1rem}
.co{
  background:var(--surface);border:1px solid var(--line);border-radius:10px;
  box-shadow:var(--shadow);overflow:hidden;
}
.co-h{
  display:flex;align-items:baseline;flex-wrap:wrap;gap:.5rem .75rem;
  padding:1rem 1.25rem;border-bottom:1px solid var(--line);background:var(--sunk);
}
.co-h h2{font-family:Archivo,sans-serif;font-size:1.06rem;font-weight:600;margin:0;letter-spacing:-.01em}
.badge{
  font-family:"JetBrains Mono",ui-monospace,monospace;font-size:.66rem;letter-spacing:.06em;
  text-transform:uppercase;padding:.2rem .45rem;border-radius:4px;
  background:var(--accent-soft);color:var(--accent);
}
.counts{
  margin-left:auto;font-family:"JetBrains Mono",ui-monospace,monospace;font-size:.75rem;
  color:var(--muted);font-variant-numeric:tabular-nums;
}
.jobs{list-style:none;margin:0;padding:0;display:flex;flex-direction:column}
.job{padding:.95rem 1.25rem;border-bottom:1px solid var(--line);display:flex;flex-direction:column;gap:.3rem}
.job:last-child{border-bottom:0}
.job a{
  font-family:Archivo,sans-serif;font-weight:600;font-size:1rem;
  color:var(--ink);text-decoration:underline;text-decoration-color:var(--line);
  text-underline-offset:3px;transition:text-decoration-color .15s;
}
.job a:hover{text-decoration-color:var(--accent)}
.job .meta{
  display:flex;flex-wrap:wrap;align-items:center;gap:.5rem;
  font-family:"JetBrains Mono",ui-monospace,monospace;font-size:.74rem;color:var(--muted);
}
.chip{
  font-size:.63rem;letter-spacing:.08em;text-transform:uppercase;font-weight:500;
  padding:.15rem .4rem;border-radius:3px;
}
.chip.new{background:var(--new-soft);color:var(--new)}
.chip.gone{background:var(--closed-soft);color:var(--closed)}
.none{margin:0;padding:.95rem 1.25rem;color:var(--muted);font-size:.9rem}
.err{margin:0;padding:.95rem 1.25rem;color:var(--closed);font-size:.85rem;
     font-family:"JetBrains Mono",ui-monospace,monospace;background:var(--closed-soft)}
details{border-top:1px solid var(--line);background:var(--sunk)}
summary{
  cursor:pointer;padding:.6rem 1.25rem;font-size:.78rem;color:var(--muted);
  font-family:"JetBrains Mono",ui-monospace,monospace;
}
details ul{list-style:none;margin:0;padding:0 1.25rem .85rem;display:flex;flex-direction:column;gap:.3rem}
details li{font-size:.83rem;color:var(--muted)}
.gone-list .job a{color:var(--muted);text-decoration-line:line-through}

/* provenance */
.sources{border-top:1px solid var(--line);padding-top:1.5rem;display:flex;flex-direction:column;gap:.75rem}
.sources h2{font-family:Archivo,sans-serif;font-size:.9rem;font-weight:600;margin:0}
.sources p{margin:0;font-size:.83rem;color:var(--muted);max-width:64ch}
.sources p.warn{color:var(--closed)}
.tbl{overflow-x:auto}
table{border-collapse:collapse;width:100%;font-family:"JetBrains Mono",ui-monospace,monospace;font-size:.73rem}
th,td{text-align:left;padding:.45rem .7rem .45rem 0;border-bottom:1px solid var(--line);white-space:nowrap}
th{color:var(--muted);font-weight:500;letter-spacing:.05em;text-transform:uppercase;font-size:.65rem}
td{color:var(--muted)}
td.co-name{color:var(--ink)}
@media (prefers-reduced-motion:reduce){*{transition:none!important;animation:none!important}}
</style>
"""


def esc(s):
    return html.escape(str(s or ""))


def render(results, prev):
    prev_posts = prev.get("postings", {})
    cur = {}
    new_ct = 0
    for r in results:
        for h in r["hits"]:
            u = h["url"]
            h["first_seen"] = prev_posts.get(u, {}).get("first_seen", TODAY)
            h["is_new"] = (u not in prev_posts) and bool(prev_posts)
            if h["is_new"]:
                new_ct += 1
            cur[u] = {"title": h["title"], "company": r["name"],
                      "location": h["location"], "first_seen": h["first_seen"]}

    # a posting that was live last run and is absent now == filled or pulled.
    # keep it visible for 14 days so a missed day is not a silent deletion.
    closed = [c for c in prev.get("closed", [])
              if (NOW.date() - datetime.fromisoformat(c["closed_on"]).date()).days < 14]
    known = {c["url"] for c in closed}
    ok_names = {r["name"] for r in results if not r["error"]}
    for u, p in prev_posts.items():
        # never mark closed off the back of a failed fetch
        if u not in cur and u not in known and p.get("company") in ok_names:
            closed.append({**p, "url": u, "closed_on": TODAY})

    total  = sum(r["total"] for r in results)
    live   = sum(len(r["hits"]) for r in results)
    broken = [r for r in results if r["error"]]

    p = [CSS, '<div class="wrap">']

    p.append('<header class="head">')
    p.append('<p class="eyebrow">Daily ATS sweep &middot; Europe/Paris</p>')
    p.append("<h1>Stage Watch</h1>")
    p.append('<p class="tagline">Tech internships and PFE in France, read straight from each '
             "company&rsquo;s applicant-tracking API. Every link below came back in a live API "
             "response &mdash; none were searched for or guessed.</p>")
    p.append('<p class="statusline">')
    p.append('<span class="live"><b>%d</b> live match%s</span>' % (live, "" if live == 1 else "es"))
    p.append("<span><b>%d</b> new since last run</span>" % new_ct)
    p.append("<span><b>%d</b> roles scanned</span>" % total)
    p.append("<span><b>%d</b> compan%s</span>" % (len(results), "y" if len(results) == 1 else "ies"))
    p.append("<span>run %s %s</span>" % (esc(NOW.strftime("%a %d %b %Y, %H:%M")), TZLABEL))
    p.append("</p></header>")

    p.append('<div class="cards">')
    for r in results:
        p.append('<article class="co">')
        p.append('<header class="co-h"><h2>%s</h2><span class="badge">%s</span>'
                 % (esc(r["name"]), esc(r["ats"])))
        if not r["error"]:
            p.append('<span class="counts">%d open &middot; %d in France</span>' % (r["total"], r["france"]))
        p.append("</header>")

        if r["error"]:
            p.append('<p class="err">API fetch failed &mdash; %s. Slug may have changed; re-run discovery.</p>'
                     % esc(r["error"]))
        elif r["hits"]:
            p.append('<ul class="jobs">')
            for h in r["hits"]:
                chip = '<span class="chip new">New</span>' if h["is_new"] else ""
                p.append('<li class="job"><a href="%s" target="_blank" rel="noopener">%s</a>'
                         '<div class="meta"><span>%s</span>%s<span>seen since %s</span></div></li>'
                         % (esc(h["url"]), esc(h["title"]), esc(h["location"]), chip, esc(h["first_seen"])))
            p.append("</ul>")
        else:
            p.append('<p class="none">No tech internships open in France right now.</p>')

        if r["other"]:
            p.append("<details><summary>%d non-tech internship%s filtered out</summary><ul>"
                     % (len(r["other"]), "" if len(r["other"]) == 1 else "s"))
            for o in r["other"]:
                p.append("<li>%s &mdash; %s</li>" % (esc(o["title"]), esc(o["location"])))
            p.append("</ul></details>")
        p.append("</article>")

    if closed:
        p.append('<article class="co"><header class="co-h"><h2>Recently closed</h2>'
                 '<span class="counts">gone from the board &mdash; filled or pulled</span></header>'
                 '<ul class="jobs gone-list">')
        for c in sorted(closed, key=lambda x: x["closed_on"], reverse=True):
            p.append('<li class="job"><a href="%s" target="_blank" rel="noopener">%s</a>'
                     '<div class="meta"><span>%s</span><span class="chip gone">Closed %s</span></div></li>'
                     % (esc(c["url"]), esc(c["title"]), esc(c.get("company", "")), esc(c["closed_on"])))
        p.append("</ul></article>")
    p.append("</div>")

    p.append('<section class="sources"><h2>Where this came from</h2>')
    p.append("<p>One request per company, straight to the board API. A role is listed only if the API "
             "returned it in this run, so a posting that disappears has been filled or pulled &mdash; "
             "no link here needs re-checking by hand.</p>")
    p.append('<div class="tbl"><table><thead><tr><th>Company</th><th>ATS</th><th>Endpoint</th>'
             "<th>This run</th></tr></thead><tbody>")
    for r in results:
        st = "failed" if r["error"] else "%d roles" % r["total"]
        p.append('<tr><td class="co-name">%s</td><td>%s</td><td>%s</td><td>%s</td></tr>'
                 % (esc(r["name"]), esc(r["ats"]), esc(r["endpoint"]), esc(st)))
    p.append("</tbody></table></div>")
    p.append("<p>Filter: location in France &middot; title contains stage / stagiaire / PFE / intern "
             "&middot; excludes alternance and apprentissage &middot; engineering, data, infra, SRE or "
             "security role.</p>")
    if broken:
        p.append('<p class="warn">%d compan%s failed to fetch this run, so its roles may be stale. '
                 "Nothing was marked closed for it.</p>"
                 % (len(broken), "y" if len(broken) == 1 else "ies"))
    p.append("</section></div>")

    state = {"generated": NOW.isoformat(), "postings": cur, "closed": closed}
    p.append('<script type="application/json" id="state">%s</script>'
             % json.dumps(state, ensure_ascii=False).replace("</", "<\\/"))
    return "\n".join(p), live, new_ct


if __name__ == "__main__":
    prev_path = sys.argv[sys.argv.index("--prev") + 1] if "--prev" in sys.argv else None
    out = sys.argv[sys.argv.index("--out") + 1] if "--out" in sys.argv else "board.html"
    res = scan()
    # A board where every company errored is worse than no board: publishing it
    # wipes real postings out of the state block. Bail before writing anything.
    failed = [r for r in res if r["error"]]
    if failed and len(failed) == len(res):
        print("ALL %d companies failed to fetch - refusing to write a board" % len(res), file=sys.stderr)
        for r in failed:
            print("  %s: %s" % (r["name"], r["error"]), file=sys.stderr)
        sys.exit(2)
    doc, live, new = render(res, load_prev(prev_path))
    open(out, "w", encoding="utf-8").write(doc)
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    for r in res:
        print("%-12s %-16s %s" % (r["name"], r["ats"], r["error"] or
              "%3d open / %2d FR / %d hits" % (r["total"], r["france"], len(r["hits"]))))
    print("-> %s  (%d live, %d new)" % (out, live, new))
