"""Pydantic models for MyGP wire formats — domain-split, facade-re-exported.

The API's envelope conventions:
* success — plain JSON with domain fields
* failure — ``{"error": {"code": ..., "reason": ..., "message": ...,
  "description": ..., "status": "failed"}}`` (HTTP status is often 200 even
  for logical failures, e.g. guest-login with a null ``aaId``).

Consumers should keep importing from the package root
(``from gpcli.models import Auth``) — the per-domain modules are internal
organization, not a public surface.
"""

from gpcli.models.account import Balance, EmergencyBalance, Me, Profile, UsageDetail
from gpcli.models.auth import (
    Auth,
    GuestLoginResponse,
    GuestSession,
    GuestTokenResponse,
    OtpResponse,
)
from gpcli.models.autopay import (
    AutoPayListResponse,
    AutoPaymentInfo,
    AutoPayProduct,
    AutoPaySettings,
)
from gpcli.models.billing import (
    BillCycle,
    UsageHistoryCategory,
    UsageHistoryItem,
    UsageHistoryResponse,
)
from gpcli.models.catalog import (
    CmpOffer,
    FlexiBundlePrice,
    FlexiMap,
    FlexiPlan,
    FlexiSelected,
    PackItem,
    PackValidity,
    PackVolume,
    PackVolumeItem,
    VasCategory,
    VasService,
)
from gpcli.models.common import ErrorInfo, error_from_payload
from gpcli.models.comms import (
    BalanceStatusItem,
    BiometricDocType,
    BiometricSim,
    BiometricSimList,
    FnfInfo,
    FnfItem,
    FnfList,
    GAOfferInfo,
    ReceiverGift,
    SimOwnershipCertificate,
    WelcomeTune,
)
from gpcli.models.gamification import (
    ClaimResult,
    DailyLoginHeader,
    DailyLoginSettings,
    DailyLoginStreakInfo,
    RewardPointBalance,
    StreakMilestone,
)
from gpcli.models.partners import PartnerServiceToken, PartnerToken
from gpcli.models.purchase import (
    DirectRechargeData,
    MakePaymentResult,
    PaymentHistory,
    PaymentHistoryItem,
    RechargeAndActivateData,
    RechargeAndActivateResponse,
    RechargeGatewayResult,
    RechargeOffer,
)
from gpcli.models.transfer import BalanceTransferResponse, PinResetInitiateData

__all__ = [
    # common
    "ErrorInfo",
    "error_from_payload",
    # auth
    "Auth",
    "OtpResponse",
    "GuestLoginResponse",
    "GuestTokenResponse",
    "GuestSession",
    # account
    "Profile",
    "Me",
    "UsageDetail",
    "Balance",
    "EmergencyBalance",
    # catalog
    "FlexiMap",
    "FlexiSelected",
    "FlexiPlan",
    "FlexiBundlePrice",
    "VasCategory",
    "VasService",
    "PackVolumeItem",
    "PackVolume",
    "PackValidity",
    "PackItem",
    "CmpOffer",
    # transfer
    "BalanceTransferResponse",
    "PinResetInitiateData",
    # billing
    "UsageHistoryItem",
    "UsageHistoryCategory",
    "UsageHistoryResponse",
    "BillCycle",
    # autopay
    "AutoPayProduct",
    "AutoPaySettings",
    "AutoPaymentInfo",
    "AutoPayListResponse",
    # gamification
    "StreakMilestone",
    "DailyLoginHeader",
    "DailyLoginSettings",
    "DailyLoginStreakInfo",
    "ClaimResult",
    "RewardPointBalance",
    # comms
    "SimOwnershipCertificate",
    "BiometricDocType",
    "BiometricSim",
    "BiometricSimList",
    "FnfItem",
    "FnfInfo",
    "FnfList",
    "WelcomeTune",
    "ReceiverGift",
    "GAOfferInfo",
    "BalanceStatusItem",
    # partners
    "PartnerServiceToken",
    "PartnerToken",
    # purchase
    "RechargeOffer",
    "PaymentHistoryItem",
    "PaymentHistory",
    "RechargeGatewayResult",
    "DirectRechargeData",
    "RechargeAndActivateData",
    "RechargeAndActivateResponse",
    "MakePaymentResult",
]
