import json
import unittest

from .helpers import (
    RecordingFetch,
    http_request,
    json_response,
    start_test_server,
    stop_test_server,
)


class RoutesTest(unittest.TestCase):
    def setUp(self):
        self._servers = []

    def tearDown(self):
        for server in self._servers:
            stop_test_server(server)

    def start_server(self, fetch_impl):
        server, base_url = start_test_server(fetch_impl)
        self._servers.append(server)
        return base_url

    def assert_proxy_mapping(
        self, *, request_path, expected_url, method="GET", body=None, expected_body=None
    ):
        fetch = RecordingFetch(response=json_response({"code": 0, "data": "ok"}))
        base_url = self.start_server(fetch)

        headers = {} if body is None else {"content-type": "application/json"}
        status, response_body = http_request(
            f"{base_url}{request_path}", method=method, body=body, headers=headers
        )

        self.assertEqual(status, 200)
        self.assertEqual(json.loads(response_body), {"code": 0, "data": "ok"})

        call = fetch.last_call
        self.assertEqual(call["url"], expected_url)
        self.assertEqual(call["method"], method)
        self.assertEqual(call["headers"]["authorization"], "Bearer sk-test")
        if expected_body is None:
            self.assertIsNone(call["body"])
        else:
            self.assertEqual(call["body"].decode("utf-8"), expected_body)

    def test_get_worlds_maps_to_openapi_worlds_list(self):
        fetch = RecordingFetch(response=json_response({"code": 0, "data": []}))
        base_url = self.start_server(fetch)

        status, body = http_request(
            f"{base_url}/server-api/worlds?page=1&filter=a%20b"
        )

        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body), {"code": 0, "data": []})
        call = fetch.last_call
        self.assertEqual(
            call["url"],
            "https://example.test/api/v2/apps/happyoyster-1.0/openapi/v1/worlds?page=1&filter=a%20b",
        )
        self.assertEqual(call["method"], "GET")
        self.assertIsNone(call["body"])

    def test_post_worlds_maps_to_openapi_world_creation(self):
        fetch = RecordingFetch(response=json_response({"code": 0, "data": {"id": 1}}))
        base_url = self.start_server(fetch)
        request_body = b'{"title":"oyster"}'

        status, body = http_request(
            f"{base_url}/server-api/worlds",
            method="POST",
            body=request_body,
            headers={"content-type": "application/json"},
        )

        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body), {"code": 0, "data": {"id": 1}})
        call = fetch.last_call
        self.assertEqual(
            call["url"],
            "https://example.test/api/v2/apps/happyoyster-1.0/openapi/v1/worlds",
        )
        self.assertEqual(call["body"], request_body)

    def test_post_worlds_preserves_request_body_bytes(self):
        body = b'{\n  "mode": 2,\n  "prompt": "oyster"\n}'
        self.assert_proxy_mapping(
            request_path="/server-api/worlds",
            expected_url=(
                "https://example.test/api/v2/apps/happyoyster-1.0"
                "/openapi/v1/worlds"
            ),
            method="POST",
            body=body,
            expected_body=body.decode("utf-8"),
        )

    def test_post_worlds_forwards_scenario_role_fields(self):
        request_body = {
            "mode": 1,
            "async": True,
            "perspective": "first_person",
            "uploadMode": "scenario_role",
            "scenePrompt": "A neon oyster market at night",
            "rolePrompt": "A cheerful robot guide",
            "sceneImage": {
                "url": "https://cdn.example.com/scene.jpg",
                "referenceType": "default",
            },
            "roleImage": {
                "url": "https://cdn.example.com/role.jpg",
                "referenceType": "default",
            },
            "inputImages": [
                {
                    "base64": "SU5QVVRfSU1BR0U=",
                    "referenceType": "default",
                }
            ],
        }

        fetch = RecordingFetch(response=json_response({"code": 0, "data": {"id": 1}}))
        base_url = self.start_server(fetch)

        status, _ = http_request(
            f"{base_url}/server-api/worlds",
            method="POST",
            body=json.dumps(request_body).encode("utf-8"),
            headers={"content-type": "application/json"},
        )

        self.assertEqual(status, 200)
        call = fetch.last_call
        self.assertEqual(json.loads(call["body"].decode("utf-8")), request_body)

    def test_post_worlds_forwards_scriptlist_base64_image_refs(self):
        request_body = {
            "mode": 2,
            "async": True,
            "creationModel": "scriptlist",
            "resolution": "720p",
            "firstFrameImage": {
                "base64": "data:image/png;base64,iVBORw0KGgo=",
            },
            "scriptList": {
                "synopsis": "A rainy neon street.",
                "subjects": [
                    {
                        "label": "[character_1]",
                        "type": "character",
                        "refImage": {
                            "base64": "UkVGX0lNQUdF",
                            "referenceType": "default",
                        },
                    }
                ],
                "acts": [
                    {
                        "turn": 1,
                        "content": "[character_1] looks at the rain.",
                    }
                ],
            },
        }
        fetch = RecordingFetch(response=json_response({"code": 0, "data": {"id": 1}}))
        base_url = self.start_server(fetch)

        status, _ = http_request(
            f"{base_url}/server-api/worlds",
            method="POST",
            body=json.dumps(request_body).encode("utf-8"),
            headers={"content-type": "application/json"},
        )

        self.assertEqual(status, 200)
        self.assertEqual(
            json.loads(fetch.last_call["body"].decode("utf-8")), request_body
        )

    def test_post_travel_credential_maps_to_get_travel_credential(self):
        self.assert_proxy_mapping(
            request_path="/server-api/travel-credential",
            expected_url=(
                "https://example.test/api/v2/apps/happyoyster-1.0"
                "/openapi/v1/worlds/get-travel-credential"
            ),
            method="POST",
            body=b'{"encryptedWorldId":"ENC_WORLD"}',
            expected_body='{"encryptedWorldId":"ENC_WORLD"}',
        )

    def test_get_build_status_maps_to_openapi_build_status(self):
        self.assert_proxy_mapping(
            request_path="/server-api/worlds/build-status?encryptedWorldId=ENC_WORLD",
            expected_url=(
                "https://example.test/api/v2/apps/happyoyster-1.0"
                "/openapi/v1/worlds/build-status?encryptedWorldId=ENC_WORLD"
            ),
        )

    def test_get_world_detail_maps_to_openapi_world_detail(self):
        self.assert_proxy_mapping(
            request_path="/server-api/worlds/detail?encryptedWorldId=ENC_WORLD",
            expected_url=(
                "https://example.test/api/v2/apps/happyoyster-1.0"
                "/openapi/v1/worlds/detail?encryptedWorldId=ENC_WORLD"
            ),
        )

    def test_post_world_delete_maps_to_openapi_world_deletion(self):
        self.assert_proxy_mapping(
            request_path="/server-api/worlds/delete",
            expected_url=(
                "https://example.test/api/v2/apps/happyoyster-1.0"
                "/openapi/v1/worlds/delete"
            ),
            method="POST",
            body=b'{"encryptedWorldId":"ENC_WORLD"}',
            expected_body='{"encryptedWorldId":"ENC_WORLD"}',
        )

    def test_get_travels_maps_to_openapi_travels_list(self):
        self.assert_proxy_mapping(
            request_path="/server-api/travels?page=1&pageSize=20",
            expected_url=(
                "https://example.test/api/v2/apps/happyoyster-1.0"
                "/openapi/v1/travels?page=1&pageSize=20"
            ),
        )

    def test_get_artifacts_maps_to_openapi_artifacts(self):
        self.assert_proxy_mapping(
            request_path="/server-api/travels/artifacts?encryptedTravelId=ENC_TRAVEL",
            expected_url=(
                "https://example.test/api/v2/apps/happyoyster-1.0"
                "/openapi/v1/travels/artifacts?encryptedTravelId=ENC_TRAVEL"
            ),
        )

    def test_post_update_script_maps_to_openapi_script_update(self):
        body = json.dumps(
            {
                "encryptedTravelId": "ENC_TRAVEL",
                "scriptList": {
                    "acts": [
                        {"turn": index + 1, "content": f"act {index + 1}"}
                        for index in range(45)
                    ]
                },
                "userAgent": "sdk-test/1.0",
            },
            separators=(",", ":"),
        ).encode("utf-8")
        self.assert_proxy_mapping(
            request_path="/server-api/travels/update-script",
            expected_url=(
                "https://example.test/api/v2/apps/happyoyster-1.0"
                "/openapi/v1/travels/update-script"
            ),
            method="POST",
            body=body,
            expected_body=body.decode("utf-8"),
        )

    def test_temp_api_key_mints_temporary_dashscope_key(self):
        fetch = RecordingFetch(
            response=json_response({"token": "st-test", "expires_at": 1744080369})
        )
        base_url = self.start_server(fetch)

        status, body = http_request(
            f"{base_url}/server-api/temp-api-key?expire_in_seconds=1800", method="POST"
        )

        self.assertEqual(status, 200)
        self.assertEqual(
            json.loads(body), {"token": "st-test", "expires_at": 1744080369}
        )
        call = fetch.last_call
        self.assertEqual(
            call["url"], "https://example.test/api/v1/tokens?expire_in_seconds=1800"
        )
        self.assertEqual(call["method"], "POST")
        self.assertEqual(call["headers"]["authorization"], "Bearer sk-test")
        self.assertIsNone(call["body"])

    def test_temp_api_key_rejects_invalid_ttl(self):
        fetch = RecordingFetch(error=AssertionError("invalid ttl must not call upstream"))
        base_url = self.start_server(fetch)

        status, body = http_request(
            f"{base_url}/server-api/temp-api-key",
            method="POST",
            body=json.dumps({"expireInSeconds": 1801}).encode("utf-8"),
            headers={"content-type": "application/json"},
        )

        self.assertEqual(status, 400)
        self.assertEqual(
            json.loads(body),
            {
                "success": False,
                "errorCode": "PARAM_INVALID",
                "message": "expire_in_seconds must be an integer between 1 and 1800",
            },
        )
        self.assertEqual(fetch.calls, [])

    def test_temp_api_key_rejects_boolean_ttl(self):
        fetch = RecordingFetch(error=AssertionError("invalid ttl must not call upstream"))
        base_url = self.start_server(fetch)

        status, body = http_request(
            f"{base_url}/server-api/temp-api-key",
            method="POST",
            body=json.dumps({"expireInSeconds": True}).encode("utf-8"),
            headers={"content-type": "application/json"},
        )

        self.assertEqual(status, 400)
        self.assertEqual(
            json.loads(body),
            {
                "success": False,
                "errorCode": "PARAM_INVALID",
                "message": "expire_in_seconds must be an integer between 1 and 1800",
            },
        )
        self.assertEqual(fetch.calls, [])

    def test_temp_api_key_rejects_non_object_json_body(self):
        fetch = RecordingFetch(
            error=AssertionError("invalid body must not call upstream")
        )
        base_url = self.start_server(fetch)

        status, body = http_request(
            f"{base_url}/server-api/temp-api-key",
            method="POST",
            body=b"null",
            headers={"content-type": "application/json"},
        )

        self.assertEqual(status, 400)
        self.assertEqual(
            json.loads(body),
            {
                "success": False,
                "errorCode": "PARAM_INVALID",
                "message": "request body must be a JSON object",
            },
        )
        self.assertEqual(fetch.calls, [])

    def test_unknown_path_returns_404(self):
        base_url = self.start_server(RecordingFetch(response=json_response({})))

        status, body = http_request(f"{base_url}/missing")

        self.assertEqual(status, 404)
        self.assertEqual(body, b"Not Found\n")

    def test_unknown_server_api_path_returns_404(self):
        fetch = RecordingFetch(error=AssertionError("unknown path must not call upstream"))
        base_url = self.start_server(fetch)

        status, body = http_request(f"{base_url}/server-api/typo")

        self.assertEqual(status, 404)
        self.assertEqual(body, b"Not Found\n")
        self.assertEqual(fetch.calls, [])

    def test_unsupported_method_returns_405(self):
        base_url = self.start_server(RecordingFetch(response=json_response({})))

        status, body = http_request(f"{base_url}/server-api/worlds", method="OPTIONS")

        self.assertEqual(status, 405)
        self.assertEqual(body, b"Method Not Allowed\n")

    def test_upstream_failure_returns_stable_502_envelope(self):
        fetch = RecordingFetch(error=RuntimeError("network down"))
        base_url = self.start_server(fetch)

        status, body = http_request(f"{base_url}/server-api/worlds")

        self.assertEqual(status, 502)
        self.assertEqual(
            json.loads(body),
            {
                "success": False,
                "errorCode": "UPSTREAM_ERROR",
                "message": "Upstream OpenAPI request failed",
            },
        )


if __name__ == "__main__":
    unittest.main()
