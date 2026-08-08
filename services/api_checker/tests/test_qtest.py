import json
import os
import stat
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from services.api_checker.ventor_qtest.runner import cli


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


if __name__ == "__main__":
    unittest.main()
