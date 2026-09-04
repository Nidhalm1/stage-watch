#!/usr/bin/env python3
"""Probe the HTML job boards that have no JSON API, and print their shape.

    python probe_html.py [name ...]

The Claude sandbox's egress proxy answers 403 to CONNECT for every one of these
hosts, so this cannot be run there - it exists to be run from Actions, where the
runner has real internet, exactly like bulk_probe.py. Read the log, then write
the fetcher against what it printed. Nothing here is guessed.

Round 1 established the link patterns. What each source needs now is the CARD:
the block of markup around one offer, which is where the location and contract
live. So each source names the container it wraps an offer in, and this prints
whole containers verbatim.
"""
import re, sys, gzip, urllib.error, urllib.parse, urllib.request

UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36",
      "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
      "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8"}

# name -> (url, container-open regex, how many cards to dump)
SOURCES = {
    "amundi":      ("https://jobs.amundi.com/offre-de-emploi/liste-toutes-offres.aspx?page=1&LCID=1036",
                    r'<li[^>]*class="[^"]*ts-offer-list-item[^"]*"', 2),
    "amundi2":     ("https://jobs.amundi.com/offre-de-emploi/liste-toutes-offres.aspx?page=2&LCID=1036",
                    r'<li[^>]*class="[^"]*ts-offer-list-item[^"]*"', 1),
    "dassault-av": ("https://dassault-aviation-cand.talent-soft.com/offre-de-emploi/liste-offres.aspx?page=1",
                    r'<li[^>]*class="[^"]*ts-offer-list-item[^"]*"', 2),
    "expleo":      ("https://expleo-jobs-fr-fr.icims.com/jobs/search?pr=0&in_iframe=1",
                    r'<li[^>]*class="[^"]*iCIMS_JobCardItem[^"]*"', 2),
    "expleo2":     ("https://expleo-jobs-fr-fr.icims.com/jobs/search?pr=1&in_iframe=1",
                    r'<li[^>]*class="[^"]*iCIMS_JobCardItem[^"]*"', 1),
    # Round 1: the gestmax page loads but none of the offer-link shapes matched
    # and it carries only 33 anchors. Dump every anchor to find out what it does
    # link to before writing anything.
    "mbda":        ("https://mbda.gestmax.fr/search/index/page/1", None, 0),
    # 472 offers parse but 0 place as France, so the location cell is not where
    # the link-to-link text picks it up. Dump the whole row around a link.
    "mbda-row":    ("https://mbda.gestmax.fr/search/index/page/1", "CONTEXT", 2),
    "mbda2":       ("https://mbda.gestmax.fr/search/index/page/2", None, 0),
    # BNP. The public board is group.bnpparibas/en/careers/all-job-offers, which
    # answers 200 to a plain server-side fetch with no cookies and a non-browser
    # UA - Akamai Bot Manager is on the domain but is not gating this path. The
    # 403 that put BNP on WTTJ was a different host (the applicant portal). So
    # no cookie warming and no sensor replay; a later 403 would be rate limiting,
    # and the answer to that is a sleep between pages.
    "bnp":         ("https://group.bnpparibas/en/careers/all-job-offers", "FORM", 2),
    # The facet VALUES, not just the control names: paging all 380 pages daily to
    # find 362 internships is the wrong trade when the board can be asked.
    "bnp-facets":  ("https://group.bnpparibas/en/careers/all-job-offers", "FACETS", 0),
    "bnp-p2":      ("https://group.bnpparibas/en/careers/all-job-offers?page=1", "FORM", 1),
}


# The BNP ladder settled this: rungs 1-4 (no headers, plain UA, browser UA,
# browser UA + Accept */*) all got 403 Access Denied from the runner, and the
# FULL browser header set got 200 and the real listing. So it is a header check,
# not an IP block - and every probe sends the full set from here on.
BROWSER = dict(UA, **{
    "Referer": "https://group.bnpparibas/en/careers",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document", "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "same-origin", "Sec-Fetch-User": "?1",
    "Connection": "keep-alive"})


def fetch(url):
    req = urllib.request.Request(url, headers={**BROWSER, "Accept-Encoding": "gzip"})
    with urllib.request.urlopen(req, timeout=60) as r:
        raw = r.read()
        if "gzip" in (r.headers.get("Content-Encoding") or "").lower():
            raw = gzip.decompress(raw)
        return r.status, r.geturl(), raw.decode(r.headers.get_content_charset() or "utf-8", "replace")


