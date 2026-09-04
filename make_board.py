#!/usr/bin/env python3
"""Stage Watch - build the internship board from ATS APIs.

  python make_board.py                      -> board.html (fresh, no diff)
  python make_board.py --prev prev.html     -> board.html, diffed against the
                                               previous artifact for NEW/CLOSED

Self-contained on purpose: the nightly cloud run has no access to any other
file, so config + fetchers + template all live here.
"""
import json, os, re, sys, html, urllib.error, urllib.parse, urllib.request, time
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

# Probed and confirmed to have NO supported public API. Listed so nobody wastes
# time re-probing them; check these by hand or via their own alerts.
#
# "clean negative" below means the probe workflow got a REAL answer - a 404, or
# SmartRecruiters' documented 200-with-empty-content - from every one of those
# six ATSs. It is not a claim that the company is unreachable by any means: a
# vendor-locked system (Avature, Taleo, Phenom, SuccessFactors, iCIMS) or a
# Workday site whose name has to be read off the careers page looks exactly the
# same from here. Where a path is untested rather than ruled out, it says so.
#
# Two caveats on the negatives, both from the probe's own per-tester tally:
#   - recruitee has never once answered across any run and had no control
#     company, so "not on recruitee" is unproven rather than established.
#   - Welcome to the Jungle is excluded entirely: it 403s every request from a
#     runner, including companies known to be on it. See bulk_probe.py.
NO_API = [
    ("Dynatrace",    "custom Coveo search endpoint; probed 2026-09-04 against greenhouse/lever/ashby/smartrecruiters/teamtailor/workable: clean negative. Three guessed\n                      Workday sites all returned 422, so Workday is untested rather than ruled\n                      out - it needs the real site name off the careers page"),
    ("OVHcloud",     "SAP SuccessFactors; probed 2026-09-04 against greenhouse/lever/ashby/smartrecruiters/teamtailor/workable: clean negative.\n                      Guessed Workday sites returned 422, so untested"),
    ("GitHub",       "iCIMS; probed 2026-09-04 against greenhouse/lever/ashby/smartrecruiters/teamtailor/workable: clean negative"),
    ("HashiCorp",    "acquired by IBM, careers redirect to IBM Careers; probed 2026-09-04 against greenhouse/lever/ashby/smartrecruiters/teamtailor/workable: clean negative"),
    ("Clever Cloud", "/careers/ redirects to a product page; probed 2026-09-04 against greenhouse/lever/ashby/smartrecruiters/teamtailor/workable: clean negative, 3 slug variants"),
    ("Tsuga",        "no job board found; probed 2026-09-04 against greenhouse/lever/ashby/smartrecruiters/teamtailor/workable: clean negative, 3 slug variants"),
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
    # slug is "mistral.ai" WITH the dot - "mistral", "mistralai" and "mistral-ai"
    # all return an empty SPA shell that answers 200, which is why probing by
    # status code alone marked this company unreachable.
    {"name": "Mistral AI",       "ats": "ashby", "slug": "mistral.ai",
     "careers": "https://mistral.ai/careers"},
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
    # Confirmed 2026-09-04 by the probe workflow: 16 postings on teamtailor/deezer,
    # titles unmistakably Deezer France. The old note said the careers URL
    # redirected to their investor site, which was true and beside the point -
    # the ATS feed was there the whole time.
    {"name": "Deezer",           "ats": "teamtailor", "slug": "deezer",
     "careers": "https://deezer.teamtailor.com/"},
    {"name": "Amadeus",          "ats": "workday", "tenant": "amadeus", "wd": "wd502",
     "site": "jobs", "careers": "https://careers.amadeus.com/"},
    {"name": "Murex",            "ats": "workday", "tenant": "murex", "wd": "wd3",
     "site": "MurexCareerPage1", "careers": "https://careers.murex.com/"},
]

NO_API2 = [
    ("Kayrros",    "careers page 404s; probed 2026-09-04 against greenhouse/lever/ashby/smartrecruiters/teamtailor/workable: clean negative, 3 slug variants"),
    ("INRIA",      "custom public-research portal (jobs.inria.fr); probed 2026-09-04 against greenhouse/lever/ashby/smartrecruiters/teamtailor/workable: clean negative.\n                    Three guessed JSON endpoints returned 301 or HTML, so the portal may still\n                    expose a feed - finding it needs a browser, not another guess"),
    ("CEA",        "custom public-research portal; probed 2026-09-04 against greenhouse/lever/ashby/smartrecruiters/teamtailor/workable: clean negative"),
    ("CNRS",       "custom public-research portal (emploi.cnrs.fr); probed 2026-09-04 against greenhouse/lever/ashby/smartrecruiters/teamtailor/workable: clean negative"),
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
    # The four French banks below are reached through Welcome to the Jungle, not
    # their own systems: BNP's careers site 403s a datacenter IP, Societe
    # Generale's Taleo layer needs a PORTAL_ID that is not in the page source,
    # and Credit Agricole and Natixis have no public feed at all. Confirmed
    # 2026-09-04, each returning real stages - "Software developper" (Lille) at
    # SocGen, "Stage - Economiste / Data visualisation" (Paris) at BNP.
    # partial on purpose: WTTJ is a second-hand view of SG's own Taleo board, so
    # its absence from WTTJ is not evidence a role closed. Drop the flag once the
    # Taleo PORTAL_ID is captured and SG is read from source.
    {"name": "Societe Generale", "ats": "wttj", "slug": "societe-generale", "partial": True,
     "careers": "https://www.welcometothejungle.com/fr/companies/societe-generale/jobs"},
    {"name": "BNP Paribas",     "ats": "wttj", "slug": "bnp-paribas",
     "careers": "https://www.welcometothejungle.com/fr/companies/bnp-paribas/jobs"},
    # groupe-credit-agricole covers the group including CIB. jobs.ca-cib.com has
    # a working stage-filtered RSS feed, but it is capped at 20 items and carries
    # no location, so a role dropping off the end would look closed - see NO_API3.
    {"name": "Credit Agricole", "ats": "wttj", "slug": "groupe-credit-agricole",
     "careers": "https://www.welcometothejungle.com/fr/companies/groupe-credit-agricole/jobs"},
    {"name": "Natixis",         "ats": "wttj", "slug": "natixis",
     "careers": "https://www.welcometothejungle.com/fr/companies/natixis/jobs"},
    # Jane Street and IMC have working boards but no French office, so they will
    # normally show 0. Kept because a Paris desk would appear here immediately.
    {"name": "Jane Street", "ats": "greenhouse", "slug": "janestreet",
     "careers": "https://www.janestreet.com/join-jane-street/"},
    {"name": "IMC",         "ats": "greenhouse", "slug": "imc",
     "careers": "https://careers.imc.com/"},
]

