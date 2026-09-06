"""`gpcli netcare` — network complaints: list, detail, form, submit."""

from __future__ import annotations

import json

import typer
from rich import box
from rich.table import Table

from gpcli.context import get_context
from gpcli.render import _fmt_panel_grid, console, render_action_response
from gpcli.services.netcare import NetworkComplainService

app = typer.Typer(help="Network complaints: list, detail, questionnaires, submit")


@app.command("list")
def netcare_list() -> None:
    """My network complaints (GET network-complain-feedbacks)."""
    ctx = get_context()
    with ctx.client() as client:
        result = NetworkComplainService(client).feedbacks()
    if ctx.json_out:
        console.print_json(data=result)
        return
    items = result.get("feedbacks", []) if isinstance(result, dict) else []
    if not items:
        console.print("[dim]no complaints submitted[/dim]")
        return
    table = Table(box=box.SIMPLE_HEAVY, title=f"Complaints ({len(items)})")
    table.add_column("id", justify="right", style="cyan")
    table.add_column("status")
    table.add_column("created", style="dim")
    for item in items:
        created = str(item.get("created_at", "-"))[:19]
        table.add_row(str(item.get("id", "-")), str(item.get("status", "-")), created)
    console.print(table)


@app.command()
def detail(feedback_id: str = typer.Argument(...)) -> None:
    """Complaint detail with status timeline."""
    ctx = get_context()
    with ctx.client() as client:
        result = NetworkComplainService(client).feedback(feedback_id)
    if ctx.json_out:
        console.print_json(data=result)
        return
    if not isinstance(result, dict) or not result:
        console.print("[dim]no complaint detail[/dim]")
        return
    rows = []
    for key, value in result.items():
        if isinstance(value, (dict, list)):
            summary = f"{len(value)} entries" if value else "-"
            rows.append((key, summary))
        else:
            rows.append((key, "-" if value in (None, "") else str(value)[:60]))
    console.print(_fmt_panel_grid(f"Complaint {feedback_id}", rows))
    console.print("[dim]full detail: gpcli --json netcare detail[/dim]")


@app.command()
def questionnaires() -> None:
    """The complaint form's questions and choices."""
    ctx = get_context()
    with ctx.client() as client:
        result = NetworkComplainService(client).questionnaires()
    if ctx.json_out:
        console.print_json(data=result)
        return
    questions = result.get("questions", []) if isinstance(result, dict) else []
    for question in questions:
        if question.get("itemType") == "header":
            console.print(f"\n[bold]{question.get('title', '')}[/bold]")
            continue
        required = " [red]*[/red]" if question.get("required") else ""
        qid = question.get("id")
        console.print(f"  [cyan]id={qid}[/cyan] {question.get('title', '')}{required}")
        info = f"    type={question.get('type')}"
        if question.get("source"):
            info += f" source={question['source']}"
        console.print(info, style="dim")
        for choice in question.get("choices", []) or []:
            console.print(f"      - {choice.get('key')} = {choice.get('value')}", style="dim")
    settings = result.get("settings", {}) if isinstance(result, dict) else {}
    if settings.get("top_info"):
        console.print(f"\n[dim]{settings['top_info']}[/dim]")


@app.command()
def submit(
    answers: str = typer.Argument(
        ..., help='JSON list: [{"id": 1, "type": "textarea", "feedback": "..."}]'
    ),
    meta: str = typer.Option("", "--meta", help="Optional meta JSON (lat/long/rnc/lac/cid...)"),
) -> None:
    """Submit a network complaint (questions from `gpcli netcare questionnaires`)."""
    try:
        parsed = json.loads(answers)
    except json.JSONDecodeError as err:
        raise typer.BadParameter(f"answers is not valid JSON: {err}") from err
    if not isinstance(parsed, list) or not parsed:
        raise typer.BadParameter("answers must be a non-empty JSON list")
    meta_obj = None
    if meta:
        try:
            meta_obj = json.loads(meta)
        except json.JSONDecodeError as err:
            raise typer.BadParameter(f"meta is not valid JSON: {err}") from err

    ctx = get_context()
    with ctx.client() as client:
        result = NetworkComplainService(client).submit(parsed, meta=meta_obj)
    if ctx.json_out:
        console.print_json(data=result)
        return
    if not render_action_response(result, title="Complaint submitted", rows=[
        ("answers", str(len(parsed))),
    ]):
        raise typer.Exit(1)
