import json
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

from services.api_checker.algorithms import common, pamela, signature


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
