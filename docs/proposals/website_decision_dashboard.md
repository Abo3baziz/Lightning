# Website decision dashboard

**Status:** proposal, ready to build. Owner asked for it on 2026-10-14. Builder: a Claude session (branch `claude/website-decision-dashboard` in **both** repos, per `AGENTS.md` § 6).
**Repo:** the website (`elfekimuhammed/Lightning_website`). This file is the brief; delete it once built and move what holds into the website README › Analytics and consent.

## 1. Why the current dashboard fails

`analytics/dashboard.html` shows numbers, not decisions. The owner cannot tell from it what to change, whether a change worked, or whether a number is real:

- No trend: every figure is one total for the period, with no comparison to the period before.
- No verdicts: the reader has to work out what matters across eight sections of tables.
- No confidence: 2 of 3 and 200 of 300 both show as 67%.
- No link from evidence to action, and no way to see whether a release (a new page version) helped.
- No data health: if the receiver script is out of date or data stopped arriving, nothing says so.

## 2. What the owner decides, and the signal for each

| Decision | Question | Signal | Data |
|---|---|---|---|
| Change navigation or copy | Can people find the download? | Downloads link on screen; went to Downloads; pressed a download; signed up without ever seeing Downloads | Page views tab |
| Fix the Downloads page | Do people who reach Downloads get the app? | Downloads-page presses ÷ Downloads-page views; wrong-platform presses; GitHub real downloads | Page views + GitHub downloads tabs |
| Where to post | Which channels bring people who download? | Download rate per source vs the site average | Page views tab |
| What to fix first | What is broken or slow, and for how many? | Errors, slow loads, dead taps, repeated clicks, each with % of page views and the page | Page views tab |
| Rewrite a section | Where do readers stop, what are they unsure about? | Biggest drop between consecutive sections; FAQ questions opened, with their text | Page views tab + the live page |
| Keep a page version | Did the last release help? | Current vs previous release of the same page, same rates, with confidence | Page views tab (release column) |
| Arabic investment | Do Arabic visitors behave differently? | Download and signup rates, Arabic vs English | Page views tab |
| Trust the numbers | Is data arriving, and is the script current? | Last row time, script version, dropped events, GoatCounter gap | Receiver meta |

## 3. Principles

1. **Verdicts first.** The page opens with at most five plain-language findings, each with what was seen, how sure it is, what to do, and a link to the evidence below.
2. **Every rate shows its certainty.** Wilson 90% interval (z = 1.645) on every percentage. Labels: *Clear* (n ≥ 100 and half-width ≤ 10 points), *Early sign* (n ≥ 30), *Too early* (otherwise, with "needs about N more page views, about D days at the current pace").
3. **Compare, don't just count.** Every key number shows the previous period of the same length, as a change with words ("up 12 from 40"), coloured by meaning, not by direction (guideline A16: "Chip by direction: Good or bad").
4. **One source.** All behaviour comes from the Page views tab. GoatCounter appears only in the data-health strip as a cross-check.
5. **Plain language.** Every code is translated (`eventLabel` already exists; extend it). Raw codes only inside collapsed details.
6. **Less, not more.** Anything that drives no decision goes into one collapsed "Details" area at the bottom.

## 4. Page layout, top to bottom

All copy follows `guideline/brand-voice.md`; headings Title Case (B02), buttons and labels sentence case, no caps anywhere, whole numbers, colours only from B03 with their meanings. Keep the key gate, Lock button and period buttons that exist today.

1. **Data health strip** (one line, always first). Last page view received (e.g. "12 minutes ago"), script version check, dropped events, the GoatCounter gap, and how many days of data exist. Green text when fine. Strong rose (B03: *errors only*) when the script is out of date or nothing arrived for 72 hours, with the fix in words ("Paste the latest receiver script and deploy a new version").
2. **What To Act On.** One to five verdict cards from § 5, sorted by impact (affected page views × severity). Each card: a one-sentence finding with numbers, a confidence label, two or three concrete options, and "See the evidence" (jumps to the block). When nothing qualifies: one card, "Nothing is clear yet", with the page views needed and days at the current pace. A finding is never shown as *Clear* below its minimum data.
3. **Key Numbers.** Five tiles: page views, download presses, real downloads (GitHub, period delta), signups sent, download rate (presses per 100 page views). Each with the previous-period value, the change in words, and a 7-point daily sparkline. Periods: 7, 14 and 28 days, each against the period before (needs 2× days of data; 28 + 28 = 56 ≤ 88). Drop the current 90-day option.
4. **The Path to a Download.** One funnel per device (Phone, Tablet, Computer), page-view based:
   1. Page views on pages other than Downloads.
   2. Downloads link on screen.
   3. Downloads page views (with how they arrived: from which page, or from outside the site; needs `from`, § 6).
   4. Download presses on the Downloads page, with wrong-platform presses called out.
   5. Real downloads from GitHub (all devices together; GitHub has no device split).
   A side branch from step 1: "Sent the signup without ever seeing Downloads". Mark the biggest drop between steps. State once, plainly: "Each step counts page views, not people: someone may see the link on one page and sign up on another."
