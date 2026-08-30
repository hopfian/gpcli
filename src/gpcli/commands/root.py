"""Root-level commands — login, guest, status, me, balance, news.

Registered directly on the top-level app by `main.py` (the composition root).
"""

from __future__ import annotations

import contextlib

import typer
from rich.prompt import Prompt

from gpcli.context import get_context
from gpcli.errors import MyGPError
from gpcli.render import (
    console,
    render_auth_status,
    render_balance,
    render_login_success,
    render_me,
    render_news,
)
from gpcli.services.account import AccountService
from gpcli.services.auth import AuthService
from gpcli.services.content import ContentService


def login(msisdn: str) -> None:
    """Interactive OTP login: send code, prompt, verify, save session."""
    ctx = get_context()
    with ctx.client() as client:
        auth_service = AuthService(client)
        result = auth_service.send_otp(msisdn)
        if result.result != "success":
            err = result.error
            console.print(
                f"[red]OTP request failed:[/red] [{err.code if err else '?'}] "
                f"{err.summary() if err else 'unknown'}"
            )
            raise typer.Exit(1)
        code = Prompt.ask("Enter the OTP from your SMS")
        auth = auth_service.verify_otp(code)
    if ctx.json_out:
        console.print_json(data=auth.model_dump(exclude_none=True))
        return
    render_login_success(auth)
    with contextlib.suppress(MyGPError), ctx.client() as client:
        render_me(AccountService(client).me())


def guest() -> None:
    """Establish/refresh an anonymous guest session (no SIM required)."""
    ctx = get_context()
    with ctx.client() as client:
        session = AuthService(client).guest_login(refresh_token=True)
    if ctx.json_out:
        console.print_json(data=session.model_dump(exclude_none=True))
        return
    console.print(f"[green]guest session ready[/green] — user id {session.user_id}")


def status() -> None:
    """Show session and device state."""
    ctx = get_context()
    if ctx.json_out:
        console.print_json(data=ctx.state.model_dump(exclude={"path"}, exclude_none=True))
        return
    render_auth_status(ctx.state)


def me() -> None:
    """Subscriber identity and profile."""
    ctx = get_context()
    with ctx.client() as client:
        result = AccountService(client).me()
    if ctx.json_out:
        console.print_json(data=result.model_dump(exclude_none=True))
        return
    render_me(result)


def balance() -> None:
    """Main/package balances."""
    ctx = get_context()
    with ctx.client() as client:
        result = AccountService(client).balance()
    if ctx.json_out:
        console.print_json(data=result.model_dump(exclude_none=True))
        return
    render_balance(result)


def news() -> None:
    """News feed (subscriber)."""
    ctx = get_context()
    with ctx.client() as client:
        result = ContentService(client, AuthService(client)).news()
    if ctx.json_out:
        console.print_json(data=result)
        return
    render_news(result)
