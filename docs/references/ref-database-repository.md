# ref-database-repository.md

## 适用模块

- Module D: SQLite 数据库与 Repository
- Module G: 核心分类服务与工单服务
- Module H: CSV 批处理

## SQLite v1 策略

SQLite 适合作为 v1 单云服务器、低到中等并发的持久化方案。必须通过 repository 层隔离，避免后续迁移 PostgreSQL 时影响 service/API 层。

## 必启 PRAGMA

```sql
PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;
PRAGMA busy_timeout=5000;
PRAGMA synchronous=NORMAL;
```

## 表设计重点

`TicketRecord` 必须保存：

- 原始描述与 `description_hash`
- LLM 原始输出
- 标准化分类结果
- 复核状态与复核备注
- batch 关联
- 错误摘要
- 处理时间与 LLM latency

`BatchJob` 必须保存：

- batch 状态
- 上传文件路径
- 导出文件路径
- total / processed / success / failed / review_required 计数
- started_at / completed_at

## 迁移触发条件

满足任一条件时进入 Iter：

1. 历史结果超过 100 万条且查询变慢。
2. 批处理任务并发超过 3 个。
3. 需要多台 API 实例同时写库。
4. 复核流程需要多人权限与审计。
5. 需要定时重跑 prompt 或批量评估准确率。

## 参考来源

- SQLModel: https://sqlmodel.tiangolo.com/
- SQLite PRAGMA: https://sqlite.org/pragma.html
