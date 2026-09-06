#!/usr/bin/env python3
"""Stage Watch - build the internship board from ATS APIs.

  python make_board.py                      -> board.html (fresh, no diff)
  python make_board.py --prev prev.html     -> board.html, diffed against the
                                               previous artifact for NEW/CLOSED

Self-contained on purpose: the nightly cloud run has no access to any other
file, so config + fetchers + template all live here.
"""
import json, os, re, sys, html, http.cookiejar, urllib.error, urllib.parse, urllib.request, time
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
    # --- added 2026-09-06. Every endpoint below was read off a live response by
    # probe_new.py on a runner that day; see that file for the exact request and
    # NEW-SOURCES.md for what each one answered with. The rule has not changed:
    # nothing goes in this list that has not been probed.
    {"name": "GitHub",       "ats": "phenom",
     "api": "https://www.github.careers/api/jobs", "keywords": ("",), "pages": 40,
     "careers": "https://www.github.careers/"},
    # This replaces the "GitHub: iCIMS, no public API" note that used to sit in
    # NO_API. It IS iCIMS underneath - data.ats_code says so - but Phenom sits in
    # front of it with a JSON board. keywords="" pages the whole thing: a
    # keywords=intern search answered 200 with totalCount 0 while the board was
    # live, so on a board this small asking for everything is safer and cheaper.
    {"name": "Atlassian",    "ats": "atlassian",
     "careers": "https://www.atlassian.com/company/careers/all-jobs"},
    {"name": "Dynatrace",    "ats": "coveo",
     "api": "https://www.dynatrace.com/api/coveo/search/",
     "careers": "https://careers.dynatrace.com/"},
    {"name": "OpenAI",       "ats": "ashby", "slug": "openai",
     "careers": "https://openai.com/careers/search/"},
    {"name": "Anthropic",    "ats": "greenhouse", "slug": "anthropic",
     "careers": "https://www.anthropic.com/careers"},
    {"name": "Stripe",       "ats": "greenhouse", "slug": "stripe",
     "careers": "https://stripe.com/jobs/search"},
    {"name": "Palantir",     "ats": "lever", "slug": "palantir",
     "careers": "https://www.palantir.com/careers/"},
    # The capital N is part of the SmartRecruiters slug, like SopraSteria1.
    {"name": "ServiceNow",   "ats": "smartrecruiters", "slug": "ServiceNow",
     "careers": "https://careers.servicenow.com/"},
    {"name": "IBM",          "ats": "ibm",
     "careers": "https://www.ibm.com/careers/search"},
    {"name": "Oracle",       "ats": "oracle_cx",
     "host": "https://eeho.fa.us2.oraclecloud.com",
     "careers": "https://careers.oracle.com/jobs/"},
    {"name": "SAP",          "ats": "sfhtml", "pages": 12,
     "base": "https://jobs.sap.com",
     "list": "https://jobs.sap.com/tile-search-results/?q=%s&locationsearch=France&startrow=%d",
     "careers": "https://jobs.sap.com/"},
    {"name": "Microsoft",    "ats": "eightfold",
     "host": "https://apply.careers.microsoft.com", "domain": "microsoft.com",
     "careers": "https://careers.microsoft.com/"},
    {"name": "Amazon / AWS", "ats": "amazon",
     "careers": "https://www.amazon.jobs/en/search?base_query=intern&loc_query=France"},
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
    # Probed live 2026-09-04, totalFound on each: SopraSteria1 1969 (884 France),
    # alten 1125 (608 France), Ubisoft2 281 (90 France), lever/veepee 73 (16
    # France). The capital letters and the trailing digits in the SmartRecruiters
    # slugs are part of the slug - "soprasteria" and "ubisoft" both 404.
    {"name": "Sopra Steria",     "ats": "smartrecruiters", "slug": "SopraSteria1",
     "careers": "https://www.soprasteria.com/careers"},
    {"name": "Alten",            "ats": "smartrecruiters", "slug": "alten",
     "careers": "https://www.alten.fr/nos-offres/"},
    {"name": "Ubisoft",          "ats": "smartrecruiters", "slug": "Ubisoft2",
     "careers": "https://www.ubisoft.com/en-us/company/careers"},
    {"name": "Veepee",           "ats": "lever", "slug": "veepee",
     "careers": "https://careers.veepee.com/"},
    # iCIMS, 20 cards a page, ~25 pages. pr is 0-based and in_iframe=1 is what
    # returns the bare list instead of the chrome around it.
    {"name": "Expleo",           "ats": "icims", "pages": 35,
     "list": "https://expleo-jobs-fr-fr.icims.com/jobs/search?pr=%d&in_iframe=1",
     "careers": "https://expleo-jobs-fr-fr.icims.com/jobs/search?in_iframe=1"},
    # --- added 2026-09-06, probed live by probe_new.py. These four are not
    # French companies, but each runs a large French engineering site - OVHcloud
    # is Roubaix/Croix/Toulouse outright, Nokia is Paris-Saclay and Lannion,
    # Ericsson is Massy, Siemens is Saint-Denis - so they belong with the French
    # market rather than on the defence/silicon board.
    {"name": "OVHcloud",         "ats": "sfhtml", "pages": 10,
     "base": "https://careers.ovhcloud.com",
     # This instance has no /tile-search-results/ (404) - the /search/ page
     # carries the same job-tile markup, so the fetcher reads that instead.
     "list": "https://careers.ovhcloud.com/search/?q=%s&locale=fr_FR&startrow=%d",
     "careers": "https://careers.ovhcloud.com/search/"},
    {"name": "Nokia",            "ats": "oracle_cx",
     "host": "https://fa-evmr-saasfaprod1.fa.ocs.oraclecloud.com",
     # jobs.nokia.com/hcmRestApi/... serves the SPA shell, not the API; the
     # oraclecloud host is the one that answers.
     "careers": "https://jobs.nokia.com/"},
    {"name": "Ericsson",         "ats": "eightfold",
     "host": "https://jobs.ericsson.com", "domain": "ericsson.com",
     # jobs.ericsson.com/search/ (the old SuccessFactors board) now redirects to
     # a Microsoft login - do not go back to it.
     "careers": "https://jobs.ericsson.com/"},
    {"name": "Siemens",          "ats": "avature", "pages": 8,
     "base": "https://jobs.siemens.com",
     # Avature puts the keyword in the PATH, not in a query parameter.
     "list": "https://jobs.siemens.com/en_US/externaljobs/SearchJobs/%s?listFilterMode=1&page=%d",
     "careers": "https://jobs.siemens.com/en_US/externaljobs/SearchJobs"},
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
    # Societe Generale reads its OWN board (see f_sgcareers). WTTJ carried 95 SG
    # postings against 1083 on the real board - an 11x under-report - so the
    # aggregator was costing roles, not saving them. The old note here said SG's
    # Taleo layer needed a PORTAL_ID: that was a dead end and is closed. There is
    # no searchjobs call; careers.societegenerale.com has a JSON API of its own.
    {"name": "Societe Generale", "ats": "sgcareers",
     "careers": "https://careers.societegenerale.com/rechercher"},
    # BNP reads its own board too - see f_bnp. The old note here said its careers
    # site 403s a datacenter IP; that was measured against the wrong thing. The
    # 403 is a missing-header check on the public board, and the applicant portal
    # (bwelcome.hr.bnpparibas) is the auth-gated host that has no way in.
    {"name": "BNP Paribas",     "ats": "bnp", "pages": 45,
     "careers": "https://group.bnpparibas/en/careers/all-job-offers"},
    # Credit Agricole and Natixis stay on Welcome to the Jungle: neither has a
    # public feed of its own. Confirmed 2026-09-04, both returning real stages.
    # groupe-credit-agricole covers the group including CIB. jobs.ca-cib.com has
    # a working stage-filtered RSS feed, but it is capped at 20 items and carries
    # no location, so a role dropping off the end would look closed - see NO_API3.
    {"name": "Credit Agricole", "ats": "wttj", "slug": "groupe-credit-agricole",
     "careers": "https://www.welcometothejungle.com/fr/companies/groupe-credit-agricole/jobs"},
    {"name": "Natixis",         "ats": "wttj", "slug": "natixis",
     "careers": "https://www.welcometothejungle.com/fr/companies/natixis/jobs"},
    # Amundi needs its own fetcher rather than riding on Credit Agricole: it is a
    # separate Talentsoft tenant (jobs.amundi.com, mirrored at
    # casa-amundi-recrute.talent-soft.com) that the CA sources do not cover. 78
    # offers, 50 a page, and 30 of them are stages - the highest stage density of
    # anything on these three boards. LCID=1036 is French; the RSS the tenant
    # advertises 404s, so the list pages are the way in.
    {"name": "Amundi",          "ats": "talentsoft", "pages": 8,
     "base": "https://jobs.amundi.com",
     "list": "https://jobs.amundi.com/offre-de-emploi/liste-toutes-offres.aspx?page=%d&LCID=1036",
     "careers": "https://jobs.amundi.com/offre-de-emploi/liste-toutes-offres.aspx"},
    # Same Talentsoft layout, different field order in the card - see
    # f_talentsoft. 55 offers, 10 a page.
    {"name": "Dassault Aviation", "ats": "talentsoft", "pages": 12,
     "base": "https://dassault-aviation-cand.talent-soft.com",
     "list": "https://dassault-aviation-cand.talent-soft.com/offre-de-emploi/liste-offres.aspx?page=%d",
     "careers": "https://dassault-aviation-cand.talent-soft.com/offre-de-emploi/liste-offres.aspx"},
    # Gestmax (Kioskemploi). 20 rows a page over 24 pages; the site is MBDA
    # France, so nothing on it is foreign.
    {"name": "MBDA",            "ats": "gestmax", "pages": 30,
     "list": "https://mbda.gestmax.fr/search/index/page/%d",
     "careers": "https://mbda.gestmax.fr/search/index/page/1"},
    # Jane Street and IMC have working boards but no French office, so they will
    # normally show 0. Kept because a Paris desk would appear here immediately.
    {"name": "Jane Street", "ats": "greenhouse", "slug": "janestreet",
     "careers": "https://www.janestreet.com/join-jane-street/"},
    {"name": "IMC",         "ats": "greenhouse", "slug": "imc",
     "careers": "https://careers.imc.com/"},
    # --- added 2026-09-06, probed live by probe_new.py ----------------------
    # Two groups arrive here at once. The trading floors and banks are the
    # obvious fit; the silicon and enterprise-hardware companies are here
    # because they are the same kind of employer as the defence and aerospace
    # firms this board already carries - large engineering sites, long
    # internships - and because putting sixteen more companies on batch 1 would
    # have made one board twice the size of the other two.
    {"name": "Goldman Sachs", "ats": "gs", "site": "https://higher.gs.com",
     "careers": "https://higher.gs.com/roles"},
    {"name": "Morgan Stanley", "ats": "eightfold",
     "host": "https://morganstanley.eightfold.ai", "domain": "morganstanley.com",
     "careers": "https://morganstanley.eightfold.ai/careers"},
    {"name": "J.P. Morgan",   "ats": "oracle_cx", "host": "https://jpmc.fa.oraclecloud.com",
     "careers": "https://careers.jpmorgan.com/global/en/students/programs"},
    # This tenant is on the OLDER Eightfold API: /api/pcsx/search answers 403
    # here, /api/apply/v2/jobs answers with the board.
    {"name": "Millennium",    "ats": "eightfold_v2", "host": "https://career.mlp.com",
     "domain": "mlp.com", "careers": "https://career.mlp.com/"},
    {"name": "Optiver",       "ats": "greenhouse", "slug": "optiver",
     "careers": "https://optiver.com/working-at-optiver/career-opportunities/"},
    {"name": "Intel",         "ats": "workday", "tenant": "intel", "wd": "wd1",
     "site": "External", "big": True, "careers": "https://jobs.intel.com/"},
    {"name": "NVIDIA",        "ats": "workday", "tenant": "nvidia", "wd": "wd5",
     "site": "NVIDIAExternalCareerSite", "big": True,
     "careers": "https://www.nvidia.com/en-us/about-nvidia/careers/"},
    # VMware roles live on this board now - there is no separate VMware feed.
    # The site slug must be External_Career; External and Careers both 404.
    {"name": "Broadcom",      "ats": "workday", "tenant": "broadcom", "wd": "wd1",
     "site": "External_Career", "big": True, "careers": "https://www.broadcom.com/company/careers"},
    # amd.wd1.myworkdayjobs.com does not exist - AMD left Workday for Phenom.
    {"name": "AMD",           "ats": "phenom", "api": "https://careers.amd.com/api/jobs",
     "pages": 12, "careers": "https://careers.amd.com/"},
    {"name": "Qualcomm",      "ats": "eightfold", "host": "https://careers.qualcomm.com",
     "domain": "qualcomm.com", "careers": "https://careers.qualcomm.com/careers"},
    {"name": "Arm",           "ats": "radancy", "pages": 8,
     "base": "https://careers.arm.com",
     "careers": "https://careers.arm.com/search-jobs"},
    {"name": "Dell",          "ats": "oracle_cx",
     "host": "https://enterpriseplatform.dell.com", "careers": "https://jobs.dell.com/"},
    # /api/jobs answers 500 on these two; /widgets is the door their own pages
    # use. Each tenant needs its own lang/country in the body.
    {"name": "HPE",           "ats": "phenom_widget", "api": "https://careers.hpe.com/widgets",
     "careers": "https://careers.hpe.com/us/en/search-results"},
    {"name": "Cisco",         "ats": "phenom_widget", "api": "https://careers.cisco.com/widgets",
     "body": {"lang": "en_global", "country": "global",
              "all_fields": ["country", "state", "city", "category"]},
     "careers": "https://jobs.cisco.com/jobs/SearchJobs"},
    {"name": "HSBC / CCF",    "ats": "avature", "pages": 8,
     "base": "https://mycareer.hsbc.com",
     "list": "https://mycareer.hsbc.com/en_GB/external/SearchJobs/%s?listFilterMode=1&page=%d",
     "careers": "https://mycareer.hsbc.com/en_GB/external/SearchJobs"},
]

