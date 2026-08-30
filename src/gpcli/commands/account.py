"""`gpcli` top-level account commands: me, balance, usage, sim."""

from __future__ import annotations

import typer

from gpcli.context import get_context
from gpcli.render import console, render_balance, render_dict, render_me
from gpcli.services.account import AccountService

app = typer.Typer(help="Subscriber account endpoints")


@app.command("me")
def me() -> None:
    """Subscriber identity and profile."""
    ctx = get_context()
    with ctx.client() as client:
        result = AccountService(client).me()
    if ctx.json_out:
        console.print_json(data=result.model_dump(exclude_none=True))
        return
    render_me(result)


@app.command("balance")
def balance() -> None:
    """Main balance, package balances, emergency balance."""
    ctx = get_context()
    with ctx.client() as client:
        result = AccountService(client).balance()
    if ctx.json_out:
        console.print_json(data=result.model_dump(exclude_none=True))
        return
    render_balance(result)


@app.command("usage")
def usage() -> None:
    """Current usage snapshot (raw)."""
    ctx = get_context()
    with ctx.client() as client:
        result = AccountService(client).usage()
    if ctx.json_out:
        console.print_json(data=result)
        return
    render_dict("usage", result)


@app.command("sim")
def sim() -> None:
    """SIM status (foreigner flag, validity)."""
    ctx = get_context()
    with ctx.client() as client:
        result = AccountService(client).customer_status()
    if ctx.json_out:
        console.print_json(data=result)
        return
    render_dict("sim", result)
