import unittest
from unittest.mock import patch

from fastapi import HTTPException

from services.api_checker import server
from services.api_checker.algorithms.relay_audit import ProbeResult


class ServerContractTests(unittest.TestCase):
    def test_detectable_models_are_unique_and_stable(self):
        models = server._detectable_models()
        self.assertEqual(28, len(models))
        self.assertEqual(28, len({item["id"].lower() for item in models}))
        self.assertIn(models[0]["provider"], {"anthropic", "openai_compatible"})

    def test_models_api_describes_supported_algorithms(self):
        response = server.api_relay_models()
        algorithms = response["data"]["algorithms"]
        self.assertEqual(
            "仅支持 models 列表中的模型，可进行指纹识别和黑盒审计",
            algorithms["full"],
        )
        self.assertEqual(
            "仅支持 models 列表中的模型，进行快速检测",
            algorithms["quick"],
        )

    def test_validation_error_contract_uses_string_detail(self):
        detail = server._validation_error_detail([{
            "loc": ("body", "algorithm"),
            "msg": "Input should be 'full' or 'quick'",
            "input": "secret-value",
        }])

        self.assertIsInstance(detail, str)
        self.assertEqual(
            "body.algorithm: Input should be 'full' or 'quick'",
            detail,
        )
        self.assertNotIn("secret-value", detail)

        operation = server.app.openapi()["paths"][
            "/api/v1/relay/check/stream"
        ]["post"]
        schema = operation["responses"]["422"]["content"][
            "application/json"
        ]["schema"]
        self.assertEqual(
            "#/components/schemas/ErrorResponse",
            schema["$ref"],
        )

    def test_completed_rate_is_bounded_and_rounded(self):
        self.assertEqual(0.0, server._completed_rate(1, 0))
        self.assertEqual(0.0, server._completed_rate(-1, 100))
        self.assertEqual(0.66, server._completed_rate(66, 100))
        self.assertEqual(1.0, server._completed_rate(101, 100))

    def test_base_url_normalization(self):
        self.assertEqual(
            "https://api.example.test/v1",
            server.normalize_openai_base("https://api.example.test"),
        )
        self.assertEqual(
            "https://api.example.test/custom/v2",
            server.normalize_openai_base("https://api.example.test/custom/v2/"),
        )
        self.assertEqual(
            ("https://api.example.test/v1", "https://api.example.test"),
            server.anthropic_bases("https://api.example.test/v1"),
        )

    def test_request_rejects_non_http_url(self):
        request = server.DetectRequest(
            algorithm="quick",
            base_url="file:///etc/passwd",
            api_key="secret",
            model="model-a",
        )
        with self.assertRaises(HTTPException) as caught:
            request.check_url()
        self.assertEqual(400, caught.exception.status_code)

    def test_request_rejects_private_target_by_default(self):
        request = server.DetectRequest(
            algorithm="quick",
            base_url="https://127.0.0.1:8443",
            api_key="secret",
            model="model-a",
        )
        with patch.object(server, "ALLOW_PRIVATE_TARGETS", False):
            with self.assertRaises(HTTPException) as caught:
                request.check_url()
        self.assertEqual(400, caught.exception.status_code)

    def test_request_allows_explicit_trusted_http_target(self):
        request = server.DetectRequest(
            algorithm="quick",
            base_url="http://127.0.0.1:8443",
            api_key="secret",
            model="model-a",
        )
        with (
            patch.object(server, "ALLOW_HTTP_TARGETS", True),
            patch.object(server, "ALLOW_PRIVATE_TARGETS", True),
        ):
            request.check_url()

    def test_audit_keeps_probe_results_for_internal_verdict(self):
        result = {
            "verdict": "LOW",
            "score": 0,
            "findings": [],
            "probe_results": [
                ProbeResult("models", True, 123, data={"status": 200}),
            ],
        }
        request = server.DetectRequest(
            algorithm="quick",
            base_url="https://api.example.test/v1",
            api_key="secret",
            model="model-a",
        )
        with patch.object(server, "run_relay_audit", return_value=result):
            audit = server._run_audit(request, request.base_url)

        self.assertEqual(123, audit["probe_results"][0]["latency_ms"])
        self.assertTrue(audit["probe_results"][0]["ok"])
        self.assertEqual(
            {
                "latency_ms": None,
                "tokens_per_second": None,
                "input_tokens": None,
                "output_tokens": None,
                "cache_read_tokens": None,
            },
            audit["test_info"],
        )

    def test_audit_test_info_aggregates_usage_variants(self):
        probes = [
            ProbeResult("liveness", True, 1000, data={"usage": {
                "prompt_tokens": 100,
                "completion_tokens": 20,
                "prompt_tokens_details": {"cached_tokens": 40},
            }}),
            ProbeResult("identity", True, 500, data={"usage": {
                "input_tokens": 50,
                "output_tokens": 10,
                "cache_read_input_tokens": 25,
            }}),
            ProbeResult("models", True, 80, data={"status": 200}),
        ]

        self.assertEqual(
            {
                "latency_ms": 750,
                "tokens_per_second": 20.0,
                "input_tokens": 150,
                "output_tokens": 30,
                "cache_read_tokens": 65,
            },
            server._audit_test_info(probes),
        )

    def test_quick_detect_returns_result_when_audit_succeeds(self):
        audit = {
            "verdict": "LOW",
            "_risk_score": 5,
            "findings": [],
            "probe_results": [],
        }
        request = server.DetectRequest(
            algorithm="quick",
            base_url="https://api.example.test",
            api_key="secret",
            model="model-a",
        )
        with patch.object(server, "_run_audit", return_value=audit):
            result = server._run_detect(request)

        self.assertEqual("quick", result["algorithm"])
        self.assertEqual(95.0, result["score"])
        self.assertEqual("pass", result["overall_verdict"])
        self.assertNotIn("partial_errors", result)
        self.assertNotIn("checks", result["detail"])
        self.assertNotIn("signature", result["detail"])

    def test_result_detail_does_not_expose_internal_checks_or_signature(self):
        parts = {
            "audit": {
                "findings": [],
                "probe_results": [{"name": "models", "ok": True}],
            },
            "signature": {
                "verdict": "native",
                "_score": 98.5,
            },
        }

        detail = server._result_detail("quick", parts)

        self.assertNotIn("checks", detail)
        self.assertNotIn("signature", detail)
        self.assertNotIn("probe_results", detail)
        self.assertEqual({}, detail["test_info"])

    def test_overall_verdict_rejects_findings_and_partial_results(self):
        safe_audit = {
            "verdict": "LOW",
            "_risk_score": 0,
            "findings": [],
            "probe_results": [{"name": "models", "ok": True}],
        }
        risky_audit = {
            **safe_audit,
            "findings": [{"probe": "models", "severity": "MEDIUM", "title": "missing"}],
        }
        self.assertEqual(
            "pass",
            server._overall_verdict("quick", {"audit": safe_audit}, {}),
        )
        self.assertEqual(
            "risk",
            server._overall_verdict("quick", {"audit": risky_audit}, {}),
        )
        failed_probe_audit = {
            **safe_audit,
            "probe_results": [{"name": "identity", "ok": False}],
        }
        self.assertEqual(
            "risk",
            server._overall_verdict("quick", {"audit": failed_probe_audit}, {}),
        )
        self.assertEqual(
            "inconclusive",
            server._overall_verdict("quick", {"audit": safe_audit}, {"signature": "failed"}),
        )
        self.assertEqual(
            "inconclusive",
            server._overall_verdict(
                "full",
                {
                    "audit": safe_audit,
                    "fingerprint": {
                        "_posterior": 0.99,
                        "_forgery_status": None,
                    },
                },
                {},
            ),
        )
        self.assertEqual(
            "risk",
            server._overall_verdict(
                "full",
                {
                    "audit": safe_audit,
                    "fingerprint": {
                        "_posterior": 0.99,
                        "_forgery_status": "suspected_known",
                    },
                },
                {},
            ),
        )

    def test_sse_envelope_does_not_include_secret(self):
        event = server._sse("start", server._envelope({"algorithm": "quick"}, "started"))
        self.assertIn("event: start", event)
        self.assertNotIn("api_key", event)


if __name__ == "__main__":
    unittest.main()
