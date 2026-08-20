# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

Standalone Django REST API backend for the kpground family site (`kpground.com`) and its games (currently KatTrap). Not merged with either frontend — `kpground` and `kat_trap` are separate repos, both static sites with no build step, that call this API via `fetch()`. This service owns identity/auth (meant to be shared across every game, not just KatTrap) plus each game's own domain-specific data, namespaced by Django app (`kattrap` today; a second game would get its own app alongside it, reusing the same accounts).

See `../kat_trap/CLAUDE.md` and `../kpground/CLAUDE.md` for the frontends this serves, and the latter's "Auth" section for the original hosting/identity plan this repo implements (with one refinement: token-based auth from day one instead of cookie SSO — see below).

## Commands

`uv`-managed Python 3.12 project (installed via `uv python install 3.12` — the system Python here was 3.9). Everything runs through `uv run`; dependencies are managed with `uv add`/`uv sync`, not pip/poetry (`pyproject.toml` has `[tool.uv] package = false` since this is an application, not an installable library).

- `uv run python manage.py runserver` — dev server
- `uv run python manage.py makemigrations` / `migrate`
- `uv run python manage.py check` — cheap sanity check, worth running before anything else after a settings/model change
- `uv run python manage.py seed_kathryn` — idempotent: creates the KatTrap OAuth2 `Application` (public client, password grant) + Kathryn's user (unusable password — she only ever authenticates via quick-login) + her three character wallets
- `uv run python manage.py seed_store` — idempotent: seeds a **placeholder** store catalog (see Known gaps below)

Local dev needs no setup beyond `uv sync` — `DATABASE_URL` is optional and falls back to a local `db.sqlite3` (gitignored). Copy `.env.example` to `.env` to override any setting.

No test suite exists yet — verification so far has been manual, via `curl` against a running dev server for every endpoint. That's a real gap, not a deliberate choice.

## Architecture

### Two apps, one clear split

- **`accounts`** — identity. A custom `User` model (thin `AbstractUser` subclass, no extra fields yet — set as `AUTH_USER_MODEL` from day one, since swapping it in later after real data exists is a much bigger migration than starting with an empty custom one) plus the two login paths.
- **`kattrap`** — KatTrap's own game data (wallets, store, purchases, daily gift). Intended to be one of several game-specific apps sharing the `accounts` identity layer as more games get added — don't fold KatTrap-specific logic into `accounts`, and don't assume `kattrap`'s models are the template every future game app must copy exactly.

### Auth: OAuth2 bearer tokens, not sessions/cookies — and why that matters here

Chosen deliberately over Django's default session/cookie auth, even though today every frontend is a subdomain of `kpground.com` (where a shared cookie would still work). The reason: KatTrap (and other games) are expected to eventually move to their own top-level domains (e.g. `kattrap.com`), at which point a cookie scoped to `.kpground.com` stops working entirely — a hard browser boundary, not a config setting, and third-party cookies are being phased out generally regardless of domain-matching. Bearer tokens work identically whether a frontend is on a `*.kpground.com` subdomain or its own TLD, so this auth investment doesn't need redoing when that happens.

Implemented via `django-oauth-toolkit` (`REST_FRAMEWORK['DEFAULT_AUTHENTICATION_CLASSES']` = `OAuth2Authentication` in `config/settings.py`). Two ways to obtain a token, both returning the identical JSON shape (`access_token`/`refresh_token`/`token_type`/`expires_in`/`scope`) so a frontend can treat them interchangeably:

1. **Regular login** — `POST /o/token/`, django-oauth-toolkit's own stock endpoint (no custom code), with `grant_type=password&username=...&password=...&client_id=kattrap-frontend`. Password (Resource Owner Password Credentials) grant was chosen over a redirect-based Authorization Code flow specifically because every frontend here is a static, first-party, vanilla-JS site with no server to receive an OAuth redirect callback — a login form POSTing straight to the token endpoint is the simplest fit for that constraint. If a genuinely third-party integration is ever needed, add a real Authorization Code + PKCE flow alongside this rather than replacing it.
2. **Kathryn quick-login** — `POST /api/auth/kathryn-quicklogin/` (`accounts/views.py`), a no-password shortcut that mints a token pair directly for one known seeded account, bypassing the password check entirely. Gated on `settings.ENABLE_KATHRYN_QUICKLOGIN` (env var, defaults `True`) — a genuine "log in as Kathryn, no password" door, an accepted tradeoff for a private family site's actual first/primary player, not an oversight. Flip the env var off once a real login flow exists for anyone else, or if this stops being just-for-her. Everything downstream (wallet/store/gift endpoints) is identical to a normal login; only the login step is skipped.

Access tokens are deliberately long-lived (14 days — `OAUTH2_PROVIDER['ACCESS_TOKEN_EXPIRE_SECONDS']`) so the vanilla-JS frontends don't need refresh-token handling built yet. Revisit if that tradeoff stops feeling acceptable.

`KATTRAP_CLIENT_ID`/`KATHRYN_USERNAME` (`accounts/constants.py`) are shared between `seed_kathryn` and the quick-login view so they can't drift apart — the `Application` and the user account are both looked up by these fixed values, not by name/heuristic.

### KatTrap's economy: currency and levels are per-character, not per-account

