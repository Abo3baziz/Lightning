# Competition: our compass

Last reviewed 2026-10-13. Who else helps people with their money, what their users love and hate, and what that means for Lightning. When a product decision is unclear, read *The compass* first. Every competitor fact is dated "as of" its reading; most Egyptian-app facts are from 2026-10-04 and are stale after about three months. *Evidence limits and sources* says what is solid.

## Contents

| Section | Read it when |
|---|---|
| The compass | You must choose between two designs or two priorities |
| The field in one table | You want to place Lightning against everyone else |
| What users love and hate | You are designing a screen, a first-run step or a paywall |
| Local competitors | You are working on capture, Arabic or bank SMS |
| International competitors | You are comparing a feature with the best apps |
| Phone flow, words and icons | You design a phone screen, or choose between an icon and a word |
| Where Lightning wins and loses | You write the website or plan the roadmap |
| Selling points, stress-tested | You write a headline, a hero line or a claim about what only Lightning does |
| Watch list | Every few months, or before a release |
| Open source | You want source code to inspect before designing a finance feature |
| Actual Budget code analysis | You plan a feature Actual already has, or want to know what to borrow and what to leave |
| Evidence limits and sources | You doubt a claim here |

## The compass

1. **Capture beats analysis.** The most loved apps (Say, Money Manager, Copilot) win on how fast one spend is logged: voice, autocomplete, bank SMS. A ledger that is not filled in answers nothing. Phone capture and bank SMS come before more reports.
2. **Free, private and offline is the Egyptian default.** Local apps run offline with no account. A cloud login or a subscription needs a reason a user feels in the first week.
3. **Arabic and Egyptian money first.** Vodafone Cash, InstaPay, gold, certificates, CIB and NBE SMS. International apps do not know them; local apps know only the first few.
4. **Never be the busy one.** YNAB's most common complaint is a busy interface; Actual's is setup. Mohab's test stands: fewest clicks, one name for one thing.
5. **A wrong number is worse than a missing one.** Every bank-sync review complains of numbers that drift. Lightning shows what each figure includes (Architecture, financial rules).
6. **Price stays obvious; a free trial never asks for a card.** Owner decision 2026-10-04: 7 days free, then a reminder, never a lock. Say's most repeated complaint is a paywall before trying. Users also leave over price rises (YNAB), per-person pricing (Copilot) and ads in paid versions (Money Manager).
7. **Egyptian life is more than spending.** Qershnat adds gam'eya (rotating savings circle), zakat, family assets and reminders, and users ask for more. Wealth is the right ground; gam'eya and zakat wait for the owner (`NOW.md`).

## The field in one table

Prices and features as of 2026-10-04 (Egyptian apps, Google Play) and 2026-10-05 (investment suites, official pages), USD unless stated.

