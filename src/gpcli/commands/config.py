"""`gpcli config` — device identity and preferences."""

from __future__ import annotations

import typer

from gpcli.context import get_context
from gpcli.render import console

app = typer.Typer(help="Device identity and preferences")


@app.command("show")
def show() -> None:
    """Show the current configuration."""
    ctx = get_context()
    state = ctx.state
    console.print_json(data={
        "device_id": state.device.device_id,
        "device_model": state.device.device_model,
        "device_name": state.device.device_name,
        "language": state.language,
        "state_path": str(state.path),
    })


@app.command("set")
def set_value(
    key: str = typer.Argument(...),
    value: str = typer.Argument(...),
) -> None:
    """Set a config value: language | device-model | device-name | device-id."""
    ctx = get_context()
    state = ctx.state
    mapping = {
        "language": lambda v: setattr(state, "language", v),
        "device-model": lambda v: setattr(state.device, "device_model", v),
        "device-name": lambda v: setattr(state.device, "device_name", v),
        "device-id": lambda v: setattr(state.device, "device_id", v),
    }
    setter = mapping.get(key)
    if setter is None:
        raise typer.BadParameter(f"unknown key {key!r}; expected one of: {sorted(set(mapping))}")
    setter(value)
    state.save()
    console.print(f"[green]set[/green] {key} = {value}")
