# 开发计划

## 元信息

- 项目: NetTriage AI
- 中文名: 网络故障工单智能分诊系统
- 版本: v1
- 技术栈: Python 3.12 / FastAPI / DeepSeek API / Pydantic v2 / SQLModel / SQLite / Pandas / uv / pytest / ruff / mypy / Docker
- 总模块数: 10
- 预计步骤总数: 47
- 建议开发顺序: Module A 工程骨架 → Module B 配置日志 → Module C Schema → Module D 数据库 → Module E 规则引擎 → Module F LLM → Module G 分类服务 → Module H CSV 批处理 → Module I API → Module J 测试部署文档
- 创建日期: 2026-05-06
- 最后更新: 2026-05-06

### 变更记录

| 版本 | 日期 | 变更摘要 |
|------|------|---------|
| v1 | 2026-05-06 | 初始创建，基于 architecture.md 与 research-report.md 制定完整 v1 开发计划 |

---

## Status

> 任何 agent 读到此区块即可恢复完整上下文。

- 当前阶段: Module A Step 1
- 整体进度: 0 / 47 步骤完成
- 状态: 待启动
- 阻塞项: 无

### Last Iteration Summary

首次创建，尚未执行。

### Pending Decisions

无。v1 默认决策如下：

- API 框架: FastAPI
- LLM: DeepSeek API
- 数据库: SQLite，repository 层预留 PostgreSQL
- 批处理: FastAPI BackgroundTasks，不引入 Celery/RQ
- 部署: Docker on 单云服务器
- 前端: v1 仅提供 Swagger/OpenAPI 与最小上传页面，不做独立 SPA
- 人工复核: v1 只做状态字段与 API，不做用户权限系统

---

## Module A: 工程骨架与基础依赖

### 概述

- 职责: 初始化 Python 项目、依赖、目录结构、质量工具和基础启动入口。
- 前置依赖: 无。
- 预计步骤数: 5。

### Step 1: 初始化项目与包管理

- **scope: auto**
- 操作:
  - 创建 `pyproject.toml`。
  - 设置项目名 `nettriage-ai`，包路径 `src/nettriage`。
  - Python 版本固定为 `>=3.12,<3.13`。
  - 使用 `uv` 管理依赖。
  - 添加运行依赖:
    - `fastapi`
    - `uvicorn[standard]`
    - `pydantic`
    - `pydantic-settings`
    - `sqlmodel`
    - `pandas`
    - `python-multipart`
    - `httpx`
    - `tenacity`
  - 添加开发依赖:
    - `pytest`
    - `pytest-asyncio`
    - `pytest-cov`
    - `ruff`
    - `mypy`
    - `types-python-dateutil`
- 验证:
  - `uv sync`
  - `uv run python -c "import fastapi, pydantic, sqlmodel, pandas, httpx"`

### Step 2: 创建标准目录结构

- **scope: auto**
- 操作:
  - 创建以下目录:
    - `src/nettriage/api/routes`
    - `src/nettriage/batch`
    - `src/nettriage/core`
    - `src/nettriage/db`
    - `src/nettriage/llm`
    - `src/nettriage/repositories`
    - `src/nettriage/rules`
    - `src/nettriage/schemas`
    - `src/nettriage/services`
    - `tests/unit`
    - `tests/integration`
    - `tests/e2e`
    - `tests/fixtures`
    - `data/uploads`
    - `data/exports`
    - `docs/references`
  - 为每个 Python package 创建 `__init__.py`。
  - 在 `data/` 子目录下创建 `.gitkeep`。
- 验证:
  - `test -d src/nettriage/api/routes`
  - `test -f src/nettriage/__init__.py`
  - `find src/nettriage -type d | sort`

### Step 3: 配置代码质量工具

- **scope: auto**
- 操作:
  - 在 `pyproject.toml` 中配置 `ruff`:
    - line length: 100
    - target version: py312
    - 启用 `E`, `F`, `I`, `UP`, `B`, `SIM`
  - 创建或配置 `mypy.ini`:
    - `python_version = 3.12`
    - `strict = True`
    - 对 pandas 第三方类型缺失允许局部 ignore。
  - 创建 `pytest.ini`:
    - testpaths: `tests`
    - asyncio_mode: `auto`
    - addopts: `-ra`
- 验证:
  - `uv run ruff check .`
  - `uv run mypy src`
  - `uv run pytest --collect-only`

### Step 4: 创建 FastAPI 最小应用入口

- **scope: auto**
- 操作:
  - 创建 `src/nettriage/api/main.py`。
  - 定义 `create_app() -> FastAPI`。
  - 注册 `/healthz` 路由。
  - 仅返回基础状态:
    - `status`
    - `app`
    - `version`
  - 创建 `src/nettriage/api/routes/health.py`，实现 `router = APIRouter(tags=["health"])`。
- 验证:
  - `uv run uvicorn nettriage.api.main:app --host 127.0.0.1 --port 8000`
  - 另开终端执行 `curl http://127.0.0.1:8000/healthz`

### Step 5: 建立测试基础设施

- **scope: auto**
- 操作:
  - 创建 `tests/conftest.py`。
  - 提供 `test_client` fixture，基于 `fastapi.testclient.TestClient`。
  - 创建 `tests/integration/test_health_api.py`。
  - 测试 `/healthz` 返回 200 且 `status == "ok"`。
- 验证:
  - `uv run pytest tests/integration/test_health_api.py`
  - `uv run pytest`

---

## Module B: 配置、日志与基础安全

### 概述

- 职责: 统一配置来源、环境变量、日志格式、基础安全工具。
- 前置依赖: Module A。
- 预计步骤数: 4。

