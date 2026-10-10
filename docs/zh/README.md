# Happy Oyster SDK Demo Python

[English](../../README.md) | **简体中文**

本仓库是面向客户端 SDK（App / Web）的 Python 三方服务端参考实现；生产环境可选择任意服务端语言。它示范三方服务端如何用主 `DASHSCOPE_API_KEY` 调用管理类和仅服务端接口，再把客户端完整进房所需的两项凭证都返回：临时 API Key（下文简称 `token`）和一次性 Travel `ticket`。

本仓库只暴露 `/server-api/*` 示例接口。服务端负责 World 创建与管理、凭证换取、Travel 历史与产物查询；客户端 SDK 使用临时 Key 和 ticket 通过 `/openapi/v1/*` 进房、建立 RTC / 播放并执行运行中控制。

## 环境要求

- Python `>= 3.9`
- 百炼 API Host：通过环境变量 `BAILIAN_API_HOST` 注入，填写百炼控制台 API Key 页展示的裸 host
- 百炼主 API Key：通过环境变量 `DASHSCOPE_API_KEY` 注入

API Host 必须与同一账号、同一地域的 API Key 配套使用，否则网关可能返回 `AccessDenied` 或 `401`；各地域 API Key 相互独立，不能跨地域使用。

当前工程只使用 Python 标准库，没有运行时依赖，直接启动即可。

## 快速开始

启动前设置百炼 API Host 和主 API Key。所有支持的环境变量见根目录 `.env.example`；demo 不会自动读取 `.env` 文件：

```bash
export BAILIAN_API_HOST='llm-<your-workspace-id>.cn-beijing.maas.aliyuncs.com'
export DASHSCOPE_API_KEY='sk-...'
python3 server.py
```

仅限本地联调或受控环境使用。生产接入时，必须在 `/server-api/*` 外层增加业务鉴权，不要把未加鉴权的 demo 直接暴露给公网或不可信客户端。

默认监听本机地址：

```text
http://127.0.0.1:3000
```

本地端口通过 `PORT` 切换：

```bash
PORT=3100 python3 server.py
```

手机真机自测时，监听所有网卡，并用电脑 Wi-Fi IP 访问：

```bash
HOST=0.0.0.0 python3 server.py
HOST=0.0.0.0 PORT=3100 python3 server.py
ipconfig getifaddr en0
```

假设电脑 Wi-Fi IP 为 `192.168.1.23`，手机访问：

```text
http://192.168.1.23:3000/server-api
http://192.168.1.23:3100/server-api
```

这是手机直接访问电脑上的 Python demo，不需要在手机 Wi-Fi 设置里配置代理。更完整的自测步骤见 [`test-checklist.md`](test-checklist.md)。

验证服务端接口：

```bash
curl 'http://127.0.0.1:3000/server-api/worlds?page=1&pageSize=10'
```

除 `POST /server-api/temp-api-key` 的正常响应外，业务响应都透传百炼 app 网关包装，读取 `output.code` 判断业务成败，读取 `output.data` 获取业务数据。

最短主链路：

```text
POST /server-api/worlds
  -> GET /server-api/worlds/build-status 轮询到 ready
  -> POST /server-api/temp-api-key
  -> POST /server-api/travel-credential
  -> 把 token 和 output.data.ticket 一并返回给 App / Web 客户端
```

ticket 有效期为 30 分钟且只能消费一次。临时 API Key 过期刷新时，无需重新换取 ticket。

## 调用边界

| 能力 | 负责方 / 调用方 | Python demo 是否暴露 |
| ---- | --------------- | -------------------- |
| 创建、列出、删除 World | 三方服务端 | 是，`/server-api/worlds*` |
| 查询构建状态、World 详情 | 三方服务端 | 是，`/server-api/worlds/build-status` 和 `/server-api/worlds/detail` |
| 签发 token、换取 Travel ticket | 三方服务端 | 是，`/server-api/temp-api-key` 和 `/server-api/travel-credential` |
| 查询 Travel 历史与产物 | 三方服务端 | 是，`/server-api/travels` 和 `/server-api/travels/artifacts` |
| ScriptList 全量更新 | 三方服务端 | 是，`/server-api/travels/update-script` |
| 进房、RTC、播放、运行中控制 | 客户端 SDK（App / Web） | 否；由 SDK 使用临时 Key 调用支持的 `/openapi/v1/*` 运行态接口 |

