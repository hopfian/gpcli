"""`gpcli transfer …` — balance transfer and transfer-PIN management."""

from __future__ import annotations

import typer
from rich.prompt import Prompt

from gpcli.context import get_context
from gpcli.models import BalanceTransferResponse
from gpcli.render import console
from gpcli.services.transfer import TransferService

app = typer.Typer(help="Balance transfer: send balance, register, PIN management")


def _emit(ctx, response: BalanceTransferResponse, *, sms_reason_hint: bool = False) -> None:
    if ctx.json_out:
        console.print_json(data=response.model_dump())
        return
    if response.ok:
        console.print(f"[green]success[/green] {response.message}".strip())
    else:
        detail = response.message or response.result
        console.print(f"[red]failed[/red] {detail}")
        if sms_reason_hint:
            console.print(
                "[dim]detailed failure reasons are delivered by SMS "
                "(with a reference number), not the API response[/dim]"
            )
        raise typer.Exit(1)


@app.command()
def register() -> None:
    """Enroll the account for balance transfer (GET balance/register).

    Note: an already-registered account returns the 401 "Unsuccessful"
    envelope — GP confirms the real reason ("You have already activated
    P2P_SERVICE") via SMS.
    """
    ctx = get_context()
    with ctx.client() as client:
        response = TransferService(client).register()
    _emit(ctx, response, sms_reason_hint=True)


@app.command()
def send(
    payee: str = typer.Argument(..., help="Recipient number (as typed in the app)"),
    amount: str = typer.Argument(..., help="Amount in Taka"),
    pin: str = typer.Option("", "--pin", "-p", help="Transfer PIN (prompted if omitted)"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip the confirmation prompt"),
) -> None:
    """Transfer balance to another subscriber (POST balance/transfer)."""
    ctx = get_context()
    if not pin:
        pin = Prompt.ask("Transfer PIN", password=True)
    if not yes:
        confirmed = typer.confirm(f"Send {amount} BDT to {payee}?", default=False)
        if not confirmed:
            console.print("[dim]aborted[/dim]")
            raise typer.Exit(1)
    with ctx.client() as client:
        response = TransferService(client).send(payee, amount, pin)
    _emit(ctx, response, sms_reason_hint=True)


@app.command("change-pin")
def change_pin(
    old_pin: str = typer.Option("", "--old", help="Current PIN (prompted if omitted)"),
    new_pin: str = typer.Option("", "--new", help="New PIN (prompted if omitted)"),
) -> None:
    """Change the transfer PIN (POST balance/pin)."""
    ctx = get_context()
    if not old_pin:
        old_pin = Prompt.ask("Current PIN", password=True)
    if not new_pin:
        new_pin = Prompt.ask("New PIN", password=True)
        confirm = Prompt.ask("Confirm new PIN", password=True)
        if confirm != new_pin:
            console.print("[red]PINs do not match[/red]")
            raise typer.Exit(1)
    with ctx.client() as client:
        response = TransferService(client).change_pin(old_pin, new_pin, new_pin)
    _emit(ctx, response)


@app.command("reset-pin")
def reset_pin(
    otp: str = typer.Option("", "--otp", help="OTP from SMS (prompted if omitted)"),
    msisdn: str = typer.Option("", "--msisdn", help="Override the session MSISDN"),
    new_pin: str = typer.Option("", "--new-pin", help="New PIN (prompted if omitted)"),
) -> None:
    """Reset a forgotten transfer PIN: initiate -> OTP verify -> set new PIN."""
    ctx = get_context()
    state = ctx.state
    if not msisdn:
        msisdn = state.auth.msisdn if state.auth else ""
        if not msisdn:
            raise typer.BadParameter("no session msisdn; pass --msisdn")

    # In --json mode the whole flow emits ONE object: {initiate, verify, set}
    # (with the failing step last), so stdout stays a valid single-JSON stream.
    out: dict = {}

    with ctx.client() as client:
        service = TransferService(client)
        # 1. initiate — dispatches an OTP SMS and returns a reference_id
        initiate = service.reset_pin_initiate()
        out["initiate"] = initiate
        data = initiate.get("data") or {}
        reference_id = data.get("reference_id") if isinstance(data, dict) else None
        if not reference_id:
            if ctx.json_out:
                console.print_json(data=out)
            else:
                console.print(f"[red]initiate failed[/red] {initiate}")
            raise typer.Exit(1)

        if not otp:
            otp = Prompt.ask("Enter the OTP from your SMS", password=True)

        # 2. verify
        verify = service.reset_pin_verify(str(reference_id), otp, msisdn)
        out["verify"] = verify
        verified = (
            (verify.get("data") or {}).get("is_otp_verified") in (True, "true", "1", 1)
            if isinstance(verify.get("data"), dict)
            else False
        )
        if not verified:
            if ctx.json_out:
                console.print_json(data=out)
            else:
                console.print(f"[red]OTP verification failed[/red] {verify}")
            raise typer.Exit(1)

        # 3. set the new PIN
        if not new_pin:
            new_pin = Prompt.ask("New transfer PIN", password=True)
            confirm = Prompt.ask("Confirm new PIN", password=True)
            if confirm != new_pin:
                console.print("[red]PINs do not match[/red]")
                raise typer.Exit(1)
        result = service.reset_pin_set(new_pin, new_pin)
        out["set"] = result

    if ctx.json_out:
        console.print_json(data=out)
        return
    status = result.get("result", "")
    message = result.get("message", "") or result
    if str(status).lower() == "success":
        extra = message if isinstance(message, str) else ""
        console.print(f"[green]PIN reset successful[/green] {extra}".strip())
    else:
        console.print(f"[red]PIN reset failed[/red] {message}")
        raise typer.Exit(1)