def probe(name):
    url, container, want = SOURCES[name]
    print("=" * 78)
    print("%-12s %s" % (name, url))
    try:
        status, final, page = fetch(url)
    except urllib.error.HTTPError as e:
        print("  HTTPError %s %s" % (e.code, e.reason))
        return
    except Exception as e:
        print("  %s: %s" % (type(e).__name__, e))
        return
    print("  status %s  %d bytes%s" % (status, len(page),
                                       "  -> %s" % final if final != url else ""))
    for m in re.finditer(r"(\d[\d\s ]{0,6})\s*(offres?|r[ée]sultats?|postes?)", page, re.I):
        print("  count-hint: %r" % m.group(0).strip()[:60])
        break

    if container == "CONTEXT":
        hits = list(re.finditer(r'<a\b[^>]*href="https?://[a-z0-9.-]*gestmax\.fr/\d+/\d+/[^"]*"',
                                page, re.I))
        print("  %d offer links; dumping context around the first %d" % (len(hits), want))
        for m in hits[:want]:
            print("  --- 1800 chars before / 900 after ---")
            print(page[max(0, m.start() - 1800):m.end() + 900])
        return

    if container == "FACETS":
        for m in re.finditer(r'<input\b[^>]*name="(form\[(?:type|schedule|domain|experience|study_level|international)\]\[?\]?)"[^>]*>',
                             page, re.I):
            tag = m.group(0)
            val = re.search(r'value="([^"]*)"', tag)
            idd = re.search(r'\bid="([^"]*)"', tag)
            label = ""
            if idd:
                lm = re.search(r'<label[^>]*for="%s"[^>]*>(.*?)</label>' % re.escape(idd.group(1)),
                               page, re.I | re.S)
                if lm:
                    label = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", lm.group(1))).strip()
            print("  %-26s value=%-10s label=%s"
                  % (m.group(1), val.group(1) if val else "?", label[:60]))
        for pat in (r"[\d\s ]{1,9}\s*job offers", r'data-count="[^"]*"'):
            for hit in sorted(set(re.findall(pat, page, re.I)))[:6]:
                print("  count: %r" % hit.strip())
        # every distinct offer-type actually rendered, so the labels can be mapped
        types = sorted(set(re.findall(r'<div class="offer-type"\s*>([^<]*)</div>', page, re.I)))
        print("  offer-type values on page 1: %s" % [t.strip() for t in types])
        return

    if container == "FORM":
        # What are the filters actually called? Print the controls, every class
        # that mentions an offer, and the paging links, then two whole cards.
        for pat, label in ((r'<(?:select|input)\b[^>]*\bname="([^"]+)"[^>]*>', "control name"),
                           (r'class="([^"]*offer[^"]*)"', "offer-ish class"),
                           (r'href="([^"]*(?:page|Page)=[^"]*)"', "paging href"),
                           (r'<option\b[^>]*value="([^"]*)"[^>]*>([^<]{0,60})', "option")):
            hits = []
            for h in re.findall(pat, page, re.I):
                h = h if isinstance(h, str) else " = ".join(x.strip() for x in h)
                if h not in hits:
                    hits.append(h)
            print("  %s -> %d unique" % (label, len(hits)))
            for h in hits[:60]:
                print("     %s" % h[:160])
        # the card container is whichever offer-ish class repeats most
        classes = {}
        for cl in re.findall(r'class="([^"]*offer[^"]*)"', page, re.I):
            for token in cl.split():
                if "offer" in token.lower():
                    classes[token] = classes.get(token, 0) + 1
        print("  offer class frequency: %s" % sorted(classes.items(), key=lambda kv: -kv[1])[:12])
        if classes:
            top = max(classes.items(), key=lambda kv: kv[1])[0]
            pat = r'<[a-z]+[^>]*class="[^"]*\b%s\b[^"]*"' % re.escape(top)
            starts = [m.start() for m in re.finditer(pat, page, re.I)]
            print("  dumping %d cards of class %r" % (min(want, len(starts)), top))
            for i, st in enumerate(starts[:want]):
                end = starts[i + 1] if i + 1 < len(starts) else min(len(page), st + 5000)
                print("  --- card %d verbatim ---" % (i + 1))
                print(page[st:end])
        return

    if container is None:
        seen, order = set(), []
        for h in re.findall(r'<a\b[^>]*href="([^"]+)"', page, re.I):
            if h not in seen:
                seen.add(h)
                order.append(h)
        print("  %d unique anchors:" % len(order))
        for h in order:
            print("     %s" % h[:170])
        # gestmax often renders the list from an inline JSON or a data- attribute
        for pat in (r'data-[a-z-]*(?:offer|job|annonce)[a-z-]*="[^"]{0,120}',
                    r'/(?:offre|annonce|job|emploi)[a-z0-9_/-]{0,80}'):
            hits = sorted(set(re.findall(pat, page, re.I)))[:25]
            print("  pattern %s -> %d unique" % (pat[:40], len(hits)))
            for h in hits:
                print("     %s" % h[:150])
        return

    starts = [m.start() for m in re.finditer(container, page, re.I)]
    print("  %d %s containers" % (len(starts), container[:30]))
    for i, st in enumerate(starts[:want]):
        end = starts[i + 1] if i + 1 < len(starts) else min(len(page), st + 6000)
        print("  --- card %d verbatim ---" % (i + 1))
        print(page[st:end])