### Step 6: 实现 Settings 配置模型

- **scope: auto**
- 操作:
  - 创建 `src/nettriage/core/config.py`。
  - 实现 `Settings(BaseSettings)`，字段包括:
    - `app_name: str = "NetTriage AI"`
    - `environment: str = "dev"`
    - `deepseek_api_key: SecretStr | None = None`
    - `deepseek_base_url: str = "https://api.deepseek.com"`
    - `deepseek_model: str = "deepseek-chat"`
    - `deepseek_timeout_seconds: int = 30`
    - `deepseek_max_retries: int = 2`
    - `database_url: str = "sqlite:///./data/nettriage.db"`
    - `upload_dir: Path = Path("./data/uploads")`
    - `export_dir: Path = Path("./data/exports")`
    - `max_upload_mb: int = 20`
    - `max_csv_rows: int = 50000`
    - `csv_chunksize: int = 500`
    - `review_confidence_threshold: float = 0.80`
    - `conflict_score_delta: float = 0.08`
    - `log_level: str = "INFO"`
  - 添加 `get_settings()`，使用 `functools.lru_cache`。
  - 创建 `.env.example`，包含所有关键环境变量。
- 验证:
  - `uv run python -c "from nettriage.core.config import get_settings; print(get_settings().app_name)"`
  - `uv run pytest`

### Step 7: 实现结构化日志配置

- **scope: auto**
- 操作:
  - 创建 `src/nettriage/core/logging.py`。
  - 实现 `configure_logging(settings: Settings) -> None`。
  - 默认输出 JSON-like 单行日志，字段包含:
    - `timestamp`
    - `level`
    - `logger`
    - `message`
  - 禁止日志配置中输出 `deepseek_api_key`。
  - 在 `api/main.py` 的 `create_app()` 中调用 `configure_logging()`。
- 验证:
  - `uv run python -c "from nettriage.core.logging import configure_logging; from nettriage.core.config import get_settings; configure_logging(get_settings())"`
  - `uv run ruff check src/nettriage/core/logging.py`

### Step 8: 实现安全辅助函数

- **scope: auto**
- 操作:
  - 创建 `src/nettriage/core/security.py`。
  - 实现:
    - `hash_text(text: str) -> str`，使用 SHA-256。
    - `safe_batch_id() -> str`，格式 `batch_YYYYMMDD_HHMMSS_<8hex>`。
    - `ensure_within_directory(base_dir: Path, target: Path) -> Path`，防路径穿越。
    - `redact_text(text: str, max_chars: int = 80) -> str`，只用于 debug 截断。
  - 为上述函数创建 `tests/unit/test_security.py`。
- 验证:
  - `uv run pytest tests/unit/test_security.py`
  - `uv run ruff check src/nettriage/core/security.py`

### Step 9: 实现统一 API 错误格式

- **scope: auto**
- 操作:
  - 创建 `src/nettriage/api/errors.py`。
  - 定义 `APIErrorCode(str, Enum)`，至少包含:
    - `VALIDATION_ERROR`
    - `CSV_FILE_TOO_LARGE`
    - `CSV_DESCRIPTION_COLUMN_MISSING`
    - `CSV_ROW_LIMIT_EXCEEDED`
    - `BATCH_NOT_FOUND`
    - `TICKET_NOT_FOUND`
    - `LLM_TEMPORARILY_UNAVAILABLE`
    - `INTERNAL_ERROR`
  - 定义 `APIError(Exception)`。
  - 在 `api/main.py` 注册异常 handler，返回:
    ```json
    {
      "error": {
        "code": "...",
        "message": "...",
        "details": {}
      }
    }
    ```
  - 创建 `tests/integration/test_error_format.py`。
- 验证:
  - `uv run pytest tests/integration/test_error_format.py`
  - `uv run pytest`

---

## Module C: Schema 与枚举模型

### 概述

- 职责: 定义分类枚举、API 请求响应、LLM 输出结构、批处理与复核模型。
- 前置依赖: Module A、B。
- 预计步骤数: 5。

### Step 10: 定义故障分类与状态枚举

- **scope: auto**
- 操作:
  - 创建 `src/nettriage/schemas/enums.py`。
  - 定义 `FaultCategory(str, Enum)`:
    - `COVERAGE_ISSUE`
    - `DROPPED_CONNECTION`
    - `HIGH_LATENCY`
    - `DNS_FAILURE`
    - `AUTH_FAILURE`
    - `DEVICE_FAILURE`
    - `WEAK_SIGNAL`
    - `CONFIG_ERROR`
    - `PACKET_LOSS`
    - `BANDWIDTH_DEGRADATION`
    - `SERVICE_OUTAGE`
    - `CUSTOMER_PREMISES_ISSUE`
    - `UNKNOWN`
  - 定义 `ReviewStatus(str, Enum)`:
    - `PENDING`
    - `CONFIRMED`
    - `CORRECTED`
    - `REJECTED`
  - 定义 `BatchStatus(str, Enum)`:
    - `PENDING`
    - `RUNNING`
    - `COMPLETED`
    - `PARTIAL_FAILED`
    - `FAILED`
- 验证:
  - `uv run python -c "from nettriage.schemas.enums import FaultCategory; print(FaultCategory.UNKNOWN)"`
  - `uv run mypy src/nettriage/schemas/enums.py`

### Step 11: 定义分类请求、LLM 输出与业务结果模型

