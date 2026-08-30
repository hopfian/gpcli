"""`gpcli flexiplan` — catalog display and bundle price quoting."""

from __future__ import annotations

import typer

from gpcli.context import get_context
from gpcli.render import console, render_flexiplan, render_flexiplan_quote
from gpcli.services.catalog import CatalogService, quote_flexiplan

app = typer.Typer(help="Flexiplan catalog and price quoting")


@app.command("show")
def show() -> None:
    """Show the flexiplan catalog (options, VAT, MCA pricing)."""
    ctx = get_context()
    with ctx.client() as client:
        catalog = CatalogService(client).flexiplans()
    if ctx.json_out:
        console.print_json(data=catalog.model_dump(by_alias=True, exclude_none=True))
        return
    render_flexiplan(catalog)


@app.command("quote")
def quote(
    days: int = typer.Option(30, "--days", "-d", help="Validity in days"),
    voice: int = typer.Option(0, "--voice", "-v", help="Voice minutes"),
    data: int = typer.Option(0, "--data", help="Data in MB (e.g. 30720 = 30 GB)"),
    data4g: int = typer.Option(0, "--4g", help="4G data in MB"),
    bioscope: int = typer.Option(0, "--bioscope", "-b", help="Bioscope data in MB"),
    sms: int = typer.Option(0, "--sms", "-s", help="SMS count"),
    mca: bool = typer.Option(False, "--mca", help="Include missed-call-alert pricing note"),
) -> None:
    """Look up the price of a bundle combination."""
    ctx = get_context()
    with ctx.client() as client:
        catalog = CatalogService(client).flexiplans()
        key, price = quote_flexiplan(
            catalog,
            days=days, voice=voice, data_mb=data, data4g_mb=data4g,
            bioscope_mb=bioscope, sms=sms,
        )
    if ctx.json_out:
        console.print_json(data={"bundle_key": key, "price": price.model_dump()})
        return
    render_flexiplan_quote(key, price, mca=mca)
