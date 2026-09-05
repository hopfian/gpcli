# Changelog

All notable changes to this project are documented here. The format is
based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and
this project adheres to [Semantic Versioning](https://semver.org/).

## [1.10.0] — 2026-09-06

### Added
- **Payment-method binding family** (decoded from the app's
  `payment_method_binding` feature):
  - `gpcli recharge methods` — bindable methods (`GET v2/payment-methods`:
    bkash, nagad, card);
  - `gpcli recharge bind <id>` — `POST payment-gateway/bind/{id}` with the
    app's `REMAINING-OPEN-INTERNET`/`wifi` headers, returning the provider's
    auth page (verified live: bKash's `directcharge.payment.bkash.com` and
    Nagad's in-app flow; completion redirects to `mygpapi/bind`);
  - `gpcli recharge unbind <id>` — form POST with the identifier token;
  - `gpcli recharge saved` — bound methods from `GET /balance` →
    `connected_payment_methods` (wallet, preferred flag, one-tap token).
- **Identifier auto-resolution** — `recharge pay` and `recharge unbind`
  resolve the bound method's token from balance when `--identifier` is
  omitted, making one-tap recharges a single command.
- `recharge gateway` reworked as the primary **single-use** flow — help,
  output (transaction id + campaign codes) and a "nothing is saved" hint.

### Changed
- Money endpoints now send the headers the app sends
  (`RechargeRepositoryImpl`): `X-Analytics-ID` (the `AnalyticsIdUtil`
  AES-CTR derivation of the auth msisdn — key material added to
  `crypto.py`) and `X-Service-Class-A` from balance.
- `purchase pack` (`recharge-and-activate`) `pack_data` now carries the
  numeric `service_class` from balance — the server rejects null with
  `service_class should be a numeric value.`
- README purchase section rewritten around the money-verified flows.

### Fixed
- Money commands (`pay`, `purchase pack`, `recharge gateway`) raised a
  confusing msisdn-format error when run logged out — now a clear
  `AuthRequiredError` ("log in or pass --msisdn").
- `POST /recharge` bodies hardcoded `type: PREPAID` /
  `connection_type: prepaid` — both now derive from the live balance, so
  postpaid accounts send the correct values.
- `direct_recharge.dueAmount` (and the other String-schema fields) arrive
  as ints from the server — coerced client-side instead of crashing the
  success rendering.
- `purchase pack --legacy` printed raw JSON in human mode — now renders a
  status/ticket panel and reserves JSON for `--json`.
- Deduplicated the `/v2/payment-methods` endpoint constant (single source
  in the AutoPay service, imported by the purchase service), hoisted the
  deferred `analytics_id`/`AutoPayService` imports to module level, and
  standardized every purchase command on the `ctx.client()` factory.

### Money-verified during development (2026-09-06)
- Single-use **Nagad** recharge end-to-end: gateway session → browser
  payment → `recharge-return?status=success` → +20 BDT balance.
- **One-tap instant purchase** from the bound Nagad wallet:
  `purchase pack 4234 --provider nagad` charged the wallet directly and
  returned `direct_recharge` info — no browser, no OTP, no gateway page.
- Bind → unbind → rebind cycle with real **bKash** (identifier tokens
  round-trip verbatim).
- Balance purchase of a 50 SMS pack (5.99 BDT) via `campaign-activate`.
- Known server behaviors documented: `500 "No number is bind with your
  account"` for gateway-path purchases without a bound method; `429 "Too
  many request, try after 5 minutes"` rate limiting on the money endpoints;
  `direct_recharge.dueAmount` arrives as an int despite the String schema
  (coerced client-side).

## [1.9.0] — 2026-08-31

### Added
- **Purchase & recharge family** — `gpcli purchase pack` (modern
  `recharge-and-activate` with `--legacy` `campaign-activate` mode),
  `gpcli recharge gateway|pay|offers|history|numbers`. Gateway body
  construction live-validated against production (real payment URLs);
  money paths are confirmation-gated.
- `gpcli auth import` — bring your own session (tooling/migration).
- `gpcli packs health` — dynamic Shukhee tab (`tabs_priority`).
- `gpcli packs --list-categories`.
- LICENSE (MIT), SECURITY.md (threat model, credential-storage guidance,
  vulnerability-reporting policy), CONTRIBUTING.md, this changelog.
- `py.typed` marker (PEP 561) — the package is fully typed.

### Changed
- **Renamed to gpcli** (previously `mygp-cli`): package `gpcli`, console
  command `gpcli`, PyPI name `gpcli`. The tool keeps `MyGP*` class names
  and all app-side identifiers (URLs, gateway keys) — they describe the
  target app. State written by `mygp-cli` builds migrates automatically.
- **Production refactor (no behavior change):** monolithic `models.py`
  (944 lines) and `render.py` split into domain packages with stable
  facade re-exports; `commands/comms.py` (five typer apps) and
  `commands/extras.py` (four) split one-app-per-module; `main.py` is now
  a pure composition root with a registry table.
- **SOLID wiring:** services are typed against the structural `ApiCaller`
  protocol; commands obtain clients exclusively via the `Context.client()`
  factory (no presentation-layer transport construction); wire-body
  builders consolidated in pure `bodies.py`; MSISDN utilities in
  `msisdn.py`.
- **PII purge:** all test identifiers are synthetic placeholders from
  `tests/constants.py`; no real subscriber data in the repo.
- Version single-sourced from `gpcli.__version__`; SPDX license
  expression in packaging metadata.

### Fixed
- `gpcli --json` placement documented correctly (root-level flag — before
  the subcommand).

## [1.8.0] — 2026-08-31

### Added
- Purchase subsystem wired end-to-end: `recharge-and-activate` body
  construction (`recharge_data` + `pack_data` with `forced:"1"` + `otp`),
  wallet payment (`payment-gateway/payment`), recharge offers, payment
  history, recently-recharged numbers.
- `X-Service-Class-A` header derivation from live balance.
- 12 new tests (128 total) covering body builders, gateway parsing and
  response semantics.

## [1.7.0] — 2026-08-30

### Added
- Comms family: SIM (ownership certificate, doc-type, biometric lists),
  FnF, MCA, Welcome Tunes, network complaints (netcare).
- Offers family: gifts, gift cards, GA counters, PAYG toggle (via
  campaign-activate), pack auto-renew.
- Partner tokens (Ibadah/Win/chatbot/DRM/Zee5) and streaming-content
  browse; support form + live-chat URL.
- Itemized postpaid bills (PDF download, Java-Calendar-faithful cycle
  math), AutoPay family, emergency balance, login-streak rewards,
  roaming family (status/packs/history/portal URLs).
- 20 command groups, 116 tests.

## [1.0.0] – [1.6.0] — 2026-08-2x

Initial development: the three auth flows (OTP/silent SIM/guest), the
full OkHttp interceptor emulation with token refresh semantics, account
and balance, content (cards/districts/weather/news), flexiplan catalog +
price quoter, VAS, the pack catalog with Explore-tab categories, balance
transfer with PIN management, and usage history. Detailed history was
not recorded before 1.7.0.

[1.10.0]: https://github.com/hopfian/gpcli/commits/v1.10.0
[1.9.0]: https://github.com/hopfian/gpcli/commits/v1.9.0
[1.8.0]: https://github.com/hopfian/gpcli/commits/main
[1.7.0]: https://github.com/hopfian/gpcli/commits/main
