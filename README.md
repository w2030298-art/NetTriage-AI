# NetTriage AI

**网络故障工单智能分诊系统**

基于 DeepSeek API 的网络故障工单自动分类系统，支持单条实时分类、CSV 批量处理和人工复核工作流。

## 技术栈

| 层级 | 技术 |
|------|------|
| API 框架 | FastAPI 0.115+ |
| LLM | DeepSeek API (deepseek-chat) |
| 数据库 | SQLite (SQLModel ORM，预留 PostgreSQL) |
| 数据处理 | Pandas 2.x (CSV 分块读取) |
| 包管理 | uv |
| 类型检查 | mypy (strict mode) |
| 代码质量 | ruff |
| 测试 | pytest + pytest-asyncio + pytest-cov |
| 部署 | Docker + docker-compose |

## 快速开始

### 环境要求

- Python 3.12
- [uv](https://docs.astral.sh/uv/) (推荐) 或 pip

### 1. 克隆项目

```bash
git clone <repo-url>
cd NetTriage-AI
```

### 2. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env，填入你的 DEEPSEEK_API_KEY
```

关键配置项：

```bash
# DeepSeek LLM (必需)
DEEPSEEK_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxx

# 数据库 (默认 SQLite)
DATABASE_URL=sqlite:///./data/nettriage.db

# 文件上传限制
MAX_UPLOAD_MB=20
MAX_CSV_ROWS=50000
```

> 测试模式下不需要真实的 API Key，测试使用 FakeLLMClient。

### 3. 安装依赖

```bash
uv sync --extra dev
```

### 4. 启动服务

```bash
uv run uvicorn nettriage.api.main:app --host 127.0.0.1 --port 8000 --reload
```

访问：
- API 文档: http://127.0.0.1:8000/docs
- 上传页面: http://127.0.0.1:8000/
- 健康检查: http://127.0.0.1:8000/healthz

## API 示例

### 单条分类

```bash
curl -X POST http://127.0.0.1:8000/api/v1/classify \
  -H "Content-Type: application/json" \
  -d '{"description": "DNS无法解析，能ping通IP但域名访问失败"}'
```

响应：

```json
{
  "primary_category": "DNS_FAILURE",
  "secondary_categories": ["CONFIG_ERROR"],
  "confidence": 0.92,
  "review_required": false,
  "key_symptoms": ["dns resolve failure"],
  "summary": "DNS resolution failure despite reachable IP",
  "troubleshooting_steps": ["Check DNS server config", "Verify /etc/resolv.conf"],
  "llm_model": "deepseek-chat",
  "fallback_used": false
}
```

### CSV 批量处理

```bash
# 上传 CSV
curl -X POST http://127.0.0.1:8000/api/v1/batches \
  -F "file=@tests/fixtures/sample_tickets.csv"

# 响应
# {"batch_id": "batch_20260506_120000_abcdef12", "status": "PENDING", ...}

# 查询状态
curl http://127.0.0.1:8000/api/v1/batches/batch_20260506_120000_abcdef12

# 下载结果 (状态为 COMPLETED 时)
curl -O http://127.0.0.1:8000/api/v1/batches/batch_20260506_120000_abcdef12/download
```

### 工单查询与复核

```bash
# 查询工单列表
curl "http://127.0.0.1:8000/api/v1/tickets?review_required=true&limit=20"

# 更新复核状态
curl -X PATCH http://127.0.0.1:8000/api/v1/tickets/1/review \
  -H "Content-Type: application/json" \
  -d '{"review_status": "CONFIRMED", "review_note": "确认分类正确"}'
```

## 测试

```bash
# 运行全部测试 (不调用真实 DeepSeek API)
uv run pytest

# 带覆盖率报告
uv run pytest --cov=nettriage --cov-report=term-missing

# E2E 测试 (完整的 CSV 上传 -> 处理 -> 下载流程)
uv run pytest tests/e2e/test_csv_batch_flow.py -v

# Lint 检查
uv run ruff check .

# 类型检查
uv run mypy src

# 格式化
uv run ruff format .
```

## Docker 部署

```bash
# 构建镜像
docker compose build

# 启动服务
docker compose up -d

# 查看日志
docker compose logs -f

# 停止服务
docker compose down

# 验证
curl http://127.0.0.1:8000/healthz
```

## 项目结构

```
NetTriage-AI/
├── src/nettriage/
│   ├── api/              # FastAPI 路由 (classify, batches, tickets, ui)
│   │   ├── routes/
│   │   ├── dependencies.py
│   │   ├── errors.py
│   │   └── main.py       # 应用入口
│   ├── batch/            # CSV 批处理 (processor, exporter, field mapper)
│   ├── core/             # 配置、日志、安全
│   ├── db/               # SQLModel 表定义、数据库初始化
│   ├── llm/              # DeepSeek 客户端、Prompt、输出校验
│   ├── repositories/     # TicketRepository、BatchRepository
│   ├── rules/            # 规则引擎 (关键词分类、复核策略)
│   ├── schemas/          # Pydantic 请求/响应模型
│   └── services/         # 业务服务层 (分类、批次、工单、复核)
├── tests/
│   ├── e2e/              # 端到端测试
│   ├── fixtures/         # 测试用 CSV 样本
│   ├── integration/      # API 集成测试
│   └── unit/             # 单元测试
├── data/                 # 运行时数据 (uploads, exports, SQLite)
├── docs/                 # 开发计划与报告
├── Dockerfile
├── docker-compose.yml
└── pyproject.toml
```

## 故障分类类型

| 分类 | 说明 |
|------|------|
| DNS_FAILURE | DNS 解析故障 |
| AUTH_FAILURE | 认证失败 (PPPoE/RADIUS) |
| WEAK_SIGNAL | 弱信号/WiFi 信号差 |
| PACKET_LOSS | 网络丢包 |
| HIGH_LATENCY | 高延迟 |
| DROPPED_CONNECTION | 频繁断线 |
| CONFIG_ERROR | 配置错误 (VLAN/ACL/NAT) |
| DEVICE_FAILURE | 设备故障 (光猫/路由器) |
| SERVICE_OUTAGE | 大面积服务中断 |
| BANDWIDTH_DEGRADATION | 带宽下降 |
| CUSTOMER_PREMISES_ISSUE | 用户侧问题 |
| UNKNOWN | 无法分类 |

## 常见问题

**Q: 测试需要 DeepSeek API Key 吗？**
不需要。所有测试使用 FakeLLMClient 模拟，可以离线运行。

**Q: 如何切换为 PostgreSQL？**
修改 `.env` 中的 `DATABASE_URL` 为 PostgreSQL 连接串，系统通过 SQLModel 自动适配。

**Q: CSV 文件最大支持多少行？**
默认 50,000 行，可通过 `MAX_CSV_ROWS` 环境变量调整。
