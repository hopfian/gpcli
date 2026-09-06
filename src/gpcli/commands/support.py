"""`gpcli support` — email form and live chat."""

from __future__ import annotations

import webbrowser

import typer

from gpcli.context import get_context
from gpcli.render import _fmt_panel_grid, console, render_action_response
from gpcli.services.partners import PartnerService

app = typer.Typer(help="Support: email form and live chat")


@app.command("form")
def form(
    name: str = typer.Option(..., "--name"),
    email: str = typer.Option(..., "--email"),
    issue_type: str = typer.Option(..., "--issue-type"),
    message: str = typer.Option(..., "--message"),
) -> None:
    """Send the email-support form (POST support)."""
    ctx = get_context()
    with ctx.client() as client:
        result = PartnerService(client).send_support(name, email, issue_type, message)
    if ctx.json_out:
        console.print_json(data=result)
        return
    if not render_action_response(result, title="Support form sent", rows=[
        ("name", name),
        ("email", email),
        ("issue type", issue_type),
    ]):
        raise typer.Exit(1)


@app.command("chat")
def chat(
    open_browser: bool = typer.Option(False, "--open", "-o", help="Open in a browser"),
) -> None:
    """Live chat — mint the chatbot token and print/open the chat URL."""
    ctx = get_context()
    with ctx.client() as client:
        service = PartnerService(client)
        token = service.chatbot_token().token
        url = service.chat_url(token)
    if ctx.json_out:
        console.print_json(data={"token": token, "url": url})
        return
    console.print(_fmt_panel_grid("Live chat", [("url", url)]))
    if open_browser:
        webbrowser.open(url)
        console.print("[green]opened[/green]")