- **scope: auto**
- 操作:
  - 创建 `src/nettriage/schemas/classification.py`。
  - 实现:
    - `ClassifyRequest`
    - `LLMClassificationOutput`
    - `ClassificationResult`
    - `ClassifyResponse`
  - `ClassifyRequest.description` 约束:
    - 最小长度 1
    - 最大长度 4000
  - `LLMClassificationOutput.confidence` 约束:
    - `ge=0.0`
    - `le=1.0`
  - `LLMClassificationOutput.summary` 最大长度 500。
  - `LLMClassificationOutput.troubleshooting_steps` 数量 1 到 8。
- 验证:
  - `uv run python -c "from nettriage.schemas.classification import ClassifyRequest; ClassifyRequest(description='DNS无法解析')"`
  - `uv run pytest`

### Step 12: 定义批处理 Schema

- **scope: auto**
- 操作:
  - 创建 `src/nettriage/schemas/batch.py`。
  - 实现:
    - `BatchCreateResponse`
    - `BatchStatusResponse`
    - `CSVFieldMapping`
    - `CSVRowResult`
  - `BatchStatusResponse` 必须包含:
    - `batch_id`
    - `status`
    - `total_rows`
    - `processed_rows`
    - `success_rows`
    - `failed_rows`
    - `review_required_rows`
    - `created_at`
    - `completed_at`
    - `error_message`
- 验证:
  - `uv run python -c "from nettriage.schemas.batch import BatchStatusResponse"`
  - `uv run mypy src/nettriage/schemas/batch.py`

### Step 13: 定义工单查询与复核 Schema

- **scope: auto**
- 操作:
  - 创建 `src/nettriage/schemas/ticket.py`。
  - 实现:
    - `TicketRecordResponse`
    - `TicketQueryFilters`
    - `ReviewUpdateRequest`
    - `ReviewUpdateResponse`
  - `ReviewUpdateRequest.review_status` 使用 `ReviewStatus`。
  - `ReviewUpdateRequest.reviewed_category` 使用 `FaultCategory | None`。
- 验证:
  - `uv run python -c "from nettriage.schemas.ticket import ReviewUpdateRequest"`
  - `uv run mypy src/nettriage/schemas/ticket.py`

### Step 14: 定义通用响应模型

- **scope: auto**
- 操作:
  - 创建 `src/nettriage/schemas/common.py`。
  - 实现:
    - `ErrorEnvelope`
    - `PaginationMeta`
    - `PaginatedResponse[T]`
  - 所有查询型响应后续统一复用。
- 验证:
  - `uv run python -c "from nettriage.schemas.common import ErrorEnvelope"`
  - `uv run mypy src/nettriage/schemas/common.py`

---

## Module D: SQLite 数据库与 Repository

### 概述

- 职责: 定义 SQLModel 表、数据库初始化、会话管理、工单与批处理 repository。
- 前置依赖: Module B、C。
- 预计步骤数: 5。

### Step 15: 实现数据库会话与初始化

- **scope: auto**
- 操作:
  - 创建 `src/nettriage/db/session.py`。
  - 实现:
    - `create_engine_from_settings(settings: Settings) -> Engine`
    - `get_session() -> Iterator[Session]`
  - 创建 `src/nettriage/db/init_db.py`。
  - 实现 `init_db(engine: Engine) -> None`:
    - 执行 `SQLModel.metadata.create_all(engine)`
    - 对 SQLite 执行:
      - `PRAGMA journal_mode=WAL`
      - `PRAGMA foreign_keys=ON`
      - `PRAGMA busy_timeout=5000`
      - `PRAGMA synchronous=NORMAL`
- 验证:
  - `uv run python -c "from nettriage.db.init_db import init_db"`
  - `uv run mypy src/nettriage/db`

### Step 16: 定义 SQLModel 表

- **scope: auto**
- 操作:
  - 创建 `src/nettriage/db/models.py`。
  - 实现 `TicketRecord(SQLModel, table=True)`，字段必须覆盖:
    - `id`
    - `ticket_id`
    - `batch_id`
    - `description_hash`
    - `description_text`
    - `primary_category`
    - `secondary_categories_json`
    - `confidence`
    - `category_scores_json`
    - `key_symptoms_json`
    - `summary`
    - `troubleshooting_steps_json`
    - `review_required`
    - `review_status`
    - `review_reasons_json`
    - `reviewed_category`
    - `review_note`
    - `llm_model`
    - `llm_raw_output`
    - `llm_latency_ms`
    - `fallback_used`
    - `error`
    - `source`
    - `customer_region`
    - `created_at`
    - `processed_at`
  - 实现 `BatchJob(SQLModel, table=True)`，字段必须覆盖:
    - `id`
    - `batch_id`
    - `input_filename`
    - `stored_input_path`
    - `output_path`
    - `status`
    - `total_rows`
    - `processed_rows`
    - `success_rows`
    - `failed_rows`
    - `review_required_rows`
    - `error_message`
    - `created_at`
    - `started_at`
    - `completed_at`
- 验证:
  - `uv run python -c "from nettriage.db.models import TicketRecord, BatchJob; print(TicketRecord.__tablename__, BatchJob.__tablename__)"`
  - `uv run mypy src/nettriage/db/models.py`

### Step 17: 实现 TicketRepository

- **scope: auto**
- 操作:
  - 创建 `src/nettriage/repositories/ticket_repository.py`。
  - 实现 `TicketRepository`:
    - `create_result(data: TicketRecordCreate) -> TicketRecord`
    - `get_by_id(record_id: int) -> TicketRecord | None`
    - `list_results(filters: TicketQueryFilters) -> list[TicketRecord]`
    - `update_review_status(record_id, review_status, reviewed_category, review_note) -> TicketRecord`
  - 如不想新增 `TicketRecordCreate` schema，可在 repository 文件内定义 dataclass。
  - `list_results` 支持按:
    - `primary_category`
    - `review_required`
    - `batch_id`
    - `keyword`
    - `limit`
    - `offset`
  - keyword 只对 `description_text` 和 `summary` 做 `LIKE` 查询。
