"""`gpcli partners` — partner tokens and streaming content."""

from __future__ import annotations

from typing import Any

import typer
from rich import box
from rich.table import Table

from gpcli.context import get_context
from gpcli.render import _fmt_panel_grid, console, plural
from gpcli.services.partners import PartnerService

app = typer.Typer(help="Partner tokens: ibadah, win, chatbot, DRM, Zee5, content search")


@app.command("deen")
def deen() -> None:
    """Ibadah (Islamic services) SDK token."""
    ctx = get_context()
    with ctx.client() as client:
        result = PartnerService(client).deen_token()
    if ctx.json_out:
        console.print_json(data=result.model_dump())
        return
    console.print(_fmt_panel_grid("Ibadah (deen) token", [
        ("token", result.token[:24] + "..." if result.token else "-"),
        ("url", result.url or "-"),
        ("type", result.type or "-"),
    ]))


@app.command("win")
def win() -> None:
    """WIN partner token."""
    ctx = get_context()
    with ctx.client() as client:
        result = PartnerService(client).win_token()
    if ctx.json_out:
        console.print_json(data=result.model_dump())
        return
    console.print(_fmt_panel_grid("WIN token", [
        ("token", result.token[:24] + "..." if result.token else "-"),
        ("url", result.url or "-"),
        ("type", result.type or "-"),
    ]))


@app.command("chatbot")
def chatbot() -> None:
    """Live-chat chatbot partner token."""
    ctx = get_context()
    with ctx.client() as client:
        result = PartnerService(client).chatbot_token()
    if ctx.json_out:
        console.print_json(data=result.model_dump())
        return
    console.print(_fmt_panel_grid("Chatbot token", [
        ("token", result.token[:24] + "..." if result.token else "-"),
        ("url", result.url or "-"),
        ("type", result.type or "-"),
    ]))


@app.command("drm")
def drm(
    partner: str = typer.Argument(..., help="lionsgate | chorki | zee5 | hoichoi | ..."),
    pid: str = typer.Argument(..., help="Content/partner id"),
) -> None:
    """Widevine DRM token for a streaming partner."""
    ctx = get_context()
    with ctx.client() as client:
        token = PartnerService(client).drm_token(partner, pid)
    if ctx.json_out:
        console.print_json(data={"partner": partner, "token": token})
        return
    shown = token[:32] + "..." if token else "-"
    console.print(_fmt_panel_grid("DRM token", [("partner", partner), ("token", shown)]))


@app.command("zee5")
def zee5() -> None:
    """Zee5 token + content catalog."""
    ctx = get_context()
    with ctx.client() as client:
        service = PartnerService(client)
        token = service.zee5_token()
        contents = service.zee5_contents()
    if ctx.json_out:
        console.print_json(data={"token": token, "contents": contents})
        return
    shown = token[:24] + "..." if token else "-"
    console.print(_fmt_panel_grid("Zee5", [
        ("token", shown),
        ("contents", plural(_content_count(contents), "item")),
    ]))


def _content_items(result: Any, partner: str) -> list[dict]:
    """Extract content rows from the {data: [{partner: [...]}]} wrapper."""
    if not isinstance(result, dict):
        return []
    data = result.get("data")
    if isinstance(data, list) and data and isinstance(data[0], dict):
        items = data[0].get(partner)
        if isinstance(items, list):
            return [i for i in items if isinstance(i, dict)]
    return []


def _content_count(contents: Any) -> int:
    if isinstance(contents, list):
        return len(contents)
    if isinstance(contents, dict):
        return _content_count(contents.get("data"))
    return 0


def _render_contents(result: Any, partner: str, *, title: str) -> None:
    items = _content_items(result, partner)
    if not items:
        console.print(f"[dim]no contents for {partner}[/dim]")
        return
    table = Table(box=box.SIMPLE_HEAVY, title=f"{title} ({len(items)})")
    for column in list(items[0])[:6]:
        table.add_column(column)
    for item in items[:40]:
        table.add_row(*[str(item.get(c, "-"))[:28] for c in list(items[0])[:6]])
    console.print(table)


@app.command("search")
def sbsearch(
    partner: str = typer.Argument(..., help="Partner slug (lionsgate, chorki, zee5, ...)"),
    genre: str = typer.Option("", "--genre"),
    offset: int = typer.Option(0, "--offset"),
    limit: int = typer.Option(20, "--limit"),
) -> None:
    """Browse a partner's streaming content (v1/sbcontents/search)."""
    ctx = get_context()
    with ctx.client() as client:
        result = PartnerService(client).sbcontents_search(
            partner, offset=offset, limit=limit, genre=genre
        )
    if ctx.json_out:
        console.print_json(data=result)
        return
    _render_contents(result, partner, title=f"{partner} search")


@app.command("contents")
def sbcontents(
    partner: str = typer.Argument(...),
    offset: int = typer.Option(0, "--offset"),
    limit: int = typer.Option(20, "--limit"),
) -> None:
    """Partner content list (v1/sbcontents/partner)."""
    ctx = get_context()
    with ctx.client() as client:
        result = PartnerService(client).sbcontents_partner(partner, offset=offset, limit=limit)
    if ctx.json_out:
        console.print_json(data=result)
        return
    _render_contents(result, partner, title=f"{partner} contents")
