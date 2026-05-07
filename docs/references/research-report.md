# research-report.md

## 元信息

- 项目：网络故障工单智能分类工具
- 阶段：Init / 阶段 1 技术调研
- 日期：2026-05-06
- 路线：复杂路线
- 用户已确认：
  - API 框架：FastAPI
  - LLM 提供方：DeepSeek API
  - 部署：云服务器
  - CSV 字段、分类标签、置信度规则、数据规模、工程规范：由架构侧推荐
  - 样例数据：暂无，v1 使用合成样例与规则单测覆盖

---

## 1. 调研范围

本次调研只覆盖 v1 可落地实现，不进入自训练模型或论文级算法路线。

### 重点问题

1. DeepSeek API 是否适合做结构化 JSON 分类输出。
2. 结构化输出失败、低置信度、多类别冲突时如何兜底。
3. FastAPI 如何承载单条分类、CSV 上传、批处理任务、结果下载。
4. SQLite 是否适合作为 v1 历史记录与复核状态存储。
5. Pandas CSV 批处理规模边界如何设置。
6. 执行端应采用怎样的工程栈、目录结构和测试策略。

---

## 2. 外部资料结论

### 2.1 DeepSeek API 结构化输出

DeepSeek 官方文档提供 JSON Output 能力，用于让模型输出有效 JSON 字符串。启用方式包括：

- 设置 `response_format={"type": "json_object"}`。
- 在 system 或 user prompt 中包含 `json` 字样。
- 在 prompt 中提供目标 JSON 示例。
- 合理设置 `max_tokens`，避免 JSON 被截断。
- 需要处理偶发空内容返回。

这说明 DeepSeek API 可以作为 v1 的主分类模型，但不能直接把“模型返回有效 JSON”视为“业务结果有效”。必须增加 Pydantic schema 校验、枚举约束、置信度范围校验、关键字段缺失校验、重试与兜底逻辑。

DeepSeek 也提供 Function Calling，并有 strict mode beta，可让模型输出符合函数 JSON Schema 的 tool call。由于 strict mode 仍带 beta 标记，v1 不建议把它作为主链路；可以保留为后续增强方案。

### 2.2 FastAPI 文件上传与异步任务

FastAPI 官方文档建议使用 `UploadFile` 接收上传文件。`UploadFile` 使用 spooled file，小文件在内存中，超过阈值后落盘，适合较大文件上传，不会像 `bytes` 参数那样直接把文件全部读入内存。

FastAPI `BackgroundTasks` 适合在返回 HTTP 202 后继续执行较轻量后台任务，例如文件处理。官方也明确提示：如果是重计算、跨进程或多服务器任务，应改用 Celery 等任务队列。v1 推荐先用 FastAPI BackgroundTasks；当单次批量超过 50k 行、并发批处理较多或需要多实例部署时，再升级 Celery/RQ + Redis。

### 2.3 Pandas CSV 批处理

Pandas `read_csv` 支持 `chunksize` / `iterator` 以分块读取 CSV。v1 不应默认把上传文件整体读入单个 DataFrame。建议：

- 默认 chunk size：500 行。
- 单批推荐上限：10,000 行。
- 单批硬上限：50,000 行或 20 MB，先到为准。
- 每行分类结果即时写入 SQLite，并追加到导出 CSV 临时文件，降低内存峰值。
- 对字段缺失、空描述、编码错误、重复 ticket_id 做显式错误记录。

### 2.4 SQLite 作为 v1 数据库

FastAPI 官方 SQL 数据库教程说明 FastAPI 不绑定特定数据库，SQLModel 基于 SQLAlchemy，可支持 SQLite、PostgreSQL、MySQL 等数据库。SQLModel 同时结合 SQLAlchemy 与 Pydantic，适合本项目 v1 的 API schema 与数据库模型统一表达。

SQLite 适合 v1 单云服务器、低到中等并发、主要写入分类结果和查询历史记录的场景。但必须按生产习惯设置：

- `PRAGMA journal_mode=WAL`
- `PRAGMA foreign_keys=ON`
- `PRAGMA busy_timeout=5000`
- `PRAGMA synchronous=NORMAL`
- 对 `ticket_id`、`batch_id`、`created_at`、`review_required` 建索引

当出现多实例部署、高并发写入、多人复核工作流或数据量超过百万级时，数据库应迁移到 PostgreSQL。v1 目录与 repository 层要避免把 SQLite 细节写死，以便后续迁移。

---

## 3. 方案对比

