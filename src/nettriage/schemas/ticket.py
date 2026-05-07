"""工单查询与复核 Schema — Module C Step 13."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from nettriage.schemas.enums import FaultCategory, ReviewStatus


class TicketRecordResponse(BaseModel):
    """工单记录响应模型（镜像 TicketRecord DB 表字段）。"""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., description="记录主键 ID")
    ticket_id: str | None = Field(default=None, description="工单编号")
    batch_id: str | None = Field(default=None, description="批次编号")
    description_hash: str = Field(..., description="描述文本 SHA-256")
    description_text: str = Field(..., description="故障描述原文")
    primary_category: str | None = Field(default=None, description="主分类")
    secondary_categories_json: str = Field(..., description="次分类 JSON")
    confidence: float = Field(..., description="置信度")
    category_scores_json: str = Field(..., description="分类得分 JSON")
    key_symptoms_json: str = Field(..., description="关键症状 JSON")
    summary: str = Field(..., description="故障摘要")
    troubleshooting_steps_json: str = Field(..., description="排查步骤 JSON")
    review_required: bool = Field(..., description="是否需要复核")
    review_status: str = Field(..., description="复核状态")
    review_reasons_json: str = Field(..., description="复核原因 JSON")
    reviewed_category: str | None = Field(default=None, description="复核后分类")
    review_note: str | None = Field(default=None, description="复核备注")
    llm_model: str | None = Field(default=None, description="LLM 模型名")
    llm_raw_output: str | None = Field(default=None, description="LLM 原始输出")
    llm_latency_ms: float | None = Field(default=None, description="LLM 耗时（毫秒）")
    fallback_used: bool = Field(..., description="是否规则兜底")
    error: str | None = Field(default=None, description="处理错误")
    source: str | None = Field(default=None, description="数据来源")
    customer_region: str | None = Field(default=None, description="客户区域")
    created_at: datetime = Field(..., description="创建时间")
    processed_at: datetime | None = Field(default=None, description="处理完成时间")


class TicketQueryFilters(BaseModel):
    """工单查询过滤参数。"""

    primary_category: FaultCategory | None = Field(default=None, description="按主分类筛选")
    review_required: bool | None = Field(default=None, description="按复核需求筛选")
    batch_id: str | None = Field(default=None, description="按批次筛选")
    keyword: str | None = Field(default=None, description="按关键词搜索（描述/摘要）")
    limit: int = Field(default=50, ge=1, le=1000, description="每页条数")
    offset: int = Field(default=0, ge=0, description="偏移量")


class ReviewUpdateRequest(BaseModel):
    """人工复核更新请求。"""

    review_status: ReviewStatus = Field(..., description="复核状态")
    reviewed_category: FaultCategory | None = Field(
        default=None, description="人工修正后的分类"
    )
    review_note: str | None = Field(
        default=None, max_length=500, description="复核备注"
    )


class ReviewUpdateResponse(BaseModel):
    """人工复核更新响应。"""

    record_id: int = Field(..., description="记录 ID")
    review_status: ReviewStatus = Field(..., description="更新后的复核状态")
    reviewed_category: FaultCategory | None = Field(default=None, description="修正后分类")
    review_note: str | None = Field(default=None, description="复核备注")
    updated_at: datetime = Field(..., description="更新时间")
