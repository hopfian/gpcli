"""`gpcli purchase` / `gpcli recharge` commands."""

from __future__ import annotations

import webbrowser

import typer
from rich import box
from rich.table import Table

from gpcli.context import get_context
from gpcli.render import _fmt_panel_grid, console
from gpcli.services.autopay import AutoPayService
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
    with ctx.client() as client:
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
            if ctx.json_out:
                console.print_json(data=result)
                return
            status = str(result.get("status", "")) if isinstance(result, dict) else ""
            ok = status.lower() in ("success", "pending")
            rows = [("status", status or "-")]
            for key, label in (("ticketid", "ticket"), ("remarks", "remarks"),
                               ("message", "message")):
                value = result.get(key) if isinstance(result, dict) else None
                if value:
                    rows.append((label, str(value)[:60]))
            console.print(_fmt_panel_grid(
                "Purchase submitted" if ok else "Purchase response", rows,
                border_style="green" if ok else "red",
            ))
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
    with ctx.client() as client:
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
    with ctx.client() as client:
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
    ctx = get_context()
    with ctx.client() as client:
        result = AutoPayService(client).recent_numbers()
    console.print_json(data=result)


@recharge_app.command()
def methods() -> None:
    """Bindable payment methods (bkash, nagad, card) — GET v2/payment-methods."""
    ctx = get_context()
    with ctx.client() as client:
        result = PurchaseService(client).payment_methods()
    if ctx.json_out:
        console.print_json(data=[m.model_dump(exclude_none=True) for m in result])
        return
    if not result:
        console.print("[dim]no payment methods available[/dim]")
        return
    table = Table(box=box.SIMPLE_HEAVY, title=f"Payment methods ({len(result)})")
    table.add_column("id", style="cyan")
    table.add_column("name")
    table.add_column("multi-bind", justify="center")
    table.add_column("active", justify="center")
    for method in result:
        table.add_row(
            method.payment_method_id,
            method.name,
            "yes" if method.multiple_bind_support else "no",
            "yes" if method.is_active else "no",
        )
    console.print(table)


@recharge_app.command()
def saved() -> None:
    """Bound (saved) payment methods with their one-tap identifiers — from GET /balance."""
    ctx = get_context()
    with ctx.client() as client:
        result = PurchaseService(client).bound_payment_methods()
    if ctx.json_out:
        console.print_json(data=[m.model_dump(exclude_none=True) for m in result])
        return
    if not result:
        console.print("[dim]no bound payment methods — run `recharge bind <id>`[/dim]")
        return
    table = Table(box=box.SIMPLE_HEAVY, title=f"Bound payment methods ({len(result)})")
    table.add_column("type", style="cyan")
    table.add_column("wallet")
    table.add_column("preferred", justify="center")
    table.add_column("identifier")
    for method in result:
        table.add_row(
            method.type,
            method.wallet_no or "-",
            "[green]yes[/green]" if method.is_preferred else "",
            method.identifier,
        )
    console.print(table)


@recharge_app.command()
def bind(
    method_id: str = typer.Argument(..., help="Payment method id (see `recharge methods`)"),
    open_browser: bool = typer.Option(False, "--open", "-o", help="Open the binding URL"),
) -> None:
    """Start binding a payment method — prints the provider's auth URL."""
    ctx = get_context()
    with ctx.client() as client:
        result = PurchaseService(client).bind_payment_method(method_id)
    if ctx.json_out:
        console.print_json(data=result.model_dump(exclude_none=True))
        return
    url = result.url
    if not url:
        console.print(f"[red]bind failed[/red] status={result.status} code={result.code}")
        raise typer.Exit(1)
    console.print(
        f"[green]binding URL issued[/green] — authenticate with {method_id} there; "
        "the method becomes usable once the provider flow completes"
    )
    _open(url, open_browser)


