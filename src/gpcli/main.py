"""gpcli — composition root: app assembly, command registration, error boundary.

Network/business logic lives in `services/` and `client.py`; presentation
in `commands/` + `render/`. This module only wires them together (and is
the single place a new command group gets registered).
"""

from __future__ import annotations

import contextlib
import sys

import typer

from gpcli import __version__
from gpcli.commands import (
    account as account_commands,
)
from gpcli.commands import (
    auth as auth_commands,
)
from gpcli.commands import (
    autopay as autopay_commands,
)
from gpcli.commands import (
    autorenew as autorenew_commands,
)
from gpcli.commands import (
    billing as billing_commands,
)
from gpcli.commands import (
    config as config_commands,
)
from gpcli.commands import (
    content as content_commands,
)
from gpcli.commands import (
    emergency as emergency_commands,
)
from gpcli.commands import (
    flexiplan as flexiplan_commands,
)
from gpcli.commands import (
    fnf as fnf_commands,
)
from gpcli.commands import (
    gamification as gamification_commands,
)
from gpcli.commands import (
    history as history_commands,
)
from gpcli.commands import (
    mca as mca_commands,
)
from gpcli.commands import (
    netcare as netcare_commands,
)
from gpcli.commands import (
    offers as offers_commands,
)
from gpcli.commands import (
    packs as packs_commands,
)
from gpcli.commands import (
    partners as partners_commands,
)
from gpcli.commands import (
    purchase as purchase_commands,
)
from gpcli.commands import (
    raw as raw_commands,
)
from gpcli.commands import (
    roaming as roaming_commands,
)
from gpcli.commands import (
    root as root_commands,
)
from gpcli.commands import (
    sim as sim_commands,
)
from gpcli.commands import (
    support as support_commands,
)
from gpcli.commands import (
    transfer as transfer_commands,
)
from gpcli.commands import (
    vas as vas_commands,
)
from gpcli.commands import (
    welcome_tune as welcome_tune_commands,
)
from gpcli.context import Context, set_context
from gpcli.dns import install_dns_fallback
from gpcli.errors import MyGPError
from gpcli.render import console

app = typer.Typer(
    help="Reverse-engineered MyGP (Grameenphone) API client.",
    no_args_is_help=True,
    pretty_exceptions_show_locals=False,
)

# --- subcommand groups (one module = one group) ---------------------------
GROUPS: list[tuple[typer.Typer, str]] = [
    (auth_commands.app, "auth"),
    (account_commands.app, "account"),
    (content_commands.app, "content"),
    (config_commands.app, "config"),
    (raw_commands.app, "raw"),
    (flexiplan_commands.app, "flexiplan"),
    (vas_commands.app, "vas"),
    (transfer_commands.app, "transfer"),
    (billing_commands.app, "bill"),
    (autopay_commands.app, "autopay"),
    (emergency_commands.app, "eb"),
    (gamification_commands.app, "streak"),
    (roaming_commands.app, "roaming"),
    (sim_commands.app, "sim"),
    (fnf_commands.app, "fnf"),
    (mca_commands.app, "mca"),
    (welcome_tune_commands.app, "wt"),
    (netcare_commands.app, "netcare"),
    (offers_commands.app, "offers"),
    (autorenew_commands.app, "autorenew"),
    (partners_commands.app, "partners"),
    (support_commands.app, "support"),
    (purchase_commands.purchase_app, "purchase"),
    (purchase_commands.recharge_app, "recharge"),
]
for group, name in GROUPS:
    app.add_typer(group, name=name)

# --- root-level commands ---------------------------------------------------
app.command(name="login")(root_commands.login)
app.command(name="guest")(root_commands.guest)
app.command(name="status")(root_commands.status)
app.command(name="me")(root_commands.me)
app.command(name="balance")(root_commands.balance)
app.command(name="news")(root_commands.news)
app.command(name="packs")(packs_commands.packs)
app.command(name="history")(history_commands.history)


def _version_callback(value: bool) -> None:
    if value:
        console.print(__version__)
        raise typer.Exit()


@app.callback()
def _root(
    version: bool = typer.Option(
        False, "--version", "-V", help="Show the CLI version and exit",
        callback=_version_callback, is_eager=True,
    ),
    json_out: bool = typer.Option(False, "--json", "-j", help="Machine-readable JSON output"),
) -> None:
    # Windows legacy consoles (cp1252) crash on ৳/→/Bengali etc. — replace
    # unencodable characters instead of raising UnicodeEncodeError.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            with contextlib.suppress(ValueError, OSError):
                stream.reconfigure(errors="backslashreplace")
    set_context(Context(json_out=json_out))
    install_dns_fallback()


def main() -> None:
    try:
        app()
    except MyGPError as err:
        console.print(f"[red]error:[/red] {err}")
        raise SystemExit(1) from err


if __name__ == "__main__":
    main()
