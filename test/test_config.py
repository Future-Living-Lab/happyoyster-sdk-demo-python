import unittest

from src.config import load_env


API_HOST = "llm-example.cn-beijing.maas.aliyuncs.com"
GATEWAY_BASE_URLS = {
    mode: f"https://{API_HOST}/api/v2/apps/happyoyster-1.0-{name}"
    for mode, name in ((1, "adventure"), (2, "directing"), (3, "acting"))
}


class LoadEnvTest(unittest.TestCase):
    def test_requires_dashscope_api_key(self):
        with self.assertRaisesRegex(ValueError, "DASHSCOPE_API_KEY is required"):
            load_env({"BAILIAN_API_HOST": API_HOST})

    def test_requires_bailian_api_host(self):
        with self.assertRaisesRegex(ValueError, "BAILIAN_API_HOST is required"):
            load_env({"DASHSCOPE_API_KEY": "sk-test"})

    def test_rejects_malformed_bailian_api_host(self):
        with self.assertRaisesRegex(
            ValueError, "BAILIAN_API_HOST must be a valid Bailian API Host"
        ):
            load_env({"BAILIAN_API_HOST": "not a host", "DASHSCOPE_API_KEY": "sk-test"})

    def test_rejects_bailian_api_host_with_query(self):
        with self.assertRaisesRegex(
            ValueError, "BAILIAN_API_HOST must be a valid Bailian API Host"
        ):
            load_env(
                {
                    "BAILIAN_API_HOST": f"{API_HOST}?debug=true",
                    "DASHSCOPE_API_KEY": "sk-test",
                }
            )

    def test_rejects_full_bailian_api_url(self):
        with self.assertRaisesRegex(
            ValueError, "BAILIAN_API_HOST must be a valid Bailian API Host"
        ):
            load_env(
                {
                    "BAILIAN_API_HOST": f"https://{API_HOST}/api/v2/apps/happyoyster-1.0/openapi/v1",
                    "DASHSCOPE_API_KEY": "sk-test",
                }
            )

    def test_defaults_to_local_settings(self):
        config = load_env(
            {
                "BAILIAN_API_HOST": API_HOST,
                "DASHSCOPE_API_KEY": "sk-test",
            }
        )

        self.assertEqual(config.host, "127.0.0.1")
        self.assertEqual(config.port, 3000)
        self.assertEqual(config.bailian_gateway_base_urls_by_mode, GATEWAY_BASE_URLS)
        self.assertEqual(config.bailian_api_origin, f"https://{API_HOST}")
        self.assertEqual(config.dashscope_api_key, "sk-test")
        self.assertEqual(config.request_timeout_ms, 130_000)

    def test_requires_nonblank_dashscope_api_key(self):
        with self.assertRaisesRegex(ValueError, "DASHSCOPE_API_KEY is required"):
            load_env({"BAILIAN_API_HOST": API_HOST, "DASHSCOPE_API_KEY": " "})

    def test_accepts_bailian_settings(self):
        config = load_env(
            {
                "DASHSCOPE_API_KEY": "sk-test",
                "BAILIAN_API_HOST": API_HOST,
                "PORT": "3100",
                "REQUEST_TIMEOUT_MS": "5000",
            }
        )

        self.assertEqual(config.dashscope_api_key, "sk-test")
        self.assertEqual(config.bailian_gateway_base_urls_by_mode, GATEWAY_BASE_URLS)
        self.assertEqual(config.bailian_api_origin, f"https://{API_HOST}")
        self.assertEqual(config.port, 3100)
        self.assertEqual(config.request_timeout_ms, 5000)

    def test_rejects_invalid_port(self):
        with self.assertRaisesRegex(ValueError, "PORT must be a positive integer"):
            load_env(
                {
                    "BAILIAN_API_HOST": API_HOST,
                    "DASHSCOPE_API_KEY": "sk-test",
                    "PORT": "abc",
                }
            )


if __name__ == "__main__":
    unittest.main()
