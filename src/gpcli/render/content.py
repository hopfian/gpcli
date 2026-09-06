"""Content rendering — home cards, districts, news feed."""

from __future__ import annotations

from rich import box
from rich.panel import Panel
from rich.table import Table

from gpcli.render.base import console, plural


def render_cards(data: dict) -> None:
    cards = data.get("cards") or {}
    categories = data.get("categories") or {}
    table = Table(box=box.SIMPLE_HEAVY, title=f"Cards engine — {plural(len(cards), 'card')}")
    table.add_column("card id", style="cyan")
    table.add_column("type")
    table.add_column("home", justify="center")
    for card_id, card in list(cards.items())[:40]:
        if not isinstance(card, dict):
            continue
        parents = card.get("parent_card_data") or []
        sub_type = ""
        if parents and isinstance(parents[0], dict):
            sub_type = str(parents[0].get("sub_type", ""))
        table.add_row(
            str(card.get("id", card_id)),
            sub_type or "-",
            "yes" if str(card.get("is_eligible_for_home")) == "1" else "",
        )
    console.print(table)
    if isinstance(categories, dict) and categories:
        cats = ", ".join(list(categories.keys())[:15])
        console.print(f"[dim]categories:[/dim] {cats}")


def render_districts(districts: list[str]) -> None:
    console.print(Panel(
        ", ".join(districts),
        title=f"Districts ({len(districts)})",
        border_style="cyan",
    ))


def render_news(data: dict) -> None:
    """`tps/v3/news`: {data: [{category, category_title, items: [...]}], ...}."""
    categories = data.get("data") or []
    rows: list[tuple[str, str, str]] = []
    for cat in categories:
        if not isinstance(cat, dict):
            continue
        for item in cat.get("items") or []:
            if isinstance(item, dict) and item.get("title"):
                rows.append((
                    str(item["title"]),
                    str(item.get("copyright", item.get("source", "-"))),
                    str(item.get("pubDate", ""))[:16],
                ))
    if not rows:
        console.print("[dim]no news[/dim]")
        return
    table = Table(box=box.SIMPLE_HEAVY, title=f"News — {plural(len(rows), 'item')}")
    table.add_column("title")
    table.add_column("source", style="dim")
    table.add_column("published", style="dim")
    for title, source, published in rows[:40]:
        table.add_row(title[:72], source[:24], published)
    console.print(table)
