# Phase 2 — Source Verification

**Date:** 2026-09-22
**Gate (SPEC §11):** ≥200 real produced emails reachable across ≥8 requests, with
same-agency clusters for cross-request negatives.
**Method:** six parallel scouting passes (NextRequest, GovQA/other portals, MuckRock,
agency-hosted sites, journalism repositories, search-term hunting), then an independent verification pass over
each modality's top two candidates. Verifiers re-derived counts, downloaded files, and
opened them.

Where a scout and its verifier disagree, **the verifier wins** and the disagreement is
stated. Scout-only rows are quarantined in §2b and must not be relied on until checked.

---

## 1. Verdict: gate MET

Met, with margin, and met by *verified* sources rather than scouted ones.

**County of San Diego alone clears it** — a verifier counted, not estimated:

| Request | Topic | Emails | Format |
|---|---|---|---|
| 25-3152 | Alpine Community Planning Group | 915 | native `.eml` |
| 24-409 | UCSD / Geosyntec planning consultants | 570 | native `.msg` |
| 25-4697 | Harmony Grove Village South | 169 | native `.msg` |
| 25-5982 | CAIR / Gaza custodian search | 129 | native-text PDF, 1 email/file |
| 25-6426 | Ramona PLDO / Mt. Woodson | 55 | native `.msg` |
| 26-2399, 26-2335, 24-2328, 26-2612 | county land use | 27+24+24+22 | native `.msg` |

≈ **1,930 emails across 9 requests from one county**, in formats that need no OCR and no
email-boundary segmentation. Six of those nine are county land-use matters handled by Planning &
Development Services, which is exactly the in-agency negative structure SPEC §7.3.1 asks for.

Three further sources were independently verified to carry hundreds of emails each
(SF Public Works, San Clemente, Carlsbad USD), so the gate does not rest on one portal.

**What the gate does *not* establish**, and should be carried forward:

- "Produced" ≠ "responsive". SF DPW's own custodian says so in writing (§5), and SF
  departments redact *non-responsive* passages out of produced emails citing
  *City of San Jose v. Superior Court* (2017) 2 Cal.5th 608, 619. Positive labels from
  production membership are noisy in the over-production direction, as SPEC §7.2 anticipated.
- Document counts on every portal are inflated 2–6× by extracted inline images and by the
  same email being pulled from multiple custodian mailboxes. Every headline number in this
  document that came from a scout's raw count has been replaced with a verifier's deduped count.

---

## 2a. Ranked sources — verified

| # | Source | Platform | Agency / agencies | Access | Emails? | Format | Est. volume (verified) | Status |
|---|---|---|---|---|---|---|---|---|
| 1 | County of San Diego PRA portal | NextRequest, custom domain | County of San Diego (PDS, DPW, COB, Parks) | open JSON API, no key | yes | native `.msg`, native `.eml`, native-text PDF | ~1,930 emails / 9 requests counted; 16,134 `.msg` + 958 `.eml` portal-wide | **verified** |
| 2 | SF Public Works email productions | NextRequest | CCSF Dept. of Public Works | open JSON API, no key, browser UA required | yes | `.html` one-email-per-file, `-redacted.html.pdf` (native text), some `.txt`, some `.rtf` | ~700–1,400 distinct messages across ~19 requests after dedup | **verified ×3** |
| 3 | City of San Clemente | JustFOIA | City of San Clemente | one-POST JSON API, no account | yes | native-text PDF, Relativity/Nuix-style export, multi-email per file | 160 emails measured in 4 files; 48 requests with email productions, 4.15 GB | **verified** |
| 4 | Carlsbad USD CPRA archive | agency website, flat PDF list | Carlsbad Unified School District | plain HTTPS GET, no API | yes | one combined native-text PDF per request (letter + records) | ~450–650 messages across 16 of 174 packets | **verified** |
| 5 | Novato City Clerk cluster | MuckRock + CDN | City of Novato | CDN filename enumeration | yes | native-text PDF, one thread per file, sequentially numbered | ~875 emails across 2 fully enumerated requests | **verified** |
| 6 | SF "Immediate Disclosure Request" cluster | MuckRock + CDN | CCSF — Mayor, SFPD, DPH, City Attorney, DA, DPW, TTX, Airport, Library, PUC | HTML scrape + open CDN | yes | native-text PDF (Acrobat PDFMaker for Outlook); 7 true `.eml`; ~18% image-only | ~300–600 separable emails + ~400 recoverable by splitting combined PDFs | **verified** |
| 7 | City of Palm Springs | JustFOIA | City of Palm Springs | same JustFOIA API | yes | **image-only** Bates-stamped PDF (OCR required); 16 native `.msg` in zips | ~300–350 scanned emails + 16 `.msg` | **verified** |
| 8 | Livermore PD #141748 | MuckRock + CDN | Livermore Police Department | CDN download open; listing gated past page 10 | yes | native-text PDF, one email/file; ~28% image-only ads | 1,687 files — effectively **all negatives**, ~0 positives | **verified** |
| 9 | City of Los Angeles portal | NextRequest on `lacity.org` | City of LA (all departments) | JSON API, **50 results/query hard cap** | yes | Gmail print-to-PDF, native text, 1–19 messages/file | ~140 messages in one request; 2,005 "Angeles Mail" docs portal-wide but not enumerable | **verified, access-limited** |
| 10 | Flock/ALPR cluster | MuckRock + CDN | Santa Cruz PD, Belmont PD, NCRIC (+ zero-email siblings) | CDN open; `www` behind Cloudflare | yes | print-to-PDF; one 49 MB **PDF Portfolio** holding 131 emails | ~190–200 emails across only **3** email-bearing requests | **verified, narrower than scouted** |

### Per-source notes (verified)

