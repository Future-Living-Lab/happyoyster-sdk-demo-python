# Happy Oyster Python Demo 接口测试清单


本文档用于验证 `happyoyster-sdk-demo-python` 暴露的 `/server-api/*` 接口。主链路为“创建世界 -> 等待构建 -> 签发临时 API Key（下文简称 `token`）并换取一次性 Travel ticket -> 查询服务端记录 -> 清理资源”。

接口清单、入参和出参的唯一契约文档见 [`server-api-reference.md`](server-api-reference.md)。本文档只记录建议测试顺序、可复制 curl 和每一步需要观察的关键字段。

这些 curl 面向本地联调环境。生产接入时，三方服务端必须在 `/server-api/*` 外层增加自己的业务登录、授权、租户隔离和资源归属校验。

## 一、测试前准备

启动前必须配置百炼 API Host 和主 API Key：

```bash
export BAILIAN_API_HOST='llm-<your-workspace-id>.cn-beijing.maas.aliyuncs.com'
export DASHSCOPE_API_KEY='sk-...'
python3 server.py
```

`BAILIAN_API_HOST` 从百炼控制台 API Key 页的“API Host”获取，例如 `llm-<your-workspace-id>.cn-beijing.maas.aliyuncs.com`。本 demo 内部会补全固定网关路径 `https://{BAILIAN_API_HOST}/api/v2/apps/happyoyster-1.0`。

API Host 必须与同一账号、同一地域的 API Key 配套使用，否则网关可能返回 `AccessDenied` 或 `401`；各地域 API Key 相互独立，不能跨地域使用。

要求 Python `>= 3.9`。当前工程没有运行时依赖，不需要额外安装 Web 框架。

### 本地地址与端口

默认监听本机地址：

```text
http://127.0.0.1:3000
```

如需切换端口，通过 `PORT` 环境变量启动：

```bash
PORT=3100 python3 server.py
```

对应访问地址改为：

```text
http://127.0.0.1:3100
```

手机真机自测时，改为监听所有网卡：

```bash
HOST=0.0.0.0 python3 server.py
```

若同时切换端口，把 `HOST` 和 `PORT` 一起传入：

```bash
HOST=0.0.0.0 PORT=3100 python3 server.py
```

查询电脑 Wi-Fi IP：

```bash
ipconfig getifaddr en0
```

假设输出为 `192.168.1.23`，手机和电脑连接同一个 Wi-Fi 后，手机访问对应端口：

```text
http://192.168.1.23:3000/server-api
http://192.168.1.23:3100/server-api
```

这是手机直接访问电脑 Python demo，不需要在手机 Wi-Fi 里配置代理。只有需要把 App 原本访问的线上域名转发到电脑抓包或本地服务时，才需要配置代理工具。若无法访问，检查 macOS 防火墙、同一局域网和访客网络隔离。

通用响应约定：

- 除 `POST /server-api/temp-api-key` 外，业务响应在 `output` 内。
- 成功判断：`output.code == 0`。
- 业务数据：读取 `output.data`。
- 若返回顶层字符串 `code`，按代理或网关层错误处理。
- `mode` 使用数值：`1=adventure`，`2=directing`，不要传字符串。
- 不要在 GET Query 或 World POST body 中传 `userAgent`；如需标识客户端，使用 HTTP `User-Agent` Header。
- 当前 demo 按单用户 / 单主 API Key 场景演示，不做业务用户隔离。
- 百炼网关注入 workspace 时，World / Travel 按 `uid + workspace` 隔离；跨 workspace 的 World 断言 `403001`，Travel 断言 `404000`。不要自行构造 `x-dashscope-*` / `X-Ho-*` Header。

测试时建议记录这些变量：

```bash
WORLD_ID='创建世界后填入 encryptedWorldId'
TRAVEL_TICKET='获取 Travel ticket 后填入 ticket'
TRAVEL_ID='已有客户端侧 Travel 后填入 encryptedTravelId'
```

## 二、临时 API Key 测试

### 1. 签发临时 API Key

调用时机：App / Web 客户端需要调用 SDK 侧接口时。客户端完整进房同时需要 token 和 Travel ticket，两者不是二选一。

接口：

```text
POST /server-api/temp-api-key
```

Query 示例：

```bash
curl -sS -X POST 'http://127.0.0.1:3000/server-api/temp-api-key?expire_in_seconds=1800'
```

Body 示例：

```bash
curl -sS -X POST 'http://127.0.0.1:3000/server-api/temp-api-key' \
  -H 'Content-Type: application/json' \
  -d '{"expire_in_seconds":1800}'
```

