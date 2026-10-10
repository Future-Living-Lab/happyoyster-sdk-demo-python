# Happy Oyster Python Demo 服务端接口契约


本文档是本工程 `/server-api/*` 接口的唯一公开契约入口。外部用户查看“Python demo 暴露哪些接口、什么时候调用、入参是什么、出参是什么”，只看这里。

`/openapi/v1/**` 是上游开放平台 / SDK 运行态契约，不是本 demo 的默认调用入口。本 demo 示范三方服务端路径：服务端持有主 API Key，客户端完整进房需要同时拿到临时 API Key（下文简称 `token`）和一次性 Travel `ticket`。

## 一、通用约定

### 1.1 本地服务地址

本地默认地址：

```text
http://127.0.0.1:3000
```

所有业务接口都使用 `/server-api/*` 前缀。Python demo 再用服务端主 `DASHSCOPE_API_KEY` 调百炼 app 网关。

### 1.2 鉴权

本地调试调用 demo 接口时，客户端不需要传 `Authorization`。启动 Python demo 前必须配置百炼 API Host 和主 API Key：

```bash
export BAILIAN_API_HOST='llm-<your-workspace-id>.cn-beijing.maas.aliyuncs.com'
export DASHSCOPE_API_KEY='sk-...'
python3 server.py
```

`BAILIAN_API_HOST` 从百炼控制台 API Key 页的“API Host”获取，例如 `llm-<your-workspace-id>.cn-beijing.maas.aliyuncs.com`。本 demo 按 `mode` 选择固定线上 App ID：`1=adventure`、`2=directing`、`3=acting`，再拼接 `https://{BAILIAN_API_HOST}/api/v2/apps/{APP_ID}`。World 创建和列表从 body/query 读取 `mode`；其他接口通过 `X-Happy-Oyster-Mode: 1|2|3` 指定。此请求头不会转发给上游。这里只支持上述正式版 App ID。

API Host 必须与同一账号、同一地域的 API Key 配套使用，否则网关可能返回 `AccessDenied` 或 `401`；各地域 API Key 相互独立，不能跨地域使用。

管理类和仅服务端接口中的 `DASHSCOPE_API_KEY` 必须是主 API Key；允许临时 Key 的客户端 OpenAPI 不受此限制。

生产接入时，三方服务端必须在 `/server-api/*` 外层增加自己的登录态、用户授权、租户隔离和资源归属校验。不要把未加业务鉴权的 demo 直接暴露给不可信客户端。

### 1.3 响应包装

除 `POST /server-api/temp-api-key` 的正常响应外，其余业务接口透传百炼 app 网关响应。正常业务数据位于 `output.data`：

```json
{
  "request_id": "xxx",
  "output": {
    "code": 0,
    "message": null,
    "data": {}
  }
}
```

判断规则：

- `output.code == 0`：业务成功。
- `output.code != 0`：开放接口业务错误。
- 顶层字符串 `code`：代理或网关层错误，例如 `ResponseTimeout`。

本地 demo 自己产生的错误只用于参数校验、未知路由或上游请求失败，例如：

```json
{
  "request_id": "随机 UUID",
  "output": {
    "code": "UPSTREAM_ERROR",
    "message": "[happyoyster-sdk-demo-python] Upstream OpenAPI request failed",
    "data": {}
  }
}
```

本地错误统一返回 HTTP `200`，`output.code` 为字符串，`output.message` 带 `[happyoyster-sdk-demo-python]` 前缀；上游响应保持原样。

### 1.4 通用枚举

| 枚举        | 取值                                                                                 |
| ----------- | ------------------------------------------------------------------------------------ |
| `mode`      | `1 = adventure`，`2 = directing`，`3 = acting`                                                            |
| 世界状态    | `generating` / `ready` / `failed`                                                    |
| Travel 状态 | `init` / `pending` / `running` / `completed` / `failed`；`pause` 响应会返回 `paused` |

`mode` 必须使用数值，不要传字符串 `adventure` / `directing` / `acting`。

### 1.5 当前用户模型

当前 demo 没有实现三方业务自己的用户体系，按单用户 / 单主 API Key 场景演示：不做业务用户登录、用户 ID 映射、租户隔离或资源归属二次校验。生产接入时，三方服务端需要在本 demo 外层补齐自己的用户鉴权与授权逻辑。