| App | Where | Price | Data lives | Capture / bank link | Wealth |
|---|---|---|---|---|---|
| **Say** (Egypt) | Android, iPhone | Free with limits; Pro about 100 EGP a month, 3-day trial | Cloud | Voice, bank SMS, calendar, email | No (gold only) |
| **Qershnat** (Egypt) | Android | Free so far (in-app items 80 to 800 EGP) | Offline-first, shareable | Manual, bank SMS | Gold, silver, property, vehicles, investments |
| **Masarifi, Masareef, Masroofy** (Egypt, Arab world) | Android | Free with ads; paid removes them | On the phone | Manual; Masareef and Masroofy read SMS | Loans or debts only |
| **Money Manager** (Realbyte) | Android, iPhone | Free with ads, EGP 99.99 once | On the phone | Manual | No. No Arabic |
| **Wallet** (BudgetBakers) | All | Premium subscription | Cloud | Manual; bank sync (15,000+ banks, not Egypt) | Basic |
| **Telda, BM app** (banks) | Phone | Free with the account | The bank | Own accounts only | No |
| **Actual Budget** | Web, desktop, self-host | Free, MIT | Your computer or server | Manual, import; SimpleFIN (US), GoCardless (EU) | No |
| **YNAB** | All | About 109 a year | Cloud | Sync (US, Canada, EU) | No |
| **Monarch** | Web, phone | 99.99 a year | Cloud | Sync (US, Canada) | Net worth, investments |
| **Copilot** | iPhone, Mac, web | 95 a year | Cloud | Sync (US) | Net worth, investments |
| **Quicken Classic Premier** | Windows, Mac | 7.99/month, first-year offer billed annually, then the then-current rate | Desktop file | Manual, downloads (US/Canada) | Deep: lots, IRR/ROI, allocation, retirement |
| **Banktivity** | Mac, iPhone, iPad | Bronze 59.99, Silver 79.99, Gold 99.99 a year; investments from Silver, multi-currency at Gold | Local, optional encrypted sync | Manual, import, sync (14,000+ institutions) | Deep: lots, cost basis, IRR, multi-currency |
| **Moneydance** | Windows, Mac, Linux | 49.99 once | Local, encrypted | Manual, downloads | Stocks, bonds, CDs, funds, cost basis |
| **GnuCash** | Windows, Mac, Linux | Free (GPL) | Local file | Manual, import | Deep accounting: lots, gains, ROI/CAGR |
| **Firefly III, Lunch Money** | Self-host; web | Free; subscription | Your server; cloud | Manual; import, some sync | Accounts only; basic |
| **Lightning** | Windows; Android beta (phone holds the ledger, PC borrows it); English and Arabic | Free so far; 7 days then a licence reminder | Your devices, encrypted, no server | Manual, CSV, PDF statements, bank SMS (Android beta); no bank link | Gold, EGX and US shares, funds, certificates, loans, foreign cash with FX gains |

## What users love and hate

Evidence: Google Play reviews (Egypt, English and Arabic, 2026-10-04) plus review sites. Lightning column checked 2026-10-13.

| Users love | Said about | Lightning today |
|---|---|---|
| Effortless logging: voice, SMS ("I resorted to my notes" before Say) | Say, Copilot | Bank SMS in Android beta; no voice. Still the biggest gap |
| Knowing where the month goes | Say, Telda, Wallet | Have it, deeper |
| Simple, uncluttered, quick add | Money Manager, Masrofi | Quick add partial; menus heavier |
| Pay once, no ads, no subscription | Money Manager | Free now; price undecided |
| No bank login, no cloud ("data stays on your hardware") | Actual, Masroofy, Money Manager | Have it: our strongest shared promise |
| A method that changes behaviour | YNAB, Actual | Rollover budgets and reserves; no "every pound a job" |
| An Egyptian maker who answers ("suggestions added right away") | Say, Qershnat, Masarifi | A visible changelog and a human reply are marketing too |
| Arabic that works: dialects, zakat, Arabic categories | Say, Masarifi, Masrofi | Arabic and right-to-left shipped in v1.1; zakat open |
| Couples and household sharing | Monarch, Qershnat | Missing |
| Zakat and gam'eya built in | Masroofy, Qershnat | Not built; owner question |

| Users hate | Said about | Lesson |
|---|---|---|
| Paywall before any try ("no free trial unless I add my card") | Say (most repeated), Masareef | No card, no account, whole app on day one |
| Bank sync that breaks, no support | Wallet, YNAB, Monarch, Actual | A failed read must say so and never post a wrong figure |
| SMS reading that misses or invents spends | Say, Qershnat, Money Manager, Wallet | Every parsed SMS waits for review; one tested rule per bank |
| Cannot edit or delete a record | Say, Masarifi | Every row editable, always |
| Data lost after a phone change, no reply from support | Masareef, Wallet, Masarifi | Backup and restore tested in Mohab's test |
| A feature removed (Wallet dropped Arabic) | Wallet | Never take away a language or feature people use |
| No Arabic, no Hijri date | Money Manager, Wallet | Launch condition; Arabic shipped |
| Price rises; per-person pricing; one platform | YNAB; Copilot | Stable pricing; say plainly that PC is Windows only |
| Busy interface, hard to learn | YNAB | Every screen answers one question |
| No mobile app, or one that fails | Actual | The phone is the capture tool; it must open every time |
| Needs a server and technical skill | Actual, Firefly III | Install is a ZIP and a double-click |
| No bills, no "safe to spend"; carry-over that fails | Money Manager | Forecast and rollover exist; keep visible |