入参：

- `expire_in_seconds`：可选，TTL 秒数，范围 `1..1800`。
- `expireInSeconds`：可选，JSON body 中可用的驼峰别名。

正常出参不包 `output`：

```json
{
  "token": "st-****",
  "expires_at": 1744080369
}
```

后续刷新 token 时，无需重新换取 Travel ticket。

本地参数错误出参：

```json
{
  "success": false,
  "errorCode": "PARAM_INVALID",
  "message": "expire_in_seconds must be an integer between 1 and 1800"
}
```

建议额外测两个错误用例：

```bash
curl -sS -X POST 'http://127.0.0.1:3000/server-api/temp-api-key?expire_in_seconds=0'
curl -sS -X POST 'http://127.0.0.1:3000/server-api/temp-api-key' \
  -H 'Content-Type: application/json' \
  -d '{bad json'
```

## 三、主链路测试

### 2. 创建世界

调用时机：测试起点。建议服务端主链路使用 `async=true` 或省略 `async`。

接口：

```text
POST /server-api/worlds
```

Directing 示例：

```bash
curl -sS -X POST 'http://127.0.0.1:3000/server-api/worlds' \
  -H 'Content-Type: application/json' \
  -d '{
    "mode": 2,
    "async": true,
    "prompt": "一座漂浮在云端的古城",
    "resolution": "720p",
    "layout": "Stable",
    "narrative": "Dramatic"
  }'
```

Adventure first_frame 示例：

`https://cdn.example.com/*.jpg` 是占位资源地址，直接复制会请求失败；联调时请替换为真实、可公网访问且图片格式正确的素材 URL。

```bash
curl -sS -X POST 'http://127.0.0.1:3000/server-api/worlds' \
  -H 'Content-Type: application/json' \
  -d '{
    "mode": 1,
    "async": true,
    "prompt": "一座漂浮在云端的古城",
    "perspective": "first_person",
    "uploadMode": "first_frame",
    "firstFrameImage": {
      "url": "https://cdn.example.com/a.jpg",
      "referenceType": "default"
    }
  }'
```

Adventure first_frame base64 示例：

```bash
IMAGE_BASE64="$(base64 -i your-image.png | tr -d '\n')"
curl -sS -X POST 'http://127.0.0.1:3000/server-api/worlds' \
  -H 'Content-Type: application/json' \
  -d "{
    \"mode\": 1,
    \"async\": true,
    \"prompt\": \"雨夜霓虹街道\",
    \"perspective\": \"first_person\",
    \"uploadMode\": \"first_frame\",
    \"firstFrameImage\": {
      \"base64\": \"$IMAGE_BASE64\"
    }
  }"
```

Adventure scenario_role 示例（不传顶层 `prompt`）：