| 方案 | 描述 | 优点 | 缺点 | 结论 |
|---|---|---|---|---|
| A. DeepSeek JSON Output + Pydantic 校验 + 规则兜底 | 用 DeepSeek 输出 JSON，后端用 Pydantic 强校验，失败则重试或规则兜底 | 落地快、成本低、工程可控、适合无训练数据起步 | 准确率依赖 prompt；需要处理空响应、格式漂移、低置信度 | **v1 首选** |
| B. DeepSeek strict Function Calling | 使用 DeepSeek beta strict mode 输出符合 JSON Schema 的 tool call | 结构化约束更强 | beta 风险；功能边界和兼容性需持续验证 | v1 备选，不作为主链路 |
| C. 传统机器学习分类器 | TF-IDF / embedding / 微调模型做分类 | 可控、可评估、低延迟 | 需要标注数据；冷启动不现实 | v2 方向 |
| D. 本地大模型 | 私有部署模型分类 | 数据不出内网、可控性强 | 运维成本高、需要 GPU/量化部署、准确率需验证 | 当前不推荐 |
| E. 纯规则分类 | 关键词、正则、字典直接分类 | 稳定、可解释、无 API 成本 | 覆盖率和鲁棒性差，难处理自然语言描述 | 只作为兜底层 |

---

## 4. 推荐技术路线

### 4.1 总体推荐

采用 **FastAPI + DeepSeek API + Pydantic v2 + Pandas + SQLModel/SQLite + 规则兜底**。

核心原则：

1. LLM 负责语义理解，不负责最终业务可信度。
2. Pydantic 负责结构化校验。
3. 规则引擎负责兜底、冲突检测和人工复核触发。
4. SQLite 保存原始输入、模型原始输出、标准化输出、处理耗时、错误信息和复核状态。
5. CSV 批处理必须可恢复、可追踪、可下载，不做黑盒批量调用。

### 4.2 推荐工程栈

| 类别 | 推荐 |
|---|---|
| Python | 3.12 |
| 包管理 | `uv` |
| Web 框架 | FastAPI |
| ASGI Server | Uvicorn |
| 数据模型 | Pydantic v2 |
| ORM | SQLModel |
| 数据库 | SQLite v1，预留 PostgreSQL 迁移 |
| CSV | Pandas |
| LLM Client | OpenAI Python SDK 指向 DeepSeek `base_url`，或封装 `httpx` |
| 配置 | `pydantic-settings` + `.env` |
| 测试 | pytest + pytest-cov |
| 质量 | ruff + mypy |
| 部署 | Docker + docker compose + systemd/nginx 可选 |
| 日志 | structlog 或标准 logging JSON formatter |

---

## 5. v1 分类标签体系

v1 采用“单主类 + 多候选类”模型。业务结果必须有一个 `primary_category`，同时允许 `secondary_categories` 用于冲突识别。

### 5.1 枚举

| 枚举值 | 中文名 | 典型症状 |
|---|---|---|
| `COVERAGE_ISSUE` | 覆盖问题 | 某区域无覆盖、室内无信号、基站覆盖盲区 |
| `DROPPED_CONNECTION` | 掉线/频繁断开 | 频繁掉线、连接中断、会话断开 |
| `HIGH_LATENCY` | 时延高 | ping 高、游戏卡顿、视频会议延迟 |
| `DNS_FAILURE` | DNS 故障 | 域名无法解析、能 ping IP 不能访问域名 |
| `AUTH_FAILURE` | 认证失败 | PPPoE 失败、账号密码错误、Radius 拒绝 |
| `DEVICE_FAILURE` | 设备故障 | 光猫/路由器/交换机异常、端口故障、硬件告警 |
| `WEAK_SIGNAL` | 弱信号 | Wi-Fi 弱、RSSI 低、信号格少、SINR 差 |
| `CONFIG_ERROR` | 配置异常 | VLAN、ACL、路由、NAT、APN、DHCP 配置错误 |
| `PACKET_LOSS` | 丢包 | ping 丢包、链路抖动、间歇性不可达 |
| `BANDWIDTH_DEGRADATION` | 带宽下降 | 速率不达标、下载慢、吞吐低 |
| `SERVICE_OUTAGE` | 服务中断 | 大面积故障、区域性不可用、核心网/出口异常 |
| `CUSTOMER_PREMISES_ISSUE` | 用户侧环境问题 | 终端、网线、电源、用户路由配置问题 |
| `UNKNOWN` | 未知/信息不足 | 描述过短、无明确症状、无法判断 |

### 5.2 输出 JSON Schema 业务字段

```json
{
  "primary_category": "HIGH_LATENCY",
  "secondary_categories": ["PACKET_LOSS"],
  "confidence": 0.86,
  "category_scores": {
    "HIGH_LATENCY": 0.86,
    "PACKET_LOSS": 0.73
  },
  "key_symptoms": ["ping 延迟高", "视频会议卡顿"],
  "summary": "用户反馈网络时延高并影响实时音视频使用。",
  "troubleshooting_steps": [
    "确认故障发生位置、时间段和接入方式。",
    "执行 ping/traceroute 检查时延与路径变化。",
    "检查链路利用率、无线信号质量和设备告警。"
  ],
  "review_required": false,
  "review_reasons": []
}
```

