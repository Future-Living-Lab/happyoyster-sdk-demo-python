# Happy Oyster OpenAPI / SDK 运行态参考（经百炼 app 网关）


> 本文档是 SDK 运行态和上游开放平台参考，包含不由 Python demo 包装、经百炼 API Host 派生出的 OpenAPI 运行态接口。只接入本 Python demo 的三方服务端开发者，应优先阅读 [`server-api-reference.md`](server-api-reference.md)；逐项测试看 [`test-checklist.md`](test-checklist.md)。

本文档面向需要直接调用百炼 app 网关的 SDK / 客户端团队，说明 Happy Oyster 开放接口的运行态契约。它不是 Python demo 的默认接入入口；三方服务端示例路径只看 `/server-api/*`。

已同步：

- Happy Oyster 开放接口请求 / 响应字段
- 主 API Key 限制与 `403003`
- 百炼 app 网关响应包装、错误码处理、响应 Header 约定
- Travel 无推流自动结束、客户端推流状态上报和 `failCode`

## 一、调用链路

```text
SDK / 客户端
  -> 百炼 app 网关（公网）
  -> Happy Oyster 开放接口
```

SDK 只面向百炼 app 网关公网业务地址调用。百炼网关鉴权后注入用户身份等上下文 header，开放接口返回业务数据，百炼再把响应包装一层返回给 SDK。

## 二、SDK 运行态接入信息

| 项               | 值                                                                                          |
| ---------------- | ------------------------------------------------------------------------------------------- |
| App ID          | 模式 `1/2/3` 选择 `happyoyster-1.0-adventure` / `happyoyster-1.0-directing` / `happyoyster-1.0-acting` |
| API Host        | `${BAILIAN_API_HOST}`，百炼 API Host（裸 host，不含 scheme 和 path）              |
| 完整地址示例     | `https://${BAILIAN_API_HOST}/api/v2/apps/happyoyster-1.0-directing/openapi/v1/worlds`       |
| 鉴权             | `Authorization: Bearer ${API_KEY}`；支持的 SDK 运行态接口用临时 Key，管理类 / 仅服务端接口用主 Key |

`BAILIAN_API_HOST` 从百炼控制台 API Key 页的“API Host”获取，例如 `llm-<your-workspace-id>.cn-beijing.maas.aliyuncs.com`。完整 OpenAPI 网关地址为 `https://${BAILIAN_API_HOST}/api/v2/apps/{APP_ID}`；模式 1/2/3 分别选择 Adventure / Directing / Acting App ID。

API Host 必须与同一账号、同一地域的 API Key 配套使用，否则网关可能返回 `AccessDenied` 或 `401`；各地域 API Key 相互独立，不能跨地域使用。

客户端使用三方服务端签发的临时 API Key（下文简称 `token`）。主 `DASHSCOPE_API_KEY` 只保留在服务端，禁止嵌入 App 或 Web 客户端。

用户身份不需要 SDK 传。百炼按 API Key 注入以下 header 供后端读取；调用方不要自行构造这些 header：

| 网关注入 Header                    | 后端用途                                                               |
| ---------------------------------- | ---------------------------------------------------------------------- |
| `x-dashscope-uid`                  | 用户 ID（主账号 uid），用于识别用户和资源归属校验                      |
| `x-dashscope-workspace`            | 百炼业务空间 ID；存在时与 uid 共同作为 World / Travel 数据隔离维度     |
| `x-dashscope-inner-workspace-meta` | JSON，含 `region`；`ap-southeast-1` 为国际，其它如 `cn-beijing` 为国内 |
| `X-DashScope-Inner-Temp-Token`     | `true` 表示临时 API Key，影响部分接口可用性                            |

SDK 不要也不能自带 `x-dashscope-*` / `X-Ho-*` 网关注入头。本 demo 会剥离这类调用方传入的头，只发送客户侧 app 网关请求。

当前 Python demo 没有实现三方业务自己的用户体系，按单用户 / 单主 API Key 场景演示：不做业务用户登录、用户 ID 映射、租户隔离或资源归属二次校验。生产接入时，三方服务端需要在 demo 外层补齐自己的用户鉴权与授权逻辑，再决定是否允许当前业务用户创建、查询、删除世界或换取凭证。

