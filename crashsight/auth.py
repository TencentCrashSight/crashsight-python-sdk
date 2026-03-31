"""CrashSight OpenAPI HMAC-SHA256 签名计算。"""

from __future__ import annotations

import base64
import hashlib
import hmac
import time


def compute_signature(user_id: str, api_key: str, timestamp: int | None = None) -> tuple[str, int]:
    """计算 OpenAPI 鉴权签名。

    签名算法: Base64(Hex(HMAC-SHA256(key=api_key, msg="{user_id}_{timestamp}")))

    Returns:
        (signature, timestamp) 元组
    """
    if timestamp is None:
        timestamp = int(time.time())
    message = f"{user_id}_{timestamp}"
    digest = hmac.new(
        api_key.encode("utf-8"),
        message.encode("utf-8"),
        digestmod=hashlib.sha256,
    ).hexdigest()
    signature = base64.b64encode(digest.encode("utf-8")).decode("utf-8")
    return signature, timestamp


def build_auth_params(user_id: str, api_key: str, timestamp: int | None = None) -> dict[str, str]:
    """构建鉴权查询参数字典。"""
    signature, ts = compute_signature(user_id, api_key, timestamp)
    return {
        "userSecret": signature,
        "localUserId": user_id,
        "t": str(ts),
    }