## Local competitors

Read directly on Google Play (Egypt), 2026-10-04. Ratings drift: refresh before quoting.

- **Say** (Roberto Joseph, Cairo): the one to watch. 4.84 stars from 2,128 ratings, 50,000+ installs; in-app items 49.99 to 999.99 EGP; reviewers arrive "from TikTok" and the maker answers there. Does voice entry, bank SMS (incl. InstaPay), goals, debts, instalments, subscriptions and bills, multi-currency, weekly report. Hated: the paywall, a 3-day trial "too short", about 100 EGP a month "a bit high", a free plan cut to 3 accounts and about 7 voice notes, SMS missed for some banks and Apple Pay, no offline, PIN or widget, cannot set the time of a spend, cannot import from other apps (a 4-year Wallet user cannot switch). Users ask for gold, silver, property and informal debts. **Gaps:** no investments, cloud only. We cannot match its capture speed; we beat it after capture, offline and on the free trial.
- **Qershnat (قرشنات):** new and rising, Egyptian, released June 2026; 4.85 from 592 ratings, 10,000+ installs. A life organiser: wallets, budgets, goals, debts, shared wallets, money held for another person, gold and silver prices, gam'eya with turns, tasks, password vault, property, vehicles, investments, SMS, widgets, offline. Complaints: SMS spends "I didn't make" (users ask to review first), lag after an update, "what will it cost when finished?"; users ask for zakat. **It covers the same wealth ground and Egyptian life as Lightning; read it before every roadmap decision.**
- **Masarifi** (4.67, 983 ratings): loved for speed without "philosophy"; asked for debts, edits, spend dates. **Masareef** (4.65, 32,000 ratings, 1M+): "easiest", hated for ads, lost Drive backups after a phone change, a daily-average bug, failing SMS. **Masroofy** (Android, 23 ratings) is not the iPhone Masrofi.
- **Money Manager** (4.67, 466,000 ratings) and **Wallet** (4.78, 387,000): global trackers Egyptians install. Hated by Arabic readers: no Arabic or Hijri date, ads in the paid version; Wallet removed Arabic and cancelled a lifetime plan with data lost. An opening for an Arabic-first app.
- **Bank apps (Telda, BM Online, CIB):** free insights and category budgets, but only their own accounts. Two banks, a wallet and cash give half a picture; the whole picture is our opening.

## International competitors

Review-site summaries, not users' own words (2026-10-04), unless marked.

| App | Loved | Hated | Lesson |
|---|---|---|---|
| **Actual Budget** (MIT, local-first, envelope) | Free, private, familiar to YNAB 4 users | No native mobile app, self-hosting skill, bank sync only SimpleFIN/GoCardless (none for Egypt), thin reports | Closest in philosophy, nearest rival for the technical user. Copy its promise (your data stays yours), not its setup |
| **YNAB** | Changes behaviour | About 109 a year, busy interface, breaking bank links | Do not charge more without adding more |
| **Monarch** | Design, no ads, household, net worth | Glitchy sync, price | Net worth plus household is what people pay for; we have the first |
| **Copilot** | Design | iPhone and Mac only, per-person pricing | Design alone earns a 4.8 |
| **Firefly III, Lunch Money** | Multi-currency, responsive support | Firefly: self-host, manual, no mobile | Support is loved by those who find it |

**Investment suites** (official pages, 2026-10-05; no user-review claims). Benchmark their accounting depth, not their US complexity:
- **Quicken Classic Premier:** IRR/ROI, allocation, dividends, tax-aware lots (FIFO, LIFO, max or min gain, average cost for funds), retirement and tax reporting. Deeper for listed securities and US tax.
- **Banktivity:** closest product-level match (budgeting, local data, real investments). Cost basis per lot, chosen lots on sale, short/long-term gains, ROI and IRR with dividends, multi-currency (Gold), device sync. Stronger conventional engine.
- **Moneydance:** stocks, bonds, CDs, funds, automatic prices, splits, cost basis; an engineering benchmark for bookkeeping longevity.
- **GnuCash:** Investment Lots report (basis, realized and unrealized gains, ROI, CAGR, lot validation). Copy the correctness discipline, not the interface. Not worth copying: stored lots with scrubbers (derive them, [investment_lots.md](proposals/investment_lots.md)), short selling, debit/credit words, report option pages.
- **Lightning's opening against all four:** Egyptian assets and institutions, physical-gold detail, certificates, held-for-others cash, plain language, the ledger/plan/report split.

