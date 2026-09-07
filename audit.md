# What the filters dropped

Rewritten by every sweep; worth a skim once a week.

- anything under **unrecognised location** that is really in France belongs in
  `_FR_CITIES` in `make_board.py` - that box is the whole point of not dropping
  a role just because its town was not on a hand-written list
- anything under **not tech** that is really an engineering role belongs in
  `TECH`, or in `STRONG` if one of the `EXCL` veto words is what is blocking it

Roles outside France are counted, not listed: that call is nearly always right
and the list would be hundreds long. A sample is kept to spot a systematic
mistake (a French site being read as foreign).

---

## Stage Watch

`board.html` &middot; sweep of 2026-09-07

### Unrecognised location - 4

| Company | Title | Location |
|---|---|---|
| Cloudflare | [EIAM Business Enablement & Operations Intern (Fall 2026)](https://boards.greenhouse.io/cloudflare/jobs/8068479?gh_jid=8068479) | In-Office |
| Cloudflare | [Software Engineer Intern (Fall 2026)](https://boards.greenhouse.io/cloudflare/jobs/8118855?gh_jid=8118855) | In-Office |
| Cloudflare | [Software Engineer Intern (Fall 2026)](https://boards.greenhouse.io/cloudflare/jobs/8118845?gh_jid=8118845) | In-Office |
| Cloudflare | [Software Engineer Intern (Fall 2026) - Austin, TX](https://boards.greenhouse.io/cloudflare/jobs/8052785?gh_jid=8052785) | In-Office |

### Not tech - 15

| Company | Title | Location |
|---|---|---|
| Doctolib | [Stage - Community Engagement Associate (x/f/m) - Octobre 2026](https://job-boards.greenhouse.io/doctolib/jobs/7802416003) | Paris, Paris, France |
| Doctolib | [Stage - Consolidation et Contrôle financier (x/f/m) - Septembre 2026](https://job-boards.greenhouse.io/doctolib/jobs/7610171003) | Paris, Paris, France |
| Doctolib | [Stage - Medical Content Associate (x/f/m) - Septembre 2026](https://job-boards.greenhouse.io/doctolib/jobs/7784750003) | Paris, Paris, France |
| Criteo | [Stage – Campaign Manager Intern \| Janvier 2027](https://criteo.wd3.myworkdayjobs.com/en-US/Criteo_Career_Site/job/Paris/Agency-Campaign-Manager-Intern--Performance-Media---French-Speaker_r20855) | Paris, France |
| Scaleway | [Approvisionneur - Stage](https://jobs.lever.co/scaleway/c85a7df4-bee6-41c2-9983-06db6a116bb8) | Paris |
| Scaleway | [Event Operations Intern](https://jobs.lever.co/scaleway/b4c5c7b1-162c-442e-bc9f-e4b1d621d1a7) | Paris |
| Snowflake | [Partner Marketing Intern - Paris (French Speaking](https://jobs.ashbyhq.com/snowflake/54c27993-5827-4a03-80c8-cc5f02b960f9) | FR-Paris |
| Palantir | [Deployment Strategist, Internship](https://jobs.lever.co/palantir/774cf5c9-bf6a-4d77-bf60-d50ef1beb1a0) | Paris, France |
| SAP | [Internship: Partner Solution Enablement Associate F/M](https://jobs.sap.com/job/Levallois-Perret-Internship-Partner-Solution-Enablement-Associate-FM-92300/1421057333/) | Levallois Perret |
| Microsoft | [National Technology Intern](https://apply.careers.microsoft.com/careers/job/1970393556988021) | France, Paris, Paris |
| Amazon / AWS | [Operations Intern - Région Sud - Start Date 2027](https://www.amazon.jobs/en/jobs/10504848/operations-intern-region-sud-start-date-2027) | Toulouse, Occitanie, FRA |
| Amazon / AWS | [Operations Intern - Région Nord - Start Date 2027](https://www.amazon.jobs/en/jobs/10492799/operations-intern-region-nord-start-date-2027) | Lille, Hauts-de-France, FRA |
| Amazon / AWS | [Operations Intern - Île de France - Start Date 2027](https://www.amazon.jobs/en/jobs/10504822/operations-intern-ile-de-france-start-date-2027) | Paris, Ile-de-France, FRA |
| Amazon / AWS | [Stagiaire service juridique](https://www.amazon.jobs/en/jobs/10518434/stagiaire-service-juridique) | Clichy, Ile-de-France, FRA |
| Amazon / AWS | [Stagiaire service juridique](https://www.amazon.jobs/en/jobs/10470003/stagiaire-service-juridique) | Clichy, Ile-de-France, FRA |

### Outside France - 516 (sample below)

| Company | Title | Location |
|---|---|---|
| Datadog | [Product Management Intern](https://careers.datadoghq.com/detail/8108241/?gh_jid=8108241) | New York, New York, USA |
| Datadog | [Software Engineering Intern (Winter)](https://careers.datadoghq.com/detail/8052095/?gh_jid=8052095) | Boston, Massachusetts, USA; New York, New York, USA |
| Doctolib | [Business Development Representative Intern - Milano (x/f/m)](https://job-boards.greenhouse.io/doctolib/jobs/7800808003) | Milano, Milan, Italy |
| Doctolib | [SEO & AI Intern (x/f/m)](https://job-boards.greenhouse.io/doctolib/jobs/7824240003) | Milano, Milan, Italy |
| Doctolib | [SEO & AI Intern (x/f/m)](https://job-boards.greenhouse.io/doctolib/jobs/7864184003) | Milano, Milan, Italy |
| Criteo | [Customer Success Intern, 6-month (German-Speaker)](https://criteo.wd3.myworkdayjobs.com/en-US/Criteo_Career_Site/job/Munich/Customer-Success-Intern--6-month--German-Speaker-_r20965) | Munich, Germany |
| Criteo | [Account Strategist Intern - Retail Media Benelux & Nordics](https://criteo.wd3.myworkdayjobs.com/en-US/Criteo_Career_Site/job/Amsterdam/Account-Strategist-Intern---Retail-Media-Benelux---Nordics_r20739) | Amsterdam, Netherlands |
| Criteo | [Account Strategist Intern - French Speaker](https://criteo.wd3.myworkdayjobs.com/en-US/Criteo_Career_Site/job/Barcelona/Account-Strategist-Intern_r20801) | Barcelona, Spain |
| Criteo | [Account Strategist Intern, 6-month (German-Speaker)](https://criteo.wd3.myworkdayjobs.com/en-US/Criteo_Career_Site/job/Munich/Account-Strategist-Intern--6-month--German-Speaker-_r20959) | Munich, Germany |
| Criteo | [Account Strategist (Intern)](https://criteo.wd3.myworkdayjobs.com/en-US/Criteo_Career_Site/job/Barcelona/Account-Strategist--Intern-_r20979) | Barcelona, Spain |
| Criteo | [Business Development & Lead Generation Intern - Independent Agency Team (France, UK & DACH)](https://criteo.wd3.myworkdayjobs.com/en-US/Criteo_Career_Site/job/Barcelona/Agency-Sales-Intern_r20802) | Barcelona, Spain |
| Criteo | [Campaign Manager Intern, Performance Media - Spanish & Italian Speaker](https://criteo.wd3.myworkdayjobs.com/en-US/Criteo_Career_Site/job/Barcelona/Campaign-Manager-Intern---Spanish---Italian-Speaker_r20908) | Barcelona, Spain |
| Criteo | [Sales Operations Data Analyst Intern](https://criteo.wd3.myworkdayjobs.com/en-US/Criteo_Career_Site/job/Barcelona/Sales-Operations-Data-Analyst-Intern_r20723) | Barcelona, Spain |
| Criteo | [People Operations Internship – French Speaker](https://criteo.wd3.myworkdayjobs.com/en-US/Criteo_Career_Site/job/Barcelona/People-Operations-Intern--French-Speaker_r20828) | Barcelona, Spain |
| Criteo | [Customer Care Intern](https://criteo.wd3.myworkdayjobs.com/en-US/Criteo_Career_Site/job/Gurgaon/Customer-Care-Intern_r20805) | Gurgaon, India |

---

## French Tech Watch

`board2.html` &middot; sweep of 2026-09-07

### Unrecognised location - 7

| Company | Title | Location |
|---|---|---|
| OVHcloud | [Stage Septembre 2026 - Industrial Lean Officer H/F/N](https://careers.ovhcloud.com/job/ROUBAIX-Stage-Septembre-2026-Industrial-Lean-Officer-HFN-59100/1385526333/) | ROUBAIX |
| OVHcloud | [Stage - Chef de projet documentation industrielle H/F/N](https://careers.ovhcloud.com/job/CROIX-Stage-Chef-de-projet-documentation-industrielle-HFN-59170/1385457233/) | CROIX |
| Siemens | [Market Development Intern](https://jobs.siemens.com/en_US/externaljobs/JobDetail/520020) | - |
| Siemens | [Finance Leadership Development Program Internship](https://jobs.siemens.com/en_US/externaljobs/JobDetail/516238) | - |
| Siemens | [Software & AI Adoption Engineering Intern](https://jobs.siemens.com/en_US/externaljobs/JobDetail/515651) | - |
| Siemens | [Smart Infrastructure Electrical Products Engineering Leadership Development Program Internship](https://jobs.siemens.com/en_US/externaljobs/JobDetail/520912) | - |
| Siemens | [Strategic Student Program: AI & Engineering Data Internship (Spring 2027, GSCS)](https://jobs.siemens.com/en_US/externaljobs/JobDetail/519908) | - |

### Not tech - 51

| Company | Title | Location |
|---|---|---|
| Qonto | [Legal Intern - Commercial](https://jobs.lever.co/qonto/ba688ab4-66b1-4d6a-9aa7-537e191ea392) | Paris |
| Qonto | [Legal Intern - Product & AI](https://jobs.lever.co/qonto/354fa50e-2741-4936-82f5-0d1ce5fb8be3) | Paris |
| Qonto | [Product Marketing Manager Intern](https://jobs.lever.co/qonto/05723cc9-e819-4a5c-aea1-15e9a771ffad) | Paris |
| BlaBlaCar | [Stagiaire Communication & Relations Publiques (6 mois) - Paris, France](https://jobs.lever.co/blablacar/517fe4e3-2611-4fed-933c-ef0455b46aad) | Paris, France |
| BlaBlaCar | [Stagiaire Marketing & Réseaux Sociaux France](https://jobs.lever.co/blablacar/f40b93ed-ad63-457f-81de-ec6ec3fbe85e) | Paris, France |
| Aircall | [GTM Enablement Intern](https://jobs.lever.co/aircall/daecac18-ae6c-45ea-9e0c-d307d18f1a14) | Paris Office |
| Aircall | [Product Manager Intern](https://jobs.lever.co/aircall/c71f52af-d884-4a38-9db7-7f7ff402e2ef) | Paris Office |
| Aircall | [Regional Marketing Intern, DACH Market](https://jobs.lever.co/aircall/6737595c-eea0-4e64-b619-0894d532bead) | Paris Office |
| Aircall | [Sales Intern - French market - 6 months](https://jobs.lever.co/aircall/131dcb57-0ba9-45fe-b5a4-e88e118bb06d) | Paris Office |
| Aircall | [Sales Intern - Iberia market - 6 months](https://jobs.lever.co/aircall/3a88fe56-9a33-476d-89de-76e4faa38cfc) | Paris Office |
| Aircall | [Sales Partner Manager Intern](https://jobs.lever.co/aircall/ae78bd4b-a11e-4cb3-8e81-a0f0a4b28b9b) | Paris Office |
| Aircall | [Strategy & Operations Intern — Office of the General Manager, Small Business](https://jobs.lever.co/aircall/d7f248d3-f16f-4bc7-9f7f-201e180600df) | Paris Office |
| Back Market | [Financial Planning & Analysis Intern](https://jobs.ashbyhq.com/backmarket/2551ba06-5d98-4441-8919-e20e844cc15a) | Bordeaux |
| Back Market | [Legal Intern / Juriste Droit des Affaires (Paris)](https://jobs.ashbyhq.com/backmarket/653540bb-f183-4f3e-a4c0-2ff083469eb5) | Paris |
| Back Market | [Sustainability and Public Affairs Intern (Paris )](https://jobs.ashbyhq.com/backmarket/68d98b54-27d2-468a-9ae2-ace32cbb90d7) | Paris |
| Alan | [CTO Founder Associate - internship](https://jobs.ashbyhq.com/alan/d457e0f1-2418-4759-b4ed-e41fdff50bf0) | Paris, France |
| Alan | [CEO Founder Associate - Internship](https://jobs.ashbyhq.com/alan/9c4eb7ab-2297-4981-ac31-ef57a349f9c9) | Paris, France |
| Alan | [Insurance Legal - Internship](https://jobs.ashbyhq.com/alan/0507d0de-823b-4058-bd6e-ec2428d362fd) | Paris, France |
| Alan | [Talent Associate (internship)](https://jobs.ashbyhq.com/alan/332f9cc1-9d40-4bf0-bfca-279b1650814d) | Paris, France |
| Alan | [Brand Associate (Internship)](https://jobs.ashbyhq.com/alan/91af2544-fd3d-49f6-92f1-095cea1580df) | Paris, France |
| Alan | [People Associate (internship)](https://jobs.ashbyhq.com/alan/71fa3e9d-1f5f-4e3f-a1de-e68b3c85803a) | Paris, France |
| Ledger | [Internship - Total Rewards (Compensation & Benefits)](https://jobs.ashbyhq.com/ledger/6dcd473c-804a-4d0e-b477-4f2a4e318cf2) | Paris, France |
| Sorare | [Player Experience Intern](https://jobs.ashbyhq.com/sorare/20495c4a-87d1-411c-a528-6420f0dc4257) | Paris |
| Deezer | [Social Ads Creative Manager Intern - FRENCH REQUIRED (m/f/d)](https://deezer.teamtailor.com/jobs/8272091-social-ads-creative-manager-intern-french-required-m-f-d) | Paris, FR |
| Deezer | [Product Marketing Intern (m/f/d)](https://deezer.teamtailor.com/jobs/8149033-product-marketing-intern-m-f-d) | Paris, FR |
| Deezer | [Procurement Intern - 6 months (m/f/d)](https://deezer.teamtailor.com/jobs/7633290-procurement-intern-6-months-m-f-d) | Paris, FR |
| Deezer | [Talent acquisition & HR development - 6 months internship (m/f/d)](https://deezer.teamtailor.com/jobs/7632031-talent-acquisition-hr-development-6-months-internship-m-f-d) | Paris, FR |
| Deezer | [Motion Design - 6 months Internship m/f/d - French speaking mandatory](https://deezer.teamtailor.com/jobs/7632023-motion-design-6-months-internship-m-f-d-french-speaking-mandatory) | Paris, FR |
| Deezer | [Legal & Business Affairs - Intern (m/f/d)](https://deezer.teamtailor.com/jobs/7632024-legal-business-affairs-intern-m-f-d) | Paris, FR |
| Sopra Steria | [Stage de fin d'études - Consultant en transformation digitale](https://jobs.smartrecruiters.com/SopraSteria1/744000147879850) | Courbevoie, fr |
| Sopra Steria | [Stage Consultant(e) - Transformation digitale - People&Change - Ile de France](https://jobs.smartrecruiters.com/SopraSteria1/744000147559756) | Courbevoie, fr |
| Sopra Steria | [Stage - Chef/fe de Projet - Services Publics - Ile de France](https://jobs.smartrecruiters.com/SopraSteria1/744000147258373) | Courbevoie, fr |
| Sopra Steria | [Stage - Consultant Stratégie des Paiements - Services Financiers - Courbevoie](https://jobs.smartrecruiters.com/SopraSteria1/744000145930048) | Courbevoie, fr |
| Sopra Steria | [Stage PPI - Juriste en droit social](https://jobs.smartrecruiters.com/SopraSteria1/744000143852928) | Paris, fr |
| Sopra Steria | [Stage Consultant(e) fonctionnel(le) - Aéronautique - Bordeaux](https://jobs.smartrecruiters.com/SopraSteria1/744000140908198) | Mérignac, fr |
| Sopra Steria | [Stage Conseil - Transformation Digitale - Energie - IDF](https://jobs.smartrecruiters.com/SopraSteria1/744000138715890) | Courbevoie, fr |
| Sopra Steria | [Stage PPI - Juriste droit social France](https://jobs.smartrecruiters.com/SopraSteria1/744000135956173) | Courbevoie, fr |
| Sopra Steria | [Stage - Chargé(e) de projet Solidarités & Engagement citoyen](https://jobs.smartrecruiters.com/SopraSteria1/744000135648124) | Paris, fr |
| Sopra Steria | [Stage de fin d'études - Consultant(e) en Transformation digitale – Services Publics - IDF](https://jobs.smartrecruiters.com/SopraSteria1/744000128533061) | Courbevoie, fr |
| Sopra Steria | [Stage - Consultant PLM et Sustainability : ACV, DPP et CSRD - Colomiers](https://jobs.smartrecruiters.com/SopraSteria1/744000111047098) | Colomiers, fr |
| Sopra Steria | [Stage Chargé(e) de Recrutement - Services Financiers - Ile-De-France](https://jobs.smartrecruiters.com/SopraSteria1/744000099047104) | Paris, fr |
| Sopra Steria | [Stage - Chargé (e)  de Recrutement](https://jobs.smartrecruiters.com/SopraSteria1/744000091562029) | Colomiers, fr |
| Alten | [STAGE - Chargé de projet qualité](https://jobs.smartrecruiters.com/alten/744000146498239) | Vitrolles, fr |
| Alten | [Internship Offer – Product Owner (Project Management Tool)](https://jobs.smartrecruiters.com/alten/744000131167400) | Toulouse, fr |
| Ubisoft | [Internship 6 months - Technical Designer (F/M/NB) [AAA Project]](https://jobs.smartrecruiters.com/Ubisoft2/744000147274629) | Annecy, fr |
| Ubisoft | [Assistant(e) Chef(fe) de Projet Communication & Evènementiel - Stage 6 mois - (F/H/NB)](https://jobs.smartrecruiters.com/Ubisoft2/744000147273141) | Annecy, fr |
| Veepee | [Stage - Assistant(e) projet SIRH – Paie & Gestion des Temps (H/F/X)](https://jobs.lever.co/veepee/6c32487d-4531-49ea-b5fc-b1facc8de206) | Saint-Denis |
| Veepee | [Stage - Assistant(e) projet SIRH – Paie & Gestion des Temps (H/F/X)](https://jobs.lever.co/veepee/8c0231c4-d2c8-48fc-8752-491b2dd18a4c) | Saint Vulbas |
| Veepee | [Stage - Chargé(e) de recrutement H/F/X (Septembre 2026)](https://jobs.lever.co/veepee/71bfb72b-ab2e-410e-8db4-4dadaaa264b2) | Saint-Denis |
| Siemens | [Stage - Chaîne logistique et approvisionnements f/h](https://jobs.siemens.com/en_US/externaljobs/JobDetail/514945) | Haguenau, Grand-Est, France |
| Siemens | [Stage - Planificateur de production f/h](https://jobs.siemens.com/en_US/externaljobs/JobDetail/521533) | Haguenau, Grand-Est, France |

### Outside France - 59 (sample below)

| Company | Title | Location |
|---|---|---|
| Qonto | [Social Media Werkstudent (m/w/d)](https://jobs.lever.co/qonto/cb2053c9-938e-4b73-a3c8-d8d42243b301) | Berlin |
| Aircall | [Regional Marketing Intern - NA Market](https://jobs.lever.co/aircall/0fbc9b05-520b-4cbb-a276-5a9a75e8f3bf) | San Francisco Office |
| Aircall | [Regional Marketing Intern, LATAM (12 months)](https://jobs.lever.co/aircall/0e52ec00-a327-49de-9378-6b8487229f89) | San Francisco Office |
| Aircall | [Sales Intern - UKI Market](https://jobs.lever.co/aircall/f1d2fb78-a40b-4a33-ab8f-75e573ba9749) | London Office |
| Aircall | [Sales Partnerships Intern](https://jobs.lever.co/aircall/462b6547-d555-4e5f-b5a2-ea8c2de46101) | Madrid Office |
| Back Market | [Business Development Intern (HK 6-month Full-Time Internship)](https://jobs.ashbyhq.com/backmarket/1d015812-58ea-4f4e-a2c2-81db4fc40129) | Hong Kong |
| Shift Technology | [Data Science Internship](https://job-boards.greenhouse.io/shifttechnology/jobs/7673330003) | Singapore - Singapore |
| Shift Technology | [Data Science internship - Spanish speaker (6months)](https://job-boards.greenhouse.io/shifttechnology/jobs/7687752003) | Spain - Madrid |
| Shift Technology | [Data Scientist Intern (English Speaker)](https://job-boards.greenhouse.io/shifttechnology/jobs/7652429003) | Mexico - Mexico City |
| Amadeus | [Intern - Customer Management Operations](https://amadeus.wd502.myworkdayjobs.com/en-US/jobs/job/Taguig-Metro-Manila/Intern---Customer-Management-Operations_R37261) | Taguig-Metro-Manila, R37261 |
| Amadeus | [Cybersecurity Intern](https://amadeus.wd502.myworkdayjobs.com/en-US/jobs/job/Taguig-Metro-Manila/Cybersecurity-Intern_R31596) | Taguig-Metro-Manila, R31596 |
| Amadeus | [Software Developer Intern](https://amadeus.wd502.myworkdayjobs.com/en-US/jobs/job/Taguig-Metro-Manila/Software-Developer-Intern_R31590) | Taguig-Metro-Manila, R31590 |
| Amadeus | [Software QA Engineering Intern](https://amadeus.wd502.myworkdayjobs.com/en-US/jobs/job/Manila-Metro-Manila/Software-QA-Engineering-Intern_R29236) | Manila-Metro-Manila, R29236 |
| Murex | [Murex Internship](https://murex.wd3.myworkdayjobs.com/en-US/MurexCareerPage1/job/Beijing/Murex-Internship_JR101126-1) | Beijing, JR101126; Intern |
| Sopra Steria | [Stage Business Analyst – Reporting & Controlling](https://jobs.smartrecruiters.com/SopraSteria1/744000146410169) | ASSAGO, it |

---

## Defence, Finance & Silicon Watch

`board3.html` &middot; sweep of 2026-09-07

### Unrecognised location - 4

| Company | Title | Location |
|---|---|---|
| Airbus | [Landing Gear Technical Engineering Intern](https://ag.wd3.myworkdayjobs.com/en-US/Airbus/job/Bristol-Area/Landing-Gear-Technical-Engineering-Intern_JR10430645) | Bristol-Area, JR10430645 |
| Airbus | [INTERNSHIP + MASTER ON COMPOSITE MATERIALS 2021 - 11th Edition](https://ag.wd3.myworkdayjobs.com/en-US/Airbus/job/INTERNSHIP---MASTER-ON-COMPOSITE-MATERIALS-2021---11th-Edition_JR10069906) | INTERNSHIP---MASTER-ON-COMPOSITE-MATERIALS-2021---11th-Edition_JR10069906, JR10069906; Internship / Stage / Praktikum / Beca |
| Dassault Aviation | [Amélioration continue - Qualité - Stage F/H](https://dassault-aviation-cand.talent-soft.com/offre-de-emploi/emploi-amelioration-continue-qualite-stage-f-h_15028.aspx) | - |
| HPE | [Contract Administrator (Internship)](https://hpe.wd5.myworkdayjobs.com/Jobsathpe/job/Heredia-Heredia-Costa-Rica/Contract-Administrator--Internship-_1213007/apply) | Heredia, Heredia, Costa Rica |

### Not tech - 286 (showing the first 60)

| Company | Title | Location |
|---|---|---|
| Thales | [STAGE -  Chargé de Projets RH - F/H](https://thales.wd3.myworkdayjobs.com/en-US/Careers/job/Meudon/STAGE----Charg-de-Projets-RH---F-H_R0339361) | Meudon, Intern/Trainee (Fixed Term) (Trainee); R0339361; 12 - HUMAN RESOURCES; Thales |
| Thales | [STAGE - Contrôleur de gestion Offres et Projets - H/F](https://thales.wd3.myworkdayjobs.com/en-US/Careers/job/Bordeaux/STAGE---Contrleur-de-gestion-Offres-et-Projets---H-F_R0334380-1) | Bordeaux, Intern/Trainee (Fixed Term) (Trainee); R0334380; 11 - FINANCE; Thales Avs France Sas |
| Thales | [STAGE - Project Support for Contract Management Transformation - H/F](https://thales.wd3.myworkdayjobs.com/en-US/Careers/job/Meudon/Stagiaire-Contract-Management---PMO_R0326789-1) | Meudon, Intern/Trainee (Fixed Term) (Trainee); R0326789; 13 - LEGAL, CONTRACTS & COMPLIANCE; Thales |
| Thales | [STAGE - Legal M&A - F/H](https://thales.wd3.myworkdayjobs.com/en-US/Careers/job/Meudon/STAGE---Legal-M-A---F-H_R0321910-1) | Meudon, Intern/Trainee (Fixed Term) (Trainee); R0321910; 13 - LEGAL, CONTRACTS & COMPLIANCE; Thales |
| Airbus | [Stage Peintre Aéro / Opérateur(trice) matériau composite H/F](https://ag.wd3.myworkdayjobs.com/en-US/Airbus/job/Salaunes/Stage-Peintre-Aro---Oprateur-trice--matriau-composite-H-F_JR10438249) | Salaunes, JR10438249 |
| Airbus | [Testia SAS – Stage Comptabilité (H/F) – Toulouse](https://ag.wd3.myworkdayjobs.com/en-US/Airbus/job/Toulouse-Area/Testia-SAS---Stage-Comptabilit--H-F----Toulouse_JR10437292) | Toulouse-Area, JR10437292 |
| Dassault Systemes | [STAGE - Chargé de Marketing Operations & Lead Management (F/H)](https://www.3ds.com/careers/jobs/stage-charge-de-marketing-operations-lead-management-f-h-549798) | France, Vélizy-Villacoublay |
| Dassault Systemes | [STAGE - Chargé de marketing (F/H)](https://www.3ds.com/careers/jobs/stage-charge-de-marketing-f-h-548955) | France, Vélizy-Villacoublay |
| Dassault Systemes | [STAGE - Chargé de Planification Stratégique (F/H)](https://www.3ds.com/careers/jobs/stage-charge-de-planification-strategique-f-h-549108) | France, Vélizy-Villacoublay |
| Dassault Systemes | [STAGE - Assistant stratégique et communication auprès de la Directrice Générale Adjointe EMEA (F/H)](https://www.3ds.com/careers/jobs/stage-assistant-strategique-et-communication-aupres-de-la-directrice-generale-adjointe-emea-f-h-548943) | France, Vélizy-Villacoublay |
| Dassault Systemes | [STAGE - Chargé de développement commercial (F/H)](https://www.3ds.com/careers/jobs/stage-charge-de-developpement-commercial-f-h-548803) | France, Vélizy-Villacoublay |
| Dassault Systemes | [STAGE - Adoption Utilisateur 3DEXPERIENCE (F/H)](https://www.3ds.com/careers/jobs/stage-adoption-utilisateur-3dexperience-f-h-549115) | France, Vélizy-Villacoublay |
| Dassault Systemes | [STAGE - Digital Learning (F/H)](https://www.3ds.com/careers/jobs/stage-digital-learning-f-h-549132) | France, Vélizy-Villacoublay |
| Dassault Systemes | [STAGE - Ingénieur technico-commercial CATIA (F/H) - Aix-en-Provence](https://www.3ds.com/careers/jobs/stage-ingenieur-technico-commercial-catia-f-h-aix-en-provence-549246) | France, Aix en Provence |
| Dassault Systemes | [STAGE - Assistant Tech-Sales (F/H)](https://www.3ds.com/careers/jobs/stage-assistant-tech-sales-f-h-549411) | France, Paris |
| Dassault Systemes | [STAGE – Analyste en gestion des risques (F/H)](https://www.3ds.com/careers/jobs/stage-analyste-en-gestion-des-risques-f-h-549514) | France, Vélizy-Villacoublay |
| Dassault Systemes | [STAGE - Chargé de Planification Stratégique (F/H)](https://www.3ds.com/careers/jobs/stage-charge-de-planification-strategique-f-h-549714) | France, Vélizy-Villacoublay |
| Dassault Systemes | [STAGE - Ingénieur Avant-vente CATIA AI Engineering (F/H)](https://www.3ds.com/careers/jobs/stage-ingenieur-avant-vente-catia-ai-engineering-f-h-549698) | France, Aix en Provence |
| Dassault Systemes | [STAGE - Ingénieur Technico-Commercial (F/H)](https://www.3ds.com/careers/jobs/stage-ingenieur-technico-commercial-f-h-549697) | France, Meudon La Foret |
| Dassault Systemes | [STAGE – Chargé de Communication Stratégique (F/H)](https://www.3ds.com/careers/jobs/stage-charge-de-communication-strategique-f-h-549041) | France, Vélizy-Villacoublay |
| Dassault Systemes | [STAGE - Chargé de missions RH Brands, Industry & Marketing (F/H)](https://www.3ds.com/careers/jobs/stage-charge-de-missions-rh-brands-industry-marketing-f-h-549138) | France, Vélizy-Villacoublay |
| Dassault Systemes | [STAGE - Assistant Marketing Digital (F/H)](https://www.3ds.com/careers/jobs/stage-assistant-marketing-digital-f-h-549189) | France, Meudon La Foret |
| Dassault Systemes | [STAGE – Juriste contrats - nouvelles technologies (F/H)](https://www.3ds.com/careers/jobs/stage-juriste-contrats-nouvelles-technologies-f-h-549099) | France, Vélizy-Villacoublay |
| Dassault Systemes | [STAGE - Fiscaliste (F/H)](https://www.3ds.com/careers/jobs/stage-fiscaliste-f-h-549045) | France, Vélizy-Villacoublay |
| Dassault Systemes | [STAGE- Chargé de projet formation (F/H)](https://www.3ds.com/careers/jobs/stage-charge-de-projet-formation-f-h-549327) | France, Vélizy-Villacoublay |
| Dassault Systemes | [STAGE – Communication Marque Employeur (F/H)](https://www.3ds.com/careers/jobs/stage-communication-marque-employeur-f-h-549331) | France, Vélizy-Villacoublay |
| Dassault Systemes | [STAGE - Manufacturing génératif — Marine & Offshore (F/H)](https://www.3ds.com/careers/jobs/stage-manufacturing-generatif-—-marine-offshore-f-h-549194) | France, Vélizy-Villacoublay |
| Dassault Systemes | [STAGE – Prix de Transfert (F/H)](https://www.3ds.com/careers/jobs/stage-prix-de-transfert-f-h-549037) | France, Vélizy-Villacoublay |
| Dassault Systemes | [STAGE - Chargé de missions RH internationales (F/H)](https://www.3ds.com/careers/jobs/stage-charge-de-missions-rh-internationales-f-h-549330) | France, Vélizy-Villacoublay |
| Dassault Systemes | [STAGE - Gestionnaire de paie (F/H)](https://www.3ds.com/careers/jobs/stage-gestionnaire-de-paie-f-h-549718) | France, Vélizy-Villacoublay |
| Dassault Systemes | [STAGE - Business Developper (F/H)](https://www.3ds.com/careers/jobs/stage-business-developper-f-h-549188) | France, Meudon La Foret |
| Dassault Systemes | [STAGE - Gestion de la Continuité d'Activité et Résilience Opérationnelle (F/H)](https://www.3ds.com/careers/jobs/stage-gestion-de-la-continuite-d-activite-et-resilience-operationnelle-f-h-549676) | France, Vélizy-Villacoublay |
| Dassault Systemes | [STAGE - Construction d’un modèle de décision médicale partagée en intégrant le jumeau numérique/virtuel du patient (F/H)](https://www.3ds.com/careers/jobs/stage-construction-d-un-modele-de-decision-medicale-partagee-en-integrant-le-jumeau-numerique-virtuel-du-patient-f-h-549383) | France, Valbonne |
| Dassault Systemes | [STAGE – Communication Marque Employeur (F/H)](https://www.3ds.com/careers/jobs/stage-communication-marque-employeur-f-h-549331) | France, Vélizy-Villacoublay |
| Dassault Systemes | [STAGE - Chargé de missions RH internationales (F/H)](https://www.3ds.com/careers/jobs/stage-charge-de-missions-rh-internationales-f-h-549330) | France, Vélizy-Villacoublay |
| Dassault Systemes | [STAGE - Charge de projet RH "Management & Leadership" (F/H)](https://www.3ds.com/careers/jobs/stage-charge-de-projet-rh-management-leadership-f-h-549329) | France, Vélizy-Villacoublay |
| Dassault Systemes | [STAGE - Chargé des Ressources Humaines Europe (F/H)](https://www.3ds.com/careers/jobs/stage-charge-des-ressources-humaines-europe-f-h-549328) | France, Vélizy-Villacoublay |
| Dassault Systemes | [STAGE- Chargé de projet formation (F/H)](https://www.3ds.com/careers/jobs/stage-charge-de-projet-formation-f-h-549327) | France, Vélizy-Villacoublay |
| Dassault Systemes | [STAGE - Chargé d'événementiel (F/H)](https://www.3ds.com/careers/jobs/stage-charge-d-evenementiel-f-h-549314) | France, Meudon La Foret |
| Dassault Systemes | [STAGE - Manufacturing génératif — Marine & Offshore (F/H)](https://www.3ds.com/careers/jobs/stage-manufacturing-generatif-—-marine-offshore-f-h-549194) | France, Vélizy-Villacoublay |
| Dassault Systemes | [STAGE – Marketing opérationnel & digital (F/H)](https://www.3ds.com/careers/jobs/stage-marketing-operationnel-digital-f-h-549191) | France, Meudon La Foret |
| Dassault Systemes | [STAGE - Assistant Marketing Digital (F/H)](https://www.3ds.com/careers/jobs/stage-assistant-marketing-digital-f-h-549189) | France, Meudon La Foret |
| Dassault Systemes | [STAGE - Business Developper (F/H)](https://www.3ds.com/careers/jobs/stage-business-developper-f-h-549188) | France, Meudon La Foret |
| Dassault Systemes | [STAGE - Chargé de missions RH Brands, Industry & Marketing (F/H)](https://www.3ds.com/careers/jobs/stage-charge-de-missions-rh-brands-industry-marketing-f-h-549138) | France, Vélizy-Villacoublay |
| Dassault Systemes | [STAGE – Juriste lutte contre la contrefaçon (F/H)](https://www.3ds.com/careers/jobs/stage-juriste-lutte-contre-la-contrefacon-f-h-549103) | France, Vélizy-Villacoublay |
| Dassault Systemes | [STAGE – Juriste contrats - nouvelles technologies (F/H)](https://www.3ds.com/careers/jobs/stage-juriste-contrats-nouvelles-technologies-f-h-549099) | France, Vélizy-Villacoublay |
| Dassault Systemes | [STAGE - Fiscaliste (F/H)](https://www.3ds.com/careers/jobs/stage-fiscaliste-f-h-549045) | France, Vélizy-Villacoublay |
| Dassault Systemes | [STAGE – Chargé de Communication Stratégique (F/H)](https://www.3ds.com/careers/jobs/stage-charge-de-communication-strategique-f-h-549041) | France, Vélizy-Villacoublay |
| Dassault Systemes | [STAGE – Chargé de Marketing & Innovation 3DEXPERIENCE Lab (F/H)](https://www.3ds.com/careers/jobs/stage-charge-de-marketing-innovation-3dexperience-lab-f-h-549040) | France, Vélizy-Villacoublay |
| Dassault Systemes | [STAGE – Prix de Transfert (F/H)](https://www.3ds.com/careers/jobs/stage-prix-de-transfert-f-h-549037) | France, Vélizy-Villacoublay |
| Societe Generale | [Stage Conseiller Clientèle Particuliers](https://careers.societegenerale.com/offres-d-emploi/stage-conseiller-clientele-particuliers-26000JH1-fr) | France |
| Societe Generale | [Stage Conseiller Clientèle Particuliers](https://careers.societegenerale.com/offres-d-emploi/stage-conseiller-clientele-particuliers-26000JGK-fr) | France |
| Societe Generale | [Stage Conseiller Clientèle Particuliers](https://careers.societegenerale.com/offres-d-emploi/stage-conseiller-clientele-particuliers-26000JH3-fr) | Dunkerque, France |
| Societe Generale | [Market Performance Analyst](https://careers.societegenerale.com/offres-d-emploi/market-performance-analyst-26000JGZ-fr) | La Defense, France |
| Societe Generale | [Assistant Chargé de Relations Bancaires](https://careers.societegenerale.com/offres-d-emploi/assistant-charge-de-relations-bancaires-26000JLH-fr) | La Defense, France |
| Societe Generale | [Chargé(e) de partenariats Marketing](https://careers.societegenerale.com/offres-d-emploi/chargee-de-partenariats-marketing-26000GUP-fr) | Courbevoie, France |
| Societe Generale | [Pôle finance](https://careers.societegenerale.com/offres-d-emploi/pole-finance-26000JI1-fr) | La Defense, France |
| Societe Generale | [Stage Conseil Marché de l'entreprise](https://careers.societegenerale.com/offres-d-emploi/stage-conseil-marche-de-lentreprise-26000JJA-fr) | France |
| Societe Generale | [Juriste Conseil juridique et ingénierie patrimoniale](https://careers.societegenerale.com/offres-d-emploi/juriste-conseil-juridique-et-ingenierie-patrimoniale-260009UX-fr) | La Defense, France |
| Societe Generale | [Auditeur Interne - Banque de Détail, Banque Privée et Assurance en France](https://careers.societegenerale.com/offres-d-emploi/auditeur-interne-banque-de-detail-banque-privee-et-assurance-en-france-26000HQH-fr) | La Defense, France |

### Outside France - 734 (sample below)

| Company | Title | Location |
|---|---|---|
| Thales | [Software Engineering Intern](https://thales.wd3.myworkdayjobs.com/en-US/Careers/job/Zaventem_EXC/Software-Engineering-Intern_R0339364) | Zaventem_EXC, Intern/Trainee (Fixed Term) (Trainee); R0339364; 20 - SOFTWARE; Thales Cyber Solutions Belgium SA |
| Thales | [Software Development and Integration Engineer (Intern)](https://thales.wd3.myworkdayjobs.com/en-US/Careers/job/Singapore/Software-Development-and-Integration-Engineer--Intern-_R0339158) | Singapore, Intern/Trainee (Fixed Term) (Trainee); R0339158; 15 - HSE, REAL ESTATE, SECURITY, PERSONAL ASSISTANCE, MEDICAL WELFARE; Thales Solutions Asia Pte. Ltd. |
| Thales | [Software Engineer Intern - Middleware (IBS)](https://thales.wd3.myworkdayjobs.com/en-US/Careers/job/Singapore/Software-Engineer-Intern---Middleware--IBS-_R0334782) | Singapore, Intern/Trainee (Fixed Term) (Trainee); R0334782; 15 - HSE, REAL ESTATE, SECURITY, PERSONAL ASSISTANCE, MEDICAL WELFARE; Thales DIS (Singapore) Pte. Ltd. |
| Thales | [Internship as Defense System Engineer (Open also to Protected Categories, Law 68/99)](https://thales.wd3.myworkdayjobs.com/en-US/Careers/job/Firenze/Internship-as-Defense-System-Engineer--Open-also-to-Protected-Categories--Law-68-99-_R0338900) | Firenze, CW Intern/Trainee; R0338900; 18 - SYSTEM; Thales Italia S.P.A. |
| Thales | [Communications Intern](https://thales.wd3.myworkdayjobs.com/en-US/Careers/job/Singapore/Communications-Intern_R0338806) | Singapore, Intern/Trainee (Fixed Term) (Trainee); R0338806; 14 - COMMUNICATIONS; Thales Solutions Asia Pte. Ltd. |
| Thales | [Business App Support Intern - 2027 Start](https://thales.wd3.myworkdayjobs.com/en-US/Careers/job/Singapore/Business-App-Support-Intern---2027-Start_R0301783) | Singapore, Intern/Trainee (Fixed Term) (Trainee); R0301783; 15 - HSE, REAL ESTATE, SECURITY, PERSONAL ASSISTANCE, MEDICAL WELFARE; Thales Solutions Asia Pte. Ltd. |
| Thales | [Junior IVVQ Engineer - Internship (Open also to Protected Categories, Law 68/99)](https://thales.wd3.myworkdayjobs.com/en-US/Careers/job/Firenze/Junior-IVVQ-Engineer---Internship--Open-also-to-Protected-Categories--Law-68-99-_R0337042) | Firenze, Intern/Trainee (Fixed Term) (Trainee); R0337042; 20 - SOFTWARE; Thales Italia S.P.A. |
| Thales | [Software Engineer Intern (C#)](https://thales.wd3.myworkdayjobs.com/en-US/Careers/job/SINGAPORE/Software-Engineer-Intern--C--_R0324316) | SINGAPORE, Intern/Trainee (Fixed Term) (Trainee); R0324316; 15 - HSE, REAL ESTATE, SECURITY, PERSONAL ASSISTANCE, MEDICAL WELFARE; Thales DIS (Singapore) Pte. Ltd. |
| Thales | [Customer Service & Sales Operations Internship](https://thales.wd3.myworkdayjobs.com/en-US/Careers/job/Mexico-City/Customer-Service---Sales-Operations-Internship_R0334316) | Mexico-City, Student/Work Experience (Fixed Term) (Seasonal); R0334316; 07 - CUSTOMER SERVICE; Thales DIS Mexico SA de CV |
| Thales | [Naval Architect Intern/Co op - Halifax](https://thales.wd3.myworkdayjobs.com/en-US/Careers/job/Halifax---Wilkinson/Naval-Architect-Intern-Co-op---Halifax_R0333841-2) | Halifax---Wilkinson, Student/Work Experience (Fixed Term) (Seasonal); R0333841; 19 - HARDWARE; Thales Canada Inc., Defence and Security |
| Thales | [Trainee NetSec - (Internship September 2026)](https://thales.wd3.myworkdayjobs.com/en-US/Careers/job/Zaventem_EXC/Trainee-NetSec----Internship-September-2026-_R0334747) | Zaventem_EXC, Intern/Trainee (Fixed Term) (Trainee); R0334747; 21 - ENGINEERING AND TECHNICAL SPECIALTIES; Thales Cyber Solutions Belgium SA |
| Thales | [Solution Customer Service Intern](https://thales.wd3.myworkdayjobs.com/en-US/Careers/job/So-Paulo/TUI-Solution-Customer-Service_R0333139-1) | So-Paulo, Intern/Trainee (Fixed Term) (Trainee); R0333139; 07 - CUSTOMER SERVICE; Thales DIS Brasil Cartoes E Solucoes De Tecnologia Ltda. |
| Thales | [Stagiaire Finance](https://thales.wd3.myworkdayjobs.com/en-US/Careers/job/Rabat/Stagiaire-Finance_R0334044-1) | Rabat, CW Intern/Trainee; R0334044; 11 - FINANCE |
| Thales | [Hardware Obsolescence Engineer - Internship (Open also to Protected Categories, Law 68/99)](https://thales.wd3.myworkdayjobs.com/en-US/Careers/job/Gorgonzola/Hardware-Obsolescence-Engineer---Internship--Open-also-to-Protected-Categories--Law-68-99-_R0333671) | Gorgonzola, CW Intern/Trainee; R0333671; 07 - CUSTOMER SERVICE; Thales Italia S.P.A. |
| Thales | [Technical Consultant Intern](https://thales.wd3.myworkdayjobs.com/en-US/Careers/job/So-Paulo/Technical-Consultant-Intern_R0332382-1) | So-Paulo, Intern/Trainee (Fixed Term) (Trainee); R0332382; 20 - SOFTWARE; Thales DIS Brasil Cartoes E Solucoes De Tecnologia Ltda. |

