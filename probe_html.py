#!/usr/bin/env python3
"""Probe the HTML job boards that have no JSON API, and print their shape.

    python probe_html.py [name ...]

The Claude sandbox's egress proxy answers 403 to CONNECT for every one of these
hosts, so this cannot be run there - it exists to be run from Actions, where the
runner has real internet, exactly like bulk_probe.py. Read the log, then write
the fetcher against what it printed. Nothing here is guessed.

For each source it prints: the HTTP status and page size, how many times each
candidate offer-link pattern matched, and a raw slice of the markup around the
first match so the card structure (title, location, contract) can be read off.
"""
import re, sys, gzip, io, urllib.error, urllib.parse, urllib.request

UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36",
      "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
      "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8"}

# name -> (url, [extra candidate link regexes])
SOURCES = {
    "amundi":      ("https://jobs.amundi.com/offre-de-emploi/liste-toutes-offres.aspx?page=1&LCID=1036", []),
    "amundi-rss":  ("https://jobs.amundi.com/rss.aspx?LCID=1036", []),
    "dassault-av": ("https://dassault-aviation-cand.talent-soft.com/offre-de-emploi/liste-offres.aspx?page=1", []),
    "mbda":        ("https://mbda.gestmax.fr/search/index/page/1", []),
    "expleo":      ("https://expleo-jobs-fr-fr.icims.com/jobs/search?pr=0&in_iframe=1", []),
    "naval":       ("https://www.naval-group.com/fr/nous-rejoindre?page=0&contractType%5B%5D=2463", []),
    "naval-all":   ("https://www.naval-group.com/fr/nous-rejoindre?page=0", []),
}

# Patterns worth counting on every page. The winner becomes the fetcher's regex.
CANDIDATES = [
    ("talentsoft-offer",  r'href="([^"]*/offre-de-emploi/emploi[^"]*\.aspx[^"]*)"'),
    ("talentsoft-any",    r'href="([^"]*offre-de-emploi[^"]*)"'),
    ("gestmax-offer",     r'href="([^"]*/offre-de-emploi/[^"]*)"'),
    ("gestmax-job",       r'href="([^"]*/job/[^"]*)"'),
    ("icims-job",         r'href="([^"]*/jobs/\d+/[^"]*)"'),
    ("drupal-offer",      r'href="([^"]*/offre[^"]*)"'),
    ("drupal-rejoindre",  r'href="([^"]*nous-rejoindre/[^"]*)"'),
    ("rss-item-link",     r'<link>\s*([^<]+)</link>'),
    ("any-anchor",        r'<a\b[^>]*href="([^"]+)"'),
]


def fetch(url):
    req = urllib.request.Request(url, headers={**UA, "Accept-Encoding": "gzip"})
    with urllib.request.urlopen(req, timeout=60) as r:
        raw = r.read()
        enc = (r.headers.get("Content-Encoding") or "").lower()
        if "gzip" in enc:
            raw = gzip.decompress(raw)
        charset = r.headers.get_content_charset() or "utf-8"
        return r.status, r.geturl(), raw.decode(charset, "replace")


def probe(name):
    url, extra = SOURCES[name]
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
    print("  status %s  %d bytes" % (status, len(page)))
    if final != url:
        print("  redirected to %s" % final)
    best = None
    for label, pat in CANDIDATES + [("extra-%d" % i, p) for i, p in enumerate(extra)]:
        hits = re.findall(pat, page, re.I)
        uniq = sorted(set(hits))
        print("  %-18s %4d matches, %3d unique" % (label, len(hits), len(uniq)))
        for h in uniq[:3]:
            print("        %s" % h[:150])
        # the winner is the most specific pattern that found a plausible list
        if 3 <= len(uniq) <= 400 and label != "any-anchor" and best is None:
            best = (label, pat, hits)
    # total-count hints: a "N offres" string tells us how paging should end
    for m in re.finditer(r"(\d[\d\s ]{0,6})\s*(offres?|r[ée]sultats?|jobs?|postes?)", page, re.I):
        print("  count-hint: %r" % m.group(0).strip()[:60])
        break
    if best:
        label, pat, hits = best
        m = re.search(pat, page, re.I)
        start = max(0, m.start() - 900)
        print("  --- markup around first %s match ---" % label)
        print(page[start:m.end() + 900])
    else:
        print("  --- head of page (no candidate matched) ---")
        print(page[:2500])


if __name__ == "__main__":
    names = sys.argv[1:] or list(SOURCES)
    for n in names:
        if n not in SOURCES:
            print("unknown source %r; known: %s" % (n, ", ".join(SOURCES)))
            continue
        probe(n)