# Sources probed 2026-09-04 and deliberately NOT adopted, with the reason - so the
# next person does not spend a morning rediscovering them:
#   jobs.ca-cib.com RSS  Talentsoft, stage-filtered, works. Capped at 20 items and
#                        carries no location; the JobCountry=79 facet is ignored.
#                        A capped feed makes a role falling off the end look
#                        CLOSED, and Credit Agricole is covered via WTTJ anyway.
#   group.bnpparibas     server-rendered and complete, but 403s a datacenter IP.
#                        Works from a browser, not from the runner. BNP via WTTJ.
#   socgen.taleo.net     real ATS layer, but there is no searchjobs call to make
#                        and the PORTAL_ID hunt was chasing something that does
#                        not exist. Closed: SG is on its own API now, see
#                        f_sgcareers. Do not reopen this.
#   m.careers.
#     societegenerale.com  robots.txt blocks it. The DESKTOP host does not:
#                        careers.societegenerale.com/robots.txt disallows only
#                        /search/ and /search?, sets no crawl-delay, and leaves
#                        /rechercher and /search-proxy.php open. Both endpoints
#                        f_sgcareers uses are permitted; the mobile host is not.
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
    # These two are NOT "no API found" - both were located and answered. They are
    # excluded because they have no French office, which is the same test that
    # kept Jane Street and IMC in (working board, no France yet) and wrote off
    # Hudson River Trading and Optiver.
    ("XTX Markets",        "greenhouse/xtxmarketstechnologies answers 200 with 10 real jobs, but every "
                           "one is London, Singapore or New York - zero France. Endpoint recorded so "
                           "nobody re-probes it: boards-api.greenhouse.io/v1/boards/xtxmarketstechnologies/jobs"),
    ("DRW",                "no public JSON board; drw.com/work-at-drw/listings is ServiceNow-backed. The "
                           "office list it renders is CA, HK, IL, NL, SG, UK, US - no France - so even a "
                           "working feed would show 0"),
    ("Naval Group",        "naval-group.com/fr/nous-rejoindre answers 200 from a runner but serves a "
                           "JS anti-bot challenge, not the board: 242839 bytes of packed script, empty "
                           "<title>, zero anchors, and byte-for-byte identical with and without the "
                           "contractType filter. Same class of block as BNP's careers site. The filters "
                           "are real and recorded for the day it is reachable - contractType[]=2463 "
                           "Stagiaire, 33228 Alternance, 2461 CDI, 2460 CDD, 2464 VIE, plus keywords=, "
                           "country=, city=, offerFamilyCategory= - but only 3 stages were live, so this "
                           "is a small loss. Do not re-probe it with plain HTTP; it needs a browser"),
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
    "salaunes|salon-de-provence|la ciotat|sainte-tulle|manosque|cadarache|le barp|biscarrosse|"
    # added with MBDA, Dassault Aviation, Amundi and Expleo - every one of these
    # is a real site of theirs that where() was answering "unknown" for
    "le plessis[- ]robinson|plessis[- ]robinson|selles[- ]saint[- ]denis|bourges|"
    "biarritz|anglet|martignas|martignas[- ]sur[- ]jalle|seclin|argonay|cazaux|"
    "saint[- ]vulbas|"
    "chateauroux|ch[âa]?teaudun|deols|saint-cloud|le plessis|fontenay-sous-bois|"
    "fontenay|courbevoie|la garenne|bois-colombes|villepinte|noisy-le-grand|"
    "champs-sur-marne|torcy|bussy|serris|coignieres|maurepas|elancourt|voisins"
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
    # from the audit: 22 of board 3's 23 unplaced roles were these
    "luxembourg|kirchberg|howald|jersey|guernsey|st helier|saint helier|senegal|"
    "s[ée]n[ée]gal|dakar|"
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
_FOREIGN_ISO = ("it|nl|de|es|pt|be|lu|ch|at|pl|cz|sk|hu|ro|bg|hr|si|ee|lv|lt|gr|"
                "se|no|dk|fi|ie|uk|gb|us|ca|br|mx|ar|cl|co|pe|in|cn|jp|kr|sg|hk|tw|"
                "au|nz|za|ma|tn|dz|sn|eg|ae|qa|sa|il|tr|ua|vn|th|my|id|ph")