**1. County of San Diego** — `https://pra.sandiegocounty.gov`. Best format found anywhere:
`file` reports `CDFV2 Microsoft Outlook Message`; headers, SPF/Exchange chains and attachments
intact. The `.eml` set is even easier (stdlib-parseable, with `In-Reply-To`/`References`
threading). Verifier downloaded doc 32979958 (118,784 bytes, req 24-409) and doc 52663271
(1,205,248 bytes, req 25-4697).
*Scout/verifier disagreement, material:* the scout claimed full-index enumeration of all
117,851 documents works. It does not — there is a hard 10,000-result window; page 199 works,
page 200+ returns HTTP 422. Shard by narrow `search_term` instead. The scout also said "a few
`.eml`"; there are 958, and 25-3152 alone holds 915 — the richest single production on the
portal, nearly missed.
Evidence: `/client/requests?page_number=1`, `/client/documents?search_term=.msg`,
`/client/requests/24-409/folders`, `/documents/32979958/download`.

**2. SF Public Works** — `https://sanfrancisco.nextrequest.com`. Verified three times across
two modalities, which is why it ranks second despite messier format. Two topically **disjoint**
clusters inside one department and one custodian of records (David A. Steinberg): the
encampment/tent family, and a vendor/corruption/named-event family. That is the cleanest
natural negatives design in the whole survey — same mail system, same signature blocks, same
external-sender banner, different subject matter.
*Verifier-vs-verifier:* on request 20-2456 one verifier counted 772 email *document records*
(490 `.html` + 268 redacted PDF + 14 `.txt`), another counted ~367 *unique* emails after
deduping filenames. Both are right; the difference is dedup. Use the deduped figure.
*Scout corrections:* 25-2701 is a trip-and-fall claim (2,498 of 2,879 docs are photos, 71
emails) and does **not** belong in the encampment cluster; 19-3409 released one bundled PDF,
not a per-email production; 20-2499's custodians are DPW staff mailboxes, not Supervisor
Vallie Brown; the proposed 646k-document full-index crawl is unnecessary.
Evidence: `/client/requests/20-2456/folders`, `/documents/5193649/download` (31,778 bytes,
exact header block confirmed), `/documents/29994040/download`, `/documents/35612837/download`.

**3. City of San Clemente** — `https://sanclementeca.justfoia.com`. One POST returns all 1,638
published requests *with full request text* in a single 953,738-byte response. Verifier
downloaded four productions and counted 160 top-level emails (~392 message texts including
quoted segments) from 4 requests; corpus-wide scan of all 152 email-seeking requests found 82
email files across 48 requests, 4.15 GB.
*Scout corrections:* "all native text, no OCR" is wrong — 43 of 116 pages (37%) in the flagship
production are image-only (email bodies are native; their attachments are often scans). The 66
zero-attachment requests are **not** no-records findings (no determination text exists in the
API; one sampled request asks for records that certainly exist). Cited request `PR-648-2026`
does not exist. Within-request duplication can hit 47% — dedupe on `(attachmentName, fileSize)`,
not `attachmentId`.
*Caveat:* `robots.txt` disallows `/publicportal/api/*` and `/Attachments/Download/*` with
`Crawl-delay: 10`, and a non-browser User-Agent gets 403. See §3.

**4. Carlsbad USD** — `https://carlsbadusd.net/87480_2`. Uniquely, request and production live in
*one PDF*, so request/production alignment is exact with no join. 174 packets, 18,164 pages,
161 distinct request IDs, 13 rolling supplements. 24 packets close with an explicit
"There are no responsive records to your request."
*Scout corrections:* the dominant email format is **Apple Mail / Outlook-for-Mac print** with
*no* `From:` label (bare sender line, then a weekday timestamp, then `To:`) — a detector keyed
on `^From:` or `---------- Forwarded message ----------` finds 12 of ~55 messages in the
flagship packet. Only 22 of 174 packets contain any email; the "Communications"/"Curriculum"
heuristic is wrong (both cited Communications packets are duds). The two largest email packets
(63-2025.2 Environmental Testing, 3,338 pp; 23-2026 SCHS AP Classes, 1,122 pp) were missed entirely.

**5. Novato City Clerk** — MuckRock. Full CDN enumeration verified: request 172966 =
884 sequential PDFs at `https://cdn.muckrock.com/foia_files/2024/12/13/NNNNN.pdf`, zero gaps,
~72% email (~635 emails); request 185422 = 241 PDFs, ~200–240 emails. Request 172966's text
*is* a keyword list (§5).
*Scout corrections:* the file the scout flagged as "a disclosability log"
(`_N275-080524_Disclosable_1_R.pdf`) is a 185-page concatenated production *volume* containing
78 more emails — "Disclosable volume 1, Redacted". **There is no log.** The DocumentCloud-derived
counts ("1,342 emails confirmed") are not reproducible. Text quality is *better* than reported:
the CDN PDFs are clean native text; the mangled characters the scout saw are a DocumentCloud
`.txt` re-rendering artifact. Request 214441 is still rolling — treat its volume as unknown.

**6. MuckRock SF IDR cluster** — 45 completed requests, all San Francisco (not 39), 2,729 unique
CDN file URLs. Files are interleaved per-communication in the HTML, so you get
(request text, cover letter, produced file) triples for free. Request 88338 alone is a 558-page
native-text PDF with ~215 discrete `From:` headers.
*Risk the scout missed:* ~38 of 45 requests come from a single anonymous requester using
near-identical boilerplate. Request-side lexical diversity is very low — a classifier evaluated
only here may be fitting one person's drafting style. Also: a MuckRock "request" is often a
rolling bundle of separately numbered sub-requests, so pair at the **cover-letter level**, not
the request level.

**7. Palm Springs** — same JustFOIA API. Nearly all emails are 300 dpi image-only PDFs
(`pdftotext` returns exactly 0 chars on 13/13 sampled). Verifier's visual classification of 42
sampled pages gives ~300–350 emails, not the scout's ~550. **The search-term bonus does not
exist**: CC-1361-2025 *asked for* search-term logs; the City answered with 24 audit-trail
exports containing none (the string "search term" appears once, inside the reproduced request
text). Its real value is §5's "Not Responsive" stamps and 16 native `.msg` files in
`*_Natives.zip`.

