"""`gpcli roaming …` — roaming status, packs (Taka/USD), history, portals."""

from __future__ import annotations

import webbrowser
from datetime import date

import typer
from rich import box
from rich.table import Table

from gpcli.context import get_context
from gpcli.render import _fmt_panel_grid, console, render_packs
from gpcli.services.history import default_window
from gpcli.services.roaming import (
    ROAMING_MANAGE_URL,
    ROAMING_RATES_URL,
    ROAMING_TIPS_URL,
    RoamingService,
)

app = typer.Typer(help="Roaming: status, packs (Taka/USD), usage history, rates & tips portals")


def _portal(url: str, open_browser: bool, title: str) -> None:
    if open_browser:
        webbrowser.open(url)
        console.print(f"[green]opened[/green] {url}")
    else:
        console.print(_fmt_panel_grid(title, [("url", url)]))


@app.command()
def status() -> None:
    """Roaming status (GET balance -> is_roaming)."""
    ctx = get_context()
    with ctx.client() as client:
        info = RoamingService(client).status()
    if ctx.json_out:
        console.print_json(data=info)
        return
    is_on = info["is_roaming"]
    rows = [
        ("roaming", "[green]ON[/green]" if is_on else "[yellow]OFF[/yellow]"),
        ("account type", str(info.get("type") or "-")),
        ("main balance", f"{info.get('balance') or 0:g} BDT"),
        ("next step", "offers are live" if is_on else "activate via `gpcli roaming manage`"),
    ]
    console.print(_fmt_panel_grid("Roaming status", rows))


@app.command()
def packs(
    usd: bool = typer.Option(False, "--usd", help="USD-priced packs (default: Taka)"),
    limit: int = typer.Option(50, "--limit", "-l"),
    search: str = typer.Option("", "--search", "-s"),
) -> None:
    """Roaming packs — Taka (mobile balance) or USD."""
    ctx = get_context()
    with ctx.client() as client:
        result = RoamingService(client).packs(usd=usd)
    if search:
        needle = search.lower()
        result = [p for p in result if needle in p.title.lower() or needle in p.keyword.lower()]
    if limit > 0:
        result = result[:limit]
    if ctx.json_out:
        console.print_json(
            data=[p.model_dump(exclude={"additional_data"}, exclude_none=True) for p in result]
        )
        return
    render_packs(result, f"roaming packs ({'USD' if usd else 'Taka'})")


@app.command()
def history(
    days: int = typer.Option(30, "--days", "-d", help="Window size ending today"),
    start: str = typer.Option("", "--start"),
    end: str = typer.Option("", "--end"),
    limit: int = typer.Option(25, "--limit", "-l", help="Max rows (0 = all)"),
) -> None:
    """Roaming usage records (CDR items flagged as roaming)."""
    ctx = get_context()
    window = (
        (date.fromisoformat(start), date.fromisoformat(end))
        if start and end
        else default_window(days)
    )
    with ctx.client() as client:
        service = RoamingService(client)
        response = service.usage(*window)
        items = service.roaming_items(response)
        menus = service.roaming_menus(response)

    if ctx.json_out:
        console.print_json(data={
            "window": [window[0].isoformat(), window[1].isoformat()],
            "roaming_menus": menus,
            "items": [i.model_dump(exclude_none=True) for i in items],
        })
        return

    if menus:
        titles = ", ".join(
            str(entry.get("title", slug)) for slug, entry in menus.items()
            if isinstance(entry, dict)
        )
        console.print(f"[dim]roaming categories:[/dim] {titles}")

    if not items:
        console.print(f"[dim]no roaming usage {window[0]} .. {window[1]}[/dim]")
        return
    table = Table(
        box=box.SIMPLE_HEAVY,
        title=f"Roaming usage - {len(items)} records ({window[0]} .. {window[1]})",
    )
    table.add_column("date", style="dim")
    table.add_column("time", style="dim")
    table.add_column("party")
    table.add_column("type")
    table.add_column("usage", justify="right")
    table.add_column("charge", justify="right", style="green")
    for item in sorted(items, key=lambda i: i.timestamp, reverse=True)[: limit or None]:
        table.add_row(
            item.usage_date[:10],
            item.usage_time[:9],
            (item.b_party or item.cdr_type or "-")[:18],
            item.cdr_type[:12] or "-",
            (item.consumed_usage or "-")[:14],
            item.charge,
        )
    console.print(table)


@app.command()
def manage(open_browser: bool = typer.Option(False, "--open", "-o", help="Open in a browser")) -> None:
    """Manage roaming (activation/deactivation happens in GP's web portal)."""
    _portal(ROAMING_MANAGE_URL, open_browser, "Roaming management portal")


@app.command()
def rates(open_browser: bool = typer.Option(False, "--open", "-o", help="Open in a browser")) -> None:
    """Country-wise roaming rates (web portal)."""
    _portal(ROAMING_RATES_URL, open_browser, "Roaming rates")


@app.command()
def tips(open_browser: bool = typer.Option(False, "--open", "-o", help="Open in a browser")) -> None:
    """Roaming tips and country/operator lists (web portal)."""
    _portal(ROAMING_TIPS_URL, open_browser, "Roaming tips")
