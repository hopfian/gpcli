"""`gpcli offers` — gifts, gift cards, GA offers, pay-as-you-go."""

from __future__ import annotations

import typer
from rich import box
from rich.table import Table

from gpcli.context import get_context
from gpcli.render import _fmt_panel_grid, console, render_action_response
from gpcli.services.offers import OffersService

app = typer.Typer(help="Offers: gifts, gift cards, GA (new-SIM) offers, pay-as-you-go")


@app.command()
def gifts() -> None:
    """Received gifts (GET v1/customers/gifts)."""
    ctx = get_context()
    with ctx.client() as client:
        result = OffersService(client).gifts()
    if ctx.json_out:
        console.print_json(data=[g.model_dump() for g in result])
        return
    if not result:
        console.print("[dim]no received gifts[/dim]")
        return
    table = Table(box=box.SIMPLE_HEAVY, title=f"Received gifts ({len(result)})")
    table.add_column("title")
    table.add_column("from", style="dim")
    table.add_column("price", justify="right")
    table.add_column("validity", style="dim")
    for gift in result:
        table.add_row(gift.title[:32], gift.sender_name[:20], gift.price or "-", gift.validity or "-")
    console.print(table)


@app.command("gift-cards")
def gift_cards(
    offset: int = typer.Option(0, "--offset"),
    limit: int = typer.Option(20, "--limit"),
) -> None:
    """Gift card themes (GET gift-cards)."""
    ctx = get_context()
    with ctx.client() as client:
        result = OffersService(client).gift_cards(offset, limit)
    if ctx.json_out:
        console.print_json(data=result)
        return
    data = result.get("data") or {}
    content = data.get("content") or []
    if not content:
        console.print("[dim]no gift card themes[/dim]")
        return
    meta = data.get("meta") or {}
    table = Table(box=box.SIMPLE_HEAVY, title=f"Gift card themes ({len(content)})")
    if total := meta.get("total"):
        table.caption = f"{total} total"
    table.add_column("id", justify="right", style="cyan")
    table.add_column("title")
    table.add_column("theme", style="dim")
    table.add_column("image", style="dim")
    for card in content:
        table.add_row(
            str(card.get("id", "-")),
            str(card.get("title", "-")),
            str(card.get("theme", "-")),
            str(card.get("image", "-")),
        )
    console.print(table)


@app.command("ga")
def ga_offers() -> None:
    """GA (new-SIM / gross add-on) offer usage counters."""
    ctx = get_context()
    with ctx.client() as client:
        result = OffersService(client).ga_offer_details()
    if ctx.json_out:
        console.print_json(data={k: v.model_dump() for k, v in result.items()})
        return
    if not result:
        console.print("[dim]no GA offers[/dim]")
        return
    table = Table(box=box.SIMPLE_HEAVY, title=f"GA offers ({len(result)})")
    table.add_column("offer")
    table.add_column("remaining", justify="right")
    table.add_column("availed", justify="right")
    table.add_column("period", justify="right", style="dim")
    for name, info in result.items():
        table.add_row(
            name, str(info.remaining),
            str(info.is_current_month_availed), str(info.total_campaign_period),
        )
    console.print(table)


@app.command("payg-status")
def payg_status() -> None:
    """Pay-as-you-go internet status (from GET balance)."""
    ctx = get_context()
    with ctx.client() as client:
        service = OffersService(client)
        status = service.payg_status()
        on_pack, off_pack = service.payg_packs()
    if ctx.json_out:
        console.print_json(data={
            "status": status,
            "on_pack": on_pack.id if on_pack else None,
            "off_pack": off_pack.id if off_pack else None,
        })
        return
    console.print(_fmt_panel_grid("Pay-as-you-go", [
        ("status", status or "unknown"),
        ("toggle available", "yes" if (on_pack and off_pack) else "no (packs missing)"),
    ]))


@app.command("payg-toggle")
def payg_toggle(
    action: str = typer.Argument(..., help="on | off"),
    yes: bool = typer.Option(False, "--yes", "-y"),
) -> None:
    """Toggle PAYG internet — purchases the pay_go_on/pay_go_off catalog pack."""
    action = action.lower()
    if action not in ("on", "off"):
        raise typer.BadParameter("action must be 'on' or 'off'")
    if not yes and not typer.confirm(f"Turn {action} pay-as-you-go internet?"):
        console.print("[dim]aborted[/dim]")
        raise typer.Exit(1)
    ctx = get_context()
    with ctx.client() as client:
        result = OffersService(client).payg_toggle(action == "on")
    if ctx.json_out:
        console.print_json(data=result)
        return
    if not render_action_response(result, title=f"PAYG internet {action}", rows=[
        ("action", action),
    ]):
        raise typer.Exit(1)
