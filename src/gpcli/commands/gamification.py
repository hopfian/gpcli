"""`gpcli streak …` — daily-login streak, milestone rewards, GP points."""

from __future__ import annotations

import typer

from gpcli.context import get_context
from gpcli.render import console
from gpcli.services.gamification import GamificationService

app = typer.Typer(help="Daily-login streak rewards and GP points")


@app.command()
def status() -> None:
    """Show the current streak and milestone rewards."""
    ctx = get_context()
    with ctx.client() as client:
        info = GamificationService(client).streak()

    if ctx.json_out:
        console.print_json(data=info.model_dump(exclude_none=True))
        return

    from rich import box
    from rich.table import Table

    from gpcli.render import _fmt_panel_grid

    total = info.settings.total_streak if info.settings else None
    rows = [
        ("current streak", f"{info.current_streak} days"),
        ("total streak", f"{total} days" if total else "-"),
        ("claimable now", str(len(info.claimable)) if info.claimable else "none"),
    ]
    if info.settings and info.settings.gamification_header:
        header = info.settings.gamification_header
        if header.subtitle:
            rows.append(("program", header.subtitle[:40]))
    console.print(_fmt_panel_grid("Daily login streak", rows))

    # runtime state (milestone[]) joined with reward config (settings.milestones[])
    config = {m.id: m for m in (info.settings.milestones if info.settings else []) if m.id}
    table = Table(box=box.SIMPLE_HEAVY, title=f"Milestones ({len(info.milestone)})")
    table.add_column("id", justify="right", style="cyan")
    table.add_column("days", justify="right")
    table.add_column("reward", justify="right", style="green")
    table.add_column("status")
    for milestone in info.milestone:
        cfg = config.get(milestone.id)
        table.add_row(
            str(milestone.id if milestone.id is not None else "-"),
            str(cfg.milestone_days if cfg and cfg.milestone_days else "-"),
            f"{cfg.milestone_reward} pts" if cfg and cfg.milestone_reward else "-",
            milestone.status_label,
        )
    console.print(table)


@app.command()
def claim(
    milestone_id: int = typer.Option(
        0, "--milestone-id", "-m",
        help="Milestone to claim (default: the first claimable one)",
    ),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip the confirmation prompt"),
) -> None:
    """Claim a daily-login milestone reward (POST daily-login/claim)."""
    ctx = get_context()
    with ctx.client() as client:
        service = GamificationService(client)
        info = service.streak()
        claimable = info.claimable
        if milestone_id == 0:
            if not claimable:
                console.print("[dim]nothing claimable today[/dim]")
                raise typer.Exit(1)
            milestone_id = claimable[0].id
            target = claimable[0]
        else:
            target = next((m for m in info.milestone if m.id == milestone_id), None)
            if target is None:
                raise typer.BadParameter(f"milestone {milestone_id} not found")
            if target.status != 2:
                console.print(
                    f"[red]milestone {milestone_id} is not claimable "
                    f"({target.status_label})[/red]"
                )
                raise typer.Exit(1)

        reward = target.milestone_reward or 0
        if not yes and not typer.confirm(f"Claim {reward} GP points (milestone {milestone_id})?"):
            console.print("[dim]aborted[/dim]")
            raise typer.Exit(1)
        result = service.claim(milestone_id)

    if ctx.json_out:
        console.print_json(data=result.model_dump(exclude_none=True))
        return
    if result.ok:
        console.print(f"[green]{result.status}[/green] {result.message}".strip())
    else:
        console.print(f"[red]failed[/red] {result.message or result.status}".strip())
        raise typer.Exit(1)


@app.command()
def points() -> None:
    """GP point balance and loyalty status (GET loyalty/balance)."""
    ctx = get_context()
    with ctx.client() as client:
        result = GamificationService(client).points()

    if ctx.json_out:
        console.print_json(data=result.model_dump())
        return
    from gpcli.render import _fmt_panel_grid

    console.print(_fmt_panel_grid("GP points", [
        ("point balance", str(result.point_balance)),
        ("loyalty status", result.loyalty_label),
    ]))