---

## 6. 置信度与人工复核规则

### 6.1 推荐阈值

| 场景 | 规则 | 动作 |
|---|---|---|
| 高可信 | `confidence >= 0.80` 且无 schema/rule 冲突 | 自动通过 |
| 中可信 | `0.60 <= confidence < 0.80` | 标记 `review_required=true`，但保留建议分类 |
| 低可信 | `confidence < 0.60` | 标记 `UNKNOWN` 或保留模型分类，必须人工复核 |
| 多类别冲突 | `top1_score - top2_score < 0.08` | 人工复核 |
| 规则冲突 | 规则强命中类别与 LLM 主类不同 | 人工复核 |
| 信息不足 | 描述长度 `< 8` 个中文字符或 `< 4` 个英文词 | 人工复核 |
| JSON 失败 | JSON parse/Pydantic 校验失败后重试仍失败 | 规则兜底 + 人工复核 |
| API 失败 | DeepSeek 超时、限流、空响应 | 规则兜底 + 记录错误 |

### 6.2 重试策略

- LLM JSON parse 失败：最多重试 1 次，使用“修复为合法 JSON”的降级 prompt。
- DeepSeek 空内容：最多重试 1 次。
- API 超时/429/5xx：指数退避重试 2 次。
- 重试后仍失败：进入规则兜底，`review_required=true`。

---

## 7. CSV 字段设计

### 7.1 输入字段

v1 接受灵活字段映射，但内部标准化为：

| 内部字段 | 必填 | 说明 | 常见别名 |
|---|---:|---|---|
| `ticket_id` | 否 | 外部工单号；缺失时系统生成 | `id`, `case_id`, `order_id`, `工单号` |
| `description` | 是 | 故障描述文本 | `desc`, `content`, `fault_description`, `故障描述`, `问题描述` |
| `created_at` | 否 | 工单创建时间 | `time`, `created_time`, `创建时间` |
| `source` | 否 | 来源系统 | `channel`, `system`, `来源` |
| `customer_region` | 否 | 区域/站点 | `region`, `area`, `site`, `区域` |
| `priority` | 否 | 原始优先级 | `severity`, `level`, `优先级` |

如果无法识别 `description`，CSV 导入直接失败并返回字段映射错误。

### 7.2 输出字段

| 输出字段 | 说明 |
|---|---|
| `ticket_id` | 原始或系统生成工单 ID |
| `primary_category` | 主分类 |
| `secondary_categories` | JSON 字符串 |
| `confidence` | 0–1 |
| `review_required` | 是否需人工复核 |
| `review_reasons` | JSON 字符串 |
| `key_symptoms` | JSON 字符串 |
| `summary` | 工单摘要 |
| `troubleshooting_steps` | JSON 字符串 |
| `llm_model` | 实际使用模型 |
| `llm_latency_ms` | LLM 调用耗时 |
| `processed_at` | 处理时间 |
| `error` | 单行错误信息，无错误为空 |

---

## 8. 数据规模建议

### 8.1 v1 默认边界

| 指标 | 推荐值 |
|---|---:|
| 单条描述最大长度 | 4,000 字符 |
| 单次 CSV 推荐行数 | 10,000 行 |
| 单次 CSV 硬上限 | 50,000 行 |
| 上传文件硬上限 | 20 MB |
| Pandas chunk size | 500 行 |
| 单批并发 LLM 请求 | 3–5 |
| API 单次超时 | 30 秒 |
| 批处理任务保留时间 | 30 天 |
| SQLite 数据量预期 | 10 万–100 万条以内 |

### 8.2 迁移触发条件

满足任一条件时，进入 Iter 重新规划数据库或任务队列：

1. 历史结果超过 100 万条且查询明显变慢。
2. 批处理任务并发超过 3 个。
3. 需要多台 API 实例同时写库。
4. 人工复核多人协作、权限与审计要求增强。
5. 需要定时重跑 Prompt 或批量评估准确率。

---

## 9. 关键风险与应对