开放平台在百炼网关注入 `x-dashscope-workspace` 时按 `uid + workspace` 隔离 World 和 Travel；跨 workspace 的 World 通常按 `403001` 处理，Travel 通常按 `404000` 处理。调用方不得伪造该头。本 demo 只有一个固定 `BAILIAN_API_HOST` / `DASHSCOPE_API_KEY` 上游身份，不替代三方业务自身的租户隔离。

## 二、接口总览

| #   | 接口             | Method | Path                              | 调用时机                         |
| --- | ---------------- | ------ | --------------------------------- | -------------------------------- |
| 1   | 签发临时 API Key | POST   | `/server-api/temp-api-key`        | App 启动或临时 Key 即将过期时    |
| 2   | 创建世界         | POST   | `/server-api/worlds`              | 三方服务端创建世界                |
| 3   | 查询构建状态     | GET    | `/server-api/worlds/build-status` | 创建世界后轮询                   |
| 4   | 查询世界详情     | GET    | `/server-api/worlds/detail`       | 确认单个世界状态和详情           |
| 5   | 获取 Travel ticket | POST   | `/server-api/travel-credential`   | 世界 `ready` 后换一次性 `ticket` |
| 6   | 查询世界列表     | GET    | `/server-api/worlds`              | 后台列表、调试或校验资源         |
| 7   | 查询 Travel 列表 | GET    | `/server-api/travels`             | 服务端侧查看 Travel 记录         |
| 8   | 查询 Travel 产物 | GET    | `/server-api/travels/artifacts`   | Travel `completed` 后查产物      |
| 9   | ScriptList 全量更新 | POST | `/server-api/travels/update-script` | 服务端侧更新 45 turn |
| 10  | 删除世界         | POST   | `/server-api/worlds/delete`       | 测试结束或业务清理资源           |

推荐主链路：

```text
POST /server-api/worlds
  -> GET /server-api/worlds/build-status 轮询到 ready
  -> POST /server-api/temp-api-key
  -> POST /server-api/travel-credential
  -> 把 token 和 ticket 一并返回给 App / Web 客户端
```

ticket 有效期为 30 分钟，由 `enter-travel` 一次性消费。临时 API Key 过期刷新时，无需重新换取 ticket。

`async=false` 会长时间占住 HTTP 请求，不建议作为服务端主路径。

服务端负责 World 创建与管理、凭证换取、Travel 历史与产物，以及 ScriptList 全量更新；客户端 SDK 负责进房、RTC / 播放和其余运行中控制。进房时，客户端用临时 Key 鉴权 `POST /openapi/v1/travels/enter-travel`，在 body 中传 ticket，并可为 Adventure 传 JSON integer `maxExperienceTimeSec`（`60` / `90` / `120`，省略默认 `60`；Directing 忽略）。随后读取 `output.data.noStreamAutoEndTimeoutSec`，轮询 `/openapi/v1/travels/status` 并按需上报 `clientStreamStatus` / `clientStreamStatusTimeMs`。若超时仍未见推流态（如 `rtcStatus=PUSHING`），调用 `POST /openapi/v1/travels/end` 并传 `failCode=TRAVEL_NO_STREAM_AUTO_END`。

最新 OpenAPI 不支持任何 GET 接口通过 Query 传 `userAgent`，World 相关 POST body 也不读取 `userAgent`；客户端标识请使用 HTTP `User-Agent`，Travel 控制类 POST 才可在 body 中显式传 `userAgent`。

## 三、接口详情

### 1. 签发临时 API Key

`POST /server-api/temp-api-key`

调用时机：需要给浏览器、移动 App 等不可信客户端调用 SDK 侧接口时。

请求 Query：

| 字段                | 类型    | 必填 | 说明                                           |
| ------------------- | ------- | ---- | ---------------------------------------------- |
| `expire_in_seconds` | integer | 否   | TTL 秒数，范围 `1..1800`；不传使用百炼默认 TTL |

请求 Body：

| 字段                | 类型    | 必填 | 说明                           |
| ------------------- | ------- | ---- | ------------------------------ |
| `expire_in_seconds` | integer | 否   | TTL 秒数，范围 `1..1800`       |
| `expireInSeconds`   | integer | 否   | `expire_in_seconds` 的驼峰别名 |

Query 和 Body 同时存在时，优先使用 Query。

正常响应不包 `output`：

```json
{
  "token": "st-****",
  "expires_at": 1744080369
}
```