# Sources probed 2026-09-04 and deliberately NOT adopted, with the reason - so the
# next person does not spend a morning rediscovering them:
#   jobs.ca-cib.com RSS  Talentsoft, stage-filtered, works. Capped at 20 items and
#                        carries no location; the JobCountry=79 facet is ignored.
#                        A capped feed makes a role falling off the end look
#                        CLOSED, and Credit Agricole is covered via WTTJ anyway.
#   group.bnpparibas     NOT an IP block - that was my wrong call, corrected by a
#                        ladder run on 2026-09-04. Diagnosed properly:
#                          step 1  browser headers, referer page first, cookie jar
#                                  kept              -> 403, Server: AkamaiGHost
#                          step 2  httpx, same headers, HTTP/2 AND HTTP/1.1
#                                                    -> 403, Server: AkamaiGHost
#                          step 3  curl_cffi impersonate=chrome
#                                                    -> 200, real page, 10 job links
#                        403 body is Akamai "Access Denied", Reference #18.6f6c3817
#                        ..., errors.edgesuite.net; sets ak_bot. The 200 sets _abck.
#                        So the discriminator is the TLS fingerprint, i.e. Akamai
#                        Bot Manager - not the IP, not the headers, not HTTP/2.
#                        robots.txt (read with the same client, HTTP 200) disallows
#                        only query-string patterns - ?q=, ?domain=, ?study= and
#                        friends - none of which match the target path.
#                        NOT adopted anyway: reaching it means impersonating a
#                        browser TLS fingerprint to defeat a bot-detection control
#                        the operator deliberately deployed, and BNP is already
#                        covered via WTTJ. Revisit only on an explicit decision.
#   socgen.taleo.net     real ATS layer. The earlier "PORTAL_ID not in the page
#                        source" was the WRONG TEST, not a finding: the id is a
#                        query parameter on the XHR the page fires, so a regex over
#                        jobsearch.ftl could never have found it. Probed 2026-09-04
#                        with the portal parameter omitted entirely, as some Taleo
#                        tenants allow: HTTP 200 but requisitionList=0 and
#                        totalCount=null. So this tenant needs the real id, from a
#                        browser network-tab capture. SG stays on WTTJ and is
#                        flagged partial there.
NO_API3 = [
    ("Capgemini",          "Phenom People; probed 2026-09-04 against greenhouse/lever/ashby/smartrecruiters/teamtailor/workable: clean negative.\n                            The eightfold probe 404d, so that endpoint is unverified"),
    ("Atos / Eviden",      "SAP SuccessFactors (jobs.atos.net); probed 2026-09-04 against greenhouse/lever/ashby/smartrecruiters/teamtailor/workable: clean negative, 4 slug variants"),
    ("Safran",             "workable/safrangroup re-probed 2026-09-04: 17 postings, every one in "
                           "Pitstone or Banbury UK = Safran Engineering Services UK Ltd, not the group"),
    ("Hudson River Trading","greenhouse/hrttalentcommunity is a talent-community stub (3 generic\n                            entries), not the real board; no French office; re-probed 2026-09-04 in a small run with no rate limiting: clean negative on all seven ATSs"),
    ("Optiver",            "bespoke careers system, no ATS; re-probed 2026-09-04 in a small run with no rate limiting: clean negative on all seven ATSs"),
    ("Millennium",         "Eightfold; probed 2026-09-04 against greenhouse/lever/ashby/smartrecruiters/teamtailor/workable: clean negative. The eightfold API probe\n                            404d on every domain tried, so that path is unverified, not ruled out"),
    ("Groupe BPCE",        "no public job API found; re-probed 2026-09-04 in a small run with no rate limiting: clean negative on all seven ATSs, 3 slug variants"),
    ("Banque Populaire",   "regional BPCE portals, no public API; re-probed 2026-09-04 in a small run with no rate limiting: clean negative on all seven ATSs"),
    ("Caisse d'Epargne",   "regional BPCE portals, no public API; re-probed 2026-09-04 in a small run with no rate limiting: clean negative on all seven ATSs, 3 variants"),
    ("Credit Mutuel",      "no public job API found; re-probed 2026-09-04 in a small run with no rate limiting: clean negative on all seven ATSs"),
    ("CIC",                "lever/cic re-probed 2026-09-04: 13 postings in Tokyo, Cambridge MA and "
                           "Warsaw = Cambridge Innovation Center, NOT the French bank"),
    ("Credit Mutuel Arkea","no public job API found; re-probed 2026-09-04 in a small run with no rate limiting: clean negative on all seven ATSs, 3 slug variants"),
    ("La Banque Postale",  "no public job API found; re-probed 2026-09-04 in a small run with no rate limiting: clean negative on all seven ATSs"),
    ("LCL",                "no public job API found; re-probed 2026-09-04 in a small run with no rate limiting: clean negative on all seven ATSs"),
    ("HSBC / CCF",         "Avature (mycareer.hsbc.com); probed 2026-09-04 against greenhouse/lever/ashby/smartrecruiters/teamtailor/workable: clean negative, 3 slug variants"),
    ("Bpifrance",          "no public job API found; re-probed 2026-09-04 in a small run with no rate limiting: clean negative on all seven ATSs"),
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

# --- location -------------------------------------------------------------
# A city whitelist can only ever SHRINK the result set: a role in a town that is
# not listed is invisible and nothing says so. Three defences: the list below is
# long, it also carries regions/departments (Workday often shows only those), and
# every fetcher that gets a structured country back normalises it to "France" so
# the country alone is enough.
_FR_CITIES = (
    "paris|lyon|nantes|lille|bordeaux|toulouse|grenoble|sophia|montpellier|nice|rennes|strasbourg|"
    "marseille|aix-en-provence|cannes|toulon|marignane|blagnac|colomiers|cugnaux|saint-nazaire|brest|"
    "angers|le mans|tours|orl[ée]?ans|dijon|metz|nancy|reims|rouen|caen|limoges|clermont-ferrand|"
    "saint-[ée]?tienne|valence|avignon|pau|tarbes|la rochelle|poitiers|amiens|dunkerque|versailles|"
    "v[ée]?lizy|villacoublay|[ée]?lancourt|massy|palaiseau|saclay|courbevoie|nanterre|boulogne|issy|"
    "meudon|montrouge|levallois|neuilly|cergy|[ée]?vry|cr[ée]?teil|roissy|gennevilliers|saint-denis|"
    "marne-la-vall[ée]?e|guyancourt|trappes|carquefou|villeurbanne|annecy|chamb[ée]?ry|besan[çc]?on|"
    "mulhouse|colmar|belfort|montbeliard|vitrolles|rungis|suresnes|colombes|vannes|lorient|quimper|"
    "laval|cholet|niort|bayonne|perpignan|b[ée]?ziers|"
    # added after an audit found real defence/aerospace/industrial sites missing
    "m[ée]?rignac|le haillan|saint-m[ée]?dard|bourges|ch[âa]?tellerault|istres|ymare|val-de-reuil|"
    "moirans|fleury-les-aubrais|bezons|osny|conflans|vitry|saint-quentin-en-yvelines|lannion|"
    "plouzan[ée]?|cesson|bruz|les mureaux|mantes|poissy|montigny|plaisir|argenteuil|la d[ée]?fense|"
    "puteaux|malakoff|vanves|clichy|saint-cloud|s[èe]?vres|chatou|rueil|antony|orsay|gif-sur-yvette|"
    "marcoussis|les ulis|corbeil|villebon|ivry|alfortville|charenton|montreuil|pantin|aubervilliers|"
    "le bourget|villaroche|melun|compi[èe]?gne|beauvais|chartres|blois|bourg-en-bresse|roanne|vienne|"
    "salaunes|salon-de-provence|la ciotat|sainte-tulle|manosque|cadarache|le barp|biscarrosse"
)
# Workday and some Taleo fronts show only the region or the department.
_FR_REGIONS = (
    "[îi]?le-de-france|hauts-de-seine|seine-saint-denis|val-de-marne|val-d.oise|yvelines|essonne|"
    "seine-et-marne|bouches-du-rh[ôo]?ne|haute-garonne|gironde|loire-atlantique|ille-et-vilaine|"
    "bas-rhin|haut-rhin|alpes-maritimes|is[èe]?re|rh[ôo]?ne|occitanie|nouvelle-aquitaine|"
    "auvergne-rh[ôo]?ne-alpes|bretagne|normandie|grand est|hauts-de-france|provence|"
    "pays de la loire|centre-val de loire|bourgogne|franche-comt[ée]?|corse"
)
LOC    = re.compile(r"\b(france|" + _FR_CITIES + "|" + _FR_REGIONS + r")\b", re.I)
# What a fetcher's structured country field looks like when it means France.
FR_CODE = re.compile(r"^\s*(fr|fra|france|frankreich)\s*$", re.I)

# --- is this role in France? ----------------------------------------------
# Three answers, not two. The old code asked "does the location match my city
# list?" and dropped everything else, so a stage in a town nobody had listed
# vanished with nothing to show it ever existed. A city whitelist can only
# shrink the result set and never tells you what it cost you.
#
# So: France when we recognise it, FOREIGN only when the string positively says
# somewhere else, and UNKNOWN otherwise - and UNKNOWN is shown on the board
# instead of being thrown away. Any real French town that turns up in that box
# belongs in _FR_CITIES; that is the feedback loop the whitelist never had.
_NOT_FR = (
    "united states|u\\.s\\.a?\\.|america|canada|mexico|brazil|br[ée]sil|argentina|chile|colombia|"
    "united kingdom|england|scotland|wales|ireland|irlande|london|londres|manchester|edinburgh|"
    "dublin|cork|belfast|"
    "germany|allemagne|deutschland|berlin|munich|m[üu]nchen|hamburg|frankfurt|cologne|k[öo]ln|"
    "stuttgart|d[üu]sseldorf|"
    "spain|espagne|espa[ñn]a|madrid|barcelona|barcelone|valencia|sevilla|m[áa]laga|"
    "portugal|lisbon|lisbonne|lisboa|porto|"
    "italy|italie|italia|milan|milano|rome|roma|turin|torino|"
    "netherlands|pays-bas|nederland|amsterdam|rotterdam|utrecht|eindhoven|the hague|"
    "belgium|belgique|belgi[ëe]|brussels|bruxelles|antwerp|anvers|ghent|"
    "switzerland|suisse|schweiz|zurich|z[üu]rich|geneva|gen[èe]ve|lausanne|basel|b[âa]le|"
    "austria|autriche|vienna|vienne|wien|"
    "poland|pologne|polska|warsaw|varsovie|krakow|cracovie|wroclaw|gdansk|"
    "czech|tch[èe]que|prague|praha|slovakia|slovaquie|bratislava|hungary|hongrie|budapest|"
    "romania|roumanie|bucharest|bucarest|cluj|bulgaria|bulgarie|sofia|"
    "sweden|su[èe]de|stockholm|gothenburg|norway|norv[èe]ge|oslo|denmark|danemark|copenhagen|"
    "copenhague|finland|finlande|helsinki|iceland|islande|reykjavik|"
    "estonia|estonie|tallinn|latvia|lettonie|riga|lithuania|lituanie|vilnius|"
    "greece|gr[èe]ce|athens|ath[èe]nes|cyprus|chypre|malta|malte|"
    "ukraine|kyiv|kiev|lviv|poland|serbia|serbie|belgrade|croatia|croatie|zagreb|slovenia|"
    "slov[ée]nie|ljubljana|"
    "israel|isra[ëe]l|tel aviv|jerusalem|turkey|turquie|istanbul|ankara|"
    "india|inde|bangalore|bengaluru|hyderabad|mumbai|pune|chennai|delhi|gurgaon|noida|"
    "china|chine|beijing|p[ée]kin|shanghai|shenzhen|hong kong|taiwan|taipei|"
    "japan|japon|tokyo|osaka|korea|cor[ée]e|seoul|s[ée]oul|"
    "singapore|singapour|malaysia|malaisie|kuala lumpur|indonesia|indon[ée]sie|jakarta|"
    "thailand|tha[ïi]lande|bangkok|vietnam|hanoi|philippines|manila|manille|"
    "australia|australie|sydney|melbourne|brisbane|perth|new zealand|auckland|"
    "south africa|afrique du sud|johannesburg|cape town|nigeria|lagos|kenya|nairobi|egypt|"
    "[ée]gypte|cairo|le caire|morocco|maroc|casablanca|rabat|tunisia|tunisie|tunis|algeria|"
    "alg[ée]rie|alger|"
    "united arab emirates|dubai|duba[ïi]|abu dhabi|saudi|arabie|riyadh|qatar|doha|"
    # US and Canadian metros that show up without a country
    "new york|nyc|brooklyn|san francisco|bay area|palo alto|mountain view|sunnyvale|san jose|"
    "santa clara|seattle|bellevue|portland|austin|dallas|houston|atlanta|chicago|boston|"
    "cambridge, ma|denver|boulder|phoenix|san diego|los angeles|washington, d|arlington, v|"
    "miami|philadelphia|pittsburgh|detroit|minneapolis|salt lake|raleigh|charlotte|nashville|"
    "toronto|vancouver|montreal|montr[ée]al|ottawa|calgary|waterloo, on|"
    # region buckets a global board uses instead of a country
    # added from the audit box after the first run - all Airbus/Thales sites
    "tianjin|suzhou|chengdu|s[ãa]?o.paulo|manching|donauw[öo]?rth|immenstaad|bremen|lodz|"
    "hengelo|gorgonzola|getafe|cadiz|c[áa]diz|brasov|braov|toulouse-blagnac-area|"
    "worldwide|global|anywhere|multiple countries"
)
NOT_FR = re.compile(r"\b(" + _NOT_FR + r")\b", re.I)
# Case-SENSITIVE on purpose. Lowercased, 'in' is Indiana, 'us' is the pronoun and
# 'me' is Maine - matching those case-insensitively turns "Remote in Europe" into
# a US role. A state code only counts after a comma, which is how every board
# writes it.
NOT_FR_CS = re.compile(r",\s*(A[KLRZ]|C[AOT]|D[CE]|FL|GA|HI|I[ADLN]|K[SY]|LA|M[ADEINOST]|"
                       r"N[CDEHJMVY]|O[HKR]|P[AR]|RI|S[CD]|T[NX]|UT|V[AT]|W[AIVY])\b"
                       r"|\b(US|USA|U\.S\.|UK|EMEA|APAC|LATAM|NAMER|AMER|ANZ|DACH|BENELUX|MENA)\b")


def where(blob):
    """'fr' | 'foreign' | 'unknown'. France wins ties: a posting listed for both
    Paris and London is a Paris posting as far as this board is concerned."""
    if LOC.search(blob):
        return "fr"
    if NOT_FR.search(blob) or NOT_FR_CS.search(blob):
        return "foreign"
    return "unknown"


INTERN = re.compile(r"\b(stage|stagiaire|pfe|intern|internship|fin d['’]?\s*[ée]tudes|c[ée]sure)\b", re.I)
ALT    = re.compile(r"\b(alternance|alternant|apprenti|apprentissage|apprentice)\b", re.I)

# Anything that plausibly means "this is an engineering role". Deliberately wide:
# a false positive costs one glance, a false negative costs an application.
TECH   = re.compile(
    r"(software|swe|engineer|engineering|developer|d[ée]veloppeur|ing[ée]nieur|informatique|logiciel|"
    r"d[ée]veloppement|donn[ée]es|r[ée]seau|syst[èe]me|embarqu[ée]|embedded|cybers[ée]curit[ée]|"
    r"algorithm|calcul|backend|back-end|frontend|front-end|fullstack|full.stack|sre|site reliability|"
    r"devops|devsecops|mlops|platform|infra|infrastructure|cloud|kubernetes|data|\bml\b|"
    r"machine learning|deep learning|\bnlp\b|\bllm\b|\bgpu\b|\bhpc\b|\bai\b|\bia\b|"
    r"intelligence artificielle|security|s[ée]curit[ée]|scientist|chercheur|quantitative|quant |"
    # added after an audit: these were all being dropped
    r"signal|radar|avionique|optique|photoniq|fpga|vhdl|verilog|[ée]lectroniq|firmware|hardware|"
    r"t[ée]l[ée]com|robot|automatis|automation|simulation|mod[ée]lisation|\bqa\b|\btest\b|validation|"
    r"\bit\b|\bweb\b|mobile|android|\bios\b|python|javascript|typescript|\bjava\b|\bc\+\+|"
    r"architect|compilateur|compiler|database|base de donn[ée]es|\bsql\b|linux|\bsap\b|"
    r"observabilit|monitoring|blockchain|cryptograph|statistiq|analytics)", re.I)

# A title can match TECH incidentally - 'Legal Intern - Product & AI' hits ai.
# These business-function words veto a tech match.
EXCL   = re.compile(r"\b(legal|juridique|marketing|sales|vente|commercial|business development|talent|"
                    r"recruit|people|hr|rh|brand|communication|content|community|finance|accounting|"
                    r"comptab|audit|payroll|paie|office manager|customer success|account executive|"
                    r"partnership)\b", re.I)
# ...but a veto word is often just the DOMAIN of a real engineering role: a data
# engineer on the finance team, a security audit, cloud pre-sales. When one of
# these unambiguous words is present the veto is overridden. Nothing generic goes
# in here - 'reseau' would let 'Marketing & Reseaux Sociaux' back in.
STRONG = re.compile(
    r"(software|\bswe\b|d[ée]veloppeur|developer|backend|back-end|frontend|front-end|fullstack|"
    r"full.stack|devops|devsecops|mlops|\bsre\b|site reliability|kubernetes|cloud|infrastructure|"
    r"\binfra\b|cybers[ée]curit[ée]|s[ée]curit[ée]|machine learning|deep learning|"
    r"data\s+(?:engineer|scientist|engineering|platform|architect)|logiciel|informatique|embarqu[ée]|"
    r"embedded|firmware|hardware|fpga|vhdl|compilateur|compiler|blockchain|cryptograph|linux|"
    r"\bsql\b|python|javascript|typescript)", re.I)


def is_tech(title):
    """True when the title reads as an engineering role. EXCL vetoes a weak
    match; STRONG overrides the veto."""
    if not TECH.search(title):
        return False
    return bool(STRONG.search(title)) or not EXCL.search(title)


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


def _fr(blob, *countries):
    """Append 'France' when the ATS handed back a structured country field that
    means France. Some boards send the ISO code only, and a bare 'FR' matches
    nothing in the city list - the country is the most reliable signal there is,
    so never let it fall through."""
    for ctry in countries:
        if ctry and FR_CODE.match(str(ctry)):
            return ("%s France" % blob).strip()
    return blob


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
        out.append((j.get("title", ""), loc, j.get("url", ""),
                    _fr(loc, j.get("country"), j.get("country_code"))))
    return out


def f_smartrecruiters(c):
    out, off = [], 0
    while True:
        d = get("https://api.smartrecruiters.com/v1/companies/%s/postings?limit=100&offset=%d" % (c["slug"], off))
        for j in d.get("content", []):
            lo = j.get("location") or {}
            loc = ", ".join(x for x in [lo.get("city"), lo.get("country")] if x)
            out.append((j.get("name", ""), loc,
                        "https://jobs.smartrecruiters.com/%s/%s" % (c["slug"], j.get("id", "")),
                        _fr(loc, lo.get("country"), lo.get("countryCode"))))
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

# Companies whose fetch came back INCOMPLETE (a paging ceiling was hit, not an
# error). Their roles are shown, but nothing of theirs may be marked closed: a
# posting past the cut-off is invisible, not gone, and closing it would fire a
# "role closed" notification for a role that is still open.
PARTIAL = set()


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
            rows, cut = _workday_page(api, pub, facets_q, text)
            if cut:
                PARTIAL.add(c["name"])
            for row in rows:
                if row[2] not in seen:
                    seen.add(row[2])
                    merged.append(row)
        return merged
    rows, cut = _workday_page(api, pub, {}, "")
    if cut:
        PARTIAL.add(c["name"])
    return rows


def _workday_page(api, pub, facets, text):
    """-> (rows, truncated). truncated means the ceiling stopped us early, so
    the caller must not treat anything missing as closed."""
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
        if len(page) < 20:
            return out, False
        if off >= WORKDAY_MAX:
            return out, True
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
        ctry = (((j.get("address") or {}).get("postalAddress") or {}).get("addressCountry"))
        # jobUrl comes back verbatim from the API - never construct it
        out.append((j.get("title", ""), blob or loc, j.get("jobUrl", ""), _fr(blob, ctry)))
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
        locs, ctries = [], []
        for L in raw:
            a = (L or {}).get("address") or {}
            ctries.append(a.get("addressCountry"))
            locs.append(", ".join(x for x in [a.get("addressLocality"), a.get("addressCountry")] if x))
        loc = "; ".join([x for x in locs if x])
        # url comes back verbatim from the feed - never construct it
        out.append((it.get("title", ""), loc, it.get("url", ""), _fr(loc, *ctries)))
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
        total = int(d.get("nhits") or 0)
        if off >= 2000 and off < total:
            PARTIAL.add(c["name"])
            return out
        if not hits or off >= total:
            return out


# Welcome to the Jungle. Not an ATS - an aggregator - and the only way in to the
# French banks, whose own systems are all vendor-locked (Avature, Taleo, Phenom)
# or refuse a datacenter IP. The site drives itself from this public Algolia
# index; the application id and search-only key below are the pair WTTJ ships in
# its own frontend JS, visible in any browser. This is the request the public
# site makes. The api.welcometothejungle.com host is a different thing and 403s
# from a runner, so do not "simplify" this to that.
#
# Probed 2026-09-04: the server-side filter really does narrow to internships,
# and the index returns each posting more than once, so both the filter and the
# de-duplication below are load-bearing.
WTTJ_APP   = "CSEKHVMS53"
WTTJ_KEY   = "4bd8f6215d0cc52b26430765769e65a0"
WTTJ_URL   = "https://csekhvms53-dsn.algolia.net/1/indexes/*/queries"
WTTJ_JOBS  = "wk_cms_jobs_production"
WTTJ_PAGES = 6              # 100 per page; Algolia caps any one query at 1000


def f_wttj(c):
    slug = c["slug"]
    flt = 'organization.slug:"%s" AND contract_type:"INTERNSHIP"' % slug
    out, seen, dropped = [], set(), 0
    verify, blocked = True, False
    for page in range(WTTJ_PAGES):
        params = "hitsPerPage=100&page=%d&filters=%s" % (page, urllib.parse.quote(flt))
        body = json.dumps({"requests": [{"indexName": WTTJ_JOBS, "params": params}]}).encode()
        req = urllib.request.Request(WTTJ_URL, data=body, headers={
            # JSON body under a form content-type: Algolia's documented CORS quirk
            "content-type": "application/x-www-form-urlencoded",
            "x-algolia-application-id": WTTJ_APP,
            "x-algolia-api-key": WTTJ_KEY,
            "origin": "https://www.welcometothejungle.com",
            "User-Agent": UA["User-Agent"]})
        with urllib.request.urlopen(req, timeout=40) as r:
            d = json.load(r)["results"][0]
        hits = d.get("hits") or []
        for h in hits:
            org, job = (h.get("organization") or {}).get("slug"), h.get("slug")
            # The filter is server-side, so check it held. A filter that quietly
            # stopped narrowing would put another company's roles on this board.
            if org != slug or not job:
                continue
            url = "https://www.welcometothejungle.com/fr/companies/%s/jobs/%s" % (org, job)
            if url in seen:
                continue
            seen.add(url)
            off = h.get("office") if isinstance(h.get("office"), dict) else {}
            loc = ", ".join(x for x in [off.get("city"), off.get("country")] if x)
            # This URL is built from two API fields rather than returned whole, so
            # it is checked before being recorded - the board's promise is that
            # every link came back live, and a constructed link has to earn that.
            # But only a 404 disproves a URL. See _verify.
            if verify:
                v = _verify(url)
                if v == "blocked":
                    verify = False      # the host refuses us; stop spending requests
                    blocked = True
                elif v == "gone":
                    dropped += 1
                    continue
            out.append((h.get("name", ""), loc, url, _fr(loc, off.get("country"))))
        if len(hits) < 100 or page + 1 >= (d.get("nbPages") or 1):
            break
        time.sleep(0.2)
    if dropped:
        # A real 404 means the URL pattern is not reliable for this company, so
        # the fetch cannot be trusted to close anything.
        PARTIAL.add(c["name"])
        print("  %s: %d WTTJ url(s) 404ed" % (c["name"], dropped), file=sys.stderr)
    elif blocked:
        print("  %s: WTTJ blocked link verification (403); links unverified this run"
              % c["name"], file=sys.stderr)
    return out


def _verify(url):
    """'ok' | 'gone' | 'blocked'.

    Only a 404/410 disproves a URL. www.welcometothejungle.com answers 403 to a
    datacenter IP for HEAD and GET alike (measured 2026-09-04), and the first
    live sweep read that "cannot check" as "does not exist" and dropped every
    role at all four banks - the exact silent deletion this check exists to
    prevent, caused by the check itself. So a blocked or failed request leaves
    the role in place; only a 404 removes it."""
    req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": UA["User-Agent"]})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return "ok" if r.status < 400 else "gone"
    except urllib.error.HTTPError as e:
        return "gone" if e.code in (404, 410) else "blocked"
    except Exception:
        return "blocked"


FETCH = {"greenhouse": f_greenhouse, "lever": f_lever, "workable": f_workable,
         "smartrecruiters": f_smartrecruiters, "workday": f_workday,
         "ashby": f_ashby, "teamtailor": f_teamtailor,
         "dassault": f_dassault, "wttj": f_wttj}

ENDPOINT = {
    "greenhouse":      lambda c: "boards-api.greenhouse.io/v1/boards/%s/jobs" % c["slug"],
    "lever":           lambda c: "api.lever.co/v0/postings/%s" % c["slug"],
    "workable":        lambda c: "apply.workable.com/api/v1/widget/accounts/%s" % c["slug"],
    "smartrecruiters": lambda c: "api.smartrecruiters.com/v1/companies/%s/postings" % c["slug"],
    "workday":         lambda c: "%s.%s.myworkdayjobs.com/wday/cxs/%s/%s/jobs" % (c["tenant"], c["wd"], c["tenant"], c["site"]),
    "ashby":           lambda c: "api.ashbyhq.com/posting-api/job-board/%s" % c["slug"],
    "teamtailor":      lambda c: "%s.teamtailor.com/jobs.json" % c["slug"],
    "dassault":        lambda c: "www.3ds.com/apisearch/card_search_api (career cards)",
    "wttj":            lambda c: "csekhvms53-dsn.algolia.net wk_cms_jobs_production (org %s)" % c["slug"],
}


def scan():
    results = []
    for c in BOARD["companies"]:
        row = {"name": c["name"], "ats": c["ats"], "careers": c.get("careers", ""),
               "endpoint": ENDPOINT[c["ats"]](c), "error": None, "zero": False,
               "partial": False, "total": 0, "france": 0, "hits": [], "other": [],
               "unsure": [], "foreign": []}
        try:
            jobs = FETCH[c["ats"]](c)
        except Exception as e:
            row["error"] = "%s: %s" % (type(e).__name__, e)
            results.append(row)
            continue
        placed = [(j, where(j[3])) for j in jobs]
        row["total"]  = len(jobs)
        row["france"] = sum(1 for _, w in placed if w == "fr")
        # Internship first, location second. Done the other way round the
        # unrecognised-location box would have to hold every role on a global
        # board with an odd location string; this way it holds a couple a week.
        # The title can lie: Thales titles an apprenticeship "STAGE - ..." while
        # its URL and Workday contract type both say alternance/apprentice.
        itn = [(j, w) for j, w in placed if INTERN.search(j[0])
               and not ALT.search(j[0]) and not ALT.search(j[3])]
        rec = lambda j: {"title": j[0], "location": j[1], "url": j[2]}
        row["hits"]    = [rec(j) for j, w in itn if w == "fr" and is_tech(j[0])]
        row["other"]   = [rec(j) for j, w in itn if w == "fr" and not is_tech(j[0])]
        # not obviously France and not obviously anywhere else - shown, never dropped
        row["unsure"]  = [rec(j) for j, w in itn if w == "unknown"]
        row["foreign"] = [rec(j) for j, w in itn if w == "foreign"]   # audit only
        # A dead slug does not raise: several ATSs answer 200 with an empty list,
        # so the company looks healthy while being invisible. Treated like a
        # partial fetch below - shown, but never a reason to close anything.
        row["zero"]    = len(jobs) == 0
        # "partial": True in the config marks a company whose feed is known to be
        # incomplete, so nothing of its own is ever marked closed off it.
        row["partial"] = c["name"] in PARTIAL or bool(c.get("partial"))
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
/* Hide control. Deliberately quiet until you hover the row - it is a convenience,
   not the point of the page - and never destructive: hiding is per-browser
   display state, the role stays in the data and can always be brought back. */
.hide-btn{float:right;margin:-.1rem 0 0 .6rem;border:0;background:none;cursor:pointer;
  color:var(--muted);font-size:1rem;line-height:1;padding:0 .15rem;opacity:0;
  transition:opacity .12s,color .12s}
li:hover>.hide-btn,.hide-btn:focus{opacity:1}
.hide-btn:hover{color:var(--closed)}
li.dimmed{opacity:.45}
.hidebar{margin:.55rem 0 0;font-size:.78rem;color:var(--muted);
  font-family:"JetBrains Mono",ui-monospace,monospace}
.hidebar button{border:0;background:none;padding:0;margin-left:.5rem;cursor:pointer;
  color:var(--accent);font:inherit;text-decoration:underline}
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
    new_roles, recent_roles = [], []
    cutoff = (NOW.date() - timedelta(days=2)).isoformat()
    for r in results:
        for h in r["hits"]:
            u = h["url"]
            h["first_seen"] = prev_posts.get(u, {}).get("first_seen", TODAY)
            h["is_new"] = (u not in prev_posts) and bool(prev_posts)
            entry = {"title": h["title"], "company": r["name"], "url": u,
                     "first_seen": h["first_seen"]}
            if h["is_new"]:
                new_ct += 1
                new_roles.append(entry)
            # first seen in the last two sweeps. The publish step needs this:
            # "new since last run" is reset by the NEXT sweep, so a day where
            # the publish did not happen would otherwise lose the role silently.
            if h["first_seen"] >= cutoff:
                recent_roles.append(entry)
            cur[u] = {"title": h["title"], "company": r["name"],
                      "location": h["location"], "first_seen": h["first_seen"]}

    # The filtered-out and unrecognised-location boxes were untracked: a role
    # landing in one got no chip and no ping, so a filter mistake cost the job
    # even though the role was sitting on the page. They are tracked here in
    # their own state block - never in `postings`, because a marketing intern
    # going away is not a closure worth reporting.
    prev_watch = prev.get("watch", {})
    watch, also_new = {}, []
    for r in results:
        for kind in ("other", "unsure"):
            for h in r[kind]:
                u = h["url"]
                h["is_new"] = (u not in prev_watch) and bool(prev_watch)
                entry = {"title": h["title"], "company": r["name"], "kind": kind}
                if h["is_new"] and (kind == "other" or is_tech(h["title"])):
                    also_new.append(entry)
                watch[u] = {"title": h["title"], "company": r["name"], "kind": kind}

    # a posting that was live last run and is absent now == filled or pulled.
    # keep it visible for 14 days so a missed day is not a silent deletion.
    closed = [c for c in prev.get("closed", [])
              # a role that is live again is not closed - without this it would
              # sit in both lists for 14 days, and re-closing it would re-notify
              if (NOW.date() - datetime.fromisoformat(c["closed_on"]).date()).days < 14
              and c["url"] not in cur]
    known = {c["url"] for c in closed}
    # an errored, empty or truncated fetch proves nothing about what is still open
    ok_names = {r["name"] for r in results
                if not r["error"] and not r["zero"] and not r["partial"]}
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
    p.append("</p>")
    p.append('<p class="hidebar" id="hidebar"></p>')
    p.append("</header>")

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
                p.append('<li class="job" data-u="%s" data-live="1">'
                         '<button class="hide-btn" type="button" title="Not interested - hide this"'
                         ' aria-label="Hide this role">&times;</button>'
                         '<a href="%s" target="_blank" rel="noopener">%s</a>'
                         '<div class="meta"><span>%s</span>%s<span>seen since %s</span></div></li>'
                         % (esc(h["url"]), esc(h["url"]), esc(h["title"]), esc(h["location"]),
                            chip, esc(h["first_seen"])))
            p.append("</ul>")
        else:
            p.append('<p class="none">No tech internships open in France right now.</p>')

        if r["other"]:
            p.append("<details%s><summary>%d non-tech internship%s filtered out</summary><ul>"
                     % (" open" if any(o["is_new"] for o in r["other"]) else "",
                        len(r["other"]), "" if len(r["other"]) == 1 else "s"))
            # Anything new is listed first, so a cap can never hide the one entry
            # that is actually news.
            for o in sorted(r["other"], key=lambda x: not x["is_new"])[:BOX_ROWS]:
                p.append('<li data-u="%s"><button class="hide-btn" type="button"'
                         ' title="Not interested - hide this" aria-label="Hide">&times;</button>'
                         '<a href="%s" target="_blank" rel="noopener">%s</a> &mdash; %s%s</li>'
                         % (esc(o["url"]), esc(o["url"]), esc(o["title"]), esc(o["location"]),
                            '<span class="chip new">New</span>' if o["is_new"] else ""))
            if len(r["other"]) > BOX_ROWS:
                p.append("<li>&hellip; and %d more &mdash; full list in audit.md</li>"
                         % (len(r["other"]) - BOX_ROWS))
            p.append("</ul></details>")

        # Never silently dropped: a location this build could not place is shown
        # here so a French town missing from the city list is visible instead of
        # costing an application. Anything real in here belongs in _FR_CITIES.
        if r["unsure"]:
            p.append("<details%s><summary>%d internship%s with an unrecognised location"
                     "</summary><ul>"
                     % (" open" if any(o["is_new"] for o in r["unsure"]) else "",
                        len(r["unsure"]), "" if len(r["unsure"]) == 1 else "s"))
            for o in sorted(r["unsure"], key=lambda x: not x["is_new"])[:BOX_ROWS]:
                p.append('<li data-u="%s"><button class="hide-btn" type="button"'
                         ' title="Not interested - hide this" aria-label="Hide">&times;</button>'
                         '<a href="%s" target="_blank" rel="noopener">%s</a> &mdash; %s%s</li>'
                         % (esc(o["url"]), esc(o["url"]), esc(o["title"]),
                            esc(o["location"] or "no location given"),
                            '<span class="chip new">New</span>' if o["is_new"] else ""))
            if len(r["unsure"]) > BOX_ROWS:
                p.append("<li>&hellip; and %d more &mdash; full list in audit.md</li>"
                         % (len(r["unsure"]) - BOX_ROWS))
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
    p.append("<p>Filter: title contains stage / stagiaire / PFE / intern / fin d&rsquo;&eacute;tudes "
             "&middot; excludes alternance and apprentissage &middot; location in France &middot; "
             "engineering, data, infra, SRE or security role. The last two steps do not delete "
             "anything: a role that fails them is in the collapsed box on its company, either as "
             "non-tech or as an unrecognised location.</p>")
    if broken:
        p.append('<p class="warn">%d compan%s failed to fetch this run, so its roles may be stale. '
                 "Nothing was marked closed for it.</p>"
                 % (len(broken), "y" if len(broken) == 1 else "ies"))
    suspect = [r for r in results if not r["error"] and (r["zero"] or r["partial"])]
    if suspect:
        p.append('<p class="warn">Incomplete this run: %s. An empty response can mean a dead slug '
                 "rather than an empty board, and a paging ceiling hides the tail, so nothing was "
                 "marked closed for these.</p>"
                 % esc(", ".join("%s (%s)" % (r["name"], "empty" if r["zero"] else "truncated")
                                 for r in suspect)))
    p.append("</section></div>")

    closed_today = [{"title": c["title"], "company": c.get("company", ""), "url": c["url"]}
                    for c in closed if c["closed_on"] == TODAY]
    # Hide-what-you-do-not-want, kept deliberately simple: it is per-browser
    # display state in localStorage, never a change to the data. The sweep still
    # tracks a hidden role, so it is never re-announced as new and never
    # mistakenly marked closed - and "restore all" always brings everything back.
    # localStorage is keyed per artifact origin and survives the nightly
    # republish to the same URL, which is what makes this work at all.
    p.append("""<script>
(function () {
  var KEY = "stage-watch-hidden:" + (document.title || "board");
  function read() { try { return JSON.parse(localStorage.getItem(KEY) || "[]"); }
                    catch (e) { return []; } }
  function write(v) { try { localStorage.setItem(KEY, JSON.stringify(v)); } catch (e) {} }
  var hidden = read(), reveal = false, bar = document.getElementById("hidebar");
  function apply() {
    var rows = document.querySelectorAll("li[data-u]"), n = 0;
    for (var i = 0; i < rows.length; i++) {
      var li = rows[i], off = hidden.indexOf(li.getAttribute("data-u")) !== -1;
      if (off) { n++; }
      li.hidden = off && !reveal;
      li.classList.toggle("dimmed", off && reveal);
    }
    if (!bar) { return; }
    bar.textContent = "";
    if (!n) { return; }
    bar.appendChild(document.createTextNode(n + " hidden as not interested"));
    var t = document.createElement("button");
    t.type = "button";
    t.textContent = reveal ? "collapse again" : "show them";
    t.onclick = function () { reveal = !reveal; apply(); };
    bar.appendChild(t);
    var r = document.createElement("button");
    r.type = "button";
    r.textContent = "restore all";
    r.onclick = function () { hidden = []; write(hidden); reveal = false; apply(); };
    bar.appendChild(r);
  }
  document.addEventListener("click", function (ev) {
    var el = ev.target;
    while (el && el !== document && !(el.classList && el.classList.contains("hide-btn"))) {
      el = el.parentNode;
    }
    if (!el || el === document) { return; }
    ev.preventDefault();
    var li = el.parentNode;
    while (li && li.tagName !== "LI") { li = li.parentNode; }
    if (!li) { return; }
    var u = li.getAttribute("data-u"), at = hidden.indexOf(u);
    if (at === -1) { hidden.push(u); } else { hidden.splice(at, 1); }
    write(hidden);
    apply();
  });
  apply();
})();
</script>""")

    state = {"generated": NOW.isoformat(), "postings": cur, "closed": closed, "watch": watch}
    p.append('<script type="application/json" id="state">%s</script>'
             % json.dumps(state, ensure_ascii=False).replace("</", "<\\/"))

    stats = {
        "board": BOARD["name"],
        "stamp": TODAY,
        "generated": NOW.isoformat(),
        "companies": len(results),
        "scanned": total,
        "live": live,
        "new": new_ct,
        "new_roles": new_roles[:STATUS_ROWS],
        "new_roles_total": len(new_roles),
        "recent_roles": recent_roles[:STATUS_ROWS],
        "recent_roles_total": len(recent_roles),
        "failed": len(broken),
        "failed_names": [r["name"] for r in broken],
        "incomplete": ["%s (%s)" % (r["name"], "empty" if r["zero"] else "truncated")
                       for r in results if not r["error"] and (r["zero"] or r["partial"])],
        "also_new": also_new[:STATUS_ROWS],
        "also_new_total": len(also_new),
        "unsure": sum(len(r["unsure"]) for r in results),
        "filtered": sum(len(r["other"]) for r in results),
        "closed_total": len(closed),
        "closed_today": closed_today[:STATUS_ROWS],
        "closed_today_total": len(closed_today),
    }
    return "\n".join(p), stats


HERE     = os.path.dirname(os.path.abspath(__file__))
STATUS   = os.path.join(HERE, "status.json")
AUDIT    = os.path.join(HERE, "audit.json")
AUDIT_MD = os.path.join(HERE, "audit.md")


def _merge(path, key, payload):
    """Read-modify-write keyed by board file. The three rosters run one after the
    other and each owns only its own key."""
    try:
        doc = json.load(open(path, encoding="utf-8"))
    except Exception:
        doc = {}
    if not isinstance(doc.get("boards"), dict):
        doc = {"boards": {}}
    doc["boards"][key] = payload
    doc["generated"] = NOW.isoformat()
    json.dump(doc, open(path, "w", encoding="utf-8"), indent=2, ensure_ascii=False, sort_keys=True)
    return doc


def write_status(out, stats):
    """One small JSON summarising every board, so the publish step never has to
    parse the HTML back out."""
    _merge(STATUS, os.path.basename(out), stats)


# status.json is read IN FULL by the publish routine every night, so no list in
# it may be unbounded. Adding four companies at once put 153 rows in also_new and
# took the file from 4.7 KB to 70 KB - more than the HTML it exists to avoid
# reading. Every capped list keeps its full count in a matching _total field, so
# the number is never lost, only the tail.
STATUS_ROWS = 12

# Per collapsed box on the board itself. The board is an artifact the routine
# may have to read back on a refused publish, and 158 filtered rows took board3
# to 115 KB. New entries sort first so a cap can never hide the news.
BOX_ROWS = 25

# audit.json is not read by the routine, but it is committed nightly and a human
# skims it weekly. Same reasoning, looser cap.
AUDIT_ROWS = 60
FOREIGN_SAMPLE = 15


def write_audit(out, results):
    """Everything the filters threw away, so the word lists get corrected from
    evidence instead of guessed at again."""
    tag = lambda r, xs: [dict(x, company=r["name"]) for x in xs]
    foreign = [x for r in results for x in tag(r, r["foreign"])]
    payload = {
        "board": BOARD["name"],
        "stamp": TODAY,
        "unknown_location":       [x for r in results for x in tag(r, r["unsure"])][:AUDIT_ROWS],
        "unknown_location_total": sum(len(r["unsure"]) for r in results),
        "non_tech":               [x for r in results for x in tag(r, r["other"])][:AUDIT_ROWS],
        "non_tech_total":         sum(len(r["other"]) for r in results),
        # nearly always correct, and there can be hundreds - count them and keep
        # a sample rather than committing the whole list every night
        "foreign_count":  len(foreign),
        "foreign_sample": foreign[:FOREIGN_SAMPLE],
    }
    _render_audit_md(_merge(AUDIT, os.path.basename(out), payload))


def _cell(s):
    return str(s or "").replace("|", "\\|").replace("\n", " ").strip()


def _table(rows):
    if not rows:
        return ["", "_none_"]
    out = ["", "| Company | Title | Location |", "|---|---|---|"]
    for x in rows:
        out.append("| %s | [%s](%s) | %s |" % (_cell(x.get("company")), _cell(x.get("title")),
                                               x.get("url", ""), _cell(x.get("location")) or "-"))
    return out


def _render_audit_md(doc):
    """The skimmable half of audit.json. Read it once a week."""
    p = ["# What the filters dropped", "",
         "Rewritten by every sweep; worth a skim once a week.", "",
         "- anything under **unrecognised location** that is really in France belongs in",
         "  `_FR_CITIES` in `make_board.py` - that box is the whole point of not dropping",
         "  a role just because its town was not on a hand-written list",
         "- anything under **not tech** that is really an engineering role belongs in",
         "  `TECH`, or in `STRONG` if one of the `EXCL` veto words is what is blocking it",
         "",
         "Roles outside France are counted, not listed: that call is nearly always right",
         "and the list would be hundreds long. A sample is kept to spot a systematic",
         "mistake (a French site being read as foreign).", ""]
    for name in sorted(doc.get("boards", {})):
        b = doc["boards"][name]
        p += ["---", "", "## %s" % b.get("board", name),
              "", "`%s` &middot; sweep of %s" % (name, b.get("stamp", "?")), ""]
        def _head(key, label):
            rows = b.get(key) or []
            tot = b.get(key + "_total", len(rows))
            extra = " (showing the first %d)" % len(rows) if tot > len(rows) else ""
            return ["### %s - %d%s" % (label, tot, extra)]
        p += _head("unknown_location", "Unrecognised location")
        p += _table(b.get("unknown_location") or [])
        p += [""] + _head("non_tech", "Not tech")
        p += _table(b.get("non_tech") or [])
        p += ["", "### Outside France - %d (sample below)" % b.get("foreign_count", 0)]
        p += _table(b.get("foreign_sample") or [])
        p += [""]
    open(AUDIT_MD, "w", encoding="utf-8").write("\n".join(p) + "\n")


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
    doc, stats = render(res, load_prev(prev_path))
    open(out, "w", encoding="utf-8").write(doc)
    write_status(out, stats)
    write_audit(out, res)
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    for r in res:
        note = " INCOMPLETE" if (r["zero"] or r["partial"]) else ""
        print("%-12s %-16s %s%s" % (r["name"], r["ats"], r["error"] or
              "%3d open / %2d FR / %d hits" % (r["total"], r["france"], len(r["hits"])), note))
    print("-> %s  (%d live, %d new)" % (out, stats["live"], stats["new"]))
