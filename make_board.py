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
    # Every slug below was confirmed against a live API response on 2026-09-02.
    # Never add one that has not been probed: a wrong slug fails silently as
    # "0 jobs", and a slug belonging to a DIFFERENT company of the same name is
    # worse still (workable/kestra is a US financial advisor, not Kestra.io).
    {"name": "Datadog",      "ats": "greenhouse", "slug": "datadog",
     "careers": "https://careers.datadoghq.com/"},
    {"name": "Doctolib",     "ats": "greenhouse", "slug": "doctolib",
     "careers": "https://careers.doctolib.com/"},
    {"name": "Criteo",       "ats": "workday", "tenant": "criteo", "wd": "wd3",
     "site": "Criteo_Career_Site", "careers": "https://careers.criteo.com/en/jobs/"},
    {"name": "Grafana Labs", "ats": "greenhouse", "slug": "grafanalabs",
     "careers": "https://grafana.com/about/careers/"},
    {"name": "Elastic",      "ats": "greenhouse", "slug": "elastic",
     "careers": "https://www.elastic.co/about/careers/"},
    {"name": "Sentry",       "ats": "ashby", "slug": "sentry",
     "careers": "https://sentry.io/careers/"},
    {"name": "Dataiku",      "ats": "greenhouse", "slug": "dataiku",
     "careers": "https://www.dataiku.com/careers/"},
    {"name": "Algolia",      "ats": "greenhouse", "slug": "algolia",
     "careers": "https://www.algolia.com/careers/"},
    {"name": "Meilisearch",  "ats": "lever", "slug": "meili",
     "careers": "https://www.meilisearch.com/careers"},
    {"name": "Kestra",       "ats": "ashby", "slug": "kestra",
     "careers": "https://kestra.io/careers"},
    {"name": "Sifflet",      "ats": "ashby", "slug": "sifflet",
     "careers": "https://www.siffletdata.com/careers"},
    {"name": "OpsMill",      "ats": "ashby", "slug": "opsmill",
     "careers": "https://opsmill.com/careers/"},
    {"name": "Scaleway",     "ats": "lever", "slug": "scaleway",
     "careers": "https://www.scaleway.com/en/careers/"},
    {"name": "Cloudflare",   "ats": "greenhouse", "slug": "cloudflare",
     "careers": "https://www.cloudflare.com/careers/"},
    {"name": "MongoDB",      "ats": "greenhouse", "slug": "mongodb",
     "careers": "https://www.mongodb.com/careers"},
    {"name": "GitLab",       "ats": "greenhouse", "slug": "gitlab",
     "careers": "https://about.gitlab.com/jobs/"},
    {"name": "Confluent",    "ats": "ashby", "slug": "confluent",
     "careers": "https://www.confluent.io/careers/"},
    {"name": "Snowflake",    "ats": "ashby", "slug": "snowflake",
     "careers": "https://careers.snowflake.com/"},
    {"name": "Databricks",   "ats": "greenhouse", "slug": "databricks",
     "careers": "https://www.databricks.com/company/careers"},
    {"name": "Red Hat",      "ats": "workday", "tenant": "redhat", "wd": "wd5",
     "site": "jobs", "careers": "https://www.redhat.com/en/jobs"},
]

# Probed on 2026-09-02 and confirmed to have NO supported public API. Listed so
# nobody wastes time re-probing them; check these by hand or via their own alerts.
NO_API = [
    ("Dynatrace",    "custom Coveo search endpoint, not a standard ATS"),
    ("OVHcloud",     "SAP SuccessFactors"),
    ("GitHub",       "iCIMS"),
    ("HashiCorp",    "acquired by IBM; careers now redirect to IBM Careers"),
    ("Clever Cloud", "no careers site found; /careers/ redirects to a product page"),
    ("Tsuga",        "no job board found"),
]