本地参数错误：

```json
{
  "request_id": "随机 UUID",
  "output": {
    "code": "PARAM_INVALID",
    "message": "[happyoyster-sdk-demo-python] expire_in_seconds must be an integer between 1 and 1800",
    "data": {}
  }
}
```

### 2. 创建世界

`POST /server-api/worlds`

调用时机：三方服务端创建世界。推荐传 `async=true` 或省略 `async`，再轮询构建状态。

请求 Body：

| 字段              | 类型    | 必填 | 说明                                              |
| ----------------- | ------- | ---- | ------------------------------------------------- |
| `mode`            | integer | 是   | `1=adventure`，`2=directing`，`3=acting`                             |
| `async`           | boolean | 否   | 默认 `true`；`false` 同步等待，容易被网关超时打断 |
| `creationModel`   | string  | 否   | `simple`（默认）/ `scriptlist`；仅 `mode=2` 有效  |
| `prompt`          | string  | 条件 | Adventure / Acting first_frame 与 Directing simple 必填；ScriptList 不接受 |
| `eventStyle`      | string  | 否   | `normal` / `dramatic`                             |
| `refWorldId`      | string  | 否   | 参考模板世界加密 ID                               |
| `perspective`     | string  | 条件 | Adventure 必填：`first_person` / `third_person`      |
| `uploadMode`      | string  | 否   | Adventure / Acting：仅 `first_frame` |
| `aspectRatio` | string | 否 | 仅 Acting：`9:16`（默认）/ `16:9`，图片画幅须匹配 |
| `firstFrameImage` | object  | 条件   | Adventure / Acting 与 ScriptList 必填；Directing simple 可选：`{ url 或 base64, referenceType }` |
| `resolution`      | string  | 否 | Directing：`480p`（默认）/ `720p` |
| `layout`          | string  | 否   | Directing：`Stable` / `Fast`                          |
| `narrative`       | string  | 否   | Directing：`Calm` / `Dramatic` / `Normal`             |
| `inputImages`     | array   | 否   | 额外参考图：`[{ url 或 base64, referenceType }]`      |
| `scriptList`      | object  | 条件 | `creationModel=scriptlist` 时必填                 |

图片引用对象 `firstFrameImage`、`inputImages[]`、`scriptList.subjects[].refImage` 使用 HTTP(S) `url` 或 `base64` 二选一，不能同时提供；`base64` 可用裸字符串或 `data:image/xxx;base64,...`。`referenceType` 可选，默认 `default`。解码后的 JPG/JPEG/PNG/WebP 图片单张严格小于 30MB、至多 4096×4096 像素；Adventure / Directing 首帧宽高比须为 `1.5..2.0`，Acting 首帧须匹配 `aspectRatio`（默认 `9:16`，也可为 `16:9`）。Demo 会原样转发图片 data URI，包括其中声明的 MIME 类型。

`prompt` 为空或纯空白会被上游视为缺失。Adventure / Acting 的 first_frame 和 Directing simple 必须传非空 `prompt`；ScriptList 创建使用 `scriptList.synopsis`。

`creationModel=scriptlist` 时仅用于 Directing 世界，需传 `firstFrameImage`（含 `url` 或 `base64` 之一）和 `scriptList`，不接受 `prompt`、`layout`、`narrative`、`inputImages`、`perspective`、`uploadMode`、`sceneImage`、`roleImage`、`scenePrompt`、`rolePrompt` 等字段。创建和 `update-script` 都要求 `scriptList.acts` 恰好 45 条，turn 按数组顺序覆盖 1 到 45、连续且不可重复。

ScriptList 完整 schema：`synopsis`（创建必填，最长 2000）、`videoTitle`（128）、`scene` / `style` / `speed` / `language`（各 64）、`setting`（2000）、`soundtrack`（500）、`prologue`（1000）、`videoTags`（最多 20 个、每个 32）、`subjects`（最多 6 个）和 `acts`。`subjects[]` 支持 `label`（`[character_1]` 到 `[character_6]`，可省略自动补齐且不可重复）、`name`、`type`（`character` / `animal` / `creature` / `narrator`）、`refImage`、`gender`、`position`、`ethnicity`、`age`、`appearance`、`voice`；其中 name/gender/position/ethnicity/age 各最长 64，appearance 最长 500，voice 最长 200。`acts[]` 支持 `turn`、`content`、`cameraType`、`shotSize`、`cut`；content 必填且单条最长 2000、45 条合计最长 100000，主体引用必须匹配已定义 label。

