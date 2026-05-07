# ref-classification-rules.md

## 适用模块

- Module C: Schema 与枚举模型
- Module E: 文本清洗、规则分类与复核策略
- Module G: 核心分类服务与工单服务

## v1 分类模型

v1 使用“单主类 + 多候选类”：

- `primary_category`: 必须有且只能有一个。
- `secondary_categories`: 可为空，用于表达次要可能性和冲突。
- `category_scores`: 用于判断 top1/top2 分差。
- `review_required`: 业务可信度控制位，不等同于模型是否成功。

## 分类枚举

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

## 复核规则

- `confidence < 0.80` → `REVIEW_LOW_CONFIDENCE`
- `top1_score - top2_score < 0.08` → `REVIEW_CATEGORY_CONFLICT`
- 信息不足 → `REVIEW_INSUFFICIENT_INFORMATION`
- LLM 主类与规则强命中主类不同 → `REVIEW_RULE_LLM_CONFLICT`
- fallback 被使用 → `REVIEW_FALLBACK_USED`
- LLM 输出非法 → `REVIEW_LLM_OUTPUT_INVALID`

## 实现纪律

1. `RuleBasedClassifier` 只做确定性关键词权重，不调用 LLM。
2. `ReviewPolicy` 只做决策，不写数据库。
3. `ClassificationService` 负责最终组装业务结果。
4. 规则层测试必须覆盖每个高频故障类别。
