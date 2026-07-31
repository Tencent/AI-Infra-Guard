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
            "高风险 (安全分 50/100, 发现 1 项风险)",
            chinese["summary"],
        )
        self.assertEqual(
            "中转服务连通性检查失败",
            chinese["detail"]["findings"][0]["title"],
        )
        self.assertEqual(
            "Failed",
            chinese["detail"]["findings"][0]["severity"],
        )
        self.assertEqual(
            "High risk (safety score 50/100, 1 finding)",
            english["summary"],
        )
        self.assertEqual(
            "Relay liveness failed",
            english["detail"]["findings"][0]["title"],
        )
        self.assertEqual(
            "Failed",
            english["detail"]["findings"][0]["severity"],
        )

    def test_full_result_uses_english_summary_sections(self):
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
            "[Fingerprint] Most similar to GPT-4o-mini (91.0/100) | "
            "[Audit] No obvious risk detected "
            "(safety score 100/100, 0 findings)",
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
            "模型列表检查通过",
            detail["findings"][0]["title"],
        )

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
            ["Passed", "Failed", "Failed"],
            [
                finding["severity"]
                for finding in chinese["findings"]
            ],
        )
        self.assertEqual(
            [
                "模型列表检查通过",
                "模型身份系列不匹配",
                "流式响应完整性检查未通过",
            ],
            [
                finding["title"]
                for finding in chinese["findings"]
            ],
        )
        self.assertEqual(
            "Model list check passed",
            english["findings"][0]["title"],
        )
        self.assertEqual(
            "Stream integrity check failed",
            english["findings"][2]["title"],
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