`cameraType` 枚举：`Static` / `Tracking` / `Pan Left` / `Pan Right` / `Tilt Up` / `Tilt Down` / `Push-in` / `Pull-out` / `POV Forward` / `POV Look Down` / `POV Look Up` / `POV Turn Left` / `POV Turn Right`，默认 `Static`。`shotSize`：`Wide` / `Medium` / `Close-up`，默认 `Medium`。`cut`：`long-take` / `hard-cut` / `cut-in` / `cut-out` / `cutaway` / `cutback` / `camera movement transition`，默认 `long-take`。

上游对本接口的参数错误统一返回 HTTP `200` 的 OpenAPI 业务信封：`Content-Type` 非 `application/json`、畸形 JSON、字段或枚举非法、图片对象同时传 `url` 与 `base64`、base64 为空或无法解码、图片超出大小/像素/比例限制、URL 非合法 HTTP(S) 图片地址等均为 `output.code=400000`。本 demo 透传该上游响应。

响应 `output.data`：

| 字段               | 类型        | 说明                              |
| ------------------ | ----------- | --------------------------------- |
| `encryptedWorldId` | string      | 加密世界 ID，后续查询和换凭证使用 |
| `status`           | string      | `generating` / `ready` / `failed` |
| `firstFrame`       | string/null | 首帧图地址                        |

### 3. 查询构建状态

`GET /server-api/worlds/build-status`

调用时机：创建世界后轮询，直到 `ready` 或 `failed`。

请求 Query：

| 字段               | 类型   | 必填 | 说明                      |
| ------------------ | ------ | ---- | ------------------------- |
| `encryptedWorldId` | string | 是   | 创建世界返回的加密世界 ID |

响应 `output.data`：

| 字段               | 类型         | 说明                                       |
| ------------------ | ------------ | ------------------------------------------ |
| `encryptedWorldId` | string       | 加密世界 ID                                |
| `status`           | string       | `generating` / `ready` / `failed`          |
| `firstFrame`       | string/null  | 首帧图地址                                 |
| `name`             | string/null  | 世界名称，通常 `ready` 后返回              |
| `mode`             | integer/null | `1=adventure`，`2=directing`，`3=acting`，通常 `ready` 后返回 |

### 4. 查询世界详情

`GET /server-api/worlds/detail`

调用时机：确认单个世界状态和详情，建议世界 `ready` 后调用。

请求 Query：

| 字段               | 类型   | 必填 | 说明        |
| ------------------ | ------ | ---- | ----------- |
| `encryptedWorldId` | string | 是   | 加密世界 ID |

响应 `output.data`：

| 字段               | 类型        | 说明                        |
| ------------------ | ----------- | --------------------------- |
| `encryptedWorldId` | string      | 加密世界 ID                 |
| `name`             | string      | 世界名称                    |
| `status`           | string      | 世界状态                    |
| `mode`             | integer     | `1=adventure`，`2=directing`，`3=acting`       |
| `prompt`           | string/null | 创建时的主题描述            |
| `creationModel`    | string      | `simple` / `scriptlist`     |
| `previewUrl`       | string/null | 世界预览地址                |
| `eventStyle`       | string/null | `normal` / `dramatic`       |
| `perspective`      | string/null | `first_person` / `third_person` |
| `uploadMode`       | string/null | `first_frame`（历史记录可能为 `scenario_role`） |
| `aspectRatio` | string/null | Acting：`9:16` / `16:9` |
| `resolution`       | string/null | `480p` / `720p`             |
| `layout`           | string/null | 运镜风格                    |
| `narrative`        | string/null | 叙事风格                    |
| `refWorldId`       | string/null | 参考模板世界加密 ID         |
| `firstFrameImage` / `sceneImage` / `roleImage` | object/null | 图片 URL / referenceType 回显 |
| `inputImages`      | array       | 额外参考图回显              |
| `scriptList`       | object/null | ScriptList 世界返回完整结构 |
| `createdAt`        | string      | 创建时间                    |
| `updatedAt`        | string      | 更新时间                    |

ScriptList 世界的 `prompt` 固定为 `null`，创建时持久化的完整剧本通过 `scriptList` 返回；图片字段不回显 base64。

### 5. 获取 Travel ticket

