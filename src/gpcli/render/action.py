"""Action-response rendering — the ``{code, status, message}`` envelope that
mutation endpoints return (``fnf-add``, ``vas set-status``, ``campaign-activate``,
``internet-renew``, netcare submit, wt activate, ...).

HTTP-level failures never reach this layer — ``MyGPClient`` raises ``ApiError``
for non-2xx responses — so judging happens on the envelope only: a present
``status`` wins, a bare ``code`` is checked for 200, and a 2xx payload without
either is assumed successful (the server has many one-off shapes).
"""

from __future__ import annotations

from typing import Any

from gpcli.render.base import _fmt_panel_grid, console

_OK_STATUSES = frozenset({"success", "pending", "accepted", "completed", "ok", "active", "true", "1"})
_MESSAGE_KEYS = ("message", "msg", "remarks", "description", "detail")


def action_ok(response: Any) -> bool:
    """Judge a mutation envelope (see module docstring for precedence)."""
    if not isinstance(response, dict):
        return bool(response)
    status = str(response.get("status", "")).strip().lower()
    if status:
        return status in _OK_STATUSES
    if "code" in response:
        return str(response["code"]) == "200"
    return True


def _display_status(response: Any) -> str:
    if isinstance(response, dict):
        for key in ("status", "code"):
            if response.get(key) is not None:
                return str(response[key])
    return "ok"


def _message(response: Any) -> str:
    if isinstance(response, dict):
        for key in _MESSAGE_KEYS:
            value = response.get(key)
            if value:
                return str(value)
    return ""


def render_action_response(
    response: Any, *, title: str, rows: list[tuple[str, str]] | None = None
) -> bool:
    """Panel-render a mutation result; returns success (caller exits 1 on failure)."""
    ok = action_ok(response)
    panel_rows: list[tuple[str, str]] = [("status", _display_status(response))]
    panel_rows.extend(rows or [])
    message = _message(response)
    if message:
        panel_rows.append(("message", message[:100]))
    console.print(_fmt_panel_grid(title, panel_rows, border_style="green" if ok else "red"))
    return ok