# --- Batch 2: French tech / fintech / scale-ups -----------------------------
# Confirmed against live API responses on 2026-09-02. Doctolib is intentionally
# absent - it lives in COMPANIES (batch 1) and must not be tracked twice.
COMPANIES2 = [
    {"name": "Qonto",            "ats": "lever", "slug": "qonto",
     "careers": "https://qonto.com/en/careers"},
    {"name": "Contentsquare",    "ats": "lever", "slug": "contentsquare",
     "careers": "https://contentsquare.com/careers/"},
    {"name": "BlaBlaCar",        "ats": "lever", "slug": "blablacar",
     "careers": "https://blog.blablacar.com/careers"},
    {"name": "Swile",            "ats": "lever", "slug": "swile",
     "careers": "https://www.swile.co/en-gb/careers"},
    {"name": "Aircall",          "ats": "lever", "slug": "aircall",
     "careers": "https://aircall.io/careers/"},
    {"name": "Younited",         "ats": "lever", "slug": "younited",
     "careers": "https://www.younited-credit.com/carrieres"},
    {"name": "Back Market",      "ats": "ashby", "slug": "backmarket",
     "careers": "https://jobs.backmarket.com/"},
    {"name": "Alan",             "ats": "ashby", "slug": "alan",
     "careers": "https://alan.com/careers"},
    {"name": "Pennylane",        "ats": "ashby", "slug": "pennylane",
     "careers": "https://www.pennylane.com/careers/"},
    {"name": "Ledger",           "ats": "ashby", "slug": "ledger",
     "careers": "https://www.ledger.com/careers"},
    {"name": "Sorare",           "ats": "ashby", "slug": "sorare",
     "careers": "https://sorare.com/careers"},
    {"name": "Mirakl",           "ats": "greenhouse", "slug": "mirakl",
     "careers": "https://www.mirakl.com/careers"},
    # ashby/shift is a DIFFERENT company (an Australian lender). Do not "fix" this slug.
    {"name": "Shift Technology", "ats": "greenhouse", "slug": "shifttechnology",
     "careers": "https://www.shift-technology.com/careers"},
    {"name": "Dailymotion",      "ats": "smartrecruiters", "slug": "dailymotion",
     "careers": "https://careers.dailymotion.com/"},
    {"name": "Hugging Face",     "ats": "workable", "slug": "huggingface",
     "careers": "https://apply.workable.com/huggingface/"},
    {"name": "Payfit",           "ats": "teamtailor", "slug": "payfit",
     "careers": "https://payfit.com/careers/"},
    {"name": "Amadeus",          "ats": "workday", "tenant": "amadeus", "wd": "wd502",
     "site": "jobs", "careers": "https://careers.amadeus.com/"},
    {"name": "Murex",            "ats": "workday", "tenant": "murex", "wd": "wd3",
     "site": "MurexCareerPage1", "careers": "https://careers.murex.com/"},
]

NO_API2 = [
    ("Deezer",     "careers URL redirects to their investor site; no job board found"),
    ("Mistral AI", "Ashby UI only - the posting API 404s for every slug variant"),
    ("Kayrros",    "careers page returns 404"),
    ("INRIA",      "custom public-research portal (jobs.inria.fr)"),
    ("CEA",        "custom public-research portal"),
    ("CNRS",       "custom public-research portal (emploi.cnrs.fr)"),
]

# Selected by --roster; render() reads BOARD for the page name and blurb.
# --- Batch 3: defence / aerospace / trading ---------------------------------
# Thales and Airbus are flagged "big": 6000+ postings each, so they are fetched
# as a union of the intern/trainee facet plus keyword searches instead of being
# paged whole. See f_workday.
COMPANIES3 = [
    {"name": "Thales",      "ats": "workday", "tenant": "thales", "wd": "wd3",
     "site": "Careers", "big": True, "careers": "https://www.thalesgroup.com/en/career"},
    {"name": "Airbus",      "ats": "workday", "tenant": "ag", "wd": "wd3",
     "site": "Airbus", "big": True, "careers": "https://www.airbus.com/en/careers"},
    {"name": "Dassault Systemes", "ats": "dassault", "slug": "3ds",
     "careers": "https://www.3ds.com/careers/jobs"},
    # Jane Street and IMC have working boards but no French office, so they will
    # normally show 0. Kept because a Paris desk would appear here immediately.
    {"name": "Jane Street", "ats": "greenhouse", "slug": "janestreet",
     "careers": "https://www.janestreet.com/join-jane-street/"},
    {"name": "IMC",         "ats": "greenhouse", "slug": "imc",
     "careers": "https://careers.imc.com/"},
]

