"""Catalog rendering — flexiplan, VAS, packs, CMP offers."""

from __future__ import annotations

from rich import box
from rich.panel import Panel
from rich.table import Table

from gpcli.render.base import _fmt_mb, console


def _decode_bundle_key(key: str) -> tuple[int, int, int, int, int, int]:
    """Parse `L.._V.._D..(_G|M)_F.._B.._S..` back into components (MB)."""
    parts: dict[str, int] = {}
    for seg in key.split("_"):
        letter, rest = seg[0], seg[1:]
        if rest.endswith("G"):
            parts[letter] = int(float(rest[:-1]) * 1024)
        elif rest.endswith("M"):
            parts[letter] = int(float(rest[:-1]))
        else:
            parts[letter] = int(float(rest or 0))
    return (
        parts.get("L", 0), parts.get("V", 0), parts.get("D", 0),
        parts.get("F", 0), parts.get("B", 0), parts.get("S", 0),
    )


def render_flexiplan(catalog) -> None:
    m = catalog.map
    table = Table(box=box.SIMPLE_HEAVY, title="Flexiplan — selectable options")
    table.add_column("component")
    table.add_column("available values")
    table.add_row("validity (days)", ", ".join(map(str, m.days)))
    table.add_row("voice (min)", ", ".join(map(str, m.voice)))
    table.add_row("data", ", ".join(_fmt_mb(v) for v in m.data))
    if m.data4g:
        table.add_row("4G data", ", ".join(_fmt_mb(v) for v in m.data4g))
    table.add_row("sms", ", ".join(map(str, m.sms)))
    if m.bioscope:
        table.add_row("bioscope", ", ".join(_fmt_mb(v) for v in m.bioscope))
    console.print(table)

    sel = catalog.selected
    grid = Table.grid(padding=(0, 2))
    grid.add_column(style="dim", justify="right")
    grid.add_column()
    grid.add_row("priced bundles", f"{len(catalog.bundles)}")
    grid.add_row(
        "current selection",
        f"{sel.days}d, {_fmt_mb(sel.data)}, {sel.voice} min, {sel.sms} SMS",
    )
    if catalog.vat:
        grid.add_row("vat", ", ".join(f"{k} x{v}" for k, v in catalog.vat.items()))
    if catalog.mca_price:
        grid.add_row(
            "mca price (prepaid)",
            f"{catalog.mca_price.get('prepaid', 0):g} BDT "
            f"(market {catalog.mca_market_price.get('prepaid', 0):g})",
        )
    console.print(Panel(grid, title="Flexiplan catalog", border_style="cyan"))


def render_flexiplan_quote(key: str, price, mca: bool = False) -> None:
    days, voice, data, four_g, bioscope, sms = _decode_bundle_key(key)
    combo = Table.grid(padding=(0, 2))
    combo.add_column(style="dim", justify="right")
    combo.add_column()
    combo.add_row("bundle key", key)
    combo.add_row("validity", f"{days} days")
    combo.add_row("voice", f"{voice} min")
    if data:
        combo.add_row("data", _fmt_mb(data))
    if four_g:
        combo.add_row("4G data", _fmt_mb(four_g))
    if bioscope:
        combo.add_row("bioscope", _fmt_mb(bioscope))
    if sms:
        combo.add_row("sms", str(sms))
    if mca:
        combo.add_row("mca", "included")

    price_table = Table(box=box.SIMPLE_HEAVY, title="Price")
    price_table.add_column("component", style="dim")
    price_table.add_column("BDT", justify="right")
    price_table.add_row("base", f"{price.base_price:g}")
    price_table.add_row("base + VAT", f"{price.base_price_vat:g}")
    price_table.add_row("market", f"{price.market_price:g}")
    price_table.add_row(
        "[green]prepaid total (VAT+MCA)[/green]",
        f"[green]{price.price_vat_mca_prepaid:g}[/green]",
    )
    price_table.add_row("commission", f"{price.commission:g}")
    if price.discount_percent:
        price_table.add_row("discount", f"{price.discount_percent}%")

    console.print(combo)
    console.print(price_table)


def render_vas_categories(categories) -> None:
    table = Table(box=box.SIMPLE_HEAVY, title=f"VAS categories ({len(categories)})")
    table.add_column("id", justify="right", style="cyan")
    table.add_column("name")
    table.add_column("priority", justify="right")
    for category in categories:
        table.add_row(str(category.id), category.name, str(category.priority))
    console.print(table)


def render_vas_services(services, title: str) -> None:
    table = Table(box=box.SIMPLE_HEAVY, title=title)
    table.add_column("id", justify="right", style="cyan")
    table.add_column("name")
    table.add_column("price", justify="right")
    table.add_column("cycle", style="dim")
    for service in services:
        cycle = f"{service.subscription_period} {service.subscription_unit}".strip()
        table.add_row(str(service.id), service.name, f"{service.price} {service.price_unit}", cycle)
    console.print(table)


def render_vas_items(items: list, title: str) -> None:
    if not items:
        console.print(f"[dim]{title}: none[/dim]")
        return
    table = Table(box=box.SIMPLE_HEAVY, title=f"{title} ({len(items)})")
    columns: list[str] = []
    for item in items:
        if isinstance(item, dict):
            for key in item:
                if key not in columns:
                    columns.append(key)
    for column in columns[:6]:
        table.add_column(column)
    for item in items[:30]:
        table.add_row(*(str(item.get(c, ""))[:28] for c in columns[:6]))
    console.print(table)


def render_packs(packs, title: str, *, show_cashback: bool = False) -> None:
    if not packs:
        console.print(f"[dim]{title}: none found[/dim]")
        return
    table = Table(box=box.SIMPLE_HEAVY, title=f"{title} ({len(packs)})")
    table.add_column("id", justify="right", style="cyan")
    table.add_column("title")
    table.add_column("price", justify="right")
    table.add_column("validity", style="dim")
    table.add_column("volume")
    if show_cashback:
        table.add_column("cashback", style="green")
    for pack in packs:
        row = [
            pack.id,
            pack.title[:44],
            f"{pack.price}" if pack.price else "-",
            pack.validity_summary()[:18] or "-",
            pack.volume_summary()[:34] or "-",
        ]
        if show_cashback:
            row.append(pack.cashback_text()[:28] or "-")
        table.add_row(*row)
    console.print(table)


def render_cmp_offers(offers, group: str) -> None:
    if not offers:
        console.print(f"[dim]{group}: none[/dim]")
        return
    table = Table(box=box.SIMPLE_HEAVY, title=f"my offers — {group} ({len(offers)})")
    table.add_column("name")
    table.add_column("price", justify="right")
    table.add_column("type", style="dim")
    table.add_column("contents")
    table.add_column("campaign", justify="right", style="cyan")
    for offer in offers:
        table.add_row(
            getattr(offer, "name", str(offer))[:40],
            getattr(offer, "price", "") or "-",
            (getattr(offer, "catalog_pack_type", "") or "")[:12],
            getattr(offer, "offers_summary", lambda: "")()[:36] or "-",
            getattr(offer, "campaign_id", "") or "-",
        )
    console.print(table)