开放平台在网关注入 `x-dashscope-workspace` 时按 `uid + workspace` 隔离 World 和 Travel；跨 workspace 访问 World 通常返回 `403001`，跨 workspace 访问 Travel 通常返回 `404000`。调用方不得自行构造 workspace 头；若网关没有注入该头，当前服务为兼容存量链路退化为仅按 uid 隔离。

## 三、请求 / 响应包装约定

### 3.1 请求

- Path：先按 mode 选择 App ID，再拼接接口路径。例：`GET /openapi/v1/worlds` -> `GET https://${BAILIAN_API_HOST}/api/v2/apps/happyoyster-1.0-directing/openapi/v1/worlds`。
- Query：原样透传，直接拼 URL。
- Body：`POST` / `PUT` / `PATCH` 的 JSON body 即业务 body；`GET` / `DELETE` 无 body。

### 3.2 成功响应（output 包装）

百炼把后端业务响应外面再包一层 `{ request_id, output }`：

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

`output` 才是开放接口的业务信封 `{ code, message, data }`。SDK 先取 `output`，再读业务字段。判定成败用 `output.code == 0`，不要只看 HTTP 状态码。

### 3.3 错误处理

百炼 app 网关不改写开放接口业务错误码。SDK 需要区分两类错误。

业务错误：后端已返回业务信封，`output.code` 是数值码：

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

代理 / 网关错误：网关未拿到开放接口响应或代理异常，`code` 是字符串状态名：

| 异常               | DashScope status | code                 |
| ------------------ | ---------------- | -------------------- |
| 连接后端失败       | `503`            | `ServiceUnavailable` |
| 请求后端超时       | `504`            | `ResponseTimeout`    |
| 其它 HTTP 传输异常 | `503`            | `ServiceUnavailable` |
| 代理处理异常       | `500`            | `InternalError`      |

处理建议：`output.code` 为数字时按业务错误码处理；`code` 为字符串时按代理 / 网关层错误处理，通常走重试、熔断或告警。后端返回非 JSON 时，`output` 可能形如 `{ "raw": "<文本>" }`。

## 四、公共约定

### 4.1 业务信封（output 内）

| 字段      | 类型   | 含义                              |
| --------- | ------ | --------------------------------- |
| `code`    | int    | `0` 表示成功，非 `0` 为错误码     |
| `message` | string | 成功时为 `null`，失败时为错误描述 |
| `data`    | object | 业务数据，失败时通常为 `null`     |

### 4.2 加密 ID

World ID / Travel ID 对外为加密串：

- `encryptedWorldId`
- `encryptedTravelId`

服务端下发后 SDK 原样透传，不可自造。加密 ID 绑定 userId，跨账号访问会失败（世界归属错误通常 `403001`，Travel 归属错误通常 `404000`）。

### 4.3 通用枚举

| 枚举        | 取值                                                    |
| ----------- | ------------------------------------------------------- |
| mode 类型码 | `1 = adventure`，`2 = directing`，`3 = acting`                               |
| 世界状态    | `generating` / `ready` / `failed`                       |
| Travel 状态    | `init` / `pending` / `running` / `completed` / `failed` |

注意：最新 OpenAPI DTO 中 `mode` 为数值类型码。创建、列表过滤和响应里的 `mode` 都使用 `1 / 2`，不要传字符串形式的 `adventure / directing`。

### 4.4 错误码（output.code，数值）

