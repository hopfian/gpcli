"""Rendering primitives — the shared console and formatting helpers."""

from __future__ import annotations

import time
from typing import Any

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()


def _fmt_panel_grid(title: str, rows: list[tuple[str, str]], border_style: str = "cyan"):
    """Two-column grid panel — label/value rows."""
    grid = Table.grid(padding=(0, 2))
    grid.add_column(style="dim", justify="right")
    grid.add_column()
    for label, value in rows:
        grid.add_row(label, str(value))
    return Panel(grid, title=title, border_style=border_style)


def _fmt_ts(ts: int | None) -> str:
    if not ts:
        return "-"
    remaining = ts - int(time.time())
    if remaining <= 0:
        return "expired"
    hours, rem = divmod(remaining, 3600)
    minutes = rem // 60
    if hours:
        return f"in {hours}h {minutes}m"
    return f"in {minutes}m"


def _fmt_mb(mb: int) -> str:
    return f"{mb / 1024:g} GB" if mb and mb % 1024 == 0 else f"{mb} MB"


def render_dict(title: str, data: Any) -> None:
    console.print_json(data=data) if isinstance(data, (dict, list)) else console.print(str(data))
