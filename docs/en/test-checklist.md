# Happy Oyster Python Demo API Test Checklist


This document verifies the `/server-api/*` endpoints exposed by `happyoyster-sdk-demo-python`. The main flow is "create world -> wait for build -> issue a temporary API Key (`token`) and exchange a one-time Travel ticket -> query server-side records -> clean up resources".

The single source of truth for the endpoint list, request parameters, and response fields is [`server-api-reference.md`](server-api-reference.md). This document only records the recommended test order, copy-paste-ready curl commands, and the key fields to observe at each step.

These curl commands target a local integration testing environment. For production integration, the third-party server must add its own business login, authorization, tenant isolation, and resource ownership checks on top of `/server-api/*`.

## 1. Pre-test Setup

Before starting, you must configure the Bailian API Host and the main API Key:

```bash
export BAILIAN_API_HOST='llm-<your-workspace-id>.cn-beijing.maas.aliyuncs.com'
export DASHSCOPE_API_KEY='sk-...'
python3 server.py
```

`BAILIAN_API_HOST` is obtained from the "API Host" field on the API Key page of the Bailian console, for example `llm-<your-workspace-id>.cn-beijing.maas.aliyuncs.com`. This demo completes the fixed gateway path internally as `https://{BAILIAN_API_HOST}/api/v2/apps/happyoyster-1.0`.

The API Host must be used with an API Key from the same account and region; otherwise the gateway may return `AccessDenied` or `401`. API Keys are region-specific and cannot be used across regions.

Python `>= 3.9` is required. The current project has no runtime dependencies, so no additional web framework needs to be installed.

### Local Address and Port

By default the server listens on the local address:

```text
http://127.0.0.1:3000
```

To switch the port, start with the `PORT` environment variable:

```bash
PORT=3100 python3 server.py
```

The corresponding access address changes to:

```text
http://127.0.0.1:3100
```

When testing on a real mobile device, listen on all network interfaces instead:

```bash
HOST=0.0.0.0 python3 server.py
```

If you also switch the port, pass `HOST` and `PORT` together:

```bash
HOST=0.0.0.0 PORT=3100 python3 server.py
```

Look up the computer's Wi-Fi IP:

```bash
ipconfig getifaddr en0
```

Assuming the output is `192.168.1.23`, once the phone and the computer are on the same Wi-Fi network, the phone can access the corresponding port:

```text
http://192.168.1.23:3000/server-api
http://192.168.1.23:3100/server-api
```

This is the phone accessing the computer's Python demo directly; no proxy needs to be configured in the phone's Wi-Fi settings. A proxy tool is only needed when you want to forward the online domain the App originally accesses to the computer for packet capture or a local service. If the address is not reachable, check the macOS firewall, that both devices are on the same LAN, and guest network isolation.

Common response conventions:

- Except for `POST /server-api/temp-api-key`, business responses are wrapped in `output`.
- Success check: `output.code == 0`.
- Business data: read `output.data`.
- If a top-level string `code` is returned, treat it as a proxy or gateway-layer error.
- `mode` uses numeric values: `1=adventure`, `2=directing`; do not pass strings.
- Do not pass `userAgent` in GET query strings or World POST bodies; if you need to identify the client, use the HTTP `User-Agent` header.
- The current demo demonstrates a single-user / single main API Key scenario and does not implement business-level user isolation.
- When Bailian injects a workspace, Worlds and Travels are isolated by `uid + workspace`. Assert `403001` for a cross-workspace World and `404000` for a cross-workspace Travel. Do not construct `x-dashscope-*` / `X-Ho-*` headers yourself.

During testing it is recommended to record these variables:

```bash
WORLD_ID='fill in encryptedWorldId after creating a world'
TRAVEL_TICKET='fill in ticket after getting the Travel ticket'
TRAVEL_ID='fill in encryptedTravelId once a client-side Travel exists'
```

## 2. Temporary API Key Tests

### 1. Issue a Temporary API Key

When to call: when an App or Web client needs to call SDK-side endpoints. A complete client entry flow requires this token and a Travel ticket; they are not alternatives.

Endpoint:

```text
POST /server-api/temp-api-key
```

Query example:

```bash
curl -sS -X POST 'http://127.0.0.1:3000/server-api/temp-api-key?expire_in_seconds=1800'
```

Body example:

```bash
curl -sS -X POST 'http://127.0.0.1:3000/server-api/temp-api-key' \
  -H 'Content-Type: application/json' \
  -d '{"expire_in_seconds":1800}'
```

Request parameters:

- `expire_in_seconds`: optional, TTL in seconds, range `1..1800`.
- `expireInSeconds`: optional, camelCase alias usable in the JSON body.

The successful response is not wrapped in `output`:

```json
{
  "token": "st-****",
  "expires_at": 1744080369
}
```