NOT_FR_ISO = re.compile(r",\s*(?:%s)\s*$" % _FOREIGN_ISO, re.I)
NOT_FR_CS = re.compile(r",\s*(A[KLRZ]|C[AOT]|D[CE]|FL|GA|HI|I[ADLN]|K[SY]|LA|M[ADEINOST]|"
                       r"N[CDEHJMVY]|O[HKR]|P[AR]|RI|S[CD]|T[NX]|UT|V[AT]|W[AIVY])\b"
                       r"|\b(US|USA|U\.S\.|UK|EMEA|APAC|LATAM|NAMER|AMER|ANZ|DACH|BENELUX|MENA)\b")


def where(blob):
    """'fr' | 'foreign' | 'unknown'. France wins ties: a posting listed for both
    Paris and London is a Paris posting as far as this board is concerned."""
    if LOC.search(blob):
        return "fr"
    if NOT_FR.search(blob) or NOT_FR_CS.search(blob) or NOT_FR_ISO.search(blob.strip()):
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
    r"observabilit|monitoring|blockchain|cryptograph|statistiq|analytics|"
    r"business analyst|analyste m[ée]tier)", re.I)

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
# A bare "Mozilla/5.0" is a bot signature: BNP 403s it outright, and several
# of the 2026-09-06 batch (Arm, Amazon, the Phenom sites) were only ever probed
# with a full browser string. Send the same one everywhere.
UA    = {"User-Agent": ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"),
         "Accept": "application/json,text/plain,*/*"}


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
        cat = j.get("categories") or {}
        loc = cat.get("location", "") or ""
        # commitment is Lever's own contract label ("Internship", "Stage", "CDI")
        out.append((j.get("text", ""), loc, j.get("hostedUrl", ""), loc,
                    _contract(cat.get("commitment"))))
    return out


def f_workable(c):
    d = get("https://apply.workable.com/api/v1/widget/accounts/%s" % c["slug"])
    out = []
    for j in d.get("jobs", []):
        loc = ", ".join(x for x in [j.get("city"), j.get("country")] if x)
        out.append((j.get("title", ""), loc, j.get("url", ""),
                    _fr(loc, j.get("country"), j.get("country_code"))))
    return out


SR_MAX = 4000               # Sopra Steria is the largest board here at ~1970


def f_smartrecruiters(c):
    # Paged whole rather than narrowed with the API's own &country=fr. That
    # filter works (884 of Sopra Steria's 1969, 608 of Alten's 1125) and would
    # save ~15 requests a day, but a server-side location filter can only ever
    # DELETE roles, and silently: a posting whose country field is blank or
    # mistyped disappears with nothing to show it existed. where() makes that
    # same call locally and puts what it cannot place in a visible box instead.
    out, off = [], 0
    while True:
        d = get("https://api.smartrecruiters.com/v1/companies/%s/postings?limit=100&offset=%d" % (c["slug"], off))
        for j in d.get("content", []):
            lo = j.get("location") or {}
            loc = ", ".join(x for x in [lo.get("city"), lo.get("country")] if x)
            out.append((j.get("name", ""), loc,
                        "https://jobs.smartrecruiters.com/%s/%s" % (c["slug"], j.get("id", "")),
                        _fr(loc, lo.get("country"), lo.get("countryCode")),
                        _contract((j.get("typeOfEmployment") or {}).get("label"))))
        off += 100
        total = d.get("totalFound", 0)
        if off >= SR_MAX and off < total:
            PARTIAL.add(c["name"])
            return out
        if off >= total:
            return out


INTERN_SUBTYPE = re.compile(r"intern|trainee|student|stage|stagiaire", re.I)
APPRENTICE_SUBTYPE = re.compile(r"apprentice|apprenti|alternan", re.I)


def _contract(label):
    """An ATS's OWN contract label -> 'intern' | 'alt' | None.

    Some boards say what a posting is - Societe Generale's sourcestr8,
    SmartRecruiters' typeOfEmployment, Lever's categories.commitment - and a
    fetcher may pass that through as a fifth element of its row. scan() lets it
    OVERRIDE the title test, because the title is wrong in both directions:
    Societe Generale files "Software developper" and "Developpeur Front React"
    under INTERNSHIP with nothing in the title to say so (3 of its 5 live tech
    stages), and Thales titles an apprenticeship "STAGE - ...".

    None means "this board did not say", and the title test runs as before -
    so a label this does not recognise costs nothing.
    """
    text = str(label or "").strip()
    if not text:
        return None
    if APPRENTICE_SUBTYPE.search(text):
        return "alt"
    if INTERN_SUBTYPE.search(text):
        return "intern"
    return None


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


# Societe Generale. Its careers site is a Drupal front over a Sinequa ("CES")
# search service at api.socgen.com, reached through a passthrough on the site's
# own host. Two calls, both permitted by careers.societegenerale.com/robots.txt
# (which disallows only /search/ and /search?, and sets no crawl-delay - the
# robots block people run into is on m.careers.societegenerale.com, a different
# host this code never touches):
#
#   1. GET /rechercher            - sets the session cookie and carries the CSRF
#                                   token in its drupalSettings JSON blob
#      GET /sg-careers-offers/get-token
#                                 - with that cookie + token, returns a JWT
#                                   (OAuth2 client_credentials, ~600s)
#   2. POST /search-proxy.php     - a pure passthrough: it moves X-Proxy-URL into
#                                   the real request URL. The JWT goes in
#                                   Authorization-API, NOT Authorization.
#
# This replaced a Welcome to the Jungle feed that showed 95 of SG's 1083
# postings. Polled once a day by the sweep, which is what "politely" means here.
SG_HOST = "https://careers.societegenerale.com"
SG_API  = ("https://api.socgen.com/business-support/it-for-it-support/"
           "cognitive-service-knowledge/api/v1/search-profile")
