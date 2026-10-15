# Designs 004: the owner's first-run walk-through (15 tickets)

The owner started a brand-new profile and sent 15 points with five screenshots (welcome samples, a grey field,
the account page header, the CSV column-mapping form, the import review's "Needs a decision" block).
Every ticket below is approved to build. Delete this file with the batch (feedback-review §5).

Read code by grep, never whole files. Guideline: `python tools/guideline.py A10` etc., never open it whole.
Every new visible string gets its Arabic in `lightning/ui/i18n.py` (see `skills/arabic-check`).
Phone (Part C) keeps one column; never reuse a PC layout on the phone.

## Branches: stacked, in this order

Each branch starts from the previous one (the first from `origin/main`), so they merge cleanly in order.
Many touch `lightning/ui/static/style.css`; after any CSS change rebuild the RTL copies with
`node tools/build_rtl_css.js` (check its usage line) and commit them together.

| # | Branch | Tickets |
|---|---|---|
| 1 | `claude/first-run-currencies` | T4, T5 |
| 2 | `claude/account-form-trim` | T3, T6, T8 |
| 3 | `claude/institution-picker` | T7 |
| 4 | `claude/field-well-colour` | T2 |
| 5 | `claude/compact-forms` | T11 |
| 6 | `claude/date-picker-jump` | T9 |
| 7 | `claude/page-header` | T10 |
| 8 | `claude/welcome-sample-boxes` | T1 |
| 9 | `claude/import-review-rows` | T12, T13, T14 |
| 10 | `claude/import-same-day-order` | T15 |

Shared files: `style.css` (4, 5, 6, 7, 8, 9), `accounts/form.html` (2, 3, 5), `dashboard/welcome.html` (1, 8),
`bank_imports.py` and `routes/bank_imports.py` (9, 10), `register.html` (7), guideline files (4, 5, 6, 7).

---

## T1 · Welcome samples: four boxes, not an essay (owner chose the four)

- `lightning/ui/templates/dashboard/welcome.html` `.demo-card`: replace everything with a section header
  ("Or explore a sample", A05 section header, no eyebrow "Just looking?") and **four equal boxes**:
  **Mohab · A full year** (`POST /sample/mohab-2026`), **Amr**, **Menna**, **Fatma** (`POST /sample/<key>`).
  Each box: name · label in bold, one short line (the story's question; Mohab: "Salary, a raise, Ramadan, THNDR and gold, January to today"), a quiet "Load" button. The whole box submits.
- No card in a card (A16): the section is not a card; each box is a card (A07). 4 columns on PC, 2×2 below ~900px, one column on the phone.
- Cut: the three-month household button and paragraph, Abdelrahman (keep his route, data and tests; just not offered here),
  the CSV download links paragraph, the long paragraphs. Keep one muted line: "Samples fill this profile. Use a separate profile to keep them apart from your own money." (the non-secure variant keeps its `--demo` hint, one line).
- `sample_stories()` in `lightning/samples/profiles/stories.py`: let the route pick the three keys; do not delete Abdelrahman.
- Test: welcome page has exactly four `/sample/` forms, no `action="/demo"`, no "Just looking?". Update `tests/test_demo_and_visuals.py`, `tests/test_app_guard.py`, `tests/test_phone_frame.py` where they post `/demo` from the welcome page (the route stays).

## T2 · Field wells: a new colour instead of grey

- Today wells are `#EEF4F2` / focus `#E4EEEA` (hard-coded in `style.css` ~line 2934, the file input, and others; grep `EEF4F2`, `E4EEEA`, `EEF6F3`, `E6F2EC` across `lightning/ui/static/*.css` and `guideline/*.html`). On the mint paper they read grey.
- New well: **`#E8F1FA`**, focus **`#E3EEF9`**, focus edge stays Meadow dark `#0B8A5F`. It is the canvas's own blue end (`--canvas-end #E1EEFB`) lifted, so it belongs to the palette and reads as "type here" on mint paper. Dark mode unchanged.
- Define `--field` and `--field-focus` once in the `:root` block (~line 1020) and use the variables everywhere (style, phone, profiles CSS; the search well A10.7 too). Error well stays rose.
- Verify contrast with a short script: Ink, Ink 2 and Muted (placeholder) on both must stay ≥ 4.5:1 (Claude measured Muted 4.68 on the well, 4.55 on focus; focus is a slightly deeper blue so it still reads as pressed in). Put the measured ratios in the commit message.
- Guideline: change `--field` / `--field-focus` in `guideline/app.html`, `app-ar.html`, `phone.html`, `phone-ar.html` (light themes only). A10.3 words stay ("soft tinted well, never white"). Add a NOW.md *Next* item: website repo needs the same guideline copy (website-sync).
- Test: a CSS test that `#EEF4F2` no longer appears in `lightning/ui/static` and that `--field:#E8F1FA` is defined.

## T3 · "Cash at hand" is just "Cash"

- `lightning/accounts/domain.py` lines ~27 and ~39: `AccountType.CASH_AT_HAND` label → "Cash" (both maps). `CASH` stays "Cash wallet".
- Arabic: add/adjust the translation of "Cash" in the account-type context if needed.
- Grep tests for the label "Cash at hand" (an account *named* "Cash at hand" is fine; only the type label changes).
- Test: the new-account type list shows "Cash" and no "Cash at hand".

## T4 + T5 · Setup starts with your currencies; account currency is a pick list

- **Welcome step 1, "Your currencies"** (`welcome.html` `.welcome-currency` form, route `POST /setup/currency` in `lightning/ui/routes/dashboard.py:249`):
  - Profile currency: type-and-pick (the existing `data-own-picker` select), default EGP.
  - "Other currencies you hold": add several, as removable chips, type-and-pick from the ISO list
    (`CurrencyRegistry.suggestions`, `lightning/database/currencies.py`). Common first: USD, EUR, SAR, AED, GBP, KWD.
  - One "Save currencies" button registers all (`c.currencies.register`) and sets the base (`c.set_profile_currency`).
    Same guard as today: base only changes while there are no accounts/ledger entries; extra currencies can always be added.
  - Until saved, step 2 ("Where do you keep your money?") is shown but its Add links are inactive with one muted line "Save your currencies first."
    After saving, step 1 collapses to one line: "EGP · USD · EUR" and a quiet "Change" (setting `setup_currencies_done`).
- **Account form currency** (`lightning/ui/templates/accounts/form.html` `#currency`, today a free-text `<input list>`):
  a `<select data-own-picker>` of **registered currencies only** (`code — name`), default the base. No free text.
  Help line: "Only your currencies are listed. Add one in Settings › Currencies." (link). Disabled on edit as today.
  The server already rejects unregistered codes (`lightning/accounts/service.py:102`); keep that.
- Tests: posting `/setup/currency` with `currency=EGP&extra=USD&extra=EUR` registers three and sets EGP; the account form has no `<datalist id="account-currencies">` and lists only registered codes; welcome Add links are inactive before setup. Update `tests/test_demo_and_visuals.py:202` area.

## T6 · No Travel in the default categories

- `lightning/database/seed.py` lines 61 and 76: delete `EXP.PERSONAL.TRAVEL` and `EXP.WORK.TRAVEL`. Seeding runs once per new profile; existing profiles keep theirs (no migration that deletes).
- `lightning/samples/generate_mohab_2026.py:33` uses "Personal › Travel" for the Sahel weekend: switch it to "Personal › Entertainment", regenerate the sample CSVs with the generator, and fix any Mohab/sample expectations that named Travel.
- `tests/test_accounts_categories.py` lines ~164, 237, 256 use Travel as a fixture: switch to another seeded category or create one in the test.
- Test: a fresh profile has no category named Travel under Personal or Work.

## T7 · Institutions: a pick list of Egypt's banks, add your own, with logos

- **Data**: `lightning/accounts/institutions.csv` with `code,name,short_name,arabic_name,kind,website,logo`.
  `kind` ∈ bank, broker, wallet, fintech. Banks: every bank registered with the Central Bank of Egypt (try `WebSearch`/`WebFetch` for the CBE's registered-banks list; if the network blocks it, use: National Bank of Egypt, Banque Misr, Banque du Caire, Agricultural Bank of Egypt, Bank of Alexandria, CIB, QNB Egypt, HSBC Egypt, Crédit Agricole Egypt, Emirates NBD Egypt, Bank ABC Egypt, Attijariwafa Bank Egypt, Faisal Islamic Bank, ADIB Egypt, ADCB Egypt, First Abu Dhabi Bank Misr, Mashreq Egypt, NBK Egypt, Al Ahli Bank of Kuwait Egypt, Kuwait Finance House Egypt, Al Baraka Bank Egypt, SAIB, Suez Canal Bank, Egyptian Gulf Bank, Export Development Bank of Egypt, aiBANK, Arab International Bank, Arab African International Bank, Arab Bank Egypt, Housing and Development Bank, Egyptian Arab Land Bank, Industrial Development Bank, MIDBank, Nasser Social Bank, Citibank Egypt, Bank NXT). Plus brokers/wallets Egyptians use: THNDR, EFG Hermes, Azimut Egypt, CI Capital, Vodafone Cash, Orange Cash, Etisalat (e&) Cash, valU, Fawry, Egypt Post.
- **User additions**: table `institutions(id, name, short_name, created_at)` via a new migration (follow the migrations pattern in `lightning/database/`; never edit an old migration). A service in `lightning/accounts/institutions.py`: `list()` merges built-ins (CSV, read once) and custom rows; `add(name)`; `match(text)` finds the built-in for existing free-text values ("CIB", "cib", "Commercial International Bank") by name/short name, case-insensitive.
- `accounts.institution` stays text (no schema change); the picker writes the canonical name.
- **Picker**: the account form's Institution field becomes type-and-pick (A10.3 "Your own data is type-and-pick": results with a 20px logo tile, "Used before" first, then the list, then `+ Add "<typed>"`, which saves a custom institution). Reuse the existing picker JS (the counterparty picker in `app.js` ~line 121/209 is the model); do not write a third picker from scratch.
- **Logos**: bundled, never fetched at runtime (local-first). `tools/fetch_institution_logos.py` downloads each site's `apple-touch-icon`/favicon once into `lightning/ui/static/institutions/<code>.png` (≤ 64px, ≤ 8 KB each, optimise), and writes the file name into the CSV. A missing logo, or a custom institution, shows a **monogram tile**: rounded square, Track `#E6EFEC` background, Ink 2 initials (no brand colours, A03). Show the tile in: picker options, inside the Institution well, the account page header (T10), the Accounts list rows and the sidebar account list (16–20px).
- If logo downloads are blocked, ship monograms only and add a NOW.md *Next* item to run the fetch tool from a PC.
- Tests: `match("cib")` → CIB; adding "My Credit Union" lists it next time; account form renders institution options; a missing logo renders the monogram.

## T8 · Account form: drop "More details", keep Notes

- `accounts/form.html`: delete the `<details>` "More details" and the Last 4 digits field; Notes becomes a plain visible field at the end.
- Editing must not wipe an existing `last4`: in `lightning/ui/routes/accounts.py` (`FIELDS` includes `last4`), keep the stored value when the form omits it. Keep the column; show nothing for it.
- Test: the form has no "More details" and no `last4` input; editing an account with last4 "1234" keeps it.

## T9 · Date picker: jump to a month or a year

- `lightning/ui/static/app.js` `openCalendar` (~line 388). The head's "October 2026" becomes a button. Levels:
  **days** → click title → **months** (12-month grid, year with ‹ ›) → click the year → **years** (12-year grid, ‹ › pages 12).
  Pick a year → months; pick a month → days. Escape goes up one level back to days, then closes. Arrow keys move in each grid.
  Highlight the chosen and the current month/year (chosen in Nile, current ringed, as days do).
- Reuse the month popup's look (`.month-popup-grid`, ~line 1863) so both pickers match. Phone: 44px targets (phone.css ~499).
- Guideline A10.3 gets one sentence: "The date picker's month opens the months, its year opens the years."
- Test: a Playwright check (Chromium at `/opt/pw-browsers`) on any page with a date field: open, click title, click 2025, click Mar, see March 2025 days. If the suite has no browser tests, keep this as a `tests/` test that skips when Playwright is missing.

## T10 · Page headers: one clear design everywhere

Today the topbar's look is set five times in `style.css` (grep `.topbar`: ~lines 100, 747, 1058, 1186, 1640, 1874) and each template builds its own heading (78 templates use `{% block heading %}`). The account page header (screenshot) has a floating "Balance / 0", a meta line beside it, and three equal buttons.

- **One CSS block** for `.topbar`, replacing the older layers (delete the overridden rules): left column = optional 40px tile + title (A05: 28px display, Ink) with the line under it (Ink 2 dates or meta joined by " · ", Muted extras); right = period control, one Secondary, then ⋯. Hairline under, 24px below. Back button sits inline before the tile/title, same height as the title line.
- **One macro** `page_header(title, line='', tile=none, figure=none)` in `partials/macros.html`; migrate the templates whose heading is just a title + line (most of them) to it.
- **Account pages** (`register.html` heading and `top_actions`): tile = institution logo/monogram (T7); title = account name; line = "Bank account · CIB · EGP" (short type label); a **figure strip on the right of the title** before the actions: "Balance" label (13px Muted) above the figure (28px, tabular, whole EGP per A16, Ink), and "What you own" beside it only when it differs (keep the logic just added in commit 9a8511d; build on it, do not undo it).
  Actions: one Secondary "Import statement" then ⋯ holding Convert, Change ownership, Edit account, the rest. Three equal pills → one pill and ⋯.
- Guideline A05 page header: add the account variant (tile, figure strip) in words and in its example markup, PC and phone (C04: tile 32px, figure under the title).
- Run the guideline audit skill's automatic part on the changed pages; check A16.
- Tests: register page heading has exactly one Secondary and one ⋯ in the topbar; `.topbar` is defined in one CSS block (count `^\.topbar \{`).

## T11 · Forms: short fields side by side, everywhere

- Rule (write it into A10.3): "Short fields sit side by side, up to four in a row; a field takes the whole row only for long text (notes). On a phone, one column."
- CSS: `.form-grid { display:grid; grid-template-columns:repeat(auto-fill,minmax(220px,1fr)); gap:12px 16px }`; `.form-grid .wide { grid-column:1/-1 }`. Phone: one column.
- **Map columns page** (`lightning/ui/templates/bank_import_map.html`, screenshot 4): use `.field` labels in one `.form-grid`:
  Date · Amount (or Money in + Money out) · Counterparty · Category · Notes · Reference.
  "How does this statement show amounts?" becomes a two-choice **segment** (A10.2): "One amount column | In and out columns"; no fieldset box. "Reverse the sign" is a small checkbox under the Amount field.
  The intro paragraph becomes one line: "Check the columns we matched. We remember them for this bank." Cut the rest.
- **Account form** (T8 already trimmed): rows Name · Institution · Type · Currency, then Starting balance · As of · Held for, then Notes (wide). The starting-balance box stays a soft section, not a card in a card.
- Sweep: grep templates for forms that stack four or more short fields one per row (`form-card`, `class="row"`, consecutive `<label>`), and apply `.form-grid`. List the forms you changed in the commit message; leave register rows alone.
- Test: the map page has a `.form-grid` and no `<fieldset class="import-amount-model">`; the account form uses `.form-grid`.

## T12 + T13 + T14 · Import review: rows like the register, pick-many to edit together

The block-per-name design (screenshot 5) forces one Counterparty, Save-as, Category, Transfer and Held-for choice on every row with the same imported name, so "money in from Dad" and "transfer to THNDR held for Dad" cannot both be right. Replace it.

**Screen** (`lightning/ui/templates/bank_import_preview.html`, route `lightning/ui/routes/bank_imports.py`):
- One table like the account register (`register.html` `inputs` macro and its CSS): `[select] Date · Counterparty or account · Category · Held for · Notes · Amount · Status`. Every cell is an editable 30px well (A10.3 register rows). Reuse the register's pickers: the counterparty picker that also lists **your accounts** and offers `+ New counterparty "Dad"`, the category picker, and the held-for picker (with Create too).
- Rows are still grouped by imported name: a group header row (checkbox that selects its rows, the name, n rows, total, a status dot, collapse toggle). Groups needing attention are open; ready groups collapsed.
- Filter chips at the top replace the h3 sections: **All · To fix n · Needs you n · Possible duplicates n · Ready n**.
- **Bulk edit bar** (appears when ≥1 row is ticked, sticky under the header): "n selected", Counterparty, Category, Held for, "Use this category for this counterparty next time", **Apply**, **Skip**. Apply writes the values into the ticked rows' wells (client side); nothing posts until "Post ready rows".
- Duplicates: the row's Status cell holds a compact choice "Link to … / Post as new / Skip" (as today's radios, shorter).
- The **Save as** field is gone (T12). The counterparty well decides: pick a saved counterparty → linked; pick **your account** → it is a transfer to/from that account; pick `+ New counterparty` → created on post (once per batch, reuse `_created_in_batch`), with the imported text as its alias; typed but not picked → posted with that text, unlinked (today's "Leave unlinked"). Suggestions (`_suggestions`, `_transfer_target_suggestion`) appear at the top of the picker's list as "Suggested"; a suggested transfer is not chosen until clicked.

**Server** (`lightning/ui/routes/bank_imports.py` `_decision`, `_review_groups`, `_keep_typed`; `lightning/bank_imports.py` `_post_import_row`):
- Decisions are per row only: `date_<id>`, `amount_<id>`, `notes_<id>`, `counterparty_<id>` (text), `counterparty_pick_<id>` (`account:<id>` | `counterparty:<id>` | `new:<name>` | empty), `category_<id>`, `whom_<id>` (text) + `whom_pick_<id>` (`self` | `counterparty:<id>` | `new:<name>`), `skip_<id>`, `match_<id>`, `remember_<id>`. Remove the `group_*` fields and the `group_block` macro. Raise `_review_form_max_fields` to fit ~12 fields per row.
- **Held for works on any row, not only the custody category (T14)**. Mirror the register's rules exactly: grep the register save path for `whom` (`lightning/ui/routes/register.py` and the transaction workflow it calls) and reuse it rather than keeping import-only copies.
  - inflow + held for X → money you hold for X (custody inflow), counterparty is who paid (Dad);
  - transfer + held for X → `money_from_others.sync_transfer` with owner X, whatever the category (today it requires `EXP.SYSTEM.CUSTODY`, `bank_imports.py` ~line 690);
  - outflow + held for X → paid out of X's money.
  So: line 33 `+20,000` → counterparty Dad, held for Dad; line 31 `−20,000` → counterparty THNDR (your account → transfer), held for Dad. Both post.
- `whom_pick_ = new:<name>` creates the counterparty (T13: "I cannot create Dad inside the import"). Same for the counterparty well.
- Status per row is computed server-side as today (errors, needs a decision, duplicate, ready); the page re-renders with errors beside the row.
- Tests (new `tests/test_import_review_rows.py`): (a) the Dad scenario above posts both rows with the right owner and a transfer to THNDR; (b) creating "Dad" from both wells creates one counterparty; (c) two rows with the same imported name can get different counterparties; (d) a held-for on a transfer with no category moves custody. Update `tests/test_mohab_year.py`, `tests/test_own_data_picker.py`, `tests/test_sample_2026.py` from `group_*` fields to per-row fields; Mohab must still pass in full.

## T15 · Same-day order: money in first when the day ends above zero

- `lightning/bank_imports.py` `confirm()` `posting_order` (~line 563) sorts by (date, CSV line). A newest-first statement puts a day's expenses before its salary.
- Rule (the owner's): for each date in the batch, compute the account's balance at the end of that day (ledger balance before that date + earlier batch days + this day's rows being posted). If it is ≥ 0, post that day's **inflows before outflows** (line order within each); if it is < 0, keep the statement's order so the error points at the real row. Apply it per owner for custody rows too (held-for money: same rule on that owner's balance) if the code makes that easy; otherwise account balance only and say so.
- Document the rule in Architecture › CSV import and export contract (one sentence).
- Test: a new account at 0, one day with `−2,000` (line 1), `−500` (line 2), `+10,000` (line 3) posts with no error and the register's running balance never drops below zero that day; a day ending negative keeps line order.

---

## Owner decisions already made

- T1: the four boxes are Mohab 2026, Amr, Menna, Fatma.
- T2: the new well colour above (Claude's pick per the owner's "find another one"); the owner sees it at the milestone check.

## Close-out (build agent)

- One changelog line per branch atop `Unreleased` (`2026-10-15 · Claude:`), ≤ 3 lines each.
- Update Architecture (import rules, institutions, header), Glossary (any new term), guideline A05/A10 as above.
- Mohab and A16 for each visible branch; full suite once at the end (`-n auto --dist loadfile`).
- Anything not built: one report in `report/` each (front matter per `report/README.md`), then `python tools/report_index.py`.
