#!/usr/bin/env python3
"""ATS sweep: one API call per company, no per-posting verification.

  python ats_scan.py            scan + update ats-state.json + write report.md
  python ats_scan.py --dry      scan, print, do not write state
  python ats_scan.py --probe Foo greenhouse:foo lever:foo   test slugs for a new company
"""
import json, re, sys, time, os, urllib.request, urllib.error
from datetime import date

HERE  = os.path.dirname(os.path.abspath(__file__))
STATE = os.path.join(HERE, "ats-state.json")
UA    = {"User-Agent": "Mozilla/5.0", "Accept": "application/json"}
TODAY = date.today().isoformat()

LOC    = re.compile(r"\b(france|paris|lyon|nantes|lille|bordeaux|toulouse|grenoble|sophia|montpellier|nice|rennes|strasbourg)\b", re.I)
INTERN = re.compile(r"\b(stage|stagiaire|pfe|intern|internship)\b", re.I)
ALT    = re.compile(r"\b(alternance|alternant|apprenti|apprentissage|apprentice)\b", re.I)
TECH   = re.compile(r"(software|swe|engineer|engineering|developer|d[ée]veloppeur|backend|back-end|frontend|front-end|fullstack|full.stack|sre|site reliability|devops|platform|infra|infrastructure|cloud|kubernetes|data|\bml\b|machine learning|\bai\b|security|s[ée]curit[ée]|network|system)", re.I)


def get(url, body=None):
    req = urllib.request.Request(url, data=json.dumps(body).encode() if body else None,
                                 headers={**UA, **({"Content-Type": "application/json"} if body else {})})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


# --- one fetcher per ATS: returns [(title, location, url)] -------------------
def f_greenhouse(a):
    d = get(f"https://boards-api.greenhouse.io/v1/boards/{a['slug']}/jobs?content=false")
    return [(j.get("title", ""), (j.get("location") or {}).get("name", ""), j.get("absolute_url", "")) for j in d.get("jobs", [])]

def f_lever(a):
    d = get(f"https://api.lever.co/v0/postings/{a['slug']}?mode=json")
    return [(j.get("text", ""), (j.get("categories") or {}).get("location", "") or "", j.get("hostedUrl", "")) for j in d]

def f_workable(a):
    d = get(f"https://apply.workable.com/api/v1/widget/accounts/{a['slug']}")
    return [(j.get("title", ""), ", ".join(x for x in [j.get("city"), j.get("country")] if x), j.get("url", "")) for j in d.get("jobs", [])]

def f_smartrecruiters(a):
    out, off = [], 0
    while True:
        d = get(f"https://api.smartrecruiters.com/v1/companies/{a['slug']}/postings?limit=100&offset={off}")
        for j in d.get("content", []):
            lo = j.get("location") or {}
            out.append((j.get("name", ""), ", ".join(x for x in [lo.get("city"), lo.get("country")] if x),
                        f"https://jobs.smartrecruiters.com/{a['slug']}/{j.get('id','')}"))
        off += 100
        if off >= d.get("totalFound", 0): return out

def f_workday(a):
    host = f"https://{a['tenant']}.{a['wd']}.myworkdayjobs.com"
    api  = f"{host}/wday/cxs/{a['tenant']}/{a['site']}/jobs"
    pub  = f"{host}/en-US/{a['site']}"
    out, off, total = [], 0, None
    while True:
        d = get(api, {"appliedFacets": {}, "limit": 20, "offset": off, "searchText": ""})
        page = d.get("jobPostings", [])
        if total is None: total = d.get("total", 0)
        for j in page:
            # externalPath carries the city; bulletFields carries the country
            blob = f"{j.get('locationsText','')} {'; '.join(j.get('bulletFields') or [])} {j.get('externalPath','').replace('/',' ').replace('-',' ')}"
            city = j.get("externalPath", "").split("/job/")[-1].split("/")[0] if "/job/" in j.get("externalPath", "") else j.get("locationsText", "")
            show = ", ".join(x for x in [city, "; ".join(j.get("bulletFields") or [])] if x)
            out.append((j.get("title", ""), show, pub + j.get("externalPath", ""), blob.strip()))
        off += 20
        if not page or off >= total: return out
        time.sleep(0.3)

