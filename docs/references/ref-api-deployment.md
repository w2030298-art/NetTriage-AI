# ref-api-deployment.md

## 适用模块

- Module A: 工程骨架与基础依赖
- Module B: 配置、日志与基础安全
- Module I: FastAPI 路由与端到端 API
- Module J: 测试、样例数据、Docker 与交付文档

## API 设计纪律

1. API 层只做 HTTP 入参、依赖注入和响应封装。
2. API 层不得直接访问数据库。
3. API 层不得直接调用 DeepSeek。
4. 所有业务逻辑进入 service 层。
5. 错误响应统一为 `{ "error": { "code", "message", "details" } }`。
6. 查询接口必须支持 limit/offset，避免无界返回。

## v1 路由

- `GET /healthz`
- `POST /api/v1/classify`
- `POST /api/v1/batches`
- `GET /api/v1/batches/{batch_id}`
- `GET /api/v1/batches/{batch_id}/download`
- `GET /api/v1/tickets`
- `GET /api/v1/tickets/{record_id}`
- `PATCH /api/v1/tickets/{record_id}/review`
- `GET /`

## 部署纪律

1. Docker 镜像基于 Python 3.12 slim。
2. 容器内使用非 root 用户。
3. `./data` 必须挂载到容器 `/app/data`。
4. `.env` 不得提交真实 DeepSeek API key。
5. 公网访问时必须加 HTTPS 反向代理和基本访问控制。
6. 测试默认离线运行，不依赖真实 DeepSeek API。

## 参考来源

- FastAPI: https://fastapi.tiangolo.com/
- Uvicorn: https://www.uvicorn.org/
- Docker Compose: https://docs.docker.com/compose/
