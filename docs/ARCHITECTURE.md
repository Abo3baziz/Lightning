# Architecture

Last reviewed 2026-10-13 · app 1.0.0b1 · schema 0052

How Lightning is built and calculated: stack, module boundaries, data model and every calculation contract. History lives in [CHANGELOG.md](../CHANGELOG.md), the product story in [Project Overview](PROJECT_OVERVIEW.md), term definitions in the [Glossary](GLOSSARY.md), the visual system in the [Brand guideline](../guideline/), unbuilt designs in [proposals/](proposals/). Where the code or a test states a rule better, this file names it instead of copying it.

Lightning is a local-first, single-user modular monolith: one Python process, one SQLite database, a server-rendered browser UI. Correctness first, then clear ownership of data, then new asset types without duplicated transaction logic.

## Contents

Read only the section your task needs (`grep -n '^## ' docs/ARCHITECTURE.md`, then read from that line).

| Section | Read it when |
|---|---|
| Stack and local operation | You add a dependency or change how Lightning starts |
| Three layers: ledger, plan, report | You are new to the code |
| Runtime and dependency direction | You add an import between modules |
| Modules | You look for where something lives |
| One main ledger; one linked valuation ledger | You touch transactions, postings, holdings or prices |
| Data ownership and derived values | You add a stored or derived value |
| Position and reporting contract | You change any figure on the Overview, Investments or reports, or the figures layer |
| Cash planning contract | You change bills, income, the forecast or Safe to spend |
| Budget and reserve contract | You change the budget, reserves or the emergency fund |
| Persistence, precision, and indexing | You add a migration, an index, a money column or foreign currency |
| UI contract | You add a page, route or template |
| CSV import and export contract | You change import, export or the AI-analysis workbook |
| Search and identity contract | You change names, counterparties or search |
| Desktop app and encrypted profiles | You touch the Windows window, profiles, encryption, devices, packaging or releases |
| Working rules | Always, before you push code (short) |

## Stack and local operation

| Area | Choice |
|---|---|
| Runtime | Python 3.11+, FastAPI, Uvicorn |
| UI | Jinja2 server-rendered HTML, vanilla JS/CSS, no frontend build |
| Persistence | One SQLite file, ordered SQL migrations, local backups |
| Precision | `Decimal` in Python, scaled integers (`_e6`) in SQLite; no binary floats in financial logic |
| Quality | pytest and `import-linter` (`[tool.importlinter]` in `pyproject.toml`, run by `tests/test_architecture.py`) |
| Network | Local server on `127.0.0.1` only |

Legacy mode: `./run.sh` or `python -m lightning` opens `http://127.0.0.1:8765` (plaintext `data/lightning.db`). Startup takes a backup, runs migrations and processes due valuation checkpoints. `python -m lightning --demo` opens the sample household (`lightning/demo.py`) in `data/demo.db` on port 8766, rebuilt on every start. The main product runs as encrypted profiles (see Desktop app).

## Three layers: ledger, plan, report

These describe what data *is*, not which package may import which.

| Layer | Holds | Modules | Moves money? |
|---|---|---|---|
| **Ledger** (real money) | Accounts, posted transactions and ledger lines, prices and valuations, custody (held for others) | `accounts`, `transactions`, `assets`, trades in `investments`, `money_from_others`, `physical_items` | Yes. Only `TransactionService` writes postings. |
| **Plan** (what-if) | Budget rules and carryover, reserves, planned items and payments, sale factors, the cash forecast | `budgeting`, `reserves`, `planning` | No. "Record and mark paid" posts an ordinary transaction through `TransactionService`; the plan then links to it. |
| **Report** | Nothing of its own: figures computed on read | `reporting`, `planning.position` (`PositionService`), `investments.report`, `integrity`, `ui` | No. |

- **Real money is only what the ledger says.** A budget, reserve, scheduled bill or forecast never appears in a ledger figure.
- **A plan figure is labelled as one.** What you owe, reserves, planned amounts, safe to spend, the forecast and every "(estimate)" come from the plan, alone or with the ledger.
- **Each figure has one name, one formula, one function**, in `lightning/core/figures.py` with its layer. The Glossary's figure tables are generated from it (`python -m lightning.core.figures`); `tests/test_figures.py` checks they match and every named function exists.
- **Routes never compute figures.** A screen calls the function the registry names.

## Runtime and dependency direction

```
ui/                   FastAPI routes, Jinja templates, small vanilla JS/CSS; no SQL, no calculations
workflows/            transactional use-cases spanning modules
planning/             recurring items, loans, what you owe, cash forecast (read-only)
domain services/      accounts, assets, categories, transactions, investments, deposits, budgeting
reporting/            read-only queries and derived views
database/             SQLite, migrations, seed, backup, settings, audit
core/                 dates, money, identifiers, posting rules; no app dependencies
```

`bootstrap.py` is the composition root. Cross-module operations call public services, never another module's repository. `import-linter` and tests enforce this. Only `TransactionService` writes postings; other modules build validated postings and ask it.

## Modules