The central modeling decision in `kattrap/models.py`: a user has **three independent wallets** — `CharacterWallet(user, character, coins, level, xp)`, one row each for Cat/Mouse/Dog (`unique_together`) — not one account-wide balance. Coins/XP earned playing Cat only ever land in the Cat wallet; a Cat store item is gated by Cat-wallet level, never Mouse or Dog progress. This was an explicit, later refinement of an initial one-wallet-per-user design — when adding anything economy-related, check which specific wallet(s) it should touch rather than assuming a single balance exists.

A planned (not yet built) "aggregate" store, spendable against the *sum* of a user's three wallets, is meant to be a read-only computed sum over the three existing wallets — don't add a fourth currency/wallet type for it later.

`StoreItem(character, slug, name, item_type[cosmetic|perk], cost, min_level)` is a per-character catalog — its `character` field is both "which wallet pays for this" and "which wallet's level gates it". `OwnedItem(user, item)` is a permanent purchase record (`unique_together` blocks re-buying the same item).

`kattrap/economy.py` holds every tunable number (coin/XP amounts per round outcome, daily gift amount, the XP-per-level curve) as plain module constants, deliberately not DB-configurable — retune by editing this file, not by adding an admin-editable settings model, until there's an actual need to change these without a deploy. `XP_PER_LEVEL` uses a flat linear curve (advancing from level N to N+1 costs `N * XP_PER_LEVEL`) as the simplest starting point, untested against real play data. Coin/XP amounts are currently flat by outcome (`WIN_COINS`/`LOSS_COINS`, `WIN_XP`/`LOSS_XP`) — the loss amount is deliberately small but non-zero so losing still feels like progress; a performance-scaled bonus (time survived, close-call escapes) is planned as an addition on top of this, not a replacement.

**In-gameplay coin pickups** (collectibles during a round, separate from the round-completion reward) are handled by `submit_round()` (`kattrap/services.py`) taking a `coins_collected` param — meant to be tallied client-side during play and submitted once at round end, not one network call per pickup. `MAX_COINS_COLLECTED_PER_ROUND` caps what a single submission can credit — a sanity ceiling against a malformed/tampered client, not a full anti-cheat system (not warranted by this app's actual threat model).

### Business logic lives in `services.py`, not in views

`kattrap/views.py`'s `APIView` classes stay thin — parse the request, call a `services.py` function, serialize the response. `purchase_item()`, `claim_daily_gift()`, and `submit_round()` do the actual work, independent of HTTP, and are where any new economy rule belongs. `PurchaseError` is a plain exception carrying a user-facing message, caught in the view and turned into a 400.

Wallet-mutating operations wrap in `transaction.atomic()` and take `select_for_update()` on the wallet row(s) being changed — deliberate, since these are read-modify-write balance updates. `DailyGiftClaim`'s `unique_together(user, claimed_date)` is the actual guard against a double claim, not application logic alone — `claim_daily_gift()`'s `get_or_create` just turns a would-be race into a clean "already claimed" result instead of a raw `IntegrityError`.

`get_or_create_wallets()` lazily creates any of a user's three wallets that don't exist yet, called from every wallet-touching endpoint — only Kathryn's account is pre-seeded (via `seed_kathryn`), so any other/future user gets wallets created on first API call rather than needing a manual seed step.

### Settings are entirely environment-driven (`config/settings.py`)

Every real value (`SECRET_KEY`, `DEBUG`, `ALLOWED_HOSTS`, `DATABASE_URL`, `CORS_ALLOWED_ORIGINS`, `ENABLE_KATHRYN_QUICKLOGIN`) comes from `python-decouple`'s `config()`, documented in `.env.example` — there's no real production secret hardcoded anywhere, only an explicit dev-only fallback for `SECRET_KEY`. `DATABASES` uses `dj_database_url.config()` against `DATABASE_URL`, falling back to local SQLite when unset — the intended database in any real environment is Neon Postgres (see `../kpground/CLAUDE.md`'s hosting plan), but nothing here hardcodes that; any Postgres-compatible `DATABASE_URL` works. `CORS_ALLOWED_ORIGINS` has to list each frontend origin explicitly — CORS is unrelated to the OAuth2 bearer-token auth itself (tokens aren't cookies, so cookie-domain rules don't apply), but a browser still won't let a page on one origin call this API at all unless CORS allows it.

## Known gaps (worth knowing before extending this)

- **No test suite.** Verification so far has been manual `curl` checks against a running dev server for every endpoint added.
- **No deploy config yet.** Not deployed anywhere — the plan is a Render Web Service + Neon (see `../kpground/CLAUDE.md`), not yet done. Local dev only so far.
- **`seed_store`'s catalog is placeholder data** for exercising the purchase flow, not final game content — real item names, costs, and any cosmetics still need designing.
- **No frontend integration yet.** Neither `kpground` nor `kat_trap` calls any endpoint here yet (planned for KatTrap: "I'm Kathryn"/"Login" buttons on `SetupScreen`, token storage, wallet/store UI, in-game coin pickups).

## When working in this repo

- Keep `accounts` (identity, shared across future games) and `kattrap` (this game's own data) separated the way they are now — a second game should get its own app alongside `kattrap`, not have its models merged into it.
- Any new tunable economy number belongs in `kattrap/economy.py` as a plain constant, not inline in a view/service or in a DB-editable settings model.
- Any new wallet-mutating endpoint should go through `services.py` with `transaction.atomic()` + `select_for_update()` on the wallet row(s) it touches, matching the existing purchase/claim/submit functions — don't mutate `CharacterWallet.coins`/`.xp`/`.level` directly from a view.
- Update `.env.example` alongside any new `config()`-read setting so local setup stays accurate.
