"""Account & session rendering — status, profile, balances, login."""

from __future__ import annotations

from rich import box
from rich.panel import Panel
from rich.table import Table

from gpcli.models import Auth, Balance, GuestSession, Me
from gpcli.render.base import _fmt_ts, console
from gpcli.state import State


def render_auth_status(state: State) -> None:
    grid = Table.grid(padding=(0, 2))
    grid.add_column(style="dim", justify="right")
    grid.add_column()

    grid.add_row("device id", state.device.device_id)
    grid.add_row("device model", f"{state.device.device_name} {state.device.device_model}")
    grid.add_row("language", state.language)

    if state.auth and state.auth.access_token:
        auth = state.auth
        rows: list[tuple[str, str]] = [
            ("subscriber", auth.msisdn or "?"),
            ("auth id", str(auth.id)),
            ("non-GP (ng)", str(auth.ng)),
            ("access token", auth.access_token[:12] + "…"),
            ("expires", _fmt_ts(auth.expire_at)),
            ("refresh token", auth.refresh_token[:12] + "…" if auth.refresh_token else "-"),
        ]
        for row in rows:
            grid.add_row(*row)
        console.print(Panel(grid, title="Session — subscriber", border_style="green"))
    else:
        console.print(Panel(grid, title="Session — none (guest available)", border_style="yellow"))

    if state.guest:
        g: GuestSession = state.guest
        ggrid = Table.grid(padding=(0, 2))
        ggrid.add_column(style="dim", justify="right")
        ggrid.add_column()
        ggrid.add_row("user id", g.user_id)
        ggrid.add_row("access token", (g.access_token[:12] + "…") if g.access_token else "-")
        ggrid.add_row("expires", _fmt_ts(g.expires_at))
        console.print(Panel(ggrid, title="Guest session", border_style="cyan"))


def render_me(me: Me) -> None:
    p = me.profile
    if p is None:
        console.print_json(data=me.model_dump(exclude_none=True))
        return
    grid = Table.grid(padding=(0, 2))
    grid.add_column(style="dim", justify="right")
    grid.add_column()
    grid.add_row("name", p.name or "-")
    grid.add_row("msisdn", me.msisdn or p.msisdn or "-")
    grid.add_row("email", p.email or "-")
    grid.add_row("address", p.address or "-")
    grid.add_row("gender", p.gender or "-")
    grid.add_row("NID DOB", p.nid_dob or p.birthday or "-")
    grid.add_row("status", p.status or "-")
    grid.add_row("connect id", p.connectid_sub or "-")
    grid.add_row("member since", p.created_at or "-")
    grid.add_row("login method", me.login_method or "-")
    if p.rfu_1:
        grid.add_row("interests", p.rfu_1)
    console.print(Panel(grid, title="MyGP Subscriber", border_style="green"))


def render_balance(balance: Balance) -> None:
    table = Table(box=box.SIMPLE_HEAVY, title="Balance & Usage")
    table.add_column("Item", style="dim")
    table.add_column("Value", justify="right")
    table.add_row("main balance", f"{balance.balance:g} BDT")
    table.add_row("account type", balance.type)
    table.add_row("service class", str(balance.service_class))
    if balance.internet_details:
        d = balance.internet_details
        table.add_row("internet", f"{d.value} {d.unit} ({d.label})")
    if balance.sms_details:
        d = balance.sms_details
        table.add_row("sms", f"{d.value} {d.unit} ({d.label})")
    if balance.internet_packs:
        table.add_row("internet packs", str(len(balance.internet_packs)))
    if balance.emergency_balance:
        eb = balance.emergency_balance
        table.add_row("emergency balance", f"{eb.balance:g} BDT (due {eb.due:g})")
        table.add_row("  EB remaining", f"{eb.remaining} (limit {eb.dynamic_eb_limit})")
    console.print(table)


def render_login_success(auth: Auth) -> None:
    grid = Table.grid(padding=(0, 2))
    grid.add_column(style="dim", justify="right")
    grid.add_column()
    grid.add_row("msisdn", auth.msisdn)
    grid.add_row("auth id", str(auth.id))
    grid.add_row("expires", _fmt_ts(auth.expire_at))
    console.print(Panel(grid, title="Login successful", border_style="green"))
