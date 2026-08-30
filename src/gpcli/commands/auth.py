"""`gpcli auth …` — login staging, refresh, import, logout."""

from __future__ import annotations

import time

import typer

from gpcli.context import get_context
from gpcli.models import Auth
from gpcli.render import console, render_login_success
from gpcli.services.auth import AuthService
from gpcli.state import apply_new_auth

app = typer.Typer(help="Authentication: OTP, silent SIM, guest, refresh, logout")


def _fmt_expiry(expire_at: int | None) -> str:
    if not expire_at:
        return "?"
    remaining = expire_at - int(time.time())
    if remaining <= 0:
        return "expired"
    hours, rem = divmod(remaining, 3600)
    return f"in {hours}h {rem // 60}m" if hours else f"in {rem // 60}m"


@app.command("send-otp")
def send_otp(msisdn: str) -> None:
    """Request an OTP SMS for a MSISDN (stages it for `verify-otp`)."""
    ctx = get_context()
    with ctx.client() as client:
        result = AuthService(client).send_otp(msisdn)
    if ctx.json_out:
        console.print_json(data=result.model_dump(exclude_none=True))
        return
    if result.result == "success":
        console.print("[green]OTP dispatched[/green] — check your SMS, then run:")
        console.print("  [dim]$[/dim] gpcli auth verify-otp <code>")
    else:
        err = result.error
        code = err.code if err else "?"
        summary = err.summary() if err else "unknown error"
        console.print(f"[red]OTP request failed:[/red] [{code}] {summary}")
        raise typer.Exit(1)


@app.command("verify-otp")
def verify_otp(
    otp: str,
    msisdn: str | None = typer.Option(None, help="Override the staged MSISDN"),
) -> None:
    """Exchange the received SMS code for a subscriber session."""
    ctx = get_context()
    with ctx.client() as client:
        auth = AuthService(client).verify_otp(otp, msisdn=msisdn)
    if ctx.json_out:
        console.print_json(data=auth.model_dump(exclude_none=True))
        return
    render_login_success(auth)


@app.command("silent")
def silent() -> None:
    """Silent SIM login (requires Grameenphone mobile-data connectivity)."""
    ctx = get_context()
    with ctx.client() as client:
        auth = AuthService(client).silent_login()
    if ctx.json_out:
        console.print_json(data=auth.model_dump(exclude_none=True))
        return
    render_login_success(auth)


@app.command("refresh")
def refresh(force: bool = typer.Option(False, "--force", help="Bypass the 600s rate-guard")) -> None:
    """Refresh the access token using the stored refresh token."""
    ctx = get_context()
    with ctx.client() as client:
        auth = AuthService(client).refresh(force=force)
    if ctx.json_out:
        console.print_json(data=auth.model_dump(exclude_none=True))
        return
    console.print(f"[green]refreshed[/green] — expires {_fmt_expiry(auth.expire_at)}")


@app.command("import")
def import_tokens(
    access_token: str = typer.Option(..., "--access-token"),
    refresh_token: str = typer.Option(..., "--refresh-token"),
    auth_id: int = typer.Option(..., "--id"),
    msisdn: str = typer.Option("", "--msisdn"),
    expire_at: int = typer.Option(0, "--expire-at", help="unix epoch seconds"),
) -> None:
    """Import an existing session (tooling / migration)."""
    ctx = get_context()
    state = ctx.state
    auth = Auth(
        id=auth_id,
        access_token=access_token,
        token=access_token,
        refresh_token=refresh_token,
        msisdn=msisdn,
        expire_at=expire_at or None,
    )
    apply_new_auth(state, auth)
    state.save()
    if ctx.json_out:
        console.print_json(data={"imported": True, "id": auth.id, "msisdn": auth.msisdn})
    else:
        console.print(f"[green]session imported[/green] (auth id {auth.id})")


@app.command("logout")
def logout(all_devices: bool = typer.Option(False, "--all", help="Log out from every device")) -> None:
    """Invalidate the current session."""
    ctx = get_context()
    with ctx.client() as client:
        AuthService(client).logout(all_devices=all_devices)
    console.print("[green]logged out[/green]" + (" (all devices)" if all_devices else ""))
