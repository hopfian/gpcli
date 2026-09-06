# Bug Report for `gpcli` (`src/` and `src/gpcli/`)

This report documents all bugs, runtime exceptions, type errors, and API contract mismatches identified through static analysis, type checking (`mypy`), and code inspection within `src/` and `src/gpcli/`.

---

## Summary of Findings

| # | Severity | Category | Affected File(s) | Description |
|---|---|---|---|---|
| 1 | **Critical** | Runtime Crash / AttributeError | [`src/gpcli/render/account.py`](file:///c:/Users/Inan/Documents/Project/Triage/mygp/app/src/gpcli/render/account.py#L68) | `Profile.rfu_1` does not exist on model; crashes `gpcli me` / `gpcli account me` / `gpcli login` |
| 2 | **High** | Runtime Crash / TypeError | [`src/gpcli/models/catalog.py`](file:///c:/Users/Inan/Documents/Project/Triage/mygp/app/src/gpcli/models/catalog.py#L179), [`src/gpcli/render/catalog.py`](file:///c:/Users/Inan/Documents/Project/Triage/mygp/app/src/gpcli/render/catalog.py#L158) | `PackItem.validity_summary()` returns `None`, causing `TypeError: 'NoneType' object is not subscriptable` in `render_packs` |
| 3 | **High** | Scoping / Type Shadowing | [`src/gpcli/services/autopay.py`](file:///c:/Users/Inan/Documents/Project/Triage/mygp/app/src/gpcli/services/autopay.py#L60), [`src/gpcli/services/welcome_tune.py`](file:///c:/Users/Inan/Documents/Project/Triage/mygp/app/src/gpcli/services/welcome_tune.py#L32) | Defining method `list()` shadows Python's built-in `list` type in class scope, breaking type annotations and runtime type introspection |
| 4 | **High** | Logical Bug / Missing Join | [`src/gpcli/commands/gamification.py`](file:///c:/Users/Inan/Documents/Project/Triage/mygp/app/src/gpcli/commands/gamification.py#L91) | `gpcli streak claim` checks `milestone_reward` on `StreakMilestone` where it is `None` (reward is in `settings.milestones`), prompting to claim `0 GP points` |
| 5 | **High** | Runtime Crash / TypeError & ValueError | [`src/gpcli/services/emergency.py`](file:///c:/Users/Inan/Documents/Project/Triage/mygp/app/src/gpcli/services/emergency.py#L57), [`src/gpcli/commands/emergency.py`](file:///c:/Users/Inan/Documents/Project/Triage/mygp/app/src/gpcli/commands/emergency.py#L42) | Raw JSON scalar types (string numbers) cause unhandled `TypeError` during `<` and `>` comparisons, and `ValueError` on `:g` formatting |
| 6 | **Medium** | API Contract Mismatch | [`src/gpcli/constants.py`](file:///c:/Users/Inan/Documents/Project/Triage/mygp/app/src/gpcli/constants.py#L52), [`src/gpcli/services/partners.py`](file:///c:/Users/Inan/Documents/Project/Triage/mygp/app/src/gpcli/services/partners.py#L28) | `ID_PARAM_SKIP_MARKERS` specifies `v2/sbcontents/search` while endpoints use `v1/sbcontents/search`, erroneously leaking `?id=` query param into streaming partner calls |
| 7 | **Medium** | Logical Bug / Expiry Check | [`src/gpcli/models/auth.py`](file:///c:/Users/Inan/Documents/Project/Triage/mygp/app/src/gpcli/models/auth.py#L79) | `GuestSession.token_expired()` returns `0` (int) instead of `bool` when `expires_at == 0`, preventing guest token re-minting |
| 8 | **Medium** | Type Contract / Dependency Inversion Violation | [`src/gpcli/services/content.py`](file:///c:/Users/Inan/Documents/Project/Triage/mygp/app/src/gpcli/services/content.py#L26) | `ContentService` accepts `ApiCaller` but initializes `AuthService(client)` which expects concrete `MyGPClient` (for `raw_post`) |
| 9 | **Medium** | Unhandled Exceptions / Traceback Leakage | [`src/gpcli/services/offers.py`](file:///c:/Users/Inan/Documents/Project/Triage/mygp/app/src/gpcli/services/offers.py#L83), [`src/gpcli/services/catalog.py`](file:///c:/Users/Inan/Documents/Project/Triage/mygp/app/src/gpcli/services/catalog.py#L152) | Raising standard `RuntimeError` and `KeyError` instead of `MyGPError` bypasses `main.py` error boundary and dumps raw tracebacks |
| 10 | **Medium** | Runtime Crash / TypeError on null data | [`src/gpcli/services/catalog.py`](file:///c:/Users/Inan/Documents/Project/Triage/mygp/app/src/gpcli/services/catalog.py#L210) | `vas_categories` and `vas_services` do `data.get("data", [])`; if the backend returns `{"data": null}`, list comprehension crashes on `None` |
| 11 | **Medium** | Crash on null dictionary | [`src/gpcli/render/content.py`](file:///c:/Users/Inan/Documents/Project/Triage/mygp/app/src/gpcli/render/content.py#L13) | `data.get("cards", {})` returns `None` if payload has `{"cards": null}`, crashing `len()` and `.items()` |
| 12 | **Low** | CLI Output Corruption | [`src/gpcli/commands/raw.py`](file:///c:/Users/Inan/Documents/Project/Triage/mygp/app/src/gpcli/commands/raw.py#L57) | `gpcli raw call` unconditionally prints HTTP status line before JSON even when `--json` flag is supplied |
| 13 | **Low** | False Success Exit Code | [`src/gpcli/commands/mca.py`](file:///c:/Users/Inan/Documents/Project/Triage/mygp/app/src/gpcli/commands/mca.py#L56) | When activation/deactivation fails, `gpcli mca on/off` prints failure message but does not raise `typer.Exit(1)` |
| 14 | **Low** | Broken `--json` Output & Silent Failure | [`src/gpcli/commands/transfer.py`](file:///c:/Users/Inan/Documents/Project/Triage/mygp/app/src/gpcli/commands/transfer.py#L107) | `gpcli transfer reset-pin` emits multiple separate JSON payloads and returns 0 exit code on early failures |
| 15 | **Low** | Silent Parameter Drop | [`src/gpcli/commands/history.py`](file:///c:/Users/Inan/Documents/Project/Triage/mygp/app/src/gpcli/commands/history.py#L31) | Providing only `--start` or only `--end` evaluates `start and end` to False and silently drops the user-supplied date |
| 16 | **Low** | File System Error | [`src/gpcli/commands/sim.py`](file:///c:/Users/Inan/Documents/Project/Triage/mygp/app/src/gpcli/commands/sim.py#L33) | `gpcli sim certificate --out <path>` does not ensure parent directories exist before calling `out.write_text()`, causing `FileNotFoundError` |
| 17 | **Low** | String Formatting Bug | [`src/gpcli/commands/autopay.py`](file:///c:/Users/Inan/Documents/Project/Triage/mygp/app/src/gpcli/commands/autopay.py#L99) | `frequency` is a `str`; calling `plural(frequency, 'day')` performs `"1" == 1` which evaluates to False, producing `"1 days"` |
| 18 | **Low** | Runtime Crash / KeyError | [`src/gpcli/services/netcare.py`](file:///c:/Users/Inan/Documents/Project/Triage/mygp/app/src/gpcli/services/netcare.py#L36) | `NetworkComplainService.submit()` uses direct dictionary indexing `a["id"]`, `a["type"]`, `a["feedback"]` which crashes if keys are missing |

---

## Detailed Bug Reports

### 1. `AttributeError` in `render_me` ([`render/account.py:L68`](file:///c:/Users/Inan/Documents/Project/Triage/mygp/app/src/gpcli/render/account.py#L68))
- **File:** [`src/gpcli/render/account.py`](file:///c:/Users/Inan/Documents/Project/Triage/mygp/app/src/gpcli/render/account.py) (lines 68–69) & [`src/gpcli/models/account.py`](file:///c:/Users/Inan/Documents/Project/Triage/mygp/app/src/gpcli/models/account.py)
- **Description:**
  ```python
  if p.rfu_1:
      grid.add_row("interests", p.rfu_1)
  ```
  `Profile` model does not declare an `rfu_1` field. In Pydantic v2, extra fields are stored in `__pydantic_extra__` and accessing `p.rfu_1` when not present in the payload raises an `AttributeError`.
- **Impact:** Any call to `gpcli me`, `gpcli account me`, or `gpcli login` crashes whenever the API response lacks `rfu_1`. In `gpcli login`, this crashes right after successful login.

---

### 2. `PackItem.validity_summary()` Returns `None`, Causing `TypeError` in `render_packs` ([`models/catalog.py:L179`](file:///c:/Users/Inan/Documents/Project/Triage/mygp/app/src/gpcli/models/catalog.py#L179))
- **File:** [`src/gpcli/models/catalog.py`](file:///c:/Users/Inan/Documents/Project/Triage/mygp/app/src/gpcli/models/catalog.py) (lines 173–180) & [`src/gpcli/render/catalog.py`](file:///c:/Users/Inan/Documents/Project/Triage/mygp/app/src/gpcli/render/catalog.py#L158)
- **Description:**
  ```python
  def validity_summary(self) -> str:
      validity = self.validity
      if not validity:
          return ""
      if validity.value:
          return f"{validity.value} {validity.unit}".strip()
      return validity.unit  # Returns None if validity.unit is None!
  ```
  In [`render/catalog.py`](file:///c:/Users/Inan/Documents/Project/Triage/mygp/app/src/gpcli/render/catalog.py#L158):
  ```python
  pack.validity_summary()[:18] or "-"
  ```
  When `validity_summary()` returns `None`, slicing `None[:18]` raises:
  `TypeError: 'NoneType' object is not subscriptable`.
  Additionally, when `validity.value` is `"30"` and `validity.unit` is `None`, line 178 formats it as `"30 None"`.
- **Impact:** `gpcli packs` crashes whenever a pack in Grameenphone's catalog has an empty or unit-less validity.

---

### 3. Built-in `list` Shadowed by Class Method `list()` ([`services/autopay.py`](file:///c:/Users/Inan/Documents/Project/Triage/mygp/app/src/gpcli/services/autopay.py#L60), [`services/welcome_tune.py`](file:///c:/Users/Inan/Documents/Project/Triage/mygp/app/src/gpcli/services/welcome_tune.py#L32))
- **File:** [`src/gpcli/services/autopay.py`](file:///c:/Users/Inan/Documents/Project/Triage/mygp/app/src/gpcli/services/autopay.py#L60-L77), [`src/gpcli/services/welcome_tune.py`](file:///c:/Users/Inan/Documents/Project/Triage/mygp/app/src/gpcli/services/welcome_tune.py#L32-L44)
- **Description:**
  Inside `AutoPayService`:
  ```python
  def list(self, connection_type: str = "prepaid") -> AutoPayListResponse:
      ...
  def products(self, connection_type: str = "prepaid") -> list[AutoPayProduct]:
      ...
  ```
  Because `list` is declared as a method name in class scope, subsequent type annotations `list[...]` resolve `list` to `AutoPayService.list` (a function object) instead of Python's built-in `list` type.
- **Impact:** Mypy flags 7 errors; typing evaluation and reflection fail with `Function is not valid as a type`.

---

### 4. `gpcli streak claim` Accesses Unpopulated Reward ([`commands/gamification.py:L91`](file:///c:/Users/Inan/Documents/Project/Triage/mygp/app/src/gpcli/commands/gamification.py#L91))
- **File:** [`src/gpcli/commands/gamification.py`](file:///c:/Users/Inan/Documents/Project/Triage/mygp/app/src/gpcli/commands/gamification.py#L78-L93)
- **Description:**
  `info.milestone` items returned by `GET /v2/gamification/daily-login` only contain `id` and `status`. The reward amount (`milestone_reward`) is returned in `info.settings.milestones`.
  In `claim()`:
  ```python
  target = claimable[0]
  ...
  reward = target.milestone_reward or 0
  label = plural(reward, "GP point")
  if not yes and not typer.confirm(f"Claim {label} (milestone {milestone_id})?"):
  ```
  `target` from `info.milestone` never has `milestone_reward` set (it is always `None`). Therefore, `reward` is always `0`, and user is prompted: `Claim 0 GP points (milestone 1)?`.
  Furthermore, `target.id` can be `None`, in which case `milestone_id` becomes `None` and is passed as `{"milestone_id": null}` to the API.
- **Impact:** Confirmation prompt displays 0 points and potential null milestone payload.

---

### 5. String-Numeric Type Errors in Emergency Balance ([`services/emergency.py:L57`](file:///c:/Users/Inan/Documents/Project/Triage/mygp/app/src/gpcli/services/emergency.py#L57))
- **File:** [`src/gpcli/services/emergency.py`](file:///c:/Users/Inan/Documents/Project/Triage/mygp/app/src/gpcli/services/emergency.py#L53-L63) & [`src/gpcli/commands/emergency.py`](file:///c:/Users/Inan/Documents/Project/Triage/mygp/app/src/gpcli/commands/emergency.py#L42-L48)
- **Description:**
  `full_state()` returns raw dict data from `/balance` without Pydantic conversion.
  ```python
  main_balance = state.get("balance", 0) or 0
  threshold = settings.get("eb_eligibility_balance", 18)
  active_loan = (eb.get("total") or 0) > 0
  "eligible": not active_loan and main_balance < threshold
  ```
  When the backend returns string representations (e.g. `"100.50"` or `"0"`), Python raises:
  `TypeError: '<' not supported between instances of 'str' and 'int'`.
  In `commands/emergency.py`:
  `rows.append(("main balance", f"{info['main_balance']:g} BDT"))`
  `f"{'100.50':g}"` raises `ValueError: Unknown format code 'g' for object of type 'str'`.
- **Impact:** `gpcli eb status` crashes on production accounts where balance fields arrive as strings.

---

### 6. Interceptor Skip Marker Discrepancy (`v2` vs `v1`) ([`constants.py:L52`](file:///c:/Users/Inan/Documents/Project/Triage/mygp/app/src/gpcli/constants.py#L52))
- **File:** [`src/gpcli/constants.py`](file:///c:/Users/Inan/Documents/Project/Triage/mygp/app/src/gpcli/constants.py#L52) vs [`src/gpcli/services/partners.py`](file:///c:/Users/Inan/Documents/Project/Triage/mygp/app/src/gpcli/services/partners.py#L28)
- **Description:**
  `constants.py` defines:
  ```python
  ID_PARAM_SKIP_MARKERS = ("v2/sbcontents/search", "v2/sbcontents/get-content-by-id")
  ```
  While `partners.py` defines:
  ```python
  SBCONTENTS_SEARCH_ENDPOINT = "/v1/sbcontents/search"
  SBCONTENTS_PARTNER_ENDPOINT = "/v1/sbcontents/partner"
  ```
  Because the marker specifies `v2` instead of `v1`, `MyGPClient._base_params` does not recognize the endpoint and appends `?id=<auth.id>` to `/v1/sbcontents/search` and `/v1/sbcontents/partner`.
- **Impact:** Leaks subscriber ID to partner content endpoints, violating the reverse-engineered interceptor contract.

---

### 7. `GuestSession.token_expired()` Returns `0` (int) Instead of `bool` ([`models/auth.py:L79`](file:///c:/Users/Inan/Documents/Project/Triage/mygp/app/src/gpcli/models/auth.py#L79))
- **File:** [`src/gpcli/models/auth.py`](file:///c:/Users/Inan/Documents/Project/Triage/mygp/app/src/gpcli/models/auth.py#L78-L80)
- **Description:**
  ```python
  def token_expired(self, now: int, skew: int = 60) -> bool:
      return not self.access_token or (self.expires_at and now > self.expires_at - skew)
  ```
  When `access_token` exists and `expires_at == 0`, `(0 and now > ...)` returns `0`.
- **Impact:** Mypy type error (`Literal[0] | bool`); falsy return value prevents token expiration detection.

---

### 8. `ContentService` Incompatible with `ApiCaller` ([`services/content.py:L26`](file:///c:/Users/Inan/Documents/Project/Triage/mygp/app/src/gpcli/services/content.py#L26))
- **File:** [`src/gpcli/services/content.py`](file:///c:/Users/Inan/Documents/Project/Triage/mygp/app/src/gpcli/services/content.py#L24-L26)
- **Description:**
  `ContentService.__init__` is typed to take `client: ApiCaller`, but inside initializes `AuthService(client)`. `AuthService` explicitly requires `MyGPClient` because it invokes `self.client.raw_post(...)`, which is not part of the `ApiCaller` protocol.
- **Impact:** Passing an `ApiCaller` mock or alternative transport crashes with `AttributeError` when guest tokens are minted.

---

### 9. Bypassing Error Boundary with Built-in Exceptions ([`services/offers.py:L83`](file:///c:/Users/Inan/Documents/Project/Triage/mygp/app/src/gpcli/services/offers.py#L83), [`services/catalog.py:L152`](file:///c:/Users/Inan/Documents/Project/Triage/mygp/app/src/gpcli/services/catalog.py#L152))
- **File:** [`src/gpcli/services/offers.py`](file:///c:/Users/Inan/Documents/Project/Triage/mygp/app/src/gpcli/services/offers.py#L83), [`src/gpcli/services/catalog.py`](file:///c:/Users/Inan/Documents/Project/Triage/mygp/app/src/gpcli/services/catalog.py#L152)
- **Description:**
  `main.py` only catches `MyGPError`:
  ```python
  try:
      app()
  except MyGPError as err:
      console.print(f"[red]error:[/red] {err}")
      raise SystemExit(1) from err
  ```
  In `payg_toggle()`: raises `RuntimeError("no ... pack in the catalog")`.
  In `quote_flexiplan()`: raises `KeyError(f"no bundle priced for {key}")`.
- **Impact:** When a user queries an invalid flexiplan bundle or toggles PAYG without catalog packs, an unhandled Python traceback is printed to the console.

---

### 10. `NoneType` Iteration on Null `data` in VAS ([`services/catalog.py:L210`](file:///c:/Users/Inan/Documents/Project/Triage/mygp/app/src/gpcli/services/catalog.py#L210))
- **File:** [`src/gpcli/services/catalog.py`](file:///c:/Users/Inan/Documents/Project/Triage/mygp/app/src/gpcli/services/catalog.py#L208-L228)
- **Description:**
  ```python
  def vas_categories(self) -> list[VasCategory]:
      data = self.client.get_json(...)
      return [VasCategory.model_validate(item) for item in data.get("data", [])]
  ```
  If `data` has `{"data": null}`, `data.get("data", [])` returns `None`. The list comprehension then raises:
  `TypeError: 'NoneType' object is not iterable`.
- **Impact:** `gpcli vas categories` and `gpcli vas services` crash if the server returns a null data field.

---

### 11. `NoneType` Error in `render_cards` ([`render/content.py:L13`](file:///c:/Users/Inan/Documents/Project/Triage/mygp/app/src/gpcli/render/content.py#L13))
- **File:** [`src/gpcli/render/content.py`](file:///c:/Users/Inan/Documents/Project/Triage/mygp/app/src/gpcli/render/content.py#L12-L19)
- **Description:**
  ```python
  cards = data.get("cards", {})
  ...
  table = Table(..., title=f"Cards engine — {plural(len(cards), 'card')}")
  for card_id, card in list(cards.items())[:40]:
  ```
  If `data` contains `{"cards": null}`, `cards` becomes `None`. Both `len(cards)` and `cards.items()` raise `TypeError` and `AttributeError`.
- **Impact:** `gpcli content cards` crashes on null card response.

---

### 12. Unconditional Text in `--json` Mode ([`commands/raw.py:L57`](file:///c:/Users/Inan/Documents/Project/Triage/mygp/app/src/gpcli/commands/raw.py#L57))
- **File:** [`src/gpcli/commands/raw.py`](file:///c:/Users/Inan/Documents/Project/Triage/mygp/app/src/gpcli/commands/raw.py#L57)
- **Description:**
  `gpcli raw call` unconditionally executes:
  ```python
  console.print(f"[dim]{response.status_code} {response.reason_phrase}[/dim]")
  ```
  even when `--json` is active, corrupting stdout with non-JSON text.
- **Impact:** Automation pipelines consuming `gpcli --json raw call ...` fail JSON deserialization.

---

### 13. Silent Failure Exit Code in `mca` ([`commands/mca.py:L56`](file:///c:/Users/Inan/Documents/Project/Triage/mygp/app/src/gpcli/commands/mca.py#L56))
- **File:** [`src/gpcli/commands/mca.py`](file:///c:/Users/Inan/Documents/Project/Triage/mygp/app/src/gpcli/commands/mca.py#L53-L57)
- **Description:**
  When `gpcli mca on` or `gpcli mca off` receives a non-pending response from the API, it prints `[red]failed[/red] ...` but does not raise `typer.Exit(1)`.
- **Impact:** Command exits with code 0 on failure, misleading shell scripts.

---

### 14. Broken `--json` Flow & Silent Failure in `transfer reset-pin` ([`commands/transfer.py:L107`](file:///c:/Users/Inan/Documents/Project/Triage/mygp/app/src/gpcli/commands/transfer.py#L107))
- **File:** [`src/gpcli/commands/transfer.py`](file:///c:/Users/Inan/Documents/Project/Triage/mygp/app/src/gpcli/commands/transfer.py#L105-L133)
- **Description:**
  In `reset_pin()`, if `ctx.json_out` is True:
  - It prints `{"initiate": ...}` on step 1.
  - It prints `{"verify": ...}` on step 2.
  - It prints `{"set": ...}` on step 3.
  This results in multiple distinct JSON objects on stdout. Furthermore, if step 1 or 2 fails under `--json`, the function simply calls `return` with an exit code of 0.
- **Impact:** Produces invalid JSON streams and falsely signals success on error.

---

### 15. Silent Drop of Date Filter in `history` ([`commands/history.py:L31`](file:///c:/Users/Inan/Documents/Project/Triage/mygp/app/src/gpcli/commands/history.py#L31))
- **File:** [`src/gpcli/commands/history.py`](file:///c:/Users/Inan/Documents/Project/Triage/mygp/app/src/gpcli/commands/history.py#L29-L33)
- **Description:**
  ```python
  window = (
      (date.fromisoformat(start), date.fromisoformat(end))
      if start and end
      else default_window(days)
  )
  ```
  If a user passes only `--start 2026-09-01` or only `--end 2026-09-05`, `start and end` evaluates to False, and the user's explicit parameter is silently discarded in favor of `default_window(days)`.
- **Impact:** User filters are silently ignored without an error or warning.

---

### 16. Missing Directory Creation in `sim certificate` ([`commands/sim.py:L33`](file:///c:/Users/Inan/Documents/Project/Triage/mygp/app/src/gpcli/commands/sim.py#L33))
- **File:** [`src/gpcli/commands/sim.py`](file:///c:/Users/Inan/Documents/Project/Triage/mygp/app/src/gpcli/commands/sim.py#L32-L34)
- **Description:**
  ```python
  if out:
      out.write_text(cert.data, encoding="utf-8")
  ```
  If `out` includes non-existent parent directories (e.g. `--out certs/sim.html`), `out.write_text()` raises `FileNotFoundError`. Unlike `BillService.itemized_pdf`, it does not call `out.parent.mkdir(parents=True, exist_ok=True)`.
- **Impact:** Crash when saving certificate to a nested path.

---

### 17. Pluralization Bug with String Frequency ([`commands/autopay.py:L99`](file:///c:/Users/Inan/Documents/Project/Triage/mygp/app/src/gpcli/commands/autopay.py#L99))
- **File:** [`src/gpcli/commands/autopay.py`](file:///c:/Users/Inan/Documents/Project/Triage/mygp/app/src/gpcli/commands/autopay.py#L85, #L99) & [`src/gpcli/render/base.py`](file:///c:/Users/Inan/Documents/Project/Triage/mygp/app/src/gpcli/render/base.py#L42)
- **Description:**
  `frequency` is a CLI string option (`""`). `plural(n: int, word: str)` expects an integer and tests `n == 1`. Passing a string `"1"` results in `"1" == 1` evaluating to `False`, rendering `"1 days"` instead of `"1 day"`.
- **Impact:** Grammatical error and type check failure.

---

### 18. Unhandled `KeyError` in Netcare Submit ([`services/netcare.py:L36`](file:///c:/Users/Inan/Documents/Project/Triage/mygp/app/src/gpcli/services/netcare.py#L36))
- **File:** [`src/gpcli/services/netcare.py`](file:///c:/Users/Inan/Documents/Project/Triage/mygp/app/src/gpcli/services/netcare.py#L34-L39)
- **Description:**
  `NetworkComplainService.submit()` constructs:
  ```python
  "questions": [
      {"id": a["id"], "type": a["type"], "feedback": a["feedback"]}
      for a in answers
  ]
  ```
  If any dictionary in `answers` omits `type`, `id`, or `feedback`, it raises an unhandled `KeyError`.
- **Impact:** Crash with Python traceback instead of validation error.