NO_API3 = [
    ("Capgemini",          "Phenom People"),
    ("Atos / Eviden",      "no job board found; listing paths 404"),
    ("Safran",             "only workable/safrangroup exists = Safran Engineering Services UK Ltd, a UK subsidiary"),
    ("Hudson River Trading","greenhouse/hrttalentcommunity is a talent-community stub (3 generic entries), not the real board; no French office"),
    ("Optiver",            "bespoke careers system, no ATS"),
    ("Millennium",         "Eightfold"),
    ("BNP Paribas",        "careers site returns 403 to non-browser clients"),
    ("Societe Generale",   "Oracle Taleo"),
    ("Credit Agricole",    "Oracle Taleo"),
    ("Groupe BPCE",        "no public job API found"),
    ("Natixis",            "no public job API found"),
    ("Banque Populaire",   "regional BPCE portals, no public API"),
    ("Caisse d'Epargne",   "regional BPCE portals, no public API"),
    ("Credit Mutuel",      "no public job API found"),
    ("CIC",                "lever/cic is Cambridge Innovation Center, NOT the French bank"),
    ("Credit Mutuel Arkea","no public job API found"),
    ("La Banque Postale",  "no public job API found"),
    ("LCL",                "no public job API found"),
    ("HSBC / CCF",         "no public job API found"),
    ("Bpifrance",          "no public job API found"),
]

ROSTERS = {
    "1": {"name": "Stage Watch", "companies": COMPANIES,
          "blurb": "Tech internships and PFE in France at observability, infrastructure and "
                   "developer-tools companies, read straight from each company&rsquo;s "
                   "applicant-tracking API."},
    "3": {"name": "Defence & Finance Watch", "companies": COMPANIES3,
          "blurb": "Tech internships and PFE in France at defence, aerospace and trading "
                   "firms, read straight from each company&rsquo;s applicant-tracking API."},
    "2": {"name": "French Tech Watch", "companies": COMPANIES2,
          "blurb": "Tech internships and PFE in France at French tech, fintech and scale-up "
                   "companies, read straight from each company&rsquo;s applicant-tracking API."},
}

BOARD = ROSTERS["1"]

LOC    = re.compile(r"\b(france|paris|lyon|nantes|lille|bordeaux|toulouse|grenoble|sophia|montpellier|nice|rennes|strasbourg|marseille|aix-en-provence|cannes|toulon|marignane|blagnac|colomiers|saint-nazaire|brest|angers|le mans|tours|orl[ée]ans|dijon|metz|nancy|reims|rouen|caen|limoges|clermont-ferrand|saint-[ée]tienne|valence|avignon|pau|tarbes|la rochelle|poitiers|amiens|dunkerque|versailles|v[ée]lizy|[ée]lancourt|massy|palaiseau|saclay|courbevoie|nanterre|boulogne|issy|meudon|montrouge|levallois|neuilly|cergy|[ée]vry|cr[ée]teil|roissy|gennevilliers|saint-denis|marne-la-vall[ée]e|guyancourt|trappes|carquefou|villeurbanne|annecy|chamb[ée]ry|besan[çc]on|mulhouse|colmar|belfort|montbeliard|vitrolles|rungis|suresnes|colombes|vannes|lorient|quimper|laval|cholet|niort|bayonne|perpignan|b[ée]ziers)\b", re.I)
INTERN = re.compile(r"\b(stage|stagiaire|pfe|intern|internship)\b", re.I)
ALT    = re.compile(r"\b(alternance|alternant|apprenti|apprentissage|apprentice)\b", re.I)
TECH   = re.compile(r"(software|swe|engineer|engineering|developer|d[\u00e9e]veloppeur|backend|back-end|frontend|front-end|fullstack|full.stack|sre|site reliability|devops|platform|infra|infrastructure|cloud|kubernetes|data|\bml\b|machine learning|\bai\b|security|s[\u00e9e]curit[\u00e9e]|network|system)", re.I)
# A title can match TECH incidentally - 'Legal Intern - Product & AI' hits ai.
# These business-function words veto a tech match.
EXCL   = re.compile(r"\b(legal|juridique|marketing|sales|vente|commercial|business development|talent|recruit|people|hr|rh|brand|communication|content|community|finance|accounting|comptab|audit|payroll|paie|office manager|customer success|account executive|partnership)\b", re.I)

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


