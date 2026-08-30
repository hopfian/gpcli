"""Network complaint (netcare) service.

Wire format (verified against the decompiled sources): ``GET common/v1/network-complain-feedbacks[/{id}]``,
``GET common/v1/network-complain-questionnaires``,
``POST common/v1/network-complain-feedbacks {questions: [{id, type, feedback}], meta?}``.
"""

from __future__ import annotations

from gpcli.client import ApiCaller, AuthMode

FEEDBACKS_ENDPOINT = "/common/v1/network-complain-feedbacks"
FEEDBACK_ENDPOINT = "/common/v1/network-complain-feedbacks/{id}"
QUESTIONNAIRES_ENDPOINT = "/common/v1/network-complain-questionnaires"


class NetworkComplainService:
    def __init__(self, client: ApiCaller):
        self.client = client

    def feedbacks(self) -> dict:
        return self.client.get_json("GET", FEEDBACKS_ENDPOINT, auth_mode=AuthMode.SUBSCRIBER)

    def feedback(self, feedback_id: str) -> dict:
        return self.client.get_json(
            "GET", FEEDBACK_ENDPOINT.format(id=feedback_id), auth_mode=AuthMode.SUBSCRIBER
        )

    def questionnaires(self) -> dict:
        return self.client.get_json("GET", QUESTIONNAIRES_ENDPOINT, auth_mode=AuthMode.SUBSCRIBER)

    def submit(self, answers: list[dict], *, meta: dict | None = None) -> dict:
        """`answers`: [{id, type, feedback}] — from `gpcli netcare questionnaires`."""
        body: dict = {
            "questions": [
                {"id": a["id"], "type": a["type"], "feedback": a["feedback"]}
                for a in answers
            ]
        }
        if meta:
            body["meta"] = meta
        return self.client.get_json(
            "POST", FEEDBACKS_ENDPOINT, json_body=body, auth_mode=AuthMode.SUBSCRIBER
        )
