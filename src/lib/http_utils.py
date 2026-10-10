"""HTTP response helper utilities."""

import json
from uuid import uuid4

TEXT_CONTENT_TYPE = "text/plain; charset=utf-8"
JSON_CONTENT_TYPE = "application/json; charset=utf-8"


def send_body(handler, status_code, body, content_type=TEXT_CONTENT_TYPE):
    data = body.encode("utf-8") if isinstance(body, str) else bytes(body or b"")
    handler.send_response(status_code)
    handler.send_header("Content-Type", content_type)
    handler.send_header("Content-Length", str(len(data)))
    handler.end_headers()
    handler.wfile.write(data)


def send_json(handler, status_code, data):
    payload = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    send_body(handler, status_code, f"{payload}\n", JSON_CONTENT_TYPE)


def send_gateway_error(handler, code, message, data=None):
    send_json(
        handler,
        200,
        {
            "request_id": str(uuid4()),
            "output": {
                "code": code,
                "message": f"[happyoyster-sdk-demo-python] {message}",
                "data": data if data is not None else {},
            },
        },
    )


def method_not_allowed(handler):
    send_gateway_error(handler, "METHOD_NOT_ALLOWED", "Method Not Allowed")


def not_found(handler):
    send_gateway_error(handler, "NOT_FOUND", "Not Found")
