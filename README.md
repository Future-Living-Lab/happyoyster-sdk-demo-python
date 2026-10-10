# Happy Oyster SDK Demo Python

**English** | [简体中文](docs/zh/README.md)

A Python reference implementation for the third-party server used with the client SDK (App / Web). Production third-party servers may use any server-side language. It shows how the third-party server uses the main `DASHSCOPE_API_KEY` for management and server-only APIs, then returns both credentials required by the client: a temporary API Key (`token`) and a one-time Travel `ticket`.

This repository exposes only the `/server-api/*` sample endpoints. The server creates and manages Worlds, exchanges credentials, and queries Travel history and artifacts. The client SDK uses the temporary API Key and ticket to enter a Travel, establish RTC / playback, and perform runtime controls through `/openapi/v1/*`.

## Requirements

- Python `>= 3.9`
- Bailian API Host: injected via the `BAILIAN_API_HOST` env var. Use the bare host shown on the API Key page of the Bailian console
- Bailian main API Key: injected via the `DASHSCOPE_API_KEY` env var

The API Host must be used with an API Key from the same account and region; otherwise the gateway may return `AccessDenied` or `401`. API Keys are region-specific and cannot be used across regions.

The project has no runtime dependencies and uses only the Python standard library; just start it.

## Quick Start

Set the Bailian API Host and main API Key before starting. See `.env.example` for all supported variables; the demo does not read `.env` files automatically:

```bash
export BAILIAN_API_HOST='llm-<your-workspace-id>.cn-beijing.maas.aliyuncs.com'
export DASHSCOPE_API_KEY='sk-...'
python3 server.py
```

Use this demo only for local integration testing or controlled environments. For production, add business authentication in front of `/server-api/*`; do not expose an unauthenticated demo directly to the public internet or untrusted clients.

Default listen address:

```text
http://127.0.0.1:3000
```

Switch the local port via `PORT`:

```bash
PORT=3100 python3 server.py
```

For testing on a real mobile device, listen on all interfaces and use your computer's Wi-Fi IP:

```bash
HOST=0.0.0.0 python3 server.py
HOST=0.0.0.0 PORT=3100 python3 server.py
ipconfig getifaddr en0
```

Assuming the computer's Wi-Fi IP is `192.168.1.23`, the phone accesses:

```text
http://192.168.1.23:3000/server-api
http://192.168.1.23:3100/server-api
```

The phone talks directly to the Python demo on your computer; no proxy needs to be configured in the phone's Wi-Fi settings. See [`test-checklist.md`](docs/en/test-checklist.md) for the full self-test procedure.

Verify the server API:

```bash
curl 'http://127.0.0.1:3000/server-api/worlds?page=1&pageSize=10'
```

Except for the normal response of `POST /server-api/temp-api-key`, business responses pass through the Bailian app gateway wrapper: read `output.code` to determine business success and `output.data` for the business payload.

Shortest main flow:

```text
POST /server-api/worlds
  -> GET /server-api/worlds/build-status, poll until ready
  -> POST /server-api/temp-api-key
  -> POST /server-api/travel-credential
  -> return both token and output.data.ticket to the App / Web client
```

The ticket is valid for 30 minutes and can be consumed only once. Refreshing an expired temporary API Key does not require exchanging for a new ticket.

## Call Boundary

| Capability                     | Owner / caller             | Exposed by the Python demo |
| ------------------------------ | -------------------------- | -------------------------- |
| Create / list / delete Worlds  | Third-party server         | Yes, `/server-api/worlds*` |
| Query build status / detail    | Third-party server         | Yes, `/server-api/worlds/build-status` and `/server-api/worlds/detail` |
| Issue token / Travel ticket    | Third-party server         | Yes, `/server-api/temp-api-key` and `/server-api/travel-credential` |
| Query Travel history / artifacts | Third-party server      | Yes, `/server-api/travels` and `/server-api/travels/artifacts` |
| Full ScriptList update         | Third-party server      | Yes, `/server-api/travels/update-script` |
| Enter Travel / RTC / playback / runtime controls | Client SDK (App / Web) | No; the SDK calls supported `/openapi/v1/*` runtime endpoints with the temporary Key |

This demo assumes one user and one main API Key; it does not implement login, user mapping, tenant isolation, or resource ownership checks. Add your own authentication and authorization before production use.

## Environment

| Name                   | Default          | Description                                                                       |
| ---------------------- | ---------------- | --------------------------------------------------------------------------------- |
| `HOST`                 | `127.0.0.1`      | Local listen address                                                              |
| `PORT`                 | `3000`           | Local listen port                                                                 |
| `BAILIAN_API_HOST`     | none             | Required. Bailian API Host (bare host, without scheme or path)                    |
| `DASHSCOPE_API_KEY`    | none             | Required. Used by management and server-only endpoints as `Authorization: Bearer ...` |
| `REQUEST_TIMEOUT_MS`   | `130000`         | Upstream request timeout, covers the up-to-120s synchronous wait of `async=false` |

This demo only goes through the Bailian app gateway, matching the real third-party integration path.

`BAILIAN_API_HOST` comes from the "API Host" field on the API Key page of the Bailian console, e.g. `llm-<your-workspace-id>.cn-beijing.maas.aliyuncs.com`. This demo selects the fixed online App ID by mode (`1=adventure`, `2=directing`, `3=acting`) and builds `https://{BAILIAN_API_HOST}/api/v2/apps/{APP_ID}`. Only production App IDs are supported. Set `mode` in World creation/list requests and `X-Happy-Oyster-Mode: 1|2|3` for follow-up requests.

`DASHSCOPE_API_KEY` must be a main API Key for management and server-only endpoints. Client SDK runtime endpoints that support temporary Keys must use the temporary Key instead. If a temporary API Key is used to call an endpoint that requires the main API Key, the server returns `403003 MAIN_API_KEY_REQUIRED`.

The Bailian app gateway wraps open-API business responses as `{ request_id, output }`. Third-party apps should read `output.code` / `output.data`, not a bare `{ code, data }`.

## API Documents

| Document                                                     | Purpose                                                                                                       |
| ------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------- |
| [`server-api-reference.md`](docs/en/server-api-reference.md) | Must-read. `/server-api/*` contract: endpoint list, when to call, params, responses                           |
| [`test-checklist.md`](docs/en/test-checklist.md)             | For integration testing. Step-by-step tests in recommended order with copy-paste curl                        |
| [`openapi-client-api.md`](docs/en/openapi-client-api.md)     | Reference. SDK runtime and upstream `/openapi/v1/**` contract; not the default entry point of the Python demo |

## Architecture

```text
server.py                                    # compatibility entry, only starts src.main
src/main.py                                  # process entry: create server, listen, signal exit
src/app.py                                   # composition root: error boundary + access log + routing
src/config.py                                # env var loading, defaults, basic validation
src/routes.py                                # /server-api/*, 404, 405 dispatch
src/lib/http_utils.py                        # text / JSON response helpers
src/lib/request_body.py                      # raw request body reading
src/lib/upstream_client.py                   # generic upstream request, timeout, error wrapping
src/modules/providers/bailian_app_provider.py # Bailian app gateway provider
src/modules/providers/header_utils.py        # forwardable header filtering
src/modules/proxy/proxy_controller.py        # proxy controller
src/modules/tokens/token_controller.py       # temporary API Key issuing controller
src/modules/tokens/token_service.py          # temporary API Key issuing service
```

## Test

```bash
python3 -m unittest discover -s test -t .
```

Tests use Python's built-in `unittest`; no extra test framework is introduced.
