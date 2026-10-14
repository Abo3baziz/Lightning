# Lightning User Feedback — Batch 003

- **Source:** Google Drive → `Lightning Data` (spreadsheet) → `App Feedback` tab; screenshots in Drive folder `AppFeedback`
- **Feedback date:** 14 October 2026 (20:36–20:55 Cairo, one tester, one session)
- **Processed:** 14 October 2026 · **Processed by:** Claude
- **Build / release:** 1.1.0-beta.1-windows · landing release UX-2026.10.13.15 · desktop
- **Coverage:** 18 submissions = worksheet rows **79–96** = Ticket # **78–95** (Ticket # is unique from here on). Rows 77–78 are empty; rows 71–76 were batch 002.
- **Not yet in the sheet:** Batch #, Processed on and Processed by are blank for these rows. Mark them `003 · reviewed` once handled.
- **Investigated and built:** 14 October 2026, Claude. Results are in *Outcome* at the end; do not reopen a Fixed ticket without reproducing it first.
- **Privacy:** sender, session ID and page URL are omitted. Screenshots are copied into this repo (below); the Drive originals stay private.
- **Sheet quirk:** for rows with a screenshot the Drive link landed in the **Batch #** column (L), not **Attachment URL** (Q). Read column L for rows 80–84, 91, 95, 96 when going back to the sheet. The website receiver is the likely cause.

## Screenshots

Open the PNG from the repo; no Drive access needed. Paths are relative to this file. Each file is named `<Ticket #>_<n>.png`. The red box in ticket 79's image is the tester's own mark.

| Ticket | Row | Image | Drive file ID (private) |
|---|---|---|---|
| 79 | 80 | [79_1.png](screenshots/batch-003/79_1.png) | `1H2SRj61ZM_oUduOpAp9JCpChxRpGEpUr` |
| 80 | 81 | [80_1.png](screenshots/batch-003/80_1.png) | `1Cw_jnWT0URDUT7-aVf1t5xxSi3O6ATaI` |
| 81 | 82 | [81_1.png](screenshots/batch-003/81_1.png) | `1H_UC5eYU_T4Fkjpat8YVuIon7__nnWJf` |
| 82 | 83 | [82_1.png](screenshots/batch-003/82_1.png) | `1yzkNPlW25khajZESpzSNqbY-SPuAN3Q1` |
| 83 | 84 | [83_1.png](screenshots/batch-003/83_1.png) | `1N68pCVVxM2IZT6IqP4eCIMCHmmkD-2vE` |
| 90 | 91 | [90_1.png](screenshots/batch-003/90_1.png) | `1WPtqXWjEsPycOQ1J1q1BB352gRJXkhJb` |
| 94 | 95 | [94_1.png](screenshots/batch-003/94_1.png) | `1dJ3BO0KSKnpn0T6bRry8DRfs76_gR9wa` |
| 95 | 96 | [95_1.png](screenshots/batch-003/95_1.png) | `1camBhQj_mUdidP4MfAN3sJoRRkfl9VFl` |

Drive naming: files are `<ticket>_<n>.<ext>` in the owner's `AppFeedback` folder; the Drive description holds `ticket N · screenshot n`. To fetch more later: search Drive `parentId = '1wy5_h3A1zy5lSRZ8EVBAAECmCq0k1fSH'` and download by file ID.

## Executive summary

Almost all of it is the **Overview** page and the way it explains itself. The tester finds it repetitive (two halves of a card say the same thing, tiles repeat), time-inconsistent (some cards follow the period, some do not), and hard to read (savings-rate page, Budget groups, Cash planning timeline). Two items are possible **calculation** defects: the investing rate (89) and the Net worth card against its own chart (80). One is a repeat of an earlier request (feedback upload speed, 88 = batch 002 row 76). Everything else is layout, grouping or styling.

## Investigation instructions for an AI

Per ticket: look at the screenshot, find the screen's template and the service that feeds it, reproduce with the demo profile, then report file paths, the function involved and a minimal reproduction. Rules:

- Read `AGENTS.md` first. The brand guideline is strict: `python tools/guideline.py A16` (before it ships), `A03` (colour meaning). Phone follows Part C, never reuse the PC layout.
- Money calculations stay in Python services, never templates or JavaScript. Plans move no money; investment capital movements are not income or expense.
- Tickets marked **Check first** may be defects in a number; the rest are design requests: judge them against the guideline and the Overview plan in `docs/PROJECT_OVERVIEW.md`, do not treat preference as a bug.
- Do not reopen anything batch 002 marks Fixed or Existing without reproducing it first. Overlaps are noted below.
- Code pointers are **unverified starting points** from a text search, not findings.