```bash
curl -sS -X POST 'http://127.0.0.1:3000/server-api/worlds' \
  -H 'Content-Type: application/json' \
  -d '{
    "mode": 1,
    "async": true,
    "perspective": "first_person",
    "uploadMode": "scenario_role",
    "scenePrompt": "一座漂浮在云端的古城",
    "rolePrompt": "一只戴着斗篷的牡蛎向导",
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

主要入参：

- `mode`：必填，`1=adventure`，`2=directing`。
- `async`：可选，默认 `true`；`false` 会同步等待，最长可能到 120 秒。
- `prompt`：first_frame / Directing simple 必填；scenario_role 不需要顶层 `prompt`，但至少填写 `scenePrompt` / `rolePrompt` 之一，或同时提供 `sceneImage` 与 `roleImage`（各含 `url` 或 `base64` 之一）。
- `eventStyle`：可选，`normal` / `dramatic`。
- `refWorldId`：可选，参考模板世界加密 ID。
- Adventure：`perspective` 必填；`uploadMode` 可选，默认 `first_frame`；`firstFrameImage`、`sceneImage`、`roleImage`、`scenePrompt`、`rolePrompt` 按上传模式条件传入。
- Directing：`resolution` 必填；`layout`、`narrative`、`firstFrameImage`、`inputImages` 可选。
- 图片对象：`firstFrameImage`、`sceneImage`、`roleImage`、`inputImages[]`、`scriptList.subjects[].refImage` 均支持 `url` 或 `base64` 二选一；裸 base64 和 `data:image/png;base64,...` data URI 都必须成功。JPG/JPEG/PNG/WebP 单张严格小于 30MB，最大 4096×4096 像素；首帧宽高比必须在闭区间 `1.5..2.0`，其它参考图不要求该比例。
- ScriptList 创建和 `update-script` 都要求恰好 45 条 acts，turn 从 1 到 45 按顺序连续且不可重复。逐项断言完整 schema：创建必填 `synopsis`；subjects 最多 6 个且 label/type/各文本长度合法；content 单条最多 2000、合计最多 100000；`cameraType`、`shotSize`、`cut` 只能使用文档列出的枚举。

创建接口必须补测参数错误统一响应：非 `application/json` Content-Type、畸形 JSON、非法枚举、图片超限或格式/比例错误都应为 HTTP `200`，且业务信封 `output.code=400000`，不能断言 HTTP `400` / `415`。

成功后重点看：

- `output.data.encryptedWorldId`：保存为 `WORLD_ID`。
- `output.data.status`：通常为 `generating`，也可能直接为 `ready`。
- `output.data.firstFrame`：首帧信息。

下一步：用 `WORLD_ID` 轮询构建状态。

### 3. 轮询构建状态

调用时机：创建世界后循环调用，直到 `status` 为 `ready` 或 `failed`。

接口：

```text
GET /server-api/worlds/build-status
```

示例：

```bash
curl -sS "http://127.0.0.1:3000/server-api/worlds/build-status?encryptedWorldId=$WORLD_ID"
```

入参 Query：

- `encryptedWorldId`：必填，创建世界返回的加密世界 ID。

成功后重点看：

- `output.data.status`：`generating` / `ready` / `failed`。
- `output.data.name`：仅 `ready` 后通常有值。
- `output.data.mode`：仅 `ready` 后通常有值。
- `output.data.firstFrame`：首帧信息。

下一步：`ready` 后查世界详情，或直接获取 Travel ticket。

### 4. 查询世界详情

调用时机：世界创建后确认详情，建议在 `ready` 后测。

接口：

```text
GET /server-api/worlds/detail
```

示例：

```bash
curl -sS "http://127.0.0.1:3000/server-api/worlds/detail?encryptedWorldId=$WORLD_ID"
```

入参 Query：

- `encryptedWorldId`：必填。

成功后重点看：

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
- `output.data.scriptList`：ScriptList 世界必须返回创建时持久化的完整结构，且 `prompt=null`
- `output.data.createdAt`
- `output.data.updatedAt`

下一步：获取 Travel ticket。

### 5. 获取 Travel ticket

调用时机：世界 `ready` 后调用。世界未 ready 会返回 `403002`。

推荐接口：

```text
POST /server-api/travel-credential
```

示例：

```bash
curl -sS -X POST 'http://127.0.0.1:3000/server-api/travel-credential' \
  -H 'Content-Type: application/json' \
  -d "{\"encryptedWorldId\":\"$WORLD_ID\"}"
```

入参 Body：

- `encryptedWorldId`：必填。

成功后重点看：

- `output.data.ticket`：保存为 `TRAVEL_TICKET`，与 token 一并交给 App / Web 客户端。
- `output.data.expiresIn`：1800 秒（30 分钟）；ticket 只能消费一次。
- `output.data.encryptedWorldId`

下一步：把 token 和 ticket 一并返回给客户端。客户端用 token 鉴权 `POST /openapi/v1/travels/enter-travel`，并在 body 中传 ticket；Adventure 可额外传 JSON integer `maxExperienceTimeSec=60/90/120`，省略默认 60，Directing 忽略。断言响应 `maxExperienceTimeSec` 在 Adventure 为实际生效值、Directing 为 `null`，非法类型或档位返回 `400000`。随后客户端负责 RTC / 播放和运行中控制；服务端继续负责 World 管理、凭证换取、Travel 历史与产物。刷新 token 无需新 ticket。

客户端回溯联调时还应断言：服务端按每个 act 约 4 秒将 `rewindToSec` 四舍五入到 act 边界，响应 `actualRewindToSec` 为实际落点，`resumedAtSec` 与其相等。

### 5.1 可选：ScriptList 全量更新（服务端侧）

调用时机：客户端已经用 ScriptList 世界进入 Directing Travel，且需要运行中全量替换 45 turn acts。

接口：

```text
POST /server-api/travels/update-script
```

示例：

```bash
curl -sS -X POST 'http://127.0.0.1:3000/server-api/travels/update-script' \
  -H 'Content-Type: application/json' \
  -d @scriptlist-update.json
