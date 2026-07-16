"""Read the raw request body for the POST routes exposed by this demo."""


def read_request_body(handler):
    if handler.command != "POST":
        return None

    content_length = int(handler.headers.get("Content-Length") or 0)
    if content_length <= 0:
        return None
    return handler.rfile.read(content_length)