- 验证:
  - `uv run pytest tests/integration/test_repository.py -k ticket`
  - `uv run mypy src/nettriage/repositories/ticket_repository.py`

### Step 18: 实现 BatchRepository

- **scope: auto**
- 操作:
  - 创建 `src/nettriage/repositories/batch_repository.py`。
  - 实现 `BatchRepository`:
    - `create_batch(data: BatchJobCreate) -> BatchJob`
    - `get_by_batch_id(batch_id: str) -> BatchJob | None`
    - `mark_running(batch_id: str, total_rows: int) -> None`
    - `increment_progress(batch_id: str, success_delta: int, failed_delta: int, review_required_delta: int) -> None`
    - `mark_completed(batch_id: str, output_path: str) -> None`
    - `mark_partial_failed(batch_id: str, output_path: str, error_message: str | None = None) -> None`
    - `mark_failed(batch_id: str, error_message: str) -> None`
  - 保证找不到 batch 时抛出明确 repository 异常。
- 验证:
  - `uv run pytest tests/integration/test_repository.py -k batch`
  - `uv run mypy src/nettriage/repositories/batch_repository.py`

### Step 19: 补齐 Repository 集成测试

- **scope: auto**
- 操作:
  - 创建 `tests/integration/test_repository.py`。
  - 使用临时 SQLite 文件。
  - 覆盖:
    - 创建工单结果
    - 查询工单结果
    - 更新复核状态
    - 创建 batch
    - 更新 batch 进度
    - 标记完成/失败
  - 测试完成后清理临时数据库文件。
- 验证:
  - `uv run pytest tests/integration/test_repository.py`
  - `uv run pytest --cov=nettriage.repositories`

---

## Module E: 文本清洗、规则分类与复核策略

### 概述

- 职责: 实现非 LLM 层的稳定性兜底，包括文本标准化、关键词权重、低置信度与冲突复核。
- 前置依赖: Module C。
- 预计步骤数: 5。

### Step 20: 实现 TextNormalizer

- **scope: auto**
- 操作:
  - 创建 `src/nettriage/rules/text_normalizer.py`。
  - 实现 `TextNormalizer.normalize(text: str) -> str`:
    - 去除前后空白
    - 合并连续空白
    - 全角转半角
    - 英文统一 lower
    - 保留中文
  - 实现 `TextNormalizer.is_insufficient(text: str) -> bool`:
    - 中文/混合文本少于 8 个非空字符返回 true
    - 英文文本少于 4 个词返回 true
- 验证:
  - `uv run pytest tests/unit/test_text_normalizer.py`

### Step 21: 定义关键词规则表

- **scope: auto**
- 操作:
  - 创建 `src/nettriage/rules/keyword_rules.py`。
  - 定义 `KEYWORD_RULES: dict[FaultCategory, dict[str, int]]`。
  - 至少覆盖:
    - `DNS_FAILURE`: `dns`, `域名解析`, `无法解析`, `能ping ip`
    - `AUTH_FAILURE`: `认证失败`, `pppoe`, `radius`, `账号密码`
    - `WEAK_SIGNAL`: `信号弱`, `rssi`, `sinr`, `wifi弱`, `wi-fi弱`
    - `PACKET_LOSS`: `丢包`, `packet loss`, `ping丢`, `抖动`
    - `HIGH_LATENCY`: `延迟高`, `时延高`, `ping高`, `卡顿`
    - `DROPPED_CONNECTION`: `掉线`, `断开`, `频繁中断`
    - `CONFIG_ERROR`: `vlan`, `acl`, `nat`, `路由配置`, `dhcp`
    - `DEVICE_FAILURE`: `光猫故障`, `路由器故障`, `端口故障`, `硬件告警`
    - `SERVICE_OUTAGE`: `大面积`, `区域故障`, `全站不可用`, `出口异常`
    - `BANDWIDTH_DEGRADATION`: `下载慢`, `速率低`, `带宽不达标`
  - 每个类别至少 4 个关键词。
- 验证:
  - `uv run python -c "from nettriage.rules.keyword_rules import KEYWORD_RULES; assert KEYWORD_RULES"`
  - `uv run ruff check src/nettriage/rules/keyword_rules.py`

### Step 22: 实现 RuleBasedClassifier

- **scope: auto**
- 操作:
  - 创建 `src/nettriage/rules/rule_classifier.py`。
  - 定义:
    - `RuleClassificationResult`
    - `RuleBasedClassifier`
  - 实现 `RuleBasedClassifier.classify(description: str) -> RuleClassificationResult`:
    - 按关键词权重累计每个 `FaultCategory` 的分数。
    - 分数最高作为 `primary_category`。
    - 分数大于 0 的其余类别作为候选。
    - 最高分 `>= 3` 时 `strong_match=True`。
    - 无命中时返回 `UNKNOWN`。
- 验证:
  - `uv run pytest tests/unit/test_rule_classifier.py`
  - `uv run mypy src/nettriage/rules/rule_classifier.py`

### Step 23: 实现 ReviewPolicy

