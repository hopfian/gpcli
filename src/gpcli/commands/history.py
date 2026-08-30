"""`gpcli history` — prepaid usage history (CDR feed)."""

from __future__ import annotations

from datetime import date

import typer

from gpcli.context import get_context
from gpcli.render import console, render_usage_history
from gpcli.services.history import HistoryService, default_window

app = typer.Typer(help="Usage history: calls, internet, SMS, recharges, purchases")


@app.command()
def history(
    days: int = typer.Option(7, "--days", "-d", help="Window size ending today"),
    start: str = typer.Option("", "--start", help="Explicit start (yyyy-mm-dd)"),
    end: str = typer.Option("", "--end", help="Explicit end (yyyy-mm-dd)"),
    category: str = typer.Option(
        "", "--category", "-c",
        help="Filter to one category slug (voice-history, internet-history, recharge, …)",
    ),
    limit: int = typer.Option(25, "--limit", "-l", help="Max rows per category (0 = all)"),
) -> None:
    """Fetch CDR records: calls, data, SMS, recharges, packs, balance transfers."""
    ctx = get_context()
    window = (
        (date.fromisoformat(start), date.fromisoformat(end))
        if start and end
        else default_window(days)
    )
    if window[0] > window[1]:
        raise typer.BadParameter("start date is after end date")

    with ctx.client() as client:
        response = HistoryService(client).usage_history(*window)

    if ctx.json_out:
        console.print_json(data=response.model_dump(by_alias=True, exclude_none=True))
        return
    render_usage_history(response, (window[0].isoformat(), window[1].isoformat()),
                         category or None, limit)
