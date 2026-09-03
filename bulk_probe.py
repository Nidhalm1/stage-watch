#!/usr/bin/env python3
"""Probe candidate ATS endpoints for many companies at once.

    python bulk_probe.py cands.json

cands.json is {"Company": ["slug1", "slug2", ...], ...}. Every slug is tried
against every ATS that takes a plain slug. Entries of the form "type:spec" probe
one specific system instead - "workday:tenant,wd,site", "eightfold:domain.com",
"url:https://..." for a one-off endpoint.

Never trust a status code alone. SmartRecruiters returns 200 with an empty
content[] for ANY bogus slug, Workable can return a stale legacy account, and a
slug can belong to a DIFFERENT company of the same name - workable/kestra is a US
financial advisory firm, not Kestra.io. So a candidate only counts as confirmed
if the response carries jobs, and sample titles are printed for every hit so the
company can be identified before the slug is trusted.
"""
import json, re, sys, urllib.request, urllib.error
from concurrent.futures import ThreadPoolExecutor

UA = {"User-Agent": "Mozilla/5.0", "Accept": "application/json"}
FR = re.compile(r"\b(france|paris|lyon|nantes|lille|bordeaux|toulouse|grenoble|sophia|rennes|"
                r"m[ée]rignac|v[ée]lizy|issy|courbevoie|nanterre|montrouge|cesson|blagnac)\b", re.I)


def get(url, body=None, timeout=25):
    req = urllib.request.Request(
        url, data=json.dumps(body).encode() if body else None,
        headers={**UA, **({"Content-Type": "application/json"} if body else {})})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)


# each tester returns [(title, location)] -----------------------------------
def t_greenhouse(s):
    return [(j.get("title", ""), (j.get("location") or {}).get("name", ""))
            for j in get("https://boards-api.greenhouse.io/v1/boards/%s/jobs?content=false" % s).get("jobs", [])]

def t_lever(s):
    d = get("https://api.lever.co/v0/postings/%s?mode=json" % s)
    return [(j.get("text", ""), (j.get("categories") or {}).get("location", "")) for j in (d if isinstance(d, list) else [])]

def t_workable(s):
    return [(j.get("title", ""), ", ".join(x for x in [j.get("city"), j.get("country")] if x))
            for j in get("https://apply.workable.com/api/v1/widget/accounts/%s" % s).get("jobs", [])]

def t_smartrecruiters(s):
    d = get("https://api.smartrecruiters.com/v1/companies/%s/postings?limit=20" % s)
    if not d.get("totalFound"):            # 200 + 0 means WRONG slug
        return []
    return [(j.get("name", ""), ((j.get("location") or {}).get("city") or "")) for j in d.get("content", [])]

def t_ashby(s):
    return [(j.get("title", ""), j.get("location", "")) for j in
            get("https://api.ashbyhq.com/posting-api/job-board/%s" % s).get("jobs", [])]

def t_recruitee(s):
    return [(j.get("title", ""), j.get("location", "")) for j in
            get("https://%s.recruitee.com/api/offers/" % s).get("offers", [])]

def t_teamtailor(s):
    return [(i.get("title", ""), "") for i in get("https://%s.teamtailor.com/jobs.json" % s).get("items", [])]

def t_welcometothejungle(s):
    d = get("https://api.welcometothejungle.com/api/v1/organizations/%s/jobs?page=1&per_page=30" % s)
    return [(j.get("name", ""), ((j.get("offices") or [{}])[0] or {}).get("city", "")) for j in d.get("jobs", [])]

def t_eightfold(domain):
    d = get("https://api.eightfold.ai/api/apply/v2/jobs?domain=%s&start=0&num=30&sort_by=relevance" % domain)
    return [(p.get("name", ""), "; ".join(p.get("locations") or [])) for p in d.get("positions", [])]

