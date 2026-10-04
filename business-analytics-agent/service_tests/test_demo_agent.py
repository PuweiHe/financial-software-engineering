"""Exercise the browser agent against a real graph, tool schema and SQLite store."""

import json
import unittest
from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage
from portfolio_demo.agent_server import make_app, ScriptedModel


def events(response):
    return [
        (
            frame.splitlines()[0].removeprefix("event: "),
            json.loads(frame.splitlines()[1].removeprefix("data: ")),
        )
        for frame in response.text.replace("\r\n", "\n").strip().split("\n\n")
    ]


class DemoAgentTests(unittest.TestCase):
    def test_foreign_hosts_and_origins_are_rejected(self):
        with TestClient(make_app()) as client:
            payload = {"question": "Revenue in 2025?"}
            self.assertEqual(
                client.post(
                    "/api/agent/stream", json=payload, headers={"origin": "https://example.com"}
                ).status_code,
                403,
            )
            self.assertEqual(
                client.get("/api/years", headers={"host": "example.com"}).status_code, 400
            )

    def test_tool_evidence_preserves_missing_baseline(self):
        with TestClient(make_app()) as client:
            result = events(
                client.post(
                    "/api/agent/stream",
                    json={"question": "Revenue share and growth for BRANCH003 in 2025?"},
                )
            )
        report = next(data for kind, data in result if kind == "report")
        self.assertEqual(report["selected_branch"]["share"], 0.2)
        self.assertIsNone(report["selected_branch"]["growth"])
        self.assertEqual(result[-1][0], "done")

    def test_ambiguous_year_requests_clarification_without_query(self):
        with TestClient(make_app()) as client:
            result = events(
                client.post("/api/agent/stream", json={"question": "Revenue in 2024 and 2025?"})
            )
        self.assertNotIn("report", [kind for kind, _ in result])
        self.assertTrue(
            any(kind == "answer" and "one year" in data["text"] for kind, data in result)
        )

    def test_unavailable_year_never_returns_invented_metrics(self):
        with TestClient(make_app()) as client:
            result = events(client.post("/api/agent/stream", json={"question": "Revenue in 2020?"}))
        self.assertNotIn("report", [kind for kind, _ in result])
        self.assertTrue(any(data.get("message", "").startswith("No report") for _, data in result))

    def test_invalid_model_arguments_cannot_query_database(self):
        def model(question):
            return ScriptedModel(
                disable_streaming=True,
                messages=iter(
                    [
                        AIMessage(
                            content="",
                            tool_calls=[
                                {
                                    "name": "branch_report",
                                    "args": {"year": 2025, "branch_id": "' OR 1=1"},
                                    "id": "invalid",
                                }
                            ],
                        ),
                        AIMessage(content="Unable to query that branch."),
                    ]
                ),
            )

        with TestClient(make_app(model_factory=model)) as client:
            result = events(client.post("/api/agent/stream", json={"question": "Revenue in 2025?"}))
        self.assertNotIn("report", [kind for kind, _ in result])

    def test_provider_failure_is_redacted(self):
        def broken(question):
            raise RuntimeError("private-provider-detail")

        with TestClient(make_app(model_factory=broken)) as client:
            response = client.post("/api/agent/stream", json={"question": "Revenue in 2025?"})
        self.assertNotIn("private-provider-detail", response.text)
        self.assertEqual(events(response)[-1][0], "error")

    def test_question_size_and_unknown_fields_are_rejected(self):
        with TestClient(make_app()) as client:
            for payload in (
                {"question": "x" * 501},
                {"question": " "},
                {"question": "Revenue in 2025?", "sql": "SELECT *"},
            ):
                self.assertEqual(client.post("/api/agent/stream", json=payload).status_code, 422)

    def test_sequential_requests_do_not_reuse_evidence(self):
        with TestClient(make_app()) as client:
            client.post("/api/agent/stream", json={"question": "Revenue in 2025?"})
            result = events(client.post("/api/agent/stream", json={"question": "Revenue?"}))
        self.assertNotIn("report", [kind for kind, _ in result])