5. **Trends.** Small multiples, not a dual axis: daily page views, daily download presses, daily signups, daily real downloads. Each line carries thin vertical markers for releases of the home page and the Downloads page (ids and names from `../version-registry.json`; the date is in the id, `UX-YYYY.MM.DD.NN`). Hover shows the day's value and any release that day.
6. **Channels.** Source (utm_source, else the referring site, else "Direct or unknown"), page views, download rate with its interval, and a verdict against the site average: *better*, *worse* or *no clear difference* (intervals that don't overlap mean different). Sources under 5 page views stay merged as today.
7. **Fix List.** One ranked list mixing errors, slow loads (phone LCP over 4 seconds), dead taps and repeated clicks. Each row shows what happened in words, the page, the share of that page's views affected, and the kind of fix ("broken file", "speed", "looks clickable"). It is ranked by affected page views.
8. **Content.**
   - The section reach curve for the chosen page (the bar list exists today), with the biggest drop called out in words.
   - The FAQ questions opened, by their real question text: read the Nth `#faq details summary` of that page, as `sectionNames` already does for headings.
9. **Did the Last Release Help?** Pick a page. Compare its current release with the previous one on the same rates (seen, went to Downloads, pressed, signup without seeing), with intervals and a verdict. Show "Too early" until both have 30 page views.
10. **Details** (one collapsed `<details>`):
   - browser, operating system and language splits
   - the existing usage list with codes
   - Allow-all journeys
   - the GoatCounter tables

## 5. Verdict rules

Rates are over the chosen period. *n* is the denominator. Each rule fires only at its minimum *n*. Its confidence label comes from the Wilson half-width (§ 3). Write each rule as a pure function `(data) → card | null` in one `rules` array, so it can be tested without a browser.

| id | Fires when | Min n | Finding (template) | Options |
|---|---|---|---|---|
| `hidden-on-phone` | phone: seen ÷ views < 30% | 50 phone views | "On phones the Downloads link was on screen in only {p}% of page views: it sits in the closed menu." | Show Downloads in the phone top bar outside the menu · Say "Download" in the hero line · Link Downloads from the signup band |
| `signup-instead` | signups without seeing Downloads ÷ all signups ≥ 50% | 10 signups | "{x} of {y} signups came from people who never saw the Downloads link: they may think signing up is how to get the app." | Say on the signup band that the app is free to download now · Put the Downloads link in the band · Ask after signup what they hoped to do (decision 15 in `OWNER.md`) |
| `downloads-page-leak` | Downloads-page presses ÷ its views < 40% | 30 views | "People reach Downloads but {p}% leave without pressing a download." | Check the page on a phone · Make the right platform obvious · Shorten what comes before the buttons |
| `wrong-platform` | wrong-platform presses ≥ 10% of presses | 20 presses | "{p}% of download presses were for another device (for example a phone pressing the Windows file)." | Show the build for the visitor's device first · Label platforms with device words |
| `good-channel` / `weak-channel` | a source's download-rate interval is wholly above / below the site's | 30 views from that source | "Visitors from {source} press a download {k}× as often as the site average." | Post more there / Change what you post there, or stop |
| `broken` | any error code on ≥ 2% of a page's views | 50 views of the page | "{error in words} on {page}, in {p}% of its page views." | (by kind) fix the file path / check the script / it's an ad blocker, no action |
| `slow-phones` | phone LCP median > 4 s | 30 measured | "On phones the main content takes {s} seconds to appear; {p}% wait more than 4." | Shrink the hero images · Load the wow animation later |
| `looks-clickable` | one dead-tap code on ≥ 3% of its page's views | 50 views | "{p}% of page views tap {thing} in "{section}", which does nothing." | Make it open or zoom · Make it look less like a button |
| `drop-off` | the largest drop between consecutive sections of a page > 30 points | 50 views | "On {page}, {p} points of readers stop between "{a}" and "{b}"." | Shorten or move "{a}" · Put the key message before it |
| `arabic-gap` | Arabic download rate interval wholly below English | 30 Arabic views | "Arabic visitors press a download less often ({a}% vs {e}%)." | Check the Arabic Downloads path · Check Arabic copy for the download |
| `release-effect` | current vs previous release of a page differ on any rule rate (non-overlapping intervals) | 30 views each | "Since {release}, {metric} on {page} went from {a}% to {b}%." | Keep it / roll back (link to the version archive) |

The options are suggestions for the owner, not actions the dashboard takes. **Never suggest adding a download button**: the owner decided against it (2026-10-14).

## 6. Data changes (receiver, client, notice)

The owner pastes the receiver by hand, so give the owner the **full** new `apps-script/AnalyticsEventsReceiverPatch.gs` (from `const ANALYTICS_SPREADSHEET_ID` to the end) with paste-and-deploy steps, as previous sessions did.

**Receiver (`AnalyticsEventsReceiverPatch.gs`)**
- `const ANALYTICS_SCRIPT_VERSION = '2026-10-xx.1';` returned as `meta.script_version` by `what=insights`. The dashboard holds the same string as `EXPECTED_SCRIPT_VERSION`: a mismatch turns the data-health strip strong rose.
- `meta`: `{script_version, last_row_at, rows_today, dropped_total}`.
- `daily`: one entry per Cairo date × device over the requested days: `views, seen, went_downloads` (Downloads-page views), `pressed` (page views with `download-app-…`), `started, submitted, signup_unseen, wrong_platform`.
- Errors, dead taps, FAQ and LCP **per page**: `{code, page, count, page_views}`, so the Fix List and Content can show shares of the page.
- `by_release`: per page and release, `{page, release, first, last, views, seen, went, pressed, submitted, signup_unseen}`.
- `from` breakdown for Downloads-page views: `{from, count}` (see client).
- Wrong platform: a phone (OS android or ios) pressing `-windows`/`-mac`/`-linux`, or a computer pressing `-android`.
- Keep every current field: the current dashboard and older data must keep working while the owner updates.
- Accept a new optional payload field `from` (regex `^[A-Za-z0-9._\/-]{0,80}$` or `outside`), stored in a new **last** column `From` of the Page views tab. New column at the end only: existing rows keep their positions. Update `ANALYTICS_PV_HEADERS` and the setup so the header cell is written.
- Keep `days` up to 88 (56 needed).

**Client (`js/analytics.js`)**
- Add `from` to the v2 payload. For a same-site referrer, use the page path the same way `page` is made (`index`, `ar/features`). For another site use `outside`, and for none use an empty string. Never the full URL and never a query string.

**Privacy Notice.** Section 2 of `privacy.html` and `ar/privacy.html` gains: "and, when you arrive from another page of this site, that page's name."
- Before editing, archive the live English page and give it a new release ID (README › Version identity and archive), as the 2026-10-14 sessions did.
- Do **not** raise `POLICY`: this is essential-tier data, not part of the consent choice. Change the README line that says to raise it, to: "raise it when what Allow all adds changes".

**Statistics** live in the dashboard: Wilson intervals, the overlap test and "needs about N more" (`N ≈ z²·p(1−p)/0.1² − n`, with p = 0.5 when unknown, and days = N ÷ the average daily page views of the period).

## 7. Charts

Load the `dataviz` skill before writing chart code. Use inline SVG with no library and a single hue per chart (Nile, or green for good-meaning series). Use small multiples, never two y-axes. Hover tooltips with a larger hit area. A "Show as table" toggle per chart. Dark mode through the page's tokens. Release markers are thin, Ink at low opacity, with a label on hover. Phone widths have no horizontal page scroll (charts scroll inside their card if needed).

## 8. Files

- **Website repo:**
  - `analytics/dashboard.html` (rebuild; keep the key gate and plain-language helpers)
  - `apps-script/AnalyticsEventsReceiverPatch.gs`
  - `js/analytics.js`
  - `privacy.html`, `ar/privacy.html`, `archive/`, `version-registry.json`, `versions.html`
  - `README.md` › Analytics and consent
  - tests in `apps-script/tests/` and `analytics/tests/`
- **App repo:**
  - `CHANGELOG.md`
  - `NOW.md` (remove the item when done)
  - `OWNER.md` (the paste-and-deploy step)
  - delete this file

## 9. Steps (commit and push each, per `AGENTS.md`)

1. **Receiver:** the new fields and `from` column, with tests in `apps-script/tests/receiver.test.js`. Add cases for every new field, the version, per-page errors and wrong platform. Old payloads must still store.
2. **Client:** `from`. Test in a browser: same-site, outside and none give `index`, `outside` and an empty string. No query string ever leaves.
3. **Rules and statistics** as pure functions, with a Node test, `analytics/tests/rules.test.js`. Each rule must fire on a fixture built to trigger it, stay silent below its minimum *n*, and give the right confidence label.
4. **Dashboard rebuild**, block by block in § 4 order. Extend `analytics/tests/gen-data.js` so each rule fires at least once. `analytics/tests/dashboard-smoke.js` must show no page errors, and no horizontal scroll at 390 px and 1280 px, in light and dark.
5. **Notice and archive**, then the README.
6. **Hand-off:**
   - the full receiver code and steps for the owner
   - the `OWNER.md` step
   - the changelog
   - merge both branches to `main`

## 10. Acceptance

- All three test scripts pass, plus `rules.test.js`.
- With generated data:
  - the first screen shows the health strip, at least one verdict card and the key numbers with previous-period changes
  - every percentage shows a confidence label
  - every verdict links to its evidence
- With an outdated script (an old `what=insights` answer without `meta`): the strip says to update and the page still renders from what exists.
- With no data: one honest "Nothing is clear yet" card with days to wait; no empty tables.
- Guideline A16 list passes: no caps, tone by meaning, whole numbers, no card in a card, no colour outside B03.
- No code, ID or query string from a visitor leaves the private sheet except as totals.

## 11. Out of scope

- A download button (owner: no).
- Telemetry inside the app.
- The two one-tap questions (decision 15 in `OWNER.md`).
- Moving off Apps Script, which is only needed past a few thousand page views a day.
