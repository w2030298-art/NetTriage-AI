# ref-csv-batch.md

## 适用模块

- Module H: CSV 批处理
- Module I: FastAPI 路由与端到端 API
- Module J: 测试、样例数据、Docker 与交付文档

## CSV 输入策略

v1 内部标准字段：

- `ticket_id`
- `description`
- `created_at`
- `source`
- `customer_region`
- `priority`

只有 `description` 必须识别成功。缺少 description 字段时，整个 CSV 创建失败。

## 批处理边界

- 上传文件硬上限: 20 MB
- CSV 行数硬上限: 50,000
- 推荐单批规模: 10,000 行以内
- Pandas chunksize: 500
- 每行独立错误隔离
- 每个 chunk 后更新 batch 进度

## 实现纪律

1. 先把 `UploadFile` 复制到 `data/uploads/{batch_id}.csv`，再启动后台任务。
2. 禁止使用原始文件名作为落盘文件名。
3. 禁止一次性把全量 CSV 分类结果放入内存。
4. 单行失败写入结果 CSV 的 `error` 字段，不应让整个 batch 失败。
5. 系统性错误才将 batch 标记为 `FAILED`。
6. 下载接口只能从 `data/exports/{batch_id}.csv` 定位文件，不能接收任意路径。

## 参考来源

- FastAPI UploadFile: https://fastapi.tiangolo.com/tutorial/request-files/
- FastAPI BackgroundTasks: https://fastapi.tiangolo.com/tutorial/background-tasks/
- Pandas read_csv: https://pandas.pydata.org/docs/reference/api/pandas.read_csv.html
