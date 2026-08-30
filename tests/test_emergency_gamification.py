"""Emergency balance and gamification (streak) services."""

from gpcli.models import (
    ClaimResult,
    DailyLoginStreakInfo,
    EmergencyBalance,
    RewardPointBalance,
    StreakMilestone,
)
from gpcli.services.emergency import EmergencyBalanceService
from gpcli.services.gamification import GamificationService


class TestEmergencyBalanceModels:
    def test_status_parse(self):
        eb = EmergencyBalance.model_validate({"id": 12, "value": 35, "validity": "30 Days"})
        assert eb.value == 35.0
        assert eb.validity == "30 Days"
        assert eb.total_due == 0.0  # due/data_loan default 0

    def test_total_due_ceiling(self):
        eb = EmergencyBalance(due=34.95, data_loan=0.5)
        assert eb.total_due == 36  # ceil(34.95 + 0.5)

    def test_avail_success_statuses(self):
        assert EmergencyBalanceService.is_avail_success({"status": "PENDING"})
        assert EmergencyBalanceService.is_avail_success({"status": "success"})
        assert not EmergencyBalanceService.is_avail_success({"status": "failed"})
        assert not EmergencyBalanceService.is_avail_success({})

    def test_eligibility_rules(self):
        state = {
            "balance": 5.0,
            "emergency_balance": {"total": 0, "due": 0},
            "settings": {"eb_eligibility_balance": 18},
        }
        info = EmergencyBalanceService.eligibility(state)
        assert info["eligible"] is True
        # active loan blocks
        state["emergency_balance"]["total"] = 35
        assert EmergencyBalanceService.eligibility(state)["eligible"] is False
        # rich user blocked
        state["emergency_balance"]["total"] = 0
        state["balance"] = 50
        assert EmergencyBalanceService.eligibility(state)["eligible"] is False


class TestStreakModels:
    def test_streak_parse_with_claimable(self):
        info = DailyLoginStreakInfo.model_validate({
            "current_streak": 5,
            "last_unbroken_streak": 0,
            "milestone": [
                {"id": 1, "status": 3, "milestone_days": 3, "milestone_reward": 10},
                {"id": 2, "status": 2, "milestone_days": 5, "milestone_reward": 20},
                {"id": 3, "status": 1, "milestone_days": 7, "milestone_reward": 50},
            ],
            "settings": {"total_streak": 30, "milestones": []},
        })
        assert info.current_streak == 5
        assert info.settings.total_streak == 30
        assert len(info.claimable) == 1
        assert info.claimable[0].id == 2
        assert info.milestone[0].status_label == "claimed"
        assert info.milestone[1].status_label == "CLAIMABLE"

    def test_claim_result_semantics(self):
        assert ClaimResult(status="success", message="done").ok
        assert ClaimResult(status="PENDING").ok
        assert not ClaimResult(status="failed").ok

    def test_reward_point_balance(self):
        points = RewardPointBalance.model_validate({"point_balance": 120, "loyalty_status": 1})
        assert points.point_balance == 120
        assert points.loyalty_label == "enrolled"
        assert RewardPointBalance(loyalty_status=-3).loyalty_label == "not eligible"

    def test_milestone_defaults(self):
        milestone = StreakMilestone()
        assert milestone.status_label == "locked"


class TestServiceWireBodies:
    def test_claim_posts_milestone_id(self, make_client):
        client, rec = make_client()
        rec.add("POST", "/v2/gamification/daily-login/claim",
                json={"status": "success", "message": "claimed"})
        result = GamificationService(client).claim(7)
        import json as _json

        body = _json.loads(rec.requests[0].content)
        assert body == {"milestone_id": 7}
        assert result.ok

    def test_eb_avail_empty_body(self, make_client):
        client, rec = make_client()
        rec.add("POST", "/emergency-balance", json={"status": "PENDING"})
        response = EmergencyBalanceService(client).avail()
        import json as _json

        body = _json.loads(rec.requests[0].content)
        assert body == {}
        assert EmergencyBalanceService.is_avail_success(response)
