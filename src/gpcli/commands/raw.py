"""`gpcli raw` — authenticated passthrough for arbitrary endpoints.

The escape hatch for the ~200 endpoints already mapped in the decompiled
sources but not yet wrapped by a typed command.
"""

from __future__ import annotations

import json as _json

import typer

from gpcli.client import AuthMode
from gpcli.context import get_context
from gpcli.errors import MyGPError
from gpcli.render import console

app = typer.Typer(help="Raw authenticated API passthrough")

_METHODS = ("GET", "POST", "PUT", "PATCH", "DELETE")


@app.command("call")
def call(
    method: str = typer.Argument(...),
    path: str = typer.Argument(..., help="Path (e.g. balance) or absolute URL"),
    base: str = typer.Option("mygpapi", "--base", help="mygpapi | apigw"),
    body: str | None = typer.Option(None, "--body", "-b", help="JSON request body"),
    guest: bool = typer.Option(False, "--guest", help="Use the guest session"),
    no_auth: bool = typer.Option(False, "--no-auth", help="Send unauthenticated"),
) -> None:
    """Fire an arbitrary request through the full interceptor stack."""
    method = method.upper()
    if method not in _METHODS:
        raise typer.BadParameter(f"method must be one of {_METHODS}")

    if guest:
        auth_mode = AuthMode.GUEST
    elif no_auth:
        auth_mode = AuthMode.NONE
    else:
        auth_mode = AuthMode.AUTO

    json_body = None
    if body is not None:
        try:
            json_body = _json.loads(body)
        except _json.JSONDecodeError as err:
            raise typer.BadParameter(f"--body is not valid JSON: {err}") from err

    ctx = get_context()
    with ctx.client() as client:
        response = client.request(
            method, path, base=base, json_body=json_body, auth_mode=auth_mode
        )

    if not ctx.json_out:
        console.print(f"[dim]{response.status_code} {response.reason_phrase}[/dim]")
    try:
        console.print_json(data=response.json())
    except (ValueError, MyGPError):
        console.print(response.text[:2000])
