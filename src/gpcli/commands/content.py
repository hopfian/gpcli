"""`gpcli` content commands: cards, districts, weather, news."""

from __future__ import annotations

import typer

from gpcli.context import get_context
from gpcli.render import console, render_cards, render_dict, render_districts, render_news
from gpcli.services.auth import AuthService
from gpcli.services.content import ContentService

app = typer.Typer(help="Content endpoints (cards engine, districts, weather, news)")


@app.command("cards")
def cards(
    category: str = typer.Option("All", "--category", "-c"),
    offset: int = typer.Option(0, "--offset", "-o"),
    limit: int = typer.Option(20, "--limit", "-l"),
) -> None:
    """Homepage card engine (guest session, auto-provisioned)."""
    ctx = get_context()
    with ctx.client() as client:
        result = ContentService(client, AuthService(client)).cards(
            category=category, offset=offset, limit=limit
        )
    if ctx.json_out:
        console.print_json(data=result)
        return
    render_cards(result)


@app.command("districts")
def districts() -> None:
    """District list (guest session)."""
    ctx = get_context()
    with ctx.client() as client:
        result = ContentService(client, AuthService(client)).districts()
    if ctx.json_out:
        console.print_json(data=result)
        return
    render_districts(result)


@app.command("weather")
def weather(
    lat: str = typer.Option("23.8103", "--lat"),
    lon: str = typer.Option("90.4125", "--lon"),
) -> None:
    """Weather lookup (guest session; param contract partially verified)."""
    ctx = get_context()
    with ctx.client() as client:
        result = ContentService(client, AuthService(client)).weather(lat, lon)
    if ctx.json_out:
        console.print_json(data=result)
        return
    render_dict("weather", result)


@app.command("news")
def news() -> None:
    """News feed (subscriber session)."""
    ctx = get_context()
    with ctx.client() as client:
        result = ContentService(client, AuthService(client)).news()
    if ctx.json_out:
        console.print_json(data=result)
        return
    render_news(result)
