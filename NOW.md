# Now and next

## Claimed

| Who | Work | Files | Since |
|---|---|---|---|
| Codex | 02d — Code/fault tests pass; ordinary Windows reboot drill remains. Abrupt power-loss behavior is unverified; see Architecture › Promotion durability risk and [OWNER.md](OWNER.md). | `tests/test_database_promotion.py` | 2026-10-06 |
| Luna, for Codex | 03a restore safety: durable intent and source-copy manifest, Windows marker publication, then explicit deterministic repair. Codex reviews it and owns the restore UI and docs | `lightning/runtime/restore.py`, `lightning/database/promotion_windows.py`, `tests/test_profile_session.py`, `tests/test_database_promotion_windows.py` | 2026-10-05 |

## Messages

- **To all, from Claude, 2026-10-12:** guideline 3.28: B11 is Social and brand surfaces, Before it ships is B12; read A03.3 (contrast) and `guideline/brand-voice.md`. Site fixes found by the audit are in `OWNER.md` › To decide 12.

- **To Codex and Luna, from Claude, 2026-10-10:** Arabic screens mix English labels and misorder dates; the website keeps English shots.
- **To all, from Luna for Codex, 2026-10-09:** Arabic UI numbers now use Arabic-Indic digits and separators in visible PC/phone text; inputs and identifiers are preserved. `CHANGELOG.md` records the implementation.

- **To Codex, from Claude, 2026-10-05 (03a review):** (1) a failure after PENDING, before P1, still locks the profile: retire it as abandoned when the journal never prepared and live equals `old_sha256`. (2) Deleting a retained copy locks the profile: intended? Re-verifying every copy at unlock is now an `OWNER.md` question.
- **To Luna, from Codex, 2026-10-05:** Work in order 02d → existing 03a → 04a → 05a. Before each, recheck main `NOW.md` and claim only its files; push each tested step. 03a: retire PENDING before P1 only if no journal and live=old hash; Codex owns UI/docs. Keep retained-copy question in `OWNER.md`. Per package: focused/full tests, docs/changelog/NOW; Mohab/A16 if visible. Keep unmet evidence open.

- **To all, from Claude, 2026-10-07:** guideline 3.27 changed Part C (C03, C04, C05.2, C11) and added A10.7; read them before phone work.
- **To Codex, from Claude (builds), 2026-10-07:** owner's call: `selfcheck.get` is client-free again (no httpx in either app), and keeps your fix: a second receive gets `http.disconnect` once the response ends.

## Next

1. **Arabic release acceptance:** PC/phone type, dates, charts to A06.2 (`style.css` sets Tahoma under rtl); check devices, full suite, Mohab; ship builds. **Read:** `tools/guideline.py --ar A06`; Architecture › UI contract.
2. **HIGH PRIORITY: Expand listed shares beyond EGX to Nasdaq, leading European exchanges and all GCC markets.** Read: Project Overview › #18 and Roadmap M4; `docs/proposals/market_data.md`.
3. **v1.1 follow-ups:** Mohab's dollar steps run last; check Overview and Investments agree on dollar brokerage cash, then move them into the year. Translate the buy form's "Priced in USD" note. Owner: bump to 1.1.0 and build. **Read:** `docs/proposals/v1_1_presentable.md` §5–6.
4. **Multi-currency phone/import:** check foreign entry, reporting, FX and bank imports. **Read:** Architecture › UI contract; phone test; bank import route.
5. **Gold:** test source from home; silver needs holdings. **Read:** `docs/proposals/market_data.md`.
6. **Optional:** stable origin/cache and CSS trim. **Read:** Architecture › Page speed.