## Phone flow, words and icons

How the best money apps lay out a phone, read 2026-10-06 (Claude) for the phone audit. Their tab bars: YNAB *Plan, Spending, Accounts, Reflect*; Copilot *Dashboard, Transactions, Investments, Accounts, Categories*; Monarch *Dashboard, Accounts, Transactions, Plan…*; Money Manager *Trans., Stats, Accounts, More*.

- **Words beside every icon.** Every one of them names each tab under its icon. Apple and Material 3 say the same (Material: with four or five tabs, labels on the inactive ones "if space permits"; "should only be used when the icons have a clear meaning"). Nielsen Norman Group: "text labels are necessary to communicate the meaning and reduce ambiguity", and if a fitting icon takes more than five seconds to think of, use a word. Universal icons only stand alone: search, back, close, add (+), more (⋯), settings.
- **Tabs move, they never act.** (Apple: "use a tab bar to support navigation, not to provide actions".) The everyday action, adding a transaction, sits one tap away on the main screens: YNAB puts *Add Transaction* on Plan and on Accounts; Money Manager a + on every list.
- **Home is a short answer and a to-do list;** rows say what a tap does (*Review*, *Pay*); segmented controls are words (Out, In, Transfer).
- **Entry is a sheet:** words first, amount on the number pad, category from recent ones, Save in reach.

