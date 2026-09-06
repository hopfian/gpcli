# gpcli

A fully reverse-engineered command-line client for **MyGP** — Grameenphone's
subscriber super-app (`com.portonics.mygp` 5.31.0, versionCode 530). Built
from static analysis of the decompiled APK (jadx + apktool smali), with
every flow live-validated against the production API and the wire formats
frozen under a 147-test suite.

```
$ gpcli me
+------------------------------ MyGP Subscriber ------------------------------+
|         name  GP Subscriber                                                 |
|       msisdn  8801700000000                                                 |
|        email  …                                                             |
|   member since  2021-01-13 19:57:09                                         |
+-----------------------------------------------------------------------------+
```

| | |
|---|---|
| Version | 1.10.0 (src-layout, Python ≥ 3.10) |
| Command groups | 24 subcommand groups + 8 root commands |
| Test suite | 147 tests, ruff-clean |
| Coverage | auth (3 flows) · account · catalog/flexiplan · purchase/recharge · transfer · bills · autopay · rewards · roaming · SIM/FnF/MCA/WT/netcare · partners · raw |

> **Status note:** every read path is live-verified, and the money paths are
> verified with **real transactions** — single-use recharge via Nagad
> (browser payment), bind/unbind/rebind cycles, one-tap purchases from a
> bound wallet, and balance purchases (see the Purchase & recharge section
> for the receipts). All money commands are confirmation-gated; the only
> untested corner (plain wallet recharge without a pack) is tracked in the
> [Roadmap](#roadmap).

## Contents

- [Quick start](#quick-start)
- [Command reference](#command-reference)
- [How it works](#how-it-works)
- [Domain notes](#domain-notes)
- [Configuration & state](#configuration--state)
- [Errors & exit codes](#errors--exit-codes)
- [Architecture](#architecture)
- [Testing & development](#testing--development)
- [Security research notes](#security-research-notes)
- [License](#license)
- [Roadmap](#roadmap)

## Quick start

```powershell
git clone <repository-url> gpcli && cd gpcli   # repo root == this directory
pip install -e .
gpcli login 01700000000        # OTP flow: sends SMS, prompts for the code
gpcli status                   # session, device identity, token expiry
```

A day with the CLI:

```powershell
gpcli balance                  # main balance, packages, emergency-balance state
gpcli packs internet --search booster
gpcli purchase pack 4575       # confirm-prompted; prints the payment URL
gpcli history --days 7         # CDR feed: calls, data, SMS, recharges
gpcli streak status            # daily-login streak + claimable rewards
```

The global `--json` flag switches any command to machine-readable output.
It belongs to the root command, so it goes **before** the subcommand:
`gpcli --json balance` (not `gpcli balance --json`).

## Command reference

### Session & identity

| Command | What it does |
|---|---|
| `gpcli login <msisdn>` | Interactive OTP login (send code → prompt → verify → save) |
| `gpcli guest` | Establish/refresh an anonymous guest session (no SIM needed) |
| `gpcli status` | Session, device identity, token expiry — no network |
| `gpcli auth send-otp <msisdn>` | Request an OTP SMS (stages the number) |
| `gpcli auth verify-otp <code> [--msisdn]` | Exchange the SMS code for tokens |
| `gpcli auth silent` | Silent SIM login (GP mobile-data IPs only, by design) |
| `gpcli auth refresh [--force]` | Refresh the access token (`--force` bypasses the 600s rate-guard) |
| `gpcli auth import --access-token T --refresh-token R --id N [--msisdn M] [--expire-at E]` | Import an existing session (tooling/migration) |
| `gpcli auth logout [--all]` | Invalidate server-side (`--all` = every device) and clear state |

### Account & content

| Command | What it does |
|---|---|
| `gpcli me` / `gpcli account me` | Subscriber identity and profile |
| `gpcli balance` / `gpcli account balance` | Main + package balances, EB block |
| `gpcli account usage` | Usage snapshot (`GET /current-usage`, raw) |
| `gpcli account sim` | SIM status — foreigner flag, validity |
| `gpcli content cards [--category C] [--offset N] [--limit N]` | Homepage card engine (guest, auto-provisioned) |
| `gpcli content districts` | District list (guest) |
| `gpcli content weather [--lat 23.8103] [--lon 90.4125]` | Weather lookup (guest; params partially verified) |
| `gpcli news` | Subscriber news feed |

### Catalog: packs, flexiplan, VAS

| Command | What it does |
|---|---|
| `gpcli packs [CATEGORY] [--search S] [--limit N] [--usd] [--all-groups] [--list-categories]` | Master pack catalog by Explore-tab category (default `all`; `--limit 0` = everything) |
| `gpcli flexiplan show` | The build-your-own-bundle catalog (options, VAT, MCA pricing) |
| `gpcli flexiplan quote --days 30 --voice 100 --data 30720 [--4g MB] [--bioscope MB] [--sms N] [--mca]` | Price a bundle combination (data in MB: 30720 = 30 GB) |
| `gpcli vas categories` / `services <id>` / `subscribed` / `history` | Browse VAS |
| `gpcli vas activate <service_id> [charge_code] [partner]` / `deactivate …` / `stop-all [--yes]` | Manage VAS subscriptions (set-status) |

Pack categories: `internet · bundles · minutes · sms · cashback · gifts ·
rate-cutter · roaming · entertainment · subscriptions · health · my-offers ·
all` — `gpcli packs --list-categories` prints the live table with the
selection predicate for each.

### Money: purchase, recharge, transfer, autopay, emergency balance

| Command | What it does |
|---|---|
| `gpcli purchase pack <id-or-keyword> [--amount N] [--otp C] [--provider P --identifier I] [--msisdn M] [--legacy] [--yes]` | Buy a pack — modern `recharge-and-activate`, or `--legacy` = `campaign-activate` (free/PAYG-style) |
| `gpcli recharge gateway <amount> [--msisdn M] [--channel C] [--open]` | Get payment/bKash/Rocket WebView URLs for a recharge |
| `gpcli recharge pay <amount> --provider P --identifier I [--msisdn M] [--yes]` | Direct wallet payment (bound payment method) |
| `gpcli recharge offers` / `history` / `numbers` | Recharge offers, bill-payment history, recently recharged numbers |
| `gpcli transfer send <payee> <amount> [--pin P] [--yes]` | Balance transfer (hidden PIN prompt) |
| `gpcli transfer register` / `change-pin` / `reset-pin` | Enroll, rotate, or OTP-reset the transfer PIN |
| `gpcli autopay list` / `products` / `methods` / `recent` | Subscriptions, server config, saved payment methods, recent numbers |
| `gpcli autopay validate <msisdn>` | GP/skitto + connection type + EB-due check |
| `gpcli autopay setup <msisdn> <amount> [--frequency N] [--start-from D] [--provider P --identifier I] [--yes]` | Create a scheduled / low-balance auto-recharge |
| `gpcli autopay update <id> […]` / `cancel <id>` | Modify or remove a subscription |
| `gpcli eb status` | Eligible loan amount, active loan, eligibility rules |
| `gpcli eb avail [--yes]` | Request the loan (POST with an **empty** body) |

### History, bills, rewards

| Command | What it does |
|---|---|
| `gpcli history [--days 7 \| --start --end] [--category slug] [--limit 25]` | CDR feed: calls, data, SMS, recharges, packs, EB, transfers, call drops |
| `gpcli bill cycles` | 6 selectable postpaid cycles (Java-Calendar-faithful math) |
| `gpcli bill itemized [--cycle 1 \| --month yyyy-MM-dd] [--type local\|roaming] [--out FILE]` | Itemized-bill PDF (validates the `%PDF` magic the app never checks) |
| `gpcli streak status` | Daily-login streak, milestones joined with reward config |
| `gpcli streak claim [--milestone-id N] [--yes]` | Claim a reward (auto-picks the first claimable) |
| `gpcli streak points` | GP point balance + loyalty enrollment |

### Comms: SIM, FnF, MCA, Welcome Tune, netcare

| Command | What it does |
|---|---|
| `gpcli sim certificate [--out FILE]` | SIM ownership certificate (HTML) |
| `gpcli sim doc-type` | ID document type on file (NID/passport) |
| `gpcli sim list <last-4-of-NID>` | Biometric SIM lists: active / bondho / other-operator |
| `gpcli fnf list` / `add <msisdn> [--super]` / `remove <msisdn> [--super]` | Friends & Family with quota panel |
| `gpcli mca status` / `on [--yes]` / `off [--yes]` | Missed Call Alert |
| `gpcli wt status` / `list` / `search <text>` / `activate <code> [--yes]` / `deactivate` | Welcome Tunes |
| `gpcli netcare list` / `detail <id>` / `questionnaires` / `submit <answers-json> [--meta JSON]` | Network complaints |

### Offers, partners, support, roaming

| Command | What it does |
|---|---|
| `gpcli offers gifts` / `gift-cards` / `ga` | Received gifts, gift-card themes, GA (new-SIM) counters |
| `gpcli offers payg-status` / `payg-toggle <on\|off> [--yes]` | Pay-as-you-go internet (toggles a catalog pack) |
| `gpcli autorenew status` / `set-renew <shortcode> <on\|off>` | Pack auto-renew (POST `internet-renew`) |
| `gpcli partners deen` / `win` / `chatbot` | Partner JWTs (Ibadah, WIN, live-chat) |
| `gpcli partners drm <partner> <pid>` | Widevine DRM token (lionsgate, chorki, zee5, hoichoi, …) |
| `gpcli partners zee5` / `search <partner> [--genre]` / `contents <partner>` | Streaming catalogs + content browse |
| `gpcli support form --name --email --issue-type --message` / `chat [--open]` | Email support form, live-chat URL |
| `gpcli roaming status` / `packs [--usd]` / `history [--days N]` / `manage` / `rates` / `tips` | Roaming family — the last three are GP web portals (`--open` to launch) |

### Utilities

| Command | What it does |
|---|---|
| `gpcli raw call <METHOD> <path> [--base mygpapi\|apigw] [--body JSON] [--guest] [--no-auth]` | Authenticated passthrough for any of the ~200 mapped endpoints; `METHOD` ∈ GET/POST/PUT/PATCH/DELETE, path may be absolute |
| `gpcli config show` / `set <key> <value>` | Device identity (`device-id`, `device-model`, `device-name`) and `language` |

## How it works

### Two gateways

| Gateway | Role | Auth |
|---|---|---|
| `mygp.grameenphone.com/mygpapi` | nginx legacy — most endpoints | subscriber `Authorization: Bearer …` + `?id=<auth.id>` |
| `apigw.grameenphone.com` | Apigee — cards/districts/weather, OAuth | guest bearer (client-credentials) + literal `userId` header |

### The interceptor stack (replicated exactly)

* **UserAgentInterceptor** — every request carries
  `User-Agent: Android/34 MyGP/530 (en)`, `Accept-Language`, `Vary`,
  `APP-MSISDN`, `APP-MSISDN-OLD`, `X-REFERENCE-ID` (the persistent device
  id), the `ng` header, and `?lang=&ng=` query params.
* **AuthInterceptor** — subscriber requests to the legacy gateway carry the
  bearer + `?id=<auth.id>` (skipped for `v2/sbcontents/*`). **403** → one
  silent refresh + retry; **401 / 911 / 410** → session invalidated and
  cleared.
* **Refresh semantics** — tokens are never refreshed within 600s of issuance
  (the app's rate-guard) and proactively refreshed within 600s of expiry.
  Endpoint: `v2/oauth/connectid/refresh-token/android`
  (or `v2/refresh-token-all/android` for non-GP users).

### The three login flows (reverse-engineered)

1. **OTP** — `GET /v2/otp-login?msisdn=8801…` triggers an SMS;
   `POST /v2/otp-login` with `{msisdn, otp, app_version, device_id,
   device_model, device_name}` returns the full token set. MSISDNs must be
   exactly 13 characters in `880`-format (the CLI normalizes this for you).
2. **Silent SIM** — `GET /code` issues a challenge; the client encrypts its
   device id with AES-256-CTR under a key derived from
   `"mygp" + ts[idx:idx+2] + "grameenp" + code[idx:idx+2]` (16 bytes of key
   material, used as IV, doubled as the key) and answers via
   `POST /v2/code`. Gated to Grameenphone mobile-data IPs.
3. **Guest** — `POST /guest-login {deviceId, aaId}` (any 16-hex + any UUID)
   issues OAuth client credentials; `POST apigw/oauth/v2/token` (form field
   `userId`, **not** `user_id`) mints an hourly anonymous bearer. Guest
   sessions are re-minted transparently when expired.

The app's hardcoded AES key/IV (`EncryptionUtil`) and the silent-login key
derivation are replicated in `gpcli/crypto.py` — Java's
`AES/CTR/NoPadding` with a 16-byte `IvParameterSpec` is byte-for-byte
`cryptography`'s CTR mode with a 16-byte nonce.

### Quirks documented in code

* The guest `userId` header is literally named `userId`
  (`SMTInboxConstants.API_KEY_USER_ID == "userId"`).
* Logical failures arrive as `{"error": {...}}` inside HTTP 200s —
  surfaced as typed `ApiError`s.
* `current-usage` returns `402 failed` server-side for some accounts;
  the CLI reports it cleanly.
* `apigw.grameenphone.com` is an Apigee gateway that leaks internal policy
  names (`JS-VerifySCResponseParams`) on bad input.
* Backend scalar typing is sloppy: prices arrive as `150` or `"150"`,
  validity objects as `null` — the pydantic models coerce before
  validation (faithful to the app's Gson adapters).

### DNS resilience

`gpcli/dns.py` installs a fail-open `getaddrinfo` patch: when the local
resolver fails, the host is resolved over DNS-over-HTTPS (via direct
`8.8.8.8` / `1.1.1.1` — no DNS needed to reach the resolvers themselves),
cached, and the request retried. A recursion guard keeps the DoH lookup
itself from looping back through the patch.

## Domain notes

### Pack catalog & categories

`gpcli packs` maps the app's Explore tabs to catalog predicates over
`GET v3/catalogs` (the master pack feed — 351 packs live):

| category | selects |
|---|---|
| `internet` / `bundles` / `minutes` / `sms` / `subscriptions` | pack `type` |
| `cashback` | `recharge_offer` packs + cashback text from `additional_data` |
| `gifts` | `giftable_offer` / `gift_only_offer` / `recharge_giftable_offer` attributes |
| `rate-cutter` | `rate_cutter_offer` / `free_rate_cutter_offer` attributes |
| `roaming` | `roaming_offer` attribute; `--usd` selects `Buy_with_USD`, default Taka (`roaming_mobile_balance`) |
| `entertainment` | `entertainment_offer` attribute or streaming filters (hoichoi, chorki, bioscope, sonyliv, …) |
| `health` | dynamic Explore tab — packs under `tabs_priority['health']` (Shukhee bundles) |
| `my-offers` | personalized CMP campaigns (`GET v2/cmp-offers`: myoffers, rc, mysterybox, … via `--all-groups`) |

### Flexiplan price matrix

The bundle catalog is a dict of encoded keys → encoded prices
(`FlexiplanHelperKt`, replicated in `services/catalog.py`):

* **key** `L{days}_V{voice}_D{dataMB}M_F{4gMB}M_B{bioscopeMB}M_S{sms}`
  — volumes as `0M`, `{gb}G` or `{mb}M`; app keywords prefix `FLXPLN_V2_`
  and express data in GB.
* **value** `B{base}_M{market}_C{commission}_T{baseVat}_P{prepaidTotal}_S{postpaid}_D{discount}`
  — `P` is the final prepaid price incl. VAT (+MCA); discount is ceil'ed
  exactly like the app.

### Balance transfer

```
gpcli transfer send 01712345678 50          # hidden PIN prompt + confirmation
gpcli transfer send 01712345678 50 --pin 1234 --yes
gpcli transfer register                      # enroll (already-enrolled → 401 envelope + SMS)
gpcli transfer change-pin                    # old → new (hidden prompts)
gpcli transfer reset-pin                     # initiate → OTP (SMS) → verify → set new PIN
```

The API only returns a bare `{status, result, message}` envelope; GP delivers
the **detailed failure reason by SMS** with a transaction reference number
(e.g. `4596: You do not have sufficient credit`, `You have already activated
P2P_SERVICE`). The CLI hints at this when a transfer fails. Amounts must be
10–100 BDT.

### Usage history & itemized bills

* Wire dates are `yyyy-MM-dd`; the default window is the first
  `_meta.filters` entry (7 days ending today, app logic); item-level
  `usage_date` is `dd-MM-yyyy`.
* Itemized bills are postpaid-only (prepaid gets a clean 404); the CLI
  validates the `%PDF` magic the app never checks.

### Emergency balance & streak rewards

* The app's EB eligibility rule is replicated: prepaid, main balance below
  `eb_eligibility_balance` (settings, default 18 BDT) and no active loan.
  Avail sends a POST with an **empty** JSON body.
* Streak milestones split across two arrays on the wire (runtime state
  `milestone[]` + reward config `settings.milestones[]`) — the CLI joins
  them by id, exactly like the app's adapter (7d = 100 pts … 56d = 800 pts).

### Roaming

**There is no native roaming-activation API in MyGP 5.31.0** — the app itself
just WebViews `roaming.grameenphone.com` portals (decoded from its search
config). The CLI prints the same URLs (or opens them with `--open`); the
`is_roaming` status and roaming-flagged usage history are real API calls
(`usage_flag_type == "roaming"`).

### Purchase & recharge

```
gpcli recharge gateway 20 [--open]        # single-use: one-time payment session
gpcli recharge saved                       # bound methods + one-tap identifiers
gpcli recharge bind nagad [--open]         # bind once (provider auth page)
gpcli recharge pay 20 --provider nagad     # instant one-tap from bound wallet
gpcli recharge unbind bkash                # remove a binding
gpcli purchase pack 4234                   # buy from main balance (--legacy path)
```

**Verified with real money** (2026-09-06):

* **Single-use recharge** — `POST /recharge` returns a one-time payment
  session (`payment_url` + `transaction_id` + campaign codes). Paying it
  with **Nagad** in a browser completed end-to-end: the provider redirects
  back to `mygpapi/recharge-return?...status=success&service_provider=NAGAD`
  and the balance lands instantly (the MyGP-40% campaign arrives later as
  cashback). No method is saved.
* **Binding** — `POST payment-gateway/bind/{id}` (headers
  `REMAINING-OPEN-INTERNET`, `wifi`) returns the provider's auth page
  (Nagad's in-app, bKash's `directcharge.payment.bkash.com`); completion
  redirects to `mygpapi/bind?...identifier=<token>&status=success`. Bound
  methods live in `GET /balance` → `connected_payment_methods[]` with
  opaque base64 `identifier` tokens that round-trip verbatim through
  bind → unbind → rebind.
* **Buy from main balance** — `purchase pack <id> --legacy`
  (`POST /campaign-activate/`) is async `{status: pending, ticketid}`,
  provisioned within seconds (5.99 BDT test: 183.38 → 177.39, 28 → 78 SMS).
* `purchase pack <id>` without `--provider/--identifier` is the
  **gateway-recharge** path — the server rejects it with
  `500 "No number is bind with your account"` unless a payment method is
  bound to the account.

**Headers the money endpoints need** (decoded from `RechargeRepositoryImpl`):
`X-Analytics-ID` = hex(AES-CTR(auth msisdn, key/iv from `AnalyticsIdUtil`
— see `crypto.py`)) and `X-Service-Class-A` from balance. The
recharge-and-activate `pack_data` also requires a numeric
`service_class` (from balance) — the server rejects null with
`service_class should be a numeric value.` Money endpoints rate-limit:
**429 "Too many request, try after 5 minutes"** on rapid attempts.

**Flow semantics** (from the app): `POST /recharge` returns per-MFS payment
URLs (the app loads them in a payment WebView — the CLI prints them, `--open`
to launch). `POST /recharge-and-activate` wraps a `MakePaymentBody`
(`recharge_data`) + the `Api.l()` pack body (`pack_data`, plus `forced:"1"`)
and returns `data.status`: `"action_required"` → `data.url.payment_url`
(complete payment there), `"success"/"pending"` → done. The wallet path
(`payment-gateway/payment`) completes without any URL — success only when
`status == "success"`. All purchase commands are confirmation-gated.

**Verified with real money** (2026-09-06, 5.99 BDT):

* `purchase pack <id> --legacy` (`POST /campaign-activate/`) is the
  **buy-from-main-balance** path — async `{status: "pending", ticketid}`
  response, provisioned within seconds (balance 183.38 → 177.39 BDT,
  28 → 78 SMS). Use this when you already have balance.
* `purchase pack <id>` without `--provider/--identifier` is the
  **gateway-recharge** path — the server rejects it with
  `500 "No number is bind with your account"` unless a payment method is
  bound to the account. That's the flow the app's payment WebView serves;
  run it with wallet params or complete the `action_required` URL.

Endpoints behind them:

* `POST /recharge` — gateway selection (body = `Recharge` object) —
  live-validated against the production server
* `POST /payment-gateway/payment` — wallet purchase (`MakePaymentBody`) —
  success only when `status == "success"` (no URL involved)
* `POST /recharge-and-activate` — `recharge_data` + `pack_data`
  (Api.l body + `forced:"1"` + optional `otp`)
* `POST /v1/marketplace/cart/purchase` — add-on carts (documented, not
  surfaced — the CLI doesn't compose add-on carts)
* Headers: `X-Service-Class-A` (from balance), `X-Service-Class-B` (B-party)

## Configuration & state

* `gpcli config show` / `set <key> <value>` — keys: `language`,
  `device-model`, `device-name`, `device-id` (the emulated Android ID sent
  as `X-REFERENCE-ID`; regenerate to appear as a new device).
* State lives in `%LOCALAPPDATA%\gpcli\state.json` (platformdirs):
  device identity, subscriber tokens, guest session, staged OTP msisdn.
  Delete it to reset. Treat it as a credential store. Sessions written by
  pre-rename `mygp-cli` builds are migrated here automatically on first
  run.
* `gpcli auth import` moves a session between machines or from other
  tooling: `--access-token`, `--refresh-token`, `--id` are required;
  `--msisdn` and `--expire-at` (unix seconds) are advisory.

## Errors & exit codes

All failures derive from `MyGPError` and exit with code 1 (confirmation
aborts included):

| Error | Meaning |
|---|---|
| `AuthRequiredError` | no subscriber session — `gpcli login <msisdn>` first |
| `AuthExpiredError` | server rejected the session (401/911/410) — cleared, re-login |
| `ApiError` | ErrorV2 envelope `[code] message (description)` |
| `GuestFlowError` | guest login / token minting failed |
| `SilentLoginUnavailable` | `/code` is IP-gated to GP mobile data |
| `MsisdnFormatError` | number not normalizable to 13-char `880`-format |

## Architecture

Production-grade layout — strict presentation/business decoupling:

```
src/gpcli/
├── main.py            composition root: registry table + error boundary only
├── client.py          OkHttp interceptor emulation (ApiCaller protocol + MyGPClient)
├── bodies.py          pure wire-format builders (Api.l / MakePaymentBody)
├── msisdn.py          pure MSISDN normalization utilities
├── constants.py       endpoints, gateways, emulated app identity
├── crypto.py          EncryptionUtil replication (AES-256-CTR, silent login)
├── dns.py             fail-open DoH getaddrinfo patch
├── errors.py          error taxonomy
├── state.py           persistent device/session state
├── models/            pydantic wire models, one domain per module, facade-reexported
├── render/            Rich presentation, one domain per module, facade-reexported
├── services/          business logic, one concern per module (ApiCaller-typed)
└── commands/          typer apps, one group per module (ctx.client() factory)
```

Layering rules:

* **commands/** (and only it) talks to Typer/Rich. It builds services,
  renders results, and owns the `--json` switch. It never imports `httpx`
  or constructs a client — `Context.client()` is the single sanctioned
  factory (Dependency Inversion).
* **services/** hold the endpoint knowledge and wire-format semantics,
  typed against the structural `ApiCaller` protocol — no typer/rich imports.
* **bodies.py / msisdn.py** are pure functions (no I/O, trivially testable)
  so the exact wire literals live in one auditable place.
* **models/** + **render/** + **services/** are facade packages — the import
  surface (`from gpcli.models import Auth`) stays stable while internals
  split freely (Open/Closed).
* **client.py** is the only module that knows about HTTP. Its interceptor
  semantics are the compatibility contract — the test suite freezes them.

Adding a command group = three touches: `commands/<name>.py` (one typer app),
a service module if the logic is non-trivial, one line in `main.py`'s
`GROUPS` registry.

## Testing & development

```
python -m pytest tests -q   # 147 tests, hermetic (MockTransport, one-shot routes)
python -m ruff check src tests
pip install -e .
```

Tests exercise the real wire contracts — URL shapes, header injection,
body literals, refresh sequencing — against a scripted `httpx.MockTransport`
(one-shot routes so retry paths observe fresh responses). Identifiers are
synthetic: `tests/constants.py` holds the placeholder msisdn/auth-id set;
real subscriber data is banned from the repo.

Contributions follow [CONTRIBUTING.md](CONTRIBUTING.md) — it covers the
layering rules, the three-touch recipe for adding a command group, and the
PR checklist. Release history lives in [CHANGELOG.md](CHANGELOG.md).

## Security research notes

All reverse-engineering findings — endpoint inventory, wire formats, crypto,
IP-gating, interceptor semantics — live in the source docstrings, the
domain notes above, and `SECURITY.md`. Operational security of the tool
itself (credential storage, DNS fail-open behavior, payment-flow cautions,
vulnerability reporting) is covered in [SECURITY.md](SECURITY.md).

**This is unofficial, third-party software.** It is not affiliated with or
endorsed by Grameenphone. Use it only with your own GP number, on networks
you're authorized to use it from, and in accordance with the operator's
terms. The client holds live session tokens — protect `state.json` like a
password.

## License

Released under the [MIT License](LICENSE) — see the file for the full text.

Two scope notes worth being explicit about:

* The license covers **this client's code only** — the reverse-engineering
  effort, the interceptor replication, the wire-format models. It does not
  grant any rights to Grameenphone's app, API, trademarks, or service.
* Using this software against the production API remains your
  responsibility: the MIT license's "AS IS" clause means no warranty, and
  the operator's terms of service apply independently of it.

## Roadmap

Shipped since the first release: flexiplan show/quote, VAS management,
itemized bills, payment history + saved payment methods, FnF/Welcome-Tune
management, gamification, purchase & recharge, the v1.9.0 production
refactor (PII purge, SOLID architecture), and the v1.10.0 payment-method
family — all money paths verified with real transactions (single-use
Nagad recharge, bind/unbind/rebind, one-tap bound-wallet purchase,
balance purchase). Still open:

- [ ] Plain wallet recharge (`recharge pay` without a pack) — the
  `payment-gateway/payment` endpoint returned `500` in manual testing; it
  may be reserved for server-driven low-balance flows. The pack-purchase
  path with a bound wallet is the verified alternative.
- [ ] Flexiplan purchase (`v2/flexiplan/purchase`) — legacy endpoint with no
  in-app callers (dead code); wire only if it proves functional
- [ ] Marketplace add-on cart purchase (`v1/marketplace/cart/purchase`)
- [ ] Interactive TUI over the same service layer
