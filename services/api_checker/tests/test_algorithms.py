import json
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from services.api_checker.algorithms import common, pamela, relay_audit, signature


class BaselineTests(unittest.TestCase):
    def test_bundled_baselines_are_complete(self):
        baselines = common.load_baselines()
        self.assertEqual(28, len(baselines))
        self.assertEqual(28, len({item["model"].lower() for item in baselines}))
        for baseline in baselines:
            self.assertEqual(common.NUMBER_RANGE, len(baseline["counts"]))
            self.assertEqual(common.NUMBER_RANGE, len(baseline["distribution"]))
            self.assertEqual(baseline["iterations"], sum(baseline["counts"]))
            self.assertEqual(baseline["iterations"], len(baseline["rawData"]))

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


class RelayAuditTests(unittest.TestCase):
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

        def generation_probe(_base_url, _key, model, _api_type):
            seen_models.append(model)
            return relay_audit.ProbeResult("generation", True, 1)

        with patch.dict(relay_audit._PROBES, {
            "models": models_probe,
            "liveness": generation_probe,
            "identity": generation_probe,
        }):
            result = relay_audit.run_relay_audit(
                "https://example.test/v1",
                "secret",
                "deepseek/deepseek-v4-pro",
                profile="quick",
            )

        self.assertEqual(
            ["deepseek-v4-pro", "deepseek-v4-pro"],
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

        def identity_probe(_base_url, _key, model, _api_type):
            self.assertEqual("kimi-k2.6", model)
            return relay_audit.ProbeResult(
                "identity",
                True,
                1,
                data={"status": 200, "resolved_model": model},
            )

        with patch.dict(relay_audit._PROBES, {
            "models": models_probe,
            "liveness": liveness_probe,
            "identity": identity_probe,
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

        self.assertEqual(3, len(result["probe_results"]))
        self.assertTrue(all(
            probe.error == "audit exceeded total timeout"
            for probe in result["probe_results"]
        ))
        self.assertEqual([(1, 3), (2, 3), (3, 3)], progress)
        for probe in probes.values():
            probe.assert_not_called()


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
