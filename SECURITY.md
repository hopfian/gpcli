# Security Policy

## Supported versions

| Version | Supported |
|---|---|
| 1.9.x | yes — latest minor line |
| < 1.9 | no |

## Reporting a vulnerability

If you find a security issue **in this codebase**, please report it
privately rather than in a public issue:

* **GitHub** — Security tab → *"Report a vulnerability"* (private advisory
  reporting). This is the preferred channel and reaches the maintainer
  immediately.
* Include: the CLI version (`gpcli --version` / `pip show gpcli`), the
  command or module involved, a minimal reproduction, and the impact. Do
  **not** paste live tokens, `state.json` contents, or your MSISDN into
  the report.
* Expect an acknowledgement within ~72h and a fix in the next patch
  release where practical.

### Out of scope

* **Grameenphone infrastructure and the MyGP app.** Vulnerabilities in the
  operator's API, app, or portal belong with the operator's own security
  team — this project only replicates observed client behavior for
  interoperability research.
* The reverse-engineered constants documented in the source (static AES
  key/IV, guest OAuth client credentials). These are extracted from the
  publicly distributed APK and are identical on every install — they are
  app-wide design properties, not disclosures.
* Attacks requiring physical access to an unlocked machine.

## Threat model & data handling

### Credential storage — `state.json`

The CLI stores **live session tokens in plaintext** at
`%LOCALAPPDATA%\gpcli\state.json` (platformdirs): subscriber
access/refresh bearer tokens, the guest OAuth credential pair, and the
emulated device identity. There is no OS keychain/DPAPI integration — by
design, to keep the tool dependency-light and inspectable.

Consequences and guidance:

* Treat the file like a password. Anything running as your user can read it.
* Tokens are server-scoped (~24h validity) but the refresh token extends
  that — if the file leaks, run `gpcli auth logout --all` from a machine
  that still has a valid session, then delete the file everywhere it was
  copied.
* `gpcli config set device-id <new-16-hex>` rotates the emulated Android ID
  (server-side device fingerprint) without wiping your session.
* Do not commit, sync, or share this file. It is git-ignored by default;
  keep it that way.

### Network behavior

* The client talks **only** to `*.grameenphone.com` endpoints
  (`mygpapi` and `apigw` gateways). No telemetry, analytics, or
  third-party callbacks originate from this tool.
* **DNS fail-open:** when the local resolver fails, the host is resolved
  via DNS-over-HTTPS through direct `8.8.8.8` (Google) / `1.1.1.1`
  (Cloudflare) with a Host-header override, then cached for the process
  lifetime. This exists to survive ISP resolver flakiness — be aware it
  discloses the queried hostnames to those resolvers in that failure
  case. Remove `install_dns_fallback()` from the root callback in
  `main.py` if this is unacceptable for your environment.

### Payment flows

`gpcli purchase pack`, `gpcli recharge pay`, `gpcli eb avail` and
`gpcli transfer send` move real money. All are confirmation-gated and
print exactly what will be sent before you confirm, but:

* Payment URLs surfaced by `recharge gateway` come from the production
  API. Verify the domain (`payments.grameenphone.com` observed live) and
  the amount in the web payment page before authenticating to your MFS
  wallet. The CLI never handles wallet credentials itself.
* `--yes` skips the confirmation prompt — script with care.

### The `raw` passthrough

`gpcli raw call` fires arbitrary requests with your full session
(including auth headers and token refresh). It exists for research over
the ~200 mapped endpoints; it can also trigger irreversible actions on
the backend. Understand a request before firing it.

### Cryptographic replication

`crypto.py` replicates the app's AES-256-CTR usage with a static
hardcoded key — that is the app's design, replicated for
interoperability. It provides **no confidentiality** against anyone who
has the APK; do not build on it as if it were a secret.

### Distribution hygiene

* Python build artifacts (sdist/wheel) exclude caches automatically.
* **Folder copies do not**: `__pycache__` bytecode and tool caches embed
  the compiling machine's absolute paths (including the OS username).
  Purge `__pycache__/`, `.ruff_cache/`, `.pytest_cache/` before zipping
  or sharing a working tree.

## Hardening recommendations

* Keep the project (or at least `state.json`) on an encrypted volume if
  your threat model includes device theft.
* Log out (`gpcli auth logout --all`) before handing over a machine
  profile or user account to anyone else.
* Pin dependency versions (`pip freeze`) in controlled environments; the
  `pyproject.toml` ranges are intentionally permissive for research use.
* If you script the CLI, prefer `--json` output over parsing rendered
  tables — parsing failures that mask a money-moving error are the worst
  failure mode here.