INTERN_SUBTYPE = re.compile(r"intern|trainee|student|stage|stagiaire", re.I)
APPRENTICE_SUBTYPE = re.compile(r"apprentice|apprenti|alternan", re.I)


def _workday_intern_facets(api):
    """workerSubType ids meaning intern/trainee, discovered live.

    Returns [] when the tenant exposes no such facet, in which case the caller
    pages the whole board rather than silently fetching nothing.
    """
    d = get(api, {"appliedFacets": {}, "limit": 1, "offset": 0, "searchText": ""})
    ids = []
    for fp in d.get("facets", []) or []:
        if fp.get("facetParameter") != "workerSubType":
            continue
        for v in fp.get("values") or []:
            desc = v.get("descriptor") or ""
            if INTERN_SUBTYPE.search(desc) and not APPRENTICE_SUBTYPE.search(desc):
                if v.get("id"):
                    ids.append(v["id"])
    return ids


WORKDAY_MAX = 1200          # ceiling; Thales and Airbus are ~2-3k each


def f_workday(c):
    host = "https://%s.%s.myworkdayjobs.com" % (c["tenant"], c["wd"])
    api  = "%s/wday/cxs/%s/%s/jobs" % (host, c["tenant"], c["site"])
    pub  = "%s/en-US/%s" % (host, c["site"])
    # Boards flagged "big" (Thales, Airbus: 6000+ postings) are never paged whole.
    # Instead: the intern/trainee facet UNION a few keyword searches. The facet
    # alone is not enough - Airbus files some French stages under other contract
    # types - and the keywords alone miss English-titled trainee roles.
    if c.get("big"):
        queries = []
        ids = _workday_intern_facets(api)
        if ids:
            queries.append(({"workerSubType": ids}, ""))
        # "intern" is deliberately absent: Workday's search is fuzzy and it matches
        # essentially the whole Thales board, which is useless as a narrowing term.
        for kw in ("stagiaire", "stage", "internship", "apprenti"):
            queries.append(({}, kw))
        seen, merged = set(), []
        for facets_q, text in queries:
            for row in _workday_page(api, pub, facets_q, text):
                if row[2] not in seen:
                    seen.add(row[2])
                    merged.append(row)
        return merged
    return _workday_page(api, pub, {}, "")


def _workday_page(api, pub, facets, text):
    out, off = [], 0
    # Workday's "total" is capped at 2000 and keeps reporting 2000 while further
    # offsets still return results, so it cannot be used as the stop condition.
    # Page until a short page comes back.
    while True:
        d = get(api, {"appliedFacets": facets, "limit": 20, "offset": off, "searchText": text})
        page = d.get("jobPostings", [])
        for j in page:
            path = j.get("externalPath", "")
            blob = "%s %s %s" % (j.get("locationsText", ""),
                                 "; ".join(j.get("bulletFields") or []),
                                 path.replace("/", " ").replace("-", " "))
            city = path.split("/job/")[-1].split("/")[0] if "/job/" in path else j.get("locationsText", "")
            show = ", ".join(x for x in [city, "; ".join(j.get("bulletFields") or [])] if x)
            out.append((j.get("title", ""), show, pub + path, blob))
        off += 20
        # A keyword that turns out to be too fuzzy just stops at the ceiling
        # rather than failing the whole company; the other queries still run.
        if len(page) < 20 or off >= WORKDAY_MAX:
            return out
        time.sleep(0.15)


def f_ashby(c):
    d = get("https://api.ashbyhq.com/posting-api/job-board/%s" % c["slug"])
    out = []
    for j in d.get("jobs", []):
        if j.get("isListed") is False:
            continue
        sec = []
        for s in (j.get("secondaryLocations") or []):
            sec.append(s.get("location", "") if isinstance(s, dict) else str(s))
        loc = j.get("location", "") or ""
        blob = " ".join([x for x in [loc] + sec if x])
        # jobUrl comes back verbatim from the API - never construct it
        out.append((j.get("title", ""), blob or loc, j.get("jobUrl", ""), blob))
    return out