| 风险 | 影响 | v1 应对 |
|---|---|---|
| DeepSeek JSON 空响应或格式漂移 | 分类失败 | JSON mode + 示例 + Pydantic 校验 + 1 次重试 + 规则兜底 |
| 模型自信但分类错 | 误分派工单 | 规则冲突检测 + 人工复核阈值 + 保存原始输出 |
| 无真实样例 | Prompt 与规则初始准确率不可验证 | 内置合成样例测试集，后续由 SQLite 历史复核数据迭代 |
| CSV 字段混乱 | 批处理失败 | 字段别名映射 + 导入前 preview + 明确错误 |
| SQLite 写锁 | 批处理失败或接口慢 | WAL + busy_timeout + 单写入通道 + 批量提交 |
| LLM 成本与限流 | 批处理慢 | 并发上限、缓存相同描述 hash、失败重试限额 |
| 上传文件安全 | 路径穿越/超大文件/恶意内容 | 禁止使用原始文件名落盘；校验扩展名、MIME、大小；临时目录隔离 |
| 故障描述包含敏感信息 | 合规风险 | 日志禁止记录完整描述；数据库按需脱敏；错误日志只记录 ticket_id |

---

## 10. 蒸馏给执行端的技术要点

1. `ClassificationService.classify_text()` 是核心入口：输入标准化描述，输出 `ClassificationResult`。
2. LLM 层必须封装为 `LLMClient` 协议，默认实现 `DeepSeekClient`，测试使用 `FakeLLMClient`。
3. DeepSeek 模型名称不要散落硬编码，只允许在 `Settings.deepseek_model` 中配置。
4. LLM 原始响应必须保存到 `llm_raw_output` 字段，方便追责和 prompt 迭代。
5. Pydantic schema 校验失败不得吞异常，必须转换为 `review_required=true` 的业务结果。
6. 规则兜底实现为 `RuleBasedClassifier`，先用关键词权重表，不做复杂 NLP。
7. CSV 处理必须按 chunk 执行，不能一次性把大文件全部分类后再写库。
8. 批处理接口返回 `batch_id` 和状态，不应让 HTTP 请求阻塞到整个 CSV 处理完成。
9. SQLite repository 层只暴露业务方法，避免上层依赖 SQLModel Session。
10. 测试必须覆盖：有效 JSON、非法 JSON、空响应、低置信度、多类别冲突、缺失 description、CSV 导出。

---

## 11. 推荐方案

### 首选方案

**FastAPI + DeepSeek JSON Output + Pydantic 校验 + 规则兜底 + Pandas chunk CSV + SQLModel/SQLite。**

原因：

- 符合用户指定 FastAPI 与 DeepSeek API。
- 无真实训练数据时，比传统分类器更快落地。
- 结构化输出能力足够支撑 v1，但通过 Pydantic 与规则层补足可靠性。
- SQLite 足够支撑单云服务器 v1，并且通过 repository 层保留 PostgreSQL 迁移路径。
- 批处理规模可控，后续可平滑升级到队列和 PostgreSQL。

### 备选方案

如果 DeepSeek JSON Output 在真实测试中稳定性不足：

1. 保留 DeepSeek 语义分类。
2. 增加二阶段 JSON 修复器：把模型自然语言/半结构化输出转为合法 JSON。
3. 或切换到 strict Function Calling beta 做结构化输出试验。
4. 如仍不稳定，再评估 OpenAI/通义等支持更强 schema 输出的 API。

---

## 12. 阶段 2 架构设计建议输入

架构设计阶段默认按以下决策继续，除非用户明确推翻：

- API：FastAPI only，不做 Streamlit。
- 部署：Docker on 单云服务器。
- 数据库：SQLite v1，repository 层预留 PostgreSQL。
- 批处理：FastAPI BackgroundTasks，暂不引入 Celery。
- LLM：DeepSeek API，模型名通过环境变量配置。
- 分类：单主类 + 多候选类。
- 人工复核：v1 只做状态字段和 API，不做复杂权限系统。
- UI：v1 可提供 Swagger/OpenAPI + 最小 HTML 上传页；若要求完整前端，需新增前端模块。

---

## 13. 关键参考资料

1. DeepSeek API Docs — JSON Output  
   https://api-docs.deepseek.com/guides/json_mode
2. DeepSeek API Docs — Function Calling / strict mode beta  
   https://api-docs.deepseek.com/guides/function_calling
3. DeepSeek API Docs — First API Call / OpenAI-compatible format  
   https://api-docs.deepseek.com/
4. FastAPI Docs — Request Files / UploadFile  
   https://fastapi.tiangolo.com/tutorial/request-files/
5. FastAPI Docs — BackgroundTasks  
   https://fastapi.tiangolo.com/tutorial/background-tasks/
6. FastAPI Docs — SQL Databases / SQLModel  
   https://fastapi.tiangolo.com/tutorial/sql-databases/
7. SQLModel GitHub README  
   https://github.com/fastapi/sqlmodel
8. Pandas Docs — read_csv chunksize / iterator  
   https://pandas.pydata.org/docs/reference/api/pandas.read_csv.html
9. SQLite Python Best Practices — PRAGMA, WAL, foreign_keys, busy_timeout  
   https://tessl.io/registry/tessl-labs/sqlite-python-best-practices/0.2.0
