import json
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from services.api_checker import server
from services.api_checker.algorithms import common, pamela, relay_audit, signature


class BaselineTests(unittest.TestCase):
    def test_all_bundled_baseline_ids_map_case_insensitively(self):
        baselines = common.load_baselines()
        for baseline in baselines:
            name = baseline["name"]
            model_id = baseline["model"]
            aliases = {
                name.swapcase(),
                model_id.swapcase(),
                model_id.split("/", 1)[-1].swapcase(),
            }
            for alias in aliases:
                with self.subTest(name=name, alias=alias):
                    self.assertEqual(
                        name,
                        common.resolve_baseline_name(alias, baselines),
                    )

    def test_baseline_mapping_accepts_unique_provider_alias(self):
        baselines = common.load_baselines()

        self.assertEqual(
            "GPT-4o-mini",
            common.resolve_baseline_name(
                "Azure/GPT-4O-MINI",
                baselines,
            ),
        )

    def test_baseline_mapping_rejects_ambiguous_unprefixed_id(self):
        baselines = [
            {"name": "Vendor-A", "model": "vendor-a/shared-model"},
            {"name": "Vendor-B", "model": "vendor-b/shared-model"},
        ]

        self.assertIsNone(
            common.resolve_baseline_name("shared-model", baselines),
        )
        self.assertEqual(
            "Vendor-A",
            common.resolve_baseline_name(
                "VENDOR-A/SHARED-MODEL",
                baselines,
            ),
        )

    def test_full_fingerprint_passes_mapped_dataset_name(self):
        request = server.DetectRequest(
            algorithm="full",
            base_url="https://api.example.test/v1",
            api_key="secret",
            model="Azure/GPT-4O-MINI",
            iterations=50,
        )
        fingerprint_result = {
            "bayes": {
                "best_model_name": "GPT-4o-mini",
                "best_posterior": 0.9,
                "forgery": {"status": "unknown_anomaly"},
            },
        }

        with patch.object(
            server,
            "test_model",
            return_value=fingerprint_result,
        ) as test_model:
            result = server._run_fingerprint(
                request,
                "openai",
                request.base_url,
            )

        self.assertEqual(
            "GPT-4o-mini",
            test_model.call_args.args[8],
        )
        self.assertEqual("supported", result["_forgery_status"])

    def test_full_fingerprint_keeps_unknown_anomaly_for_a_different_model(self):
        self.assertEqual(
            "unknown_anomaly",
            server._effective_forgery_status(
                {
                    "best_model_name": "model-b",
                    "best_posterior": 1.0,
                    "forgery": {"status": "unknown_anomaly"},
                },
                "model-a",
            ),
        )

    def test_bundled_baselines_are_complete(self):
        baselines = common.load_baselines()
        self.assertEqual(41, len(baselines))
        model_ids = {item["model"].lower() for item in baselines}
        self.assertEqual(41, len(model_ids))
        self.assertTrue({
            "google/gemini-2.5-flash",
            "google/gemini-2.5-flash-lite",
            "google/gemini-3.1-flash-lite",
            "google/gemma-2-27b-it",
            "google/gemma-3-4b-it",
            "google/gemma-3-12b-it",
            "google/gemma-3-27b-it",
            "google/gemma-3n-e4b-it",
            "google/gemma-4-26b-a4b-it",
            "google/gemma-4-31b-it",
            "z-ai/glm-5.3",
            "glm-5.3-flash",
        }.issubset(model_ids))
        for baseline in baselines:
            self.assertEqual(common.NUMBER_RANGE, len(baseline["counts"]))
            self.assertEqual(common.NUMBER_RANGE, len(baseline["distribution"]))
            self.assertEqual(baseline["iterations"], sum(baseline["counts"]))
            self.assertEqual(baseline["iterations"], len(baseline["rawData"]))

    def test_deepseek_flash_keeps_preview_and_current_baselines(self):
        baselines = {
            baseline["model"]: baseline
            for baseline in common.load_baselines()
        }

        preview = baselines["deepseek-v4-flash-preview"]
        current = baselines["deepseek-v4-flash"]
        self.assertEqual("DeepSeek-V4-Flash-Preview", preview["name"])
        self.assertEqual("DeepSeek-V4-Flash", current["name"])
        self.assertEqual(496, preview["iterations"])
        self.assertEqual(5000, current["iterations"])
        self.assertNotEqual(preview["rawData"], current["rawData"])

    def test_save_baselines_keeps_numeric_arrays_on_single_lines(self):
        baseline = common.build_baseline(
            "Model A",
            "model-a",
            "openai",
            [1, 2, 2],
            no_think=True,
        )
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "baselines.json"
            common.save_baselines([baseline], str(path))
            text = path.read_text(encoding="utf-8")
            restored = json.loads(text)
            mode = path.stat().st_mode & 0o777

        lines = [line.strip() for line in text.splitlines()]
        distribution_line = next(
            line for line in lines if line.startswith('"distribution": [')
        )
        counts_line = next(
            line for line in lines if line.startswith('"counts": [')
        )
        raw_data_line = next(
            line for line in lines if line.startswith('"rawData": [')
        )
        self.assertTrue(distribution_line.endswith("],"))
        self.assertTrue(counts_line.endswith("],"))
        self.assertEqual('"rawData": [1, 2, 2]', raw_data_line)
        self.assertEqual([baseline], restored)
        self.assertEqual(0o644, mode)

    def test_calculate_stats(self):
        stats = common.calculate_stats([1, 2, 2, 5])
        self.assertEqual(2.5, stats["mean"])
        self.assertEqual(2, stats["median"])
        self.assertEqual(2, stats["mode"])
        self.assertEqual(2, stats["modeCount"])

    def test_collect_samples_honors_preexisting_cancellation(self):
        cancelled = threading.Event()
        cancelled.set()
        with patch.object(common, "_call_api_for_number") as call:
            results, errors = common.collect_samples(
                "openai",
                "https://example.test/v1",
                "secret",
                "model-a",
                cancel_event=cancelled,
            )
        self.assertEqual([], results)
        self.assertEqual(0, errors)
        call.assert_not_called()

    def test_responses_fingerprint_omits_optional_temperature(self):
        response = {
            "output": [{
                "type": "message",
                "content": [{
                    "type": "output_text",
                    "text": "7",
                }],
            }],
        }
        with patch.object(
            common,
            "http_post_json",
            return_value=(200, response),
        ) as request:
            result = common._call_api_for_number(
                "openai-responses",
                "https://example.test/v1",
                "secret",
                "model-a",
            )

        self.assertEqual("7", result)
        _, _, body = request.call_args.args
        self.assertNotIn("temperature", body)


