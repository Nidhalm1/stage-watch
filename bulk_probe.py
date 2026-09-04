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
import json, random, re, sys, time, urllib.parse, urllib.request, urllib.error
from concurrent.futures import ThreadPoolExecutor

UA = {"User-Agent": "Mozilla/5.0", "Accept": "application/json"}
FR = re.compile(r"\b(france|paris|lyon|nantes|lille|bordeaux|toulouse|grenoble|sophia|rennes|"
                r"m[ée]rignac|v[ée]lizy|issy|courbevoie|nanterre|montrouge|cesson|blagnac)\b", re.I)


def get(url, body=None, timeout=25, tries=4):
    req = urllib.request.Request(
        url, data=json.dumps(body).encode() if body else None,
        headers={**UA, **({"Content-Type": "application/json"} if body else {})})
    for attempt in range(tries):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            # 429 is "ask again later", not "this company has no jobs". Recording
            # it as a miss is how a reachable company gets written off.
            if e.code not in (429, 503) or attempt == tries - 1:
                raise
            time.sleep(2 ** attempt + random.random())


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
    out = []
    for i in get("https://%s.teamtailor.com/jobs.json" % s).get("items", []):
        raw = (i.get("_jobposting") or {}).get("jobLocation") or []
        if isinstance(raw, dict):
            raw = [raw]
        locs = []
        for L in raw:
            a = (L or {}).get("address") or {}
            locs.append(", ".join(x for x in [a.get("addressLocality"), a.get("addressCountry")] if x))
        out.append((i.get("title", ""), "; ".join(x for x in locs if x)))
    return out

WTTJ_SHAPES = ["https://api.welcometothejungle.com/api/v1/organizations/%s/jobs?page=1&per_page=30",
               "https://www.welcometothejungle.com/api/v1/organizations/%s/jobs?page=1&per_page=30",
               "https://api.welcometothejungle.com/api/v1/organizations/%s"]


def t_welcometothejungle(s):
    last = None
    for shape in WTTJ_SHAPES:
        try:
            d = get(shape % s, tries=2)
        except Exception as e:
            last = e
            continue
        jobs = d.get("jobs") or (d.get("organization") or {}).get("jobs") or []
        if jobs:
            return [(j.get("name", ""), ((j.get("offices") or [{}])[0] or {}).get("city", ""))
                    for j in jobs]
    if last:
        raise last
    return []

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


# --- non-slug sources -------------------------------------------------------
# Welcome to the Jungle drives its own site from a public Algolia index. The
# application id and search-only key below are the ones WTTJ ships in its own
# frontend JS, visible to any browser - this is the same request the public site
# makes, not the api.welcometothejungle.com path that 403s from a runner.
WTTJ_APP  = "CSEKHVMS53"
WTTJ_KEY  = "4bd8f6215d0cc52b26430765769e65a0"
WTTJ_URL  = "https://%s-dsn.algolia.net/1/indexes/*/queries" % WTTJ_APP.lower()
WTTJ_JOBS = "wk_cms_jobs_production"


def _algolia(index, params):
    body = json.dumps({"requests": [{"indexName": index, "params": params}]}).encode()
    req = urllib.request.Request(WTTJ_URL, data=body, headers={
        # JSON body despite the form content-type - Algolia's documented CORS quirk
        "content-type": "application/x-www-form-urlencoded",
        "x-algolia-application-id": WTTJ_APP,
        "x-algolia-api-key": WTTJ_KEY,
        "origin": "https://www.welcometothejungle.com",
        "User-Agent": UA["User-Agent"]})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)["results"][0]


def t_wttj_shape(query):
    """Discovery only: dump nbHits and the REAL field names of a hit. The field
    list for this index has not been smoke-tested, and guessing a schema is how a
    fetcher ends up silently returning nothing."""
    d = _algolia(WTTJ_JOBS, "hitsPerPage=3&page=0&query=%s" % urllib.parse.quote(query))
    hits = d.get("hits") or []
    print("      nbHits=%s  keys=%s" % (d.get("nbHits"), sorted(hits[0].keys()) if hits else "NO HITS"))
    for h in hits[:2]:
        print("      sample: %s" % json.dumps(h, ensure_ascii=False)[:700])
    return [(h.get("name", ""), str(h.get("office") or h.get("offices") or "")) for h in hits]