Refreshing the token later does not require exchanging for another Travel ticket.

Local parameter error response:

```json
{
  "success": false,
  "errorCode": "PARAM_INVALID",
  "message": "expire_in_seconds must be an integer between 1 and 1800"
}
```

It is recommended to additionally test two error cases:

```bash
curl -sS -X POST 'http://127.0.0.1:3000/server-api/temp-api-key?expire_in_seconds=0'
curl -sS -X POST 'http://127.0.0.1:3000/server-api/temp-api-key' \
  -H 'Content-Type: application/json' \
  -d '{bad json'
```

## 3. Main Flow Tests

### 2. Create a World

When to call: the starting point of the tests. For the main server-side flow it is recommended to use `async=true` or omit `async`.

Endpoint:

```text
POST /server-api/worlds
```

Directing example:

```bash
curl -sS -X POST 'http://127.0.0.1:3000/server-api/worlds' \
  -H 'Content-Type: application/json' \
  -d '{
    "mode": 2,
    "async": true,
    "prompt": "An ancient city floating above the clouds",
    "resolution": "720p",
    "layout": "Stable",
    "narrative": "Dramatic"
  }'
```

Adventure first_frame example:

`https://cdn.example.com/*.jpg` is a placeholder resource URL and will fail if copied as-is. For integration testing, replace it with a real, publicly accessible image URL in the expected format.

```bash
curl -sS -X POST 'http://127.0.0.1:3000/server-api/worlds' \
  -H 'Content-Type: application/json' \
  -d '{
    "mode": 1,
    "async": true,
    "prompt": "An ancient city floating above the clouds",
    "perspective": "first_person",
    "uploadMode": "first_frame",
    "firstFrameImage": {
      "url": "https://cdn.example.com/a.jpg",
      "referenceType": "default"
    }
  }'
```

Adventure first_frame base64 example:

```bash
IMAGE_BASE64="$(base64 -i your-image.png | tr -d '\n')"
curl -sS -X POST 'http://127.0.0.1:3000/server-api/worlds' \
  -H 'Content-Type: application/json' \
  -d "{
    \"mode\": 1,
    \"async\": true,
    \"prompt\": \"Rainy neon street at night\",
    \"perspective\": \"first_person\",
    \"uploadMode\": \"first_frame\",
    \"firstFrameImage\": {
      \"base64\": \"$IMAGE_BASE64\"
    }
  }"
```

Adventure scenario_role example (no top-level `prompt`):

```bash
curl -sS -X POST 'http://127.0.0.1:3000/server-api/worlds' \
  -H 'Content-Type: application/json' \
  -d '{
    "mode": 1,
    "async": true,
    "perspective": "first_person",
    "uploadMode": "scenario_role",
    "scenePrompt": "An ancient city floating above the clouds",
    "rolePrompt": "An oyster guide wearing a cloak",
    "sceneImage": {
      "url": "https://cdn.example.com/scene.jpg",
      "referenceType": "default"
    },
    "roleImage": {
      "url": "https://cdn.example.com/role.jpg",
      "referenceType": "default"
    }
  }'
```

Main request parameters:

- `mode`: required, `1=adventure`, `2=directing`.
- `async`: optional, defaults to `true`; `false` waits synchronously, which can take up to 120 seconds.
- `prompt`: required for first_frame / Directing simple; scenario_role does not need a top-level `prompt`, but at least one of `scenePrompt` / `rolePrompt` must be provided, or both `sceneImage` and `roleImage` must be provided, each containing either `url` or `base64`.
- `eventStyle`: optional, `normal` / `dramatic`.
- `refWorldId`: optional, encrypted ID of a reference template world.
- Adventure: `perspective` is required; `uploadMode` is optional and defaults to `first_frame`; `firstFrameImage`, `sceneImage`, `roleImage`, `scenePrompt`, and `rolePrompt` are passed conditionally depending on the upload mode.
- Directing: `resolution` is required; `layout`, `narrative`, `firstFrameImage`, and `inputImages` are optional.
- Image objects: `firstFrameImage`, `sceneImage`, `roleImage`, `inputImages[]`, and `scriptList.subjects[].refImage` all support either `url` or `base64`. Both raw base64 and a `data:image/png;base64,...` data URI must succeed. JPG/JPEG/PNG/WebP images must each be strictly smaller than 30 MB and at most 4096×4096 pixels. First-frame aspect ratio must be in the inclusive range `1.5..2.0`; other reference images do not have this ratio requirement.
- ScriptList creation and `update-script` both require exactly 45 acts, ordered as continuous, non-duplicate turns 1 through 45. Assert the complete schema: `synopsis` is required on create; subjects are limited to 6 with valid labels, types, and text lengths; content is limited to 2,000 characters per act and 100,000 total; and `cameraType`, `shotSize`, and `cut` use only the documented enums.