| 数值码   | 枚举名                      | 含义                                           |
| -------- | --------------------------- | ---------------------------------------------- |
| `0`      | `SUCCESS`                   | 成功                                           |
| `400000` | `PARAM_INVALID`             | 通用参数非法                                   |
| `404000` | `RESOURCE_NOT_FOUND`        | 资源不存在，含部分 ID 不归属当前账号场景       |
| `401010` | `TICKET_INVALID`            | Travel ticket 无效或已过期                   |
| `401011` | `TICKET_USED`               | Travel ticket 已被使用                       |
| `403001` | `WORLD_NOT_OWNED`           | 世界不归属当前账号                             |
| `403002` | `WORLD_NOT_READY`           | 世界状态非 READY，无法开始体验                     |
| `403003` | `MAIN_API_KEY_REQUIRED`     | 当前接口仅允许主 API Key 调用，临时 Key 不可用 |
| `403004` | `CONTENT_MODERATION_REJECTED` | 输入内容或指令被安审拦截                     |
| `403005` | `CONTENT_COPYRIGHT_VIOLATION` | 输入图片版权 / IP 违规                       |
| `403006` | `INSTRUCT_NOT_ALLOWED`      | `creationModel=scriptlist` 剧本世界不支持发送指令 |
| `409000` | `STATE_CONFLICT`            | 当前资源状态与请求冲突                         |
| `500001` | `INFERENCE_ALLOCATE_FAILED` | 推理资源分配失败                               |
| `500000` | `SYSTEM_ERROR`              | 系统错误；服务异常会被 OpenAPI 包装成该码      |

### 4.5 分页

列表接口 `output.data` 为：

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

### 4.6 主 API Key 限制

管理类和仅服务端接口要求主 API Key；右栏 SDK 运行态接口支持临时 Key，因此不能把 `403003` 绝对化为所有运行态接口都要求主 Key。

| 仅主 Key                                                               | 主 Key + 临时 Key 均可                                                      |
| ---------------------------------------------------------------------- | --------------------------------------------------------------------------- |
| 创建世界、世界列表、世界详情、删除世界、获取 Travel ticket、Travel 列表、查产物、更新剧本 | 查构建状态、开始体验、查状态、回溯、暂停、恢复、结束、发送指令 |

### 4.7 客户端标识

GET 接口不支持 Query 参数 `userAgent`，World 全部接口也不读取 body `userAgent`。客户端标识优先通过 HTTP `User-Agent` Header 传递；仅 Travel 控制类 POST（如 `rewind` / `pause` / `resume` / `end` / `instruct` / `update-script`）可在 body 中显式传 `userAgent` 并优先于 Header。

### 4.8 临时 API Key 签发（三方服务端接口）

浏览器、移动 App 等不可信客户端不要持有主 API Key。三方服务端用主 `DASHSCOPE_API_KEY` 调百炼 token 接口生成临时 API Key，再返回给客户端：

```text
POST https://llm-<your-workspace-id>.cn-beijing.maas.aliyuncs.com/api/v1/tokens?expire_in_seconds=1800
Authorization: Bearer ${DASHSCOPE_API_KEY}
```

百炼默认 TTL 为 60 秒，`expire_in_seconds` 范围为 `1..1800` 秒。正常响应：

```json
{
  "token": "st-****",
  "expires_at": 1744080369
}
```

本 Python demo 提供对应服务端接口：

```bash
curl -sS -X POST 'http://127.0.0.1:3000/server-api/temp-api-key?expire_in_seconds=1800'
```

也可通过 JSON body 传 `expire_in_seconds` 或 `expireInSeconds`。临时 API Key 到期自动失效，不能提前删除；刷新临时 Key 无需重新换取 Travel ticket。

## 五、业务接口清单

实际地址 = `https://${BAILIAN_API_HOST}/api/v2/apps/{APP_ID}` + endpoint path（例如 `/openapi/v1/worlds`），由 mode 选择 App ID。

| #   | 接口             | Method | Path                                       | 需主 Key |
| --- | ---------------- | ------ | ------------------------------------------ | -------- |
| 1   | 创建世界         | POST   | `/openapi/v1/worlds`                       | 是       |
| 2   | 世界列表         | GET    | `/openapi/v1/worlds`                       | 是       |
| 3   | 查构建状态       | GET    | `/openapi/v1/worlds/build-status`          | 否       |
| 4   | 世界详情         | GET    | `/openapi/v1/worlds/detail`                | 是       |
| 5   | 删除世界         | POST   | `/openapi/v1/worlds/delete`                | 是       |
| 6   | 获取 Travel ticket     | POST   | `/openapi/v1/worlds/get-travel-credential` | 是       |
| 7   | 开始体验         | POST   | `/openapi/v1/travels/enter-travel`         | 否       |
| 8   | 查询 Travel 状态     | GET    | `/openapi/v1/travels/status`               | 否       |
| 9   | 回溯             | POST   | `/openapi/v1/travels/rewind`               | 否       |
| 10  | 暂停             | POST   | `/openapi/v1/travels/pause`                | 否       |
| 11  | 恢复             | POST   | `/openapi/v1/travels/resume`               | 否       |
| 12  | 结束             | POST   | `/openapi/v1/travels/end`                  | 否       |
| 13  | 发送文本指令     | POST   | `/openapi/v1/travels/instruct`             | 否       |
| 14  | ScriptList 全量更新 | POST | `/openapi/v1/travels/update-script`        | 是       |
| 15  | Travel 列表         | GET    | `/openapi/v1/travels`                      | 是       |
| 16  | 查产物           | GET    | `/openapi/v1/travels/artifacts`            | 是       |