def t_wttj(slug):
    """One organisation's postings. Server-side filter first, client-side filter
    as a fallback, so an unfilterable attribute degrades instead of silently
    returning an empty board."""
    attempts = [
        "hitsPerPage=100&page=0&filters=" + urllib.parse.quote('organization.slug:"%s"' % slug),
        "hitsPerPage=100&page=0&facetFilters=" + urllib.parse.quote(json.dumps([["organization.slug:%s" % slug]])),
        "hitsPerPage=100&page=0&query=" + urllib.parse.quote(slug),
    ]
    for params in attempts:
        try:
            d = _algolia(WTTJ_JOBS, params)
        except Exception:
            continue
        hits = [h for h in (d.get("hits") or [])
                if (h.get("organization") or {}).get("slug") == slug]
        if hits:
            out = []
            for h in hits:
                off = h.get("office") or {}
                city = off.get("city", "") if isinstance(off, dict) else ""
                out.append(("%s [%s]" % (h.get("name", ""), h.get("contract_type", "")), city))
            return out
    return []


def t_wttj_filter(spec):
    """Settle the three things a fetcher cannot guess: does a server-side filter
    on organization.slug AND contract_type actually narrow, how many hits exist
    behind the 100-per-page cap, and how many of them are duplicates.

    Every one of those, guessed wrong, produces a company that looks empty or a
    board that reports the same role twice."""
    slug = spec
    f = 'organization.slug:"%s" AND contract_type:"INTERNSHIP"' % slug
    d = _algolia(WTTJ_JOBS, "hitsPerPage=100&page=0&filters=" + urllib.parse.quote(f))
    hits = d.get("hits") or []
    kinds = {}
    for h in hits:
        kinds[h.get("contract_type", "?")] = kinds.get(h.get("contract_type", "?"), 0) + 1
    orgs = {(h.get("organization") or {}).get("slug") for h in hits}
    slugs = [h.get("slug") for h in hits]
    uniq = len({s for s in slugs if s})
    print("      %-26s nbHits=%-5s nbPages=%-3s returned=%-3d unique-slug=%-3d contract=%s org=%s"
          % (slug, d.get("nbHits"), d.get("nbPages"), len(hits), uniq, kinds, sorted(o for o in orgs if o)))
    if hits:
        h = hits[0]
        print("      url parts: org=%s job-slug=%s  office=%s"
              % ((h.get("organization") or {}).get("slug"), h.get("slug"),
                 json.dumps(h.get("office"), ensure_ascii=False)[:120]))
    return [(h.get("name", ""), ((h.get("office") or {}) or {}).get("city", "")) for h in hits[:6]]


def t_wttj_head(slug):
    """The live sweep returned 0 roles for every WTTJ company while this probe
    returned 6. The only step the fetcher has that the probe does not is the
    HEAD verification of the constructed job URL, so measure exactly what that
    HEAD returns instead of reasoning about it."""
    f = 'organization.slug:"%s" AND contract_type:"INTERNSHIP"' % slug
    d = _algolia(WTTJ_JOBS, "hitsPerPage=3&page=0&filters=" + urllib.parse.quote(f))
    out = []
    for h in (d.get("hits") or [])[:3]:
        org, job = (h.get("organization") or {}).get("slug"), h.get("slug")
        url = "https://www.welcometothejungle.com/fr/companies/%s/jobs/%s" % (org, job)
        for method in ("HEAD", "GET"):
            req = urllib.request.Request(url, method=method,
                                         headers={"User-Agent": UA["User-Agent"]})
            try:
                with urllib.request.urlopen(req, timeout=20) as r:
                    verdict = "%s %s" % (method, r.status)
            except urllib.error.HTTPError as e:
                verdict = "%s HTTPError %s" % (method, e.code)
            except Exception as e:
                verdict = "%s %s" % (method, type(e).__name__)
            print("      %-6s %s" % (verdict, url[:96]))
            out.append((verdict, url[-40:]))
    return out