Also test the unified creation error response: non-`application/json` Content-Type, malformed JSON, invalid enums, and invalid image size / format / ratio must all return HTTP `200` with `output.code=400000`, not HTTP `400` / `415`.

Key fields to check on success:

- `output.data.encryptedWorldId`: save as `WORLD_ID`.
- `output.data.status`: usually `generating`, but may also be `ready` directly.
- `output.data.firstFrame`: first-frame information.

Next step: poll the build status with `WORLD_ID`.

### 3. Poll the Build Status

When to call: call in a loop after creating a world, until `status` is `ready` or `failed`.

Endpoint:

```text
GET /server-api/worlds/build-status
```

Example:

```bash
curl -sS "http://127.0.0.1:3000/server-api/worlds/build-status?encryptedWorldId=$WORLD_ID"
```

Query parameters:

- `encryptedWorldId`: required, the encrypted world ID returned when creating the world.

Key fields to check on success:

- `output.data.status`: `generating` / `ready` / `failed`.
- `output.data.name`: usually only has a value after `ready`.
- `output.data.mode`: usually only has a value after `ready`.
- `output.data.firstFrame`: first-frame information.

Next step: after `ready`, query the world detail, or get the Travel ticket directly.

### 4. Query World Detail

When to call: to confirm the details after the world is created; it is recommended to test after `ready`.

Endpoint:

```text
GET /server-api/worlds/detail
```

Example:

```bash
curl -sS "http://127.0.0.1:3000/server-api/worlds/detail?encryptedWorldId=$WORLD_ID"
```

Query parameters:

- `encryptedWorldId`: required.

Key fields to check on success:

- `output.data.encryptedWorldId`
- `output.data.name`
- `output.data.status`
- `output.data.mode`
- `output.data.prompt`
- `output.data.previewUrl`
- `output.data.creationModel`
- `output.data.eventStyle`
- `output.data.perspective`
- `output.data.uploadMode`
- `output.data.resolution`
- `output.data.layout`
- `output.data.narrative`
- `output.data.refWorldId`
- `output.data.firstFrameImage`
- `output.data.inputImages`
- `output.data.sceneImage`
- `output.data.roleImage`
- `output.data.scenePrompt`
- `output.data.rolePrompt`
- `output.data.scriptList`: a ScriptList world must return the complete persisted structure and `prompt=null`
- `output.data.createdAt`
- `output.data.updatedAt`

Next step: get the Travel ticket.

### 5. Get the Travel Ticket

When to call: after the world is `ready`. If the world is not ready yet, `403002` is returned.

Recommended endpoint:

```text
POST /server-api/travel-credential
```

Example:

```bash
curl -sS -X POST 'http://127.0.0.1:3000/server-api/travel-credential' \
  -H 'Content-Type: application/json' \
  -d "{\"encryptedWorldId\":\"$WORLD_ID\"}"
```

Body parameters:

- `encryptedWorldId`: required.

Key fields to check on success:

- `output.data.ticket`: save as `TRAVEL_TICKET` and hand it to the App / Web client together with the token.
- `output.data.expiresIn`: 1800 seconds (30 minutes); the ticket can be consumed only once.
- `output.data.encryptedWorldId`

Next step: return both token and ticket to the client. The client authenticates `POST /openapi/v1/travels/enter-travel` with the token and sends the ticket in the body. For Adventure it may also pass the JSON integer `maxExperienceTimeSec=60/90/120`; omission defaults to 60 and Directing ignores it. Assert that the response returns the effective `maxExperienceTimeSec` for Adventure and `null` for Directing, while an invalid type or tier returns `400000`. The client then owns RTC / playback and runtime controls. The server continues to own World management, credential exchange, Travel history, and artifacts. Refreshing the token does not require a new ticket.

For client rewind integration, also assert that the server rounds `rewindToSec` to an act boundary using approximately four seconds per act, `actualRewindToSec` is the actual landing point, and `resumedAtSec` has the same value.

### 5.1 Optional: Full ScriptList Update (Server-Side)

When to call: after the client has entered a Directing Travel created from a ScriptList world, when you need to fully replace the 45 turn acts at runtime.

Endpoint:

```text
POST /server-api/travels/update-script
```

Example:

```bash
curl -sS -X POST 'http://127.0.0.1:3000/server-api/travels/update-script' \
  -H 'Content-Type: application/json' \
  -d @scriptlist-update.json
```

Generate a valid example containing exactly 45 acts:

```bash
python3 - <<'PY'
import json

acts = [
    {"turn": turn, "content": f"act {turn} content"}
    for turn in range(1, 46)
]
with open("scriptlist-update.json", "w", encoding="utf-8") as file:
    json.dump(
        {"encryptedTravelId": "TRAVEL_ID_FROM_ENTER_TRAVEL", "scriptList": {"acts": acts}},
        file,
        ensure_ascii=False,
        indent=2,
    )
PY
```