本 demo 按单用户、单主 API Key 场景演示，不包含登录、用户映射、租户隔离或资源归属校验。生产接入时必须补齐业务鉴权与授权。

## 环境变量

| 名称                   | 默认值                                           | 说明                                                                   |
| ---------------------- | ------------------------------------------------ | ---------------------------------------------------------------------- |
| `HOST`                 | `127.0.0.1`                                      | 本地监听地址                                                           |
| `PORT`                 | `3000`                                           | 本地监听端口                                                           |
| `BAILIAN_API_HOST`     | 无                                               | 必填，百炼 API Host（裸 host，不含 scheme 和 path）         |
| `DASHSCOPE_API_KEY`    | 无                                               | 必填，管理类和仅服务端接口以其作为 `Authorization: Bearer ...` |
| `REQUEST_TIMEOUT_MS`   | `130000`                                         | 上游请求超时时间，覆盖 `async=false` 最长 120 秒同步等待               |

本 demo 只走百炼 app 网关，和真实三方接入路径保持一致。

`BAILIAN_API_HOST` 可以从百炼控制台 API Key 页的“API Host”获取，例如 `llm-<your-workspace-id>.cn-beijing.maas.aliyuncs.com`。本 demo 按模式选择固定线上 App ID（`1=adventure`、`2=directing`、`3=acting`），拼接 `https://{BAILIAN_API_HOST}/api/v2/apps/{APP_ID}`。只支持正式版 App ID。创建/列举世界时传 `mode`；后续请求传 `X-Happy-Oyster-Mode: 1|2|3`。

管理类和仅服务端接口中的 `DASHSCOPE_API_KEY` 必须使用主 API Key。支持临时 Key 的客户端 SDK 运行态接口应使用临时 Key。如果使用临时 API Key 调用只允许主 API Key 的接口，服务端会返回 `403003 MAIN_API_KEY_REQUIRED`。

百炼 app 网关会把开放接口业务响应包装为 `{ request_id, output }`。三方服务端应读取 `output.code` / `output.data`，不要按裸 `{ code, data }` 解析响应。

## API 文档

| 文档                                                           | 用途                                                             |
| -------------------------------------------------------------- | ---------------------------------------------------------------- |
| [`server-api-reference.md`](server-api-reference.md) | 必读。本 demo `/server-api/*` 接口契约：接口清单、调用时机、入参、出参 |
| [`test-checklist.md`](test-checklist.md)             | 联调用。按推荐顺序逐项测试，并提供可复制 curl                    |
| [`openapi-client-api.md`](openapi-client-api.md)     | 参考。SDK 运行态和上游 `/openapi/v1/**` 契约，不是 Python demo 默认接入入口 |

## 工程结构

```text
server.py                                    # 兼容入口，只启动 src.main
src/main.py                                  # 进程入口：创建 server、listen、信号退出
src/app.py                                   # 组合根：错误边界、访问日志和路由
src/config.py                                # 环境变量读取、默认值、基本校验
src/routes.py                                # /server-api/*、404、405 分发
src/lib/http_utils.py                        # 文本 / JSON 响应工具
src/lib/request_body.py                      # 原始请求 body 读取
src/lib/upstream_client.py                   # 通用上游请求、超时、错误封装
src/modules/providers/bailian_app_provider.py # 百炼 app 网关 provider
src/modules/providers/header_utils.py        # 可透传 header 过滤
src/modules/proxy/proxy_controller.py        # 代理 controller
src/modules/tokens/token_controller.py       # 临时 API Key 签发 controller
src/modules/tokens/token_service.py          # 临时 API Key 签发 service
```

## 测试

```bash
python3 -m unittest discover -s test -t .
```

测试使用 Python 内置 `unittest`，不引入额外测试框架。