def t_wttj_org(slug):
    o = get("https://api.welcometothejungle.com/api/v1/organizations/%s" % slug)
    org = o.get("organization") or o
    return [("ORG RESOLVES: %s" % org.get("name", "?"), org.get("slug", ""))]


def t_rss(url):
    import xml.etree.ElementTree as ET
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30) as r:
        root = ET.fromstring(r.read())
    out = []
    for item in root.iter("item"):
        desc = re.sub(r"<[^>]+>", " ", item.findtext("description") or "")
        out.append(((item.findtext("title") or "").strip(),
                    "%s | %s" % (" ".join(desc.split())[:80], (item.findtext("link") or "")[-38:])))
    return out


JOB_HREF = re.compile(r'href="([^"]*/offre-emploi/[^"?#]+)"[^>]*>(?:\s*<[^>]*>)*\s*([^<]{3,120})', re.I)


def t_html(url):
    """A listing that genuinely ships its links in the HTML. Never point this at
    a JS-rendered page - it would report zero and look like an empty board."""
    req = urllib.request.Request(url, headers={"User-Agent": UA["User-Agent"],
                                               "Accept": "text/html"})
    with urllib.request.urlopen(req, timeout=30) as r:
        page = r.read().decode("utf-8", "replace")
    seen, out = set(), []
    for href, text in JOB_HREF.findall(page):
        if href not in seen:
            seen.add(href)
            out.append((" ".join(text.split()), href[-58:]))
    if not out:
        print("      no job links matched in %d bytes of HTML" % len(page))
    return out


# --- diagnostics ------------------------------------------------------------
# "403" is a symptom. Closing a source needs the request that was sent, the
# status, the body and the response headers that name the WAF. Everything below
# prints all four so a verdict can be checked instead of taken on trust.
BROWSER_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
                  " (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8",
    "Referer": "https://group.bnpparibas/emploi-carriere",
}
DIAG_HEADERS = ("server", "set-cookie", "cf-ray", "x-iinfo", "akamai-grn", "x-akamai-request-id",
                "x-akamai-transformed", "content-type", "x-cache", "via", "x-powered-by",
                "x-served-by", "x-request-id")


def _report(label, sent, status, body, headers):
    print("      ===== %s" % label)
    print("      REQUEST HEADERS SENT:")
    for k, v in sent.items():
        print("        %s: %s" % (k, v))
    print("      STATUS: %s" % status)
    seen = False
    for hk, hv in headers:
        if hk.lower() in DIAG_HEADERS:
            seen = True
            print("      RESP %-22s %s" % (hk + ":", str(hv)[:150]))
    if not seen:
        print("      RESP (none of the diagnostic headers present)")
    body = (body or "")[:500].replace("\n", " ").replace("\r", " ")
    print("      BODY[:500]: %s" % body)
    hit = "Nous avons" in (body or "")
    print("      contains 'Nous avons': %s" % hit)


def t_robots(url):
    """On the record before any automated fetching: what the site itself asks for."""
    from urllib.parse import urlsplit
    s = urlsplit(url)
    r_url = "%s://%s/robots.txt" % (s.scheme, s.netloc)
    req = urllib.request.Request(r_url, headers=BROWSER_HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=25) as r:
            txt = r.read().decode("utf-8", "replace")
        print("      robots.txt from %s (%d bytes):" % (r_url, len(txt)))
        for line in txt.splitlines()[:40]:
            print("        %s" % line[:120])
    except Exception as e:
        print("      robots.txt fetch failed: %s" % e)
    return [("robots.txt fetched", r_url)]