SG_PAGE = 100
SG_MAX  = 20                # pages; 2000 is far past the whole board (~1083)

# Field names are SG's, from the site's own global-quantum.js:
#   sourcestr6 "job"|"page"   sourcestr4  reference     sourcestr7  location text
#   sourcecsv1 location ids   sourcestr8  contract      sourcestr10 job family
#   sourcestr12 <ref>-<lang>  sourcedatetime1 published  url1        offer URL
# Contract ids: INTERNSHIP Stage - APPRENTICESHIP Alternance - STANDARD CDI -
# TEMPORARY_WORK CDD - COOPERATIVE V.I.E - GRADUATE_JOB - SUMMER_JOB - EXPERIENCED.


def _sg_field(doc, name):
    """Sinequa returns metadata flat on the doc; some profiles nest it."""
    if name in doc:
        return doc[name]
    for key in ("metadata", "Metadata", "columns", "Columns"):
        sub = doc.get(key)
        if isinstance(sub, dict) and name in sub:
            return sub[name]
    return None


def _sg_token(opener):
    req = urllib.request.Request(SG_HOST + "/rechercher", headers={
        "User-Agent": UA["User-Agent"],
        "Accept": "text/html,application/xhtml+xml"})
    with opener.open(req, timeout=40) as r:
        page = r.read().decode("utf-8", "replace")
    m = re.search(r'"csrfToken"\s*:\s*"([^"]+)"', page)
    if not m:
        raise RuntimeError("no csrfToken in /rechercher - the page shape changed")
    req = urllib.request.Request(SG_HOST + "/sg-careers-offers/get-token", headers={
        "User-Agent": UA["User-Agent"],
        "Accept": "application/json",
        "X-Requested-With": "XMLHttpRequest",
        "X-CSRF-Token": m.group(1)})
    with opener.open(req, timeout=40) as r:
        tok = (json.load(r) or {}).get("token")
    if not tok:
        raise RuntimeError("get-token returned no token")
    return tok


