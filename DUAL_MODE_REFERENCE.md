# CrashSight OpenAPI 双模调用参考

每个接口支持两种等价调用方式：

| | 脚本方式 | SDK 方式 |
|---|---|---|
| **鉴权** | 手动生成签名拼 URL | 自动处理 |
| **参数** | 原始 camelCase JSON body | Python snake_case 关键字参数 |
| **响应** | 原始 `{ret: {data: ...}}` | 已解包，直接返回 `data` 内容 |
| **错误** | 需自行判断 `code != 200` | 自动抛出 `CrashSightAPIError` |
| **适用场景** | 非 Python 环境、调试、直接对接 HTTP | Python 项目主力调用方式 |

---

## 公共设置

### 脚本方式（通用）

```python
import requests, time, base64, hmac, hashlib

LOCAL_USER_ID    = "your_user_id"
USER_OPENAPI_KEY = "your_api_key"
BASE_URL         = "https://crashsight.qq.com"   # 新加坡用 crashsight.wetest.net

HEADERS = {"Content-Type": "application/json", "Accept-Encoding": "*"}

def _sign():
    t = int(time.time())
    msg = f"{LOCAL_USER_ID}_{t}"
    h = hmac.new(USER_OPENAPI_KEY.encode(), msg.encode(), hashlib.sha256).hexdigest()
    sig = base64.b64encode(h.encode()).decode()
    return sig, t, LOCAL_USER_ID

def post(path, body):
    """POST 请求：签名附在 query string"""
    sig, t, uid = _sign()
    url = f"{BASE_URL}{path}?userSecret={sig}&localUserId={uid}&t={t}"
    resp = requests.post(url, json=body,
                         headers=HEADERS, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    if "ret" in data and isinstance(data["ret"], dict):
        return data["ret"].get("data", data["ret"])
    return data.get("data", data)

def get(path_with_query):
    """旧式 GET：URL 已含 ?param=v，签名用 & 追加"""
    sig, t, uid = _sign()
    url = f"{BASE_URL}{path_with_query}&userSecret={sig}&localUserId={uid}&t={t}"
    return requests.get(url, headers=HEADERS, timeout=30).json()
```

### SDK 方式（初始化一次全局复用）

```python
from crashsight import CrashSightClient, Platform, CrashType, VmType, IssueStatus

client = CrashSightClient(
    user_id="your_user_id",
    api_key="your_api_key",
    region="cn",      # "cn" 国内  |  "sg" 新加坡
    timeout=30,
)
```

---

## 调用示例（以三个典型接口展示规律）

### 示例 1 — POST 接口，返回列表

`getTrendEx` / `get_trend`

```python
# ── 脚本 ────────────────────────────────────────────────────
result = post("/uniform/openapi/getTrendEx", {
    "appId":      "c5f3c55bbe",
    "platformId": 10,               # 1=Android  2=iOS  10=PC
    "type":       "crash",          # "crash" | "anr" | "error"
    "dataType":   "trendData",      # 固定值
    "vm":         0,                # 0=全部  1=真机  2=模拟器
    "startDate":  "20260323",
    "endDate":    "20260329",
    "version":    "-1",
    "mergeMultipleVersionsWithInaccurateResult": False,
    "needCountryDimension": False,
    "countryList": [],
})

# ── SDK ─────────────────────────────────────────────────────
result = client.get_trend(
    app_id="c5f3c55bbe",
    platform=Platform.PC,
    start_date="20260323",
    end_date="20260329",
    crash_type=CrashType.CRASH,
    version="-1",
)

# 返回值（两种方式相同）：
# List[{"appId", "platformId", "version", "date", "crashNum",
#        "crashUser", "accessNum", "accessUser", "crashRate", ...}]
```

---

### 示例 2 — 需要 issue_id 的级联查询

`issueInfo` + `lastCrashInfo` + `crashDoc`

```python
# ── 脚本 ────────────────────────────────────────────────────
issue = post("/uniform/openapi/issueInfo", {
    "appId": "c5f3c55bbe",  "platformId": "10",  # 注意：字符串
    "issueId": "4f158c6cedf7f687add95a876b626e40",
    "fsn": "any-unique-id",
})

last = post("/uniform/openapi/lastCrashInfo", {
    "appId": "c5f3c55bbe",  "platformId": "10",
    "issues": "4f158c6cedf7f687add95a876b626e40",
    "crashDataType": "undefined",  "fsn": "any-unique-id",
})
crash_id   = last["crashId"]
crash_hash = ":".join(crash_id[i:i+2] for i in range(0, len(crash_id), 2))

doc = post("/uniform/openapi/crashDoc", {
    "appId": "c5f3c55bbe",  "platformId": "10",
    "crashHash": crash_hash,  "fsn": "any-unique-id",
})

# ── SDK ─────────────────────────────────────────────────────
import time
issue_id = "4f158c6cedf7f687add95a876b626e40"

issue = client.get_issue_info("c5f3c55bbe", Platform.PC, issue_id);  time.sleep(2.5)
last  = client.get_last_crash("c5f3c55bbe", Platform.PC, issue_id);  time.sleep(2.5)
crash_id   = last["crashId"]
crash_hash = ":".join(crash_id[i:i+2] for i in range(0, len(crash_id), 2))
doc   = client.get_crash_doc("c5f3c55bbe", Platform.PC, crash_hash)

print(doc["crashMap"].get("keyStack"))
```

---

### 示例 3 — GET 旧式接口（路径参数）

`noteList`（GET），签名追在 `?` 参数后面用 `&`

```python
# ── 脚本 ────────────────────────────────────────────────────
result = get(
    f"/uniform/openapi/noteList"
    f"/appId/c5f3c55bbe/platformId/10/issueId/4f158c6cedf7f687..."
    f"?crashDataType=undefined&fsn=some-uuid"
)

# ── SDK ─────────────────────────────────────────────────────
result = client.get_issue_notes(
    app_id="c5f3c55bbe",
    platform=Platform.PC,
    issue_id="4f158c6cedf7f687...",
)
```

---

## 错误处理（SDK）

```python
from crashsight.exceptions import (
    CrashSightAPIError,
    CrashSightAuthError,
    CrashSightRateLimitError,
)

try:
    data = client.get_trend(...)
except CrashSightAuthError:
    print("鉴权失败，检查 user_id 和 api_key")
except CrashSightRateLimitError:
    time.sleep(5)   # 25次/分钟限制，等待后重试
except CrashSightAPIError as e:
    print(f"业务错误: {e.message}  code={e.status_code}  traceId={e.trace_id}")
```

---

## 注意事项

| 接口 / 场景 | 说明 |
|---|---|
| 频率限制 | 同一用户所有接口合计 **25 次/分钟** |
| `platformId` 类型 | `issueInfo`、`lastCrashInfo`、`crashDoc`、`appDetailCrash` 的 `platformId` 传字符串；SDK 已自动处理 |
| `getMinuteCrashData` | 响应慢（>30s），建议 `CrashSightClient(timeout=120)` |
| `getNetworkDevices` | 偶发响应慢，建议 `timeout=60` |
| 移动端专用 | `getNetworkDevices`、`getCrashDeviceInfo`、`getDeviceUserInfo` 等仅支持 `platformId=1/2` |
| App 级鉴权 | `getStackCrashStat`、`getCrashDeviceStat`、`getStackDeviceInfo`、`getCrashDeviceInfoByExpUid` 需 `appSecret/X-token`，HMAC 用户鉴权不适用 |

---
