import asyncio
import hashlib
import json
import logging
import unittest
from unittest.mock import patch

from fastapi import HTTPException

from services.api_checker import server
from services.api_checker.algorithms.relay_audit import ProbeResult


class ServerContractTests(unittest.TestCase):
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
                },
            }

        with (
            patch.object(server, "test_model", side_effect=fake_test_model),
            patch.object(server, "_resolve_baseline_name", return_value="model-a"),
        ):
            server._run_fingerprint(
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

        self.assertEqual(expected, progress)
        self.assertEqual({
            "completed": 14,
            "total": 14,
            "success": 14,
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
            "综合检查发现异常（50/100）",
            chinese["summary"],
        )
        self.assertIn(
            {
                "probe": "liveness",
                "severity": "Failed",
                "title": "中转服务连通性专项检查",
            },
            chinese["detail"]["findings"],
        )
        self.assertEqual(
            "Overall check found issues (50/100)",
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
        self.assertEqual(
            "Overall check passed (91/100)",
            result["summary"],
        )

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

        self.assertEqual(35.0, result["score"])
        self.assertEqual("risk", result["overall_verdict"])
        self.assertEqual(
            "综合检查发现异常（35/100）",
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
        self.assertEqual(
            [("signature", "signature unavailable")],
            component_errors,
        )
        self.assertEqual(
            "综合检查未完成（0/100）",
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
                    {"name": "models", "ok": True},
                    {"name": "identity", "ok": True},
                    {"name": "stream_integrity", "ok": False},
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

    def test_all_18_audit_checks_return_passed_or_failed(self):
        probe_results = [
            {"name": probe, "ok": True}
            for probe in server.PROBE_CHECK_TITLE
        ]
        safe_parts = {
            "audit": {
                "findings": [],
                "probe_results": probe_results,
            },
        }

        chinese = server._result_detail("full", safe_parts, "zh")["findings"]
        english = server._result_detail("full", safe_parts, "en")["findings"]
        self.assertEqual(18, len(chinese))
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
                    {"name": item["name"], "ok": item["name"] != failed_probe}
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

    def test_full_result_returns_fingerprint_status(self):
        parts = {
            "audit": {
                "findings": [],
                "probe_results": [{"name": "models", "ok": True}],
            },
            "fingerprint": {
                "best_model": "DeepSeek-V4-Flash",
                "_posterior": 0.97,
                "_forgery_status": "supported",
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
