"""批处理 Schema — Module C Step 12."""

from __future__ import annotations

from pydantic import BaseModel, Field

from nettriage.schemas.enums import BatchStatus, FaultCategory


class BatchCreateResponse(BaseModel):
    """批处理创建响应。"""

    batch_id: str = Field(..., description="批次唯一标识")
    status: BatchStatus = Field(..., description="批次状态")
    received_rows: int = Field(default=0, description="接收到的行数")
    message: str = Field(..., description="状态消息")


class BatchStatusResponse(BaseModel):
    """批处理状态查询响应。"""

    batch_id: str = Field(..., description="批次唯一标识")
    status: BatchStatus = Field(..., description="批次状态")
    total_rows: int = Field(..., description="总行数")
    processed_rows: int = Field(..., description="已处理行数")
    success_rows: int = Field(..., description="成功行数")
    failed_rows: int = Field(..., description="失败行数")
    review_required_rows: int = Field(..., description="需复核行数")
    created_at: str = Field(..., description="创建时间（ISO 格式）")
    completed_at: str | None = Field(default=None, description="完成时间（ISO 格式）")
    error_message: str | None = Field(default=None, description="错误消息")


class CSVFieldMapping(BaseModel):
    """CSV 字段映射配置。"""

    description_column: str = Field(..., description="描述字段列名")
    ticket_id_column: str | None = Field(default=None, description="工单编号列名")


class CSVRowResult(BaseModel):
    """CSV 单行处理结果。"""

    row_index: int = Field(..., description="行索引（0-based）")
    ticket_id: str | None = Field(default=None, description="工单编号")
    primary_category: FaultCategory | None = Field(default=None, description="主分类")
    success: bool = Field(..., description="是否处理成功")
    error: str | None = Field(default=None, description="错误信息")
