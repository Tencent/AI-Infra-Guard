import asyncio
import hashlib
import json
import logging
import unittest
from unittest.mock import patch

from fastapi import HTTPException

from services.api_checker import server
from services.api_checker.algorithms.relay_audit import ProbeResult


def fully_evaluable_probe_results():
    return [
        {
            "name": "models",
            "ok": True,
            "data": {"status": 200, "target_model_present": True},
        },
        {
            "name": "liveness",
            "ok": True,
            "data": {"status": 200, "truncated": False},
        },
        {
            "name": "identity",
            "ok": True,
            "data": {
                "status": 200,
                "identity_text": "I am GPT.",
                "requested_families": ["openai"],
                "identity_families": ["openai"],
            },
        },
        {
            "name": "glitch_fingerprint",
            "ok": True,
            "data": {
                "status": 200,
                "analyzable": True,
                "requested_families": ["openai"],
                "best_family": "openai",
                "candidate_families": [{
                    "family": "openai",
                    "consistent": True,
                }],
            },
        },
        {
            "name": "token_delta",
            "ok": True,
            "data": {"status": 200, "delta": 0},
        },
        {
            "name": "echo_rewrite",
            "ok": True,
            "data": {
                "status": 200,
                "truncated": False,
                "exact_match": True,
                "suspicious_terms": [],
            },
        },
        {
            "name": "stream_integrity",
            "ok": True,
            "data": {"chunk_count": 2, "stream_models": ["model-a"]},
        },
        {
            "name": "context_canary",
            "ok": True,
            "data": {"status": 200, "saw_end": True, "truncated": False},
        },
    ]


