"""`gpcli packs <category>` — the pack/offer catalog by Explore-tab category."""

from __future__ import annotations

import typer
from rich import box
from rich.table import Table

from gpcli.context import get_context
from gpcli.models import CmpOffer
from gpcli.render import console, render_cmp_offers, render_packs
from gpcli.services.catalog import PACK_CATEGORIES, CatalogService

_CATEGORY_HELP = " | ".join(f"{slug} ({hint})" for slug, hint in PACK_CATEGORIES.items())


def packs(
    category: str = typer.Argument("all", help=_CATEGORY_HELP),
    usd: bool = typer.Option(False, "--usd", help="roaming: USD-priced packs instead of Taka"),
    search: str = typer.Option("", "--search", "-s", help="Substring filter on title/keyword"),
    limit: int = typer.Option(50, "--limit", "-l", help="Max rows (0 = all)"),
    all_groups: bool = typer.Option(
        False, "--all-groups", help="my-offers: show every CMP group, not just myoffers"
    ),
    list_categories: bool = typer.Option(
        False, "--list-categories", help="Show available categories and exit"
    ),
) -> None:
    """List packs by category from the app's master catalog (v3/catalogs)."""
    ctx = get_context()

    if list_categories:
        if ctx.json_out:
            console.print_json(data=PACK_CATEGORIES)
            return
        table = Table(box=box.SIMPLE_HEAVY, title="Pack categories")
        table.add_column("category", style="cyan")
        table.add_column("selects")
        for slug, hint in PACK_CATEGORIES.items():
            table.add_row(slug, hint)
        console.print(table)
        return

    if category not in PACK_CATEGORIES:
        raise typer.BadParameter(
            f"unknown category {category!r}; choose one of: {', '.join(PACK_CATEGORIES)}"
        )

    with ctx.client() as client:
        service = CatalogService(client)

        if category == "my-offers":
            data = service.cmp_offers()
            groups: list[tuple[str, list]] = (
                [(k, v) for k, v in data.items() if isinstance(v, list) and v]
                if all_groups
                else [("myoffers", data.get("myoffers", []))]
            )
            if ctx.json_out:
                console.print_json(
                    data=data if all_groups else {"myoffers": data.get("myoffers", [])}
                )
                return
            if not any(items for _, items in groups):
                console.print("[dim]no personalized offers right now[/dim]")
                return
            for name, items in groups:
                offers = [CmpOffer.model_validate(item) for item in items if isinstance(item, dict)]
                render_cmp_offers(offers, name)
            return

        result = service.category_packs(category, usd=usd)
        if search:
            needle = search.lower()
            result = [
                p for p in result
                if needle in p.title.lower() or needle in p.keyword.lower()
            ]
        if limit > 0:
            result = result[:limit]

    if ctx.json_out:
        console.print_json(
            data=[p.model_dump(exclude={"additional_data"}, exclude_none=True) for p in result]
        )
        return
    title = f"{category} packs" + (" (USD)" if usd else "")
    render_packs(result, title, show_cashback=(category == "cashback"))