@recharge_app.command()
def unbind(
    method_id: str = typer.Argument(..., help="Payment method id (see `recharge methods`)"),
    identifier: str = typer.Option(
        "", "--identifier", "-i",
        help="Identifier token (default: auto-resolve from the bound methods)",
    ),
    yes: bool = typer.Option(False, "--yes", "-y"),
) -> None:
    """Remove a bound payment method (form POST with identifier)."""
    ctx = get_context()
    with ctx.client() as client:
        service = PurchaseService(client)
        resolved = identifier or ""
        if not resolved:
            bound = service.resolve_identifier(method_id)
            if bound is not None:
                resolved = bound.identifier
        if not resolved:
            console.print(f"[red]no bound {method_id} method found[/red] — nothing to unbind")
            raise typer.Exit(1)
        if not yes and not typer.confirm(f"Unbind {method_id} ({resolved})?"):
            console.print("[dim]aborted[/dim]")
            raise typer.Exit(1)
        result = service.unbind_payment_method(method_id, resolved)
    console.print_json(data=result)


@recharge_app.command()
def gateway(
    amount: int = typer.Argument(..., help="Recharge amount"),
    msisdn: str = typer.Option("", "--msisdn", "-m", help="Recipient (default: self)"),
    channel: str = typer.Option("", "--channel", help="Sub-channel override"),
    open_browser: bool = typer.Option(False, "--open", "-o", help="Open the payment page"),
) -> None:
    """Single-use recharge: one-time payment session (pick any MFS on the page)."""
    ctx = get_context()
    with ctx.client() as client:
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
    if result.transaction_id:
        rows.append(("transaction", result.transaction_id))
    if result.campaign_code:
        rows.append(("campaign", result.campaign_code))
    console.print(_fmt_panel_grid(f"Recharge {amount} BDT — single-use payment session", rows))
    if open_browser and result.payment_url:
        webbrowser.open(result.payment_url)
        console.print("[green]opened[/green]")
    else:
        console.print(
            "[dim]open the payment url and pick your method (bKash / Nagad / card / gPay / rocket) — "
            "one-time payment, no method is saved[/dim]"
        )


@recharge_app.command()
def pay(
    amount: str = typer.Argument(..., help="Amount in BDT"),
    provider: str = typer.Option(
        ..., "--provider", "-p",
        help="Bound method id (bkash, nagad, card - see `recharge saved`)",
    ),
    identifier: str = typer.Option(
        "", "--identifier", "-i",
        help="Identifier token (default: auto-resolve from the bound methods)",
    ),
    msisdn: str = typer.Option("", "--msisdn", "-m", help="Recipient (default: self)"),
    yes: bool = typer.Option(False, "--yes", "-y"),
) -> None:
    """One-tap instant recharge from a BOUND method (POST payment-gateway/payment).

    No provider auth, no browser, no OTP — the bound wallet is charged
    directly. Requires `recharge bind <id>` once. For a one-time payment
    without binding, use `recharge gateway <amount>` instead.
    """
    ctx = get_context()
    with ctx.client() as client:
        service = PurchaseService(client)
        resolved = identifier
        wallet = ""
        if not resolved:
            bound = service.resolve_identifier(provider)
            if bound is not None:
                resolved = bound.identifier
                wallet = bound.wallet_no
        if not resolved:
            console.print(
                f"[red]no bound {provider} method[/red] — run `gpcli recharge bind {provider}` first, "
                "or use `recharge gateway` for a one-time payment"
            )
            raise typer.Exit(1)
        target = f" ({wallet})" if wallet else ""
        if not yes and not typer.confirm(f"Pay {amount} BDT via {provider}{target}?"):
            console.print("[dim]aborted[/dim]")
            raise typer.Exit(1)
        result = service.pay(
            amount, provider=provider, identifier=resolved, msisdn=msisdn
        )
    if ctx.json_out:
        console.print_json(data=result.model_dump())
        return
    if result.ok:
        console.print(f"[green]success[/green] {result.data.get('remarks', '')}".strip())
    else:
        console.print(f"[red]failed[/red] status={result.status} {result.data.get('payment_remarks', '')}")
        raise typer.Exit(1)