## Grouped feedback

### 1. Free cash and Your position cards (Overview)

**Tickets:** 80, 81, 83 · **Rows:** 81, 82, 84 · **Images:** 80, 81, 83

- **Ticket 81 (row 82, Bug, Visual) — "plan to invest is not placed correctly".** In the Free cash card the green *Plan to invest* button floats centred between the figure and the Cash-you-own row, off the card's left edge alignment and over the divider. See [81_1.png](screenshots/batch-003/81_1.png). Investigate: the button's container and its alignment against the card header/figure (guideline A-section for action buttons).
- **Ticket 83 (row 84, Improvement, Visual) — two halves do the same job.** Left: Cash you own − Reserves − Bills due = Free cash. Right "How it is built": the same three numbers as bars. Tester suggests the right side shows something new, "maybe the investments weight", and that the *If you sold today* card sits next to it with the *Net cash flow* card. See [83_1.png](screenshots/batch-003/83_1.png) (same card as 81). Repeat of batch 002 row 51 (marked *Existing redesign*: component breakdown added). The tester still sees the duplication, so the redesign did not solve it; the earlier suggestion was upcoming bills. A16: "A line that repeats its label: cut it."
- **Ticket 80 (row 81, Improvement, Visual) — "cards that do not change with time are confusing; now everything changes with the time horizon".** Screenshot [80_1.png](screenshots/batch-003/80_1.png) is Your position › Net worth with a red box over the empty top-right of the card. Read it as: every Overview card should respond to the selected period, or the page should say which ones do not. **Check first:** the card shows **431,877** "as of 2026-10-14" while the chart's last point reads **397,877** (2026-09, month-end) and *What you own* 481,967 − *What you owe* 50,090 = 431,877. The two numbers may be correctly "today" vs "last month-end", but the chart's final label vs the card figure will read as a mismatch to a user. Investigate: `lightning/planning/position.py`, `lightning/ui/templates/dashboard/index.html`, and which cards take the period filter.

### 2. Where money went (Sankey) and Net cash flow placement

**Tickets:** 78, 79, 82, 85, 86 · **Rows:** 79, 80, 83, 86, 87 · **Images:** 79, 82

- **Ticket 78 (row 79) — split the Sankey into two sections:** this month, and the last 6 months.
- **Ticket 82 (row 83) — show Kept, and the invested part of it in blue.** [82_1.png](screenshots/batch-003/82_1.png) shows *Kept 284,586 · 49%* as one green block; the owner wants the invested portion distinguished. Keep investment purchases out of "spent" (capital movement, not expense); the question is only how to show the split inside Kept.
- **Ticket 79 (row 80) — monthly Net cash flow heatmap should look like a real calendar, in months, with the same formatting as the daily one.** [79_1.png](screenshots/batch-003/79_1.png) shows a single row of 12 month tiles (J F M … D) for 2026 with +17k etc. Ask: a calendar-style grid (months as the cells, years down) matching the day calendar's styling. Investigate the renderer for the day calendar (`day_calendar`) and the month one in `lightning/ui/visuals.py` / `partials/charts.html`.
- **Ticket 85 (row 86) — remove Net cash flow from the Spending tab** ("makes no sense to track it by the day").
- **Ticket 86 (row 87) — put the by-month Net cash flow on Overview; keep the expenses calendar on Spending.** Tickets 79, 85 and 86 are one change: Overview owns monthly net cash flow, Spending owns the daily expenses calendar only. Contradicts the batch 002 row 64 outcome ("net cash flow is a separate secondary view" on Spending); confirm with the owner before removing. Check phone parity (Part C).

### 3. Overview structure, rates and readability

**Tickets:** 84, 87, 89 · **Rows:** 85, 88, 90

- **Ticket 84 (row 85) — group the "Needs you" tiles.** Six separate items; wants categories, each opening a page listing its items. Start at `lightning/ui/keynotes.py` (tile builder). A16: "Five or more names: Four, then Other."
- **Ticket 87 (row 88) — "Savings rate over time is a good chart; the rest of the page is very hard to read".** The page is most likely Financial health (`lightning/ui/templates/financial_health.html`, `lightning/reporting/service.py`). The owner gave no screenshot; open the page in the demo profile and list what is hard to read before proposing structure.
- **Ticket 89 (row 90, Bug, Technical) — investing rate. Check first.** "Review how you calculate investing rate; calculate it as a % of free cash in that period, and remove it from the waffle charts, leave saving rate only." Investigate the current definition and denominator (`lightning/core/figures.py`, `lightning/investments/report.py`, `lightning/ui/routes/dashboard.py`), whether "free cash in the period" is well defined (a stock, not a flow), and the Glossary entry. Report the formula and a numeric example from the demo profile; do not change the figure's name without updating the Glossary.

