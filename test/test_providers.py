import unittest

from src.modules.providers.bailian_app_provider import call_bailian_app
from src.modules.proxy.proxy_controller import ProxyRequest

from .helpers import RecordingFetch, json_response, test_config


class BailianProviderTest(unittest.TestCase):
    def test_prefixes_app_path_and_strips_internal_gateway_headers(self):
        body = b'{"title":"oyster"}'
        fetch = RecordingFetch(response=json_response({"code": 0}))

        call_bailian_app(
            ProxyRequest(
                method="POST",
                path="/openapi/v1/worlds",
                search="?dry_run=true",
                headers={
                    "accept-encoding": "gzip, deflate, br",
                    "content-type": "application/json",
                    "x-dashscope-uid": "must-not-forward",
                    "x-dashscope-inner-entity-id": "must-not-forward",
                    "x-ho-uid": "must-not-forward",
                },
                body=body,
            ),
            config=test_config(),
            fetch_impl=fetch,
        )

        call = fetch.last_call
        self.assertEqual(
            call["url"],
            "https://example.test/api/v2/apps/happyoyster-1.0/openapi/v1/worlds?dry_run=true",
        )
        self.assertEqual(call["method"], "POST")
        self.assertEqual(call["headers"]["authorization"], "Bearer sk-test")
        self.assertEqual(call["headers"]["accept-encoding"], "identity")
        self.assertEqual(call["headers"]["content-type"], "application/json")
        self.assertNotIn("x-dashscope-uid", call["headers"])
        self.assertNotIn("x-dashscope-inner-entity-id", call["headers"])
        self.assertNotIn("x-ho-uid", call["headers"])
        self.assertEqual(call["body"], body)
        self.assertEqual(call["timeout_ms"], 1_000)


if __name__ == "__main__":
    unittest.main()