`scriptList.acts` must contain exactly 45 items ordered as every continuous turn from 1 through 45. Test 44/46 items, duplicate or out-of-order turns, empty content, per-act / total overflow, and invalid `cameraType` / `shotSize` / `cut`; each must return `400000`. The upstream only consumes acts; `subjects` and world-level fields such as `synopsis` keep the values stored at world creation time. Calling `instruct` for a ScriptList world must still return `403006 INSTRUCT_NOT_ALLOWED`.

### 6. Query the World List

When to call: to verify the world records under the current main API Key, or to filter by status / mode.

Endpoint:

```text
GET /server-api/worlds
```

Example:

```bash
curl -sS 'http://127.0.0.1:3000/server-api/worlds?page=1&pageSize=20'
curl -sS 'http://127.0.0.1:3000/server-api/worlds?page=1&pageSize=20&status=ready&mode=2'
```

Query parameters:

- `page`: optional, defaults to `1`.
- `pageSize`: optional, defaults to `20`, maximum `100`.
- `status`: optional, `ready` / `failed` / `generating`.
- `mode`: optional, `1=adventure`, `2=directing`.

Key fields to check on success:

- `output.data.items[]`
- `output.data.pagination.page`
- `output.data.pagination.pageSize`
- `output.data.pagination.total`
- `output.data.pagination.hasMore`

Main fields in `items[]`:

- `encryptedWorldId`
- `name`
- `status`
- `mode`
- `perspective`
- `creationModel`
- `uploadMode`
- `createdAt`

### 7. Query the Travel List

When to call: once a client-side Travel exists, to view Travel records on the server side.

Endpoint:

```text
GET /server-api/travels
```

Example:

```bash
curl -sS 'http://127.0.0.1:3000/server-api/travels?page=1&pageSize=20'
curl -sS "http://127.0.0.1:3000/server-api/travels?page=1&pageSize=20&encryptedWorldId=$WORLD_ID"
```

Query parameters:

- `page`: optional.
- `pageSize`: optional.
- `status`: optional, e.g. `running` / `completed` / `failed`.
- `encryptedWorldId`: optional, used to query Travels under a specific world.

Key fields to check on success:

- `output.data.items[]`
- `output.data.pagination`

Main fields in `items[]`:

- `encryptedTravelId`: save as `TRAVEL_ID`, used to query artifacts.
- `status`
- `mode`
- `encryptedWorldId`
- `durationSec`
- `createdAt`
- `endedAt`

Next step: query the artifacts after the Travel completes.

### 8. Query Travel Artifacts

When to call: after the Travel status is `completed`.

Endpoint:

```text
GET /server-api/travels/artifacts
```

Example:

```bash
curl -sS "http://127.0.0.1:3000/server-api/travels/artifacts?encryptedTravelId=$TRAVEL_ID"
```

Query parameters:

- `encryptedTravelId`: required.

Key fields to check on success:

- `output.data.encryptedTravelId`
- `output.data.composeStatus`
- `output.data.video`

`video` always contains four variants: `original`, `withWatermark`, `withInstruction`, and `withInstructionAndWatermark`. The structure of each value:

```json
{
  "url": "https://example.com/video.mp4",
  "status": "ready",
  "resolution": "720p",
  "durationSec": null
}
```

### 9. Delete a World

When to call: to clean up resources after testing is done.

Endpoint:

```text
POST /server-api/worlds/delete
```

Example:

```bash
curl -sS -X POST 'http://127.0.0.1:3000/server-api/worlds/delete' \
  -H 'Content-Type: application/json' \
  -d "{\"encryptedWorldId\":\"$WORLD_ID\"}"
```

Body parameters:

- `encryptedWorldId`: required.

Key fields to check on success:

- `output.data.encryptedWorldId`
- `output.data.deleted`

## 4. Common Failure Points

- `BAILIAN_API_HOST is required`: the Bailian API Host was not configured before startup.
- `DASHSCOPE_API_KEY is required`: the main API Key was not configured before startup.
- `403002 WORLD_NOT_READY`: the Travel ticket was requested before the world became ready.
- `403003 MAIN_API_KEY_REQUIRED`: a temporary API Key was used on a management or server-only endpoint. Supported SDK runtime endpoints use the temporary Key.
- `TRAVEL_NO_STREAM_AUTO_END`: after starting the Travel, the client did not receive a stream within `noStreamAutoEndTimeoutSec`; the Travel should be ended and marked as failed.
- `400000 PARAM_INVALID`: a field name, type, or required field does not match the API requirements.
- Top-level string `code`: treat it as a proxy or gateway-layer error, not as the business `output.code`.
