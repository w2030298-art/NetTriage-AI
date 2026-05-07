"""通用响应模型 — Module C Step 14."""

from __future__ import annotations

from typing import Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class ErrorEnvelope(BaseModel):
    """统一错误响应格式。"""

    error: ErrorDetail = Field(..., description="错误详情")


class ErrorDetail(BaseModel):
    """错误详情模型。"""

    code: str = Field(..., description="错误代码")
    message: str = Field(..., description="错误消息")


class PaginationMeta(BaseModel):
    """分页元信息。"""

    total: int = Field(..., description="总记录数")
    limit: int = Field(..., description="每页条数")
    offset: int = Field(..., description="偏移量")


class PaginatedResponse(BaseModel, Generic[T]):  # noqa: UP046
    """泛型分页响应。"""

    items: list[T] = Field(..., description="数据列表")
    pagination: PaginationMeta = Field(..., description="分页信息")
