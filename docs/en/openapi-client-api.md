# Happy Oyster OpenAPI / SDK Runtime Reference (via Bailian App Gateway)


> This document is the SDK runtime and upstream open platform reference, covering the runtime endpoints derived from the Bailian API Host that are not wrapped by the Python demo. Third-party server developers who only integrate with this Python demo should read [`server-api-reference.md`](server-api-reference.md) first; for step-by-step testing see [`test-checklist.md`](test-checklist.md).

This document targets SDK / client teams that need to call the Bailian app gateway directly, and describes the runtime contract of the Happy Oyster open APIs. It is not the default integration entry point of the Python demo; for the third-party server example paths, look only at `/server-api/*`.

Already synchronized:

- Happy Oyster open API request / response fields
- Main API Key restrictions and `403003`
- Bailian app gateway response wrapping, error code handling, and response header conventions
- Travel auto-end when no stream is pushed, client stream status reporting, and `failCode`

## 1. Call Chain

```text
SDK / client
  -> Bailian app gateway (public network)
  -> Happy Oyster open APIs
```

The SDK only calls the public business address of the Bailian app gateway. After authenticating, the Bailian gateway injects context headers such as the user identity; the open APIs return business data, and Bailian wraps the response in one more layer before returning it to the SDK.

## 2. SDK Runtime Integration Info

| Item                 | Value                                                                                       |
| ---------------- | ------------------------------------------------------------------------------------------- |
| API Host        | `${BAILIAN_API_HOST}`, the Bailian API Host (bare host, without scheme or path) |
| Full URL example     | `https://${BAILIAN_API_HOST}/api/v2/apps/happyoyster-1.0/openapi/v1/worlds` |
| Authentication             | `Authorization: Bearer ${API_KEY}`; use a temporary Key for supported SDK runtime endpoints and the main Key for management / server-only endpoints |

`BAILIAN_API_HOST` is obtained from the "API Host" field on the API Key page of the Bailian console, for example `llm-<your-workspace-id>.cn-beijing.maas.aliyuncs.com`. The full OpenAPI gateway address is derived by adding the fixed path: `https://${BAILIAN_API_HOST}/api/v2/apps/happyoyster-1.0`.

The API Host must be used with an API Key from the same account and region; otherwise the gateway may return `AccessDenied` or `401`. API Keys are region-specific and cannot be used across regions.

The client uses a temporary API Key (`token`) issued by the third-party server. The main `DASHSCOPE_API_KEY` remains server-side and must never be embedded in an App or Web client.

The SDK does not need to pass the user identity. Bailian injects the following headers based on the API Key for the backend to read; callers must not construct these headers themselves:

| Gateway-injected header                    | Backend purpose                                                               |
| ---------------------------------- | ---------------------------------------------------------------------- |
| `x-dashscope-uid`                  | User ID (primary account uid), used to identify the user and validate resource ownership                      |
| `x-dashscope-workspace`            | Bailian workspace ID; when present, it combines with uid as the World / Travel isolation boundary |
| `x-dashscope-inner-workspace-meta` | JSON containing `region`; `ap-southeast-1` means international, others such as `cn-beijing` mean domestic (China) |
| `X-DashScope-Inner-Temp-Token`     | `true` indicates a temporary API Key, which affects the availability of some endpoints                            |

The SDK must not (and cannot) send its own `x-dashscope-*` / `X-Ho-*` gateway-injected headers. This demo strips such headers passed in by callers and only sends the client-side app gateway request.

The current Python demo does not implement a third-party business's own user system; it demonstrates a single-user / single main API Key scenario: no business user login, no user ID mapping, no tenant isolation, and no secondary resource ownership validation. For production integration, the third-party server must add its own user authentication and authorization logic on top of the demo, and then decide whether the current business user is allowed to create, query, or delete worlds, or exchange for credentials.

When the gateway injects `x-dashscope-workspace`, the open platform isolates Worlds and Travels by `uid + workspace`. Cross-workspace World access usually returns `403001`, while cross-workspace Travel access usually returns `404000`. Callers must not construct the workspace header themselves. If the gateway does not inject it, the current service falls back to uid-only isolation for compatibility with existing traffic.

## 3. Request / Response Wrapping Conventions

### 3.1 Request