**8. Livermore PD #141748** — a **negatives mine, not a balanced request**. Every one of 20
documents opened was third-party inbound mail: Apple News digests, IACP newsletters, DDA Monday
Morning Memos, GovX/Vortex tactical-gear ads. ~0 true positives. Two hard constraints the scout
missed: the files listing returns HTTP 401 past page 10 ("Please create an account and log in to
see results for pages beyond the first 10"), so ~687 of 1,687 filenames need a free account; and
~28% of the sample is image-only with **zero** of the 11 search terms in the text layer, so those
are not usable keyword-hit negatives without OCR.

**9. City of Los Angeles** — the portal is genuinely open and the emails are clean, but
**pagination is completely non-functional**: `page`, `per_page`, `offset`, `limit` are all
silently ignored on `/client/requests` and `/client/documents`, including the scout's proposed
`page=N&search_term=` workaround (pages 1/2/3 returned byte-identical payloads). Hard ceiling
is 50 documents / 100 requests per distinct query string against 60,232 documents. There is no
request→documents endpoint. The `count` field is **not** a page count (doc 960399 has
`count=170` and is 4 pages) — the scout read it as one. Worst of all, request 20-2414 (the best
hard-negative artifact in the portal, §5) has 51 produced files named `001.pdf`…`051.pdf`, which
are unreachable through the discovered API. Request 23-5978's production is login-gated.

**10. Flock/ALPR** — the selling point ("~11 agencies answering identical request text") does not
hold for email. Sonoma County Sheriff, Cotati PD and San Bruno PD produce **zero** emails
(contracts, policies, and 25–47 MB ALPR audit CSVs). Santa Cruz PD 203267 — the one email-rich
request — is a *different*, domain-scoped request that isn't in the template cluster at all.
Critical format trap: the 49 MB `Cecena.pdf` inside `Released_2026-09-03.zip` is a **PDF Portfolio**
holding 131 embedded email PDFs; `pdftotext` returns 92 characters. Use
`pdfdetach -saveall`.

---

## 2b. Unverified candidates (scout-only — do not rely on)

| Source | Agency | Why it might matter | What is unverified |
|---|---|---|---|
| Orange County HCA ambulance-RFP family | OC Health Care Agency | native `.msg`, 8+ overlapping requests on one procurement, agency publishes hit-set-vs-released arithmetic and a written narrowed responsiveness definition (25-5039) | all of it; strongest unverified lead |
| BART e-mail Search Request Forms | BART | agency releases its **own filled search form** — boolean query, custodian mailboxes, date range, alongside the production (doc 13502395, req 22-92) | form is a scan; only one filled instance confirmed by a scout |
| City of Oakland | Oakland | 311,885 docs, 117,592 requests; RT-21352 publishes encampment search terms near-identical to SF's | email density; heavy building-permit dilution |
| City of San Diego | San Diego | 3,685 email-titled docs; 19-4460 is a raw Exchange search export | whether the batch PDFs have text layers |
| SF TTX 25-7541 | CCSF Treasurer/Tax Collector | 888 **Bates-numbered** PDFs — gaps in the Bates sequence are themselves a withholding signal | whether the Bates PDFs are emails at all |
| SF meta-requests 26-2361 / 26-2362 / 26-2358 | CCSF DPW | requester asked for the agency's own IT search tickets "including date ranges, custodians, and search terms"; 92 / 29 / 209 docs released | nobody opened the documents — highest-value unopened lead in the survey |
| Riverside #155628 | City of Riverside | only stated **non-responsiveness rule** found: "emails from Amazon Prime, customer service, amazon order confirmation, and deliveries were not provided because they are not responsive" | 411 email PDFs claimed, none opened by a verifier |
| NOCCCD #173948 | Fullerton College | diversifies agency type (community college district); 105 email PDFs | not verified |
| San Rafael / Richardson Bay RBRA | city + JPA | adds a joint-powers special district | scout found MS-Information-Protection stubs with no recoverable body |
| Berkeley PD / UC Berkeley PD | city PD + UC | adds a UC campus; several explicit "No Responsive Documents" outcomes | low volume (tens) |
| DocumentCloud API + `related_article` join | repository | MuckRock stamps each uploaded file with its request URL — a machine-readable request↔production join | rate-limited to ~25–30 anonymous calls/hr; one verifier was blocked for 40 min and could not reproduce the search API at all |
| EFF LAPD/Ring binders 19-4563 | LAPD | 3,096 pages of LAPD↔Ring email | **request text is not published** — fails the pairing requirement unless recovered from EFF |
| San Mateo GovQA archive | City of San Mateo | ~2,450 request→production pairs | ~zero emails (permits/plans) |
| Redding / Roseville / Bakersfield / Palmdale / Westminster JustFOIA | various | same one-POST API | thin, or (Bakersfield) no request text at all |
| CPUC portal | CPUC | 5,826 published requests with rich request text — best **request-text-only** corpus found | publishes **zero** documents; use for prompts, not productions |

---

## 3. Recommended acquisition plan

Pull three sources, in this order. Stop and reassess after (1) — it may be sufficient for phase 3.

### Step 1 — County of San Diego (primary positives, zero preprocessing)

Why first: native `.msg`/`.eml` means real RFC-822/MAPI structure, so no OCR, no email-boundary
segmentation, and ground-truth `From`/`To`/`Cc`/`Sent`/`Subject` for SPEC §5's prompt layout.

1. `GET https://pra.sandiegocounty.gov/client/requests?page_number=1..159` → all 15,862 requests
   with full `request_text`. 159 pages is safely under the 200-page cap.
2. Shard the document index by narrow topical terms so **each result set stays under 10,000**:
   `?search_term=Harmony%20Grove` (422), `Ramona` (250), `Mt%20Woodson` (155), `Majdal` (33),
   `.eml` (958), `email` (1,038). Union on each row's `pretty_id`.
3. Join document → request on `pretty_id` / `request_path`. Keep `state=="public"` only.
4. `GET https://pra.sandiegocounty.gov/documents/{id}/download` with a **browser User-Agent** and
   a `Referer` of the document page. Without a browser UA every download returns
   403 "You do not have permission to download that document" — this is a UA filter, not an
   access control, and it cost two scouts a wrong conclusion.

**Traps.** No per-request documents endpoint exists. `?request_id=`, `?folder_id=`, `?pretty_id=`
are all silently ignored and return the **full unfiltered index with HTTP 200** — a pipeline that
assumes they filter will mislabel every request. `search_term=24-409` title-matches; it does not
scope to that request. Pagination param is `page_number`; `page` is ignored.

**Start set:** 25-3152, 24-409, 25-4697, 25-5982 ≈ 1,780 emails, two of them with published
search terms.

### Step 2 — SF Public Works (negatives structure + the search-term trail)

Why second: this is where real hard negatives come from (§5), and where the two-cluster
in-department design lives.

1. `GET https://sanfrancisco.nextrequest.com/client/requests/{id}` → request text.
2. `GET .../client/requests/{id}/timeline` → the full custodian correspondence, including hit
   counts and non-responsiveness reasoning. **This is the payload**, not the documents.
3. `GET .../client/request_documents?request_id={id}&page_number=N` — 25 rows/page. `page_number`
   is the working parameter (verified by enumerating all 57 pages of 24-3826 to exactly 1,420
   unique ids); `page`, `offset`, `per_page`, `limit` are ignored. Timeline filename enumeration
   is **truncated** on large requests (70 of 605 on 21-5453), so do not use it to enumerate.
4. `GET https://sanfrancisco.nextrequest.com/documents/{id}/download` → 302 to a presigned S3 URL
   (~1,000 s expiry). **Browser UA required** (403 otherwise). Throttle: the tenant returns a
   12-byte `Retry later` body **under HTTP 200** after ~6–20 rapid calls, so status-code-only
   error handling will write garbage files.
5. Filter to `file_extension in (html, htm, rtf)` for clean positives; `pdf` second tier (native
   text, `pdftotext`); treat `.txt` as **calendar-item metadata dumps**, not emails; drop
   jpg/png/jpeg/gif entirely (signature logos are 68% of some productions).
6. Dedupe on `(folder_name stripped of -extracted, subfolder_name)` — those two fields give you
   custodian mailbox and email subject for free, without downloading a byte.

**Deadline:** documents carry `expiration_date` with `exempt_from_retention: false`. Request
24-987's files are stamped for purge **02/26/2027**. Harvest before then.

### Step 3 — City of San Clemente (second agency type, different vendor)

Why third: a small city on a different platform, with the City's own response letters and an
internal staff argument about responsiveness inside the production.

1. `POST https://sanclementeca.justfoia.com/publicportal/api/Search`, body
   `{"searchText":null,"languageCode":"en"}` → all 1,638 requests with complete request text in
   one response. Do **not** use `searchText` to filter (not full-text; returns 0 on real terms);
   filter client-side.
2. `GET /publicportal/api/Request?FullRequestNumber=PR-661-2026` → `responseDocAttachments[]`.
3. `GET https://sanclementeca.justfoia.com/Attachments/Download/{attachmentId}` (curl `-L`).

**Etiquette / caveats:** `robots.txt` is `Disallow: /` with `Crawl-delay: 10` and explicitly
excludes both the API and the download path; a default Python UA gets 403. Nothing blocks you
technically, but throttle to ≥10 s, send a browser UA, and — given this is ~4 GB from a small
city clerk's office — a courtesy note to the City Clerk before a bulk pull is the right call.
Dedupe on `(attachmentName, fileSize)`.

**Start set:** PR-660-2026 (379 pp, 53 emails), PR-17-2026 (324 pp, 62), PR-661-2026 (116 pp, 40),
PR-601-2026 (the adjacency partner to PR-17), plus PR-1012-2025 / PR-1157-2025 / PR-891-2025.

### Optional step 4 — Carlsbad USD (labels, not volume)

Cheap: scrape 174 `href`→label pairs off `https://carlsbadusd.net/87480_2` (files live on
`https://files.smartsites.parentsquare.com/3467/*.pdf`) and pull all 1.6 GB in under a minute.
Filenames are **not** derivable from request labels — you must keep the scraped mapping.
Worth it only for the agency-authored per-item responsiveness determinations (§5).

### Explicitly deferred

Livermore (negatives-only; revisit when building the negative set), MuckRock SF IDR (requester
monoculture), Palm Springs (OCR cost), LA City (enumeration ceiling), Flock (three requests).

---

## 4. Same-agency clusters available

These are the source of *real* cross-request negatives (SPEC §7.3.1). Adjacency is flagged
because SPEC asks for it as metadata.

**County of San Diego — Planning & Development Services** (high adjacency; same custodians, same
vocabulary, different project):
25-3152 Alpine Community Planning Group · 24-409 UCSD/Geosyntec planning consultants ·
25-4697 Harmony Grove Village South · 26-2612 Harmonia Estates subdivision ·
26-2335 Loma Del Sol Specific Plan · 25-3256 SB 450 tentative parcel map ·
25-6426 Ramona PLDO / Mt. Woodson trailhead · 25-6781 Ramona Archway DPW permits.
Plus 25-5982 (CAIR/Gaza custodian search) as a **low**-adjacency in-county negative.

**SF Public Works — cluster A, encampments** (very high adjacency; overlapping terms, disjoint
windows): 20-2456 (Jan–Jun 2020, 14 terms, all DPW accounts) · 20-2499 (Aug–Nov 2019, 4 terms,
8 DPW custodians) · 21-1493 → 21-3262 → 21-4338 → 21-5453 → 21-6321 (sequential date slices,
same terms, same mailbox) · 23-6249 · 23-6965 · 23-7322 · 24-987 · 24-7093 · 21-1027
(Recology/Nuru corruption — **same two custodian mailboxes as 20-2456, different topic**, which
is the single cleanest near-miss pair in the survey).

**SF Public Works — cluster B, vendors/events** (same department + custodian of records,
topically disjoint from A — use as A's negative pool and vice versa):
24-3826 (`@ingka.com` / `@midmarketcbd.org` domain-scoped) · 20-737 (Nuru personal email) ·
20-951 (Zuniga travel) · 23-847 (holiday party / Recology / Pankow / Webcor) ·
24-3362 (needle/fentanyl/tenderloin) · 23-4809 (APEC) · 25-2382 (bollard / union square /
smash and grab) · 25-1020 (NBA All-Star) · 25-10835 (Oceanwide) · 24-7524 (hotel names) ·
23-6444 (fentanyl/overdose).
**Free controlled cross-agency pair:** 23-6444 (DPW) and 23-6443 (SF DPH) were filed with the
*identical* keyword set — same query, two agencies, two productions. Note DPH's side is 12
merged batch PDFs with no custodian or subject metadata.

**City of San Clemente** — 412 address-specific permit/property requests in near-identical
wording with different addresses (ideal same-shape negatives), plus the hardest pair in the
corpus: PR-17-2026 (104/106 Avenida Buena Ventura) vs PR-601-2026 (101 Avenida Buena Ventura) —
same street, adjacent parcels, same code-enforcement subject. Governance cluster: PR-1012-2025,
PR-1157-2025 (sales-tax initiative), PR-891-2025 (council/manager/attorney emails).

**Carlsbad USD** — Ethnic Studies (04-2026, 04-2026.2, 64-2025, plus 33-2025 trustee comms
"relating to the Ethnic Studies course") · Mahmoud v. Taylor / religious opt-outs (60-2025 .1–.5,
rolling, ~95 emails — the same request text maps to disjoint document sets at different dates) ·
Environmental (63-2025, 63-2025.2) · Electrification (58-2025 ×3) · AP course structure (23-2026 ×2).

**Novato City Clerk** — 172966 (Lee Gerner Park encampment, keyword-scoped) · 185422 (named-pair
communications, people-scoped) · 214441 (ERF, rolling) · plus 177615 (homeless sweep protocols)
and 177499 (homelessness service requests), which the scout missed. Amy Cunningham is a custodian
in 172966 and a named subject in 214441; Marin County correspondents recur across both.

**Palm Springs** — HRC/antisemitism (CC-131-2024, biggest email pool) · Oswit Land Trust /
Prescott Preserve (CC-1157-2024, CC-1127-2024, CC-311-2024) · hotel TOT/code cluster, all from
one requester (CC-1046/1077/1043/872/1116/1123/1125/1126-2025).

**MuckRock SF** — Mayor ×5, SFPD ×6, DPW ×4, DPH ×4, DA ×4, City Attorney ×3. Best structure:
"Calendars and Emails" filed with near-identical text to three departments — 84162 (TTX),
84170 (Airport), 84172 (Library) — so agency B's production is a *guaranteed* true negative for
agency A's request while remaining stylistically identical.

**City of LA** — 21-11467 / 21-11468 / 21-11469: one identical pandemic-telecommuting request to
LAFD, LAPD and City Clerk; LAFD produced 14 docs, LAPD an email bundle, City Clerk found **no
responsive records**. A clean natural experiment, all three public.

---

## 5. Hard-negative leads (SPEC §12: "is there any source that publishes the search terms?")

**Answer: yes for search terms, no for a non-responsive log.** No California agency was found
that publishes a document-level list of keyword hits it deemed non-responsive. What exists is
better than nothing and in one case is close to ideal.

### Tier 1 — verified, agency-authored, quantified

**SF Public Works 24-987** (`/client/requests/24-987/timeline`) — the best artifact found. The
custodian writes the query and the hit counts into the public record:

> "The modified first search essentially didn't change: Keywords: 'encampment' OR 'encampments'
> OR 'tent' OR 'tents' OR 'planter' OR 'planters' still had more than 2,100 hits. The second had
> 145 hits: Keywords: 'homeless' OR 'unhoused.'"

then documents ~600 keyword hits withheld **as non-responsive in substance** (daily service-request
spreadsheets hitting on "planter"), and **releases a clip demonstrating the false positive**.

**SF Public Works 23-6965** — "more than 3,700 potentially responsive emails" identified vs 1,319
documents released, plus an explicit exclusion rule: "all of the emails I referenced would not be
responsive because Ian Schneider's name is included on a spreadsheet but not as a sender or
recipient … we will exclude such emails." (200+ emails in that class.)

**SF Public Works 24-7524** — the custodian names the category outright:
> "…the remaining files, **which are responsive based on the keywords but likely not the subject
> matter you're interested in**."

**Verified non-responsive keyword hits inside actual productions** — SF DPW 23-4809 ("APEC"):
a press-clips newsletter matching once in a link roundup; a Small Business newsletter matching on
"coincide with the APEC Summit"; a glass-replacement schedule using APEC only as a date anchor.
SF DPW 24-7524 ("Morgan"/"Westin"/"Hilton"/"Hyatt"/"Marriot"): a stock newsletter matching on
*JP Morgan*. These are real, released, agency-produced hard negatives — no synthesis required.
A verifier also confirmed that a released 24-987 email contains **zero whole-word matches** for
any requested term; its only "tent" occurrences are inside the word *content* in the security
banner, which strongly implies substring matching and explains the implausible hit counts.

**Requester-side exclusion rules (verified in request text):** 21-6321 "EXCLUDE any emails with
subjects that contain the phrase 'S.F.Clean Tent Count'" · 24-7093 "EXCLUDE teams chats containing
10 or more recipients and EXCLUDE calendar events" · 23-1090 excludes "S.F.Clean Tent Count"
subjects, Teams chats with 10+ recipients, calendar invites and logo/profile images ·
23-7322 spells out the boolean expansion ("cedar OR covid AND encampment OR tent — in other words
any email with: cedar and encampment / cedar and tent / covid and encampment / covid and tent")
and records a negotiated exclusion of SES Weekly / BSES Daily reports.

**Published search-term lists (verified verbatim):** SF 20-2456 — 14 terms (homeless, homelessness,
no lodging zone, encampment, encampments, tent, tents, 647(e), protest, black lives matter, looting,
riot, george floyd, curfew) · 19-3409 — 20 terms · 20-2499 — 4 terms · San Diego County 24-409 —
a negotiated eDiscovery protocol (date range, named individuals, named firms) · San Diego County
25-5982 — seven custodian mailboxes, keywords "CAIR, KARAMA, MAJDAL, GAZA", range Jan 2023–Nov 2025,
**and the produced PDFs are named by custodian+keyword** ("Taryell, Majdal, Email 3.pdf"), i.e.
free per-document custodian and keyword labels.

### Tier 2 — verified, message- or item-level determinations

- **Palm Springs in-document "Not Responsive" stamps.** `PSJO1157_0000289.pdf` carries a black box
  labeled in white text **"Not Responsive"** covering the top message of a thread, with the
  responsive message left visible below. Agency-labeled non-responsive content at *message*
  granularity inside a keyword-hit thread — exactly the target. Appeared in 1 of 20 sampled docs.
  No text layer, so finding them all needs OCR or black-rectangle detection.
- **MuckRock SF 88338 and 94374 redaction logs** name specific page numbers withheld as
  non-responsive, citing *City of San Jose v. Superior Court* (2017) 2 Cal.5th 608, 619 —
  e.g. "we redacted information that was non-responsive on pages 550 and 552-553".
- **San Clemente PR-17-2026** contains an internal City email adjudicating the production
  file-by-file: "I'm unclear why 'PR-1188-2023C (45).pdf' needs redaction, looks responsive to me.
  … We should be recommending that attorney-client privileged communications be withheld not
  redacted, they are not responsive." Same production carries the formal response letter
  ("currently identified six responsive files/records") and a search-criteria email listing
  mailbox scope, date range and `Search Terms:`.
- **San Clemente `EmailKeywords` field** — real (e.g. "EmailKeywords 2225 Calle Cidra, occupancy,
  pool", "Email Date Range 01/01/1983 to 12/31/1986") but **not** a disclosure policy: it is the
  JustFOIA intake notification for request X, swept up by a later search and produced in request Y.
  Opportunistic, and the term lists are thin.
- **Belmont PD** `Muckrock_ALPR_Responses.docx` walks items 1–20 with explicit determinations
  ("Item 2 — Amendments/Renewals: No responsive records") paired with an actual 39-message email
  production.
- **Carlsbad USD** — per-item dispositions inside every packet ("Responsive records are attached"
  vs "There has been no formal adoption of instructional materials" vs "There are no responsive
  records to your request"), 24 packets closing with a flat no-records finding, and 23-2026 pushing
  back on the requester's proposed terms.

### Tier 3 — a raw hit set with no filtering

**Livermore PD #141748** — the requester enumerated 11 terms ("Proud Boy", "Three Percenters",
"Stop the Steal", "QAnon", "Boogaloo", "Thin Blue Line", "Blue Lives Matter", "car caravan", …)
and LPD appears to have produced the raw hit set with essentially no responsiveness filtering:
1,687 files of newsletters and tactical-gear ads. Note this is an *inference from content*, not an
agency statement — LPD's only methodology language is boilerplate. Example read end-to-end: an LPD
lieutenant forwarding a WordPress notification from a blog called *Thin Blue Line Leadership* with
the body "FYI only" — 8 term occurrences, zero relevance.

### Unverified but high-value

**BART** publishes its own filled internal "e-mail Search Request Form" as a responsive record
(doc 13502395, request 22-92): requestor, date range Jan 2019–Mar 2022, four named custodian
mailboxes, and `Keywords to Search for: "Urban Alchemy" Or "BART's Strategic Homelessness Action
Plan"`, routed to "Upload to Next Request #22-92". Query + custodians + window + produced set all
public. Scanned, needs OCR. **Orange County HCA** publishes hit-set arithmetic
("over four thousand potentially responsive emails" vs 487 released) *and* the reason its search
over-captures ("the search results include communications between HCA and these parties that are
unrelated to the RFP … routine operations"), then memorializes a narrowed responsiveness definition
in the request text of 25-5039. **Riverside #155628** states a reusable exclusion rule verbatim.
**SF meta-requests 26-2361/26-2362/26-2358** may contain the agency's own IT search tickets
"including date ranges, custodians, and search terms" — 92/29/209 documents released, none opened.

**Implication for SPEC §7.3.** Real keyword-hit-but-non-responsive negatives are obtainable at
meaningful scale from SF DPW and Livermore. Synthetic hard negatives remain necessary for the
specific failure modes SPEC lists (wrong time window, same people/different subject), but the
"keyword hit in a signature block, quoted thread, or newsletter" category can now be sourced
from real productions and should be, so it can be reported separately from generated data.

---

## 6. Dead ends (do not re-scout)

**Platform/vendor level**
- **GovQA / `mycusthelp.com` / `govqa.us`** — public archives show request *text* only, no released
  documents, at Santa Monica, Manhattan Beach, Caltrans, Riverside, Torrance, CDCR. Long Beach and
  LA County expose files via presigned Azure SAS URLs but have 3 and 1 items respectively. San Mateo
  is the one substantial instance (~2,450 pairs) and is ~all permits/plans, no email.
- **Laserfiche WebLink** — general records repositories (agendas, minutes, permits), never
  per-request CPRA productions, and never paired with request text.
- **JustFOIA without `isSearchEnabled`** — Brea, Elk Grove, Rancho Mirage have the portal and no
  public browse path at all. Stockton has search enabled and 0 published. Bakersfield has 300
  published items with **no request text** (`publicDescription` is an internal case code,
  `fieldData: null`).
- **NextRequest tenants that publish nothing** — `hsr-ca` (1,404 requests / 0 docs), `la-mesa-ca`
  (1,710 / 0), `calbarca`, `shra`, `alamedacountyca`, `riversidecountyca` (all 0/0).
  `longbeach.nextrequest.com` 302s to a CivicPlus migration page.
- **CPUC** — 5,826 published requests, **2** published documents portal-wide. Request-text corpus only.

**API / access**
- **MuckRock `api_v1`** — HTTP 401 without a token; `api.www.muckrock.com` did not resolve.
  `www.muckrock.com` HTML is Cloudflare-challenged to curl (WebFetch/browser passes);
  `cdn.muckrock.com` is wide open to plain curl.
- **MuckRock `?jurisdiction=California-52`** does not actually filter — results include Georgia,
  Texas, Michigan. Filter client-side on the `/foi/<place-slug>-<id>/` path segment.
  `/place/california/` and `/jurisdiction/california-52/` are 404.
- **DocumentCloud search API** — aggressive anonymous rate limiting (HTTP 429 /
  Cloudflare 1015, `Retry-After` ~2,400–3,500 s after ~25–30 calls). Two verifiers were locked out
  entirely. `related_article` is populated per-document but **not query-indexed**. Full-text search
  is OR-ish, not phrase search. Get a token before relying on it.
- **NextRequest generally** — pages are Vue SPAs; a naive fetcher gets only the `<title>` and
  concludes the portal is empty. Direct S3 `asset_url` values are 403 without the signature.
  There is no per-request documents endpoint on any tenant. `search_term` matches document
  **titles only**, never body text, despite a `highlights` field that suggests otherwise —
  so you find email productions by filename convention, which is why agencies that name files
  `Email_00017_*.pdf` are disproportionately valuable.
- **Subdomain guessing** — ~170 JustFOIA and ~95 GovQA guesses yielded 11 and 8 live CA instances;
  ~90 NextRequest guesses mostly failed (note Berkeley is `cityofberkeleyca`, and San Diego County
  is on a custom domain, so guessing under `nextrequest.com` misses agencies). No vendor publishes a
  customer list. Find these from agency PRA landing pages instead.

**Content level**
- **UC and CSU** — Berkeley, Irvine, UCOP, Merced: process pages only, no logs, no posted records.
  No UC/CSU campus publishing a disclosure log with documents was found.
- **County offices of education and most K-12 districts** — SDCOE, Hayward USD, Los Rios, HBUHSD,
  Garden Grove USD, SDUSD, PAUSD: process pages only. Carlsbad USD appears to be genuinely unusual.
- **State agencies** — State Lands Commission, State Water Board, POST, Caltrans: intake/contact
  pages, no disclosure logs. POST's posted PDFs are press releases and redaction-notification memos.
  `prarequest.osi.ca.gov` is decommissioned.
- **LAPD CPRA Unit Manual v11** — policy only; imposes **no** requirement to document search terms
  or log non-responsive hits.
- **UCLA PD encampment cluster** (#163733/163751/163756/163763) — four beautifully near-identical
  keyword requests, but the productions are acknowledgment letters and "No Responsive Documents".
  Harvest for *request text* only.
- **Sonoma County Sheriff, Cotati PD, San Bruno PD Flock requests** — verified to contain zero emails.
- **No pre-existing dataset** pairing FOIA/CPRA request text with produced emails appears to exist.
  Searches returned eDiscovery vendor marketing and FOIA request *metadata* dumps. This is being
  built from scratch.
- **Generic web search** is useless for this modality — the material lives inside SPA portals that
  search engines do not index. Everything useful here came from probing portal APIs directly.

---

## 7. Data-quality notes

**Format tiers, by preprocessing cost**

| Tier | Format | Where | Cost |
|---|---|---|---|
| A | native `.msg` / `.eml` | San Diego County; Palm Springs `*_Natives.zip` (16 files); a few LA City | none — real headers, threading, attachments |
| B | `.html` one-email-per-file | SF Public Works | trivial strip; headers are plain text above the body |
| C | native-text PDF, one email/file | San Diego County, LA City, Novato, MuckRock SF, Livermore | `pdftotext -layout` |
| D | native-text PDF, many emails/file | San Clemente, City Attorney 88338 (558 pp), Carlsbad USD | needs page-level boundary segmentation |
| E | image-only PDF | Palm Springs (~95%), San Clemente (~37% of pages), MuckRock SF (~18%), Livermore (~28%) | OCR |

**Over-production and label noise.** SPEC §7.2 flagged this; it is confirmed and worse than
assumed. Production membership is a *noisy positive*: SF DPW's custodian explicitly released files
that are "responsive based on the keywords but likely not the subject matter you're interested in",
and SF departments redact non-responsive passages *out of* produced emails under
*City of San Jose*. Consider a two-tier positive label (produced / produced-and-plausibly-on-topic)
or holding the Livermore-style raw hit sets out of the positive class entirely.

**Duplication is severe and systematic.** The same email is pulled from several custodian mailboxes
and re-uploaded with hash suffixes. Measured: SF 24-987 744 file entries → 345 unique names (2.2×);
SF 23-6965 1,311 → 234 (5.6×); SF 24-7524's 89 documents are **four** email threads (48 copies of
one daily sheet); San Clemente PR-17-2026 43 attachments → 23 unique (47%); Novato reply chains
produce 9 PDFs each quoting all prior messages; Livermore ships the same newsletter under `_1`,
`_2`, `_3` suffixes. **Dedupe before any count and before any train/eval split**, or near-identical
text leaks across the split and the negative class ends up dominated by a handful of newsletters.

**Portal document counts are not email counts.** Extracted inline images (signature logos,
`image001.png`) are released as separate document records: 68% of SF DPW 24-3826, 505 of 1,606 in
SF 20-2456, 313 of 345 unique names in SF 24-987. Every headline "N documents" figure overstates
emails by 2–50×.

**Container traps.** Santa Cruz `Cecena.pdf` is a **PDF Portfolio** (`pdfdetach -saveall`, or you
silently lose 131 emails and score a 49 MB file as near-empty). Palm Springs and San Clemente ship
`.zip` bundles whose contents do **not** appear in the attachment manifest (CC-131-2024's zip holds
53 PDFs with zero name overlap with its 321 listed files). SF and Oakland ship per-custodian `.zip`
releases. Novato's `_Disclosable_1_R.pdf` is a 185-page concatenated volume, not a log.

**Text-layer hazards.** Carlsbad USD determination letters are saturated with invisible Unicode
format characters (U+202C/U+202B/U+200B/U+00AD) interleaved between words, and several packets drop
ligatures on extraction ("reques ng", "a ached", "no fied"). Normalize away Unicode category `Cf`
and handle fi/ti/tt dropout, or literal matching silently fails. Novato's clean native CDN text is
mangled only in DocumentCloud's `.txt` re-rendering — pull from the CDN.

**Leakage features to strip before scoring.** External-sender banners, which are agency-specific and
have **at least two variants per agency** ("***CAUTION*** This email was sent from outside of the
City of Livermore email system" on 2020 mail vs "Exercise Caution: This message is from outside the
City email system…" on later mail; "[EXTERNAL MAIL]"; SF's own banner — whose word *content*
contains the substring "tent" and appears to have driven SF's inflated hit counts). Also:
Outlook-web print headers carrying `outlook.office365.com` URLs; filenames that encode date +
subject + custodian (Riverside) or sequential production numbers (Novato `0001`–`0884`, LA
`Email_00001`–`000NN`); and sender **domain**, which in Livermore is a near-perfect giveaway of
non-responsiveness (govx.com, police1.com, bulletinmedia.com, insideapple.apple.com).

**Redaction artifacts.** Black boxes extract as garbage characters, as the literal word "Privacy"
(SF, LA), or as "REDACTED". San Rafael productions include Microsoft Information Protection stubs
with no recoverable body (`.rpmsg`). Budget a "no recoverable content" drop rule.

**Portal metadata worth keeping.** `folder_name` / `subfolder_name` (SF: custodian mailbox + email
subject, free, no download); San Diego County folder names double as production-wave metadata
("DPW - released 5.17.24", "OES - Ready to Release"); San Diego County 25-5982's filenames encode
custodian + keyword per document; SF TTX 25-7541 is Bates-numbered, so **gaps in the Bates sequence
are a withholding signal**.

**Retention clock.** SF NextRequest documents carry `expiration_date` with
`exempt_from_retention: false` (24-987 stamped for purge 02/26/2027). San Diego City has already
purged at least one request's records per its retention schedule. Harvest and archive, don't plan
to re-fetch.

**PII / redistribution.** These productions contain unredacted personal email addresses, direct
phone numbers, City employees' personal-account addresses (one PUC GM's personal Yahoo address
appears in a file named `…_Redacted.pdf`), names of homeless individuals behind imperfect
blackouts, and PHI-adjacent EMS material (Orange County). Lawfully public, but if the eval set is
redistributed we are republishing named individuals' contact details. A scrub pass before anything
leaves the machine.

---

## 8. Open questions for review

1. **Is production membership an acceptable positive label?** Given SF DPW's own "responsive based
   on the keywords but likely not the subject matter" release and the *City of San Jose*
   non-responsive redaction practice, how much over-production is normal? Should marginal
   productions (Livermore) be excluded from positives entirely, or kept with a flag?
2. **Is SF DPW's search representative?** The hit counts (2,100 for "encampment OR tent") plus a
   released email whose only "tent" is inside *content* in the security banner suggest substring,
   not whole-word, matching. Is that typical of how agencies actually run these searches, and should
   the negative set therefore include substring-only hits as a distinct category?
3. **Can the LA ITA productions be reached another way?** Request 20-2414 publishes literal boolean
   strings, custodian scope and date range across 17 per-custodian-per-boolean folders, but its 51
   files (`001.pdf`…`051.pdf`) are unreachable through the public API. Is there a route — a direct
   ask to the City Clerk, a different portal view — worth pursuing? It is the best unrealized
   hard-negative artifact found.
4. **Is a meta-CPRA request worth filing?** SF requests 26-2361/26-2362/26-2358 asked agencies for
   their own IT search tickets "including date ranges, custodians, and search terms" and got 92/29/209
   documents. Do agencies routinely retain such tickets, and would a targeted request to a
   cooperative agency produce a real non-responsive log — the one artifact this survey could not find?
5. **Agency-type coverage.** Everything ranked above is a city, a county department, a city PD or one
   K-12 district. Is that enough for the claim we want to make, or does the eval need a special
   district, a UC/CSU campus, or a state agency to be credible to this audience? (BART and Orange
   County HCA are the cheapest additions; both unverified.)
6. **`.msg` / `.eml` vs PDF-rendered email.** San Diego County gives real MAPI/RFC-822 structure;
   everything else gives a rendering. Does the header fidelity difference matter for the screening
   claim, or should all sources be normalized down to the PDF-rendered header block so the model
   sees one format?
7. **Scraping posture.** San Clemente's `robots.txt` disallows the API and the download path with a
   10 s crawl delay; the SF and San Diego portals filter non-browser User-Agents; several portals
   rate-limit. Nothing here requires an account and nothing is technically blocked. Where is the line
   for a ~4 GB pull from a small city clerk, and should we notify agencies in advance?
8. **Redistribution.** Given the PII noted in §7, what is acceptable to publish alongside the
   write-up — full emails, header-stripped bodies, hashes and URLs only?
9. **Blind spots.** Which California agencies that actually post productions did six scouting passes
   miss? There is no vendor customer list, so coverage is certainly incomplete, and a practitioner's
   knowledge of who posts what would be worth more than another sweep.
