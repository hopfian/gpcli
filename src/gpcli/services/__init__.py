"""Service layer — one concern per module, exported through this facade.

Services are thin: transport via `MyGPClient`, wire formats via
`gpcli.models` / `gpcli.bodies`. Consumers should import from the
package root — `from gpcli.services import AuthService` — the per-module
split is internal organization.
"""

from gpcli.services.account import AccountService
from gpcli.services.auth import AuthService
from gpcli.services.autopay import AutoPayService
from gpcli.services.billing import BillService
from gpcli.services.catalog import CatalogService
from gpcli.services.content import ContentService
from gpcli.services.emergency import EmergencyBalanceService
from gpcli.services.fnf import FnfService
from gpcli.services.gamification import GamificationService
from gpcli.services.history import HistoryService
from gpcli.services.mca import McaService
from gpcli.services.netcare import NetworkComplainService
from gpcli.services.offers import OffersService
from gpcli.services.partners import PartnerService
from gpcli.services.purchase import PurchaseService
from gpcli.services.roaming import RoamingService
from gpcli.services.sim import SimService
from gpcli.services.transfer import TransferService
from gpcli.services.welcome_tune import WelcomeTuneService

__all__ = [
    "AccountService",
    "AuthService",
    "AutoPayService",
    "BillService",
    "CatalogService",
    "ContentService",
    "EmergencyBalanceService",
    "FnfService",
    "GamificationService",
    "HistoryService",
    "McaService",
    "NetworkComplainService",
    "OffersService",
    "PartnerService",
    "PurchaseService",
    "RoamingService",
    "SimService",
    "TransferService",
    "WelcomeTuneService",
]
