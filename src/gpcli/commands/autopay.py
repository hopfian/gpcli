"""`gpcli autopay …` — automatic recharge subscriptions."""

from __future__ import annotations

from datetime import date

import typer
from rich.panel import Panel

from gpcli.context import get_context
from gpcli.errors import MyGPError
from gpcli.render import (
    _fmt_panel_grid,
    console,
    plural,
    render_action_response,
    render_autopay_list,
    render_autopay_products,
    render_payment_methods,
)
from gpcli.services.auth import normalize_msisdn
from gpcli.services.autopay import AutoPayService

app = typer.Typer(help="AutoPay: scheduled and low-balance automatic recharges")


@app.command("list")
def list_subscriptions() -> None:
    """List autopay subscriptions and settings (GET subscription-list)."""
    ctx = get_context()
    with get_context().client() as client:
        response = AutoPayService(client).subscriptions()
    if ctx.json_out:
        console.print_json(data=response.model_dump(exclude_none=True))
        return
    render_autopay_list(response)


@app.command()
def products() -> None:
    """Show autopay product configuration (codes, frequencies, limits)."""
    ctx = get_context()
    with get_context().client() as client:
        result = AutoPayService(client).products()
    if ctx.json_out:
        console.print_json(data=[p.model_dump(exclude_none=True) for p in result])
        return
    render_autopay_products(result)


@app.command()
def methods() -> None:
    """Saved payment methods — the source of service_provider values."""
    ctx = get_context()
    with get_context().client() as client:
        result = AutoPayService(client).payment_methods()
    if ctx.json_out:
        console.print_json(data=result)
        return
    render_payment_methods(result)


@app.command()
def recent() -> None:
    """Recently recharged numbers (autopay candidates)."""
    with get_context().client() as client:
        result = AutoPayService(client).recent_numbers()
    if get_context().json_out:
        console.print_json(data=result)
        return
    console.print(Panel(", ".join(result) if result else "none", title=f"Recent numbers ({len(result)})"))


@app.command()
def validate(msisdn: str) -> None:
    """Check a number's autopay eligibility (GP/skitto, connection type, EB due)."""
    normalized = normalize_msisdn(msisdn)
    ctx = get_context()
    with ctx.client() as client:
        result = AutoPayService(client).validate_msisdn(normalized)
    if ctx.json_out:
        console.print_json(data=result)
        return
    data = result.get("data") if isinstance(result, dict) else None
    data = data if isinstance(data, dict) else {}
    eb = data.get("emergency_balance") or {}
    eligible = data.get("is_gp") and not data.get("is_skitto") and data.get("connection_type")
    verdict = "[green]eligible[/green]" if eligible else "[red]not eligible[/red]"
    console.print(_fmt_panel_grid(f"Autopay eligibility — {msisdn}", [
        ("verdict", verdict),
        ("is gp", "yes" if data.get("is_gp") else "no"),
        ("is skitto", "yes" if data.get("is_skitto") else "no"),
        ("connection type", str(data.get("connection_type", "-"))),
        ("service class", str(data.get("service_class", "-"))),
        ("eb due", str(eb.get("due", "-")) if isinstance(eb, dict) else "-"),
    ]))