def f_teamtailor(c):
    # Teamtailor career sites expose a JSON Feed at <slug>.teamtailor.com/jobs.json.
    # There is no page parameter that works (page=2 returns nothing), so the feed is
    # all published jobs; if a company ever exceeds the feed size this would silently
    # under-report, so keep an eye on the count.
    d = get("https://%s.teamtailor.com/jobs.json" % c["slug"])
    out = []
    for it in d.get("items", []):
        jp = it.get("_jobposting") or {}
        raw = jp.get("jobLocation") or []
        if isinstance(raw, dict):
            raw = [raw]
        locs = []
        for L in raw:
            a = (L or {}).get("address") or {}
            locs.append(", ".join(x for x in [a.get("addressLocality"), a.get("addressCountry")] if x))
        loc = "; ".join([x for x in locs if x])
        # url comes back verbatim from the feed - never construct it
        out.append((it.get("title", ""), loc, it.get("url", ""), loc))
    return out


def f_dassault(c):
    # 3ds.com exposes a public JSON search over its career cards. Underlying ATS
    # is Taleo (see content_cta_2_url), but this layer is clean and paginated:
    # b = offset, hf = hits per fetch, nhits = true total.
    base = ("https://www.3ds.com/apisearch/card_search_api?q=%23all%20card_content_lang%3Aen"
            "%20%20%20(card_content_type%3D%22career%22)%20&s=desc(card_content_start_datetime)")
    out, off = [], 0
    while True:
        d = get("%s&b=%d&hf=100&output_format=json" % (base, off))
        hits = d.get("hits", []) or []
        for h in hits:
            m = {}
            for meta in h.get("metas", []) or []:
                if isinstance(meta, dict):
                    k, v = meta.get("name"), meta.get("value")
                    if k and k not in m:
                        m[k] = v
            title = m.get("content_title", "")
            loc = m.get("content_info_2_value", "") or ""
            # content_cta_1_url is the real posting URL, returned verbatim
            url = m.get("content_cta_1_url", "") or ""
            if title and url:
                out.append((title, loc, url, loc))
        off += 100
        if not hits or off >= int(d.get("nhits") or 0) or off >= 2000:
            return out


FETCH = {"greenhouse": f_greenhouse, "lever": f_lever, "workable": f_workable,
         "smartrecruiters": f_smartrecruiters, "workday": f_workday,
         "ashby": f_ashby, "teamtailor": f_teamtailor,
         "dassault": f_dassault}

ENDPOINT = {
    "greenhouse":      lambda c: "boards-api.greenhouse.io/v1/boards/%s/jobs" % c["slug"],
    "lever":           lambda c: "api.lever.co/v0/postings/%s" % c["slug"],
    "workable":        lambda c: "apply.workable.com/api/v1/widget/accounts/%s" % c["slug"],
    "smartrecruiters": lambda c: "api.smartrecruiters.com/v1/companies/%s/postings" % c["slug"],
    "workday":         lambda c: "%s.%s.myworkdayjobs.com/wday/cxs/%s/%s/jobs" % (c["tenant"], c["wd"], c["tenant"], c["site"]),
    "ashby":           lambda c: "api.ashbyhq.com/posting-api/job-board/%s" % c["slug"],
    "teamtailor":      lambda c: "%s.teamtailor.com/jobs.json" % c["slug"],
    "dassault":        lambda c: "www.3ds.com/apisearch/card_search_api (career cards)",
}


def scan():
    results = []
    for c in BOARD["companies"]:
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
        row["hits"]   = [{"title": t, "location": l, "url": u} for t, l, u, _ in itn if TECH.search(t) and not EXCL.search(t)]
        row["other"]  = [{"title": t, "location": l, "url": u} for t, l, u, _ in itn if not (TECH.search(t) and not EXCL.search(t))]
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
<title>__BOARD_NAME__</title>
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

    p = [CSS.replace("__BOARD_NAME__", esc(BOARD["name"])), '<div class="wrap">']

    p.append('<header class="head">')
    p.append('<p class="eyebrow">Daily ATS sweep &middot; Europe/Paris</p>')
    p.append("<h1>%s</h1>" % esc(BOARD["name"]))
    p.append('<p class="tagline">%s Every link below came back in a live API '
             "response &mdash; none were searched for or guessed.</p>" % BOARD["blurb"])
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
    if "--roster" in sys.argv:
        BOARD = ROSTERS[sys.argv[sys.argv.index("--roster") + 1]]
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
