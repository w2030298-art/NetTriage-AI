# ref-llm-deepseek.md

## 适用模块

- Module F: DeepSeek LLM Client 与输出校验
- Module G: 核心分类服务与工单服务

## 实现要点

1. DeepSeek API 使用 OpenAI-compatible chat completions 风格封装。
2. v1 主链路采用 JSON Output，不采用 strict Function Calling beta。
3. 请求必须设置 `response_format={"type": "json_object"}`。
4. system prompt 必须包含 `JSON` / `json` 字样，并明确只返回合法 JSON。
5. user prompt 只拼接故障描述，不允许用户输入改变系统指令。
6. 模型原始输出必须保存到 `TicketRecord.llm_raw_output`。
7. 空 content、非法 JSON、Pydantic 校验失败都不能吞掉，必须映射成可复核业务结果。
8. 测试默认使用 `FakeLLMClient` 或 mock transport，不能调用真实 DeepSeek API。

## 错误策略

- 429 / 5xx: 指数退避重试，最多 `settings.deepseek_max_retries`。
- timeout: 抛 `LLMTimeoutError`。
- 空 content: 抛 `LLMEmptyResponseError`。
- JSON parse 失败: 抛 `LLMOutputParseError`。
- schema 校验失败: 抛 `LLMOutputValidationError`。
- 所有降级结果必须 `fallback_used=True` 且 `review_required=True`。

## 参考来源

- DeepSeek JSON Output: https://api-docs.deepseek.com/guides/json_mode
- DeepSeek Function Calling: https://api-docs.deepseek.com/guides/function_calling
- DeepSeek API Docs: https://api-docs.deepseek.com/
