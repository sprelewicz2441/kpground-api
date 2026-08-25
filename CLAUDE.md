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
- `uv run python manage.py seed_store` — idempotent: seeds the store catalog. Perks are still placeholder data (real names/costs/cosmetics for Cat/Mouse aren't designed yet), but the dog's outfit cosmetics are real: 4 of 5 planned tutu colors (pink/teal/orange/green) point at real per-color walk-cycle art, `is_active=True`; purple stays a placeholder (`is_active=False`, points at the default `dog_v2.png`) pending its own art regeneration — see the sibling `kat_trap` repo's CLAUDE.md, Currency & economy system section, for that art's own extraction history

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

`StoreItem(character, slug, name, item_type[cosmetic|perk], cost, min_level)` is a per-character catalog — its `character` field is both "which wallet pays for this" and "which wallet's level gates it". `OwnedItem(user, item)` is a permanent purchase record (`unique_together` blocks re-buying the same item). `sell_item()` (`kattrap/services.py`) is the reverse: refunds `SELL_REFUND_FRACTION` (0.2, rounded to a whole coin — see `economy.py`) of `cost` and deletes the `OwnedItem` row; deliberately well under 1.0 so buy-then-sell can't launder coins. Only cosmetics and perks alike can be sold — there's no item-type restriction, unlike equip below.

Cosmetics additionally use `slot` (`ItemSlot`, only `'outfit'` exists today — a real choices field from day one so a future per-piece wardrobe, e.g. hat/top/accessory each its own slot, needs new slot values only, no schema change) and `sprite_src` (the frontend asset path for that look). `EquippedItem(user, character, slot, item)` (`unique_together` on `user`/`character`/`slot`) tracks what's currently worn — no row means the default look for that slot. `equip_item()`/`unequip_slot()` in `services.py` are the only way this table changes; `equip_item()` rejects perks (`EquipError`) and un-owned items. `sell_item()` also deletes any `EquippedItem` row pointing at the sold item first, so a sale can never leave one pointing at something the user no longer owns.

`kattrap/economy.py` holds every tunable number (coin/XP amounts per round outcome, daily gift amount, the XP-per-level curve) as plain module constants, deliberately not DB-configurable — retune by editing this file, not by adding an admin-editable settings model, until there's an actual need to change these without a deploy. `XP_PER_LEVEL` uses a flat linear curve (advancing from level N to N+1 costs `N * XP_PER_LEVEL`) as the simplest starting point, untested against real play data. Coin/XP amounts are currently flat by outcome (`WIN_COINS`/`LOSS_COINS`, `WIN_XP`/`LOSS_XP`) — the loss amount is deliberately small but non-zero so losing still feels like progress; a performance-scaled bonus (time survived, close-call escapes) is planned as an addition on top of this, not a replacement.

**In-gameplay coin pickups** (collectibles during a round, separate from the round-completion reward) are handled by `submit_round()` (`kattrap/services.py`) taking a `coins_collected` param — meant to be tallied client-side during play and submitted once at round end, not one network call per pickup. `MAX_COINS_COLLECTED_PER_ROUND` caps what a single submission can credit — a sanity ceiling against a malformed/tampered client, not a full anti-cheat system (not warranted by this app's actual threat model).

### Business logic lives in `services.py`, not in views

`kattrap/views.py`'s `APIView` classes stay thin — parse the request, call a `services.py` function, serialize the response. `purchase_item()`, `sell_item()`, `equip_item()`, `unequip_slot()`, `claim_daily_gift()`, and `submit_round()` do the actual work, independent of HTTP, and are where any new economy rule belongs. Each has its own exception type (`PurchaseError`, `SellError`, `EquipError`) carrying a user-facing message, caught in its view and turned into a 400 — follow this pattern for any new mutating action rather than returning error tuples or raising a generic exception.

Wallet-mutating operations wrap in `transaction.atomic()` and take `select_for_update()` on the wallet row(s) being changed — deliberate, since these are read-modify-write balance updates. `DailyGiftClaim`'s `unique_together(user, claimed_date)` is the actual guard against a double claim, not application logic alone — `claim_daily_gift()`'s `get_or_create` just turns a would-be race into a clean "already claimed" result instead of a raw `IntegrityError`.

`get_or_create_wallets()` lazily creates any of a user's three wallets that don't exist yet, called from every wallet-touching endpoint — only Kathryn's account is pre-seeded (via `seed_kathryn`), so any other/future user gets wallets created on first API call rather than needing a manual seed step.

### Settings are entirely environment-driven (`config/settings.py`)

Every real value (`SECRET_KEY`, `DEBUG`, `ALLOWED_HOSTS`, `DATABASE_URL`, `CORS_ALLOWED_ORIGINS`, `ENABLE_KATHRYN_QUICKLOGIN`) comes from `python-decouple`'s `config()`, documented in `.env.example` — there's no real production secret hardcoded anywhere, only an explicit dev-only fallback for `SECRET_KEY`. `DATABASES` uses `dj_database_url.config()` against `DATABASE_URL`, falling back to local SQLite when unset — the intended database in any real environment is Neon Postgres (see `../kpground/CLAUDE.md`'s hosting plan), but nothing here hardcodes that; any Postgres-compatible `DATABASE_URL` works. `CORS_ALLOWED_ORIGINS` has to list each frontend origin explicitly — CORS is unrelated to the OAuth2 bearer-token auth itself (tokens aren't cookies, so cookie-domain rules don't apply), but a browser still won't let a page on one origin call this API at all unless CORS allows it.

## Deploy (Render Web Service + Neon) — live

**Deployed 2026-08-25**, confirmed live: `https://kpground-api.onrender.com` (Render Web Service, free tier — not a Static Site, see `../kat_trap/CLAUDE.md`'s Deployment & hosting for that contrast; this is a real Django process, not static files). Environment: Python 3. No `Procfile`; Render's dashboard build/start command fields are used directly since this is a `uv`-managed project, not a plain `requirements.txt` one:

- **Build Command**: `pip install uv && uv sync --frozen && uv cache prune --ci && uv run python manage.py migrate && uv run python manage.py seed_kathryn && uv run python manage.py seed_store && uv run python manage.py collectstatic --noinput`
- **Start Command**: `uv run gunicorn config.wsgi:application --bind 0.0.0.0:$PORT`

**`migrate`/`seed_kathryn`/`seed_store` run inside the Build Command, not a separate Pre-Deploy Command** — Render's free tier has no Pre-Deploy Command *or* Shell access at all (both are Starter-plan-and-up features, confirmed live when the field showed locked/uneditable on this service). Folding them into the build is safe specifically because all three are idempotent (`seed_kathryn`/`seed_store` say so explicitly in their own `manage.py` help text, and a plain `migrate` no-ops once every migration's applied) — they just re-run harmlessly on every deploy. Revisit this (move to a real Pre-Deploy Command) if the service ever upgrades off the free tier.

Static files (admin + DRF browsable-API CSS/JS only — this API has no other static content) are served by whitenoise (`whitenoise.middleware.WhiteNoiseMiddleware`, `STORAGES['staticfiles']` in `config/settings.py`) directly from the Django process — no separate static host/CDN needed at this scale. `collectstatic` writes to `STATIC_ROOT` (`staticfiles/`, gitignored, rebuilt every deploy).

Environment variables actually set on the Render service (see `.env.example` for the full list/format): `SECRET_KEY` (a real random value generated with `uv run python -c "import secrets; print(secrets.token_urlsafe(50))"`, not the dev default), `DEBUG=False`, `DATABASE_URL` (Neon's connection string, see below), `CORS_ALLOWED_ORIGINS=https://kattrap.kpground.com,https://kattrap.onrender.com`. `ALLOWED_HOSTS` didn't need Render's own `*.onrender.com` hostname added by hand — `RENDER_EXTERNAL_HOSTNAME` is set automatically by Render on every deploy and gets appended in `settings.py`. `ENABLE_KATHRYN_QUICKLOGIN` was left at its default (`True`), same as dev, since Kathryn is still the only real user.

**Database**: Neon Postgres, not Render's own Postgres add-on — see `../kpground/CLAUDE.md`'s hosting table for why (Render's free Postgres auto-deletes after 30+14 days). Neon auto-created a project named `kat_trap` (org "Scott") with a `production` branch and default database `neondb`/role `neondb_owner` on signup — that default naming was kept as-is rather than renamed, since it already reads fine. `DATABASE_URL` uses Neon's **pooled** connection string (PgBouncer, `-pooler` in the hostname) rather than the direct one — reasonable for a small Django app with a handful of gunicorn workers, revisit only if a real pooling-related bug shows up (e.g. session-level Postgres features that don't survive PgBouncer's transaction-pooling mode).

**No custom domain** (`api.kpground.com`) — deliberately using the raw `onrender.com` URL instead, since a 3rd custom domain costs $0.25/month on Render's free workspace tier (2 are already used by `kpground.com` + `kattrap.kpground.com` — see `../kpground/CLAUDE.md`'s cost note). `kat_trap`'s `js/utils/api.js` points at the onrender.com URL directly; revisit both if that tradeoff changes.

## Known gaps (worth knowing before extending this)

- **No test suite.** Verification so far has been manual `curl` checks against a running dev server for every endpoint added, plus `manage.py check` after any model/view/url change.
- **`seed_store`'s perk catalog is still placeholder data** for exercising the purchase flow, not final game content — real item names/costs for Cat's and Mouse's perks still need designing. The dog's outfit cosmetics are real (see the command above), not placeholder.
- **`kat_trap` is fully wired up to this API** — wallet/HUD, the Bloomingtails (cosmetics) + Pawgreens (perks) store, purchase/sell/equip/unequip, and round submission all call real endpoints here. `kpground` (the landing page) still has no integration with this API at all — shared account/auth across the whole site is still just the plan, not built.

## When working in this repo

- Keep `accounts` (identity, shared across future games) and `kattrap` (this game's own data) separated the way they are now — a second game should get its own app alongside `kattrap`, not have its models merged into it.
- Any new tunable economy number belongs in `kattrap/economy.py` as a plain constant, not inline in a view/service or in a DB-editable settings model.
- Any new wallet-mutating endpoint should go through `services.py` with `transaction.atomic()` + `select_for_update()` on the wallet row(s) it touches, matching the existing purchase/claim/submit functions — don't mutate `CharacterWallet.coins`/`.xp`/`.level` directly from a view.
- Update `.env.example` alongside any new `config()`-read setting so local setup stays accurate.