- **scope: auto**
- 操作:
  - 创建 `src/nettriage/rules/review_policy.py`。
  - 定义:
    - `ReviewDecision`
    - `ReviewReason(str, Enum)` 或常量字符串。
  - 实现 `ReviewPolicy.evaluate(...) -> ReviewDecision`。
  - 固定规则:
    - `fallback_used=True` → `REVIEW_FALLBACK_USED`
    - `parse_error is not None` → `REVIEW_LLM_OUTPUT_INVALID`
    - `llm_result is None` → `REVIEW_LLM_RESULT_MISSING`
    - `confidence < 0.80` → `REVIEW_LOW_CONFIDENCE`
    - `top1_score - top2_score < 0.08` → `REVIEW_CATEGORY_CONFLICT`
    - 规则强命中且规则主类不同于 LLM 主类 → `REVIEW_RULE_LLM_CONFLICT`
    - 信息不足 → `REVIEW_INSUFFICIENT_INFORMATION`
- 验证:
  - `uv run pytest tests/unit/test_review_policy.py`
  - `uv run mypy src/nettriage/rules/review_policy.py`

### Step 24: 补齐规则层单元测试

- **scope: auto**
- 操作:
  - 创建:
    - `tests/unit/test_text_normalizer.py`
    - `tests/unit/test_rule_classifier.py`
    - `tests/unit/test_review_policy.py`
  - 用例至少覆盖:
    - DNS 命中
    - PPPoE/RADIUS 命中
    - Wi-Fi 信号弱命中
    - ping 丢包命中
    - 无关键词返回 UNKNOWN
    - 低置信度触发复核
    - 多类别分数冲突触发复核
    - LLM 与规则冲突触发复核
    - fallback 触发复核
- 验证:
  - `uv run pytest tests/unit/test_text_normalizer.py tests/unit/test_rule_classifier.py tests/unit/test_review_policy.py`
  - `uv run pytest --cov=nettriage.rules`

---

## Module F: DeepSeek LLM Client 与输出校验

### 概述

- 职责: 封装 DeepSeek API、prompt、重试、错误映射，以及 LLM JSON 输出校验。
- 前置依赖: Module B、C、E。
- 预计步骤数: 5。

### Step 25: 定义 LLM 抽象协议与错误类型

- **scope: auto**
- 操作:
  - 创建 `src/nettriage/llm/base.py`。
  - 定义:
    - `LLMClient(Protocol)`
    - `LLMRawResponse`
  - 创建 `src/nettriage/llm/errors.py`。
  - 定义:
    - `LLMError`
    - `LLMTimeoutError`
    - `LLMRateLimitError`
    - `LLMEmptyResponseError`
    - `LLMProviderError`
    - `LLMOutputParseError`
    - `LLMOutputValidationError`
- 验证:
  - `uv run python -c "from nettriage.llm.base import LLMRawResponse"`
  - `uv run mypy src/nettriage/llm`

### Step 26: 编写 DeepSeek 分类 Prompt

- **scope: review**
- 操作:
  - 创建 `src/nettriage/llm/prompts.py`。
  - 实现 `CLASSIFICATION_SYSTEM_PROMPT`。
  - Prompt 必须要求:
    - Return only valid JSON.
    - 不输出 markdown。
    - `primary_category` 必须从 `FaultCategory` 枚举中选择。
    - 输出字段必须包含:
      - `primary_category`
      - `secondary_categories`
      - `confidence`
      - `category_scores`
      - `key_symptoms`
      - `summary`
      - `troubleshooting_steps`
    - `confidence` 范围 0 到 1。
    - `troubleshooting_steps` 1 到 8 条。
  - 实现 `build_classification_user_prompt(description: str) -> str`。
  - user prompt 只拼接故障描述，不允许把用户输入解释为系统指令。
- 验证:
  - `uv run python -c "from nettriage.llm.prompts import CLASSIFICATION_SYSTEM_PROMPT; assert 'JSON' in CLASSIFICATION_SYSTEM_PROMPT.upper()"`
  - `uv run ruff check src/nettriage/llm/prompts.py`

### Step 27: 实现 DeepSeekClient

- **scope: review**
- 操作:
  - 创建 `src/nettriage/llm/deepseek.py`。
  - 实现 `DeepSeekClient(LLMClient)`:
    - 构造函数接收 `Settings` 与可选 `httpx.AsyncClient`。
    - `classify_fault(description: str) -> LLMRawResponse`。
    - 请求地址使用 `settings.deepseek_base_url`。
    - 请求 body 使用 OpenAI-compatible chat completions。
    - 设置 `response_format={"type": "json_object"}`。
    - 设置 `model=settings.deepseek_model`。
    - 设置 timeout 为 `settings.deepseek_timeout_seconds`。
    - 429/5xx 使用 `tenacity` 指数退避重试，最多 `settings.deepseek_max_retries`。
    - content 为空时抛 `LLMEmptyResponseError`。
    - 不在日志记录完整 description。
  - 不在此 Step 中接入真实 API 测试。
- 验证:
  - `uv run mypy src/nettriage/llm/deepseek.py`
  - `uv run ruff check src/nettriage/llm/deepseek.py`
  - `uv run pytest tests/unit/test_deepseek_client.py`

### Step 28: 实现 LLM 输出校验器

- **scope: auto**
- 操作:
  - 创建 `src/nettriage/llm/output_validator.py`。
  - 实现 `ClassificationOutputValidator.parse_and_validate(raw_content: str) -> LLMClassificationOutput`。
  - 行为:
    - `json.loads` 失败抛 `LLMOutputParseError`。
    - Pydantic 校验失败抛 `LLMOutputValidationError`。
    - `category_scores` 中非枚举 key 必须失败。
    - 空字符串必须失败。
  - 创建 `tests/unit/test_output_validator.py`。
- 验证:
  - `uv run pytest tests/unit/test_output_validator.py`
  - `uv run mypy src/nettriage/llm/output_validator.py`

### Step 29: 创建 FakeLLMClient 与 LLM 单元测试

