#!/usr/bin/env python3
"""Probe candidate ATS slugs for many companies at once.

Never trust a status code alone: SmartRecruiters returns 200 with an empty
content[] for ANY bogus slug, and Workable can return a stale legacy account.
A candidate only counts as confirmed if the response actually carries jobs.
"""
import json, sys, urllib.request, urllib.error
from concurrent.futures import ThreadPoolExecutor

UA = {"User-Agent": "Mozilla/5.0", "Accept": "application/json"}


def get(url, timeout=20):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)


def t_greenhouse(slug):
    d = get("https://boards-api.greenhouse.io/v1/boards/%s/jobs?content=false" % slug)
    return len(d.get("jobs", []))


def t_lever(slug):
    d = get("https://api.lever.co/v0/postings/%s?mode=json" % slug)
    return len(d) if isinstance(d, list) else 0


def t_workable(slug):
    d = get("https://apply.workable.com/api/v1/widget/accounts/%s" % slug)
    return len(d.get("jobs", []))


def t_smartrecruiters(slug):
    d = get("https://api.smartrecruiters.com/v1/companies/%s/postings?limit=1" % slug)
    return int(d.get("totalFound", 0))          # 200 + 0 means WRONG slug


def t_ashby(slug):
    d = get("https://api.ashbyhq.com/posting-api/job-board/%s" % slug)
    return len(d.get("jobs", []))


def t_recruitee(slug):
    d = get("https://%s.recruitee.com/api/offers/" % slug)
    return len(d.get("offers", []))


TESTS = [("greenhouse", t_greenhouse), ("lever", t_lever), ("workable", t_workable),
         ("smartrecruiters", t_smartrecruiters), ("ashby", t_ashby), ("recruitee", t_recruitee)]


def probe(job):
    company, ats, fn, slug = job
    try:
        n = fn(slug)
        return (company, ats, slug, n, None)
    except urllib.error.HTTPError as e:
        return (company, ats, slug, 0, "HTTP %s" % e.code)
    except Exception as e:
        return (company, ats, slug, 0, type(e).__name__)


def main(path):
    cands = json.load(open(path, encoding="utf-8"))
    jobs = []
    for company, slugs in cands.items():
        for slug in slugs:
            for ats, fn in TESTS:
                jobs.append((company, ats, fn, slug))
    with ThreadPoolExecutor(max_workers=24) as ex:
        results = list(ex.map(probe, jobs))

    hits, misses = {}, []
    for company, ats, slug, n, err in results:
        if err is None and n > 0:
            hits.setdefault(company, []).append((ats, slug, n))

    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    for company in cands:
        if company in hits:
            for ats, slug, n in sorted(hits[company], key=lambda x: -x[2]):
                print("  CONFIRMED  %-16s %-16s %-22s %4d jobs" % (company, ats, slug, n))
        else:
            misses.append(company)
    print("\nNO PUBLIC API FOUND (need career-page inspection): %d" % len(misses))
    for m in misses:
        print("   -", m)


if __name__ == "__main__":
    main(sys.argv[1])