典型调用链：

```text
创建世界
  -> 轮询构建状态至 ready
  -> 签发临时 API Key + 获取一次性 Travel ticket
  -> 同时使用两项凭证开始体验
  -> 轮询状态并上报客户端推流状态
  -> 回溯 / 暂停 / 恢复 / 发指令
  -> 结束
  -> 查产物
```

## 六、接口详情

以下“响应 data 字段”均位于 `output.data` 内。

### 1. 创建世界

`POST /openapi/v1/worlds`，需主 Key。

`async=false` 会同步等待构建完成，最长 120 秒；超时后降级返回 `generating`。三方服务端主链路建议使用默认异步，并轮询构建状态。

请求 body：

| 字段                         | 类型    | 必填 | 说明                                           |
| ---------------------------- | ------- | ---- | ---------------------------------------------- |
| `mode`                       | integer | 是   | `1=adventure`，`2=directing`，`3=acting`                          |
| `async`                      | boolean | 否   | 默认 `true`；`false` 同步等待                  |
| `creationModel`              | string  | 否   | `simple`（默认）/ `scriptlist`；仅 `mode=2` 有效 |
| `prompt`                     | string  | 条件 | Adventure / Acting first_frame 与 Directing simple 必填；ScriptList 不接受 |
| `eventStyle`                 | string  | 否   | `normal` / `dramatic`                          |
| `refWorldId`                 | string  | 否   | 参考模板世界加密 ID                            |
| `perspective`                | string  | 条件 | Adventure 必填：`first_person` / `third_person`   |
| `uploadMode`                 | string  | 否   | Adventure / Acting：仅 `first_frame` |
| `aspectRatio` | string | 否 | 仅 Acting：`9:16`（默认）/ `16:9`，图片画幅须匹配 |
| `firstFrameImage`            | object  | 条件   | Adventure / Acting 与 ScriptList 必填；Directing simple 可选：`{ url 或 base64, referenceType }` |
| `resolution`                 | string  | 否 | Directing：`480p`（默认）/ `720p` |
| `layout`                     | string  | 否   | Directing：`Stable` / `Fast`                       |
| `narrative`                  | string  | 否   | Directing：`Calm` / `Dramatic` / `Normal`          |
| `inputImages`                | array   | 否   | `[{ url 或 base64, referenceType }]`           |
| `scriptList`                 | object  | 条件 | `creationModel=scriptlist` 时必填              |

图片引用对象 `firstFrameImage`、`inputImages[]`、`scriptList.subjects[].refImage` 使用 HTTP(S) `url` 或 `base64` 二选一，不能同时提供；`base64` 可用裸字符串或 `data:image/xxx;base64,...`。`referenceType` 可选，默认 `default`。解码后的 JPG/JPEG/PNG/WebP 图片单张严格小于 30MB、至多 4096×4096 像素；Adventure / Directing 首帧宽高比须为 `1.5..2.0`，Acting 首帧须匹配 `aspectRatio`（默认 `9:16`，也可为 `16:9`）。

`prompt` 为空或纯空白会被上游视为缺失。Adventure / Acting 的 first_frame 和 Directing simple 必须传非空 `prompt`；ScriptList 创建使用 `scriptList.synopsis`。

`creationModel=scriptlist` 仅支持 Directing 世界，需传 `firstFrameImage`（含 `url` 或 `base64` 之一）和 `scriptList`，不接受 `prompt`、`layout`、`narrative`、`inputImages`、`perspective`、`uploadMode`、`sceneImage`、`roleImage`、`scenePrompt`、`rolePrompt` 等 prompt / Adventure 字段。创建和运行中 `update-script` 都要求 `scriptList.acts` 恰好 45 条，turn 按数组顺序覆盖 1 到 45、连续且不可重复。