class SignatureTests(unittest.TestCase):
    def test_signature_score_deduction_is_capped_at_twenty(self):
        self.assertEqual(80.0, signature._capped_signature_score(0))
        self.assertEqual(80.0, signature._capped_signature_score(79.9))
        self.assertEqual(80.0, signature._capped_signature_score(80))
        self.assertEqual(92.5, signature._capped_signature_score(92.5))
        self.assertEqual(100.0, signature._capped_signature_score(120))

    def test_model_consistency_is_case_insensitive(self):
        result = signature._check_model_consistency(
            "Claude-Sonnet-5",
            {"model": " claude-sonnet-5 "},
        )

        self.assertTrue(result.passed)

    def test_random_fingerprint_uses_shared_stats_function(self):
        values = iter(str(number) for number in range(1, 13))

        def completion(*_args, **_kwargs):
            return {"text": next(values)}

        with patch.object(signature, "simple_completion", side_effect=completion):
            result = signature._check_random_fingerprint(
                "https://example.test",
                "secret",
                "claude-test",
                samples=12,
            )

        self.assertTrue(result.passed)
        self.assertIn("均值=", result.detail)

    def test_all_checks_report_each_network_request(self):
        passed = signature.CheckResult(
            "Thinking Signature",
            True,
            "signature ok",
            2.0,
            True,
        )
        progress = []

        def one_request(*args):
            args[-1](True)
            return passed

        def latency_requests(*args):
            callback = args[-1]
            for _ in range(3):
                callback(True)
            return passed

        with (
            patch.object(
                signature,
                "_check_thinking_signature",
                return_value=(passed, {"signature": "test"}),
            ),
            patch.object(
                signature,
                "_check_replay",
                side_effect=one_request,
            ),
            patch.object(
                signature,
                "_check_response_headers",
                side_effect=one_request,
            ),
            patch.object(
                signature,
                "_check_system_prompt",
                side_effect=one_request,
            ),
            patch.object(
                signature,
                "_check_latency",
                side_effect=latency_requests,
            ),
        ):
            signature.run_all_checks(
                "https://example.test",
                "secret",
                "claude-test",
                skip_fingerprint=True,
                skip_latency=False,
                on_progress=lambda completed, total, success, error: progress.append(
                    (completed, total, success, error)
                ),
            )

        self.assertEqual(
            [
                (
                    completed,
                    signature.SIGNATURE_QUICK_REQUEST_COUNT,
                    completed,
                    0,
                )
                for completed in range(
                    1,
                    signature.SIGNATURE_QUICK_REQUEST_COUNT + 1,
                )
            ],
            progress,
        )

    def test_signature_progress_removes_skipped_replay_request(self):
        failed = signature.CheckResult(
            "Thinking Signature",
            False,
            "no signature",
            2.0,
            True,
        )
        passed = signature.CheckResult("mock", True, "ok")
        progress = []

        def one_request(*args):
            args[-1](True)
            return passed

        def latency_requests(*args):
            callback = args[-1]
            for _ in range(3):
                callback(True)
            return passed

        with (
            patch.object(
                signature,
                "_check_thinking_signature",
                return_value=(failed, {}),
            ),
            patch.object(
                signature,
                "_check_response_headers",
                side_effect=one_request,
            ),
            patch.object(
                signature,
                "_check_system_prompt",
                side_effect=one_request,
            ),
            patch.object(
                signature,
                "_check_latency",
                side_effect=latency_requests,
            ),
        ):
            result = signature.run_all_checks(
                "https://example.test",
                "secret",
                "claude-test",
                skip_fingerprint=True,
                on_progress=lambda completed, total, success, error: progress.append(
                    (completed, total, success, error)
                ),
            )

        self.assertEqual((1, 6, 1, 0), progress[0])
        self.assertEqual((6, 6, 6, 0), progress[-1])
        self.assertEqual(80.0, result["score"])
        self.assertEqual("proxy", result["verdict"])