`POST /server-api/travel-credential`

调用时机：世界 `ready` 后调用。世界非 `ready` 通常返回 `403002`。

请求 Body：

| 字段               | 类型   | 必填 | 说明                     |
| ------------------ | ------ | ---- | ------------------------ |
| `encryptedWorldId` | string | 是   | 加密世界 ID              |

响应 `output.data`：

| 字段               | 类型    | 说明                                                            |
| ------------------ | ------- | --------------------------------------------------------------- |
| `ticket`           | string  | 一次性 Travel ticket，返回给 App / Web 客户端用于 `enter-travel` |
| `expiresIn`        | integer | 有效期秒数：1800（30 分钟） |
| `encryptedWorldId` | string  | 加密世界 ID                                                     |

ticket 只能消费一次；客户端刷新临时 API Key 时无需重新换 ticket。开始体验后若在 `noStreamAutoEndTimeoutSec` 秒内未收到推流，应调用 `/openapi/v1/travels/end` 并传 `failCode=TRAVEL_NO_STREAM_AUTO_END`。

### 6. 查询世界列表

`GET /server-api/worlds`

调用时机：后台列表、调试或校验当前主 API Key 下的资源。

请求 Query：

| 字段       | 类型    | 必填 | 说明                              |
| ---------- | ------- | ---- | --------------------------------- |
| `page`     | integer | 否   | 默认 `1`                          |
| `pageSize` | integer | 否   | 默认 `20`，最大 `100`             |
| `status`   | string  | 否   | `ready` / `failed` / `generating` |
| `mode`     | integer | 条件 | 用于选择 App；未传 `X-Happy-Oyster-Mode` 时必填。`1=adventure`，`2=directing`，`3=acting` |

每次调用只查询一个模式；如需合并列表，请分别查询模式 1、2、3。

响应 `output.data`：

| 字段         | 类型   | 说明     |
| ------------ | ------ | -------- |
| `items`      | array  | 世界列表 |
| `pagination` | object | 分页信息 |

`items[]`：

| 字段               | 类型        | 说明                        |
| ------------------ | ----------- | --------------------------- |
| `encryptedWorldId` | string      | 加密世界 ID                 |
| `name`             | string      | 世界名称                    |
| `status`           | string      | 世界状态                    |
| `mode`             | integer     | `1=adventure`，`2=directing`，`3=acting`       |
| `perspective`      | string/null | `first_person` / `third_person` |
| `creationModel`    | string      | `simple` / `scriptlist` |
| `uploadMode`       | string/null | `first_frame`（历史记录可能为 `scenario_role`） |
| `aspectRatio` | string/null | Acting：`9:16` / `16:9` |
| `createdAt`        | string      | 创建时间                    |

`pagination`：

| 字段       | 类型    | 说明           |
| ---------- | ------- | -------------- |
| `page`     | integer | 当前页         |
| `pageSize` | integer | 每页数量       |
| `total`    | integer | 总数           |
| `hasMore`  | boolean | 是否还有下一页 |

### 7. 查询 Travel 列表

`GET /server-api/travels`

调用时机：已有客户端侧 Travel 后，服务端侧查看 Travel 记录。

请求 Query：

| 字段               | 类型    | 必填 | 说明                                                    |
| ------------------ | ------- | ---- | ------------------------------------------------------- |
| `page`             | integer | 否   | 当前页                                                  |
| `pageSize`         | integer | 否   | 每页数量                                                |
| `status`           | string  | 否   | `init` / `pending` / `running` / `completed` / `failed` |
| `encryptedWorldId` | string  | 否   | 按世界过滤                                              |

响应 `output.data`：

| 字段         | 类型   | 说明        |
| ------------ | ------ | ----------- |
| `items`      | array  | Travel 列表 |
| `pagination` | object | 分页信息    |

`items[]`：

| 字段                | 类型         | 说明                  |
| ------------------- | ------------ | --------------------- |
| `encryptedTravelId` | string       | 加密 Travel ID        |
| `status`            | string       | Travel 状态           |
| `mode`              | integer      | `1=adventure`，`2=directing`，`3=acting` |
| `encryptedWorldId`  | string       | 加密世界 ID           |
| `durationSec`       | integer/null | 时长秒数              |
| `createdAt`         | string       | 创建时间              |
| `endedAt`           | string/null  | 结束时间              |

### 8. 查询 Travel 产物

