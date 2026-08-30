"""`gpcli autorenew` — pack auto-renew status and toggling."""

from __future__ import annotations

import typer
from rich import box
from rich.table import Table

from gpcli.context import get_context
from gpcli.render import console
from gpcli.services.offers import OffersService

app = typer.Typer(help="Pack auto-renew: status and toggling")


@app.command("status")
def autorenew_status() -> None:
    """Pack auto-renew status (GET balance-status)."""
    ctx = get_context()
    with ctx.client() as client:
        result = OffersService(client).balance_status()
    if ctx.json_out:
        console.print_json(data={k: [i.model_dump() for i in v] for k, v in result.items()})
        return
    for kind, items in result.items():
        if not items:
            continue
        table = Table(box=box.SIMPLE_HEAVY, title=f"{kind} packs ({len(items)})")
        table.add_column("pack")
        table.add_column("shortcode", style="cyan")
        table.add_column("auto-renew")
        for item in items:
            auto = item.auto_renew_status
            if auto == 1:
                label = "[green]ON[/green]"
            elif auto is not None:
                label = "[yellow]OFF[/yellow]"
            else:
                label = "-"
            table.add_row(item.name[:30], item.product_short_code, label)
        console.print(table)
    if not any(result.values()):
        console.print("[dim]no active packs with auto-renew[/dim]")


@app.command()
def set_renew(
    product_short_code: str = typer.Argument(..., help="From `gpcli autorenew status`"),
    action: str = typer.Argument(..., help="on | off"),
) -> None:
    """Toggle a pack's auto-renew (POST internet-renew)."""
    action = action.lower()
    if action not in ("on", "off"):
        raise typer.BadParameter("action must be 'on' or 'off'")
    ctx = get_context()
    with ctx.client() as client:
        result = OffersService(client).set_auto_renew(product_short_code, action == "on")
    console.print_json(data=result)
