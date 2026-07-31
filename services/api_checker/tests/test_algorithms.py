import json
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

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