- Path: append the endpoint path directly to the derived OpenAPI gateway address. Example: `GET /openapi/v1/worlds` -> `GET https://${BAILIAN_API_HOST}/api/v2/apps/happyoyster-1.0/openapi/v1/worlds`.
- Query: passed through as-is, appended directly to the URL.
- Body: for `POST` / `PUT` / `PATCH`, the JSON body is the business body; `GET` / `DELETE` have no body.

### 3.2 Success Response (output wrapping)

Bailian wraps the backend business response in one more layer, `{ request_id, output }`:

```json
{
  "request_id": "f51147e0-...",
  "output": {
    "code": 0,
    "message": null,
    "data": {}
  }
}
```

`output` is the business envelope `{ code, message, data }` of the open APIs. The SDK should first take `output`, then read the business fields. Determine success or failure with `output.code == 0`; do not rely on the HTTP status code alone.

### 3.3 Error Handling

The Bailian app gateway does not rewrite the business error codes of the open APIs. The SDK needs to distinguish two kinds of errors.

Business error: the backend has returned the business envelope, and `output.code` is a numeric code:

```json
{
  "request_id": "...",
  "output": {
    "code": 403002,
    "message": "World status is not READY and cannot be entered.",
    "data": null
  }
}
```

Proxy / gateway error: the gateway did not get a response from the open API or the proxy failed, and `code` is a string status name:

| Exception               | DashScope status | code                 |
| ------------------ | ---------------- | -------------------- |
| Failed to connect to the backend       | `503`            | `ServiceUnavailable` |
| Backend request timed out       | `504`            | `ResponseTimeout`    |
| Other HTTP transport exceptions | `503`            | `ServiceUnavailable` |
| Proxy processing exception       | `500`            | `InternalError`      |

Handling advice: when `output.code` is a number, handle it as a business error code; when `code` is a string, handle it as a proxy / gateway layer error, typically with retries, circuit breaking, or alerting. When the backend returns non-JSON content, `output` may look like `{ "raw": "<text>" }`.

## 4. Common Conventions

### 4.1 Business Envelope (inside output)

| Field      | Type   | Meaning                              |
| --------- | ------ | --------------------------------- |
| `code`    | int    | `0` means success; non-`0` is an error code     |
| `message` | string | `null` on success; an error description on failure |
| `data`    | object | Business data; usually `null` on failure     |

### 4.2 Encrypted IDs

World / travel IDs are exposed externally as encrypted strings:

- `encryptedWorldId`
- `encryptedTravelId`

After the server issues them, the SDK passes them through as-is and must not fabricate them. Encrypted IDs are bound to the userId; cross-account access will fail (wrong world ownership usually returns `403001`, wrong travel ownership usually returns `404000`).

### 4.3 Common Enums

| Enum        | Values                                                    |
| ----------- | ------------------------------------------------------- |
| mode type code | `1 = adventure`, `2 = directing`                               |
| World status    | `generating` / `ready` / `failed`                       |
| Travel status    | `init` / `pending` / `running` / `completed` / `failed` |

Note: in the latest OpenAPI DTOs, `mode` is a numeric type code. Creation, list filtering, and responses all use `1 / 2` for `mode`; do not pass the string values `adventure / directing`.

### 4.4 Error Codes (output.code, numeric)

| Numeric code   | Enum name                      | Meaning                                           |
| -------- | --------------------------- | ---------------------------------------------- |
| `0`      | `SUCCESS`                   | Success                                           |
| `400000` | `PARAM_INVALID`             | Generic invalid parameter                                   |
| `404000` | `RESOURCE_NOT_FOUND`        | Resource not found, including some cases where the ID does not belong to the current account       |
| `401010` | `TICKET_INVALID`            | Travel ticket is invalid or expired                   |
| `401011` | `TICKET_USED`               | Travel ticket has already been used                       |
| `403001` | `WORLD_NOT_OWNED`           | World does not belong to the current account                             |
| `403002` | `WORLD_NOT_READY`           | World status is not READY; Travel cannot be started                     |
| `403003` | `MAIN_API_KEY_REQUIRED`     | This endpoint only allows the main API Key; temporary Keys are not allowed |
| `403004` | `CONTENT_MODERATION_REJECTED` | Input content or instruction was blocked by content moderation                     |
| `403005` | `CONTENT_COPYRIGHT_VIOLATION` | Input image violates copyright / IP                       |
| `403006` | `INSTRUCT_NOT_ALLOWED`      | `creationModel=scriptlist` script worlds do not support sending instructions |
| `409000` | `STATE_CONFLICT`            | Current resource state conflicts with the request                         |
| `500001` | `INFERENCE_ALLOCATE_FAILED` | Failed to allocate inference resources                               |
| `500000` | `SYSTEM_ERROR`              | System error; service exceptions are wrapped by the OpenAPI into this code      |

