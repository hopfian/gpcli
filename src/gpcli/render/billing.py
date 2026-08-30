"""Billing rendering — usage history, bill cycles, autopay, payment methods."""

from __future__ import annotations

from rich import box
from rich.panel import Panel
from rich.table import Table

from gpcli.render.base import console


def render_usage_history(response, window: tuple[str, str], category: str | None, limit: int) -> None:
    categories = response.cdr
    if category:
        categories = [c for c in categories if c.slug == category or c.type == category]
    if not categories:
        console.print(f"[dim]no usage history for {window[0]} .. {window[1]}[/dim]")
        return
    for cat in categories:
        items = sorted(cat.data, key=lambda i: i.timestamp, reverse=True)[: limit or None]
        table = Table(
            box=box.SIMPLE_HEAVY,
            title=f"{cat.title or cat.slug} - {len(cat.data)} records ({window[0]} .. {window[1]})",
        )
        table.add_column("date", style="dim")
        table.add_column("time", style="dim")
        table.add_column("party")
        table.add_column("dir", justify="center")
        table.add_column("usage", justify="right")
        table.add_column("charge", justify="right", style="green")
        for item in items:
            table.add_row(
                item.usage_date[:10],
                item.usage_time[:9],
                (item.b_party or item.cdr_type or "-")[:18],
                item.direction,
                (item.consumed_usage or "-")[:14],
                item.charge,
            )
        console.print(table)


def render_bill_cycles(cycles, anchor_note: str) -> None:
    table = Table(box=box.SIMPLE_HEAVY, title=f"Itemized-bill cycles (anchor: {anchor_note})")
    table.add_column("#", justify="right", style="cyan")
    table.add_column("covers")
    table.add_column("invoice_month", style="dim")
    for index, cycle in enumerate(cycles, start=1):
        table.add_row(str(index), f"{cycle.start} .. {cycle.end}", cycle.invoice_month)
    console.print(table)


def render_autopay_list(response) -> None:
    subs = response.subscription
    if subs:
        table = Table(box=box.SIMPLE_HEAVY, title=f"AutoPay subscriptions ({len(subs)})")
        table.add_column("id", justify="right", style="cyan")
        table.add_column("msisdn")
        table.add_column("amount", justify="right")
        table.add_column("type")
        table.add_column("schedule")
        table.add_column("next run", style="green")
        for sub in subs:
            schedule = sub.frequency + f" {sub.frequency_unit}" if sub.frequency else "on low balance"
            table.add_row(
                str(sub.id),
                sub.msisdn,
                sub.amount,
                sub.product_type,
                schedule,
                sub.next_schedule_date or "-",
            )
        console.print(table)
    else:
        console.print("[dim]no autopay subscriptions[/dim]")

    if response.setting:
        s = response.setting
        grid = Table.grid(padding=(0, 2))
        grid.add_column(style="dim", justify="right")
        grid.add_column()
        if s.autopay_prepaid_min_amount and s.autopay_prepaid_max_amount:
            lo, hi = s.autopay_prepaid_min_amount, s.autopay_prepaid_max_amount
            grid.add_row("prepaid amount range", f"{lo} – {hi} BDT")
        if s.autopay_setup_limit:
            grid.add_row("setup limit", f"{s.autopay_setup_limit} subscriptions")
        if s.autopay_blocked_amount:
            grid.add_row("blocked amounts", ", ".join(s.autopay_blocked_amount))
        if s.autopay_suggested_recharge_amount:
            grid.add_row("suggested amounts", ", ".join(s.autopay_suggested_recharge_amount[:8]))
        if grid.rows:
            console.print(Panel(grid, title="AutoPay settings", border_style="cyan"))


def render_autopay_products(products) -> None:
    if not products:
        console.print("[dim]no autopay products configured[/dim]")
        return
    table = Table(box=box.SIMPLE_HEAVY, title=f"AutoPay products ({len(products)})")
    table.add_column("type", style="cyan")
    table.add_column("code")
    table.add_column("frequencies", justify="right")
    table.add_column("unit")
    table.add_column("trigger", justify="right")
    for product in products:
        table.add_row(
            product.product_type or "-",
            product.product_code or "-",
            ", ".join(product.frequency) or "-",
            product.frequency_unit or "-",
            product.trigger_amount or "-",
        )
    console.print(table)


def render_payment_methods(methods) -> None:
    if not methods:
        console.print("[dim]no saved payment methods (autopay needs service_provider values)[/dim]")
        return
    table = Table(box=box.SIMPLE_HEAVY, title=f"Saved payment methods ({len(methods)})")
    columns: list[str] = []
    for method in methods:
        for key in method:
            if key not in columns:
                columns.append(key)
    for column in columns[:5]:
        table.add_column(column)
    for method in methods:
        table.add_row(*(str(method.get(c, ""))[:28] for c in columns[:5]))
    console.print(table)