ScriptList 完整 schema 和约束：

| 字段 | 类型 | 创建必填 | 约束 |
| ---- | ---- | -------- | ---- |
| `scriptList.synopsis` | string | 是 | 最长 2000 字符；`update-script` 不消费 |
| `scriptList.videoTitle` | string | 否 | 最长 128 字符 |
| `scriptList.scene` / `style` / `speed` / `language` | string | 否 | 各最长 64 字符 |
| `scriptList.setting` | string | 否 | 最长 2000 字符 |
| `scriptList.soundtrack` | string | 否 | 最长 500 字符 |
| `scriptList.prologue` | string | 否 | 最长 1000 字符 |
| `scriptList.videoTags` | string[] | 否 | 最多 20 个，单项最长 32 字符 |
| `scriptList.subjects` | array | 否 | 最多 6 个；`update-script` 不消费 |
| `subjects[].label` | string | 否 | `[character_1]` 到 `[character_6]`，省略时按顺序补齐；不可重复 |
| `subjects[].name` / `gender` / `position` / `ethnicity` / `age` | string | 否 | 各最长 64 字符 |
| `subjects[].type` | string | 否 | `character` / `animal` / `creature` / `narrator` |
| `subjects[].refImage` | object | 否 | `{ url 或 base64, referenceType }`，遵循通用图片约束 |
| `subjects[].appearance` | string | 否 | 最长 500 字符 |
| `subjects[].voice` | string | 否 | 最长 200 字符 |
| `scriptList.acts` | array | 是 | 创建和更新均必须恰好 45 条 |
| `acts[].turn` | integer | 否 | 1 到 45；省略时使用数组位置，最终必须按顺序连续且不可重复 |
| `acts[].content` | string | 是 | 非空，单条最长 2000 字符，45 条合计最长 100000 字符；`[character_x]` 必须引用已定义主体 |
| `acts[].cameraType` | string | 否 | 默认 `Static`；`Static` / `Tracking` / `Pan Left` / `Pan Right` / `Tilt Up` / `Tilt Down` / `Push-in` / `Pull-out` / `POV Forward` / `POV Look Down` / `POV Look Up` / `POV Turn Left` / `POV Turn Right` |
| `acts[].shotSize` | string | 否 | 默认 `Medium`；`Wide` / `Medium` / `Close-up` |
| `acts[].cut` | string | 否 | 默认 `long-take`；`long-take` / `hard-cut` / `cut-in` / `cut-out` / `cutaway` / `cutback` / `camera movement transition` |

本接口的参数错误统一使用 OpenAPI 业务信封：参数或枚举非法、`Content-Type` 不是 `application/json`、畸形 JSON、图片对象同时传 `url` 与 `base64`、base64 为空或无法解码、图片超出大小/像素/比例限制、URL 非合法 HTTP(S) 图片地址等，均返回 HTTP `200` 且 `output.code=400000`；不要按旧行为期待 HTTP `400` / `415`。

响应 data：`encryptedWorldId`、`status`、`firstFrame`。

### 2. 世界列表

`GET /openapi/v1/worlds`，需主 Key。

Query：`page`、`pageSize`、`status`、`mode`。

- `page` 默认 `1`
- `pageSize` 默认 `20`，最大 `100`
- `status`: `ready` / `failed` / `generating`
- `mode`: integer，`1=adventure`，`2=directing`，`3=acting`

响应 data：`items[]` + `pagination`。

`items[]` 字段：`encryptedWorldId`、`name`、`status`、`mode`、`previewUrl`、`createdAt`、`perspective`、`creationModel`、`uploadMode`。

### 3. 查构建状态

`GET /openapi/v1/worlds/build-status`

Query：`encryptedWorldId` 必填。

响应 data：`encryptedWorldId`、`status`、`firstFrame`、`name`（仅 ready）、`mode`（仅 ready）。

### 4. 世界详情

`GET /openapi/v1/worlds/detail`，需主 Key。

Query：`encryptedWorldId` 必填。

