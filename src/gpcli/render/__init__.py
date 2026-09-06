"""Rich rendering for human output; `--json` mode bypasses all of this.

Facade package: presentation code lives in per-domain modules (`account`,
`content`, `catalog`, `billing`) on top of shared primitives (`base`).
Consumers should keep importing from the package root —
``from gpcli.render import render_balance`` — the split is internal
organization, not a public surface.
"""

from gpcli.render.account import (
    render_auth_status,
    render_balance,
    render_login_success,
    render_me,
)
from gpcli.render.action import action_ok, render_action_response
from gpcli.render.base import _fmt_panel_grid, console, plural, render_dict
from gpcli.render.billing import (
    render_autopay_list,
    render_autopay_products,
    render_bill_cycles,
    render_payment_methods,
    render_usage_history,
)
from gpcli.render.catalog import (
    render_cmp_offers,
    render_flexiplan,
    render_flexiplan_quote,
    render_packs,
    render_vas_categories,
    render_vas_items,
    render_vas_services,
)
from gpcli.render.content import render_cards, render_districts, render_news

__all__ = [
    # base
    "console",
    "plural",
    "render_dict",
    "_fmt_panel_grid",  # shared by command files (public primitive, legacy name)
    # account
    "render_auth_status",
    "render_me",
    "render_balance",
    "render_login_success",
    # action
    "action_ok",
    "render_action_response",
    # content
    "render_cards",
    "render_districts",
    "render_news",
    # catalog
    "render_flexiplan",
    "render_flexiplan_quote",
    "render_vas_categories",
    "render_vas_services",
    "render_vas_items",
    "render_packs",
    "render_cmp_offers",
    # billing
    "render_usage_history",
    "render_bill_cycles",
    "render_autopay_list",
    "render_autopay_products",
    "render_payment_methods",
]
