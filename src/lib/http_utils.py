"""HTTP response helper utilities."""

import json

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


def method_not_allowed(handler):
    send_body(handler, 405, "Method Not Allowed\n")


def not_found(handler):
    send_body(handler, 404, "Not Found\n")