def t_bnp1(url):
    """Step 1: browser headers on a persistent session - cookie jar kept, referer
    page fetched first, then the target, exactly as a browser would arrive."""
    import http.cookiejar
    jar = http.cookiejar.CookieJar()
    op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
    for stage, target in (("warm-up (referer page)", BROWSER_HEADERS["Referer"]), ("target", url)):
        req = urllib.request.Request(target, headers=BROWSER_HEADERS)
        try:
            with op.open(req, timeout=30) as r:
                body = r.read().decode("utf-8", "replace")
                _report("step1 urllib+session %s" % stage, BROWSER_HEADERS, r.status, body,
                        r.headers.items())
        except urllib.error.HTTPError as e:
            _report("step1 urllib+session %s" % stage, BROWSER_HEADERS, e.code,
                    e.read().decode("utf-8", "replace"), e.headers.items())
        except Exception as e:
            print("      step1 %s: %s: %s" % (stage, type(e).__name__, e))
    print("      cookies held after session: %s" % [c.name for c in jar])
    return [("step1 done", "see diagnostics above")]


def t_bnp2(url):
    """Step 2: HTTP/2. urllib only speaks HTTP/1.1, and a WAF fingerprinting the
    protocol version alone would explain a 403 that a browser never sees."""
    try:
        import httpx
    except ImportError:
        print("      httpx not installed - step 2 not run")
        return []
    for h2 in (True, False):
        try:
            with httpx.Client(http2=h2, headers=BROWSER_HEADERS, timeout=30,
                              follow_redirects=True) as cl:
                r = cl.get(url)
                _report("step2 httpx http2=%s (negotiated %s)" % (h2, r.http_version),
                        dict(r.request.headers), r.status_code, r.text, list(r.headers.items()))
        except Exception as e:
            print("      step2 http2=%s: %s: %s" % (h2, type(e).__name__, e))
    return [("step2 done", "see diagnostics above")]


def t_bnp3(url):
    """Step 3: TLS fingerprint. curl_cffi impersonates Chrome's JA3, which is the
    last thing left if headers and HTTP/2 are not the discriminator."""
    try:
        from curl_cffi import requests as creq
    except ImportError:
        print("      curl_cffi not installed - step 3 not run")
        return []
    try:
        r = creq.get(url, impersonate="chrome", timeout=30)
        _report("step3 curl_cffi impersonate=chrome", BROWSER_HEADERS, r.status_code,
                r.text, list(r.headers.items()))
        if r.status_code == 200:
            links = set(re.findall(r'href="([^"]*/offre-emploi/[^"?#]+)"', r.text))
            print("      job links found: %d" % len(links))
            for l in sorted(links)[:5]:
                print("        %s" % l[:110])
    except Exception as e:
        print("      step3: %s: %s" % (type(e).__name__, e))
    return [("step3 done", "see diagnostics above")]


def t_sgtaleo(spec):
    """Societe Generale without the portal parameter. The portal id is a query
    param on the XHR the search page fires, not a string in the HTML, so the
    earlier regex over jobsearch.ftl could never have found it. Some Taleo
    tenants accept the call with no portal at all - one request settles it."""
    url = "https://socgen.taleo.net/careersection/rest/jobboard/searchjobs?lang=fr"
    if spec and spec != "noportal":
        url += "&portal=%s" % spec
    body = json.dumps({"multilineEnabled": False,
                       "sortingSelection": {"sortBySelectionParam": "1",
                                            "ascendingSortingOrder": "false"},
                       "fieldData": {"fields": {"KEYWORD": "", "LOCATION": "", "CATEGORY": ""},
                                     "valid": True},
                       "pageNo": 1}).encode()
    hdrs = {"Content-Type": "application/json", "X-Requested-With": "XMLHttpRequest",
            "Referer": "https://socgen.taleo.net/careersection/sgcareers/jobsearch.ftl",
            "User-Agent": BROWSER_HEADERS["User-Agent"]}
    req = urllib.request.Request(url, data=body, headers=hdrs)
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            d = json.loads(r.read().decode("utf-8", "replace"))
    except urllib.error.HTTPError as e:
        txt = e.read().decode("utf-8", "replace")
        print("      %s -> HTTP %s  body[:300]: %s" % (url, e.code, txt[:300].replace("\n", " ")))
        return []
    except Exception as e:
        print("      %s -> %s: %s" % (url, type(e).__name__, e))
        return []
    reqs = (d.get("requisitionList") or [])
    total = (d.get("pagingData") or {}).get("totalCount")
    print("      %s -> requisitionList=%d totalCount=%s" % (url, len(reqs), total))
    out = []
    for j in reqs[:6]:
        col = {c.get("columnName"): c.get("value") for c in (j.get("column") or [])
               if isinstance(c, dict)}
        out.append((col.get("jobtitle") or j.get("jobId") or "?", col.get("location") or ""))
    return out