- **scope: auto**
- 操作:
  - 在 `tests/conftest.py` 或 `tests/fakes.py` 中实现 `FakeLLMClient`。
  - Fake 支持配置:
    - 返回合法 JSON。
    - 返回非法 JSON。
    - 返回空 content。
    - 抛出 `LLMProviderError`。
  - 创建 `tests/unit/test_deepseek_client.py`，使用 mock transport，不调用真实 DeepSeek API。
  - 覆盖:
    - 正常解析 response content。
    - 429/5xx 错误映射。
    - 空 content 错误。
    - timeout 错误。
- 验证:
  - `uv run pytest tests/unit/test_deepseek_client.py tests/unit/test_output_validator.py`
  - `uv run pytest --cov=nettriage.llm`

---

## Module G: 核心分类服务与工单服务

### 概述

- 职责: 组装 LLM、校验、规则、复核策略和 repository，形成单条分类闭环。
- 前置依赖: Module C、D、E、F。
- 预计步骤数: 5。

### Step 30: 实现 ClassificationService 主流程

- **scope: review**
- 操作:
  - 创建 `src/nettriage/services/classification_service.py`。
  - 实现 `ClassificationService`:
    - 构造函数接收:
      - `llm_client`
      - `validator`
      - `rule_classifier`
      - `review_policy`
      - `ticket_repository`
      - `settings`
    - 实现 `async classify_text(...) -> ClassificationResult`。
  - 固定流程:
    1. `TextNormalizer.normalize(description)`
    2. 判断信息不足。
    3. 调用 `llm_client.classify_fault(normalized_description)`。
    4. `validator.parse_and_validate(raw.content)`。
    5. 调用 `rule_classifier.classify(normalized_description)`。
    6. 调用 `review_policy.evaluate(...)`。
    7. 组装 `ClassificationResult`。
    8. 调用 `ticket_repository.create_result(...)` 保存。
    9. 返回结果。
- 验证:
  - `uv run pytest tests/unit/test_classification_service.py -k success`
  - `uv run mypy src/nettriage/services/classification_service.py`

### Step 31: 实现分类失败与规则兜底流程

- **scope: review**
- 操作:
  - 在 `ClassificationService.classify_text()` 中实现失败路径:
    - LLM JSON parse 失败后允许一次 JSON 修复重试。
    - LLM 调用异常时进入规则兜底。
    - 规则未命中时返回 `UNKNOWN`。
    - 所有降级结果必须:
      - `fallback_used=True`
      - `review_required=True`
      - `review_reasons` 包含明确原因。
  - 实现 `_build_fallback_result(...)` 私有方法。
  - API 响应不返回内部堆栈。
  - DB 记录 `error` 字段只保存错误类型和摘要。
- 验证:
  - `uv run pytest tests/unit/test_classification_service.py -k fallback`
  - `uv run pytest tests/unit/test_classification_service.py -k invalid_json`

### Step 32: 实现 TicketService 与 ReviewService

- **scope: auto**
- 操作:
  - 创建 `src/nettriage/services/ticket_service.py`。
  - 实现:
    - `list_tickets(filters: TicketQueryFilters) -> list[TicketRecordResponse]`
    - `get_ticket(record_id: int) -> TicketRecordResponse`
  - 创建 `src/nettriage/services/review_service.py`。
  - 实现:
    - `update_review(record_id: int, request: ReviewUpdateRequest) -> ReviewUpdateResponse`
  - 找不到记录时抛 `APIError(code=TICKET_NOT_FOUND)` 或 service 层领域异常，由 API 转换。
- 验证:
  - `uv run pytest tests/unit/test_ticket_service.py`
  - `uv run mypy src/nettriage/services`

### Step 33: 实现服务层依赖装配

- **scope: auto**
- 操作:
  - 创建 `src/nettriage/api/dependencies.py`。
  - 实现:
    - `get_settings_dep()`
    - `get_db_session()`
    - `get_ticket_repository()`
    - `get_batch_repository()`
    - `get_llm_client()`
    - `get_classification_service()`
    - `get_ticket_service()`
    - `get_review_service()`
  - 测试环境必须允许 override `get_llm_client()` 为 `FakeLLMClient`。
- 验证:
  - `uv run python -c "from nettriage.api.dependencies import get_classification_service"`
  - `uv run pytest tests/integration/test_classify_api.py -k dependency`

### Step 34: 补齐分类服务单元测试

- **scope: auto**
- 操作:
  - 创建 `tests/unit/test_classification_service.py`。
  - 覆盖:
    - LLM 成功且高置信度。
    - LLM 成功但低置信度。
    - LLM 与规则冲突。
    - LLM 非法 JSON。
    - LLM 空响应。
    - LLM provider error。
    - 信息不足。
    - repository 被调用并保存。
- 验证:
  - `uv run pytest tests/unit/test_classification_service.py`
  - `uv run pytest --cov=nettriage.services`

---

## Module H: CSV 批处理

### 概述

- 职责: 上传文件保存、字段识别、CSV 分块读取、逐行分类、结果导出、批处理状态更新。
- 前置依赖: Module D、G。
- 预计步骤数: 5。

### Step 35: 实现上传文件存储

- **scope: auto**
- 操作:
  - 创建 `src/nettriage/batch/file_store.py`。
  - 实现 `BatchFileStore`:
    - `save_upload(batch_id: str, upload_file: UploadFile) -> Path`
    - `get_input_path(batch_id: str) -> Path`
    - `get_output_path(batch_id: str) -> Path`
  - 行为:
    - 只接受 `.csv`。
    - 文件大小超过 `settings.max_upload_mb` 抛错。
    - 使用 `batch_id.csv` 命名，禁止使用原始文件名作为落盘文件名。
    - 保存到 `settings.upload_dir`。