def t_workday(spec):
    tenant, wd, site = spec.split(",")
    host = "https://%s.%s.myworkdayjobs.com" % (tenant, wd)
    d = get("%s/wday/cxs/%s/%s/jobs" % (host, tenant, site),
            {"appliedFacets": {}, "limit": 20, "offset": 0, "searchText": ""})
    return [(j.get("title", ""), j.get("locationsText", "")) for j in d.get("jobPostings", [])]

def t_url(u):
    """One-off endpoint. Walks the JSON for the first list of dicts that looks
    like postings, so an unfamiliar shape still reports something usable."""
    d = get(u)
    best = []
    stack = [d]
    while stack:
        x = stack.pop()
        if isinstance(x, dict):
            stack.extend(x.values())
        elif isinstance(x, list) and x and isinstance(x[0], dict):
            keys = set(x[0])
            if keys & {"title", "name", "text", "jobTitle", "intitule", "libelle"}:
                if len(x) > len(best):
                    best = x
            stack.extend(x)
    out = []
    for j in best:
        t = next((j[k] for k in ("title", "name", "text", "jobTitle", "intitule", "libelle")
                  if isinstance(j.get(k), str)), "")
        loc = next((j[k] for k in ("location", "city", "lieu", "ville") if isinstance(j.get(k), str)), "")
        out.append((t, loc))
    return out


SLUG_TESTS = [("greenhouse", t_greenhouse), ("lever", t_lever), ("workable", t_workable),
              ("smartrecruiters", t_smartrecruiters), ("ashby", t_ashby),
              ("recruitee", t_recruitee), ("teamtailor", t_teamtailor),
              ("wttj", t_welcometothejungle)]
TYPED = {"workday": t_workday, "eightfold": t_eightfold, "url": t_url}


def probe(job):
    company, ats, fn, spec = job
    try:
        rows = fn(spec)
        return (company, ats, spec, rows, None)
    except urllib.error.HTTPError as e:
        return (company, ats, spec, [], "HTTP %s" % e.code)
    except Exception as e:
        return (company, ats, spec, [], "%s: %s" % (type(e).__name__, str(e)[:60]))


def main(path):
    cands = json.load(open(path, encoding="utf-8"))
    jobs = []
    for company, specs in cands.items():
        for spec in specs:
            typ = spec.split(":", 1)[0] if ":" in spec else None
            if typ in TYPED:
                jobs.append((company, typ, TYPED[typ], spec.split(":", 1)[1]))
            else:
                for ats, fn in SLUG_TESTS:
                    jobs.append((company, ats, fn, spec))
    with ThreadPoolExecutor(max_workers=16) as ex:
        results = list(ex.map(probe, jobs))

    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    hits = {}
    for company, ats, spec, rows, err in results:
        if not err and rows:
            hits.setdefault(company, []).append((ats, spec, rows))

    print("=" * 78)
    for company in cands:
        if company not in hits:
            continue
        for ats, spec, rows in sorted(hits[company], key=lambda x: -len(x[2])):
            fr = [r for r in rows if FR.search(r[1] or "")]
            print("\nCONFIRMED  %s  ->  %s : %s" % (company, ats, spec))
            print("           %d jobs in the response, %d of them look French" % (len(rows), len(fr)))
            print("           CHECK THESE TITLES ARE THE RIGHT COMPANY:")
            for t, l in rows[:6]:
                print("             - %s   [%s]" % (t[:70], (l or "")[:40]))
            for t, l in fr[:4]:
                print("             FR: %s   [%s]" % (t[:70], (l or "")[:40]))
    print("\n" + "=" * 78)
    print("NOTHING FOUND (need a browser pass): %s"
          % ", ".join(c for c in cands if c not in hits))
    print("\nErrors, for the record:")
    for company, ats, spec, rows, err in results:
        if err and not err.startswith("HTTP 404"):
            print("   %-22s %-16s %-26s %s" % (company, ats, spec[:26], err))


if __name__ == "__main__":
    main(sys.argv[1])