def t_taleoportal(url):
    """Read Societe Generale's missing PORTAL_ID off the page that uses it,
    rather than leaving that source blocked on an unknown value."""
    req = urllib.request.Request(url, headers={"User-Agent": UA["User-Agent"],
                                               "Accept": "text/html"})
    with urllib.request.urlopen(req, timeout=30) as r:
        page = r.read().decode("utf-8", "replace")
    found = set()
    for pat in (r"[?&]portal=(\d{4,})", r"portalId[\"'=:\s]{1,4}(\d{4,})", r"portal[\"'=:\s]{1,4}(\d{6,})"):
        found.update(re.findall(pat, page, re.I))
    print("      page=%d bytes  PORTAL_ID candidates: %s" % (len(page), sorted(found) or "NONE"))
    return [("PORTAL_ID candidate %s" % f, "") for f in sorted(found)]


SLUG_TESTS = [("greenhouse", t_greenhouse), ("lever", t_lever), ("workable", t_workable),
              ("smartrecruiters", t_smartrecruiters), ("ashby", t_ashby),
              ("recruitee", t_recruitee), ("teamtailor", t_teamtailor)]
# t_welcometothejungle is deliberately NOT in that list. Probed 2026-09-04: it
# answers 403 to every request from a runner, including all three control
# companies, which are demonstrably on WTTJ. It blocks non-browser clients, so
# every "miss" it produces is meaningless and it only burns request budget.
# Re-enable only alongside something that can present as a browser.
TYPED = {"workday": t_workday, "eightfold": t_eightfold, "url": t_url,
         "wttjshape": t_wttj_shape, "wttj": t_wttj, "wttjorg": t_wttj_org,
         "wttjfilter": t_wttj_filter, "wttjhead": t_wttj_head,
         "robots": t_robots, "bnp1": t_bnp1, "bnp2": t_bnp2, "bnp3": t_bnp3,
         "sgtaleo": t_sgtaleo,
         "rss": t_rss, "html": t_html, "taleoportal": t_taleoportal}


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
    with ThreadPoolExecutor(max_workers=4) as ex:
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
    print("\nPer-tester tally. A tester with 0 hits and 404 on EVERY candidate is more"
          "\nlikely broken than proof that nobody uses it - check it before trusting a miss.")
    tally = {}
    for company, ats, spec, rows, err in results:
        t = tally.setdefault(ats, {"hits": 0, "404": 0, "other_err": 0, "empty200": 0})
        if err == "HTTP 404":
            t["404"] += 1
        elif err:
            t["other_err"] += 1
        elif rows:
            t["hits"] += 1
        else:
            t["empty200"] += 1
    for ats in sorted(tally):
        t = tally[ats]
        flag = "   <-- SUSPECT: never once answered" if not t["hits"] and not t["empty200"] else ""
        print("   %-16s hits=%-3d empty-200=%-3d 404=%-3d other-error=%-3d%s"
              % (ats, t["hits"], t["empty200"], t["404"], t["other_err"], flag))

    throttled = [(c, a, sp) for c, a, sp, rows, err in results if err and "429" in err]
    if throttled:
        print("\n!! %d probes ended in 429 even after backoff. These are NOT misses - nothing"
              "\n   was learned about them. Re-run before treating any as unreachable:" % len(throttled))
        for c, a, sp in throttled[:20]:
            print("     %-22s %-16s %s" % (c, a, sp))

    print("\nErrors, for the record:")
    for company, ats, spec, rows, err in results:
        if err and not err.startswith("HTTP 404"):
            print("   %-22s %-16s %-26s %s" % (company, ats, spec[:26], err))


if __name__ == "__main__":
    main(sys.argv[1])
