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
    "mbda2":       ("https://mbda.gestmax.fr/search/index/page/2", None, 0),
    # BNP. The public board is group.bnpparibas/en/careers/all-job-offers, which
    # answers 200 to a plain server-side fetch with no cookies and a non-browser
    # UA - Akamai Bot Manager is on the domain but is not gating this path. The
    # 403 that put BNP on WTTJ was a different host (the applicant portal). So
    # no cookie warming and no sensor replay; a later 403 would be rate limiting,
    # and the answer to that is a sleep between pages.
    "bnp":         ("https://group.bnpparibas/en/careers/all-job-offers", "FORM", 2),
    "bnp-p2":      ("https://group.bnpparibas/en/careers/all-job-offers?page=1", "FORM", 1),
}


def fetch(url):
    req = urllib.request.Request(url, headers={**UA, "Accept-Encoding": "gzip"})
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


if __name__ == "__main__":
    for n in (sys.argv[1:] or list(SOURCES)):
        if n not in SOURCES:
            print("unknown source %r; known: %s" % (n, ", ".join(SOURCES)))
            continue
        probe(n)