- 验证:
  - `uv run pytest tests/unit/test_file_store.py`
  - `uv run mypy src/nettriage/batch/file_store.py`

### Step 36: 实现 CSV 字段映射

- **scope: auto**
- 操作:
  - 创建 `src/nettriage/batch/field_mapper.py`。
  - 实现 `CSVFieldMapper`:
    - `infer_mapping(columns: list[str]) -> CSVFieldMapping`
    - `infer_mapping_from_file(input_path: Path) -> CSVFieldMapping`
  - 内部标准字段:
    - `ticket_id`
    - `description`
    - `created_at`
    - `source`
    - `customer_region`
    - `priority`
  - 描述字段别名至少支持:
    - `description`
    - `desc`
    - `content`
    - `fault_description`
    - `problem_description`
    - `故障描述`
    - `问题描述`
    - `故障现象`
  - 无法识别 description 时抛 `CSV_DESCRIPTION_COLUMN_MISSING`。
- 验证:
  - `uv run pytest tests/unit/test_field_mapper.py`
  - `uv run mypy src/nettriage/batch/field_mapper.py`

### Step 37: 实现结果 CSV 导出器

- **scope: auto**
- 操作:
  - 创建 `src/nettriage/batch/exporter.py`。
  - 实现 `ResultCSVExporter`:
    - `create_output(batch_id: str) -> Path`
    - `append_row(batch_id: str, row: CSVRowResult | dict[str, Any]) -> None`
    - `get_output_path(batch_id: str) -> Path`
  - 输出字段固定:
    - `ticket_id`
    - `primary_category`
    - `secondary_categories`
    - `confidence`
    - `review_required`
    - `review_reasons`
    - `key_symptoms`
    - `summary`
    - `troubleshooting_steps`
    - `llm_model`
    - `llm_latency_ms`
    - `processed_at`
    - `error`
  - list/dict 字段写入 CSV 前必须 JSON 序列化。
- 验证:
  - `uv run pytest tests/unit/test_exporter.py`
  - `uv run mypy src/nettriage/batch/exporter.py`

### Step 38: 实现 CSVProcessor

- **scope: review**
- 操作:
  - 创建 `src/nettriage/batch/csv_processor.py`。
  - 实现 `CSVProcessor.process_batch(batch_id: str, input_path: Path) -> None`。
  - 行为:
    - 通过 `CSVFieldMapper` 识别字段。
    - 计算总行数并校验不超过 `settings.max_csv_rows`。
    - 调用 `batch_repository.mark_running(batch_id, total_rows)`。
    - 使用 `pd.read_csv(input_path, chunksize=settings.csv_chunksize)` 分块读取。
    - 每行调用 `ClassificationService.classify_text(...)`。
    - 每行结果追加到 `ResultCSVExporter`。
    - 单行失败只记录该行 error，并增加 failed_rows。
    - 每个 chunk 后更新 batch 进度。
    - 全部成功标记 `COMPLETED`。
    - 部分失败标记 `PARTIAL_FAILED`。
    - 系统性失败标记 `FAILED`。
  - 不允许一次性把全部 CSV 分类结果放入内存。
- 验证:
  - `uv run pytest tests/unit/test_csv_processor.py`
  - `uv run mypy src/nettriage/batch/csv_processor.py`

### Step 39: 实现 BatchService

- **scope: auto**
- 操作:
  - 创建 `src/nettriage/services/batch_service.py`。
  - 实现:
    - `create_batch(upload_file: UploadFile, background_tasks: BackgroundTasks) -> BatchCreateResponse`
    - `get_batch_status(batch_id: str) -> BatchStatusResponse`
    - `get_batch_download_path(batch_id: str) -> Path`
  - `create_batch` 行为:
    - 生成 `batch_id`。
    - 保存上传文件。
    - 创建 `BatchJob(PENDING)`。
    - 将 `CSVProcessor.process_batch` 放入 `BackgroundTasks`。
    - 返回 `BatchCreateResponse`。
- 验证:
  - `uv run pytest tests/unit/test_batch_service.py`
  - `uv run mypy src/nettriage/services/batch_service.py`

---

## Module I: FastAPI 路由与端到端 API

### 概述

- 职责: 暴露分类、批处理、工单查询、复核更新与下载接口。
- 前置依赖: Module G、H。
- 预计步骤数: 4。

### Step 40: 实现单条分类 API

- **scope: auto**
- 操作:
  - 创建 `src/nettriage/api/routes/classify.py`。
  - 实现 `POST /api/v1/classify`。
  - 请求模型使用 `ClassifyRequest`。
  - 响应模型使用 `ClassifyResponse`。
  - 在 `api/main.py` 注册 router。
  - 集成测试使用 `FakeLLMClient`，不得调用真实 DeepSeek API。
- 验证:
  - `uv run pytest tests/integration/test_classify_api.py`
  - `uv run uvicorn nettriage.api.main:app --host 127.0.0.1 --port 8000`

### Step 41: 实现批处理 API

- **scope: review**
- 操作:
  - 创建 `src/nettriage/api/routes/batches.py`。
  - 实现:
    - `POST /api/v1/batches`
    - `GET /api/v1/batches/{batch_id}`
    - `GET /api/v1/batches/{batch_id}/download`
  - 上传参数使用 `UploadFile`。
  - `POST /api/v1/batches` 返回 `BatchCreateResponse`，不等待处理完成。
  - 下载接口使用 `FileResponse`。
  - 禁止通过 query/path 参数传任意文件路径。