### 4.5 Pagination

For list endpoints, `output.data` is:

```json
{
  "items": [],
  "pagination": {
    "page": 1,
    "pageSize": 20,
    "total": 0,
    "hasMore": false
  }
}
```

### 4.6 Main API Key Restrictions

Management and server-only endpoints require the main API Key. SDK runtime endpoints in the right column support temporary Keys; therefore `403003` must not be interpreted as applying to every runtime endpoint.

| Main Key only                                                               | Both main Key and temporary Key allowed                                                      |
| ---------------------------------------------------------------------- | --------------------------------------------------------------------------- |
| Create world, world list, world detail, delete world, get Travel ticket, travel list, query artifacts, update script | Query build status, start Travel, query status, rewind, pause, resume, end, send instruction |

### 4.7 Client Identification

GET endpoints do not support the query parameter `userAgent`, and none of the World endpoints read `userAgent` from the body. Client identification should preferably be passed via the HTTP `User-Agent` header; only Travel control POST endpoints (such as `rewind` / `pause` / `resume` / `end` / `instruct` / `update-script`) may pass `userAgent` explicitly in the body, which takes precedence over the header.

### 4.8 Temporary API Key Issuance (third-party server endpoint)

Untrusted clients such as browsers and mobile apps must not hold the main API Key. The third-party server uses the main `DASHSCOPE_API_KEY` to call the Bailian token endpoint to generate a temporary API Key, and then returns it to the client:

```text
POST https://llm-<your-workspace-id>.cn-beijing.maas.aliyuncs.com/api/v1/tokens?expire_in_seconds=1800
Authorization: Bearer ${DASHSCOPE_API_KEY}
```

Bailian's default TTL is 60 seconds; the range of `expire_in_seconds` is `1..1800` seconds. Normal response:

```json
{
  "token": "st-****",
  "expires_at": 1744080369
}
```

This Python demo provides a corresponding server endpoint:

```bash
curl -sS -X POST 'http://127.0.0.1:3000/server-api/temp-api-key?expire_in_seconds=1800'
```

`expire_in_seconds` or `expireInSeconds` can also be passed via a JSON body. Temporary API Keys expire automatically and cannot be deleted early. Refreshing the temporary Key does not require exchanging for a new Travel ticket.

## 5. Business Endpoint List

Actual URL = `https://${BAILIAN_API_HOST}/api/v2/apps/happyoyster-1.0` + endpoint path (for example `/openapi/v1/worlds`).

| #   | Endpoint             | Method | Path                                       | Main Key required |
| --- | ---------------- | ------ | ------------------------------------------ | -------- |
| 1   | Create world         | POST   | `/openapi/v1/worlds`                       | Yes       |
| 2   | World list         | GET    | `/openapi/v1/worlds`                       | Yes       |
| 3   | Query build status       | GET    | `/openapi/v1/worlds/build-status`          | No       |
| 4   | World detail         | GET    | `/openapi/v1/worlds/detail`                | Yes       |
| 5   | Delete world         | POST   | `/openapi/v1/worlds/delete`                | Yes       |
| 6   | Get travel credential     | POST   | `/openapi/v1/worlds/get-travel-credential` | Yes       |
| 7   | Start Travel         | POST   | `/openapi/v1/travels/enter-travel`         | No       |
| 8   | Query travel status     | GET    | `/openapi/v1/travels/status`               | No       |
| 9   | Rewind             | POST   | `/openapi/v1/travels/rewind`               | No       |
| 10  | Pause             | POST   | `/openapi/v1/travels/pause`                | No       |
| 11  | Resume             | POST   | `/openapi/v1/travels/resume`               | No       |
| 12  | End             | POST   | `/openapi/v1/travels/end`                  | No       |
| 13  | Send text instruction     | POST   | `/openapi/v1/travels/instruct`             | No       |
| 14  | ScriptList full update | POST | `/openapi/v1/travels/update-script`        | Yes      |
| 15  | Travel list         | GET    | `/openapi/v1/travels`                      | Yes       |
| 16  | Query artifacts           | GET    | `/openapi/v1/travels/artifacts`            | Yes       |

