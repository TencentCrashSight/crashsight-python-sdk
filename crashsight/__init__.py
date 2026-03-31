"""CrashSight OpenAPI Python SDK。

用法::

    from crashsight import CrashSightClient, Platform, CrashType

    client = CrashSightClient(
        user_id="your_user_id",
        api_key="your_api_key",
        region="cn",
    )
    data = client.get_trend(
        app_id="your_app_id",
        platform=Platform.ANDROID,
        start_date="20240301",
        end_date="20240327",
    )
"""

from .client import CrashSightClient
from .enums import CrashType, IssueStatus, Platform, Region, VmType
from .exceptions import (
    CrashSightAPIError,
    CrashSightAuthError,
    CrashSightError,
    CrashSightRateLimitError,
)

__version__ = "1.0.0"
__all__ = [
    "CrashSightClient",
    "Platform",
    "CrashType",
    "VmType",
    "IssueStatus",
    "Region",
    "CrashSightError",
    "CrashSightAPIError",
    "CrashSightAuthError",
    "CrashSightRateLimitError",
]