def f_sgcareers(c):
    # One cookie jar for the whole fetch: /rechercher sets the session that
    # get-token checks, and a fresh opener per call would fail that check.
    opener = urllib.request.build_opener(
        urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
    token = _sg_token(opener)
    out, frm, seen = [], 0, set()
    for _ in range(SG_MAX):
        # Filtered to internships in France, but NOT to a job family. The family
        # ids exist (BJ725 IT, JN482 Innovation/Digital/Projet) and would cut 118
        # French internships to 14, but that is the same call is_tech() makes -
        # and is_tech shows what it rejected in a box on the card, where a
        # mistake costs a glance. A server-side family filter just deletes.
        body = {"profile": "ces_profile_sgcareers",
                "query": {"advanced": [
                    {"type": "simple", "name": "sourcestr6", "op": "eq", "value": "job"},
                    {"type": "multi", "name": "sourcestr8", "op": "eq",
                     "values": ["INTERNSHIP"]},
                    {"type": "multi", "name": "sourcecsv1", "op": "eq",
                     "values": ["FRA"]}],
                    "skipCount": SG_PAGE, "skipFrom": frm,
                    "sort": "sourcedatetime1.desc"},
                "lang": "fr", "responseType": "SearchResult"}
        req = urllib.request.Request(
            SG_HOST + "/search-proxy.php", data=json.dumps(body).encode(),
            headers={"Content-Type": "application/json",
                     "Accept": "application/json",
                     "User-Agent": UA["User-Agent"],
                     "Authorization-API": "Bearer " + token,
                     "X-Proxy-URL": SG_API})
        with opener.open(req, timeout=60) as r:
            d = json.load(r)
        docs = ((d.get("Result") or {}).get("Docs")) or []
        for doc in docs:
            if not isinstance(doc, dict):
                continue
            # The three filters above are server-side, so check they held. A
            # filter that quietly stopped narrowing would put SG's 1083 CDIs on
            # an internship board.
            kind = _sg_field(doc, "sourcestr6")
            if kind and str(kind) != "job":
                continue
            title = str(_sg_field(doc, "title") or "").strip()
            url   = str(_sg_field(doc, "url1") or "").strip()
            if not title or not url:
                continue
            url = urllib.parse.urljoin(SG_HOST, url)
            if url in seen:
                continue
            seen.add(url)
            loc = str(_sg_field(doc, "sourcestr7") or "").strip()
            codes = _sg_field(doc, "sourcecsv1") or ""
            if isinstance(codes, (list, tuple)):
                codes = ";".join(str(x) for x in codes)
            # sourcecsv1 is "<City>;<Country>" ids - the FRA token is the most
            # reliable France signal on the whole record, so feed it to _fr()
            # rather than hoping the town is in _FR_CITIES (Fontenay-sous-Bois,
            # La Defense and Lille's spellings are not all in there).
            out.append((title, loc, url,
                        _fr(loc, *re.split(r"[;,\s]+", str(codes))),
                        _contract(_sg_field(doc, "sourcestr8"))))
        frm += SG_PAGE
        total = int(d.get("TotalCount") or 0)
        if not docs or frm >= total:
            break
        time.sleep(0.3)
    else:
        # Ran out of pages before running out of results: shown, nothing closed.
        PARTIAL.add(c["name"])
    return out


# ------------------------------------------- the 2026-09-06 batch ----------
# Nine more ATSs. Every field name below was read off a live payload by
# probe_new.py on 2026-09-06 - run that from Actions before changing any of
# them, exactly as with the HTML boards. The pattern to watch for here is the
# SEARCH-SCOPED board: IBM, Phenom, Eightfold, Oracle CX and Amazon are all far
# too large to page whole, so each is fetched as the union of a few keyword
# searches. That is the same trade Thales and Airbus already make in f_workday:
# a role whose title carries none of the keywords is invisible to us, which is
# why the keyword lists below include the French words as well as the English.


def _rows_from(seen, out, title, loc, url, blob, contract=None):
    """Append one row, de-duplicated by url. Every fetcher below merges several
    searches, and the same posting comes back under more than one of them."""
    if not title or not url or url in seen:
        return 0
    seen.add(url)
    out.append((title, loc, url, blob, contract))
    return 1


# --- IBM (custom Elasticsearch behind www-api.ibm.com) ----------------------
# POST with an Elasticsearch query. Two things are load-bearing and neither is
# guessable: the _source list (with no _source the hits come back as
# _id/_index/_score and nothing else) and appId/scopes, which select the careers
# index. _source.url is the posting's own link, so nothing is constructed.
#   field_keyword_05  country          field_keyword_19  "Chicago, US"
#   field_keyword_18  contract label   field_keyword_08  job family
# HashiCorp is IBM now and its roles are on this same index, which is why
# "hashicorp" is one of the queries rather than a separate company.
IBM_URL = "https://www-api.ibm.com/search/api/v2"
IBM_SOURCE = ["_id", "title", "url", "field_keyword_05", "field_keyword_08",
              "field_keyword_17", "field_keyword_18", "field_keyword_19",
              "field_text_01"]
IBM_PAGE = 50
IBM_MAX = 400


def f_ibm(c):
    out, seen = [], set()
    for query in c.get("queries", ("intern", "internship", "stage", "stagiaire",
                                   "apprentice france", "hashicorp")):
        frm = 0
        while frm < IBM_MAX:
            body = {"appId": "careers", "scopes": ["careers2"],
                    "size": IBM_PAGE, "from": frm, "sort": [{"_score": "desc"}],
                    "_source": IBM_SOURCE,
                    "query": {"bool": {"must": [{"simple_query_string": {
                        "query": query,
                        "fields": ["keywords^1", "body^1", "url^2", "description^2",
                                   "title^3", "field_text_01"]}}]}}}
            d = get(IBM_URL, body)
            hits = ((d.get("hits") or {}).get("hits")) or []
            for h in hits:
                s = h.get("_source") or {}
                loc = s.get("field_keyword_19") or s.get("field_keyword_05") or ""
                _rows_from(seen, out, s.get("title", ""), loc, s.get("url", ""),
                           " ".join(x for x in [loc, s.get("field_keyword_05")] if x),
                           _contract(s.get("field_keyword_18")))
            frm += IBM_PAGE
            total = (((d.get("hits") or {}).get("total")) or {}).get("value") or 0
            if len(hits) < IBM_PAGE or frm >= total:
                break
            time.sleep(0.2)
    return out


# --- Phenom People, the /api/jobs flavour (AMD, GitHub) ---------------------
# jobs[] is a list of {"data": {...}} envelopes, 10 to a page. The link to show
# is data.meta_data.canonical_url: data.apply_url points at the ATS behind the
# site (iCIMS for both of these), which is a login page, not a posting.
# A company with an empty keyword in its list is paged whole - github.careers
# answered keywords=intern with totalCount 0 while carrying a real board, so on
# a small board asking for everything is both safer and cheaper.
PHENOM_PAGE = 10


def f_phenom(c):
    out, seen = [], set()
    for kw in c.get("keywords", ("intern", "internship", "stage", "stagiaire")):
        for page in range(1, c.get("pages", 12) + 1):
            d = get("%s?page=%d%s&sortBy=relevance&descending=false&internal=false"
                    % (c["api"], page,
                       "&keywords=%s" % urllib.parse.quote(kw) if kw else ""))
            rows = d.get("jobs") or []
            fresh = 0
            for j in rows:
                data = j.get("data") if isinstance(j.get("data"), dict) else j
                loc = (data.get("full_location") or data.get("short_location")
                       or data.get("location_name") or "")
                fresh += _rows_from(
                    seen, out, data.get("title", ""), loc,
                    (data.get("meta_data") or {}).get("canonical_url") or "",
                    _fr(loc, data.get("country"), data.get("country_code")))
            if len(rows) < PHENOM_PAGE or not fresh:
                break
            time.sleep(0.3)
    return out


# --- Phenom People, the /widgets flavour (HPE, Cisco) -----------------------
# Same vendor, different door: /api/jobs answers 500 on these two and /widgets
# is what their own pages call. The body is the site's own refineSearch payload;
# lang/country/all_fields differ per tenant, so each company carries its own
# overrides. applyUrl is returned by the API (it points into the tenant's
# Workday), so again nothing is constructed.
PHENOM_WIDGET_BODY = {
    "lang": "en_us", "deviceType": "desktop", "country": "us",
    "pageName": "search-results", "ddoKey": "refineSearch", "sortBy": "",
    "subsearch": "", "from": 0, "jobs": True, "counts": True,
    "all_fields": ["category", "country", "state", "city", "type"], "size": 20,
    "clearAll": False, "jdsource": "facets", "isSliderEnable": False,
    "pageId": "page11", "siteType": "external", "keywords": "", "global": True,
    "selected_fields": {}, "locationData": {}}
WIDGET_MAX = 300


def f_phenom_widget(c):
    out, seen = [], set()
    for kw in c.get("keywords", ("intern", "internship", "stage", "stagiaire")):
        frm = 0
        while frm < WIDGET_MAX:
            body = dict(PHENOM_WIDGET_BODY, **c.get("body", {}))
            body.update({"keywords": kw, "from": frm, "size": 20})
            d = get(c["api"], body)
            rs = d.get("refineSearch") or {}
            rows = ((rs.get("data") or {}).get("jobs")) or []
            for j in rows:
                loc = j.get("cityStateCountry") or j.get("location") or ""
                more = [x.get("location", "") for x in (j.get("multi_location_array") or [])
                        if isinstance(x, dict)]
                _rows_from(seen, out, j.get("title", ""), loc, j.get("applyUrl", ""),
                           " ".join([x for x in [loc] + more if x]))
            frm += 20
            total = int(rs.get("totalHits") or 0)
            if len(rows) < 20 or frm >= total:
                break
            time.sleep(0.3)
    return out


# --- Eightfold, the pcsx flavour (Qualcomm, Microsoft, Morgan Stanley, ...) --
# positionUrl comes back RELATIVE ("/careers/job/4467...") so the link has to be
# built from the tenant host - and a built link gets verified before it is shown,
# the same rule f_wttj follows. location= is a fuzzy relevance term rather than a
# filter (a France search returns Mexico City), so it narrows without deleting,
# and where() still makes the real call locally.
EIGHTFOLD_PAGE = 20
EIGHTFOLD_MAX = 200


def f_eightfold(c):
    out, seen = [], set()
    verify, blocked = True, False
    for query, place in c.get("queries", (("intern", "France"), ("stage", "France"),
                                          ("stagiaire", ""), ("internship", "France"))):
        start = 0
        while start < EIGHTFOLD_MAX:
            d = get("%s/api/pcsx/search?domain=%s&query=%s&location=%s&start=%d&num=%d"
                    % (c["host"], c["domain"], urllib.parse.quote(query),
                       urllib.parse.quote(place), start, EIGHTFOLD_PAGE))
            positions = ((d.get("data") or {}).get("positions")) or []
            for p in positions:
                path = p.get("positionUrl") or ""
                if not path:
                    continue
                url = urllib.parse.urljoin(c["host"], path)
                if url in seen:
                    continue
                if verify:
                    v = _verify(url)
                    if v == "blocked":
                        verify = False          # host refuses us; stop spending requests
                        blocked = True
                    elif v == "gone":
                        PARTIAL.add(c["name"])
                        continue
                locs = [x for x in (p.get("locations") or []) if x]
                std = [x for x in (p.get("standardizedLocations") or []) if x]
                _rows_from(seen, out, p.get("name", ""), "; ".join(locs) or "; ".join(std),
                           url, " ".join(locs + std))
            start += EIGHTFOLD_PAGE
            count = int(((d.get("data") or {}).get("count")) or 0)
            if len(positions) < EIGHTFOLD_PAGE or start >= count:
                break
            time.sleep(0.3)
    if blocked:
        print("  %s: link verification blocked (403); links unverified this run"
              % c["name"], file=sys.stderr)
    return out


# --- Eightfold, the older apply/v2 flavour (Millennium) ---------------------
# Same vendor, older API: /api/pcsx/search answers 403 on this tenant. This one
# returns canonicalPositionUrl whole, so nothing is built, and it pages the board
# rather than searching it - the query parameter here is a relevance term that
# returns unrelated roles, not a filter.
V2_PAGE = 50
V2_MAX = 600


def f_eightfold_v2(c):
    out, seen, start = [], set(), 0
    while start < V2_MAX:
        d = get("%s/api/apply/v2/jobs?domain=%s&start=%d&num=%d"
                % (c["host"], c["domain"], start, V2_PAGE))
        positions = d.get("positions") or []
        for p in positions:
            locs = [x for x in (p.get("locations") or []) if x] or \
                   ([p.get("location")] if p.get("location") else [])
            _rows_from(seen, out, p.get("name", ""), "; ".join(locs),
                       p.get("canonicalPositionUrl") or "", " ".join(locs))
        start += V2_PAGE
        count = int(d.get("count") or 0)
        if len(positions) < V2_PAGE or start >= count:
            return out
        time.sleep(0.3)
    PARTIAL.add(c["name"])
    return out


# --- Oracle HCM Cloud, candidate-experience API (Dell, Nokia, Oracle, JPM) ---
# The requisitionList only comes back when the expand names it - without it the
# response is a TotalJobsCount with nothing under it, which is the shape of a
# fetch that silently returns nothing. Requisitions carry an Id and no link, so
# the candidate-experience URL is built on the SAME host that served the API and
# verified before it is shown.
ORACLE_PAGE = 25
ORACLE_MAX = 300
ORACLE_EXPAND = "requisitionList.workLocation,requisitionList.secondaryLocations"


def f_oracle_cx(c):
    out, seen = [], set()
    verify, blocked = True, False
    site = c.get("site", "CX_1")
    for kw in c.get("keywords", ("intern", "internship", "stage", "stagiaire")):
        off = 0
        while off < ORACLE_MAX:
            url = ("%s/hcmRestApi/resources/latest/recruitingCEJobRequisitions"
                   "?onlyData=true&expand=%s&finder=findReqs;siteNumber=%s,limit=%d,"
                   "offset=%d,sortBy=POSTING_DATES_DESC,keyword=%s"
                   % (c["host"], ORACLE_EXPAND, site, ORACLE_PAGE, off,
                      urllib.parse.quote(kw)))
            d = get(url)
            items = d.get("items") or []
            block = items[0] if items else {}
            reqs = block.get("requisitionList") or []
            for r in reqs:
                rid = str(r.get("Id") or "")
                if not rid:
                    continue
                link = "%s/hcmUI/CandidateExperience/en/sites/%s/job/%s/" % (c["host"], site, rid)
                if link in seen:
                    continue
                if verify:
                    v = _verify(link)
                    if v == "blocked":
                        verify = False
                        blocked = True
                    elif v == "gone":
                        PARTIAL.add(c["name"])
                        continue
                loc = r.get("PrimaryLocation") or ""
                where_bits = [loc, r.get("PrimaryLocationCountry") or ""]
                for w in (r.get("workLocation") or []):
                    if isinstance(w, dict):
                        where_bits += [w.get("TownOrCity") or "", w.get("Country") or "",
                                       w.get("Region2") or ""]
                for sec in (r.get("secondaryLocations") or []):
                    if isinstance(sec, dict):
                        where_bits.append(sec.get("Name") or sec.get("LocationName") or "")
                _rows_from(seen, out, r.get("Title", ""), loc, link,
                           _fr(" ".join(x for x in where_bits if x),
                               r.get("PrimaryLocationCountry")),
                           _contract(r.get("WorkerType") or r.get("ContractType")))
            off += ORACLE_PAGE
            total = int(block.get("TotalJobsCount") or 0)
            if len(reqs) < ORACLE_PAGE or off >= total:
                break
            time.sleep(0.3)
    if blocked:
        print("  %s: link verification blocked (403); links unverified this run"
              % c["name"], file=sys.stderr)
    return out


# --- Amazon / AWS -----------------------------------------------------------
# amazon.jobs publishes its own search as JSON. loc_query is a relevance term,
# not a filter (a France search returns Mexico City), so it is used to narrow the
# request and where() still decides. job_path is the site's own path; the host is
# the only part added.
AMAZON_HOST = "https://www.amazon.jobs"
AMAZON_LIMIT = 100
AMAZON_MAX = 400


def f_amazon(c):
    out, seen = [], set()
    for base, place in c.get("queries", (("intern", "France"), ("stage", "France"),
                                         ("stagiaire", "France"), ("internship", "France"))):
        off = 0
        while off < AMAZON_MAX:
            d = get("%s/en/search.json?base_query=%s&loc_query=%s&result_limit=%d&offset=%d"
                    % (AMAZON_HOST, urllib.parse.quote(base), urllib.parse.quote(place),
                       AMAZON_LIMIT, off))
            jobs = d.get("jobs") or []
            for j in jobs:
                path = j.get("job_path") or ""
                loc = j.get("normalized_location") or j.get("location") or ""
                _rows_from(seen, out, j.get("title", ""), loc,
                           urllib.parse.urljoin(AMAZON_HOST, path) if path else "",
                           " ".join(x for x in [loc, j.get("city"), j.get("state"),
                                                j.get("country_code")] if x))
            off += AMAZON_LIMIT
            if len(jobs) < AMAZON_LIMIT or off >= int(d.get("hits") or 0):
                break
            time.sleep(0.3)
    return out


# --- Goldman Sachs (its own GraphQL gateway) --------------------------------
# One operation, GetRoles, with an experiences filter. EARLY_CAREER is the whole
# campus population - internships, analyst programmes and graduate roles - so it
# is fetched whole and the internship test does the rest. Location has to be a
# filter here rather than a search term, and the filter values come from a second
# operation; that is not worth the extra call while the early-career board is
# this small, so France is decided locally like everywhere else.
GS_URL = "https://api-higher.gs.com/gateway/api/v1/graphql"
GS_QUERY = ("query GetRoles($searchQueryInput: RoleSearchQueryInput!){roleSearch"
            "(searchQueryInput:$searchQueryInput){totalCount items{roleId jobTitle "
            "division jobFunction locations{primary city country} "
            "externalSource{sourceId}}}}")
GS_PAGE = 50
GS_MAX = 20                 # pages


def f_gs(c):
    out, seen = [], set()
    verify, blocked = True, False
    for page in range(GS_MAX):
        body = {"operationName": "GetRoles", "query": GS_QUERY,
                "variables": {"searchQueryInput": {
                    "page": {"pageSize": GS_PAGE, "pageNumber": page},
                    "sort": {"sortStrategy": "RELEVANCE", "sortOrder": "DESC"},
                    "filters": [], "experiences": c.get("experiences", ["EARLY_CAREER"]),
                    "searchTerm": ""}}}
        d = get(GS_URL, body)
        search = ((d.get("data") or {}).get("roleSearch")) or {}
        items = search.get("items") or []
        for it in items:
            src = str((it.get("externalSource") or {}).get("sourceId") or "")
            if not src:
                continue
            url = "%s/roles/%s" % (c["site"], src)
            if url in seen:
                continue
            if verify:
                v = _verify(url)
                if v == "blocked":
                    verify = False
                    blocked = True
                elif v == "gone":
                    PARTIAL.add(c["name"])
                    continue
            bits = []
            for L in (it.get("locations") or []):
                if isinstance(L, dict):
                    bits.append(", ".join(x for x in [L.get("city"), L.get("country")] if x))
            loc = "; ".join(x for x in bits if x)
            _rows_from(seen, out, it.get("jobTitle", ""), loc, url, loc)
        if len(items) < GS_PAGE or (page + 1) * GS_PAGE >= int(search.get("totalCount") or 0):
            break
        time.sleep(0.3)
    if blocked:
        print("  %s: link verification blocked (403); links unverified this run"
              % c["name"], file=sys.stderr)
    return out


# --- Coveo (Dynatrace) ------------------------------------------------------
# dynatrace.com proxies its Coveo index at /api/coveo/search/. clickUri is the
# posting's own URL; raw.office_locations and raw.country carry the location.
def f_coveo(c):
    out, seen = [], set()
    for kw in c.get("keywords", ("intern", "internship", "stage", "student", "werkstudent")):
        d = get(c["api"], {"q": kw, "numberOfResults": c.get("size", 100)})
        for r in d.get("results") or []:
            raw = r.get("raw") or {}
            offices = [x for x in (raw.get("office_locations") or []) if x]
            countries = [x for x in (raw.get("country") or []) if x]
            loc = "; ".join(offices) or "; ".join(countries)
            _rows_from(seen, out, r.get("title", ""), loc,
                       r.get("clickUri") or r.get("uri") or "",
                       " ".join(offices + countries))
        time.sleep(0.3)
    return out


# --- Atlassian (its own endpoint) -------------------------------------------
# One call returns the whole board (248 postings), so there is nothing to page
# and nothing to search. portalJobPost.portalUrl is the posting's own link.
def f_atlassian(c):
    d = get("https://www.atlassian.com/endpoint/careers/listings")
    out, seen = [], set()
    for j in d if isinstance(d, list) else []:
        locs = [x for x in (j.get("locations") or []) if x]
        url = ((j.get("portalJobPost") or {}).get("portalUrl")) or j.get("applyUrl") or ""
        _rows_from(seen, out, j.get("title", ""), "; ".join(locs), url, " ".join(locs))
    return out


# ---------------------------------------------------------- HTML boards ----
# Four sources below publish no JSON at all and are read from their list pages.
# That is strictly worse than an API and is treated that way: each pages until a
# page adds nothing new, and a page ceiling marks the company PARTIAL rather than
# letting a missing role look closed. Every selector here was read off a live
# page by probe_html.py - none of it is guessed. Re-run that probe before
# changing any of these patterns.
_STRIP = re.compile(r"(?is)<(script|style)\b.*?</\1\s*>")
_TAG   = re.compile(r"<[^>]+>")


def get_text(url, extra=None):
    """A page as text. Sends a browser Accept - UA's JSON Accept gets a 406 or a
    different rendering out of several of these hosts."""
    req = urllib.request.Request(url, headers={
        "User-Agent": UA["User-Agent"],
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8",
        **(extra or {})})
    with urllib.request.urlopen(req, timeout=45) as r:
        return r.read().decode(r.headers.get_content_charset() or "utf-8", "replace")


def _plain(fragment):
    """Markup -> the words a human would read, entities resolved."""
    return re.sub(r"\s+", " ",
                  html.unescape(_TAG.sub(" ", _STRIP.sub(" ", fragment or "")))).strip()


def _blocks(page, open_re):
    """Slice a page into one string per card. A card runs from its opening tag to
    the next one, which is exact enough for these layouts and needs no parser."""
    starts = [m.start() for m in open_re.finditer(page)]
    return [page[st:(starts[i + 1] if i + 1 < len(starts) else min(len(page), st + 8000))]
            for i, st in enumerate(starts)]


def _paged(c, url_for, parse, pages, headers=None):
    """Page a list until a page adds nothing new. parse(page) -> rows keyed by url."""
    out, seen = [], set()
    for p in range(pages):
        try:
            page = get_text(url_for(p), headers)
        except urllib.error.HTTPError as e:
            if p and e.code in (404, 410):
                return out                      # ran off the end of the pagination
            raise
        fresh = 0
        for row in parse(page):
            if row[2] in seen:
                continue
            seen.add(row[2])
            fresh += 1
            out.append(row)
        # Paging past the last page does NOT reliably 404 - Talentsoft repeats a
        # page and BNP quietly drops the filter - so "this page added nothing
        # new" is the stop condition, not the status code.
        if not fresh:
            return out
        time.sleep(0.4)
    # Every page we were willing to fetch had something new on it, so there is
    # very likely more. Shown, but nothing of theirs may be closed.
    PARTIAL.add(c["name"])
    return out


# --- Talentsoft (Amundi, Dassault Aviation) ---------------------------------
# One <li class="ts-offer-list-item"> per offer, holding the title link and a
# <ul class="ts-offer-list-item__description"> of loose fields. The ORDER of
# those fields differs per tenant - Amundi is [contract, entity, country,
# postcode], Dassault Aviation is [ref, date, contract, city] - so the contract
# is found by asking every field what it is rather than by position.
_TS_CARD = re.compile(r'<li[^>]*class="[^"]*ts-offer-list-item[^"]*"', re.I)
_TS_LINK = re.compile(r'<a[^>]*href="([^"]*/offre-de-emploi/emploi[^"]*\.aspx[^"]*)"[^>]*>(.*?)</a>',
                      re.I | re.S)
_TS_DESC = re.compile(r'<ul[^>]*class="[^"]*ts-offer-list-item__description[^"]*"[^>]*>(.*?)</ul>',
                      re.I | re.S)
_LI      = re.compile(r"<li[^>]*>(.*?)</li>", re.I | re.S)
# a reference or a date is never the town
_TS_NOISE = re.compile(r"^\s*(?:r[ée]f\.?\s*:|\d{1,2}/\d{1,2}/\d{2,4}\s*$|\d{4}-\d+\s*$)", re.I)


def f_talentsoft(c):
    base = c["base"]

    def parse(page):
        rows = []
        for card in _blocks(page, _TS_CARD):
            m = _TS_LINK.search(card)
            if not m:
                continue
            title = _plain(m.group(2))
            if not title:
                continue
            d = _TS_DESC.search(card)
            fields = [_plain(x) for x in _LI.findall(d.group(1))] if d else []
            fields = [f for f in fields if f]
            ct, ct_at = None, -1
            for n, f in enumerate(fields):
                k = _contract(f)
                if k:
                    ct, ct_at = k, n
                    break
            # The town is the last field on both tenants - but skip the contract,
            # the reference and the date, or a card that carries no location at
            # all comes out located "Stage" or "04/09/2026". A card with nothing
            # left shows blank, which the board renders as "no location given":
            # honest, and it lands in the unrecognised-location box where it can
            # be seen rather than being quietly mislabelled.
            shown = [f for n, f in enumerate(fields)
                     if n != ct_at and not _TS_NOISE.match(f)]
            rows.append((title, shown[-1] if shown else "",
                         urllib.parse.urljoin(base, html.unescape(m.group(1))),
                         " ".join(fields), ct))
        return rows

    return _paged(c, lambda p: c["list"] % (p + 1), parse, c.get("pages", 12))


# --- iCIMS (Expleo) ---------------------------------------------------------
# <li class="iCIMS_JobCardItem">, then a <dl> of labelled fields. The location
# field is the one whose <dt> carries the map-marker glyph: matching the LABEL
# would pick up "Lieu de travail", which says "Sur place" or "Hybride", not where.
_IC_CARD = re.compile(r'<li[^>]*class="[^"]*iCIMS_JobCardItem[^"]*"', re.I)
_IC_LINK = re.compile(r'<a[^>]*href="([^"]*/jobs/\d+/[^"]*)"[^>]*>(.*?)</a>', re.I | re.S)
_IC_H3   = re.compile(r"<h3[^>]*>(.*?)</h3>", re.I | re.S)
_IC_TAG  = re.compile(r'<dt[^>]*>(.*?)</dt>\s*<dd[^>]*>(.*?)</dd>', re.I | re.S)
_IC_TYPE = re.compile(r"type\s*d.{0,3}emploi|employment\s*type|job\s*type", re.I)


def f_icims(c):
    def parse(page):
        rows = []
        for card in _blocks(page, _IC_CARD):
            m = _IC_LINK.search(card)
            if not m:
                continue
            h3 = _IC_H3.search(m.group(2))
            title = _plain(h3.group(1) if h3 else m.group(2))
            if not title:
                continue
            loc, ct = "", None
            for dt, dd in _IC_TAG.findall(card):
                val = _plain(dd)
                if "map-marker" in dt and not loc:
                    loc = val
                elif _IC_TYPE.search(_plain(dt)):
                    ct = ct or _contract(val)
            # "FR-64-Biarritz": the country prefix is the only France signal for
            # a town no city list has, so hand it to _fr rather than the matcher.
            rows.append((title, loc, html.unescape(m.group(1)), _fr(loc, loc.split("-")[0]), ct))
        return rows

    return _paged(c, lambda p: c["list"] % p, parse, c.get("pages", 35))


# --- Gestmax / Kioskemploi (MBDA) -------------------------------------------
# A sortable table, one <tr class="... vacancy-id-N"> per offer, with the title,
# date, sector and location each in a <td headers="..."> cell.
#
# EVERY cell is wrapped in its own copy of the same offer link. Reading the text
# between one link and the next therefore yields nothing at all, which is why the
# first version of this parsed 472 of MBDA's 475 offers and placed 0 of them in
# France. Parse the row and read the cells by name.
_GX_ROW  = re.compile(r'<tr[^>]*class="[^"]*vacancy-id-\d+[^"]*"', re.I)
_GX_CELL = re.compile(r'<td[^>]*headers="([a-z_]+)"[^>]*>(.*?)</td>', re.I | re.S)
_GX_HREF = re.compile(r'href="(https?://[a-z0-9.-]*gestmax\.fr/\d+/\d+/[^"]*)"', re.I)
# Gestmax writes the town as "Le Plessis Robinson (92)" - no hyphens, and with
# the French department number. The number is the reliable signal: it places
# every French town whatever the city list happens to spell, and cannot match a
# foreign site, which is written "Stevenage (UK)".
_GX_DEPT = re.compile(r"\(\s*(?:0[1-9]|[1-8]\d|9[0-8]|2[AB]|97[1-6])\s*\)")


def f_gestmax(c):
    def parse(page):
        rows = []
        for row in _blocks(page, _GX_ROW):
            row = row.split("</tr>")[0]
            cells = {k: _plain(v) for k, v in _GX_CELL.findall(row)}
            href  = _GX_HREF.search(row)
            title = cells.get("vacancy_title", "")
            if not href or not title:
                continue
            loc = cells.get("vac_localisation", "")
            blob = ("%s France" % loc) if _GX_DEPT.search(loc) else loc
            rows.append((title, loc, html.unescape(href.group(1)), blob))
        return rows

    return _paged(c, lambda p: c["list"] % (p + 1), parse, c.get("pages", 30))


# --- BNP Paribas ------------------------------------------------------------
# group.bnpparibas/en/careers/all-job-offers, server-rendered and complete. What
# it wants is the FULL browser navigation header set: measured from a runner,
# no headers / a plain UA / a browser UA / a browser UA with Accept:*/* all get
# 403 Access Denied, and adding Referer, Upgrade-Insecure-Requests and the
# Sec-Fetch-* set gets 200 and the real listing. So this is a header check, not
# the IP block the old note assumed - and NOT Akamai gating the path, though
# Akamai Bot Manager is on the domain. A 403 appearing later would be rate
# limiting, and the answer to that is a longer sleep, not more headers.
#
# robots.txt disallows only URLs carrying ref, cat, field, key, NumPage or
# as_url_id. form[type][] and page are none of those.
#
# form[type][] ids, read off the page: 2 Permanent - 146 Fixed Term - 28 Trainee
# / Internship - 33 International Volunteer - 35 Summer Job - 36 Apprenticeship -
# 2374 Zero Hours - 2134 Graduate Programme. Filtering to 28 turns 380 pages of
# 3787 offers into ~37 pages of 362, which is the difference between polite and
# not. Location is NOT filtered server-side; where() does that locally and shows
# what it cannot place.
BNP_HOST = "https://group.bnpparibas"
BNP_INTERNSHIP = "28"       # form[type][] id for "Trainee / Internship"
BNP_QUERY = urllib.parse.urlencode({"form[type][]": BNP_INTERNSHIP})


def _bnp_url(page):
    """page counts from 0 here and is sent 1-BASED, because ?page=0 returns a
    page with zero cards on it. Measured: ?page=0 -> 0 cards, ?page=1 -> 10,
    ?page=2 -> 10. Sending 0 made the first page look empty and ended the loop
    before it started, which is how this fetched nothing at all while answering
    200. Also measured: form[type] without the [] is ignored and the board comes
    back unfiltered, and type[] is a 400 - only form[type][] filters.

    Built here rather than kept as a %-template: the query percent-escapes to
    form%5Btype%5D%5B%5D, which a later %-format reads as a conversion."""
    return "%s/en/careers/all-job-offers?%s&page=%d" % (BNP_HOST, BNP_QUERY, page + 1)
BNP_HEADERS = {
    # The bare "Mozilla/5.0" in UA is a bot signature and 403s here: the ladder
    # rung that got 200 sent a full Chrome string, so send exactly that.
    "User-Agent": ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"),
    "Referer": BNP_HOST + "/en/careers",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document", "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "same-origin", "Sec-Fetch-User": "?1",
    "Connection": "keep-alive"}

_BNP_CARD  = re.compile(r'<article[^>]*class="[^"]*card-offer[^"]*"', re.I)
_BNP_LINK  = re.compile(r'<a[^>]*href="([^"]*/job-offer/[^"]*)"', re.I)
_BNP_TITLE = re.compile(r'<h3[^>]*class="[^"]*title-4[^"]*"[^>]*>(.*?)</h3>', re.I | re.S)
_BNP_TYPE  = re.compile(r'<div[^>]*class="offer-type"[^>]*>(.*?)</div>', re.I | re.S)
_BNP_LOC   = re.compile(r'<div[^>]*class="offer-location"[^>]*>(.*?)</div>', re.I | re.S)


def f_bnp(c):
    def parse(page):
        rows = []
        for card in _blocks(page, _BNP_CARD):
            link = _BNP_LINK.search(card)
            ttl  = _BNP_TITLE.search(card)
            if not link or not ttl:
                continue
            kt = _BNP_TYPE.search(card)
            kind = _contract(_plain(kt.group(1)) if kt else "")
            # Paging past the last page silently drops the filter and serves the
            # unfiltered board, so the card's OWN offer-type is checked rather
            # than trusted. Everything past the end reads "Permanent" and is
            # dropped here, which also ends the loop: _paged stops when a page
            # contributes nothing.
            if kind != "intern":
                continue
            lm = _BNP_LOC.search(card)
            loc = _plain(lm.group(1)) if lm else ""
            rows.append((_plain(ttl.group(1)), loc,
                         urllib.parse.urljoin(BNP_HOST, html.unescape(link.group(1))),
                         loc, kind))
        return rows

    return _paged(c, _bnp_url, parse, c.get("pages", 45), BNP_HEADERS)


FETCH = {"greenhouse": f_greenhouse, "lever": f_lever, "workable": f_workable,
         "smartrecruiters": f_smartrecruiters, "workday": f_workday,
         "ashby": f_ashby, "teamtailor": f_teamtailor,
         "dassault": f_dassault, "wttj": f_wttj, "sgcareers": f_sgcareers,
         "talentsoft": f_talentsoft, "icims": f_icims, "gestmax": f_gestmax,
         "bnp": f_bnp}

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
    "sgcareers":       lambda c: "careers.societegenerale.com/search-proxy.php (CES search-profile)",
    "talentsoft":      lambda c: (c["list"] % 1).split("?")[0].replace("https://", ""),
    "icims":           lambda c: (c["list"] % 0).split("?")[0].replace("https://", ""),
    "gestmax":         lambda c: (c["list"] % 1).replace("https://", ""),
    "bnp":             lambda c: "group.bnpparibas/en/careers/all-job-offers (form[type][]=28)",
}


