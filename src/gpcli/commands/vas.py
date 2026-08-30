"""`gpcli vas` — value-added services: browse, subscribe, manage."""

from __future__ import annotations

import typer

from gpcli.context import get_context
from gpcli.render import (
    console,
    render_vas_categories,
    render_vas_items,
    render_vas_services,
)
from gpcli.services.catalog import CatalogService
from gpcli.services.offers import OffersService

app = typer.Typer(help="Value-added services (VAS)")


@app.command("categories")
def categories() -> None:
    """List VAS service categories."""
    ctx = get_context()
    with ctx.client() as client:
        result = CatalogService(client).vas_categories()
    if ctx.json_out:
        console.print_json(data=[c.model_dump() for c in result])
        return
    render_vas_categories(result)


@app.command("services")
def services(category_id: int = typer.Argument(..., help="Category ID (see `vas categories`)")) -> None:
    """List VAS services in a category."""
    ctx = get_context()
    with ctx.client() as client:
        result = CatalogService(client).vas_services(category_id)
    if ctx.json_out:
        console.print_json(data=[s.model_dump() for s in result])
        return
    render_vas_services(result, f"VAS services — category {category_id}")


@app.command("subscribed")
def subscribed() -> None:
    """List active VAS subscriptions."""
    ctx = get_context()
    with ctx.client() as client:
        result = CatalogService(client).vas_subscriptions()
    if ctx.json_out:
        console.print_json(data=result)
        return
    render_vas_items(result, "Active VAS subscriptions")


@app.command("history")
def history() -> None:
    """VAS transaction history."""
    ctx = get_context()
    with ctx.client() as client:
        result = CatalogService(client).vas_history()
    if ctx.json_out:
        console.print_json(data=result)
        return
    render_vas_items(result, "VAS history")


@app.command("activate")
def vas_activate(
    service_id: str = typer.Argument(..., help="service_id of the target service"),
    charge_code: str = typer.Argument("", help="charge_code (from `gpcli vas services`)"),
    partner: str = typer.Argument("", help="partner name"),
) -> None:
    """Activate a VAS service (set-status action=active)."""
    ctx = get_context()
    with ctx.client() as client:
        result = OffersService(client).vas_activate(
            {"service_id": service_id, "charge_code": charge_code, "partner": partner}
        )
    console.print_json(data=result)


@app.command("deactivate")
def vas_deactivate(
    service_id: str = typer.Argument(..., help="service_id (or type for mca-like services)"),
    charge_code: str = typer.Argument(""),
    partner: str = typer.Argument(""),
) -> None:
    """Deactivate a VAS service (set-status action=deactive)."""
    ctx = get_context()
    with ctx.client() as client:
        result = OffersService(client).vas_deactivate(
            {"service_id": service_id, "charge_code": charge_code, "partner": partner}
        )
    console.print_json(data=result)


@app.command("stop-all")
def vas_stop_all(yes: bool = typer.Option(False, "--yes", "-y")) -> None:
    """Deactivate EVERY active VAS subscription (action=deactive_all)."""
    ctx = get_context()
    with ctx.client() as client:
        services = CatalogService(client).vas_subscriptions()
        if not services:
            console.print("[dim]no active VAS subscriptions[/dim]")
            raise typer.Exit(0)
        if not yes:
            names = ", ".join(str(s.get("label_name") or s.get("type", "?")) for s in services[:8])
            if not typer.confirm(f"Deactivate ALL {len(services)} subscriptions ({names})?"):
                console.print("[dim]aborted[/dim]")
                raise typer.Exit(1)
        result = OffersService(client).vas_stop_all(services)
    console.print_json(data=result)
