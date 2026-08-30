"""Gamification wire models — login streak and loyalty points."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class StreakMilestone(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: int | None = None
    status: int = 0  # 1 = in progress, 2 = claimable, 3 = claimed
    milestone_days: int | None = None
    milestone_reward: int | None = None
    show_reached_msg: int = 0

    @property
    def status_label(self) -> str:
        return {1: "in progress", 2: "CLAIMABLE", 3: "claimed"}.get(self.status, "locked")


class DailyLoginHeader(BaseModel):
    model_config = ConfigDict(extra="allow")

    title: str = ""
    subtitle: str = ""
    tnc: str = ""
    about: str = ""


class DailyLoginSettings(BaseModel):
    model_config = ConfigDict(extra="allow")

    milestones: list[StreakMilestone] = Field(default_factory=list)
    total_streak: int | None = None
    gamification_header: DailyLoginHeader | None = None


class DailyLoginStreakInfo(BaseModel):
    """`GET /v2/gamification/daily-login` (JSON key is `milestone`, singular)."""

    model_config = ConfigDict(extra="allow")

    current_streak: int = 0
    last_unbroken_streak: int = 0
    milestone: list[StreakMilestone] = Field(default_factory=list)
    settings: DailyLoginSettings | None = None

    @property
    def claimable(self) -> list[StreakMilestone]:
        return [m for m in self.milestone if m.status == 2]


class ClaimResult(BaseModel):
    """`POST /v2/gamification/daily-login/claim` — `PostResult`."""

    model_config = ConfigDict(extra="allow")

    status: str = ""
    message: str = ""
    description: str = ""
    remarks: str = ""

    @property
    def ok(self) -> bool:
        return self.status.lower() in ("success", "pending")


class RewardPointBalance(BaseModel):
    """`GET /loyalty/balance` — `RewardPoint.data` (loose passthrough)."""

    model_config = ConfigDict(extra="allow")

    point_balance: int = -1
    loyalty_status: int = -1  # 1 = enrolled, 0/2 = enrollment CTA, <= -2 = not eligible

    @property
    def loyalty_label(self) -> str:
        return {
            1: "enrolled",
            0: "not enrolled",
            2: "not enrolled",
        }.get(self.loyalty_status, "not eligible")