class RelayAuditTests(unittest.TestCase):
    def test_risk_verdict_uses_40_and_70_boundaries(self):
        cases = {
            0: "LOW",
            39: "LOW",
            40: "MEDIUM",
            69: "MEDIUM",
            70: "HIGH",
            100: "HIGH",
        }
        for score, expected in cases.items():
            with self.subTest(score=score):
                self.assertEqual(expected, relay_audit.risk_verdict(score))

    def test_model_candidates_strip_provider_prefix(self):
        cases = {
            "anthropic/claude-sonnet-5": [
                "anthropic/claude-sonnet-5",
                "claude-sonnet-5",
            ],
            "openai/gpt-5": ["openai/gpt-5", "gpt-5"],
            "deepseek/deepseek-v4-pro": [
                "deepseek/deepseek-v4-pro",
                "deepseek-v4-pro",
            ],
            "moonshotai/kimi-k2.6": [
                "moonshotai/kimi-k2.6",
                "kimi-k2.6",
            ],
            "gpt-5": ["gpt-5"],
        }
        for model, expected in cases.items():
            with self.subTest(model=model):
                self.assertEqual(
                    expected,
                    relay_audit._model_candidates(model),
                )

    def test_models_probe_resolves_unprefixed_canonical_id(self):
        with patch.object(
            relay_audit,
            "_http_json",
            return_value=(200, {
                "data": [
                    {"id": "claude-sonnet-5"},
                    {"id": "gpt-5"},
                ],
            }, 10),
        ):
            result = relay_audit.probe_models(
                "https://example.test/v1",
                "secret",
                "Anthropic/CLAUDE-Sonnet-5",
            )

        self.assertTrue(result.ok)
        self.assertTrue(result.data["target_model_present"])
        self.assertEqual(
            "claude-sonnet-5",
            result.data["resolved_model"],
        )

    def test_stream_model_comparison_is_case_insensitive(self):
        findings = relay_audit.build_findings(
            [
                relay_audit.ProbeResult(
                    "stream_integrity",
                    True,
                    1,
                    data={"stream_models": [" DeepSeek-V4-Pro "]},
                ),
            ],
            "deepseek-v4-pro",
        )

        self.assertEqual([], findings)

    def test_stream_model_comparison_still_rejects_different_model(self):
        findings = relay_audit.build_findings(
            [
                relay_audit.ProbeResult(
                    "stream_integrity",
                    True,
                    1,
                    data={"stream_models": ["deepseek-v3"]},
                ),
            ],
            "deepseek-v4-pro",
        )

        self.assertEqual(1, len(findings))
        self.assertEqual(
            "Stream model field mismatch",
            findings[0].title,
        )

    def test_unexecuted_and_insufficient_probes_do_not_create_risks(self):
        findings = relay_audit.build_findings(
            [
                relay_audit.ProbeResult(
                    "liveness",
                    False,
                    None,
                    data={"not_executed": True},
                    error="audit exceeded total timeout",
                ),
                relay_audit.ProbeResult(
                    "echo_rewrite",
                    False,
                    None,
                    error="request timed out",
                ),
            ],
            "model-a",
        )

        self.assertEqual([], findings)

    def test_resolved_model_is_used_by_later_probes(self):
        seen_models = []

        def models_probe(*_args):
            return relay_audit.ProbeResult(
                "models",
                True,
                1,
                data={
                    "target_model_present": True,
                    "resolved_model": "deepseek-v4-pro",
                },
            )

        def generation_probe(_base_url, _key, model, _api_type, _on_request):
            seen_models.append(model)
            return relay_audit.ProbeResult("generation", True, 1)

        with patch.dict(relay_audit._PROBES, {
            "models": models_probe,
            "liveness": generation_probe,
            "identity": generation_probe,
            "glitch_fingerprint": generation_probe,
        }):
            result = relay_audit.run_relay_audit(
                "https://example.test/v1",
                "secret",
                "deepseek/deepseek-v4-pro",
                profile="quick",
            )

        self.assertEqual(
            ["deepseek-v4-pro", "deepseek-v4-pro", "deepseek-v4-pro"],
            seen_models,
        )
        self.assertEqual("deepseek-v4-pro", result["resolved_model"])

    def test_successful_fallback_overrides_incomplete_model_list(self):
        def models_probe(*_args):
            return relay_audit.ProbeResult(
                "models",
                True,
                1,
                data={
                    "status": 200,
                    "target_model_present": False,
                    "resolved_model": None,
                },
            )

        def liveness_probe(*_args):
            return relay_audit.ProbeResult(
                "liveness",
                True,
                1,
                data={
                    "status": 200,
                    "resolved_model": "kimi-k2.6",
                },
            )

        def identity_probe(_base_url, _key, model, _api_type, _on_request):
            self.assertEqual("kimi-k2.6", model)
            return relay_audit.ProbeResult(
                "identity",
                True,
                1,
                data={"status": 200, "resolved_model": model},
            )

        def glitch_probe(_base_url, _key, model, _api_type, _on_request):
            self.assertEqual("kimi-k2.6", model)
            return relay_audit.ProbeResult(
                "glitch_fingerprint",
                True,
                1,
                data={"status": 200, "resolved_model": model},
            )

        with patch.dict(relay_audit._PROBES, {
            "models": models_probe,
            "liveness": liveness_probe,
            "identity": identity_probe,
            "glitch_fingerprint": glitch_probe,
        }):
            result = relay_audit.run_relay_audit(
                "https://example.test/v1",
                "secret",
                "moonshotai/kimi-k2.6",
                profile="quick",
            )

        self.assertEqual([], result["findings"])
        self.assertEqual("kimi-k2.6", result["resolved_model"])

    def test_progress_is_reported_after_each_probe(self):
        progress = []
        probe_names = relay_audit.PROFILES["quick"]
        probes = {
            name: lambda *_args, name=name: relay_audit.ProbeResult(
                name,
                True,
                1,
            )
            for name in probe_names
        }

        with patch.dict(relay_audit._PROBES, probes):
            relay_audit.run_relay_audit(
                "https://example.test/v1",
                "secret",
                "model-a",
                profile="quick",
                on_progress=lambda completed, total: progress.append(
                    (completed, total)
                ),
            )

        self.assertEqual(
            [(index, len(probe_names)) for index in range(1, len(probe_names) + 1)],
            progress,
        )

    def test_request_progress_counts_fallback_attempt(self):
        progress = []

        def models_probe(_base, _key, _model, _api_type, on_request):
            on_request(True)
            return relay_audit.ProbeResult("models", True, 1)

        def liveness_probe(_base, _key, _model, _api_type, on_request):
            on_request(False)
            on_request(True)
            return relay_audit.ProbeResult("liveness", True, 1)

        def identity_probe(_base, _key, _model, _api_type, on_request):
            on_request(True)
            return relay_audit.ProbeResult("identity", True, 1)

        def glitch_probe(_base, _key, _model, _api_type, on_request):
            on_request(True)
            return relay_audit.ProbeResult("glitch_fingerprint", True, 1)

        with patch.dict(relay_audit._PROBES, {
            "models": models_probe,
            "liveness": liveness_probe,
            "identity": identity_probe,
            "glitch_fingerprint": glitch_probe,
        }):
            relay_audit.run_relay_audit(
                "https://example.test/v1",
                "secret",
                "provider/model-a",
                profile="quick",
                on_request_progress=(
                    lambda completed, total, success, error: progress.append(
                        (completed, total, success, error)
                    )
                ),
            )

        self.assertEqual([
            (1, 4, 1, 0),
            (2, 4, 1, 1),
            (3, 5, 2, 1),
            (4, 5, 3, 1),
            (5, 5, 4, 1),
        ], progress)

    def test_chat_omits_temperature_and_supports_responses(self):
        messages = [{"role": "user", "content": "hello"}]
        with patch.object(
            relay_audit,
            "_http_json",
            return_value=(200, {}, 1),
        ) as request:
            relay_audit._chat(
                "https://example.test/v1",
                "secret",
                "model-a",
                messages,
            )
            chat_url, _, chat_body = request.call_args.args
            self.assertEqual(
                "https://example.test/v1/chat/completions",
                chat_url,
            )
            self.assertNotIn("temperature", chat_body)
            self.assertEqual(messages, chat_body["messages"])

            relay_audit._chat(
                "https://example.test/v1",
                "secret",
                "model-a",
                messages,
                api_type="openai-responses",
            )
            responses_url, _, responses_body = request.call_args.args
            self.assertEqual(
                "https://example.test/v1/responses",
                responses_url,
            )
            self.assertNotIn("temperature", responses_body)
            self.assertEqual(messages, responses_body["input"])
            self.assertNotIn("messages", responses_body)

    def test_chat_retries_unprefixed_model_after_model_error(self):
        with patch.object(
            relay_audit,
            "_http_json",
            side_effect=[
                (404, {"error": {"code": "model_not_found"}}, 10),
                (200, {"choices": []}, 20),
            ],
        ) as request:
            status, _, latency, resolved_model = relay_audit._chat(
                "https://example.test/v1",
                "secret",
                "openai/gpt-5",
                [{"role": "user", "content": "hello"}],
            )

        self.assertEqual(200, status)
        self.assertEqual(30, latency)
        self.assertEqual("gpt-5", resolved_model)
        self.assertEqual(2, request.call_count)
        self.assertEqual(
            "openai/gpt-5",
            request.call_args_list[0].args[2]["model"],
        )
        self.assertEqual(
            "gpt-5",
            request.call_args_list[1].args[2]["model"],
        )

    def test_responses_payload_helpers(self):
        payload = {
            "status": "completed",
            "output": [{
                "type": "message",
                "content": [{
                    "type": "output_text",
                    "text": "hello",
                }],
            }],
        }
        self.assertEqual("hello", relay_audit._extract_text(payload))
        self.assertEqual("stop", relay_audit._finish_reason(payload))
        self.assertFalse(relay_audit._is_truncated(payload))

    def test_http_json_enforces_total_deadline(self):
        class BlockingResponse:
            status = 200

            def __init__(self):
                self.closed = threading.Event()

            def read(self):
                self.closed.wait(1)
                return b"{}"

            def close(self):
                self.closed.set()

        started = time.monotonic()
        with (
            patch.object(
                relay_audit,
                "HTTP_TOTAL_TIMEOUT_SECONDS",
                0.01,
            ),
            patch.object(
                relay_audit._NO_REDIRECT_OPENER,
                "open",
                return_value=BlockingResponse(),
            ),
        ):
            with self.assertRaises(TimeoutError):
                relay_audit._http_json(
                    "https://example.test/v1/models",
                    "secret",
                    method="GET",
                )
        self.assertLess(time.monotonic() - started, 0.5)

    def test_audit_total_deadline_marks_pending_probes(self):
        probes = {
            name: Mock()
            for name in relay_audit.PROFILES["quick"]
        }
        progress = []
        with (
            patch.dict(relay_audit._PROBES, probes),
            patch.object(
                relay_audit,
                "AUDIT_TOTAL_TIMEOUT_SECONDS",
                -1,
            ),
        ):
            result = relay_audit.run_relay_audit(
                "https://example.test/v1",
                "secret",
                "model-a",
                profile="quick",
                on_progress=lambda completed, total: progress.append(
                    (completed, total)
                ),
            )

        self.assertEqual(4, len(result["probe_results"]))
        self.assertTrue(all(
            probe.error == "audit exceeded total timeout"
            for probe in result["probe_results"]
        ))
        self.assertEqual([(1, 4), (2, 4), (3, 4), (4, 4)], progress)
        for probe in probes.values():
            probe.assert_not_called()


