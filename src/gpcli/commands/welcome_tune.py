"""`gpcli wt` — Welcome Tune status, search, activation."""

from __future__ import annotations

import typer
from rich import box
from rich.table import Table

from gpcli.context import get_context
from gpcli.render import _fmt_panel_grid, console, render_action_response
from gpcli.services.welcome_tune import WelcomeTuneService

app = typer.Typer(help="Welcome Tune: status, list, search, activate, deactivate")


@app.command("status")
def wt_status() -> None:
    """Welcome Tune status (GET wt/status)."""
    ctx = get_context()
    with ctx.client() as client:
        result = WelcomeTuneService(client).status()
    if ctx.json_out:
        console.print_json(data=result)
        return
    try:
        active = int(result.get("status", 0)) == 1
    except (TypeError, ValueError):
        active = False
    console.print(_fmt_panel_grid("Welcome Tune", [
        ("status", "[green]ACTIVE[/green]" if active else "[yellow]OFF[/yellow]"),
    ]))


def _render_tunes(tunes, title: str) -> None:
    if not tunes:
        console.print(f"[dim]{title}: none[/dim]")
        return
    table = Table(box=box.SIMPLE_HEAVY, title=f"{title} ({len(tunes)})")
    table.add_column("code", style="cyan")
    table.add_column("tune")
    table.add_column("artist", style="dim")
    table.add_column("price", justify="right")
    table.add_column("valid", justify="right", style="dim")
    for tune in tunes[:40]:
        table.add_row(
            tune.ToneCode,
            tune.ToneName[:38],
            tune.SingerName[:20],
            f"{tune.Price:g}" if tune.Price is not None else "-",
            str(tune.ToneValidDay or "-"),
        )
    console.print(table)


@app.command("list")
def wt_list() -> None:
    """My tunes (GET wt/list)."""
    ctx = get_context()
    with ctx.client() as client:
        result = WelcomeTuneService(client).list()
    if ctx.json_out:
        console.print_json(data=[t.model_dump(exclude_none=True) for t in result])
        return
    _render_tunes(result, "My welcome tunes")


@app.command()
def search(keyword: str = typer.Argument(..., help="Search text")) -> None:
    """Search tunes (POST wt/search)."""
    ctx = get_context()
    with ctx.client() as client:
        result = WelcomeTuneService(client).search(keyword)
    if ctx.json_out:
        console.print_json(data=[t.model_dump(exclude_none=True) for t in result])
        return
    _render_tunes(result, f"Search: {keyword!r}")


@app.command()
def activate(
    tone_code: str = typer.Argument(...),
    yes: bool = typer.Option(False, "--yes", "-y"),
) -> None:
    """Set an owned tune as active (v2 wt/activate)."""
    if not yes and not typer.confirm(f"Activate tune {tone_code}?"):
        console.print("[dim]aborted[/dim]")
        raise typer.Exit(1)
    ctx = get_context()
    with ctx.client() as client:
        result = WelcomeTuneService(client).activate(tone_code)
    if ctx.json_out:
        console.print_json(data=result)
        return
    if not render_action_response(result, title="Welcome Tune activate", rows=[
        ("tone code", tone_code),
    ]):
        raise typer.Exit(1)


@app.command()
def deactivate() -> None:
    """Deactivate Welcome Tune (v2 wt/deactivate)."""
    ctx = get_context()
    with ctx.client() as client:
        result = WelcomeTuneService(client).deactivate()
    if ctx.json_out:
        console.print_json(data=result)
        return
    if not render_action_response(result, title="Welcome Tune deactivate"):
        raise typer.Exit(1)