@app.command()
def setup(
    msisdn: str = typer.Argument(..., help="Number to recharge for (provisioning)"),
    amount: str = typer.Argument(..., help="Recharge amount"),
    frequency: str = typer.Option(
        "", "--frequency", "-f", help="Scheduled recharge every N days (omit = low-balance)"
    ),
    start_from: str = typer.Option("", "--start-from", help="Start date yyyy-mm-dd (default tomorrow)"),
    provider: str = typer.Option("", "--provider", help="service_provider (see `gpcli autopay methods`)"),
    identifier: str = typer.Option("", "--identifier", help="service_provider_identifier"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip the confirmation prompt"),
) -> None:
    """Create an autopay subscription (POST v1/auto-payment/pay)."""
    if not provider or not identifier:
        raise typer.BadParameter(
            "--provider and --identifier are required (discover values via `gpcli autopay methods`)"
        )
    if frequency and not frequency.isdigit():
        raise typer.BadParameter("--frequency must be a whole number of days")
    start_date = date.fromisoformat(start_from) if start_from else None
    mode = f"scheduled every {plural(int(frequency), 'day')}" if frequency else "on low balance"
    when = start_date or "tomorrow"
    if not yes and not typer.confirm(
        f"Set up autopay: {amount} BDT -> {msisdn} ({mode}, starting {when})?"
    ):
        console.print("[dim]aborted[/dim]")
        raise typer.Exit(1)

    with get_context().client() as client:
        result = AutoPayService(client).setup(
            amount=amount,
            provisioning_msisdn=msisdn,
            service_provider=provider,
            service_provider_identifier=identifier,
            frequency=frequency or None,
            start_from=start_date,
        )
    ctx = get_context()
    if ctx.json_out:
        console.print_json(data=result)
        return
    if not render_action_response(result, title="Autopay created", rows=[
        ("number", msisdn),
        ("amount", f"{amount} BDT"),
        ("mode", mode),
        ("starts", str(when)),
    ]):
        raise typer.Exit(1)


@app.command()
def cancel(
    subscription_id: int = typer.Argument(...),
    msisdn: str = typer.Option("", "--msisdn", help="provisioning number (auto-resolved if omitted)"),
) -> None:
    """Cancel an autopay subscription (DELETE v1/auto-payment/{id}/cancel)."""
    with get_context().client() as client:
        service = AutoPayService(client)
        if not msisdn:
            for sub in service.subscriptions().subscription:
                if sub.id == subscription_id:
                    msisdn = sub.msisdn
        if not msisdn:
            raise typer.BadParameter(
                "could not resolve the provisioning number — pass --msisdn (see `gpcli autopay list`)"
            )
        result = service.cancel(subscription_id, msisdn)
    ctx = get_context()
    if ctx.json_out:
        console.print_json(data=result)
        return
    if not render_action_response(result, title="Autopay cancelled", rows=[
        ("subscription", str(subscription_id)),
        ("number", msisdn),
    ]):
        raise typer.Exit(1)


@app.command()
def update(
    subscription_id: int = typer.Argument(...),
    amount: str = typer.Option(..., "--amount", help="New recharge amount"),
    frequency: str = typer.Option("", "--frequency", help="New frequency in days (omit = low-balance)"),
    start_from: str = typer.Option("", "--start-from", help="New start date yyyy-mm-dd"),
    provider: str = typer.Option("", "--provider", help="service_provider"),
    identifier: str = typer.Option("", "--identifier", help="service_provider_identifier"),
    msisdn: str = typer.Option("", "--msisdn", help="provisioning number (auto-resolved if omitted)"),
) -> None:
    """Update an autopay subscription (PUT v1/auto-payment/{id}/update)."""
    with get_context().client() as client:
        service = AutoPayService(client)
        sub_msisdn = msisdn
        if not sub_msisdn:
            for sub in service.subscriptions().subscription:
                if sub.id == subscription_id:
                    sub_msisdn = sub.msisdn
                    break
        if not sub_msisdn:
            raise typer.BadParameter("could not resolve the provisioning number — pass --msisdn")
        if not provider or not identifier:
            for sub in service.subscriptions().subscription:
                if sub.id == subscription_id:
                    provider = provider or sub.service_provider
                    identifier = identifier or sub.service_provider_identifier
        if not provider or not identifier:
            raise typer.BadParameter("--provider/--identifier required (see `gpcli autopay methods`)")
        try:
            result = service.update(
                subscription_id,
                amount=amount,
                provisioning_msisdn=sub_msisdn,
                service_provider=provider,
                service_provider_identifier=identifier,
                frequency=frequency or None,
                start_from=date.fromisoformat(start_from) if start_from else None,
            )
        except MyGPError as err:
            console.print(f"[red]update failed:[/red] {err}")
            raise typer.Exit(1) from err
    ctx = get_context()
    if ctx.json_out:
        console.print_json(data=result)
        return
    if not render_action_response(result, title="Autopay updated", rows=[
        ("subscription", str(subscription_id)),
        ("amount", f"{amount} BDT"),
    ]):
        raise typer.Exit(1)
