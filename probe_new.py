#!/usr/bin/env python3
"""Probe the 2026-09-06 batch of candidate job APIs and print their shape.

    python probe_new.py [name ...]        # blank = every source

Same reason this exists as probe_html.py and bulk_probe.py: the Claude sandbox's
egress proxy answers 403 to CONNECT for every ATS host, so a response body can
only be read from a runner. Run it from Actions, read the log, then write the
fetcher against what it printed. Nothing in make_board.py may be guessed.

Every request below is exactly the one that was reported working on 2026-09-06;
this prints what it answers with, so the field names a fetcher reads are copied
off a live payload rather than assumed.
"""
import gzip, json, re, sys, time, urllib.error, urllib.parse, urllib.request

UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
JSON_HDR = {"User-Agent": UA, "Accept": "application/json,text/plain,*/*"}
HTML_HDR = {"User-Agent": UA,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8"}

IBM_BODY = {
    "appId": "careers", "scopes": ["careers2"], "size": 5, "from": 0,
    "sort": [{"_score": "desc"}],
    "query": {"bool": {"must": [{"simple_query_string": {
        "query": "intern",
        "fields": ["keywords^1", "body^1", "url^2", "description^2", "title^3", "field_text_01"]}}]}},
}

PHENOM_WIDGET = {
    "lang": "en_us", "deviceType": "desktop", "country": "us",
    "pageName": "search-results", "ddoKey": "refineSearch", "sortBy": "",
    "subsearch": "", "from": 0, "jobs": True, "counts": True,
    "all_fields": ["category", "country", "state", "city", "type"], "size": 5,
    "clearAll": False, "jdsource": "facets", "isSliderEnable": False,
    "pageId": "page11", "siteType": "external", "keywords": "intern",
    "global": True, "selected_fields": {}, "locationData": {}}

GS_BODY = {
    "operationName": "GetRoles",
    "variables": {"searchQueryInput": {
        "page": {"pageSize": 5, "pageNumber": 0},
        "sort": {"sortStrategy": "RELEVANCE", "sortOrder": "DESC"},
        "filters": [], "experiences": ["EARLY_CAREER"], "searchTerm": ""}},
    "query": ("query GetRoles($searchQueryInput: RoleSearchQueryInput!){roleSearch"
              "(searchQueryInput:$searchQueryInput){totalCount items{roleId jobTitle "
              "division jobFunction locations{primary city country} externalSource{sourceId}}}}")}

# name -> (kind, url, extra). kind: json | form | html
#   json  GET when extra has no "body", POST of extra["body"] when it does
#   form  POST of extra["form"] as x-www-form-urlencoded
#   html  GET, dump cards matching extra["card"] (or every anchor when absent)
SOURCES = {
    # --- Elasticsearch / custom -------------------------------------------
    "ibm": ("json", "https://www-api.ibm.com/search/api/v2",
            {"body": IBM_BODY, "items": "hits.hits", "total": "hits.total.value"}),

    # --- Workday (already supported; probed only to confirm the site slugs) --
    "intel": ("json", "https://intel.wd1.myworkdayjobs.com/wday/cxs/intel/External/jobs",
              {"body": {"appliedFacets": {}, "limit": 5, "offset": 0, "searchText": "intern"},
               "items": "jobPostings", "total": "total"}),
    "broadcom": ("json", "https://broadcom.wd1.myworkdayjobs.com/wday/cxs/broadcom/External_Career/jobs",
                 {"body": {"appliedFacets": {}, "limit": 5, "offset": 0, "searchText": "intern"},
                  "items": "jobPostings", "total": "total"}),
    "nvidia": ("json", "https://nvidia.wd5.myworkdayjobs.com/wday/cxs/nvidia/NVIDIAExternalCareerSite/jobs",
               {"body": {"appliedFacets": {}, "limit": 5, "offset": 0, "searchText": "intern"},
                "items": "jobPostings", "total": "total"}),

    # --- Phenom People ------------------------------------------------------
    "amd": ("json", "https://careers.amd.com/api/jobs?keywords=intern&page=1&sortBy=relevance&descending=false&internal=false",
            {"items": "jobs", "total": "totalCount"}),
    "githubcareers": ("json", "https://www.github.careers/api/jobs?keywords=intern&page=1&sortBy=relevance&descending=false&internal=false",
                      {"items": "jobs", "total": "totalCount"}),
    # keywords=intern answered 200 with totalCount 0 on 2026-09-06, so the board
    # is either empty of interns or the keyword is not matched the way AMD's is.
    # Ask for the whole board - GitHub's is small - and count what comes back.
    "githubcareers2": ("json", "https://www.github.careers/api/jobs?page=1&sortBy=relevance&descending=false&internal=false",
                       {"items": "jobs", "total": "totalCount"}),
    "amd-page2": ("json", "https://careers.amd.com/api/jobs?keywords=intern&page=2&sortBy=relevance&descending=false&internal=false",
                  {"items": "jobs", "total": "totalCount"}),
    "hpe": ("json", "https://careers.hpe.com/widgets",
            {"body": PHENOM_WIDGET, "items": "refineSearch.data.jobs",
             "total": "refineSearch.totalHits"}),
    "cisco": ("json", "https://careers.cisco.com/widgets",
              {"body": dict(PHENOM_WIDGET, lang="en_global", country="global",
                            all_fields=["country", "state", "city", "category"]),
               "items": "refineSearch.data.jobs", "total": "refineSearch.totalHits"}),

    # --- Eightfold ----------------------------------------------------------
    "qualcomm": ("json", "https://careers.qualcomm.com/api/pcsx/search?domain=qualcomm.com&query=intern&location=France&start=0&num=5",
                 {"items": "data.positions", "total": "data.count"}),
    "microsoft": ("json", "https://apply.careers.microsoft.com/api/pcsx/search?domain=microsoft.com&query=intern&location=France&start=0&num=5",
                  {"items": "data.positions", "total": "data.count"}),
    "morganstanley": ("json", "https://morganstanley.eightfold.ai/api/pcsx/search?domain=morganstanley.com&query=intern&location=France&start=0&num=5",
                      {"items": "data.positions", "total": "data.count"}),
    "ericsson": ("json", "https://jobs.ericsson.com/api/pcsx/search?domain=ericsson.com&query=intern&location=France&start=0&num=5",
                 {"items": "data.positions", "total": "data.count"}),
    "millennium": ("json", "https://career.mlp.com/api/apply/v2/jobs?domain=mlp.com&start=0&num=5&query=intern",
                   {"items": "positions", "total": "count"}),

    # --- Oracle HCM Cloud (CX) ---------------------------------------------
    "dell": ("json", "https://enterpriseplatform.dell.com/hcmRestApi/resources/latest/recruitingCEJobRequisitions?onlyData=true&expand=requisitionList.secondaryLocations,flexFieldsFacet.values&finder=findReqs;siteNumber=CX_1,limit=5,offset=0,sortBy=POSTING_DATES_DESC,keyword=intern",
             {"items": "items.0.requisitionList", "total": "items.0.TotalJobsCount"}),
    "nokia": ("json", "https://fa-evmr-saasfaprod1.fa.ocs.oraclecloud.com/hcmRestApi/resources/latest/recruitingCEJobRequisitions?onlyData=true&expand=requisitionList.workLocation,requisitionList.secondaryLocations&finder=findReqs;siteNumber=CX_1,limit=5,offset=0,keyword=intern,sortBy=POSTING_DATES_DESC",
              {"items": "items.0.requisitionList", "total": "items.0.TotalJobsCount"}),
    "oracle": ("json", "https://eeho.fa.us2.oraclecloud.com/hcmRestApi/resources/latest/recruitingCEJobRequisitions?onlyData=true&finder=findReqs;siteNumber=CX_1,limit=5,offset=0,sortBy=POSTING_DATES_DESC,keyword=intern",
               {"items": "items.0.requisitionList", "total": "items.0.TotalJobsCount"}),
    "jpmorgan": ("json", "https://jpmc.fa.oraclecloud.com/hcmRestApi/resources/latest/recruitingCEJobRequisitions?onlyData=true&finder=findReqs;siteNumber=CX_1,limit=5,offset=0,sortBy=POSTING_DATES_DESC,keyword=intern",
                 {"items": "items.0.requisitionList", "total": "items.0.TotalJobsCount"}),

    # --- one-offs -----------------------------------------------------------
    "arm": ("json", "https://careers.arm.com/search-jobs/results?ActiveFacetID=0&CurrentPage=1&RecordsPerPage=15&Distance=50&RadiusUnitType=0&Keywords=intern&Location=&ShowRadius=False&IsPagination=False&CustomFacetName=&FacetTerm=&FacetType=0&SearchResultsModuleName=Search+Results&SearchFiltersModuleName=Search+Filters&SortCriteria=0&SortDirection=0&SearchType=5",
            {"raw": 4000}),
    "amazon": ("json", "https://www.amazon.jobs/en/search.json?base_query=intern&loc_query=France&result_limit=5",
               {"items": "jobs", "total": "hits"}),
    "goldman": ("json", "https://api-higher.gs.com/gateway/api/v1/graphql",
                {"body": GS_BODY, "items": "data.roleSearch.items",
                 "total": "data.roleSearch.totalCount"}),
    "hrt": ("form", "https://www.hudsonrivertrading.com/wp-admin/admin-ajax.php",
            {"form": "action=get_hrt_jobs_handler&data[search]=", "items": ""}),
    "dynatrace": ("json", "https://www.dynatrace.com/api/coveo/search/",
                  {"body": {"q": "intern", "numberOfResults": 5},
                   "items": "results", "total": "totalCount"}),
    "atlassian": ("json", "https://www.atlassian.com/endpoint/careers/listings", {"items": ""}),

    # --- HTML only ----------------------------------------------------------
    "sap": ("html", "https://jobs.sap.com/tile-search-results/?q=intern&locationsearch=France&startrow=0",
            {"card": r'<li[^>]*class="[^"]*job-tile[^"]*"', "want": 2}),
    "ovh": ("html", "https://careers.ovhcloud.com/search/?q=stage&locale=fr_FR&startrow=0",
            {"card": r'<tr[^>]*class="[^"]*(?:data-row|job)[^"]*"|<li[^>]*class="[^"]*job-tile[^"]*"', "want": 2}),
    "siemens": ("html", "https://jobs.siemens.com/en_US/externaljobs/SearchJobs/intern?listFilterMode=1",
                {"card": r'<article[^>]*class="[^"]*article--result[^"]*"', "want": 2}),
    "hsbc": ("html", "https://mycareer.hsbc.com/en_GB/external/SearchJobs/intern?listFilterMode=1&pipelineRecordsPerPage=10",
             {"card": r'<article[^>]*class="[^"]*article--result[^"]*"', "want": 2}),
    "clevercloud": ("html", "https://www.clever.cloud/jobs/", {"want": 0}),
    "siemens-fr": ("html", "https://jobs.siemens.com/en_US/externaljobs/SearchJobs/stage?listFilterMode=1",
                   {"card": r'<article[^>]*class="[^"]*article--result[^"]*"', "want": 2}),
    "ovh-page2": ("html", "https://careers.ovhcloud.com/search/?q=stage&locale=fr_FR&startrow=25",
                  {"card": r'<li[^>]*class="[^"]*job-tile[^"]*"', "want": 1}),
}


def dig(d, path):
    cur = d
    for part in (path.split(".") if path else []):
        if isinstance(cur, list):
            try:
                cur = cur[int(part)]
            except (ValueError, IndexError):
                return None
        elif isinstance(cur, dict):
            cur = cur.get(part)
        else:
            return None
    return cur


def fetch(url, headers, data=None):
    req = urllib.request.Request(url, data=data,
                                 headers={**headers, "Accept-Encoding": "gzip"})
    with urllib.request.urlopen(req, timeout=60) as r:
        raw = r.read()
        if "gzip" in (r.headers.get("Content-Encoding") or "").lower():
            raw = gzip.decompress(raw)
        return r.status, r.geturl(), raw.decode(r.headers.get_content_charset() or "utf-8", "replace")


def flat(obj, prefix="", out=None, depth=0):
    """Every scalar in an item as path -> value, values clipped hard.

    A verbatim dump of one job posting is 2-4 KB of description HTML, and the
    only thing a fetcher needs off it is which FIELD holds the title, the URL
    and the location. So print the shape, not the prose."""
    out = {} if out is None else out
    if depth > 3:
        return out
    if isinstance(obj, dict):
        for k, v in obj.items():
            flat(v, "%s.%s" % (prefix, k) if prefix else k, out, depth + 1)
    elif isinstance(obj, list):
        if not obj:
            out[prefix] = "[]"
        else:
            for i, v in enumerate(obj[:2]):
                flat(v, "%s[%d]" % (prefix, i), out, depth + 1)
            if len(obj) > 2:
                out[prefix + "[...]"] = "%d items" % len(obj)
    else:
        text = re.sub(r"\s+", " ", str(obj))
        out[prefix] = (text[:90] + "..") if len(text) > 90 else text
    return out


# Prose and machine-learned padding: a fetcher never reads these, and printing
# them pushed the fields it DOES read off the end of the runner log.
NOISE = re.compile(r"description|responsibilit|qualificat|body|content|excerpt|"
                   r"summary|ml_|tags\d|highlight|logo|benefit|salary|compensation",
                   re.I)


def show(obj, cap=None):
    for k, v in flat(obj).items():
        if NOISE.search(k):
            continue
        print("   %-44s %s" % (k[:44], v))


def probe(name):
    kind, url, extra = SOURCES[name]
    print("=" * 78)
    print("%-14s %s %s" % (name, kind.upper(), url[:150]))
    headers = dict(JSON_HDR)
    data = None
    if kind == "json" and "body" in extra:
        headers["Content-Type"] = "application/json"
        data = json.dumps(extra["body"]).encode()
    elif kind == "form":
        headers["Content-Type"] = "application/x-www-form-urlencoded"
        data = extra["form"].encode()
    elif kind == "html":
        headers = dict(HTML_HDR)
    try:
        status, final, body = fetch(url, headers, data)
    except urllib.error.HTTPError as e:
        snippet = e.read(300).decode("utf-8", "replace").replace("\n", " ")
        print("  HTTP %s %s  %s" % (e.code, e.reason, snippet[:250]))
        return
    except Exception as e:
        print("  %s: %s" % (type(e).__name__, e))
        return
    print("  status %s  %d bytes%s" % (status, len(body),
                                       "  -> %s" % final[:120] if final != url else ""))

    if kind == "html":
        card = extra.get("card")
        want = extra.get("want", 2)
        hrefs, seen = [], set()
        for h in re.findall(r'<a\b[^>]*href="([^"]+)"', body, re.I):
            if h not in seen and re.search(r"job|offre|career|emploi", h, re.I):
                seen.add(h)
                hrefs.append(h)
        print("  %d job-ish anchors (first 25):" % len(hrefs))
        for h in hrefs[:12]:
            print("     %s" % h[:150])
        # Where does this page keep the LOCATION? Every one of these boards
        # renders it in some labelled element; print the labelled elements
        # rather than guessing which one it is.
        loc_hits = []
        for m in re.finditer(r'<[a-z]+[^>]*class="([^"]*(?:location|city|country|facility|region)[^"]*)"[^>]*>(.{0,110}?)<',
                             body, re.I | re.S):
            hit = "%s -> %s" % (m.group(1)[:50], re.sub(r"\s+", " ", m.group(2)).strip()[:70])
            if hit not in loc_hits:
                loc_hits.append(hit)
        print("  %d location-ish elements (first 12):" % len(loc_hits))
        for h in loc_hits[:12]:
            print("     %s" % h)
        if card:
            starts = [m.start() for m in re.finditer(card, body, re.I)]
            print("  %d cards matching %s" % (len(starts), card))
            for i, st in enumerate(starts[:want]):
                end = starts[i + 1] if i + 1 < len(starts) else min(len(body), st + 3000)
                print("  --- card %d verbatim ---" % (i + 1))
                print(body[st:end][:2500])
        return

    if "raw" in extra:
        print("  --- first %d chars verbatim ---" % extra["raw"])
        print(body[:extra["raw"]])
        return

    try:
        d = json.loads(body)
    except Exception as e:
        print("  not JSON (%s); first 400 chars:" % e)
        print(body[:400])
        return
    if isinstance(d, dict):
        print("  top-level keys: %s" % list(d)[:20])
    items = d if extra.get("items") == "" else dig(d, extra["items"])
    total = dig(d, extra["total"]) if extra.get("total") else None
    print("  items at %r: %s   total at %r: %s"
          % (extra.get("items"), len(items) if isinstance(items, list) else type(items).__name__,
             extra.get("total"), total))
    if isinstance(items, list) and items:
        if isinstance(items[0], dict):
            print("  item keys: %s" % sorted(items[0])[:60])
        print("  --- item 1 flattened ---")
        show(items[0])
        if len(items) > 1:
            print("  --- item 2: fields that DIFFER from item 1 ---")
            a, b = flat(items[0]), flat(items[1])
            for k, v in b.items():
                if a.get(k) != v and not NOISE.search(k):
                    print("   %-44s %s" % (k[:44], v))


if __name__ == "__main__":
    names = sys.argv[1:] or list(SOURCES)
    for n in names:
        if n not in SOURCES:
            print("unknown source %r; known: %s" % (n, " ".join(SOURCES)))
            continue
        probe(n)
        time.sleep(1)
