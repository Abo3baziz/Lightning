# Zakat

Owner decision 2026-10-14: build it. Upcoming project #14. Built by `claude/zakat`; once built, move what holds into Architecture and delete this file.

## Rule: an estimate by the common rule, never a ruling

Zakat due = 2.5% of zakatable wealth when it is at or above the nisab on your zakat day. The page says, once and plainly, that it uses the common rule and that a scholar answers your own case (`guideline/brand-voice.md`). No score, no nagging.

## Calculation (`lightning/zakat.py`, `ZakatService.assess(day)`, Python only)

Built from the one position calculation (`planning/position.py`), never re-adding balances:

| Line | Source | Default |
|---|---|---|
| Cash you own | bank, wallet, brokerage cash (owned only; *Held for others* never counts) | Counted |
| Deposits | CD principal (estimated interest not yet paid is left out) | Counted |
| Gam'eya paid in | positive circle balances, once `claude/gameya` is on `main` | Counted |
| Shares and funds | Holdings value at the latest price | Counted at full value |
| Gold you hold as savings | physical gold by grams and karat at the gold price | Counted |
| Gold you wear | pieces marked as worn | **Setting**, off by default |
| Debts due now | Bills due + Gam'eya still to pay that is due by the zakat day | **Setting**, deducted by default |

- **Nisab** = 85 g of 24K gold × the gold price on that day (the app's gold estimate, `XAU:24K`). With no gold price the user types the nisab once; it is kept and dated. A silver nisab (595 g) is a setting for later, not v1.
- **Zakat day:** the user picks a date once; the next one is 354 days later (a lunar year). Hijri dates are not built; the page shows the Gregorian date and says it follows the lunar year.
- **Paid:** zakat is paid as ordinary spending in a system category **Zakat** (add to the seeded system categories, migration `0054_zakat.sql`, which also holds the settings table). The page shows *Paid this zakat year* from that category and *Still to pay* = due − paid, never below zero.
- Cash planning shows the next zakat day's estimated amount as a dated, labelled forecast line (changes no balance), and nothing until the user sets a zakat day.

## Settings

Table `zakat_settings` (one row): `zakat_day`, `typed_nisab_e6` and its date, `count_worn_gold` (0), `deduct_debts_due` (1). Physical gold pieces get an optional `worn` flag (same migration). Settings sit behind the page's gear (Overview decision: settings behind a tab's gear).

## Screens

A Zakat tab where wealth questions are answered (check the section map in the guideline before placing it; at most five tabs per section). PC (Part A) and phone (Part C); Arabic in `ui/i18n.py` (الزكاة). Header, then the list of lines with their amounts, then Zakatable wealth, Nisab, Zakat due, Paid, Still to pay. A16 applies.

## Tests

- Below nisab → nothing due; at nisab → 2.5%.
- Held for others never counts; worn gold only with the setting; debts deducted only with the setting.
- Paying in the Zakat category lowers Still to pay; a payment before the zakat year does not.
- Mohab: a zakat-day step in `tests/test_mohab_year.py`.
