"""`gpcli mca` — Missed Call Alert status and toggling."""

from __future__ import annotations

import typer

from gpcli.context import get_context
from gpcli.render import _fmt_panel_grid, console
from gpcli.services.mca import McaService

app = typer.Typer(help="Missed Call Alert: status, on/off")


@app.command("status")
def mca_status() -> None:
    """MCA status (GET mca)."""
    ctx = get_context()
    with ctx.client() as client:
        result = McaService(client).status()
    if ctx.json_out:
        console.print_json(data=result)
        return
    active = result.get("status") == "1"
    console.print(_fmt_panel_grid("Missed Call Alert", [
        ("status", "[green]ACTIVE[/green]" if active else "[yellow]OFF[/yellow]"),
        ("due date", result.get("due_date", "-")),
    ]))


@app.command()
def on(yes: bool = typer.Option(False, "--yes", "-y")) -> None:
    """Activate Missed Call Alert (POST mca {status: true})."""
    _mca_set(True, yes)


@app.command()
def off(yes: bool = typer.Option(False, "--yes", "-y")) -> None:
    """Deactivate Missed Call Alert (POST mca {status: false})."""
    _mca_set(False, yes)


def _mca_set(enabled: bool, yes: bool) -> None:
    state = "on" if enabled else "off"
    if not yes and not typer.confirm(f"Turn {state} Missed Call Alert?"):
        console.print("[dim]aborted[/dim]")
        raise typer.Exit(1)
    ctx = get_context()
    with ctx.client() as client:
        result = McaService(client).set(enabled)
    if ctx.json_out:
        console.print_json(data=result)
        return
    pending = str(result.get("status", "")).lower() == "pending"
    console.print(
        "[green]accepted (pending)[/green]"
        if pending else f"[red]failed[/red] {result.get('message', result)}"
    )