`GET /server-api/travels/artifacts`

调用时机：Travel `completed` 后查询产物。

请求 Query：

| 字段                | 类型   | 必填 | 说明           |
| ------------------- | ------ | ---- | -------------- |
| `encryptedTravelId` | string | 是   | 加密 Travel ID |

响应 `output.data`：

| 字段                | 类型   | 说明             |
| ------------------- | ------ | ---------------- |
| `encryptedTravelId` | string | 加密 Travel ID   |
| `composeStatus`     | string | 合成变体聚合状态 |
| `video`             | object | 固定四类视频产物 |

`video` 固定包含 `original`、`withWatermark`、`withInstruction`、`withInstructionAndWatermark` 四个字段。每个值结构：

| 字段          | 类型         | 说明                                   |
| ------------- | ------------ | -------------------------------------- |
| `url`         | string/null  | 视频地址；`processing` 时为 `null`     |
| `status`      | string       | `ready` / `processing` / `unavailable` |
| `resolution`  | string/null  | 原片命中 720P 时为 `720p`，否则 `null` |
| `durationSec` | integer/null | 当前实现通常为 `null`                  |

### 9. ScriptList 全量更新

`POST /server-api/travels/update-script`

调用时机：Directing ScriptList Travel 处于可更新状态时，全量替换当前 Travel 后续剧本 acts。

请求 Body：

| 字段                | 类型   | 必填 | 说明 |
| ------------------- | ------ | ---- | ---- |
| `encryptedTravelId` | string | 是   | 加密 Travel ID |
| `scriptList`        | object | 是   | 全量剧本容器；schema 与创建世界一致，当前更新只消费 `acts` |
| `scriptList.acts`   | array  | 是   | 必须恰好 45 条，turn 从 1 到 45 连续且不可重复 |
| `userAgent`         | string | 否   | Travel 控制类客户端标识；优先于 HTTP `User-Agent` |

`update-script` 仅全量替换 acts。请求 `scriptList` 中的 `subjects` 与 world 级字段（如 `synopsis`、`scene`、`style`）会被上游忽略，沿用创建世界时已落库的 ScriptList。acts 的长度、文本长度和 `cameraType` / `shotSize` / `cut` 枚举约束与上文完整 schema 相同。`creationModel=scriptlist` 的剧本世界不支持 `instruct` 增量文本指令，保持错误码 `403006 INSTRUCT_NOT_ALLOWED`。

响应 `output.data`：

| 字段                | 类型    | 说明 |
| ------------------- | ------- | ---- |
| `encryptedTravelId` | string  | 加密 Travel ID |
| `accepted`          | boolean | 是否已接受并进入处理队列 |
| `turnCount`         | integer | 本次更新的 turn 数，固定为 `45` |

常见业务错误：`400000`（acts 非 45 条、turn 重复/越界、枚举非法等）、`403004`（剧本内容安审拦截）、`404000`（Travel 不存在或无活跃 processor）、`409000`（Travel 状态不可更新）、`500000`（下游处理失败）。

### 10. 删除世界

`POST /server-api/worlds/delete`

调用时机：测试结束或业务清理资源。

请求 Body：

| 字段               | 类型   | 必填 | 说明        |
| ------------------ | ------ | ---- | ----------- |
| `encryptedWorldId` | string | 是   | 加密世界 ID |

响应 `output.data`：

| 字段               | 类型    | 说明         |
| ------------------ | ------- | ------------ |
| `encryptedWorldId` | string  | 加密世界 ID  |
| `deleted`          | boolean | 是否删除成功 |

## 四、常见错误

| 错误                            | 来源                 | 说明                               |
| ------------------------------- | -------------------- | ---------------------------------- |
| `BAILIAN_API_HOST is required` | Python demo         | 启动前没有配置百炼 API Host |
| `DASHSCOPE_API_KEY is required` | Python demo            | 启动前没有配置主 API Key           |
| `PARAM_INVALID`                 | Python demo / 开放接口 | 参数非法                           |
| `403002`                        | 开放接口             | 世界未 ready，不能换 Travel ticket   |
| `403003`                        | 开放接口             | 管理类或仅服务端接口未使用主 API Key |
| `ResponseTimeout`               | 网关                 | 下游响应超时，常见于 `async=false` |
| `UPSTREAM_ERROR`                | Python demo            | Python demo 请求上游失败或本地超时   |