响应 data 返回完整创建信息：`encryptedWorldId`、`name`、`status`、`mode`、`prompt`、`previewUrl`、`createdAt`、`updatedAt`、`creationModel`、`eventStyle`、`perspective`、`uploadMode`、`resolution`、`layout`、`narrative`、`refWorldId`、`firstFrameImage`、`inputImages`、`sceneImage`、`roleImage`、`scenePrompt`、`rolePrompt`、`scriptList`。ScriptList 世界的 `prompt` 固定为 `null`，并通过 `scriptList` 返回创建时持久化的完整结构；图片回显只含 URL / `referenceType`，不回显 base64。

### 5. 删除世界

`POST /openapi/v1/worlds/delete`，需主 Key。

Body：`encryptedWorldId` 必填。

响应 data：`encryptedWorldId`、`deleted`。

### 6. 获取 Travel ticket

`POST /openapi/v1/worlds/get-travel-credential`，需主 Key。

为已 ready 的世界签发一次性凭证。世界非 ready 返回 `403002`。

Body：`encryptedWorldId` 必填。鉴权仅依赖网关 AK Header，不再传 `signature`。

响应 data：`ticket`、`expiresIn=1800`（30 分钟）、`encryptedWorldId`。ticket 只能消费一次；刷新临时 API Key 无需重新换 ticket。

### 7. 开始体验

`POST /openapi/v1/travels/enter-travel`

使用临时 API Key 鉴权，并在 body 中传 `ticket`，两者缺一不可。ticket 无效或过期返回 `401010`，已使用返回 `401011`。

Body：`ticket` 必填；`maxExperienceTimeSec` 可选且必须是 JSON integer，仅 Adventure 生效，可选 `60` / `90` / `120`，省略默认 `60`，Directing 忽略该值；非法类型或档位返回 `400000`。

响应 data：`encryptedTravelId`、`encryptedWorldId`、`mode`、`creationModel`、`playUrl`（当前通常为 `null`）、`firstFrame`、`rtcConfig`、`version`、`noStreamAutoEndTimeoutSec`、`maxExperienceTimeSec`。后者在 Adventure 返回实际生效值，在 Directing 为 `null`。

`rtcConfig` 字段：`channelId`、`appId`、`token`、`userId`。

客户端开始体验后应轮询 `/openapi/v1/travels/status`。如果在 `noStreamAutoEndTimeoutSec` 秒内没有看到推流态（如 `rtcStatus=PUSHING`），应调用 `POST /openapi/v1/travels/end`，并传 `failCode=TRAVEL_NO_STREAM_AUTO_END`，让服务端把本次 Travel 标记为失败。

### 8. 查询Travel 状态

`GET /openapi/v1/travels/status`

Query：

- `encryptedTravelId`：必填。
- `clientStreamStatus`：可选，客户端观测到的推流状态；服务端会归一为大写并忽略未知值。
- `clientStreamStatusTimeMs`：可选，客户端观测时间戳，毫秒。

响应 data：`encryptedTravelId`、`status`、`rtcStatus`、`updateTime`、`userInstructions[]`、`chapters[]`、`characterActions[]`、`environmentActions[]`。

`chapters[]` 字段：`chapterId`、`title`、`brief`、`actRange`、`startTime`、`endTime`、`chapterImage`。

### 9. 回溯

`POST /openapi/v1/travels/rewind`

Body：`encryptedTravelId` 必填，`rewindToSec` 必填且 `>= 0`。

响应 data：`encryptedTravelId`、`status=running`、`actualRewindToSec`、`resumedAtSec`。

服务端按每个 act 约 4 秒换算并四舍五入到 act 边界，所以实际落点可能与请求的 `rewindToSec` 不同。`actualRewindToSec` 是实际回溯秒数，`resumedAtSec` 与其值相同并作为兼容字段保留。

### 10 / 11. 暂停 / 恢复

`POST /openapi/v1/travels/pause`

`POST /openapi/v1/travels/resume`

Body：`encryptedTravelId` 必填。

响应 data：`encryptedTravelId`、`status`（暂停为 `paused`，恢复为 `running`）。

### 12. 结束

`POST /openapi/v1/travels/end`

Body：