| Package/module | Responsibility |
|---|---|
| `lightning/core` | Money/date parsing, refs, errors, posting rules, `figures.py`, `memo.py` (request cache) |
| `lightning/database` | Connection, migrations, seed, backups, audit, settings, `promotion*.py` (restore promotion) |
| `lightning/accounts` + `workflows/accounts.py` | Account rules; atomic account and opening-balance workflows |
| `lightning/assets` | Asset classes, financial assets, picker catalogue (`egx_instruments.csv`, `us_instruments.csv`, rebuilt by `tools/market/us_catalogue.py`), prices, quote adapters. An investment's currency follows its exchange (`market/iso.py` `VENUE_CURRENCY`); `InvestmentService` refuses a trade whose account is in another currency and posts each line at that day's rate |
| `lightning/market`, `workflows/market_prices.py`, `workflows/live_prices.py`, `tools/market` | Prices from shared packs and live fetches; see below |
| `lightning/fx.py` | The one exchange-rate lookup (see Persistence) |
| `lightning/categories` | Activity taxonomy; archived/pickable rules |
| `lightning/rules` | `engine.py` (pure: conditions, Actual Budget's ranking, splits that add up), `service.py` (save, preview, apply to the past with one undo). Imports and the register ask it first |
| `lightning/counterparties.py` | Canonical names, aliases, match suggestions, defaults |
| `lightning/transactions` | Posting, editing, voiding, search, tags, conversion; the only writer of postings |
| `lightning/investments` + `reevaluations.py` | Trades, positions, investment calculations, valuation checkpoints, `journey.py` (a holding's history) |
| `lightning/deposits` | Certificate terms; read-only interest/payout projections |
| `lightning/money_from_others.py` | Custody attribution for money and units held for others |
| `lightning/bank_imports.py`, `reconciliation.py` | Staged CSV review and posting; checking an account against the bank's balance (a small difference posts one IN/OUT balance adjustment) |
| `lightning/sms_imports.py` | Bank SMS: `parse_sms` (CIB, NBE; samples `tests/fixtures/bank_sms.json`) |
| `lightning/budgeting`, `reserves.py` | Spending plans and cash reserves (separate concepts) |
| `lightning/planning` | Recurring items, loans, payments, forecast; `position.py` computes every position figure once; `health.py` ratios, Financial health, plan check |
| `lightning/reporting`, `integrity.py` | Read-only queries, derived reporting, data checks |
| `lightning/workflows` | Atomic cross-module use-cases, review inbox, AI-analysis workbook |
| `lightning/runtime`, `desktop`, `security`, `sync` | Profiles, sessions, window, encryption, devices (see Desktop app) |
| `lightning/ui` | Routes, templates, static assets. `charts.py`, `visuals.py`, `keynotes.py` only draw and phrase; they never compute a figure |

**Price packs and live prices.** Packs (`lightning/market`): checked pack format, registry, delta download and import. They fill held month-ends and latest closes as source `MARKET` (a typed price always wins) when a profile opens (never a read-only copy) and after a brokerage statement import; what the files lack is listed in Needs you. `python -m tools.market release` writes `lightning/market/market.zip` (a tagged release fails without it); `tools/market` also runs daily in CI (`market-data.yml`) to publish the shared packs. Live (`workflows/live_prices.py`): each app fetches its own prices (source `ONLINE`) when a held investment lacks a passed month-end close (at most once a day) and on Update prices; final closes only. `start_if_due` gathers on its own thread; the next page render (`ui/web.render`) saves the result on the database's owning thread (`apply_finished`). `LIGHTNING_PRICES_OFFLINE=1` turns fetching off (tests). The public `fx` pack uses Banque Misr's dated transfer midpoint and never calls it an official CBE rate. Sources, phases and unbuilt work: [proposal](proposals/market_data.md).

**Bank SMS.** Unknown wording is read by a general rule and flagged *Check this*; money nothing reads stays on From SMS. Nothing posts unreviewed; `SmsImportService` stages rows into the bank import's review. On the phone, `profile_app(sms=…)` supplies the Java `SmsBridge` (`READ_SMS`, never phone-number senders), read only while the ledger is writable there. Duplicates, the re-read window and transfer pairing are in `lightning/sms_imports.py` and its tests.

**Cash at hand** is a form subtype of the cash account type (`accounts.cash_at_hand`). Its balance stays in the Physical Cash child under Liquid Cash.

## One main ledger; one linked valuation ledger

The main ledger is the source of truth. Registers, budgets, net worth, positions and analysis are views over it, never competing stores.

```
transactions (documents) ──1:n──▶ ledger_entries (account + asset effects)
                                           ▲
reevaluation_entries ──many:one── reevaluation period ──1:1 per account──▶ VAL journal in main ledger
```

The reevaluation ledger keeps per-asset, per-account month-end units, price, value, return and missing-price state, and links each row to one system `VAL` journal per account and checkpoint. It never copies ordinary transactions. Sale dates force a checkpoint at the sale price; month-end checkpoints fill on startup. A missing historical price leaves the checkpoint pending for user input; cost is never silently used as a quote. Certificates keep their purchase price as principal until a manual dated valuation replaces it, so they ask for no monthly quote; a CD portfolio's `VAL` journal has one zero-quantity noncash line per asset and owner. Manual `VAL` postings to CD portfolios are prohibited.

| Activity | Main-ledger effect |
|---|---|
| Expense 450 | Account cash −450, `OUTFLOW`, category by activity |
| CIB → THNDR transfer | CIB −10,000, THNDR +10,000, both `INTERNAL` |
| Investment buy | Brokerage cash down; units and cost up; net effect internal |
| Money held for Dad | Cash enters the named account; custody attribution reduces the owned share |
| Month-end return | Per-holding detail in reevaluation ledger; one account-level `VAL` journal |

**Posting invariants.** Internal lines net to zero; external inflows/outflows have a category; a sale cannot take an owner's position below zero; voided entries stay auditable but count nowhere. `ledger_entries.owner_id` null means user-owned, otherwise that Counterparty owns the line; a transaction's owner is copied to its cash and asset lines. Dated cash and holdings are checked per account, asset and owner on posting and editing. A zero-sum `ADJ` posting moves cash between the user and one saved person inside an account (identified by the `Ownership:` description prefix). When another person paid an expense, the `ADJ` has a user-owned categorised outflow and an equal payer-owned inflow: gross cash is unchanged, owned cash falls, and the expense line still matches budget, reserve and planned payments.

**Brokerage buys** must use cash of the same owner in the same brokerage account on the trade date. **CD purchases**: a `DEPOSIT` account is a bank-specific portfolio (Institution field) that cannot hold cash; each certificate is a separate non-cash `DEPOSIT.CD` asset; a `BUY` links it to the portfolio and debits the bank/cash account the user selects. Membership comes from the explicit account link, never from matching institution text.

### Physical gold item contract

- An item is one named thing in one `PHYSICAL_ASSET` account; quantity counts pieces; no ticker or ISIN. `net_gold_grams_per_piece` is the gold-bearing alloy per piece, stones excluded; the karat is its fineness, not a second multiplier.
- `acquisition_cost` is the total paid for the current pieces (workmanship, stones, fees); historical, never moves with prices.
- A shared reference asset gives price per gram per karat in account currency (`GLD:18K`) and must match the item's karat. Estimated metal value = `piece_count × net_gold_grams_per_piece × dated_price_per_gram` (do not multiply by `karat/24`); fine-gold exposure is reported separately as `piece_count × grams × karat/24`.
- Stones and workmanship have no resale value in the estimate. A manual dated total-item valuation overrides the reference estimate from its date. Labels: `Manual`; reference source and price date; `At cost`; or unavailable.
- Metadata, weight and karat edits post nothing and never change history or cost (the audit log keeps before/after). Purchases and sales are normal `BUY`/`SEL` with pieces and grams kept apart from cash; pieces cannot go below zero; a purchase is not income, expense or owned-wealth change.
- Values enter the owning account and the Gold allocation path exactly once; gram-based gold positions are untouched.

## Data ownership and derived values

- **Where:** `accounts` (cash, bank, CD portfolio, brokerage, physical-asset location, other). **What:** `financial_assets`, `asset_classes`. **Why:** `categories` (L1 Personal, Work or Investment; L2 broad; L3 unused). **Who:** `counterparties`, copied from the transaction's `Whom` to its lines.
- Holdings, cash balances, budget actuals, ownership shares, gains and net worth are calculated from posted ledger effects, owner IDs and dated prices.
- Whole-asset estimates for Other asset accounts are kept by effective date (`other_asset_valuations`); they replace that account's cash-like value in as-of reports and post nothing.
- IDs are internal keys; stable refs identify transactions; readable codes identify master records for imports and search. Screens show names. Source CSV spellings are kept during review; counterparty matches are suggestions, never silent merges.
- **Integrity checks** (read-only, `lightning/integrity.py`): gross account values against asset-class reports; `owned net worth + held for others = gross`, overall and per account; categorised outflows against spending and budget actuals; reserves against owned liquid cash; the month-to-date net-worth bridge. Missing valuations make a comparison incomplete, never green. They never adjust entries.

**Default category for a counterparty** (register and CSV import): the counterparty's own category, else its *usual category* (`TransactionService.usual_categories`): the same category in at least 3 of its last 5 categorised transactions, or in every one while it has 2 to 4, counting only the 180 days before its newest (as Actual Budget). With no habit the field stays empty. **A rule comes first** (`RuleService.outcome`, Glossary › Rule): in import review it sets the category, adds its tags to the notes and, for money out kept in the rule's category, splits the expense (`update_expense_split`). The register fills a category as you type only from rules on the name alone; a rule needing amount, notes or account decides on saving (`register.category_when_empty`, also the phone's entry sheet). Applying a rule to the past refiles only single-category, owned money-in/out rows it decides among all rules (never system categories), with old categories kept for one undo (setting `rules_apply_undo`); splits and tags never change the past.

## Position and reporting contract

### Investment report contract

Uses posted, non-void main-ledger entries by transaction date, scoped to `owner_id IS NULL`, with cost lots keyed by owner, account and asset. An opening (`OPN`) holding is a baseline, never new money.

- **Boundary** (owner decisions 2026-10-04): the portfolio includes investment holdings. Brokerage cash is not part of any portfolio figure (it counts in Cash you own). A balance kept in a physical-asset or Other account, or left as cash in a deposit account, is that asset's value, a holding with `price_source` `BALANCE`. **Everything that is not cash sits under one roof**: certificates, stocks, funds, gold and other assets all count in Holdings value, which is Portfolio value. *Deposits* is a part of it, never added beside it. What you own = Cash you own + Holdings value + Other you own; If you sold today = Free cash + Holdings after sale.
- Transfers and trades inside investment accounts net internally; direct physical purchases/sales count only their holding change. Dividends are distributions, not contributions. Checkpoint rows (`return_base_e6`) and `VAL` journals are reconciliation data, excluded from return.
- **Interval:** new money is the positive posted change across the boundary, withdrawals the absolute negative change; money added is their difference. Gain from sales = net sale proceeds less average cost removed (basis per owner/account/asset; fees already included). Distributions use cash actually posted. Price change on what you hold = end balance less the balance just before the interval. Net gain or loss adds gain from sales, price change, distributions and any separately identified FX/cost effects once. No balancing "other return". Missing prices or ownership make the result unavailable.
- **As of a date:** cost of holdings = remaining basis; holdings value = units × a dated confirmed valuation; unrealized gain = value less basis. An asset with no typed or trade price yet is valued at remaining cost and listed in the report's `at_cost` notices; a missing price after that makes Net gain unavailable. Dividend attribution is stored in `investment_dividend_assets`. YTD is labelled Calendar 2026 (no fiscal-year setting).
- **Investment return:** holdings value less remaining cost, plus gains from sales and dividends. Certificate interest lands on a bank/cash account as Investment › Interest; when its payer is a CD portfolio's Institution (any case) it is that portfolio's certificates' interest, split by cost held that day (`ReportingService.certificate_interest`), in Dividends and interest, Net gain and XIRR (owner decision 2026-10-06). Portfolio and management XIRR must not be assumed owned-only until historical custody cash flows are verified.
- **Price and FX apart** (`investments/report.py::foreign_gain_split`): for a holding priced in another currency, `price_part = (value − cost) in its currency × today's rate`, `fx_part = cost in its currency × today's rate − cost in the profile currency`; they add to its unrealized gain.

### Shared figures and rules

- **Position figures** (What you own, Cash you own, Deposits, Holdings value, Reserves, Bills due, What you owe, Net worth, Free cash, Portfolio value, Holdings after sale, If you sold today) come from `PositionService.at(date)` in `lightning/planning/position.py`. Base values are read from reporting, reserves and planning; every other figure is a property composing them (`free_cash = cash_you_own − reserves − bills_due`). Routes and templates read the `Position`; they never re-add balances. Historical after-sale estimates use current sale factors; an unavailable reserve history makes Free cash and If you sold today unavailable.
- **Sale factors:** each asset class has a 0–100% factor (95% unset, `investments.domain.DEFAULT_SALE_FACTOR`). Holdings after sale = Σ holdings value × factor, deposits included (CDs follow their early-withdrawal terms). A scenario with current settings, not a quote or booked loss.
- **Average monthly income:** `BudgetService.income_average(month)` is the only income average: chosen income categories over the last 3 or 6 completed months that had income, or a manual amount. A recurring-income transaction explicitly linked to a scheduled payment counts in that payment's due month for this average (cash-flow reports keep the bank date). Budget percentages, emergency-fund coverage and the forecast all read it.
- **Average monthly spending:** `BudgetService.spending_average(month)`: household money out (investments and one-off categories left out) over the same window. `BudgetService.emergency_fund(month, set_aside)` counts the fund in months of income or of spending (setting `emergency_fund_basis`, `income` by default) against a six-month target.
- **One rule for Money in and Money out** (2026-10-04): `reporting.service.flow_of(effect, amount, category)`. A line with the income effect in a category with an income class is Money in; every other categorised line is spending, where a payment adds and a refund (a positive amount, whatever effect it was recorded with) takes away. Every adding path uses it on the same rows (cash flow, month trends, calendars, category and spending breakdowns, Budget, which also leaves investment categories out); `tests/test_one_money_rule.py` checks they agree. "Money in" on an expense category records a refund (`record_inflow` → `record_refund`).
- **Period flows:** posted external activity in the range. Internal transfers and investment purchases are not income or expense; custody is excluded from owned analysis.
- **XIRR** is an annualised money-weighted rate over dated investment cash flows and an ending value. Since-inception XIRR is a separate measure from a period's currency return; a period XIRR needs an opening valuation as an initial flow. If dates, flows or value are inadequate, show an unavailable reason, never 0%. Missing prices never become invented quotes. Wealth movement stays distinct from investment return.
- **Overview and reports** share one date-range parser (`ui/periods.py`; Birdview was folded into the Overview on 2026-09-30, `/birdview` redirects, Expense analysis keeps `/birdview/expenses`). Flows use the selected interval; the Overview's position cards stay valued as of today. Expense analysis uses daily calendars up to 92 days, monthly summaries beyond. Asset-class weights divide by owned investment value, excluding cash and custody. The four horizons apply alike to flow, expense and position views (position as of range end).

### Figures layer and speed

**Figures layer** (2026-10-04). Every number on a screen is a registry figure computed by the function the registry names; `lightning/ui/visuals.py` and templates only draw. Expense analysis reads `reporting/spending.py`; a holding's page reads `investments/journey.py`; Cash planning reads the forecast's `payments_before_income` and `ForecastMonth.money_in/money_out/net`. To add a figure: a registry row in `lightning/core/figures.py` (name, meaning, formula, function), the function in a service, `python -m lightning.core.figures` to regenerate the Glossary, then draw it. `tests/test_figures_layer.py` guards it.

**No stored calculations table** (decided 2026-10-04). One central place computes every figure: the registry plus the services it names. A table of stored daily figures was not built: a back-dated edit or import rewrites every later day, plan figures depend on today and settings, and a missed refresh would show wrong numbers silently. Revisit when a real profile passes about 4,000 transactions or any tab passes 400 ms (Budget › All time was 236 ms on 2,239 transactions, 2026-10-04). Design if needed: [proposals/stored_figures.md](proposals/stored_figures.md).

**Request cache** (`lightning/core/memo.py`). `ui/web.py` wraps every request in `request_cache(container.db)`; a read decorated `@request_cached` computes each distinct call once per request, and nothing is cached outside a request. It is safe because: it lives for one request only; any write empties it (`total_changes` changes); it never serves or stores inside a transaction (`conn.in_transaction`); callers get copies (`deep=True` for the investment report); and only pure reads with hashable arguments are decorated (see the decorated functions). `tests/test_reporting_performance.py` caps SELECTs per main tab on Mohab's year plus two earlier years, checks every tab renders byte-identical HTML with and without the cache, and checks each register page against the full register.

**Page speed.** Measured 2026-10-03 on 2,239 transactions (4-vCPU container): the Overview fell from 507 to 163 ms and Budget › All time from 4.6 s to 0.33 s (encrypted: 7.0 s to 0.25 s). Three causes, three fixes: figures recalculated many times per page (the request cache); SQLCipher wiping every freed allocation (`cipher_memory_security` off, owner decision 2026-10-03; see Encryption); registers summing every row to show 50 (`ReportingService.register_page` counts in SQL, reads one page with `LIMIT`/`OFFSET`, and starts a single account's running balance from `statement_movement`; search or category filters show no running balance). Fonts are bundled in `lightning/ui/static/fonts/`; the profile `Guard` lets the window cache `/static/` (`private, max-age=86400`) while pages stay `no-store`. Still open: routes are `async def` with synchronous database work; the live database uses the rollback journal (`DELETE`, synchronous `FULL`).

## Cash planning contract

`lightning/planning/` owns planned items (`planned_items`) and payments (`planned_payments`). It reads the ledger, budget and reserves through services and never posts; recording a payment goes through `TransactionService`.

- **Items.** A bill, subscription, income or loan with an amount per payment and a schedule: frequency (once, weekly, monthly, every 3 months, yearly) every N periods from a first date, optionally ending at a last date or after N payments (loans need one). Monthly dates keep the first date's day, clamped to month end. **On a weekend** (`weekend_move`: keep, day before, day after, migration 0047) moves a Friday or Saturday date to Thursday or Sunday (`planning/schedule.py::on_working_day`); the default is keep, and a one-off payment always keeps its date. Last date and payment count apply to the calendar date; a reporting window applies to the moved date. A payment settled under its calendar date stays settled after the setting changes.
- **Status.** Paid (linked to a posted transaction), Skipped, Due (on or before today, unsettled) or Upcoming. Voiding the linked transaction makes it Due again. A transaction settles at most one payment. Historical dates use today's status; schedules are not versioned.
- **Matching.** A posted, owned money-out (money-in for income) settles a payment automatically when it is the only candidate within 7 days, on the item's account if set, matching counterparty or category, within 10% of the amount (1% for loans). A plausible non-strict match (up to 45 days, 50% off) is offered for confirmation, also before the due date, and never settles itself. A confirmed link stores the transaction's actual amount. A changed amount prompts but never updates later payments or a related reserve target on its own.
- **What you owe** = bills due + loans still to pay, each payment once. **Bills due** = Due bills, subscriptions and loan payments. **Net worth** = what you own − what you owe. **Free cash** = owned liquid cash − effective reserves − bills due; the Integrity check verifies free cash + reserves + bills due = owned liquid cash.
- **Loan budget lines are derived, not stored:** `BudgetService.amounts_for` asks `PlanningService.loan_payments_by_category(month)` (wired in `bootstrap.py`, so budgeting never imports planning) and plans a category with no rule of its own at that month's loan payments (not skipped). A user rule wins; `has_plan` ignores these lines. **Loan payments are spending:** recording one is an ordinary money-out in its category (default `EXP.SYSTEM.LOANS`; migration 0052 groups the ledger exceptions), so it counts in budget actuals and cash flow, leaves loans still to pay and leaves net worth unchanged. The loan is never a ledger account.
- **Debt and fixed-cost ratios** (`planning/health.py`, `HealthService.at(day)`): Debt to net worth, Debt to cash, Loan payments to income, Fixed costs to income. A zero or negative divisor gives None, never a number.
- **Financial health** (`HealthService.overview(as_of)`): those ratios, the Savings rate for the last completed month, Emergency fund (same target and Settings › Budget basis), month-end Net worth for six completed months (missing = None). It calls `PositionService.at(..., match_payments=False)` so a read cannot settle a payment. Limits are `SettingsStore` values per profile; minimum/maximum are inclusive; unavailable figures or unset limits have no status. Limits never edit the emergency target or financial data.
- **Cash forecast** (an estimate; changes nothing): from free cash today, per month adds scheduled income (or the three-completed-month average when none is scheduled, labelled) and separately labelled projected CD proceeds, and subtracts upcoming bill and loan payments, the budget still planned (current month: plan less spent; bills in a planned category count inside it) and what dated reserve goals still need ((target − assigned) ÷ months left). CD principal at maturity is a transfer into liquid cash, never income. **Safe to spend** = free cash − payments before the next income − budget still planned this month − Saving needed (see plan check), shown with its parts; it never spends projected CD cash before receipt.

### Certificates and time deposits

`lightning/deposits/` models a `DEPOSIT` account as a portfolio of `DEPOSIT.CD` assets, each with principal, annual rate, start date, earliest withdrawal date, maturity (direct, or from a term in quarter-year steps), simple/compound method, payout schedule and, for compound, capitalisation frequency. The funding account must hold enough user-owned cash on the purchase date, and the service replays later cash activity so the locked-up purchase cannot make a later balance negative (earlier negative history is fine).

Interest and maturity are forecast estimates only: actual interest is entered from the bank statement, redemption records principal the user enters, and a recorded interest entry does not change the forecast schedule. Projections use actual elapsed days ÷ 365 in `Decimal` and change no balance, Net worth or Free cash. The earliest withdrawal date is eligibility, not a cash event: before it the CD is not redeemable; from it until maturity the *if sold today* estimate applies the `DEPOSIT.CD` sale factor as an early-redemption haircut; at maturity, full principal and estimated interest. A redeemed certificate is no longer projected. Migration `0039_cd_portfolios.sql` keeps account-level `cd_terms` as legacy data and rewrites no history; old `DEPOSIT` cash must be moved out by the user.

## Budget and reserve contract

Budget limits are monthly spending constraints. Reserves assign already-owned cash to emergency or project plans; an assignment is neither a ledger transaction nor a budget limit, and reduces free cash. Budget room and free cash stay separate. Brokerage cash can be reserved, with its transfer requirement disclosed.

- **Actuals** come from posted owned ledger expenses; expense-category refunds reduce their original category. Custody, transfers, investment purchases and revaluations are excluded.
- **Base rules:** fixed EGP, a percentage of budgeting income, or a 3/6-completed-month spending average (divided by distinct months with qualifying activity; none = unavailable, never zero, never beyond the window). The income basis is the selected owned income categories or a manual monthly amount.
- **A parent limit is a ceiling** for its branch; child amounts are allocations, never added to the cap.
- **Over a longer period** Planned and Spent cover the same months (spending counts from the first month with a plan). YTD, All time and Custom aggregate monthly base plans and actuals and include range-opening carryover once; partial-month comparisons are prorated estimates.
- **Carryover** is opt-in, default off, effective from a selected month. It is derived spending room, never cash or a liability:

```text
current_budget(M)       = base_monthly_budget(M) + incoming_carryover(M)
left(M)                 = current_budget(M) - owned_spending(M)
incoming_carryover(M+1) = left(M) when enabled; 0 when disabled or reset at M+1
```

  Positive room and overspending both carry, unclamped. A dated reset clears the incoming amount from that month and leaves history and later settings intact.
- Budget's ordinary view is a compact plan summary and a Personal/Work/Investment rollup; rule editing and background estimates open on demand.

**The plan check: one savings target for every screen** (owner request 2026-10-05). `HealthService.plan_check(month)` returns a `PlanCheck` from Average monthly income, the month's Planned (`BudgetService.plan_summary`), the Savings rate limit, Saving for goals (`CashForecaster.goal_needs` via `budgets.reserve_goal_needs`) and the Emergency fund top-up (`EmergencyFund.top_up`: the gap to six months over `EMERGENCY_TOP_UP_MONTHS`, 24). Saving needed = the larger of the Savings target and goals plus top-up; Most you can plan = income less that; `over_by` = how much to take out of the plan. Budget key notes, the line under Planned, Needs you and Financial health's Planned savings rate all read it; a longer period compares its base plan with the target alone. It replaced the separate spending-ceiling setting (migration 0042). Details:

- Reserves shows each dated goal's share of Saving for goals. *Fill this month* keeps a row ticked only while it fits Most you can plan (`HealthService.fit_fill`).
- Saving a bill, subscription or loan reports Fixed costs to income and, for a loan, Loan payments to income (`HealthService.commitments_note`). Bills and subscriptions plan their category automatically, as loans do, until it has its own rule (`BudgetService.scheduled_payments`, `bill_lines`); the forecast counts a bill in a planned category inside that plan.
- The forecast holds back the same emergency top-up each month until the fund is full (`ForecastMonth.emergency_saving`, `planning.forecast.emergency_fund`). Before any completed month has income, Average monthly income is the income set up in Recurring (`PlanningService.income_a_month`, `IncomeAverage.scheduled`).
- Saving a target, goal, allocation or emergency fund says what it does to this month's Most you can plan (`HealthService.plan_note`). Needs you names a category whose own rule plans less than the bills and loan payments scheduled in it (`BudgetService.below_scheduled`).

**The smarter plan** (owner decision 2026-10-05). Safe to spend and the forecast hold back Saving needed each month: goals, the emergency top-up and the Rest of savings target (`ForecastMonth.target_saving`, never below zero). `HealthService.goal_reach` gives what the plan leaves for dated goals, earliest first, naming the month a short goal is ready. `raise_offer` notices Recurring income at least 5% above the average (*Plan with it* sets `budget_income_from_recurring`; *Save the difference* raises the Savings rate limit; *Keep the average* sets `income_raise_declined`). `short_month` puts a last completed month that saved less than the limit in Needs you, unless under half the usual income came in. `BudgetService.over_twice` finds a category over its own plan in both of the last two completed months (by at least `OVER_PLAN_MARGIN` = 50) and pairs it with the category with most room left; *Move it* (`move_room`) moves that plan from this month on, total unchanged. All of it reads the plan; only the user's choice changes a setting or a plan.

**Fill a month** (preview is read-only; it never uses actual spending or carryover as a proposal). *Last month* = the previous month's effective user-set base rules resolved to EGP there; applying creates a fixed one-month override. *Schedule* = active Bills and Subscriptions dated in the month, grouped by category (skipped payments and Loans excluded). *Goal* rows are information only (changed in Reserves). Loan-derived lines are excluded, and a category also planned for loans is called out. A limit equal to Last month's is marked "Already using last month's plan" and not preselected; other limits are conflicts; no row applies unselected; a batch whose child allocations exceed a parent ceiling is flagged. Applying uses the month-only budget save in one outer transaction.

## Persistence, precision, and indexing

- SQLite with ordered, append-only migrations; never edit an applied migration. Dates are ISO `yyyy-mm-dd`; entry accepts ISO, `dd/mm/yyyy`, `dd/m` (current year); CSV uses the same parser. An account's legacy opening date is not a transaction-date boundary; balances are chronological sums of dated lines.
- Money, prices and quantities are `Decimal` / integer `_e6`; new money inputs take two decimals. Summaries round to whole units; entry controls keep cents.
- Indexed paths: ledger account/date, asset/date, category/date, transaction id, transaction date/type/status, price history asset/date.
- Corrections are audited. Transactions are voided or deleted through recoverable flows; used categories are archived, never removed.
- **Start fresh** (Settings › Your data, `POST /settings/fresh`) never deletes data: in profile mode it locks the profile and opens new-profile setup; in browser mode it backs up, renames the database to `<name>_before-fresh_<timestamp>.db` and builds an empty one (a failed rename reopens the original).
- Data and backups live under Documents/Lightning (profiles) or `data/` (legacy), never in Git.

**Currencies and exchange rates.**

- One base currency per profile (`settings.base_currency`), from the profile's registered currencies (migration 0049: ISO 4217 suggestions plus a named custom three-letter code). It can change only before ledger or FX history exists. Each account has one currency; a registered currency has one cash asset.
- `ledger_entries.amount_e6` keeps the native amount, `amount_base_e6` the dated base amount, `fx_rate_e6` the rate used; stored values are never rewritten when rates change. A foreign cash posting needs a saved rate on or before its date. `fx_rates.base` is the foreign currency, `quote` the profile currency, in profile units per foreign unit. Transfers refuse two currencies and point to *Convert*.
- **One lookup** (`lightning/fx.py::rate_for`, used by posting, valuation, reevaluation): the newest rate on or before the day, direct, else inverse (1 ÷ rate), else a cross through EGP; derived rates are rounded to 6 places and never stored. On one day MANUAL > TRADE > MARKET > ONLINE; a newer day beats an older source. Older than 10 days (`STALE_DAYS`) still values a balance with *as of <date>* (`Valuation.fx_as_of`); older than 45 (`MISSING_DAYS`) is no rate (Needs you links to type one). The `fx` price file fills MARKET rates; `workflows/live_prices.py` fetches Yahoo `<CCY>EGP=X` as ONLINE.
- **Reevaluation of foreign cash:** month-end checkpoints value native units at the dated rate and post only the rate change as a zero-quantity `VAL` journal; a missing rate stays pending.
- **Conversion** (`DocType.CNV`, `transactions/conversion.py`, `/accounts/{id}/convert`): sent, received and an optional fee in the sending currency. The sending line leaves at the day's rate; the receiving line arrives at the **executed rate**, so internal lines net to zero in the profile currency; the fee is an OUTFLOW in Fees & Charges. Rates have 6 places, so amounts over 10,000 units may need their base value spread over two lines (`exact_lines`). The executed rate is saved as a TRADE rate, rebuilt whenever a conversion is created, edited, voided or restored. `/accounts/convert/quote` shows the executed rate and its distance from the day's market rate (a missing market rate never blocks). Spread paid = market value sent − market value received.
- **Foreign currency positions** (`reporting/fx_positions.py`, Currencies tab): average cost per currency over owned cash lines. Money in adds units at the line's profile value (conversion: executed rate; salary, opening balance: the day's rate); money out removes units at average cost, the gap to what it fetched is the realized FX gain; same-currency transfers and revaluation journals move no cost; custody is left out; a balance below zero is no position. Costs are whole cents, so unrealized + realized = held units at today's rate − the net profile value of the currency's lines (a test checks it). Figures per currency (four, then Other): Average rate, Unrealized FX gain, Realized FX gain, Spread paid.

## UI contract

- **Language and direction.** Profile setting `locale` is `en` or Egyptian Arabic `ar` (`lang="ar-EG"`, `dir="rtl"`). `ui/i18n.py` owns interface names, `ui/i18n_system.py` the entries for system words (built-in categories, asset classes, currencies, months, generated sentences, errors), which stay English in code and data. Templates use `|tr(locale)`; every Arabic page also passes `localize_html`. A typed name has no entry and stays as typed. Before unlock the chooser uses a `lightning_ui_locale` cookie (Settings sets it too). Arabic shows Arabic-Indic digits and separators in visible text only; form values, calculations, codes, URLs and identifiers are unchanged, and amounts, dates and codes keep left-to-right isolation. Arabic pages link `style.rtl.css`, `phone.rtl.css`, `profiles.rtl.css`, generated by `tools/build_rtl_css.js` (`tests/test_arabic_no_english.py` fails when one is older than its source); Arabic-only fixes go in the English file under `html[dir="rtl"]`. Terminology: [Glossary](GLOSSARY.md#العربية--المسرد-العربي).
- **Names explain themselves.** Screens show a figure's registry label; no explanation toggles. A name needing explanation is renamed in `figures.py` (the old name becomes a retired alias).
- **Thin routes.** A route parses forms, calls services, renders results or errors. No SQL or financial calculation in routes, templates or JavaScript. Charts and key notes position and phrase what a service computed; a key note may compare two figures, never derive one. A presentation change never adds a financial model.
- **Two levels** (owner, 2026-10-06). `ui/sections.py` is the one list of sections and tabs: at most six sections, five tabs each (`tests/test_two_levels.py`). `base.html` draws the sidebar and, under each title, the tab bar (`partials/section_tabs.html`) with the tab's gear opening its settings in the dialog. A page joins a tab by path, and a Settings page by `?section=`, so addresses never change. No third level: a record opens in a dialog over its tab or, when too rich, as a page inside its tab with Back (a holding). A new feature joins or replaces a tab. Each setting lives behind the gear of the tab it changes; Settings keeps only whole-profile settings plus *Settings in each tab* (links drawn from `sections.py`); no second settings button in a header; a default comes before a setting. Row actions are icons with tooltip and accessible label; words only for a form's main action. One choice, one field. No line repeats what a label says. Currencies, rates and reevaluation history are at Settings › Currencies; FX also appears as the Currencies tab under Overview.
- **The phone** (guideline Part C). The Android app passes `profile_app(phone=True)`; the gate puts `phone` in request state, `base.html` hands over to `phone/base.html` (app bar, five-section tab bar, safe areas), and `web._render` uses `templates/phone/<page>` when it exists (Overview, a register, Accounts, entry sheet, Budget, Cash planning, Investments, Devices; a holding's horizon stays on the PC table). Macros ask `phone_mode()`; `static/phone.css` loads only there. Tables become rows, KPI tiles go two by two, so nothing scrolls sideways at 360 or 320 px (`tools/phone_check.py`, Playwright). The phone's way differs from the PC's only where `tests/test_mohab_phone.py` `DETOURS` says; `tests/test_phone_frame.py` checks the frame without a browser. The PC never sees any of it. Layout rules are in guideline Part C.
- **Financial health** is the Overview's Health tab (`/financial-health`): read-only, optional past `as_of`; four KPI cards (emergency fund, savings rate, debt to net worth, fixed costs to income) on meters against their limits (cushion, saving, debt) and six completed months of savings rate and net worth.
- **Every visible action leads to a working workflow.** A drilldown applies its scope (category, dates) or says it is general activity; context survives, and a filtered register says so with Clear.
- **One review inbox.** `workflows.review.ReviewInbox.items(on)` is the single list of decisions waiting on the user (the Overview's Needs you): missing valuations, statements left in import review, posted activity still Unaccounted, overdue reserves, bills and loan payments due, a forecast that runs short, out-of-date prices, budget sections over plan. Recurring suggestions are not in it until the owner settles which Lightning should offer. It changes nothing.
- **Opening balances are not growth on charts:** the net-worth chart notes months with opening balances (`ReportingService.opening_balances_by_month`); the Investments sparkline leaves out holdings recorded as already owned (`holdings_opened_between`) and says how much.
- **Whole EGP on report pages.** Templates in `web.REPORTING_TEMPLATES` show money whole; fields and registers keep two decimals. A left/over beside two rounded figures is the difference of those figures (`charts._gap`), and a percentage that rounds to zero reads 0% unsigned (`signed_pct`).
- **The period control** keeps custom dates and filters across submissions and drilldowns. Position figures use the period end; flows the whole interval.
- **Sums in amount fields** are read by `core.money.to_decimal` (Glossary › Amount input). `GET /amount-sum` returns the result or refusal; `app.js` fills the field on leaving it or Enter. The browser never does the arithmetic; the server re-reads the sum on save.
- **Tags** live in the notes text: `transactions/tags.py` reads them, `TransactionService.tag_transaction_ids(tag)` finds posted transactions by exact tag, `ReportingService.money_in_out(ids)` totals them. The register takes `?tag=` or a search of `#tag`.
- **Privacy mode** blurs money, never percentages, dates or names. `app.js` wraps amounts in text and blurs chart labels and money fields; the server renders `class="privacy"`. The choice is the `lightning_privacy` cookie for the sitting, else profile setting `privacy_mode` (`POST /settings/privacy`; a reader session cannot save).
- **Static files carry a version** in `base.html` (`style.css?v=`, `app.js?v=`): raise it when the file changes.
- **Working, not stuck** (guideline A10.6). `app.js` disables a pressed submit and shows the turning square (`data-busy` replaces the label); links over 500 ms and background price fetches (`GET /investments/prices/online/status`) show `#busy-toast`. Downloads are left alone; a page that never comes frees the button after 20 s.
- **Failures stay visible.** Invalid edits keep typed values and show the error, also inside a disclosure. A missing valuation is never zero. Expandable rows add up to their parent or say why not.
- **Distinct concepts stay distinct:** What you own, balances including custody, Free cash, Left in plan, If you sold today. Investment transfers are not expenses; holdings are never brokerage cash.
- **A way back without browser chrome.** The desktop window has no Back button, so a full page shows one when opened with `return_to`. Pages reached from many places fall back to the same-origin `Referer`; main tabs never do (`ui/web.py::_back_url`).
- **CSS:** the last block of `style.css` ("Guideline 3.6") holds the rules that override older layers (tone by meaning, soft wells, no all caps); change rules there rather than adding a layer.

## CSV import and export contract

Import normalises one signed amount column or separate inflow/outflow columns into one signed amount (money out negative) before review. Rows stay unposted until reviewed. Review groups rows by imported name and asks once per name (`group_<field>_<n>`, each row sends `group_of_<row>`); the route turns that into one decision per row, so `BankImportService.confirm` is unchanged. A row keeps its own date, amount, note and skip, and its own category only when the statement gave a different one. A statement left in review can be discarded (`BankImportService.discard`; nothing posted is touched) and Import CSV shows a waiting review first (`BankImportService.waiting`). The AI preparation helper builds CSV instructions locally and contacts no provider.

**Matching rows you already recorded.** `BankImportService` lists *link candidates* per row: posted transactions on the same account with exactly the same signed amount within `LINK_WINDOW_DAYS` (3), not already backed by an imported row; closest first. A flagged row offers **Link to …**, **Post as new** or **Skip** (`match_<row>` = `link:<id>` / `new` / `skip`); within one statement defaults never send two rows to one entry, and a row with a free candidate defaults to *Link*, other flagged rows to *Skip*. Linking sets the row `LINKED` with that `transaction_id`; no money moves and the transaction keeps its fields. A partial unique index (`ux_bank_import_transaction`, migration 0040) allows one `POSTED` or `LINKED` row per transaction per account, so equal purchases stay distinct, a re-imported statement links once, and a transfer can be backed by each bank's statement. A row whose earlier import was voided is flagged and never ready, so a void is not quietly undone.

**Selected CSV exports** (register, Categories, reevaluation ledger) take explicit IDs, at most 1,000, never a whole account or database. A transaction export has one row per ledger line (with transaction and line IDs, account, asset, category, quantity, amount, base amount, owner ID); categories include hierarchy, direction, active state and budget flags; reevaluation exports include per-asset values and the linked journal reference. These are inspection files, not the import format. Text starting like a formula is prefixed with an apostrophe.

**Export for AI** (Settings › Your data): one workbook for All time, YTD, Monthly or Custom (`ui.periods.parse_period`). `AIAnalysisService` (`workflows/ai_analysis.py`) builds one `.xlsx` in memory with Summary, Transactions, Investment ledger and Categories sheets. Transactions include every posted owned line in the period without the export cap; a line owned by another person is omitted, while a categorised expense paid externally for the user stays. Opening checkpoints are labelled as context. Strings are OOXML inline text, so user content cannot become a formula. The editable prompt is copied when possible; nothing is sent to an AI provider and no plaintext temp file is written.

## Search and identity contract

Search is read-only retrieval; choosing a result is the user's action. Rules:

- One application-layer matcher with per-surface scopes; a result carries entity ID, type, display name, subtitle, rank and match reason. Use canonical Counterparty identities and confirmed aliases (limit ten per Counterparty); never store a fuzzy score as an alias or silently merge records.
- Order: exact ID/code/ref or name; normalised name; confirmed alias; prefix/word/substring; typo suggestion. Normalise Unicode, case, whitespace, punctuation and limited script marks for retrieval; keep canonical text for display and identity; cross-script transliteration is not proven identity. No fuzzy matching on amounts, dates or short account codes.
- Searching by a matched alias uses the canonical ID to find linked transactions; exact literal filters may keep SQL `LIKE`. Group results by type so an own account is never mistaken for a Counterparty. Transfer destination and custody owner are always explicitly selected; a match never changes posting type or ownership. CSV suggestions stay unposted until confirmed.
- Logic stays in Python services; the UI renders candidates and submits IDs. Use bounded candidate lists; if latency needs it, evaluate SQLite FTS5 under the same contract.

**Built (2026-10-05):** `ui/routes/search.py::matches()` is the one matcher for the Search page and the Ctrl-K bar (`/search?format=json`): exact name, starts with, a word starts with, contains, then a `difflib` near spelling; it returns pages, actions, a transaction by ref, accounts, counterparties, categories, investments and tags, grouped in that order, ending with "Find transactions with …". Not built (scoped pickers, alias-aware history, RapidFuzz ranking, latency checks): [proposals/search_matching.md](proposals/search_matching.md).

## Desktop app and encrypted profiles

**State:** v1.0.0-beta.1 (`lightning/__init__.py`), unsigned. Use dummy data until ordinary-PC acceptance, legacy import and backup restore are done (see Open before a beta).

**Shape.** FastAPI, Jinja and every financial service are shared; no second implementation. Windows: `Lightning.exe`, a thin pywebview 6.2.1 + WebView2 shell (`lightning/desktop/`) in a PyInstaller one-folder ZIP; it needs the WebView2 Runtime, not Python. Linux: `python -m lightning --profiles` runs the same runtime in a browser. `lightning.runtime` (paths, instance lock, session, HTTP guards, launcher) sits between `lightning.desktop | lightning.main` and `lightning.ui`; `lightning.security` beside `lightning.database`. Browser mode never imports pywebview, pythonnet, WinForms or winreg; Windows-only dependencies have their own lock files in `requirements/`.

**Profiles and data.** Container `Documents/Lightning/` (Windows known-folder API; Linux `XDG_DOCUMENTS_DIR`, else `~/Documents`).

- **Layout** (`runtime/paths.py`): one folder per profile, `Name_YYYY-MM-DD_NNN_<id>/`, holding `<same>.db`, `keys.json`, `instance.lock`, `backups/`. A chosen database keeps its companions in `.<name>.db.lightning/`. Backups append `_backup_<date>_<seq>_<id>`; pre-upgrade copies `_upgrade_`.
- **Discovery** scans only the container or a chosen folder, lists profiles and backups apart, never opens the newest-looking file. Alternate locations are typed paths (no native picker yet). A plaintext legacy database, a backup chosen as live, or a hardlinked path is refused.
- **Sync folders:** a local lock cannot coordinate two PCs. Never open one live database on two computers; move completed encrypted backups.

**Encryption** (`lightning/security/keys.py`, `runtime/session.py`).

- **Engine:** SQLCipher via `sqlcipher3` 0.6.2, keyed with a raw 32-byte data key made once per profile and never typed. Database and backups use only this key; `key_id` (an HMAC of it) is not secret.
- **Three secrets** (owner decision 2026-10-05): a password of any length (setup suggests four BIP-39 words and advises without blocking); a 12-digit recovery key (`1234-5678-9012`, any digit script, shown once, confirmed with a press, not retyped: owner 2026-10-06); a security question whose answer ignores case, spaces, punctuation, Arabic letter variants and marks, and digit script.
- **`keys.json` v2** holds two locks on the data key, each AES-256-GCM under an Argon2id key: the password (128 MiB, 4 passes) and recovery key plus answer together (256 MiB, 8 passes). A copy in `backups/keys.json` is read when `keys.json` is missing or damaged.
- **One thing opens, two things change.** The password opens; recovery key plus answer set a new password. While open, being open counts as the password: a new password needs the answer or the recovery key, a new question needs the recovery key, a new recovery key needs the answer (replacing the old only once confirmed). Any two restore the third; losing the password and another loses the data. A change rewraps the same data key; nothing is re-encrypted.
- **Wrong tries** (`AttemptGuard`, `attempts.json`): five free, then waits of 1, 5, 15 minutes and 1 hour; never a permanent lockout.
- **Same scheme on Windows and Linux** (owner decision): nothing is tied to hardware or a Windows account. Not in v1: changing the data key or rewriting backups.
- **Threat model:** a copied database or backup without `keys.json` is a 256-bit problem. With `keys.json` someone can guess offline at either lock (Argon2 slows each guess). Nothing protects an unlocked PC from malware.
- **Freed memory is not wiped** (`PRAGMA cipher_memory_security = OFF`, `database/connection.py`, owner decision 2026-10-03; wiping made encrypted reads about 3× slower). SQLCipher still wipes key material; decrypted fragments may persist in freed memory, crash dumps, the page file or hibernation file. The setting is process-wide and cannot be turned back on, so nothing else may turn it on.

**Lifecycle and the database thread.**

- **One thread:** connections are opened, migrated and closed only on the ASGI runtime's owning thread; the GUI sends commands, workers only return data. The socket is bound and the instance lock taken before any database work.
- **Lock, switch, shutdown** stop new operations, invalidate the session generation, drain requests, close connections, wipe keys, release the lock last. Finance writes carry the generation token, so a stale tab cannot save into another profile. Idle lock: 15 minutes of foreground activity.
- **Session roles** (`runtime/roles.py`): *home* (writable), *borrower* (a PC's working copy) or *reader*. A reader opens a real read-only SQLite connection (`build(read_only=True)`: no backup, migration, seed or payment matching; a copy needing upgrade is refused); the request gate only explains "This is a read-only copy". `SessionGate.change_role` reopens the profile in another role between requests, with no password. A borrowed profile lives in `<local app data>/Lightning/borrowed/<profile_id>/`, never in Documents or a synced folder.
- **Migrations** commit each script and its version row together. A missing migration resource or newer-schema database stops the app before any write. Before a pending migration a verified pre-upgrade encrypted backup is written and kept outside pruning; if it fails the migration aborts. Backups are encrypted snapshots reopened to check integrity, foreign keys, schema, rows and sequences.

**Restore and promotion** (`runtime/restore.py`, `database/promotion.py`, `promotion_windows.py`; `tests/test_database_promotion.py`). The locked chooser links each backup to a password and confirmation screen. Restore accepts only a backup of that named profile, verifies key and schema, keeps the selected bytes and a verified pre-restore snapshot, migrates a private candidate, records a versioned hash manifest before phase P1, and publishes through P0–P5 under the instance lock, leaving the session locked. Unlock compares manifest, journal and retained hashes. Restore and unlock refuse ambiguous sync control, unresolved evidence, SQLite sidecars and missing or corrupt retained files. A password-gated repair screen can resume one matching P1–P4 journal forward to P5; there is no automatic rollback. Legacy import is not built; the preview fetches no prices at startup.

**Promotion durability risk and release gate.** The journal and hashes stop an uncertain state opening for writes, but they rely on the OS and device honouring completed flushes (POSIX fsync of file and directory; Windows `MoveFileExW` with `MOVEFILE_WRITE_THROUGH`, which has no parent-directory equivalent). A sudden power loss may lose or reorder writes and recovery may need an older backup. Tests cover injected disk and flush failures, process kills at each durable phase and one real SQLCipher restore per adapter; they are not power-loss evidence. Before accepting restore for real data, run it with dummy encrypted data on an ordinary Windows PC: interrupt at the phase boundaries, restart, confirm unlock reaches the verified checkpoint or stays locked with evidence intact and no write path; record device, filesystem, method, phase and outcome, and report a normal reboot or process kill apart from an abrupt power cut. Without a real power-cut drill, label this **unverified** and require an explicit release-risk decision in [OWNER.md](../OWNER.md).

**Multiple devices** (built 2026-10-06, milestone 1; plan and unbuilt tasks: [proposals/multiple_devices.md](proposals/multiple_devices.md)). The phone is the ledger's *home*; a paired PC *borrows*, edits and hands back; one writes at a time. `tests/test_two_devices.py` walks the journey through the screens.

- `sync/domain.py` protocol (v1 frozen in `tests/fixtures/sync_v1.json`; a wire change needs a new `PROTOCOL_VERSION`); `sync/state.py` home and borrower state machines; `sync/control.py` a FULL-synchronous control store per profile per device, outside the profile folder (a missing or damaged record blocks writes, never resets to "at home"; `blocks_restore` is the restore check); `sync/service.py` lend and hand back; `sync/identity.py`, `sync/transport.py` the link; `runtime/devices.py` the app side.
- **Lend and hand back:** the home checkpoints (unlocked only), refuses a borrow when the live ledger's fingerprint differs from the checkpoint, and reopens read-only before granting. A returned copy is verified (pages, integrity, schema, `profile_identity`) and promoted when the phone is unlocked; the old copy stays as `<name>.before-<return id>.db` (last three kept). A failed verification leaves NEEDS_REPAIR with every file kept. A PC's copy is writable only while BORROWING; lock, idle lock and closing hand back when the phone answers within 5 s, else seal.
- **Link:** ECDSA P-256 key and self-signed certificate per device; the phone listens on port 47513 with TLS 1.3. Pairing uses a one-time 12-character code on the phone (ten minutes; three wrong codes per address, twenty in all), proved by HMAC bound to the certificate, with six check digits on both screens; the phone sends the profile's locked key file, so the PC uses the same password (owner, 2026-10-06: one password per profile). The PC then pins the certificate and signs every challenge. Limits: 16 connections (4 per address), 16 KB messages, a copy refused unless the device has room for it plus 64 MB.
- **Moving a home** (`move_to_phone`, `_receive_move`): two-phase, so a lost `MoveDone` never leaves two writable copies (the phone keeps the ledger hidden as `<name>.arriving` until the PC first connects as borrower; `moving.json` lets the PC finish after a crash).
- **Guards:** a profile set up for lending carries `lending.json`; if its device record is then missing (cleared app data, a copied profile) it opens read-only and Devices offers *Keep this copy* (new lineage). Restore is refused while lent or mid hand-back.
- **Not built:** prefetch while the password is typed, periodic recovery copies, discovery (the PC types the phone's address), resumable transfer, comparing copies on take-back, the two-PC fault gate, power-loss evidence.

**Local server security** (`lightning/runtime/http.py`). Loopback only, random port; Host and Origin must match exactly. A single-use launch code (30 seconds) is exchanged for a per-instance HttpOnly, SameSite cookie required on every request. `no-store` responses, a nonce-based script CSP, no inline event attributes. `Referrer-Policy: same-origin` (`no-referrer` would turn same-origin POSTs into `Origin: null`). Ordinary POSTs are capped at 512 KiB (`MAX_BODY`); the CSV import route takes up to 5 MiB with separate bounds for its mapping and confirmation requests, and the multipart spool threshold is raised so CSV bytes stay in memory, never plaintext temp files (verify this if limits change). PDFs are not accepted. No outside requests; access logs are off; logs never hold query strings, form values, amounts, names, tokens or keys.

**Window** (`lightning/desktop/window.py`). `edgechromium` is required (no IE fallback); a native navigation guard is attached before any page loads, and startup fails visibly if it cannot be. Blocked: foreign origins, unexpected schemes, new windows, file drops. No `js_api`, no remote debugging port. pywebview's `storage_path` never points at user data (6.2.1 deletes it on exit in private mode). A repeat launch focuses the locked profile's window.

**Build and release.** Actions minutes are limited and Windows counts double (owner, 2026-10-06), so nothing is built or tested twice. The rules for what each push, daily, manual and tag run does are in `packaging/ci_scope.py` and `.github/workflows/desktop-probe.yml` ("PC and phone app") and `android-app.yml` ("Phone app").

- **The ZIP that ships is the ZIP that was tested.** `packaging/package_app.py --strict` packages the PyInstaller build (README, `BUILD_INFO.txt`, licence notices with `packaging/notices/`, `Lightning.exe.config`, price packs; it refuses any database, key, log, profile or backup) and writes `APP_SHA256SUMS`. CI checks the ZIP against it, extracts it fresh, marks it downloaded (`Zone.Identifier`) and requires that `Lightning.exe` passes `--self-check` and `--smoke` through `packaging/run_check.ps1`. Only then is it uploaded.
- **Names:** only a tag matching the source version makes `Lightning-v<version>-Windows-x64.zip`; any other build is `…-dev-r<run>-<commit>-…`.
- **Matched test builds** (owner, 2026-10-07: the owner reviews milestones with one PC and one phone build of one commit): a manual run on `main` gives `Lightning-Test-<version>-<count>-<commit8>-PC` and `…-Phone` (`packaging/phone_build.py bundle`), seven-day downloads, never a release.
- **Phone test app:** CI builds **Lightning Test** (`org.lightning.app.test`, `versionCode` = commits on `main`, name `<version>-test.<count>+<commit8>` also in `lightning/build_identity.txt`); local builds stay `org.lightning.app` for Google Play. Python packages come only from `requirements/android.lock` (`tools/android_lock.py`, `--no-index`); `phone_build.py check` fails an APK that breaks the lock, the permission list `packaging/android-permissions.txt`, arm64-only libraries, or holds a database, key, backup or log. A second job, the only place the test key exists, signs it.
- **Beta signing key:** repository secrets `ANDROID_KEYSTORE_BASE64`, `ANDROID_KEYSTORE_PASSWORD`, `ANDROID_KEY_ALIAS`, `ANDROID_KEY_PASSWORD`; its fingerprint is pinned in `packaging/android-test-certificate.sha256` and a missing secret or mismatch fails rather than sign with another key (Android updates only same ID, certificate and non-falling `versionCode`; losing the key means one uninstall). Google Play needs an App Bundle under `org.lightning.app`; this APK cannot be promised to update a Play install.
- **Releasing a version:** (1) bump `lightning/__init__.py` and `pyproject.toml`, add the changelog entry, push to `main`; (2) tag that commit (`git tag v1.0.0-beta.1 <commit>`, push the tag); (3) CI refuses a tag differing from `v<DISPLAY_VERSION>` or not on `main`; after the Windows and signed phone jobs pass, the release job publishes both tested files to `elfekimuhammed/Lightning-downloads` (prerelease for a beta); it never replaces a release or tag, publishes a draft only after reading its uploads back byte for byte, and stops on any other draft (`tests/test_release_publish.py`); (4) add the version to the website's archive by hand; earlier entries stay.
- **One-time setup (owner):** a fine-grained token limited to `Lightning-downloads` (Contents: read and write) as Actions secret `LIGHTNING_DOWNLOADS_TOKEN`, and release immutability on in that repository.
- **Distribution:** unsigned. An Actions artifact needs a GitHub sign-in and expires after seven days; it is a CI handoff, not hosting. Owner decision (2026-10-03): keep at least the three latest versioned downloads permanently, each an immutable asset with its own website entry; delete a version only if the owner decides. Never make disabling Windows protections part of installation. Signing becomes necessary if recipients' PCs refuse the build.
- **Updating:** close the app, extract the new ZIP into a fresh folder, launch. Data stays in Documents. An old build refuses a newer schema; rolling back needs the matching pre-upgrade backup.
- **Developer checks:** `python desktop_app.py --self-check --report result.json` uses disposable data; on Windows `--smoke` checks the real chooser. `packaging/check_profile_browser.cjs` drives Chromium and Firefox through setup, saves, cross-tab lock, reopen, mobile layout and CSP.

**Open before a beta.** Legacy import and safe promotion of a backup restore; native file pickers; a clean-machine pass on ordinary PCs, including the second PC that failed at window startup; ZIP update acceptance from N to N+1; Windows and Linux acceptance runs.

## Working rules

1. Check `git status` first; preserve existing user changes and personal data.
2. Define a new concept in the Glossary before building it.
3. Persistent state needs a new migration and a module that owns its table. Never rewrite an applied migration.
4. Cross-module actions go in a workflow or service, with all writes in one database transaction.
5. Post every main-ledger effect through `TransactionService`. Generated valuation journals use `source=SYSTEM` and stable links to their reevaluation details.
6. Keep the UI thin (see UI contract).
7. Test the changed workflow and its invariants (date and money edge cases, ownership and net-worth effects, posting, archive, void). Run the full pytest suite, the import-boundary checks and `git diff --check`. Keep meaningful business assertions when updating old tests.
8. For UI changes check populated and empty data and a 390px viewport, and re-run Mohab (`tests/test_mohab_year.py`) when a workflow changes.
9. Log changes under `Unreleased` in `CHANGELOG.md`; keep the files in AGENTS.md section 1 consistent, and add no new files under `docs/`.