Typical call chain:

```text
Create world
  -> Poll build status until ready
  -> Issue temporary API Key + get one-time Travel ticket
  -> Start Travel with both credentials
  -> Poll status and report client stream status
  -> Rewind / pause / resume / send instructions
  -> End
  -> Query artifacts
```

## 6. Endpoint Details

All "response data fields" below are located inside `output.data`.

### 1. Create World

`POST /openapi/v1/worlds`, main Key required.

`async=false` waits synchronously for the build to complete, up to 120 seconds; after a timeout it degrades and returns `generating`. For third-party web main flows, using the default asynchronous mode and polling the build status is recommended.

Request body:

| Field                         | Type    | Required | Description                                           |
| ---------------------------- | ------- | ---- | ---------------------------------------------- |
| `mode`                       | integer | Yes   | `1=adventure`, `2=directing`                          |
| `async`                      | boolean | No   | Default `true`; `false` waits synchronously                  |
| `creationModel`              | string  | No   | `simple` (default) / `scriptlist`; only effective for `mode=2` |
| `prompt`                     | string  | Conditional | World theme description; required for first_frame / Directing simple, scenario_role does not need a top-level prompt |
| `eventStyle`                 | string  | No   | `normal` / `dramatic`                          |
| `refWorldId`                 | string  | No   | Encrypted ID of the reference template world                            |
| `perspective`                | string  | Conditional | Required for Adventure: `first_person` / `third_person`   |
| `uploadMode`                 | string  | No   | Adventure: `first_frame` / `scenario_role`        |
| `firstFrameImage`            | object  | No   | First-frame image for Adventure first_frame / Directing simple: `{ url or base64, referenceType }`, optional; required for scriptlist |
| `sceneImage` / `roleImage`   | object  | No   | Adventure scenario_role: `{ url or base64, referenceType }` |
| `scenePrompt` / `rolePrompt` | string  | No   | Adventure scene / role description                         |
| `resolution`                 | string  | Conditional | Required for Directing: `480p` / `720p`                    |
| `layout`                     | string  | No   | Directing: `Stable` / `Fast`                       |
| `narrative`                  | string  | No   | Directing: `Calm` / `Dramatic` / `Normal`          |
| `inputImages`                | array   | No   | `[{ url or base64, referenceType }]`           |
| `scriptList`                 | object  | Conditional | Required when `creationModel=scriptlist`              |

Image reference objects `firstFrameImage`, `sceneImage`, `roleImage`, `inputImages[]`, and `scriptList.subjects[].refImage` share the same structure: `url` is an HTTP(S) image URL, `base64` accepts both raw base64 and a `data:image/xxx;base64,...` data URI, and `referenceType` is optional and defaults to `default`. `url` and `base64` must not both be non-empty in the same object. URL images and decoded base64 images must be JPG/JPEG/PNG/WebP, each strictly smaller than 30 MB, with at most 4096×4096 pixels after decoding. A first-frame image must also be landscape with a width-to-height ratio in the inclusive range `1.5..2.0`; other reference images do not have this ratio requirement.

An empty, empty-string, or whitespace-only `prompt` is all treated as missing by the upstream. The default `first_frame` and Directing simple creation must pass a non-empty `prompt`; `scenario_role` does not require a top-level `prompt`, but requires at least one non-empty value among `scenePrompt` / `rolePrompt`, or both `sceneImage` and `roleImage` to be provided, each containing either `url` or `base64`.

`creationModel=scriptlist` only supports Directing worlds and requires `resolution`, `firstFrameImage` containing either `url` or `base64`, and `scriptList`. It does not accept prompt / Adventure fields such as `prompt`, `layout`, `narrative`, `inputImages`, `perspective`, `uploadMode`, `sceneImage`, `roleImage`, `scenePrompt`, or `rolePrompt`. Both creation and runtime `update-script` require exactly 45 acts, ordered as continuous, non-duplicate turns 1 through 45.