- `encryptedTravelId`：必填。
- `failCode`：可选。当前仅支持 `TRAVEL_NO_STREAM_AUTO_END`，用于 enterTravel 后超时未收到推流的自动结束场景。

正常结束响应 data：`encryptedTravelId`、`status=completed`、`endedAt`、`durationSec`。

传入 `failCode=TRAVEL_NO_STREAM_AUTO_END` 时，响应 data 中 `status=failed`，并返回 `errorCode`、`errorMessage`。

### 13. 发送文本指令

`POST /openapi/v1/travels/instruct`

Body：`encryptedTravelId` 必填，`content` 必填且非空。

响应 data：`encryptedTravelId`、`content`、`accepted`。

`creationModel=scriptlist` 的剧本世界不支持发送指令，调用返回 `403006 INSTRUCT_NOT_ALLOWED`；应改用 `update-script` 全量更新。

### 14. ScriptList 全量更新

`POST /openapi/v1/travels/update-script`，需主 Key。

Body：`encryptedTravelId` 必填，`scriptList` 必填。`scriptList.acts` 必须恰好 45 条，用于全量替换当前 Travel 剧本；ScriptList 世界不支持 `instruct` 增量文本指令。

响应 data：`encryptedTravelId`、`accepted`、`turnCount=45`。

### 15. Travel 列表

`GET /openapi/v1/travels`，需主 Key。

Query：`page`、`pageSize`、`status`、`encryptedWorldId`。

响应 data：`items[]` + `pagination`。

`items[]` 字段：`encryptedTravelId`、`status`、`mode`、`encryptedWorldId`、`durationSec`、`createdAt`、`endedAt`。

### 16. 查产物

`GET /openapi/v1/travels/artifacts`，需主 Key。

仅 completed Travel 有产物。

Query：`encryptedTravelId` 必填。

响应 data：`encryptedTravelId`、`composeStatus`、`video`。

`video` 固定包含 `original`、`withWatermark`、`withInstruction`、`withInstructionAndWatermark` 四个字段。每个值结构为 `{ url, status, resolution, durationSec }`；合成仍在处理中时 `url=null`、`status=processing`。

## 七、当前限制 / 注意

1. Query 参数为驼峰。后端读取 `pageSize`、`encryptedWorldId` 等；百炼原样透传 query，`page_size` 等下划线写法会被忽略或走默认值。
2. `mode` 是数值类型码，`1=adventure`、`2=directing`、`3=acting`。创建、列表过滤和响应都用数值，勿传旧版字符串。
3. 客户端开始体验后要以 `noStreamAutoEndTimeoutSec` 为上限监控推流状态；超时未见推流态（如 `PUSHING`）时调用 `/openapi/v1/travels/end` 并传 `failCode=TRAVEL_NO_STREAM_AUTO_END`。
4. GET 接口不支持 Query 参数 `userAgent`；World 接口也不读取 body `userAgent`。请用 HTTP `User-Agent` Header 作为客户端标识。
5. 部分服务端链路耗时头不会透传到 SDK，例如 `X-WorldModel-Request-Received-At-Ms` 与 `X-WorldModel-Request-Completed-At-Ms`。
6. SDK 侧耗时看网关自带头：`req-arrive-time`、`resp-start-time`、`req-cost-time`、`x-envoy-upstream-service-time`。

## 八、完整示例

### 8.1 GET 世界列表

```bash
curl --location "https://${BAILIAN_API_HOST}/api/v2/apps/happyoyster-1.0-directing/openapi/v1/worlds?page=1&pageSize=10&mode=2" \
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

### 8.2 POST 创建世界

```bash
curl --location "https://${BAILIAN_API_HOST}/api/v2/apps/happyoyster-1.0-directing/openapi/v1/worlds" \
  --header 'Content-Type: application/json' \
  --header 'Authorization: Bearer ${DASHSCOPE_API_KEY}' \
  --data '{
    "mode": 2,
    "async": true,
    "prompt": "一座漂浮在云端的古城",
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

### 8.3 错误响应

业务错误（数值 code）：

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

代理层错误（字符串 code）：

```json
{
  "request_id": "...",
  "code": "ServiceUnavailable",
  "message": "<503> ServiceUnavailable: downstream unreachable: ..."
}
```
