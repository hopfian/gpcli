"""`gpcli fnf` — Friends & Family management."""

from __future__ import annotations

import typer
from rich import box
from rich.table import Table

from gpcli.context import get_context
from gpcli.render import _fmt_panel_grid, console
from gpcli.services.fnf import FnfService

app = typer.Typer(help="Friends & Family: list, add, remove")


@app.command("list")
def fnf_list() -> None:
    """List FnF numbers with quota info."""
    ctx = get_context()
    with ctx.client() as client:
        result = FnfService(client).list()
    if ctx.json_out:
        console.print_json(data=result.model_dump())
        return

    info = result.info
    if info:
        console.print(_fmt_panel_grid("FnF quota", [
            ("normal", f"{info.usednormalFnF}/{info.totalnormalFnF}"),
            ("super", f"{info.usedsuperFnF}/{info.totalsuperFnF}"),
        ]))
    for title, items in (("Normal FnF", result.normal_fnf), ("Super FnF", result.super_fnf)):
        if not items:
            continue
        table = Table(box=box.SIMPLE_HEAVY, title=f"{title} ({len(items)})")
        table.add_column("number", style="cyan")
        table.add_column("requested", style="dim")
        table.add_column("changed", style="dim")
        for item in items:
            table.add_row(item.fnf, item.requestdate or "-", item.changedate or "-")
        console.print(table)
    if not (result.normal_fnf or result.super_fnf):
        console.print("[dim]no FnF numbers added[/dim]")


@app.command()
def add(
    msisdn: str = typer.Argument(..., help="Number to add"),
    super_fnf: bool = typer.Option(False, "--super", help="Add as Super FnF"),
) -> None:
    """Add an FnF number (POST fnf-add)."""
    ctx = get_context()
    with ctx.client() as client:
        result = FnfService(client).add(msisdn, super_fnf=super_fnf)
    console.print_json(data=result)


@app.command()
def remove(
    msisdn: str = typer.Argument(..., help="Number to remove"),
    super_fnf: bool = typer.Option(False, "--super", help="Remove from Super FnF"),
) -> None:
    """Remove an FnF number (POST fnf-delete; 30-day lock after change applies)."""
    ctx = get_context()
    with ctx.client() as client:
        result = FnfService(client).remove(msisdn, super_fnf=super_fnf)
    console.print_json(data=result)