Complete ScriptList schema and constraints:

| Field | Type | Required on create | Constraint |
| ----- | ---- | ------------------ | ---------- |
| `scriptList.synopsis` | string | Yes | Maximum 2,000 characters; not consumed by `update-script` |
| `scriptList.videoTitle` | string | No | Maximum 128 characters |
| `scriptList.scene` / `style` / `speed` / `language` | string | No | Maximum 64 characters each |
| `scriptList.setting` | string | No | Maximum 2,000 characters |
| `scriptList.soundtrack` | string | No | Maximum 500 characters |
| `scriptList.prologue` | string | No | Maximum 1,000 characters |
| `scriptList.videoTags` | string[] | No | At most 20 tags, 32 characters per tag |
| `scriptList.subjects` | array | No | At most 6 entries; not consumed by `update-script` |
| `subjects[].label` | string | No | `[character_1]` through `[character_6]`; auto-assigned in order when omitted; no duplicates |
| `subjects[].name` / `gender` / `position` / `ethnicity` / `age` | string | No | Maximum 64 characters each |
| `subjects[].type` | string | No | `character` / `animal` / `creature` / `narrator` |
| `subjects[].refImage` | object | No | `{ url or base64, referenceType }`, subject to the common image constraints |
| `subjects[].appearance` | string | No | Maximum 500 characters |
| `subjects[].voice` | string | No | Maximum 200 characters |
| `scriptList.acts` | array | Yes | Exactly 45 entries for both creation and update |
| `acts[].turn` | integer | No | 1 through 45; defaults to the array position, and the final sequence must be ordered, continuous, and unique |
| `acts[].content` | string | Yes | Non-empty; maximum 2,000 characters per act and 100,000 in total; each `[character_x]` must reference a defined subject |
| `acts[].cameraType` | string | No | Default `Static`; `Static` / `Tracking` / `Pan Left` / `Pan Right` / `Tilt Up` / `Tilt Down` / `Push-in` / `Pull-out` / `POV Forward` / `POV Look Down` / `POV Look Up` / `POV Turn Left` / `POV Turn Right` |
| `acts[].shotSize` | string | No | Default `Medium`; `Wide` / `Medium` / `Close-up` |
| `acts[].cut` | string | No | Default `long-take`; `long-take` / `hard-cut` / `cut-in` / `cut-out` / `cutaway` / `cutback` / `camera movement transition` |

Parameter errors use the OpenAPI business envelope consistently. Invalid parameters or enums, a `Content-Type` other than `application/json`, malformed JSON, image objects that pass both `url` and `base64`, empty or undecodable base64, image size / pixel / ratio violations, and invalid non-HTTP(S) image URLs all return HTTP `200` with `output.code=400000`; do not expect the legacy HTTP `400` / `415` behavior.

Response data: `encryptedWorldId`, `status`, `firstFrame`.

### 2. World List

`GET /openapi/v1/worlds`, main Key required.

Query: `page`, `pageSize`, `status`, `mode`.

- `page` defaults to `1`
- `pageSize` defaults to `20`, maximum `100`
- `status`: `ready` / `failed` / `generating`
- `mode`: integer, `1=adventure`, `2=directing`

Response data: `items[]` + `pagination`.

`items[]` fields: `encryptedWorldId`, `name`, `status`, `mode`, `previewUrl`, `createdAt`, `perspective`, `creationModel`, `uploadMode`.

### 3. Query Build Status

`GET /openapi/v1/worlds/build-status`

Query: `encryptedWorldId` required.

Response data: `encryptedWorldId`, `status`, `firstFrame`, `name` (ready only), `mode` (ready only).

### 4. World Detail

`GET /openapi/v1/worlds/detail`, main Key required.

Query: `encryptedWorldId` required.

Response data includes the complete creation information: `encryptedWorldId`, `name`, `status`, `mode`, `prompt`, `previewUrl`, `createdAt`, `updatedAt`, `creationModel`, `eventStyle`, `perspective`, `uploadMode`, `resolution`, `layout`, `narrative`, `refWorldId`, `firstFrameImage`, `inputImages`, `sceneImage`, `roleImage`, `scenePrompt`, `rolePrompt`, and `scriptList`. For ScriptList worlds, `prompt` is always `null`, while `scriptList` returns the complete structure persisted at creation. Image echoes contain only URL / `referenceType`, never base64.

