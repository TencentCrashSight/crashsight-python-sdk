"""CrashSight OpenAPI 枚举定义。"""

from enum import IntEnum, Enum


class Platform(IntEnum):
    """平台类型。"""
    ANDROID = 1
    IOS = 2
    PC = 10


class CrashType(str, Enum):
    """异常类型。"""
    CRASH = "crash"
    ANR = "anr"
    ERROR = "error"


class VmType(IntEnum):
    """设备类型过滤。"""
    ALL = 0
    REAL_DEVICE = 1
    EMULATOR = 2


class IssueStatus(IntEnum):
    """问题状态。"""
    UNPROCESSED = 0   # 未处理
    PROCESSED = 1     # 已处理
    PROCESSING = 2    # 处理中


class Region(str, Enum):
    """部署区域。"""
    CN = "cn"
    SG = "sg"

    @property
    def base_url(self) -> str:
        return {
            Region.CN: "https://crashsight.qq.com",
            Region.SG: "https://crashsight.wetest.net",
        }[self]