class ServerContractTests(unittest.TestCase):
    def setUp(self):
        def fake_model_summary(
            req,
            algorithm,
            parts,
            errors,
            _base_url,
            _api_type,
            _claude,
            on_request=None,
            cancel_event=None,
        ):
            if on_request:
                on_request(True)
            return server._result_summary(
                algorithm,
                parts,
                errors,
                req.language,
            )

        summary_patch = patch.object(
            server,
            "_model_result_summary",
            side_effect=fake_model_summary,
        )
        summary_patch.start()
        self.addCleanup(summary_patch.stop)

    def test_detectable_models_are_unique_and_stable(self):
        models = server._detectable_models()
        self.assertEqual(29, len(models))
        self.assertEqual(29, len({item["id"].lower() for item in models}))
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

    def test_quick_progress_preserves_actual_request_counts(self):
        self.assertEqual({
            "completed": 6,
            "total": 14,
            "success": 5,
            "error": 1,
        }, server._quick_progress(6, 14, 5, 1))

    def test_api_key_log_identity_contains_only_suffix_and_sha256(self):
        api_key = "sk-test-super-secret-xyz"
        fields = server._api_key_log_fields(api_key)

        self.assertEqual("xyz", fields["api_key_suffix"])
        self.assertEqual(
            hashlib.sha256(api_key.encode("utf-8")).hexdigest(),
            fields["api_key_sha256"],
        )
        self.assertNotIn(api_key, json.dumps(fields))

        with patch.object(server.LOGGER, "log") as log:
            server._log_event(
                logging.INFO,
                "detection_received",
                request_id="request-1",
                **fields,
            )
        payload_text = log.call_args.args[1]
        payload = json.loads(payload_text)
        self.assertEqual("detection_received", payload["event"])
        self.assertEqual("request-1", payload["request_id"])
        self.assertNotIn(api_key, payload_text)

    def test_request_id_and_log_redaction(self):
        self.assertEqual("trace-123", server._request_id("trace-123"))
        generated = server._request_id("invalid request id")
        self.assertRegex(generated, r"^[0-9a-f]{32}$")
        self.assertEqual(
            "upstream rejected [REDACTED]",
            server._redact_log_text(
                "upstream rejected secret-key",
                "secret-key",
            ),
        )

    def test_http_errors_return_request_id(self):
        request = server.Request({
            "type": "http",
            "method": "POST",
            "path": "/api/v1/relay/check/stream",
            "headers": [(b"x-request-id", b"trace-http-error")],
            "query_string": b"",
            "scheme": "http",
            "server": ("testserver", 80),
            "client": ("127.0.0.1", 12345),
        })
        response = asyncio.run(server.http_exception_handler(
            request,
            HTTPException(429, "busy"),
        ))

        self.assertEqual(429, response.status_code)
        self.assertEqual("trace-http-error", response.headers["X-Request-ID"])
        self.assertEqual({"detail": "busy"}, json.loads(response.body))

    def test_fingerprint_progress_preserves_sample_counts(self):
        request = server.DetectRequest(
            algorithm="full",
            base_url="https://api.example.test",
            api_key="secret",
            model="model-a",
        )
        progress_events = []

        def fake_test_model(*args):
            progress = args[6]
            progress(120, 200, 118, 2)
            return {
                "bayes": {
                    "best_model_name": "model-a",
                    "best_posterior": 0.9,
                    "second_model_name": "model-b",
                    "evidence_level": "strong",
                    "top5": [
                        {"name": "model-a", "posterior": 0.9},
                        {"name": "model-b", "posterior": 0.08},
                    ],
                },
                "results": [7] * 200,
            }

        with (
            patch.object(server, "test_model", side_effect=fake_test_model),
            patch.object(server, "_resolve_baseline_name", return_value="model-a"),
            patch.object(server, "load_baselines", return_value=[{
                "name": "model-a",
                "distribution": [0.0] * 6 + [1.0] + [0.0] * 348,
            }]),
        ):
            result = server._run_fingerprint(
                request,
                "openai",
                "https://api.example.test/v1",
                progress_events.append,
            )

        self.assertEqual([{
            "completed": 120,
            "total": 200,
            "success": 118,
            "error": 2,
        }], progress_events)
        self.assertEqual(200, result["_visualization"]["sample_size"])
        self.assertEqual("model-b", result["_runner_up_model"])
        self.assertEqual(0.08, result["_runner_up_posterior"])
        self.assertEqual("strong", result["_evidence_level"])

    def test_fingerprint_visualization_aggregates_observed_and_reference(self):
        reference = [0.0] * 355
        reference[6] = 0.5
        reference[354] = 0.5
        with patch.object(server, "load_baselines", return_value=[{
            "name": "model-a",
            "model": "provider/model-a",
            "distribution": reference,
        }]):
            visualization = server._fingerprint_visualization(
                [7] * 120 + [355] * 80,
                "model-a",
            )

        self.assertEqual(200, visualization["sample_size"])
        self.assertEqual(1, visualization["candidate_count"])
        self.assertEqual([1, 355], visualization["range"])
        self.assertEqual(48, len(visualization["observed_distribution"]))
        self.assertEqual(48, len(visualization["reference_distribution"]))
        self.assertAlmostEqual(
            1.0,
            sum(visualization["observed_distribution"]),
        )
        self.assertAlmostEqual(
            1.0,
            sum(visualization["reference_distribution"]),
        )
        self.assertEqual(0.9, visualization["distribution_overlap"])
        self.assertEqual({
            "range": [1, 8],
            "observed": 0.6,
            "reference": 0.5,
            "difference": 0.1,
        }, visualization["largest_deviation"])

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
            "https://api.example.test/v1",
            server.normalize_openai_base(
                "https://api.example.test/v1/chat/completions"
            ),
        )
        self.assertEqual(
            "https://api.example.test/api/v3",
            server.normalize_openai_base(
                "https://api.example.test/api/v3/responses"
            ),
        )
        self.assertEqual(
            "openai",
            server.openai_api_type(
                "https://api.example.test/v1/chat/completions"
            ),
        )
        self.assertEqual(
            "openai-responses",
            server.openai_api_type(
                "https://api.example.test/api/v3/responses"
            ),
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

    def test_result_language_defaults_to_chinese(self):
        request = server.DetectRequest(
            algorithm="quick",
            base_url="https://api.example.test/v1",
            api_key="secret",
            model="model-a",
        )

        self.assertEqual("zh", request.language)
        schema = server.app.openapi()["components"]["schemas"]["DetectRequest"]
        self.assertEqual("zh", schema["properties"]["language"]["default"])
        self.assertEqual(
            ["zh", "en"],
            schema["properties"]["language"]["enum"],
        )

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
            {"status": 200},
            audit["probe_results"][0]["data"],
        )
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

    def test_audit_test_info_reads_deepseek_cache_hits(self):
        probes = [
            ProbeResult("liveness", True, 200, data={"usage": {
                "prompt_tokens": 96,
                "completion_tokens": 4,
                "prompt_cache_hit_tokens": 64,
                "prompt_cache_miss_tokens": 32,
            }}),
        ]

        self.assertEqual(
            {
                "latency_ms": 200,
                "tokens_per_second": 20.0,
                "input_tokens": 96,
                "output_tokens": 4,
                "cache_read_tokens": 64,
            },
            server._audit_test_info(probes),
        )

    def test_audit_test_info_keeps_zero_deepseek_cache_hits(self):
        probes = [
            ProbeResult("identity", True, 100, data={"usage": {
                "prompt_tokens": 12,
                "completion_tokens": 2,
                "prompt_cache_hit_tokens": 0,
                "prompt_cache_miss_tokens": 12,
            }}),
        ]

        self.assertEqual(0, server._audit_test_info(probes)["cache_read_tokens"])

    def test_audit_test_info_supports_provider_usage_matrix(self):
        cases = {
            "siliconflow": ({
                "prompt_tokens": 9,
                "completion_tokens": 1,
                "prompt_cache_hit_tokens": 0,
            }, (9, 1, 0)),
            "openrouter": ({
                "prompt_tokens": 12,
                "completion_tokens": 1,
                "prompt_tokens_details": {"cached_tokens": 2},
            }, (12, 1, 2)),
            "aliyun": ({
                "prompt_tokens": 15,
                "completion_tokens": 3,
            }, (15, 3, None)),
            "tencent": ({
                "prompt_tokens": 20,
                "completion_tokens": 2,
                "prompt_tokens_details": {"cached_tokens": 4},
            }, (20, 2, 4)),
            "volcengine-responses": ({
                "input_tokens": 20,
                "output_tokens": 3,
                "input_tokens_details": {"cached_tokens": 5},
            }, (20, 3, 5)),
            "deepseek": ({
                "prompt_tokens": 9,
                "completion_tokens": 8,
                "prompt_cache_hit_tokens": 6,
            }, (9, 8, 6)),
            "minimax": ({
                "prompt_tokens": 46,
                "completion_tokens": 8,
                "prompt_tokens_details": {"cached_tokens": 7},
            }, (46, 8, 7)),
            "bigmodel": ({
                "prompt_tokens": 17,
                "completion_tokens": 8,
                "prompt_tokens_details": {"cached_tokens": 3},
            }, (17, 8, 3)),
            "moonshot": ({
                "prompt_tokens": 12,
                "completion_tokens": 8,
                "cached_tokens": 1,
            }, (12, 8, 1)),
        }
        for provider, (usage, expected) in cases.items():
            with self.subTest(provider=provider):
                info = server._audit_test_info([
                    ProbeResult(
                        "liveness",
                        True,
                        100,
                        data={"usage": usage},
                    ),
                ])
                self.assertEqual(expected[0], info["input_tokens"])
                self.assertEqual(expected[1], info["output_tokens"])
                self.assertEqual(expected[2], info["cache_read_tokens"])

    def test_full_responses_endpoint_selects_responses_protocol(self):
        audit = {
            "verdict": "LOW",
            "_risk_score": 0,
            "findings": [],
            "probe_results": [{"name": "models", "ok": True}],
        }
        fingerprint = {
            "best_model": "Doubao",
            "_posterior": 0.9,
            "_forgery_status": "supported",
        }
        request = server.DetectRequest(
            algorithm="full",
            base_url="https://api.example.test/api/v3/responses",
            api_key="secret",
            model="doubao-test",
            iterations=50,
        )

        with (
            patch.object(server, "_run_audit", return_value=audit) as audit_call,
            patch.object(
                server,
                "_run_fingerprint",
                return_value=fingerprint,
            ) as fingerprint_call,
        ):
            server._run_detect(request)

        self.assertEqual(
            "openai-responses",
            audit_call.call_args.kwargs["api_type"],
        )
        self.assertEqual(
            "openai-responses",
            fingerprint_call.call_args.args[1],
        )
        self.assertEqual(
            "https://api.example.test/api/v3",
            fingerprint_call.call_args.args[2],
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

    def test_fingerprint_score_is_authenticity_not_alternative_confidence(self):
        self.assertEqual(100.0, server._fingerprint_score({
            "_posterior": 1.0,
            "_forgery_status": "supported",
        }))
        self.assertEqual(70.0, server._fingerprint_score({
            "_posterior": 1.0,
            "_forgery_status": "suspected_known",
        }))
        self.assertEqual(70.0, server._fingerprint_score({
            "_posterior": 0.99,
            "_forgery_status": "unknown_anomaly",
        }))
        self.assertEqual(70.0, server._fingerprint_score({
            "_posterior": 0.1,
            "_forgery_status": "unknown_anomaly",
        }))
        self.assertEqual(70.0, server._fingerprint_score({
            "_posterior": 0.2,
            "_forgery_status": "supported",
        }))

        parts = {
            "audit": {
                "verdict": "LOW",
                "_risk_score": 0,
                "findings": [],
                "probe_results": [],
            },
            "fingerprint": {
                "_posterior": 1.0,
                "_forgery_status": "suspected_known",
            },
        }
        self.assertEqual(70.0, server._result_score("full", parts))
        self.assertEqual(
            70.0,
            server._summary_component_scores(parts)["fingerprint"],
        )

    def test_failed_components_can_never_contribute_a_full_score(self):
        risky_audit = {
            "verdict": "LOW",
            "_risk_score": 0,
            "findings": [{
                "probe": "models",
                "severity": "HIGH",
                "title": "Model list endpoint failed",
            }],
            "probe_results": [],
        }
        failed_signature = {
            "verdict": "proxy",
            "_score": 100,
            "_failed_checks": [{"name": "signature"}],
        }

        self.assertEqual(50.0, server._audit_score(risky_audit))
        self.assertEqual(80.0, server._signature_score(failed_signature))
        self.assertEqual(
            "risk",
            server._overall_verdict("quick", {"audit": risky_audit}, {}),
        )
        self.assertLess(
            server._result_score("quick", {"audit": risky_audit}),
            100.0,
        )

        weighted_identity_risk = {
            "verdict": "LOW",
            "_risk_score": 15,
            "findings": [{
                "probe": "identity",
                "severity": "LOW",
                "title": "Model identity family mismatch",
            }],
            "probe_results": [{
                "name": "identity",
                "ok": True,
                "data": {
                    "status": 200,
                    "identity_text": "I am GPT-5.",
                    "requested_families": ["anthropic"],
                    "identity_families": ["openai"],
                },
            }],
        }
        self.assertEqual(85.0, server._audit_score(weighted_identity_risk))
        self.assertEqual(
            85.0,
            server._result_score("quick", {"audit": weighted_identity_risk}),
        )
        self.assertEqual(
            "risk",
            server._overall_verdict(
                "quick", {"audit": weighted_identity_risk}, {},
            ),
        )

        inconsistent_audit = {
            "verdict": "HIGH",
            "_risk_score": 0,
            "findings": [],
            "probe_results": [],
        }
        detail = server._result_detail(
            "quick",
            {"audit": inconsistent_audit},
            "zh",
        )
        self.assertIn({
            "probe": "audit",
            "severity": "Failed",
            "title": "黑盒审计综合检查",
        }, detail["findings"])

    def test_confirmed_risk_takes_precedence_over_incomplete_components(self):
        risky_audit = {
            "verdict": "HIGH",
            "_risk_score": 50,
            "findings": [],
            "probe_results": [],
        }
        parts = {"audit": risky_audit}
        errors = {"signature": "timeout"}

        self.assertEqual(
            "risk",
            server._overall_verdict("quick", parts, errors),
        )
        self.assertEqual(0.0, server._result_score("quick", parts, errors))

    def test_risk_level_uses_safety_score_boundaries(self):
        cases = (
            (0, "risk", "high"),
            (29.9, "risk", "high"),
            (30, "risk", "medium"),
            (69.9, "risk", "medium"),
            (70, "risk", "low"),
            (99.9, "risk", "low"),
            (91, "pass", "none"),
            (0, "inconclusive", "unknown"),
        )
        for score, verdict, expected in cases:
            with self.subTest(score=score, verdict=verdict):
                self.assertEqual(
                    expected,
                    server._risk_level(score, verdict),
                )

    def test_incomplete_fingerprint_scores_50_without_exceptions(self):
        malformed_audit = {
            "verdict": "LOW",
            "_risk_score": "zero",
            "findings": [],
            "probe_results": [],
        }
        malformed_fingerprint = {
            "_posterior": "certain",
            "_forgery_status": "supported",
        }

        self.assertEqual(0.0, server._audit_score(malformed_audit))
        self.assertEqual(50.0, server._fingerprint_score(malformed_fingerprint))
        self.assertEqual(50.0, server._fingerprint_score({}))
        safe_audit = {
            "verdict": "LOW",
            "_risk_score": 0,
            "findings": [],
            "probe_results": [],
        }
        self.assertEqual(
            50.0,
            server._result_score(
                "full",
                {"audit": safe_audit},
                {"fingerprint": "timeout"},
            ),
        )
        self.assertEqual(
            50.0,
            server._result_score("full", {"audit": safe_audit}, {}),
        )
        self.assertEqual(
            50.0,
            server._summary_component_scores(
                {"audit": safe_audit},
                "full",
                {"fingerprint": "timeout"},
            )["fingerprint"],
        )
        self.assertEqual(
            "inconclusive",
            server._overall_verdict(
                "quick",
                {"audit": malformed_audit},
                {},
            ),
        )

    def test_quick_signature_uses_resolved_model_id(self):
        audit = {
            "verdict": "LOW",
            "_risk_score": 0,
            "_resolved_model": "claude-sonnet-5",
            "findings": [],
            "probe_results": [],
        }
        signature = {
            "verdict": "native",
            "_score": 100,
            "_failed_checks": [],
        }
        request = server.DetectRequest(
            algorithm="quick",
            base_url="https://api.example.test/v1",
            api_key="secret",
            model="anthropic/claude-sonnet-5",
        )

        with (
            patch.object(server, "_run_audit", return_value=audit),
            patch.object(
                server,
                "_run_signature",
                return_value=signature,
            ) as signature_call,
        ):
            result = server._run_detect(request)

        self.assertEqual(
            "claude-sonnet-5",
            signature_call.call_args.args[0].model,
        )
        self.assertNotIn("_resolved_model", result["detail"])

    def test_quick_claude_progress_combines_actual_requests(self):
        audit = {
            "verdict": "LOW",
            "_risk_score": 0,
            "findings": [],
            "probe_results": [],
        }
        signature = {
            "verdict": "native",
            "_score": 100,
            "_failed_checks": [],
        }
        request = server.DetectRequest(
            algorithm="quick",
            base_url="https://api.example.test",
            api_key="secret",
            model="claude-sonnet-5",
        )
        progress = []

        def fake_audit(_req, _base_url, _cancel_event, on_progress, _api_type):
            for completed in range(1, server.QUICK_AUDIT_REQUEST_COUNT + 1):
                on_progress({
                    "completed": completed,
                    "total": server.QUICK_AUDIT_REQUEST_COUNT,
                    "success": completed,
                    "error": 0,
                })
            return audit

        def fake_signature(_req, _base_url, _cancel_event, on_progress):
            for completed in range(
                1,
                server.SIGNATURE_QUICK_REQUEST_COUNT + 1,
            ):
                on_progress(
                    completed,
                    server.SIGNATURE_QUICK_REQUEST_COUNT,
                    completed,
                    0,
                )
            return signature

        with (
            patch.object(server, "_run_audit", side_effect=fake_audit),
            patch.object(server, "_run_signature", side_effect=fake_signature),
        ):
            server._run_detect(request, on_progress=progress.append)

        total_requests = (
            server.QUICK_AUDIT_REQUEST_COUNT
            + server.SIGNATURE_QUICK_REQUEST_COUNT
            + server.SUMMARY_REQUEST_COUNT
        )
        expected = [
            server._quick_progress(
                completed,
                total_requests,
                completed,
                0,
            )
            for completed in range(1, server.QUICK_AUDIT_REQUEST_COUNT + 1)
        ]
        expected.extend(
            server._quick_progress(
                server.QUICK_AUDIT_REQUEST_COUNT + completed,
                total_requests,
                server.QUICK_AUDIT_REQUEST_COUNT + completed,
                0,
            )
            for completed in range(
                1,
                server.SIGNATURE_QUICK_REQUEST_COUNT + 1,
            )
        )
        expected.append(server._quick_progress(
            total_requests,
            total_requests,
            total_requests,
            0,
        ))

        self.assertEqual(expected, progress)
        self.assertEqual({
            "completed": 16,
            "total": 16,
            "success": 16,
            "error": 0,
        }, progress[-1])

    def test_quick_result_localizes_summary_and_title(self):
        audit = {
            "verdict": "HIGH",
            "_risk_score": 50,
            "findings": [{
                "probe": "liveness",
                "severity": "HIGH",
                "title": "Relay liveness failed",
            }],
            "probe_results": [{"name": "liveness", "ok": False}],
        }
        chinese_request = server.DetectRequest(
            algorithm="quick",
            base_url="https://api.example.test",
            api_key="secret",
            model="model-a",
        )
        english_request = server.DetectRequest(
            algorithm="quick",
            base_url="https://api.example.test",
            api_key="secret",
            model="model-a",
            language="en",
        )

        with patch.object(server, "_run_audit", return_value=audit):
            chinese = server._run_detect(chinese_request)
            english = server._run_detect(english_request)

        self.assertEqual(
            "综合评分50/100，检测发现异常，主要涉及黑盒审计",
            chinese["summary"],
        )
        self.assertEqual("medium", chinese["risk_level"])
        self.assertEqual("medium", english["risk_level"])
        self.assertIn(
            {
                "probe": "liveness",
                "severity": "Failed",
                "title": "中转服务连通性专项检查",
            },
            chinese["detail"]["findings"],
        )
        self.assertEqual(
            "Overall score 50/100; a risk was detected in black-box audit.",
            english["summary"],
        )
        self.assertIn(
            {
                "probe": "liveness",
                "severity": "Failed",
                "title": "Relay liveness risk check",
            },
            english["detail"]["findings"],
        )

    def test_full_result_uses_concise_english_summary(self):
        audit = {
            "verdict": "LOW",
            "_risk_score": 0,
            "_resolved_model": "gpt-4o-mini",
            "findings": [],
            "probe_results": [{"name": "models", "ok": True}],
        }
        fingerprint = {
            "best_model": "GPT-4o-mini",
            "_posterior": 0.91,
            "_forgery_status": "supported",
        }
        request = server.DetectRequest(
            algorithm="full",
            base_url="https://api.example.test",
            api_key="secret",
            model="openai/gpt-4o-mini",
            language="en",
            iterations=50,
        )

        with (
            patch.object(server, "_run_audit", return_value=audit),
            patch.object(
                server,
                "_run_fingerprint",
                return_value=fingerprint,
            ) as fingerprint_call,
        ):
            result = server._run_detect(request)

        self.assertEqual(
            "gpt-4o-mini",
            fingerprint_call.call_args.args[0].model,
        )
        self.assertEqual("pass", result["overall_verdict"])
        self.assertEqual("none", result["risk_level"])
        self.assertEqual(
            "Overall score 91/100; checks passed with lower confidence in model fingerprint.",
            result["summary"],
        )

    def test_result_detail_does_not_expose_internal_checks_or_signature(self):
        parts = {
            "audit": {
                "verdict": "LOW",
                "_risk_score": 0,
                "findings": [],
                "probe_results": [{
                    "name": "models",
                    "ok": True,
                    "data": {"status": 200, "target_model_present": True},
                }],
            },
            "signature": {
                "verdict": "native",
                "_score": 98.5,
                "_failed_checks": [],
            },
        }

        detail = server._result_detail("quick", parts)

        self.assertNotIn("checks", detail)
        self.assertNotIn("signature", detail)
        self.assertNotIn("probe_results", detail)
        self.assertEqual({}, detail["test_info"])
        self.assertEqual("Passed", detail["findings"][0]["severity"])
        self.assertEqual(
            "模型列表检查",
            detail["findings"][0]["title"],
        )
        signature_finding = next(
            finding for finding in detail["findings"]
            if finding["probe"] == "signature"
        )
        self.assertEqual("Passed", signature_finding["severity"])
        self.assertEqual(
            "Claude 签名验证",
            signature_finding["title"],
        )

    def test_signature_failure_caps_score_and_explains_risk(self):
        audit = {
            "verdict": "LOW",
            "_risk_score": 0,
            "findings": [],
            "probe_results": [
                {"name": "models", "ok": True},
                {"name": "liveness", "ok": True},
            ],
        }
        signature = {
            "verdict": "proxy",
            "_score": 35,
            "_failed_checks": [{
                "name": "Thinking Signature",
                "detail": "未返回 signature",
                "critical": True,
            }],
        }
        request = server.DetectRequest(
            algorithm="quick",
            base_url="https://api.example.test",
            api_key="secret",
            model="claude-sonnet-5",
        )

        with (
            patch.object(server, "_run_audit", return_value=audit),
            patch.object(server, "_run_signature", return_value=signature),
        ):
            result = server._run_detect(request)

        self.assertEqual(80.0, result["score"])
        self.assertEqual("risk", result["overall_verdict"])
        self.assertEqual("low", result["risk_level"])
        self.assertEqual(
            "综合评分80/100，检测发现异常，主要涉及签名验证",
            result["summary"],
        )
        signature_finding = result["detail"]["findings"][-1]
        self.assertEqual("signature", signature_finding["probe"])
        self.assertEqual("Failed", signature_finding["severity"])
        self.assertEqual("Claude 签名验证", signature_finding["title"])

    def test_incomplete_component_controls_summary(self):
        audit = {
            "verdict": "LOW",
            "_risk_score": 0,
            "findings": [],
            "probe_results": [{"name": "models", "ok": True}],
        }
        request = server.DetectRequest(
            algorithm="quick",
            base_url="https://api.example.test",
            api_key="secret",
            model="claude-sonnet-5",
        )
        component_errors = []

        with (
            patch.object(server, "_run_audit", return_value=audit),
            patch.object(
                server,
                "_run_signature",
                side_effect=RuntimeError("signature unavailable"),
            ),
        ):
            result = server._run_detect(
                request,
                on_component_error=lambda component, error: (
                    component_errors.append((component, str(error)))
                ),
            )

        self.assertEqual("inconclusive", result["overall_verdict"])
        self.assertEqual("unknown", result["risk_level"])
        self.assertEqual(
            [("signature", "signature unavailable")],
            component_errors,
        )
        self.assertEqual(
            "综合评分0/100，检测证据不足，结果不完整",
            result["summary"],
        )
        self.assertEqual(0.0, result["score"])

    def test_result_detail_returns_all_probe_statuses(self):
        parts = {
            "audit": {
                "findings": [{
                    "probe": "identity",
                    "severity": "LOW",
                    "title": "Model identity family mismatch",
                }],
                "probe_results": [
                    {
                        "name": "models",
                        "ok": True,
                        "data": {"status": 200, "target_model_present": True},
                    },
                    {
                        "name": "identity",
                        "ok": True,
                        "data": {
                            "status": 200,
                            "identity_text": "I am GPT.",
                            "requested_families": ["openai"],
                            "identity_families": ["anthropic"],
                        },
                    },
                    {
                        "name": "stream_integrity",
                        "ok": False,
                        "error": "stream unavailable",
                        "data": {},
                    },
                ],
            },
        }

        chinese = server._result_detail("quick", parts, "zh")
        english = server._result_detail("quick", parts, "en")

        self.assertEqual(
            ["Passed", "Passed", "Failed"],
            [
                finding["severity"]
                for finding in chinese["findings"][:3]
            ],
        )
        self.assertEqual(
            [
                "模型列表检查",
                "模型身份检查",
                "流式响应完整性检查",
            ],
            [
                finding["title"]
                for finding in chinese["findings"][:3]
            ],
        )
        self.assertEqual(
            "Model list check",
            english["findings"][0]["title"],
        )
        self.assertEqual(
            "Stream integrity check",
            english["findings"][2]["title"],
        )
        self.assertIn(
            {
                "probe": "identity",
                "severity": "Failed",
                "title": "模型身份系列匹配检查",
            },
            chinese["findings"],
        )

    def test_all_20_audit_checks_return_passed_or_failed(self):
        probe_results = fully_evaluable_probe_results()
        safe_parts = {
            "audit": {
                "verdict": "LOW",
                "_risk_score": 0,
                "findings": [],
                "probe_results": probe_results,
            },
        }

        chinese = server._result_detail("full", safe_parts, "zh")["findings"]
        english = server._result_detail("full", safe_parts, "en")["findings"]
        self.assertEqual(20, len(chinese))
        self.assertTrue(all(item["severity"] == "Passed" for item in chinese))
        self.assertTrue(all("通过" not in item["title"] for item in chinese))
        self.assertTrue(all(item["severity"] == "Passed" for item in english))
        self.assertTrue(all("passed" not in item["title"].lower() for item in english))

        for risk_check in server.SPECIALIZED_RISK_CHECKS:
            with self.subTest(risk=risk_check["failed_title"]):
                parts = {
                    "audit": {
                        "findings": [{
                            "probe": risk_check["probe"],
                            "severity": "HIGH",
                            "title": risk_check["failed_title"],
                        }],
                        "probe_results": probe_results,
                    },
                }
                result = server._result_detail("full", parts, "zh")["findings"]
                failures = [
                    item for item in result
                    if item["severity"] == "Failed"
                ]
                self.assertEqual(1, len(failures))
                self.assertEqual(
                    risk_check["title"]["zh"],
                    failures[0]["title"],
                )

        for failed_probe in server.PROBE_CHECK_TITLE:
            with self.subTest(base_probe=failed_probe):
                failed_results = [
                    {
                        **item,
                        "ok": item["name"] != failed_probe,
                    }
                    for item in probe_results
                ]
                parts = {
                    "audit": {
                        "findings": [],
                        "probe_results": failed_results,
                    },
                }
                result = server._result_detail("full", parts, "zh")["findings"]
                self.assertIn({
                    "probe": failed_probe,
                    "severity": "Failed",
                    "title": server._probe_status_title(
                        failed_probe,
                        False,
                        "zh",
                    ),
                }, result)

    def test_insufficient_specialized_checks_are_omitted(self):
        parts = {
            "audit": {
                "findings": [{
                    "probe": "models",
                    "severity": "MEDIUM",
                    "title": "Model list endpoint failed",
                }],
                "probe_results": [
                    {
                        "name": "models",
                        "ok": False,
                        "error": "HTTP 503",
                        "data": {},
                    },
                    {
                        "name": "identity",
                        "ok": True,
                        "data": {
                            "status": 200,
                            "identity_text": "I am model-a.",
                            "requested_families": [],
                            "identity_families": [],
                        },
                    },
                    {
                        "name": "token_delta",
                        "ok": True,
                        "data": {"status": 200, "delta": None},
                    },
                    {
                        "name": "context_canary",
                        "ok": False,
                        "error": "audit exceeded total timeout",
                        "data": {"not_executed": True},
                    },
                ],
            },
        }

        findings = server._result_detail("quick", parts, "zh")["findings"]
        titles = {finding["title"] for finding in findings}

        self.assertIn("模型列表检查", titles)
        self.assertIn("模型列表接口调用检查", titles)
        self.assertIn("模型身份检查", titles)
        self.assertNotIn("请求模型存在性检查", titles)
        self.assertNotIn("模型身份系列匹配检查", titles)
        self.assertNotIn("提示词 Token 差异检查", titles)
        self.assertNotIn("提示词 Token 数量偏差检查", titles)
        self.assertNotIn("上下文完整性检查", titles)
        self.assertNotIn("上下文截断检查", titles)
        self.assertTrue(all(
            finding["severity"] in {"Passed", "Failed"}
            for finding in findings
        ))

    def test_signature_requires_complete_evidence_and_no_failed_checks(self):
        incomplete = {
            "verdict": "native",
            "_score": 92,
        }
        partially_failed = {
            "verdict": "native",
            "_score": 92,
            "_failed_checks": [{
                "name": "响应头指纹",
                "detail": "missing",
                "critical": False,
            }],
        }

        self.assertIsNone(server._signature_finding(incomplete))
        finding = server._signature_finding(partially_failed)
        self.assertEqual("Failed", finding["severity"])
        self.assertEqual(
            "risk",
            server._overall_verdict(
                "quick",
                {
                    "audit": {
                        "verdict": "LOW",
                        "_risk_score": 0,
                        "findings": [],
                        "probe_results": [],
                    },
                    "signature": partially_failed,
                },
                {},
            ),
        )

    def test_incomplete_fingerprint_finding_is_omitted(self):
        self.assertIsNone(server._fingerprint_finding({
            "best_model": "model-a",
            "_posterior": 0.95,
            "_forgery_status": None,
        }))

    def test_full_result_returns_fingerprint_status(self):
        parts = {
            "audit": {
                "findings": [],
                "probe_results": [{"name": "models", "ok": True}],
            },
            "fingerprint": {
                "best_model": "DeepSeek-V4-Flash",
                "_posterior": 0.97,
                "_runner_up_model": "DeepSeek-V4",
                "_runner_up_posterior": 0.02,
                "_evidence_level": "strong",
                "_forgery_status": "supported",
                "_visualization": {
                    "sample_size": 200,
                    "candidate_count": 29,
                    "range": [1, 355],
                    "observed_distribution": [0.4, 0.6],
                    "reference_distribution": [0.5, 0.5],
                },
            },
        }

        chinese = server._result_detail("full", parts, "zh")
        english = server._result_detail("full", parts, "en")
        self.assertEqual(
            {
                "probe": "fingerprint",
                "severity": "Passed",
                "title": "模型指纹检查",
            },
            chinese["findings"][-1],
        )
        self.assertEqual(
            "Model fingerprint check",
            english["findings"][-1]["title"],
        )
        self.assertEqual(
            [0.4, 0.6],
            chinese["fingerprint"]["observed_distribution"],
        )
        self.assertEqual(29, english["fingerprint"]["candidate_count"])
        self.assertEqual(
            "DeepSeek-V4",
            chinese["fingerprint"]["runner_up_model"],
        )
        self.assertEqual(0.02, english["fingerprint"]["runner_up_posterior"])
        self.assertEqual("strong", chinese["fingerprint"]["evidence_level"])

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
            "probe_results": [{
                "name": "identity",
                "ok": False,
                "data": {
                    "status": 200,
                    "identity_text": "I am another model.",
                },
            }],
        }
        self.assertEqual(
            "risk",
            server._overall_verdict("quick", {"audit": failed_probe_audit}, {}),
        )
        insufficient_audit = {
            **safe_audit,
            "probe_results": [{
                "name": "identity",
                "ok": False,
                "error": "identity request timed out",
                "data": {},
            }],
        }
        self.assertEqual(
            "pass",
            server._overall_verdict(
                "quick",
                {"audit": insufficient_audit},
                {},
            ),
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


class ModelSummaryTests(unittest.TestCase):
    def setUp(self):
        self.audit = {
            "verdict": "HIGH",
            "_risk_score": 50,
            "findings": [{
                "probe": "liveness",
                "severity": "HIGH",
                "title": "Relay liveness failed",
            }],
            "probe_results": [{"name": "liveness", "ok": False}],
        }

    def test_summary_prompt_contains_score_and_failure_context(self):
        prompt = server._summary_prompt(
            "quick",
            {"audit": self.audit},
            {},
            "zh",
        )

        self.assertIn('"score":50.0', prompt)
        self.assertIn('"overall_verdict":"risk"', prompt)
        self.assertIn("中转服务连通性专项检查", prompt)
        self.assertIn("20至30个汉字", prompt)

    def test_clean_model_summary_enforces_language_and_score(self):
        self.assertEqual(
            "综合评分50/100，主要因中转连通异常导致评分下降",
            server._clean_model_summary(
                "总结：综合评分50/100，主要因中转连通异常导致评分下降",
                50,
                "zh",
            ),
        )
        self.assertEqual(
            "Overall score 50/100, reduced mainly by relay connectivity failures.",
            server._clean_model_summary(
                "Overall score 50/100, reduced mainly by relay connectivity failures.",
                50,
                "en",
            ),
        )
        with self.assertRaisesRegex(ValueError, "omitted the exact score"):
            server._clean_model_summary("主要因连通异常导致评分下降", 50, "zh")
        self.assertIn(
            "98.5/100",
            server._clean_model_summary(
                "综合评分98.5/100，主要因签名验证导致评分下降",
                98.5,
                "zh",
            ),
        )

    def test_model_result_summary_returns_tested_model_output(self):
        request = server.DetectRequest(
            algorithm="quick",
            base_url="https://api.example.test",
            api_key="secret",
            model="model-a",
            language="zh",
        )
        generated = "综合评分50/100，主要因中转连通异常导致评分下降"

        with patch.object(
            server,
            "_run_summary_completion",
            return_value=generated,
        ) as completion:
            result = server._model_result_summary(
                request,
                "quick",
                {"audit": self.audit},
                {},
                "https://api.example.test/v1",
                "openai",
                False,
            )

        self.assertEqual(generated, result)
        self.assertIn('"score":50.0', completion.call_args.args[1])

    def test_model_result_summary_rejects_a_contradictory_normal_claim(self):
        request = server.DetectRequest(
            algorithm="quick",
            base_url="https://api.example.test",
            api_key="secret",
            model="model-a",
            language="zh",
        )
        with patch.object(
            server,
            "_run_summary_completion",
            return_value="综合评分50/100，各项检测均表现正常",
        ):
            with self.assertRaisesRegex(ValueError, "contradicts computed verdict"):
                server._model_result_summary(
                    request,
                    "quick",
                    {"audit": self.audit},
                    {},
                    "https://api.example.test/v1",
                    "openai",
                    False,
                )

    def test_openai_summary_completion_uses_selected_protocol(self):
        request = server.DetectRequest(
            algorithm="quick",
            base_url="https://api.example.test/v1/responses",
            api_key="secret",
            model="model-a",
            language="en",
        )
        progress = []
        payload = {
            "output": [{
                "type": "message",
                "content": [{
                    "type": "output_text",
                    "text": "Overall score 50/100, reduced mainly by relay failures.",
                }],
            }],
        }

        with patch.object(
            server,
            "relay_chat_completion",
            return_value=(200, payload, 10, "model-a"),
        ) as completion:
            text = server._run_summary_completion(
                request,
                "prompt",
                "https://api.example.test/v1",
                "openai-responses",
                False,
                progress.append,
            )

        self.assertIn("Overall score 50/100", text)
        self.assertEqual("openai-responses", completion.call_args.kwargs["api_type"])

    def test_claude_summary_completion_reports_request_progress(self):
        request = server.DetectRequest(
            algorithm="quick",
            base_url="https://api.example.test",
            api_key="secret",
            model="claude-sonnet-5",
        )
        progress = []
        with patch.object(
            server,
            "simple_completion",
            return_value={"text": "综合评分100/100，各项检测均表现正常"},
        ) as completion:
            text = server._run_summary_completion(
                request,
                "prompt",
                "https://api.example.test",
                "anthropic",
                True,
                progress.append,
            )

        self.assertEqual("综合评分100/100，各项检测均表现正常", text)
        self.assertEqual([True], progress)
        self.assertEqual(0, completion.call_args.kwargs["temperature"])


if __name__ == "__main__":
    unittest.main()
