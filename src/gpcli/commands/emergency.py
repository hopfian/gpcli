"""`gpcli eb …` — emergency balance (balance loan)."""

from __future__ import annotations

import typer

from gpcli.context import get_context
from gpcli.render import console
from gpcli.services.emergency import EmergencyBalanceService

app = typer.Typer(help="Emergency balance: loan status, eligibility, availing")


@app.command()
def status() -> None:
    """Show eligible amount, active loan state and eligibility rules."""
    ctx = get_context()
    with ctx.client() as client:
        service = EmergencyBalanceService(client)
        eb = service.status()
        try:
            state = service.full_state()
        except Exception:
            state = {}

    if ctx.json_out:
        console.print_json(data={
            "eligible_amount": eb.model_dump(),
            "balance_state": state,
        })
        return

    from gpcli.render import _fmt_panel_grid  # local helper

    rows: list[tuple[str, str]] = [
        ("eligible amount", f"{eb.value:g} BDT"),
        ("validity", eb.validity or "-"),
    ]
    if state:
        info = EmergencyBalanceService.eligibility(state)
        nested = state.get("emergency_balance") or {}
        rows.append(("main balance", f"{info['main_balance']:g} BDT"))
        rows.append(("eligibility threshold", f"< {info['threshold']} BDT"))
        if info["active_loan"]:
            rows.append(("active loan total", f"{nested.get('total', 0):g} BDT"))
            rows.append(("due", f"{nested.get('due', 0):g} BDT"))
            rows.append(("remaining", str(nested.get("remaining", "")) or "-"))
            rows.append(("data loan", f"{nested.get('data_loan', 0):g} BDT"))
        rows.append(("eligible now", "yes" if info["eligible"] else "no"))
    console.print(_fmt_panel_grid("Emergency balance", rows))


@app.command()
def avail(yes: bool = typer.Option(False, "--yes", "-y", help="Skip the confirmation prompt")) -> None:
    """Request the emergency-balance loan (POST /emergency-balance, empty body)."""
    ctx = get_context()
    with ctx.client() as client:
        service = EmergencyBalanceService(client)
        eb = service.status()
        if not yes and not typer.confirm(f"Avail {eb.value:g} BDT emergency balance?"):
            console.print("[dim]aborted[/dim]")
            raise typer.Exit(1)
        response = service.avail()

    if ctx.json_out:
        console.print_json(data=response)
        return
    if EmergencyBalanceService.is_avail_success(response):
        console.print(f"[green]success[/green] {response.get('message', '')}".strip())
    else:
        console.print(f"[red]failed[/red] {response}")
        raise typer.Exit(1)
