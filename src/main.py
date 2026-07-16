"""Process entry: create the server, listen, and handle shutdown signals."""

import logging
import signal
import threading
from http.server import ThreadingHTTPServer

from .app import create_request_handler
from .config import load_env


def serve(config=None, logger=None):
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    log = logger or logging.getLogger("happyoyster-sdk-demo")
    config = config or load_env()

    server = ThreadingHTTPServer(
        (config.host, config.port),
        create_request_handler(config=config, logger=log),
    )

    def shutdown(signum, frame):
        threading.Thread(target=server.shutdown, daemon=True).start()

    for sig in (signal.SIGINT, signal.SIGTERM):
        signal.signal(sig, shutdown)

    log.info(
        "Happy Oyster demo server listening on http://%s:%s/server-api",
        config.host,
        config.port,
    )

    try:
        server.serve_forever()
    finally:
        server.server_close()
