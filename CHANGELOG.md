# Changelog

All notable changes to this project are documented here. The format is
based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and
this project adheres to [Semantic Versioning](https://semver.org/).

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

[1.9.0]: https://github.com/hopfian/gpcli/commits/v1.9.0
[1.8.0]: https://github.com/hopfian/gpcli/commits/main
[1.7.0]: https://github.com/hopfian/gpcli/commits/main
