"""`gpcli sim` — ownership certificate, doc type, biometric SIM lists."""

from __future__ import annotations

from pathlib import Path

import typer
from rich import box
from rich.table import Table

from gpcli.context import get_context
from gpcli.render import _fmt_panel_grid, console
from gpcli.services.sim import SimService

app = typer.Typer(help="SIM: ownership certificate, biometric SIM lists")


@app.command()
def certificate(
    out: Path | None = typer.Option(None, "--out", "-o", help="Save the certificate HTML to a file"),
) -> None:
    """SIM ownership certificate (GET v1/ownership-certificate; data is HTML)."""
    ctx = get_context()
    with ctx.client() as client:
        cert = SimService(client).certificate()
    if ctx.json_out:
        console.print_json(data={"status": cert.status, "data_length": len(cert.data)})
        return
    if not cert.ok:
        console.print(f"[red]failed[/red] status={cert.status} (42901 = daily limit reached)")
        raise typer.Exit(1)
    if out:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(cert.data, encoding="utf-8")
        console.print(f"[green]saved[/green] {out} ({len(cert.data)} bytes)")
    else:
        console.print(
            f"[green]certificate available[/green] "
            f"({len(cert.data)} bytes of HTML — use --out to save)"
        )


@app.command("doc-type")
def doc_type() -> None:
    """ID document type on file (GET v1/customers/get-id-document)."""
    ctx = get_context()
    with ctx.client() as client:
        result = SimService(client).doc_type()
    if ctx.json_out:
        console.print_json(data=result.model_dump())
        return
    console.print(_fmt_panel_grid("ID document", [
        ("doc type", result.doc_type or "-"),
        ("msisdn", str(result.data.get("msisdn", "-"))),
    ]))


@app.command("list")
def sim_list(last_four: str = typer.Argument(..., help="Last 4 digits of your NID/ID")) -> None:
    """Biometric SIM lists (active / bondho / other operators)."""
    ctx = get_context()
    with ctx.client() as client:
        result = SimService(client).sim_list(last_four)

    if ctx.json_out:
        console.print_json(data=result.model_dump())
        return

    def render_sims(title: str, sims: list) -> None:
        if not sims:
            return
        table = Table(box=box.SIMPLE_HEAVY, title=f"{title} ({len(sims)})")
        table.add_column("msisdn")
        table.add_column("operator")
        table.add_column("status", style="dim")
        for sim in sims:
            table.add_row(sim.masking or sim.msisdn, sim.operator or "-", sim.status or "-")
        console.print(table)

    render_sims("Active SIMs", result.active_sims)
    render_sims("Bondho (dormant) SIMs", result.bondho_sims)
    render_sims("Other operator SIMs", result.other_operator_sims)
    if not (result.active_sims or result.bondho_sims or result.other_operator_sims):
        console.print("[dim]no SIMs found for that ID[/dim]")