### 5. Delete World

`POST /openapi/v1/worlds/delete`, main Key required.

Body: `encryptedWorldId` required.

Response data: `encryptedWorldId`, `deleted`.

### 6. Get Travel Ticket

`POST /openapi/v1/worlds/get-travel-credential`, main Key required.

Issues a one-time credential for a world that is already ready. If the world is not ready, `403002` is returned.

Body: `encryptedWorldId` required. Authentication relies solely on the gateway AK header; `signature` is no longer passed.

Response data: `ticket`, `expiresIn=1800` (30 minutes), `encryptedWorldId`. The ticket can be consumed only once; refreshing the temporary API Key does not require a new ticket.

### 7. Start Travel

`POST /openapi/v1/travels/enter-travel`

Authenticate with the temporary API Key and pass `ticket` in the body; both are required. Invalid or expired tickets return `401010`; already-used tickets return `401011`.

Body: `ticket` is required. `maxExperienceTimeSec` is optional and must be a JSON integer. It applies only to Adventure, accepts `60` / `90` / `120`, and defaults to `60` when omitted; Directing ignores it. An invalid type or tier returns `400000`.

Response data: `encryptedTravelId`, `encryptedWorldId`, `mode`, `creationModel`, `playUrl` (currently usually `null`), `firstFrame`, `rtcConfig`, `version`, `noStreamAutoEndTimeoutSec`, and `maxExperienceTimeSec`. The last field contains the effective value for Adventure and is `null` for Directing.

`rtcConfig` fields: `channelId`, `appId`, `token`, `userId`.

After starting the Travel, the client should poll `/openapi/v1/travels/status`. If no streaming state (e.g. `rtcStatus=PUSHING`) is observed within `noStreamAutoEndTimeoutSec` seconds, the client should call `POST /openapi/v1/travels/end` with `failCode=TRAVEL_NO_STREAM_AUTO_END` so that the server marks this Travel as failed.

### 8. Query Travel Status

`GET /openapi/v1/travels/status`

Query:

- `encryptedTravelId`: required.
- `clientStreamStatus`: optional, the stream status observed by the client; the server normalizes it to uppercase and ignores unknown values.
- `clientStreamStatusTimeMs`: optional, the client observation timestamp in milliseconds.

Response data: `encryptedTravelId`, `status`, `rtcStatus`, `updateTime`, `userInstructions[]`, `chapters[]`, `characterActions[]`, `environmentActions[]`.

`chapters[]` fields: `chapterId`, `title`, `brief`, `actRange`, `startTime`, `endTime`, `chapterImage`.

### 9. Rewind

`POST /openapi/v1/travels/rewind`

Body: `encryptedTravelId` required, `rewindToSec` required and `>= 0`.

Response data: `encryptedTravelId`, `status=running`, `actualRewindToSec`, `resumedAtSec`.

The server converts time using approximately four seconds per act and rounds to an act boundary, so the actual landing point may differ from the requested `rewindToSec`. `actualRewindToSec` is the actual rewind position in seconds; `resumedAtSec` has the same value and is retained for compatibility.

### 10 / 11. Pause / Resume

`POST /openapi/v1/travels/pause`

`POST /openapi/v1/travels/resume`

Body: `encryptedTravelId` required.

Response data: `encryptedTravelId`, `status` (`paused` for pause, `running` for resume).

### 12. End

`POST /openapi/v1/travels/end`

Body:

- `encryptedTravelId`: required.
- `failCode`: optional. Currently only `TRAVEL_NO_STREAM_AUTO_END` is supported, used for the auto-end scenario where no stream is received within the timeout after enterTravel.

Normal-end response data: `encryptedTravelId`, `status=completed`, `endedAt`, `durationSec`.

When `failCode=TRAVEL_NO_STREAM_AUTO_END` is passed, the response data has `status=failed` and additionally returns `errorCode` and `errorMessage`.

### 13. Send Text Instruction

`POST /openapi/v1/travels/instruct`

Body: `encryptedTravelId` required, `content` required and non-empty.

Response data: `encryptedTravelId`, `content`, `accepted`.