FETCH = {"greenhouse": f_greenhouse, "lever": f_lever, "workable": f_workable,
         "smartrecruiters": f_smartrecruiters, "workday": f_workday}


def match(jobs):
    jobs = [j if len(j) > 3 else (*j, j[1]) for j in jobs]   # j[3] = string to match on, j[1] = string to show
    fr  = [j for j in jobs if LOC.search(j[3])]
    itn = [j for j in fr if INTERN.search(j[0]) and not ALT.search(j[0])]
    return fr, [j for j in itn if TECH.search(j[0])], [j for j in itn if not TECH.search(j[0])]


def scan(dry=False):
    st = json.load(open(STATE, encoding="utf-8"))
    lines = [f"# ATS sweep - {TODAY}\n"]
    api_calls = 0
    for name, c in st["companies"].items():
        ats = c.get("ats")
        if not ats:
            lines.append(f"\n## {name}\n- no API (manual path)")
            continue
        try:
            jobs = FETCH[ats["type"]](ats); api_calls += 1
        except Exception as e:
            lines.append(f"\n## {name}\n- **FETCH FAILED** ({ats['type']}): {e}  <- re-run discovery")
            continue

        fr, hits, other = match(jobs)
        live = {j[2] for j in hits}
        prev = {p["url"]: p for p in c.get("postings", [])}
        dead = [p for u, p in prev.items() if u not in live]          # gone from API == filled
        new  = [h[2] for h in hits if h[2] not in prev]

        c["postings"] = [{"title": t, "location": l, "url": u,
                          "first_seen": prev.get(u, {}).get("first_seen", TODAY)} for t, l, u, _ in hits]
        c["verified"] = TODAY

        lines.append(f"\n## {name}  [{ats['type']}]\n"
                     f"- {len(jobs)} open roles / {len(fr)} in France / **{len(hits)} tech internships**")
        for t, l, u, _ in hits:
            tag = " **NEW**" if u in new else ""
            lines.append(f"- [{t}]({u}){tag}\n  - {l}")
        for t, l, *_ in other:
            lines.append(f"- _(non-tech intern, skipped)_ {t}")
        for p in dead:
            lines.append(f"- ~~{p['title']}~~ gone from board -> filled/closed")

    lines.append(f"\n---\n{api_calls} API calls total. 0 WebSearch, 0 per-posting WebFetch.")
    rpt = "\n".join(lines)
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    print(rpt)
    if not dry:
        json.dump(st, open(STATE, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
        open(os.path.join(HERE, "report.md"), "w", encoding="utf-8").write(rpt)


def probe(name, specs):
    """python ats_scan.py --probe Qonto greenhouse:qonto lever:qonto"""
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    for s in specs:
        typ, slug = s.split(":", 1)
        a = {"greenhouse": {"slug": slug}, "lever": {"slug": slug}, "workable": {"slug": slug},
             "smartrecruiters": {"slug": slug}}.get(typ)
        if typ == "workday":
            tenant, wd, site = slug.split(",")
            a = {"tenant": tenant, "wd": wd, "site": site}
        try:
            jobs = FETCH[typ](a)
            fr, hits, _ = match(jobs)
            verdict = "OK" if jobs else "EMPTY -> wrong slug"
            print(f"{verdict:20} {name} {typ}:{slug}  jobs={len(jobs)} france={len(fr)} hits={len(hits)}")
            for t, l, u, *_ in hits[:5]: print(f"      {t} | {l}\n      {u}")
        except Exception as e:
            print(f"{'FAIL':20} {name} {typ}:{slug}  {e}")


if __name__ == "__main__":
    if "--probe" in sys.argv:
        i = sys.argv.index("--probe"); probe(sys.argv[i + 1], sys.argv[i + 2:])
    else:
        scan(dry="--dry" in sys.argv)