**Decided 2026-10-07** after the 2026-10-06 audit (guideline 3.27; Project Overview › Product decisions): words on every tab, the add button on every section, the Overview in one screen with the rest one row away. Sources: [Material 3 navigation bar](https://developer.android.com/reference/kotlin/androidx/compose/material3/NavigationBarItem.composable), [Apple tab bars](https://developer.apple.com/design/human-interface-guidelines/tab-bars), [YNAB mobile tabs](https://support.ynab.com/en_us/spaces-in-the-mobile-app-S1iIZQoqgg.md), [Copilot tabs](https://www.macstories.net/?p=74917).

## Where Lightning wins and loses

Checked against the code, Overview and changelog 2026-10-13 (v1.1: Arabic and right-to-left, Android beta with bank SMS, foreign currency, FX gains, US stocks).

**Wins (say it on the website):**
- One ledger, plans that move no money, reports that read both.
- Wealth depth most budgeting apps lack: holdings and returns beside physical gold, Egyptian certificates, loans, money held for others, foreign cash with FX gains. Quicken, Banktivity, Moneydance and GnuCash are the investment-accounting exceptions.
- Local, encrypted, no account, no server, Windows installer; Arabic with right-to-left.
- Mohab's test: a full year through the screens. One calm, strict brand look.

**Loses (be honest, plan around it):**
- Capture: no voice; bank SMS only on Android beta; no automatic bank feed (every app with sync wins the first week).
- Windows only for PC; most Egyptians budget on a phone.
- No household sharing, receipts or reminders.
- Securities depth: no tax lots or specific-lot selling, splits, reinvested dividends, return of capital, tax reports or TWR (Overview, Deeper investments).
- No community or ratings yet: Say has 2,128, Qershnat 592 in four months.
- No gam'eya, zakat, silver, property or vehicles, which Qershnat has.

## Selling points, stress-tested (2026-10-12)

The owner's eight candidate points, tested against this file, the product docs and the code. "Mine only" and "no one else" claims fail often, because Qershnat, Moneydance, Banktivity and the local expense apps each cover part of the ground. The website never names other apps (B10), so a claim has to be true and provable on its own, never "only".

| # | Point | What the evidence says | Verdict | Safe wording today |
|---|---|---|---|---|
| 1 | Phone and PC in sync | Moneydance syncs devices, Banktivity has optional encrypted sync, Actual has a sync server, every cloud app syncs through its server. The local Egyptian apps are phone only. Ours is Wi-Fi only, no server, **one device writes at a time**; the PC is Windows only; the Android APK is a debuggable beta. | **Unique as a combination** (sync with no server and no account, for Egypt), not as a bare feature | "One ledger on your phone, borrowed by your PC over your own Wi-Fi. No account, no server." |
| 2 | Bank SMS | Say, Qershnat, Masareef and Masroofy all read SMS; Say also does voice and InstaPay. Qershnat users complain of wrong spends and ask to review before posting. | **Parity, not a point.** Our angle is real: every message waits in review, nothing posts until you say so | "Bank SMS wait in review." Not a headline |
| 3 | Recognising a recurring bill | Say tracks subscriptions and bills; Masareef has recurring; Quicken matches. Ours is built (a payment finds its bill). | **Table stakes** | Keep as a detail under "less typing" |
| 4 | Automatic prices | **Built:** EGX shares (Yahoo, one source), funds (Mubasher), FX (Banque Misr), on Update prices and on the first open after a month ends; a typed price wins. **Not built:** gold prices ("test source from home", `NOW.md`), silver (needs holdings), prices are not live or daily. Moneydance, Banktivity and Quicken also fetch prices, for other markets. Qershnat shows gold and silver prices. | **Do not claim "gold and silver".** Shares and funds revalue themselves: true and rare among Egyptian apps | "Your EGX shares and funds revalue themselves each month-end." Add gold when it ships |
| 5 | Every type of asset | Built: cash, wallets, physical gold by piece and karat, certificates, EGX shares, funds, foreign cash, US stocks (v1.1), loans owed, money held for others. **Missing:** silver, property, vehicles, crypto, money lent out (receivables were archived in migration 0011). Qershnat has property, vehicles, silver and investments. | **Overclaim.** The Egyptian wealth set (gold, certificates, shares, funds) in one net worth is real and deep | "Gold, certificates, shares and funds, valued the way each one works." Never "every" |
| 6 | Money in your account that is not yours, and money you lent out | Held for others is built and rigorous: left out of what you own, free cash, income and spending; an expense someone paid for you still counts. Qershnat also lists money held for another person and shared wallets, depth unknown. **Money lent out is not supported.** | **Half true.** Drop "lent out" or build it. Do not say "only" until Qershnat is tested | "Money you hold for family stays out of your numbers." |
| 7 | Cash forecasting | Safe to spend until the next income, with bills, loan payments, certificate interest, goals and an emergency-fund top-up, plus three months ahead. Monarch and Quicken forecast; no local Egyptian app does. | **True and strong** for this market, and it answers the question every salaried user asks | "What you can spend until payday, and your next three months." |
| 8 | Complete privacy | Not true that everyone else sends data to a server: Masarifi, Money Manager, Masrofi, Qershnat (offline-first), Actual, Moneydance and GnuCash are local. Cloud apps (Say, Wallet, Monarch, Copilot, YNAB) are not. Privacy alone is the Egyptian default (compass #2). | **A trust layer, not a differentiator alone.** It becomes unique with 1 and 5 | "No account, no server of ours. We can't see your money." |

**What weakens "I cannot see who uses it":** the 7-day licence check (undocumented; if it calls a server, say so), the website page counter (GoatCounter) and survey emails, and unsigned or debuggable builds. Price fetches go from the user's computer to the source, not to us.

### Recommended top three

1. **Your phone and PC, one ledger, no server** (points 1 and 8 together). The only claim a rival cannot copy quickly, and it answers the privacy worry with something you can see.
2. **The wealth Egyptians really hold, valued for you** (4 and 5, scoped): gold piece by piece, certificates the way banks write them, shares and funds that revalue themselves.
3. **What you can spend until payday** (7 with 6): safe to spend, with money that isn't yours and bills already taken out.


### To verify before the claims go live

- Install Qershnat and test: gold, silver and share valuation, held-for-others money in net worth, SMS review.
- Ship or drop gold prices; decide whether silver, property and vehicles come before any "every asset" claim.
- Document how the 7-day licence is checked.
- Refresh the Qershnat and Say rows (read 2026-10-04).

## Watch list

Check every few months and edit this file. Last full check 2026-10-04 (Egyptian apps) and 2026-10-05 (suites).
- **Say:** Pro price, trial rules, new features, rating, whether it adds investments.
- **Qershnat:** price once "finished", an SMS review step, gam'eya, zakat, rating.
- **Masroofy:** bank-message import and how many Egyptian banks work.
- **Telda and banks:** open banking in Egypt would change our plan; an Egyptian aggregator would change the SMS plan.
- **Actual Budget:** a mobile app, Arabic, or Egyptian bank import.

## Open source

Reference code to inspect for financial rules, as of 2026-10-04. Check the licence before copying any code. Also KMyMoney, OpenBudgeteer, Firefly III (rules, imports). Priority: Sure and Paisa (product and investment overlap), GnuCash (correctness), Actual (workflow machinery), Money Manager Ex (desktop breadth), Cashew (mobile UX).

| Project | What it is | Study it for |
|---|---|---|
| [Actual Budget](https://github.com/actualbudget/actual) | Local-first envelope budgeting, TypeScript | Rules, undo, import matching, schedules, i18n, tests (analysed below) |
| [Sure](https://github.com/we-promise/sure) | Community continuation of Maybe Finance; everyday money and wealth | Account and holding model, portfolio UX, net-worth flows |
| [Paisa](https://github.com/ananthakumaran/paisa) | Budgeting plus stocks, funds, allocation, capital gains | Allocation, capital-gain and portfolio logic (not its tax assumptions) |
| [GnuCash](https://github.com/Gnucash/gnucash) | Double-entry, security lots | Basis, FIFO/LIFO/average, validation |
| [Money Manager Ex](https://github.com/moneymanagerex/moneymanagerex) | Cross-platform, SQLite, stock accounts | Desktop, encryption, forecasts, portable installs |
| [Firefly III](https://github.com/firefly-iii/firefly-iii) | Self-hosted double-entry | Rules, imports, API |
| [Cashew](https://github.com/jameskokoska/Cashew) | Flutter, mobile-first | Entry, flexible periods, mobile navigation |

## Actual Budget code analysis

Read 2026-10-04: a shallow clone of `actualbudget/actual` at commit `9732a44` (rules, templates, spreadsheet, sync and CRDT, bank sync, importers, schedules, undo, reports, i18n, tests, CI, AI-agent files). The app was not run. Actual is TypeScript, Lightning Python: ideas to borrow, not code to copy. Paths are inside `packages/`. Which of these are built, and what is next, lives in Project Overview › Features worth building; this list keeps only what Actual does and what we learned.

| Actual has | Where | Lesson for Lightning |
|---|---|---|
| Rules engine: and/or conditions, split by amount or percent, three stages, indexed | `loot-core/src/server/rules/` | Built (Settings › Rules). Open: suggest a rule from what you file. Actual keeps `learnCategories` off by default: suggest, never learn silently |
| Undo and redo, 20 steps over every change | `loot-core/src/server/undo.ts` | Open: undo for last edit, delete or import. Most trust per line of work |
| Layered import match: exact id, then amount and nearest date; reconciled rows locked; merge two transactions | `accounts/sync.ts` (`matchTransactions`, `reconcileTransactions`), `transactions/merge.ts` | Open: reuse for SMS against CSV, lock a checked month, merge keeping a transfer linked |
| Schedules: skip weekend, amount ranges, detect recurring from three occurrences | `server/schedules/` (`find-schedules.ts`) | Weekend-aware due dates built; public holidays open |
| Budget templates: one line per category fills the month | `server/budget/goal-template.pegjs`, `cleanup-template.ts` | "Fill this month" built, as a form, not text in notes |
| i18n: locale files, string-extract CI, 50 currencies | `desktop-client/src/i18n.ts`, `shared/currencies.ts` | Arabic and RTL built; keep strings translated as screens grow |
| Entry helpers: arithmetic in amounts, `#tag`, Ctrl-K, privacy filter | `shared/arithmetic.ts`, `shared/tags.ts`, `CommandBar.tsx`, `PrivacyFilter.tsx` | All built |
| Reports as a dashboard, 14 types | `components/reports/reports/` | Open: Age of Money (salary-to-salary), a spending calendar, one saved filter shared by search, reports and rules. Leave Monte Carlo |
| One change-note file per PR | `upcoming-release-notes/` | Open: ends changelog conflicts between AIs |
| Tests: e2e with mobile variants, visual regression, migration warning | `desktop-client/e2e/`, `.github/workflows/` | Open: visual snapshots would guard the brand guideline; the migration warning is cheap |

**Do not copy:**
- **The sync design.** CRDT with a hybrid logical clock and merkle trie (`crdt/src/crdt/`). Its issue list shows the cost: "can't open budget on mobile", "can't sync changes" ([#6279](https://github.com/actualbudget/actual/issues/6279), [#7542](https://github.com/actualbudget/actual/issues/7542), [#6223](https://github.com/actualbudget/actual/issues/6223)). Lightning lends the ledger to one writer; the planned replacement is the [edit journal](proposals/edit_journal.md). A row-merge engine alone cannot enforce our financial rules.
- **The calculation engine** (`spreadsheet/spreadsheet.ts`): a second place figures live. Ours come from services; revisit only if the Budget page is measurably slow.
- **Multi-user, OpenID, public API, CLI, plugins:** for self-hosters, not a salaried user on one PC.
- **Text typed into notes as a language:** fails the user who won't read help.

**Bank sync:** five providers behind one pipeline, none for Egypt. If an Egyptian aggregator appears: one normaliser plus the layered match. Until then SMS and statements.

**Where Lightning is ahead:** wealth (Actual has no holdings); six-place scaled integers for gold grams and fund units; encrypted profile at rest (SQLCipher, Argon2id; Actual encrypts only what goes to its sync server); a Windows app and a password instead of Docker; Mohab's test checks right answers, Actual's tests check code and screenshots.

**From its AI-agent files:** `AGENTS.md`, review guidelines and five repo skills; "do not add a setting for every UI tweak". We have the same rules; repo skills for push, changelog and hand-off would be a fit.

### Suggested order

Order of value, from the 2026-10-04 reading: undo; layered match with a locked month; weekend-aware schedules and month fill (both since built); i18n and Arabic (since built); one change note per change. The owner chooses what enters *Next* in `NOW.md`; Project Overview tracks status.

## Evidence limits and sources

**Read directly (2026-10-04):** Google Play, Egypt store, via `google-play-scraper`: app details and the most relevant reviews (60 per language for Say, 40 for the others), English and Arabic. "Most relevant" favours reviews marked helpful and is not a random sample. Arabic quotes are translated.

**Not read:** App Store, Reddit, Facebook, Trustpilot, GitHub discussions, Say's own site. The Actual, YNAB, Monarch, Copilot, Firefly III and Telda rows come from review-site summaries. Quicken, Banktivity, Moneydance and GnuCash were checked against official pages on 2026-10-05; prices can change. Say's rating is 4.84 (Google Play), not the 4.63 of earlier summaries. Check any number or quote at its source before it goes on the website. **Next:** Egyptian Facebook groups, TikTok comments and App Store reviews, from a browser that can open them.

Sources: Google Play (Egypt) for [Say](https://play.google.com/store/apps/details?id=com.moments.expenses&hl=en&gl=EG), [Qershnat](https://play.google.com/store/apps/details?id=com.qrshnat.app.gms), [Masarifi](https://play.google.com/store/apps/details?id=com.tm.my_expenses), [Masareef](https://play.google.com/store/apps/details?id=com.appsqueue.masareef), [Money Manager](https://play.google.com/store/apps/details?id=com.realbyteapps.moneymanagerfree), [Wallet](https://play.google.com/store/apps/details?id=com.droid4you.application.wallet), [Masroofy](https://play.google.com/store/apps/details?id=com.masroofi.masroofi); [YNAB on Trustpilot](https://www.trustpilot.com/review/ynab.com); [Actual review](https://wealthypot.com/budgeting-apps/actual-budget/); official pages of [Quicken](https://www.quicken.com/products/pricing-comparison/), [Banktivity](https://www.banktivity.com/content/plans/plans.php), [Moneydance](https://moneydance.com/hello), [GnuCash](https://www.gnucash.org/).
