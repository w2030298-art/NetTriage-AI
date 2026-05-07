"""分类请求、LLM 输出与业务结果模型 — Module C Step 11."""

from __future__ import annotations

from pydantic import BaseModel, Field

from nettriage.schemas.enums import FaultCategory


class ClassifyRequest(BaseModel):
    """单条分类请求模型。"""

    description: str = Field(
        ..., min_length=1, max_length=4000, description="故障描述文本"
    )
    ticket_id: str | None = Field(default=None, description="工单编号")
    source: str | None = Field(default=None, description="数据来源")
    customer_region: str | None = Field(default=None, description="客户所属区域")


class LLMClassificationOutput(BaseModel):
    """LLM 分类输出模型（经校验器校验后使用）。"""

    primary_category: FaultCategory = Field(..., description="主分类")
    secondary_categories: list[FaultCategory] = Field(
        default_factory=list, description="次分类列表"
    )
    confidence: float = Field(..., ge=0.0, le=1.0, description="置信度")
    category_scores: dict[str, float] = Field(
        default_factory=dict, description="各类别得分"
    )
    key_symptoms: list[str] = Field(default_factory=list, description="关键症状")
    summary: str = Field(..., max_length=500, description="故障摘要")
    troubleshooting_steps: list[str] = Field(
        ..., min_length=1, max_length=8, description="排查步骤（1-8条）"
    )


class ClassificationResult(LLMClassificationOutput):
    """完整分类结果模型（LLM 输出 + 复核 + 元数据）。"""

    review_required: bool = Field(..., description="是否需要人工复核")
    review_reasons: list[str] = Field(default_factory=list, description="复核原因列表")
    llm_model: str | None = Field(default=None, description="LLM 模型标识")
    llm_raw_output: str | None = Field(default=None, description="LLM 原始输出")
    llm_latency_ms: float | None = Field(default=None, description="LLM 调用耗时（毫秒）")
    fallback_used: bool = Field(default=False, description="是否使用了规则兜底")
    error: str | None = Field(default=None, description="处理错误信息")
    ticket_id: str | None = Field(default=None, description="工单编号")
    batch_id: str | None = Field(default=None, description="批次编号")
    source: str | None = Field(default=None, description="数据来源")
    customer_region: str | None = Field(default=None, description="客户所属区域")


class ClassifyResponse(ClassificationResult):
    """单条分类 API 响应模型。"""

    record_id: int = Field(..., description="数据库记录 ID")
    processed_at: str = Field(..., description="处理时间（ISO 格式）")
