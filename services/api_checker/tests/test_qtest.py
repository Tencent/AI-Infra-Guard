import json
import math
import os
import stat
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from services.api_checker.ventor_qtest.repeated_request import (
    OTHER_CATEGORY,
    estimate_repeated_context_kl,
    map_outcome,
    pool_reference_categories,
    posterior_expected_kl,
    unbiased_chi_square,
)
from services.api_checker.ventor_qtest.runner import cli
from services.api_checker.ventor_qtest.runner.orchestrator import UnifiedClient
from services.api_checker.ventor_qtest.runner.repeated import (
    analyze_repeated_requests,
    collect_repeated_requests,
)


class QTestConfigTests(unittest.TestCase):
    def test_dumped_suite_uses_environment_placeholders(self):
        suite = {
            "tester": {"api_key": "tester-secret"},
            "vendors": [
                {"name": "one", "api_key": "vendor-secret"},
                {"name": "two", "api_key": "vendor-secret"},
            ],
        }
        dumped = cli._suite_for_dump(suite, distinct_tester_key=True)

        encoded = json.dumps(dumped)
        self.assertNotIn("tester-secret", encoded)
        self.assertNotIn("vendor-secret", encoded)
        self.assertEqual("${QTEST_TESTER_API_KEY}", dumped["tester"]["api_key"])
        self.assertEqual("${OPENROUTER_API_KEY}", dumped["vendors"][0]["api_key"])
        self.assertEqual("tester-secret", suite["tester"]["api_key"])

    def test_saved_config_is_owner_only(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "qtest.json"
            cli._save_config(path, {"api_key": "${OPENROUTER_API_KEY}"})

            mode = stat.S_IMODE(os.stat(path).st_mode)
            self.assertEqual(0o600, mode)
            self.assertEqual(
                {"api_key": "${OPENROUTER_API_KEY}"},
                json.loads(path.read_text(encoding="utf-8")),
            )

    def test_bundled_config_expands_data_directory(self):
        config_path = (
            Path(cli.__file__).resolve().parents[1]
            / "config"
            / "default.yaml"
        )
        with patch.dict(
            os.environ,
            {
                "MOONSHOT_API_KEY": "test-moonshot",
                "SILICONFLOW_API_KEY": "test-siliconflow",
                "OPENROUTER_API_KEY": "test-openrouter",
            },
        ):
            config = cli._load_config(config_path)
        result_dir = config["tests"][0]["result_dir"]
        self.assertTrue(Path(result_dir).is_absolute())
        self.assertIn("qtest", Path(result_dir).parts)

    def test_bundled_afl_config_uses_reference_logprobs_only(self):
        config_path = (
            Path(cli.__file__).resolve().parents[1] / "config" / "afl.yaml"
        )
        with patch.dict(os.environ, {"DEEPSEEK_API_KEY": "test-deepseek"}):
            config = cli._load_config(config_path)["afl"]

        self.assertEqual(20, config["reference"]["top_logprobs"])
        self.assertNotIn("top_logprobs", config["vendors"][0])
        self.assertTrue(Path(config["output"]).is_absolute())


class RepeatedRequestEstimatorTests(unittest.TestCase):
    def test_posterior_expected_kl_is_nonnegative(self):
        value = posterior_expected_kl(
            {"a": 40, "b": 10},
            {"a": 0.5, "b": 0.5},
        )
        self.assertGreater(value, 0.0)

    def test_estimator_detects_a_large_known_shift(self):
        result = estimate_repeated_context_kl(
            {"a": 90, "b": 10},
            {"a": 0.5, "b": 0.5},
            null_samples=3_000,
            posterior_samples=3_000,
            seed=7,
        )
        true_kl = 0.9 * math.log(0.9 / 0.5) + 0.1 * math.log(0.1 / 0.5)
        self.assertAlmostEqual(
            true_kl, result["bias_corrected_KL"], delta=0.08
        )
        self.assertLess(result["null_bootstrap_one_sided_p"], 0.01)

    def test_reference_prior_and_chi_square_match_paper_code(self):
        result = estimate_repeated_context_kl(
            {"common": 10, "rare": 0},
            {"common": 0.999, "rare": 0.001},
            null_samples=1_000,
            posterior_samples=500,
            seed=11,
        )
        self.assertEqual("reference", result["prior_mode"])
        self.assertEqual(1.0, result["prior_strength"])
        self.assertAlmostEqual(
            0.0,
            unbiased_chi_square(
                {"a": 3, "b": 1}, {"a": 0.5, "b": 0.5}
            ),
        )


class RepeatedRequestProtocolTests(unittest.TestCase):
    def test_outcome_map_requires_an_exact_label(self):
        reference = {"1": 0.45, "8": 0.45, OTHER_CATEGORY: 0.10}
        self.assertEqual("1", map_outcome("1", reference))
        for text in (" 1", "1\n", "Alright", ""):
            self.assertEqual(OTHER_CATEGORY, map_outcome(text, reference))

    def test_reference_only_pooling_conserves_probability(self):
        pooled = pool_reference_categories(
            {"1": 0.90, "8": 0.01, OTHER_CATEGORY: 0.09},
            samples=50,
            min_expected_count=1.0,
        )
        self.assertEqual({"1"}, set(pooled) - {OTHER_CATEGORY})
        self.assertAlmostEqual(0.90, pooled["1"])
        self.assertAlmostEqual(0.10, pooled[OTHER_CATEGORY])
        self.assertAlmostEqual(1.0, sum(pooled.values()))

    def test_target_client_can_preserve_nonconforming_whitespace(self):
        response = Mock()
        response.status_code = 200
        response.text = "response"
        response.raise_for_status.return_value = None
        response.json.return_value = {
            "choices": [{"message": {"content": " 1\n"}}]
        }
        client = UnifiedClient(
            {
                "name": "route",
                "base_url": "https://example.invalid",
                "path": "/v1/chat/completions",
                "api_key": "test-key",
                "model": "test-model",
                "max_tokens": 1,
                "strip_response": False,
            }
        )
        with patch(
            "services.api_checker.ventor_qtest.runner.orchestrator.requests.post",
            return_value=response,
        ):
            self.assertEqual(" 1\n", client.generate("prompt"))

    def test_route_analysis_reports_afl_and_holm_p_value(self):
        contexts = [
            {
                "id": "coin",
                "prompt": "return a or b",
                "allowed_labels": ["a", "b"],
            }
        ]
        raw_samples = []
        for route, values in {
            "faithful": ["a", "b", "a", "b"],
            "shifted": ["a", "a", "a", "a"],
        }.items():
            for sample_index, text in enumerate(values):
                raw_samples.append(
                    {
                        "context_id": "coin",
                        "route": route,
                        "sample_index": sample_index,
                        "text": text,
                        "request_failed": False,
                    }
                )
        result = analyze_repeated_requests(
            {
                "samples_per_context": 4,
                "min_expected_count": 0.0,
                "null_samples": 400,
                "posterior_samples": 400,
                "inference_samples": 400,
                "seed": 3,
            },
            contexts=contexts,
            raw_samples=raw_samples,
            references={
                "coin": {"a": 0.5, "b": 0.5, OTHER_CATEGORY: 0.0}
            },
            route_names=["faithful", "shifted"],
        )
        by_route = {row["route"]: row for row in result["route_results"]}
        self.assertGreater(
            by_route["shifted"]["average_fidelity_loss"],
            by_route["faithful"]["average_fidelity_loss"],
        )
        for row in by_route.values():
            self.assertIn("afl_credible_interval_95", row)
            self.assertIn("route_null_p_holm", row)

    def test_collection_checkpoint_resumes_without_duplicate_requests(self):
        class FakeTester:
            calls = 0

            def get_token_probabilities(self, messages, max_tokens=1):
                self.calls += 1
                return "a", {"a": 0.5, "b": 0.5}

        class FakeClient:
            def __init__(self):
                self.calls = 0

            def generate(self, prompt, temperature=1.0):
                self.calls += 1
                return "a" if self.calls % 2 else "b"

        contexts = [
            {
                "id": "coin",
                "prompt": "return a or b",
                "allowed_labels": ["a", "b"],
            }
        ]
        config = {
            "samples_per_context": 4,
            "workers": 2,
            "reference": {},
            "vendors": [{"name": "route"}],
        }
        tester = FakeTester()
        client = FakeClient()
        with tempfile.TemporaryDirectory() as directory:
            checkpoint = Path(directory) / "checkpoint.json"
            first = collect_repeated_requests(
                config,
                contexts=contexts,
                checkpoint=checkpoint,
                tester_factory=lambda _: tester,
                client_factory=lambda _: {"route": client},
            )
            self.assertEqual(4, len(first[0]))
            self.assertEqual(1, tester.calls)
            self.assertEqual(4, client.calls)
            self.assertEqual(0o600, stat.S_IMODE(os.stat(checkpoint).st_mode))

            resumed_client = FakeClient()
            second = collect_repeated_requests(
                config,
                contexts=contexts,
                checkpoint=checkpoint,
                tester_factory=lambda _: FakeTester(),
                client_factory=lambda _: {"route": resumed_client},
            )
            self.assertEqual(4, len(second[0]))
            self.assertEqual(0, resumed_client.calls)


if __name__ == "__main__":
    unittest.main()