### 4. Budget

**Tickets:** 90, 93 · **Rows:** 91, 94 · **Image:** 90

- **Ticket 90 (row 91) — "this looks empty".** [90_1.png](screenshots/batch-003/90_1.png): a single *Categories over plan 3* tile (Utilities & Bills, Food & Groceries and 1 more) in a mostly blank area, only a gear icon top right. Investigate whether other tiles failed to render (data/period) or the layout leaves a lone tile at about 60% width. Check the A16 rule on "Vivid gradient card" too: the tile is a strong pink gradient.
- **Ticket 93 (row 94) — Spending by group is awkward to navigate.** Table headers are fine; the sections are "weird". Start at `lightning/ui/templates/budget.html` and the phone twin. Ask the owner what "sections" means if it is not clear from the page.

### 5. Cash planning

**Tickets:** 94, 95 · **Rows:** 95, 96 · **Images:** 94, 95

- **Ticket 94 (row 95) — the next-30-days visual is hard to read.** [94_1.png](screenshots/batch-003/94_1.png): a timeline with labels stacked at "Today" (Landlord −12,000, Car loan −2,500, Vodafone −350, all due) and again mid-month, truncated names ("North Cairo Ele…"), and the income marker ACME Egypt +50,000 above the line. Change it or declutter it. Investigate collision handling for same-day labels, truncation, and whether overdue items should collapse into one "due now" group. Source: `lightning/ui/templates/planning/plan.html`, `style.css` (search "next 30 days").
- **Ticket 95 (row 96, Bug, Visual) — What you owe card needs a toggle and the note font is odd.** [95_1.png](screenshots/batch-003/95_1.png): *Bills due* has the small-font text "other than loan payments" next to a larger label; the card's rows have no expand chevron, unlike *Reserves* and *Bills due* in the Free cash card. Make the rows expandable the same way and set the note in one consistent size. Source: `lightning/planning/position.py` (the label), `plan.html`.

### 6. Import CSV, hover, feedback form

**Tickets:** 88, 91, 92 · **Rows:** 89, 92, 93 · **No screenshots**

- **Ticket 91 (row 92) — the Attach file button is not styled.** The native file input is unstyled; restyle to the brand button in the Import CSV screen (a template under `lightning/ui/templates/` for imports). The feedback form's own attach control is on the website repo (`Lightning_website`).
- **Ticket 92 (row 93) — row hover is a greyish colour with odd contrast.** Unspecified page. Find the shared hover rule (`style.css`, `:hover` on table rows) and compare against the guideline's row/surface colours (`python tools/guideline.py A03`).
- **Ticket 88 (row 89) — sending a ticket with images takes ~10 s; cache images in a temp file and move them on send, delete if not sent.** Repeat of batch 002 row 76 (ticket 75), now on desktop. That item was recorded as external website work (`current-status.js`, Apps Script receiver); nothing for the app repo to do. Forward to the website repo if it is not already open there.

## Ticket index

| Ticket | Row | Page | Type | Area | Group | Screenshot | Priority hint |
|---|---|---|---|---|---|---|---|
| 78 | 79 | Overview | Improvement | Visual | 2 | — | Medium |
| 79 | 80 | Overview | Improvement | Visual | 2 | [79_1](screenshots/batch-003/79_1.png) | Medium |
| 80 | 81 | Overview | Improvement | Visual | 1 | [80_1](screenshots/batch-003/80_1.png) | **Check first** |
| 81 | 82 | Overview | Bug | Visual | 1 | [81_1](screenshots/batch-003/81_1.png) | High (clear defect) |
| 82 | 83 | Overview | Improvement | Visual | 2 | [82_1](screenshots/batch-003/82_1.png) | Medium |
| 83 | 84 | Overview | Improvement | Visual | 1 | [83_1](screenshots/batch-003/83_1.png) | Medium |
| 84 | 85 | Overview | Improvement | Visual | 3 | — | Medium |
| 85 | 86 | Overview | Improvement | Visual | 2 | — | Owner decision |
| 86 | 87 | Overview | Improvement | Visual | 2 | — | Owner decision |
| 87 | 88 | Overview | Improvement | Visual | 3 | — | Needs detail |
| 88 | 89 | Something else | Improvement | Technical | 6 | — | Website repo |
| 89 | 90 | Overview | Bug | Technical | 3 | — | **Check first** |
| 90 | 91 | Budget | Improvement | Visual | 4 | [90_1](screenshots/batch-003/90_1.png) | Medium |
| 91 | 92 | Import CSV | Bug | Visual | 6 | — | High (clear defect) |
| 92 | 93 | Something else | Bug | Visual | 6 | — | Needs page |
| 93 | 94 | Budget | Improvement | Visual | 4 | — | Needs detail |
| 94 | 95 | Cash planning | Improvement | Visual | 5 | [94_1](screenshots/batch-003/94_1.png) | Medium |
| 95 | 96 | Cash planning | Bug | Visual | 5 | [95_1](screenshots/batch-003/95_1.png) | High (clear defect) |