Script worlds with `creationModel=scriptlist` do not support sending instructions; calls return `403006 INSTRUCT_NOT_ALLOWED`. Use `update-script` for a full update instead.

### 14. ScriptList Full Update

`POST /openapi/v1/travels/update-script`, main Key required.

Body: `encryptedTravelId` required, `scriptList` required. `scriptList.acts` must be exactly 45 entries, used to fully replace the current Travel script; ScriptList worlds do not support `instruct` incremental text instructions.

Response data: `encryptedTravelId`, `accepted`, `turnCount=45`.

### 15. Travel List

`GET /openapi/v1/travels`, main Key required.

Query: `page`, `pageSize`, `status`, `encryptedWorldId`.

Response data: `items[]` + `pagination`.

`items[]` fields: `encryptedTravelId`, `status`, `mode`, `encryptedWorldId`, `durationSec`, `createdAt`, `endedAt`.

### 16. Query Artifacts

`GET /openapi/v1/travels/artifacts`, main Key required.

Only completed travels have artifacts.

Query: `encryptedTravelId` required.

Response data: `encryptedTravelId`, `composeStatus`, `video`.

`video` always contains four fields: `original`, `withWatermark`, `withInstruction`, and `withInstructionAndWatermark`. Each value has the structure `{ url, status, resolution, durationSec }`; while composition is still in progress, `url=null` and `status=processing`.

## 7. Current Limitations / Notes

1. Query parameters are camelCase. The backend reads `pageSize`, `encryptedWorldId`, etc.; Bailian passes the query through as-is, so snake_case forms such as `page_size` are ignored or fall back to defaults.
2. `mode` is a numeric type code, `1=adventure`, `2=directing`. Creation, list filtering, and responses all use the numeric value; do not pass the legacy strings.
3. After starting the Travel, the client must monitor the stream status with `noStreamAutoEndTimeoutSec` as the upper bound; if no streaming state (e.g. `PUSHING`) is observed within the timeout, call `/openapi/v1/travels/end` with `failCode=TRAVEL_NO_STREAM_AUTO_END`.
4. GET endpoints do not support the query parameter `userAgent`; World endpoints do not read `userAgent` from the body either. Use the HTTP `User-Agent` header for client identification.
5. Some server-side latency headers are not passed through to the SDK, for example `X-WorldModel-Request-Received-At-Ms` and `X-WorldModel-Request-Completed-At-Ms`.
6. On the SDK side, use the gateway's built-in headers for latency: `req-arrive-time`, `resp-start-time`, `req-cost-time`, `x-envoy-upstream-service-time`.

## 8. Complete Examples

### 8.1 GET World List

```bash
curl --location "https://${BAILIAN_API_HOST}/api/v2/apps/happyoyster-1.0/openapi/v1/worlds?page=1&pageSize=10" \
  --header 'Authorization: Bearer ${DASHSCOPE_API_KEY}'
```

```json
{
  "request_id": "ddf3b005-...",
  "output": {
    "code": 0,
    "message": null,
    "data": {
      "items": [],
      "pagination": {
        "page": 1,
        "pageSize": 10,
        "total": 0,
        "hasMore": false
      }
    }
  }
}
```

### 8.2 POST Create World

```bash
curl --location "https://${BAILIAN_API_HOST}/api/v2/apps/happyoyster-1.0/openapi/v1/worlds" \
  --header 'Content-Type: application/json' \
  --header 'Authorization: Bearer ${DASHSCOPE_API_KEY}' \
  --data '{
    "mode": 2,
    "async": true,
    "prompt": "An ancient city floating above the clouds",
    "resolution": "720p",
    "layout": "Stable",
    "narrative": "Dramatic"
  }'
```

```json
{
  "request_id": "...",
  "output": {
    "code": 0,
    "message": null,
    "data": {
      "encryptedWorldId": "Zm9vYmFyMTIz",
      "status": "generating",
      "firstFrame": null
    }
  }
}
```

### 8.3 Error Responses

Business error (numeric code):

```json
{
  "request_id": "...",
  "output": {
    "code": 403003,
    "message": "This operation requires the main API Key.",
    "data": null
  }
}
```

Proxy-layer error (string code):

```json
{
  "request_id": "...",
  "code": "ServiceUnavailable",
  "message": "<503> ServiceUnavailable: downstream unreachable: ..."
}
```