```

生成一个恰好包含 45 条 acts 的有效示例：

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

`scriptList.acts` 必须恰好 45 条，并按数组顺序包含从 1 到 45 的每个连续 turn。补测 44/46 条、重复或乱序 turn、空 content、单条/合计超长以及非法 `cameraType` / `shotSize` / `cut`，均断言 `400000`。上游只消费 acts，`subjects` 与 `synopsis` 等 world 级字段会沿用创建世界时的数据；ScriptList 调 `instruct` 仍断言 `403006 INSTRUCT_NOT_ALLOWED`。

### 6. 查询世界列表

调用时机：验证当前主 API Key 下的世界记录，或按状态 / 模式过滤。

接口：

```text
GET /server-api/worlds
```

示例：

```bash
curl -sS 'http://127.0.0.1:3000/server-api/worlds?page=1&pageSize=20'
curl -sS 'http://127.0.0.1:3000/server-api/worlds?page=1&pageSize=20&status=ready&mode=2'
```

入参 Query：

- `page`：可选，默认 `1`。
- `pageSize`：可选，默认 `20`，最大 `100`。
- `status`：可选，`ready` / `failed` / `generating`。
- `mode`：可选，`1=adventure`，`2=directing`。

成功后重点看：

- `output.data.items[]`
- `output.data.pagination.page`
- `output.data.pagination.pageSize`
- `output.data.pagination.total`
- `output.data.pagination.hasMore`

`items[]` 主要字段：

- `encryptedWorldId`
- `name`
- `status`
- `mode`
- `perspective`
- `creationModel`
- `uploadMode`
- `createdAt`

### 7. 查询 Travel 列表

调用时机：已有客户端侧 Travel 后，服务端侧查看 Travel 记录。

接口：

```text
GET /server-api/travels
```

示例：

```bash
curl -sS 'http://127.0.0.1:3000/server-api/travels?page=1&pageSize=20'
curl -sS "http://127.0.0.1:3000/server-api/travels?page=1&pageSize=20&encryptedWorldId=$WORLD_ID"
```

入参 Query：

- `page`：可选。
- `pageSize`：可选。
- `status`：可选，例如 `running` / `completed` / `failed`。
- `encryptedWorldId`：可选，用于查某个世界下的 Travel。

成功后重点看：

- `output.data.items[]`
- `output.data.pagination`

`items[]` 主要字段：

- `encryptedTravelId`：保存为 `TRAVEL_ID`，用于查产物。
- `status`
- `mode`
- `encryptedWorldId`
- `durationSec`
- `createdAt`
- `endedAt`

下一步：Travel 完成后查产物。

### 8. 查询 Travel 产物

调用时机：Travel 状态为 `completed` 后调用。

接口：

```text
GET /server-api/travels/artifacts
```

示例：

```bash
curl -sS "http://127.0.0.1:3000/server-api/travels/artifacts?encryptedTravelId=$TRAVEL_ID"
```

入参 Query：

- `encryptedTravelId`：必填。

成功后重点看：

- `output.data.encryptedTravelId`
- `output.data.composeStatus`
- `output.data.video`

`video` 固定包含 `original`、`withWatermark`、`withInstruction`、`withInstructionAndWatermark` 四类变体。每个值结构：

```json
{
  "url": "https://example.com/video.mp4",
  "status": "ready",
  "resolution": "720p",
  "durationSec": null
}
```

### 9. 删除世界

调用时机：测试结束清理资源。

接口：

```text
POST /server-api/worlds/delete
```

示例：

```bash
curl -sS -X POST 'http://127.0.0.1:3000/server-api/worlds/delete' \
  -H 'Content-Type: application/json' \
  -d "{\"encryptedWorldId\":\"$WORLD_ID\"}"
```

入参 Body：

- `encryptedWorldId`：必填。

成功后重点看：

- `output.data.encryptedWorldId`
- `output.data.deleted`

## 四、常见失败点

- `BAILIAN_API_HOST is required`：启动前没有配置百炼 API Host。
- `DASHSCOPE_API_KEY is required`：启动前没有配置主 API Key。
- `403002 WORLD_NOT_READY`：世界还没 ready 就获取 Travel ticket。
- `403003 MAIN_API_KEY_REQUIRED`：用临时 API Key 调了管理类或仅服务端接口；支持临时 Key 的 SDK 运行态接口应使用临时 Key。
- `TRAVEL_NO_STREAM_AUTO_END`：客户端开始体验后超过 `noStreamAutoEndTimeoutSec` 仍未收到推流，应结束并标记失败。
- `400000 PARAM_INVALID`：字段名、类型或必填项不符合接口要求。
- 顶层字符串 `code`：按代理或网关层错误处理，不要当业务 `output.code`。
