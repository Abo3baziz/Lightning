# Gam'eya (rotating savings circle)

Owner decision 2026-10-14: build it on the certificate (CD) backbone, with the interest rate optional (none by default). Upcoming project #14. Built by `claude/gameya`; once built, move what holds into Architecture › Certificates and time deposits and delete this file.

## What a gam'eya is

N members each pay the same instalment every month; each month one member takes the whole pot (N × instalment). Taking an early turn is borrowing from the circle; a late turn is saving. Your turn is fixed when you join.

## The model: one account per circle, balance = paid in − received

- **New account type `GAMEYA`** ("Gam'eya (savings circle)", short "Gam'eya"), one account per circle, in one currency, holding only that currency's cash asset. Not liquid: left out of Cash you own and Free cash, like a CD portfolio.
- **Every movement is a real transfer** (`DocType` of an ordinary internal transfer, `Effect.INTERNAL`, never income or spending):
  - instalment: funding account → circle account;
  - payout (your turn): circle account → payout account.
- **The balance tells the position.** Positive = the circle owes you (you have paid more than you took). Negative = you owe the circle (you took the pot early). Net worth stays right through every step with no special posting.
- **Figures** (`planning/position.py`, Glossary, `core/figures.py`):
  - positive circle balances join *What you own* as **Gam'eya paid in** (beside Deposits; counted in Holdings value like deposits, owner decision 2026-10-04, sale factor 1: a circle cannot be sold early);
  - negative balances join *What you owe* as **Gam'eya still to pay** (the remaining instalments after your turn). `What you owe = Bills due + Loans still to pay + Gam'eya still to pay`.
  - Not in Bills due (that would count the same debt twice).
- **Owned-cash checks:** an instalment from cash you do not have on that date is refused with the CD's wording (`DepositService.purchase` checks); a circle account's own negative balance is allowed by design.

## Terms (the CD backbone)

Table `gameya_terms` (migration `0053_gameya.sql`), one row per circle account, mirroring the account-level `cd_terms` shape:

| Field | Rule |
|---|---|
| `organiser` | Who runs it (a person's name; a counterparty, picked or typed, never auto-created silently) |
| `members` | Whole number, 2 to 60 |
| `installment_e6` | Above zero, 2 places |
| `frequency` | `MONTHLY` only in v1 (the enum leaves room for `WEEKLY`) |
| `first_date` | First instalment date; may be in the past (joining mid-way is recorded by entering past instalments) |
| `my_turn` | 1 to `members`; payout date = `first_date` + (`my_turn` − 1) months, month-end clamped like planning items |
| `payout_e6` | Default `members × installment`; editable (an organiser may keep a cut) |
| `annual_rate` | Default 0 = **No interest** (the form's default choice). If above 0: an estimated return, simple interest on the positive balance by actual days ÷ 365 in `Decimal`, paid at your turn; estimate only, like CD interest |
| `funding_account_id`, `payout_account_id` | BANK or CASH, same currency as the circle |

## Forecast and recording

- `future_events` emits `INSTALLMENT` (outflow from the funding account), `PAYOUT` (inflow to the payout account) and, with a rate, `INTEREST` events, using the existing `DepositEvent` so Cash planning shows them beside projected CD proceeds, labelled.
- The circle page shows: paid *k* of N, next instalment, your turn date, balance as "The circle owes you" or "You owe the circle", and two prefilled actions: **Record instalment**, **Record payout** (date, amount, account from the terms). A recorded event does not change the terms, as with CDs.
- An unrecorded past-due instalment is listed under Needs you (one row per circle, not per month).
- The circle is **finished** once every instalment and the payout are recorded and the balance is zero; it then leaves forecasts and can be closed like any account.

## Screens and copy

PC (Part A) and phone (Part C) both; Arabic labels in `ui/i18n.py` (جمعية). Read `guideline/brand-voice.md` first. A16 applies: soft wells, type-and-pick for accounts and organiser, no dropdown for your own data.

## Tests

- Service: schedule dates, early turn → negative balance → What you owe, late turn → What you own, rate 0 vs rate > 0, refusal without cash, finished state.
- Position: Net worth unchanged by each instalment and by the payout.
- Mohab: add a gam'eya step to `tests/test_mohab_year.py` (he joins a 10-member, 2,000 EGP circle, turn 3) and remove "gam'eya" from the Overview's *Not scripted* list.
