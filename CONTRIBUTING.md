# Contributing

Thanks for improving gpcli. This is a small, heavily-tested research
codebase — the ground rules below keep it that way.

## Development setup

```powershell
git clone <your-fork> && cd gpcli
pip install -e .
pip install pytest ruff
python -m pytest tests -q     # 130 tests must pass
python -m ruff check src tests
```

Python ≥ 3.10. No network is needed for the test suite — everything runs
against a scripted `httpx.MockTransport`.

## Ground rules

1. **The interceptor semantics are the compatibility contract.**
   `client.py`'s header injection, the 403 → silent-refresh-retry, the
   401/911/410 logout, the 600s refresh guards — these replicate the
   Android app byte-for-byte. Never change them casually; the tests in
   `test_client.py` freeze them.
2. **Wire formats are documented in docstrings.** Every service module
   opens with the exact endpoint contract (method, path, body fields with
   their literal spellings). If you touch a wire format, update the
   docstring in the same change.
3. **No personal data.** Test fixtures use the synthetic identifiers in
   `tests/constants.py` — never paste a real MSISDN, token, or NID into
   code, tests, or an issue.
4. **Layering** (see the README Architecture section):
   - `commands/` — Typer/Rich only; get clients via `ctx.client()`
   - `services/` — endpoint knowledge; typed against `ApiCaller`
   - `bodies.py` / `msisdn.py` — pure functions, no I/O
   - `client.py` — the only module that touches HTTP
   - `models/`, `render/` — facades; import from the package root

## Adding a command group

Three touches, no more:

1. **`commands/<name>.py`** — one typer app per module:

   ```python
   import typer
   from gpcli.context import get_context
   from gpcli.render import console

   app = typer.Typer(help="One line of help")

   @app.command()
   def frobnicate() -> None:
       ctx = get_context()
       with ctx.client() as client:
           result = FrobnicateService(client).run()
       if ctx.json_out:
           console.print_json(data=result)
           return
       console.print(result)
   ```

   Every command honors the global `--json` flag (`ctx.json_out`) and
   prompts before anything irreversible (`typer.confirm` unless `--yes`).

2. **`services/<name>.py`** — if the logic is non-trivial, put the
   endpoint knowledge in a service typed against `ApiCaller`. Document
   the wire contract in the module docstring.

3. **`main.py`** — add one line to the `GROUPS` registry.

Then tests: register mock routes on the `make_client` recorder (one-shot —
add one route per expected HTTP call so retry paths see fresh responses)
and assert on the exact request URL, headers, and body.

## Pull-request checklist

- [ ] `pytest` green, `ruff` clean
- [ ] Wire-format docstrings updated alongside any format change
- [ ] New commands: `--json` support + confirmation gating
- [ ] No personal data anywhere in the diff
- [ ] `CHANGELOG.md` entry (user-visible changes)
- [ ] If you touched `client.py`'s request path: explain why the
      interceptor semantics are preserved

## Reporting security issues

See [SECURITY.md](SECURITY.md) — private disclosure, no public issues.