class RelayAuditGlitchFingerprintTests(unittest.TestCase):
    def test_item_eight_is_the_unspaced_owner_phrase(self):
        self.assertEqual("给主人留下些什么吧", relay_audit.GLITCH_TOKENS[7])

    def test_exact_failed_signature_matches_family(self):
        matches = relay_audit._match_glitch_families([5, 11, 12])
        self.assertEqual("moonshot", matches[0]["family"])
        self.assertTrue(matches[0]["exact"])
        self.assertTrue(matches[0]["consistent"])

    def test_version_subset_matches_unique_family(self):
        matches = relay_audit._match_glitch_families([2])
        self.assertEqual("minimax", matches[0]["family"])
        self.assertFalse(matches[0]["exact"])
        self.assertTrue(matches[0]["consistent"])
        self.assertEqual(1.0, matches[0]["confidence"])

    def test_probe_only_requires_repetition_and_matches_keywords(self):
        response = "\n".join(
            f"{i}. {token if i not in {2, 9} else '复述错误'}"
            for i, token in enumerate(relay_audit.GLITCH_TOKENS, 1)
        )
        with patch.object(
            relay_audit,
            "_chat",
            return_value=(200, {
                "choices": [{"message": {"content": response}, "finish_reason": "stop"}],
                "model": "unknown",
                "usage": {},
            }, 10, "model-a"),
        ) as call:
            result = relay_audit.probe_glitch_fingerprint(
                "https://example.test/v1", "secret", "model-a"
            )

        self.assertTrue(result.ok)
        self.assertEqual([2, 9], result.data["failed_indices"])
        self.assertEqual("minimax", result.data["best_family"])
        prompt = call.call_args.args[3][0]["content"]
        self.assertIn("不要解释", prompt)
        self.assertNotIn("涵义", prompt)

    def test_incomplete_response_does_not_generate_candidates(self):
        with patch.object(
            relay_audit,
            "_chat",
            return_value=(200, {
                "choices": [{
                    "message": {"content": "9. 方も多いのではないでしょうか"},
                    "finish_reason": "length",
                }],
                "model": "google/gemini-test",
            }, 10, "gemini-test"),
        ):
            result = relay_audit.probe_glitch_fingerprint(
                "https://example.test/v1", "secret", "gemini-test"
            )

        self.assertFalse(result.ok)
        self.assertFalse(result.data["complete"])
        self.assertEqual([], result.data["failed_indices"])
        self.assertEqual([], result.data["candidate_families"])
        self.assertIsNone(result.data["best_family"])

    def test_http_error_does_not_generate_candidates(self):
        with patch.object(
            relay_audit,
            "_chat",
            return_value=(
                401,
                {"error": {"message": "unauthorized"}},
                10,
                "gemini-test",
            ),
        ):
            result = relay_audit.probe_glitch_fingerprint(
                "https://example.test/v1", "secret", "gemini-test"
            )

        self.assertFalse(result.ok)
        self.assertEqual([], result.data["failed_indices"])
        self.assertEqual([], result.data["candidate_families"])

    def test_gpt_item_eight_early_stop_is_analyzable(self):
        response = "\n".join([
            *[
                f"{i}. {relay_audit.GLITCH_TOKENS[i - 1]}"
                for i in range(1, 8)
            ],
            "8.",
        ])
        with patch.object(
            relay_audit,
            "_chat",
            return_value=(200, {
                "choices": [{
                    "message": {"content": response},
                    "finish_reason": "stop",
                }],
                "model": "openai/gpt-test",
            }, 10, "gpt-test"),
        ):
            result = relay_audit.probe_glitch_fingerprint(
                "https://example.test/v1", "secret", "gpt-test"
            )

        self.assertTrue(result.ok)
        self.assertFalse(result.data["complete"])
        self.assertTrue(result.data["analyzable"])
        self.assertEqual(8, result.data["early_stop_index"])
        self.assertEqual([8], result.data["failed_indices"])
        self.assertEqual("openai", result.data["best_family"])

    def test_exact_mismatch_adds_weak_finding(self):
        probe = relay_audit.ProbeResult(
            "glitch_fingerprint",
            True,
            10,
            {
                "failed_indices": [7, 15],
                "best_family": "google",
                "candidate_families": [{
                    "family": "google",
                    "matched_indices": [7, 15],
                    "signature_indices": [7, 15],
                    "exact": True,
                    "consistent": True,
                    "confidence": 1.0,
                }],
            },
        )
        findings = relay_audit.build_findings([probe], "gpt-4o")
        self.assertEqual(1, len(findings))
        self.assertEqual("Glitch token family mismatch", findings[0].title)


class PamelaTests(unittest.TestCase):
    def test_bundled_reference_is_available(self):
        self.assertTrue(Path(pamela.DEFAULT_REFERENCE).is_file())
        reference = pamela.load_reference(pamela.DEFAULT_REFERENCE)
        self.assertEqual(167, len(reference["models"]))
        self.assertEqual(40, len(reference["by_cell"]))

    def test_jsd_identity_and_symmetry(self):
        left = {"a": 0.75, "b": 0.25}
        right = {"a": 0.25, "b": 0.75}
        self.assertEqual(0.0, pamela.jsd(left, left))
        self.assertAlmostEqual(pamela.jsd(left, right), pamela.jsd(right, left))

    def test_candidate_output_shape(self):
        counts = {("num10-random", "en"): {"7": 3, "4": 1}}
        off = {("num10-random", "en"): 2}
        records = pamela.build_candidate_distributions("model-a", counts, off)
        encoded = json.loads(json.dumps(records))
        self.assertEqual("model-a", encoded[0]["model"])
        self.assertEqual(4, encoded[0]["n_valid"])
        self.assertEqual(2, encoded[0]["n_off_format"])


if __name__ == "__main__":
    unittest.main()
