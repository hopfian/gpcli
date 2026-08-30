"""`gpcli bill` — itemized bills (postpaid PDF statements)."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import typer

from gpcli.context import get_context
from gpcli.render import console, render_bill_cycles
from gpcli.services.billing import BillService

app = typer.Typer(help="Itemized bills: bill cycles and PDF downloads (postpaid)")

_DEFAULT_OUT = Path("itemized_bill.pdf")


@app.command()
def cycles(
    anchor: str = typer.Option("", "--anchor", help="Override the bill anchor date (yyyy-mm-dd)"),
) -> None:
    """Show the 6 selectable bill cycles (anchor = last_billed_on, fallback today)."""
    ctx = get_context()
    anchor_date = date.fromisoformat(anchor) if anchor else None
    with ctx.client() as client:
        service = BillService(client)
        result = service.cycles(anchor_date)
        note = anchor if anchor else f"last_billed_on (fallback today: {service.anchor()})"
    if ctx.json_out:
        console.print_json(data=[c.model_dump() for c in result])
        return
    render_bill_cycles(result, note)


@app.command()
def itemized(
    cycle: int = typer.Option(1, "--cycle", "-n", help="Cycle number from `gpcli bill cycles` (1=latest)"),
    month: str = typer.Option("", "--month", help="Explicit invoice_month (yyyy-mm-dd)"),
    bill_type: str = typer.Option("local", "--type", help="local | roaming"),
    out: Path | None = typer.Option(None, "--out", "-o", help="Output PDF path (default: itemized_bill.pdf)"),
) -> None:
    """Download an itemized-bill PDF (POST /itemized-bill)."""
    ctx = get_context()
    if month:
        invoice_month = month
    else:
        if not 1 <= cycle <= 6:
            raise typer.BadParameter("--cycle must be 1..6")
        with ctx.client() as client:
            invoice_month = BillService(client).cycles()[cycle - 1].invoice_month

    with ctx.client() as client:
        path = BillService(client).itemized_pdf(invoice_month, bill_type, out or _DEFAULT_OUT)
    console.print(f"[green]saved[/green] {path} ({invoice_month}, {bill_type})")