- 验证:
  - `uv run pytest tests/integration/test_batch_api.py`
  - 手动验证: `curl -F "file=@tests/fixtures/sample_tickets.csv" http://127.0.0.1:8000/api/v1/batches`

### Step 42: 实现工单查询与复核 API

- **scope: auto**
- 操作:
  - 创建 `src/nettriage/api/routes/tickets.py`。
  - 实现:
    - `GET /api/v1/tickets`
    - `GET /api/v1/tickets/{record_id}`
    - `PATCH /api/v1/tickets/{record_id}/review`
  - 查询参数支持:
    - `primary_category`
    - `review_required`
    - `batch_id`
    - `keyword`
    - `limit`
    - `offset`
  - 在 `api/main.py` 注册 router。
- 验证:
  - `uv run pytest tests/integration/test_tickets_api.py`
  - `uv run pytest tests/integration`

### Step 43: 增加最小 HTML 上传页面

- **scope: auto**
- 操作:
  - 创建 `src/nettriage/api/routes/ui.py`。
  - 实现 `GET /` 返回最小 HTML:
    - 单条分类表单。
    - CSV 上传表单。
    - 指向 `/docs` 的链接。
  - 不引入前端构建工具。
  - 在 `api/main.py` 注册 router。
- 验证:
  - `uv run pytest tests/integration/test_minimal_ui.py`
  - 浏览器访问 `http://127.0.0.1:8000/`

---

## Module J: 测试、样例数据、Docker 与交付文档

### 概述

- 职责: 补齐样例 CSV、E2E 测试、Docker 部署、README 和最终质量门禁。
- 前置依赖: Module A-I。
- 预计步骤数: 4。

### Step 44: 创建样例 CSV 与 E2E 批处理测试

- **scope: auto**
- 操作:
  - 创建 `tests/fixtures/sample_tickets.csv`，至少 12 条合成工单:
    - DNS 故障
    - 认证失败
    - 弱信号
    - 丢包
    - 高时延
    - 掉线
    - 配置错误
    - 设备故障
    - 服务中断
    - 带宽下降
    - 用户侧问题
    - 信息不足
  - 创建 `tests/fixtures/malformed_tickets.csv`，缺少 description 字段。
  - 创建 `tests/e2e/test_csv_batch_flow.py`。
  - E2E 使用 `FakeLLMClient`，完整跑:
    - 上传 CSV
    - 执行批处理
    - 查询 batch 状态
    - 下载结果 CSV
    - 校验输出字段完整
- 验证:
  - `uv run pytest tests/e2e/test_csv_batch_flow.py`
  - `uv run pytest`

### Step 45: 创建 Dockerfile 与 docker-compose

- **scope: auto**
- 操作:
  - 创建 `Dockerfile`。
  - 要求:
    - 基于 Python 3.12 slim。
    - 安装 `uv`。
    - 复制 `pyproject.toml` 与 `uv.lock`。
    - 安装依赖。
    - 复制 `src/`。
    - 创建非 root 用户。
    - 创建 `/app/data/uploads` 与 `/app/data/exports`。
    - 启动命令:
      - `uvicorn nettriage.api.main:app --host 0.0.0.0 --port 8000`
  - 创建 `docker-compose.yml`:
    - service 名 `api`
    - 端口 `8000:8000`
    - `env_file: .env`
    - volume `./data:/app/data`
    - `restart: unless-stopped`
- 验证:
  - `docker compose build`
  - `docker compose run --rm api python -c "import nettriage"`
  - `docker compose up -d`
  - `curl http://127.0.0.1:8000/healthz`

### Step 46: 编写 README 与运行说明

- **scope: auto**
- 操作:
  - 创建或更新 `README.md`。
  - 内容必须包含:
    - 项目简介
    - 技术栈
    - 本地启动
    - `.env` 配置说明
    - 单条分类 API 示例
    - CSV 批处理 API 示例
    - Docker 部署
    - 测试命令
    - 常见问题
  - 不在 README 中写入真实 API key。
- 验证:
  - `grep -n "DeepSeek" README.md`
  - `grep -n "docker compose" README.md`

### Step 47: 最终质量门禁

- **scope: review**
- 操作:
  - 执行完整质量检查:
    - `uv run ruff check .`
    - `uv run mypy src`
    - `uv run pytest --cov=nettriage`
  - 确保:
    - 所有测试通过。
    - 不调用真实 DeepSeek API 的测试默认可离线运行。
    - API 可本地启动。
    - Docker 可构建。
    - CSV E2E 流程可跑通。
  - 更新 `docs/report.md`:
    - STATUS 改为 `COMPLETED` 或 `NEEDS_REVIEW`。
    - 记录测试命令与结果。
    - 记录未解决问题。
- 验证:
  - `uv run ruff check . && uv run mypy src && uv run pytest --cov=nettriage`
  - `docker compose build`

---

## 计划质量自检

1. 随机抽查 Step 30：已明确文件 `src/nettriage/services/classification_service.py`、类 `ClassificationService`、方法 `classify_text`、依赖对象、固定流程和验证命令，可直接编码。
2. `scope:auto` 步骤均为工程搭建、模型定义、CRUD、单元测试或确定性实现，无技术选型空间。
3. `scope:review` 步骤集中在 Prompt、DeepSeek API、核心服务编排、CSV 批处理和最终质量门禁，存在复杂度但路径清晰。
4. 没有 `scope:escalate`；v1 决策已锁定，无需执行中等待架构侧。
5. 每个 Step 均有验证命令。
6. 依赖顺序满足：Schema → DB/Rules/LLM → Service → Batch/API → E2E/Deploy。