## Questions for the owner (all answered in Outcome)

1. **Net cash flow:** move it from Spending to Overview (tickets 79, 85, 86)? Batch 002 kept it on Spending as a secondary view.
2. **Period:** should every Overview card follow the selected period (ticket 80), or keep "today" cards and label them?
3. **Investing rate (89):** is "% of free cash in the period" the intended definition? Free cash is a balance, not a period flow.
4. **Ticket 87 and 93:** which parts of Financial health and Spending by group are hard to read? A screenshot would settle it.

## Outcome (2026-10-14, Claude)

Built and tested. Desktop screens were checked in Chromium on the demo profile; the phone screens were not changed.

| Ticket | Outcome |
|---|---|
| 78 | **Built.** In a month, Where money in went sits beside the six months ending with it (`visuals.money_sankey`, `dashboard.PAIR_XS`). Longer periods keep one chart. |
| 79 | **Built.** Month by month is net cash flow by month drawn like the day calendar: a block per year, six months a row, name top left, amount bottom right (`charts.html` › `month_calendar`). |
| 80 | **Built (reproduced).** With a past month chosen, the Net worth card stayed at today while its chart ended at the period end: 431,877 against 397,877. Your position now follows the period end, never after today; Plan to invest shows only for today. Mohab's step changed from "stays today" to "follows the period end". |
| 81 | **Fixed.** Stacked CSS overrides made the figure full width and centred the button under it; the button now ends the figure's line. |
| 82 | **Built.** Kept splits into Invested (blue, the same amount as Saved and invested) and the rest of Kept. |
| 83 | **Built** (also batch 002 row 51). Free cash's right half is What it is made of (weights by kind) instead of the same three numbers as bars; If you sold today sits beside the period's Net flow. |
| 84 | **Built.** Needs you shows one row per kind (bills and payments, activity to sort out, budget and saving, cash and goals, prices); a kind with several opens `/needs-you/{kind}`, a kind with one shows that decision as before. |
| 85 | **Built.** Spending no longer shows net cash flow, by day or in its month table. |
| 86 | **Built.** The daily expenses calendar left the Overview; it lives on Spending. |
| 87 | **Built.** The four cards repeated the rows below and every row carried its own *Show the numbers*: Over time (the savings-rate chart) now comes first, and each limit is one line that opens its numbers and a *See details* link. |
| 88 | **Built in the website** (UX-2026.10.14.04). The deployed receiver is not the one in git and the form posts `no-cors`, so early Drive staging was not safe to build; instead the form is given back at once while the request runs in the background, and a failed send returns the tickets and images. Receiver column mismatch: `OWNER.md` › 19. |
| 89 | **Built.** Investing rate = Money added ÷ Net flow: the share of what you kept that you invested, at most 100% (free cash is a balance, so this is the period's version of it). Saved and invested shows the savings rate only; its blue squares still show what was invested. Glossary updated. |
| 90 | **Fixed.** A lone key note is one line across the page (label, figure, text, action), and a tab bar holding only the gear sits at the end of that line instead of on an empty row. |
| 91 | **Fixed.** File fields are soft wells with a secondary pill as the chooser; the CSV field has its label above it. |
| 92 | **Fixed.** Register and list rows used grey paper on hover; every row now uses the one green-tinted hover. |
| 93 | **Built.** Sub-lists had two chevrons each, an empty "Consider tracking" heading showed with nothing under it, and Select all sat on its own row (also batch 002 row 56): fixed. "System Categories" showed "Personal" under its name; it now names the categories in it that have a plan or spending (Loan payments). |
| 94 | **Fixed.** The next-30-days timeline has one label row per side; payments that would collide join one mark ("Landlord +2", their total, every payment in its tooltip), so overdue bills no longer stack at Today. |
| 95 | **Fixed.** What you owe's Bills due and Loans still to pay open to their items like Free cash's rows; the loan note is a line inside instead of a smaller font beside the name. |

Tests: `tests/test_feedback_batch_003.py`, plus the updated review-inbox, analysis-page, overview-data, Arabic and Mohab tests.
