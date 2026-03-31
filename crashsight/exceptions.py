"""CrashSight OpenAPI 异常定义。"""

from __future__ import annotations
from typing import Any, Optional


class CrashSightError(Exception):
    """CrashSight SDK 基础异常。"""


class CrashSightAPIError(CrashSightError):
    """API 调用返回错误时抛出。"""

    def __init__(
        self,
        message: str,
        status_code: Optional[int] = None,
        error_code: Optional[str] = None,
        trace_id: Optional[str] = None,
        raw_response: Optional[Any] = None,
    ):
        self.status_code = status_code
        self.error_code = error_code
        self.trace_id = trace_id
        self.raw_response = raw_response
        parts = [message]
        if status_code is not None:
            parts.append(f"status={status_code}")
        if error_code:
            parts.append(f"error_code={error_code}")
        if trace_id:
            parts.append(f"trace_id={trace_id}")
        super().__init__(" | ".join(parts))


class CrashSightAuthError(CrashSightError):
    """鉴权失败时抛出。"""


class CrashSightRateLimitError(CrashSightAPIError):
    """触发频率限制时抛出（25 次/分钟）。"""
