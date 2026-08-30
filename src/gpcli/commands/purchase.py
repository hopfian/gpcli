"""`gpcli purchase` / `gpcli recharge` commands."""

from __future__ import annotations

import webbrowser

import typer
from rich import box
from rich.table import Table

from gpcli.context import get_context
from gpcli.render import _fmt_panel_grid, console
from gpcli.services.purchase import PurchaseService

purchase_app = typer.Typer(help="Purchase packs: recharge-and-activate + legacy activation")
recharge_app = typer.Typer(help="Recharge: gateway URLs, wallet payment, offers, history")


def _open(url: str, flag: bool) -> None:
    if flag:
        webbrowser.open(url)
        console.print(f"[green]opened[/green] {url[:80]}...")
    else:
        console.print(url)


# ---------------------------------------------------------------- purchase


@purchase_app.command("pack")
def purchase_pack(
    ref: str = typer.Argument(..., help="Pack catalog id or keyword (see `gpcli packs`)"),
    msisdn: str = typer.Option("", "--msisdn", "-m", help="Recipient (default: session number)"),
    amount: int = typer.Option(
        0, "--amount", "-a",
        help="Recharge amount (default: the pack price)",
    ),
    otp: str = typer.Option("", "--otp", help="OTP if the pack requires one"),
    provider: str = typer.Option("", "--provider", help="service_provider (payment method id)"),
    identifier: str = typer.Option("", "--identifier", help="service_provider_identifier"),
    legacy: bool = typer.Option(
        False, "--legacy", help="Use POST /campaign-activate (free/PAYG-style packs)"
    ),
    yes: bool = typer.Option(False, "--yes", "-y"),
) -> None:
    """Buy a pack (POST recharge-and-activate; --legacy for campaign-activate)."""
    ctx = get_context()
    with get_context().client() as client:
        service = PurchaseService(client)
        pack = service.find_pack(ref)
        if pack is None:
            console.print(f"[red]pack not found:[/red] {ref!r} (see `gpcli packs`)")
            raise typer.Exit(1)
        if not yes and not typer.confirm(
            f"Purchase '{pack.title}' for {pack.price} BDT (keyword {pack.keyword})?"
        ):
            console.print("[dim]aborted[/dim]")
            raise typer.Exit(1)

        if legacy:
            result = service.purchase_legacy(pack, msisdn=msisdn)
            console.print_json(data=result)
            return

        response = service.purchase_pack(
            pack,
            msisdn=msisdn,
            otp=otp,
            recharge_amount=amount or None,
            provider=provider,
            identifier=identifier,
        )

    if ctx.json_out:
        console.print_json(data=response.model_dump(exclude_none=True))
        return

    if response.action_required:
        console.print("[yellow]action required[/yellow] — complete payment at:")
        console.print(response.data.payment_url)
        return
    if response.ok:
        direct = response.data.direct_recharge
        rows = [("status", response.data.status)]
        if direct:
            rows += [
                ("transaction", direct.recharge_transaction_id or "-"),
                ("amount", str(direct.rechargeAmount or "-")),
                ("provider", direct.serviceProvider or "-"),
            ]
        console.print(_fmt_panel_grid("Purchase successful", rows, border_style="green"))
        return
    console.print(f"[red]purchase failed[/red] status={response.data.status if response.data else 'none'}")
    raise typer.Exit(1)


# ---------------------------------------------------------------- recharge


@recharge_app.command()
def offers() -> None:
    """Recharge offers (GET recharge/offer)."""
    ctx = get_context()
    with get_context().client() as client:
        result = PurchaseService(client).recharge_offers()
    if ctx.json_out:
        console.print_json(data=[o.model_dump() for o in result])
        return
    if not result:
        console.print("[dim]no recharge offers[/dim]")
        return
    table = Table(box=box.SIMPLE_HEAVY, title=f"Recharge offers ({len(result)})")
    table.add_column("type", style="cyan")
    table.add_column("text")
    table.add_column("condition", style="dim")
    for offer in result:
        table.add_row(offer.type, offer.text[:60], offer.condition[:40])
    console.print(table)


@recharge_app.command()
def history() -> None:
    """Payment history (GET orders/v1/bill-payments)."""
    ctx = get_context()
    with get_context().client() as client:
        result = PurchaseService(client).payment_history()
    if ctx.json_out:
        console.print_json(data=result.model_dump())
        return
    if not result.result:
        console.print("[dim]no payment history[/dim]")
        return
    table = Table(box=box.SIMPLE_HEAVY, title=f"Payment history ({len(result.result)})")
    table.add_column("id", justify="right", style="cyan")
    table.add_column("type")
    table.add_column("amount", justify="right")
    table.add_column("date", style="dim")
    table.add_column("time", style="dim")
    for item in result.result:
        table.add_row(
            str(item.id or "-"), item.type, f"{item.amount:g}" if item.amount is not None else "-",
            item.date, item.time,
        )
    console.print(table)


@recharge_app.command()
def numbers() -> None:
    """Recently recharged numbers."""
    from gpcli.services.autopay import AutoPayService

    with get_context().client() as client:
        result = AutoPayService(client).recent_numbers()
    console.print_json(data=result)


@recharge_app.command()
def gateway(
    amount: int = typer.Argument(..., help="Recharge amount"),
    msisdn: str = typer.Option("", "--msisdn", "-m", help="Recipient (default: self)"),
    channel: str = typer.Option("", "--channel", help="Sub-channel override"),
    open_browser: bool = typer.Option(False, "--open", "-o", help="Open the payment URL"),
) -> None:
    """Get payment URLs for a recharge (POST /recharge -> payment WebView)."""
    ctx = get_context()
    with get_context().client() as client:
        result = PurchaseService(client).recharge_gateway(
            amount, msisdn=msisdn, channel=channel
        )
    if ctx.json_out:
        console.print_json(data=result.model_dump())
        return
    rows = [
        ("payment url", result.payment_url or "-"),
        ("bkash url", result.bkash_url or "-"),
        ("rocket url", result.rocket_url or "-"),
    ]
    console.print(_fmt_panel_grid(f"Recharge {amount} BDT — gateway URLs", rows))
    if open_browser and result.payment_url:
        webbrowser.open(result.payment_url)
        console.print("[green]opened[/green]")


@recharge_app.command()
def pay(
    amount: str = typer.Argument(..., help="Amount in BDT"),
    provider: str = typer.Option(..., "--provider", "-p", help="service_provider id (e.g. bkash)"),
    identifier: str = typer.Option(..., "--identifier", "-i", help="Provider identifier"),
    msisdn: str = typer.Option("", "--msisdn", "-m", help="Recipient (default: self)"),
    yes: bool = typer.Option(False, "--yes", "-y"),
) -> None:
    """Pay a recharge directly from a bound wallet (POST payment-gateway/payment)."""
    if not yes and not typer.confirm(f"Pay {amount} BDT via {provider}?"):
        console.print("[dim]aborted[/dim]")
        raise typer.Exit(1)
    ctx = get_context()
    with get_context().client() as client:
        result = PurchaseService(client).pay(
            amount, provider=provider, identifier=identifier, msisdn=msisdn
        )
    if ctx.json_out:
        console.print_json(data=result.model_dump())
        return
    if result.ok:
        console.print(f"[green]success[/green] {result.data.get('remarks', '')}".strip())
    else:
        console.print(f"[red]failed[/red] status={result.status} {result.data.get('payment_remarks', '')}")
        raise typer.Exit(1)