def _is_intern(j):
    """Is this row an internship?

    A row may carry the board's OWN contract label as a fifth element (see
    _contract). When it does, it wins outright - it is the field the ATS filters
    on, which beats a word in the title in both directions. Societe Generale
    lists "Software developper" as INTERNSHIP with no hint in the title, and
    Thales titles an apprenticeship "STAGE - ...".

    With no label, the old test stands: the title says internship, and neither
    the title nor the location blob says alternance."""
    said = j[4] if len(j) > 4 else None
    if said == "intern":
        return True
    if said == "alt":
        return False
    return bool(INTERN.search(j[0])) and not ALT.search(j[0]) and not ALT.search(j[3])


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
        itn = [(j, w) for j, w in placed if _is_intern(j)]
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
        row["partial"] = c["name"] in PARTIAL
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
    new_roles, recent_roles = [], []
    cutoff = (NOW.date() - timedelta(days=2)).isoformat()
    for r in results:
        for h in r["hits"]:
            u = h["url"]
            h["first_seen"] = prev_posts.get(u, {}).get("first_seen", TODAY)
            h["is_new"] = (u not in prev_posts) and bool(prev_posts)
            # location included: the nightly ping reads only status.json, and
            # "Software developper" is a different decision in Lille than in
            # La Defense. STATUS_ROWS still caps the list, so this cannot grow.
            entry = {"title": h["title"], "company": r["name"], "url": u,
                     "location": h["location"], "first_seen": h["first_seen"]}
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
            p.append("<details%s><summary>%d non-tech internship%s filtered out</summary><ul>"
                     % (" open" if any(o["is_new"] for o in r["other"]) else "",
                        len(r["other"]), "" if len(r["other"]) == 1 else "s"))
            # Anything new is listed first, so a cap can never hide the one entry
            # that is actually news.
            for o in sorted(r["other"], key=lambda x: not x["is_new"])[:BOX_ROWS]:
                p.append('<li><a href="%s" target="_blank" rel="noopener">%s</a> &mdash; %s%s</li>'
                         % (esc(o["url"]), esc(o["title"]), esc(o["location"]),
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
                p.append('<li><a href="%s" target="_blank" rel="noopener">%s</a> &mdash; %s%s</li>'
                         % (esc(o["url"]), esc(o["title"]), esc(o["location"] or "no location given"),
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