# BNP got a 403 from the runner on the very URL that answers 200 from a normal
# connection, with a browser UA and browser Accept headers. That is the shape of
# an IP-reputation block, not a header problem - but "looks like" is not a
# finding, so this climbs the ladder for real and prints what each rung gets.
BNP_URL = "https://group.bnpparibas/en/careers/all-job-offers"
BNP_RUNGS = [
    ("urllib default UA, no headers at all", {}),
    ("plain non-browser UA", {"User-Agent": "python-requests/2.31.0"}),
    ("browser UA only", {"User-Agent": UA["User-Agent"]}),
    ("browser UA + Accept */*", {"User-Agent": UA["User-Agent"], "Accept": "*/*"}),
    ("full browser header set", dict(UA, **{
        "Referer": "https://group.bnpparibas/en/careers",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document", "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "same-origin", "Sec-Fetch-User": "?1",
        "Connection": "keep-alive"})),
]


def bnp_ladder():
    import time
    print("=" * 78)
    print("bnp ladder   %s" % BNP_URL)
    for label, headers in BNP_RUNGS:
        req = urllib.request.Request(BNP_URL, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=45) as r:
                body = r.read()
                print("  %-38s %s  %d bytes" % (label, r.status, len(body)))
                text = body.decode("utf-8", "replace")
                for pat in (r"(\d[\d\s ]{0,6})\s*job offers", r"<title[^>]*>([^<]{0,120})"):
                    m = re.search(pat, text, re.I)
                    if m:
                        print("       %s" % m.group(0).strip()[:100])
        except urllib.error.HTTPError as e:
            snippet = e.read(400).decode("utf-8", "replace").replace("\n", " ")
            print("  %-38s HTTP %s  %s" % (label, e.code, snippet[:220]))
        except Exception as e:
            print("  %-38s %s: %s" % (label, type(e).__name__, e))
        time.sleep(2)
    # Is it the host or the path? A 200 on any other page of the same host means
    # the block is per-path; a 403 everywhere means the IP is the problem.
    for other in ("https://group.bnpparibas/en/",
                  "https://group.bnpparibas/robots.txt",
                  "https://group.bnpparibas/en/careers"):
        try:
            with urllib.request.urlopen(
                    urllib.request.Request(other, headers=UA), timeout=30) as r:
                print("  same host %-45s %s  %d bytes" % (other, r.status, len(r.read())))
        except urllib.error.HTTPError as e:
            print("  same host %-45s HTTP %s" % (other, e.code))
        except Exception as e:
            print("  same host %-45s %s" % (other, type(e).__name__))
        time.sleep(2)


if __name__ == "__main__":
    for n in (sys.argv[1:] or list(SOURCES)):
        if n == "bnp-ladder":
            bnp_ladder()
            continue
        if n not in SOURCES:
            print("unknown source %r; known: %s" % (n, ", ".join(SOURCES)))
            continue
        probe(n)
