# CrashSight Python SDK

CrashSight OpenAPI 的 Python 封装，提供类型安全的方法调用、自动签名鉴权、统一错误处理。

## 安装

### 从 GitHub 安装

```bash
pip install "git+https://github.com/TencentCrashSight/crashsight-python-sdk.git"
```

指定版本安装：

```bash
pip install "git+https://github.com/TencentCrashSight/crashsight-python-sdk.git@v2.0.0"
```

### 本地源码安装

```bash
pip install .
```

安装完成后可直接导入 `crashsight`。

---

## 快速开始

```python
from crashsight import CrashSightClient, Platform, CrashType, IssueStatus, VmType

client = CrashSightClient(
    user_id="your_user_id",       # CrashSight 个人设置 → localUserId
    api_key="your_api_key",        # CrashSight 个人设置 → userOpenapiKey
    region="cn",                   # "cn"（国内）或 "sg"（新加坡）
    timeout=30,                    # 请求超时秒数，getMinuteCrashData 建议设 120
)
```

> **频率限制**：同一用户所有接口合计 25 次/分钟。SDK 不自动限速，请自行控制调用频率。

---

## 枚举类型

```python
from crashsight import Platform, CrashType, VmType, IssueStatus

Platform.ANDROID   # 1
Platform.IOS       # 2
Platform.PC        # 10

CrashType.CRASH    # "crash"
CrashType.ANR      # "anr"
CrashType.ERROR    # "error"

VmType.ALL         # 0  全部设备
VmType.REAL_DEVICE # 1  真机
VmType.EMULATOR    # 2  模拟器

IssueStatus.UNPROCESSED  # 0  未处理
IssueStatus.PROCESSING   # 1  处理中
IssueStatus.PROCESSED    # 2  已处理
IssueStatus.REOPENED     # 3  重新打开
```

---

## 接口分组

- [趋势统计](#趋势统计)
- [问题管理](#问题管理)
- [异常分析](#异常分析)
- [用户与设备](#用户与设备)
- [附件管理](#附件管理)
- [选择器与元数据](#选择器与元数据)

---

## 趋势统计

### `get_trend` — 获取趋势数据（最近N天）

按日期范围查询崩溃/ANR/错误每日趋势。

```python
data = client.get_trend(
    app_id="c5f3c55bbe",
    platform=Platform.PC,
    start_date="20260323",          # YYYYMMDD
    end_date="20260329",
    crash_type=CrashType.CRASH,     # 默认 CRASH
    version="-1",                   # -1=全版本，支持通配符
    vm=VmType.ALL,                  # 设备类型过滤
    need_country=False,
    country_list=[],
    merge_versions=True,
)
# 返回 List[dict]，每项：
# {"appId", "platformId", "version", "date", "crashNum", "crashUser",
#  "accessNum", "accessUser", "crashRate", "country", ...}
```

---

### `get_dimension_top_stats` — 崩溃排行榜

按设备型号 / 系统版本 / 应用版本维度排行。

```python
data = client.get_dimension_top_stats(
    app_id="c5f3c55bbe",
    platform=Platform.PC,
    version="-1",
    min_date="20260323",
    max_date="20260329",
    crash_type=CrashType.CRASH,
    field="model",          # "model" | "osVersion" | "version"
    limit=20,
)
# 返回 List[dict]
```

---

### `get_daily_summary` — 日级精简统计

获取 crash/anr/error/oom/jank/hang 全类型汇总。

```python
data = client.get_daily_summary(
    app_id="c5f3c55bbe",
    platform=Platform.PC,
    start_date="20260323",
    end_date="20260329",
    version="-1",
)
# 返回 List[dict]，每项：
# {"appId", "platformId", "version", "date", "accessNum",
#  "crashNum", "anrNum", "errorNum", "oomNum", "jankNum", ...}
```

---

### `get_realtime_trend_append` — 今日累计趋势

获取指定日期逐小时累计的实时趋势。

```python
data = client.get_realtime_trend_append(
    app_id="c5f3c55bbe",
    platform=Platform.PC,
    date="20260330",        # 当天日期 YYYYMMDD
    version="-1",
    crash_type=CrashType.CRASH,
)
# 返回 List[dict]，每项含当前小时累计值
```

---

### `get_hourly_trend` — 小时粒度趋势

```python
data = client.get_hourly_trend(
    app_id="c5f3c55bbe",
    platform=Platform.PC,
    start_hour="2026032300",    # YYYYMMDDHH
    end_hour="2026032923",
    version="-1",
    crash_type=CrashType.CRASH,
)
```

---

### `get_hourly_top_issues` — 小时级 TOP 问题

```python
data = client.get_hourly_top_issues(
    app_id="c5f3c55bbe",
    platform=Platform.PC,
    start_hour="2026033000",
    limit=5,
    crash_type=CrashType.CRASH,
)
# 返回 dict：{"topIssueList": [...], "crashNum": int, "crashDevices": int, ...}
```

---

### `get_minute_crash_data` — 分钟级崩溃数据

> ⚠️ 仅部分项目支持。响应时间较长（可能超 30 秒），建议设置 `timeout=120`。

```python
client = CrashSightClient(..., timeout=120)

data = client.get_minute_crash_data(
    app_id="c5f3c55bbe",
    start_time="2026-03-23 00:00:00",   # YYYY-MM-DD HH:MM:SS
    end_time="2026-03-29 23:59:59",
    product_version="-1",
    limit=10,
)
```

---

## 问题管理

### `get_issue_list` — 获取问题列表

```python
result = client.get_issue_list(
    app_id="c5f3c55bbe",
    platform=Platform.PC,
    exception_type_list="Crash,Native,ExtensionCrash",
    # ANR:  "ANR"
    # 错误: "AllCatched,Unity3D,Lua,JS"
    rows=20,
    sort_field="uploadTime",
    sort_order="desc",
    status="0,2",       # 0=未处理, 1=已处理, 2=处理中，多选逗号分隔
    version="1.2.*",    # 支持通配符
)
# 返回 dict：{"numFound": int, "issueList": [{"issueId", "exceptionName", ...}]}

issue_id = result["issueList"][0]["issueId"]
```

---

### `get_top_issues` — TOP 问题列表

```python
result = client.get_top_issues(
    app_id="c5f3c55bbe",
    platform=Platform.PC,
    min_date="20260323",
    max_date="20260329",
    version="-1",
    crash_type=CrashType.CRASH,
    limit=20,
    top_issue_data_type="unSystemExit",   # "SystemExit" | "unSystemExit"
)
# 返回 dict：{"topIssueList": [...], "crashNum": int, ...}
```

---

### `get_issue_info` — issue 详情

```python
detail = client.get_issue_info(
    app_id="c5f3c55bbe",
    platform=Platform.PC,
    issue_id="4f158c6cedf7f687add95a876b626e40",
)
# 返回 dict：{"issueId", "exceptionName", "exceptionMessage", "keyStack",
#             "imeiCount", "uploadCount", "status", "processor", ...}
```

---

### `get_issue_notes` — issue 备注列表

```python
notes = client.get_issue_notes(
    app_id="c5f3c55bbe",
    platform=Platform.PC,
    issue_id="4f158c6cedf7f687add95a876b626e40",
)
```

---

### `get_issue_trend` — 问题趋势

```python
trend = client.get_issue_trend(
    app_id="c5f3c55bbe",
    platform=Platform.PC,
    issue_ids="4f158c6cedf7f687add95a876b626e40",  # 或 List[str]
    min_date="2026-03-23 00:00:00",
    max_date="2026-03-29 23:59:59",
    granularity_unit="DAY",     # "DAY" | "HOUR"
)
# 返回 List[{"issueId": str, "trendList": [{"date", "uploadCount", "imeiCount"}]}]
```

---

### `update_issue_status` — 更新 issue 状态

```python
ok = client.update_issue_status(
    app_id="7991094486",
    platform=Platform.ANDROID,
    issue_ids="56CF93B6F943A0633B4C9A9677977BBB",   # 多个用逗号分隔
    status=IssueStatus.PROCESSING,
    processors="user123",   # 处理人 userId
    note="已复现，正在定位",
)
# 返回 True 表示成功
```

---

### `add_issue_note` — 添加备注

```python
ok = client.add_issue_note(
    app_id="7991094486",
    platform=Platform.ANDROID,
    issue_id="56CF93B6F943A0633B4C9A9677977BBB",
    note="确认是 OOM 导致，下版本修复",
)
```

---

### `add_issue_tag` — 设置标签

```python
result = client.add_issue_tag(
    app_id="7991094486",
    platform=Platform.ANDROID,
    issue_id="56CF93B6F943A0633B4C9A9677977BBB",
    tag_name="待修复",
)
```

---

### `upsert_bugs` / `query_bugs` / `bind_bugs` — 缺陷单

```python
# 查询/创建 TAPD 缺陷单
result = client.upsert_bugs(
    app_id="7991094486",
    platform=Platform.ANDROID,
    issue_id="56CF93B6F943A0633B4C9A9677977BBB",
    issue_list=[...],
)

# 查询已有缺陷单详情
bugs = client.query_bugs(
    app_id="7991094486",
    platform=Platform.ANDROID,
    bug_infos=[{"bugPlatform": "TAPD", "id": "1234567890"}],
)

# 绑定外部缺陷单
ok = client.bind_bugs(
    app_id="7991094486",
    platform=Platform.ANDROID,
    issue_id="56CF93B6F943A0633B4C9A9677977BBB",
    bug_id="1234567890",
    bug_url="https://tapd.woa.com/projects/.../bugs/view/1234567890",
)
```

---

## 异常分析

### 典型用法：从 issue 到崩溃详情的完整链路

```python
# Step 1: 找 issue
issues = client.get_issue_list(app_id, Platform.PC, rows=5)
issue_id = issues["issueList"][0]["issueId"]

# Step 2: 获取最近一次 crash
last = client.get_last_crash(app_id, Platform.PC, issue_id)
crash_id = last["crashId"]
crash_hash = ":".join(crash_id[i:i+2] for i in range(0, len(crash_id), 2))

# Step 3a: 崩溃堆栈
doc = client.get_crash_doc(app_id, Platform.PC, crash_hash)
stack = doc["crashMap"]          # 堆栈信息
print(stack.get("keyStack", ""))

# Step 3b: 附件、日志、KV
detail = client.get_crash_detail(app_id, Platform.PC, crash_hash)
attach_list = detail.get("attachList", [])   # 附件列表（含下载链接）
sys_logs = detail.get("sysLogs", "")
```

---

### `get_crash_list` — crashHash 列表

```python
result = client.get_crash_list(
    app_id="c5f3c55bbe",
    platform=Platform.PC,
    issue_id="4f158c6cedf7f687add95a876b626e40",
    start=0,
    rows=50,
    exception_type_list="Crash,Native,ExtensionCrash",
)
# 返回 dict：{"numFound": int, "crashDatas": {"hash": {...}}}
```

---

### `query_crash_list` — 按条件搜索上报

```python
result = client.query_crash_list(
    app_id="c5f3c55bbe",
    platform=Platform.PC,
    crash_type=CrashType.CRASH,
    start_date="20260323",
    end_date="20260329",
    rows=50,
    keyword="RuntimeException",     # 堆栈关键字（可选）
    version="1.2.3",                # 版本过滤（可选）
    user_id="openid_xxx",           # 用户过滤（可选）
)
```

---

### `advanced_search` — 自定义检索

```python
result = client.advanced_search(
    app_id="c5f3c55bbe",
    platform=Platform.PC,
    start_hour="2026032300",
    end_hour="2026032923",
    crash_type=CrashType.CRASH,
    version="-1",
)
```

---

## 用户与设备

### `query_user_access_list` — 用户近 3 日上报查询

```python
import time
result = client.query_user_access_list(
    app_id="c5f3c55bbe",
    platform=Platform.PC,
    upload_time_begin_millis=int((time.time() - 3 * 86400) * 1000),
    device_id_list=["device_uuid_xxx"],     # 与 user_id_list 二选一
    # user_id_list=["openid_xxx"],
    page_size=1000,
)
```

---

### `get_crash_user_info` — 根据 openId 查崩溃

```python
result = client.get_crash_user_info(
    app_id="c5f3c55bbe",
    platform=Platform.PC,
    user_ids=["openid_xxx", "openid_yyy"],
    start_time="2026-03-23 00:00:00",
    end_time="2026-03-29 23:59:59",
    limit=100,
)
# 返回 dict：{"columns": [...], "values": [[...]], "results": [...]}
```

---

### `get_crash_user_list` — 崩溃用户列表

```python
result = client.get_crash_user_list(
    app_id="c5f3c55bbe",
    platform=Platform.PC,
    start_date="20260323",
    end_date="20260329",
    crash_type=CrashType.CRASH,
    version="-1",
)
```

---

### `get_most_report_users` — Top 上报用户

```python
result = client.get_most_report_users(
    app_id="c5f3c55bbe",
    versions=["-1"],                    # 全版本
    time_range_millis=7 * 86400 * 1000, # 最近 7 天
    exception_category="CRASH",
    limit=10,
)
# 返回 List[{"name", "total", "distinctCount", "bucketList"}]
```

---

### `get_network_devices` — 联网设备数据（仅移动端）

```python
result = client.get_network_devices(
    app_id="i1110543085",
    platform=Platform.IOS,              # 仅 ANDROID 或 IOS
    start_time="2026-03-23 00:00:00",
    end_time="2026-03-29 23:59:59",
)
```

---

### `get_crash_device_info` — issue 对应设备列表（移动端）

```python
result = client.get_crash_device_info(
    app_id="i1110543085",
    platform=Platform.IOS,
    issue_ids="BD341683D2DD69481F5A4C1CC82BBB79",  # 或 List[str]
    start_time="2026-03-23 00:00:00",
    end_time="2026-03-29 23:59:59",
    limit=500,
)
```

---

### `get_device_user_info` — 设备对应用户

```python
result = client.get_device_user_info(
    app_id="i1110543085",
    platform=Platform.IOS,
    device_id="device_uuid_xxx",
    start_time="2026-03-23 00:00:00",
    end_time="2026-03-29 23:59:59",
)
```

---

### 需要应用级鉴权的接口

> ⚠️ 以下 4 个接口使用 `appSecret/appId/X-token` 鉴权，**不支持**标准 `userSecret/localUserId` 鉴权。
> 需在 CrashSight 项目设置中获取应用密钥，并自行在请求头中设置 `X-token`。

- `get_stack_crash_stat` — 堆栈关键字崩溃统计
- `get_crash_device_stat` — deviceId 对应崩溃列表
- `get_stack_device_info` — 堆栈关键字对应机型列表
- `get_crash_device_info_by_exp_uid` — expUid 对应机型列表

---

## 附件管理

### `fetch_sdk_attachments` — SDK 直传附件

```python
result = client.fetch_sdk_attachments(
    app_id="c5f3c55bbe",
    crash_id_list=["a683c7563e19495dbb00263efdd0662c"],
    attachment_filename_list=["SDK_LOG"],   # 默认 SDK_LOG
)
# 返回 {"crashIdAndAttachmentsList": [{"crashId": str, "attachments": [...]}]}

for item in result.get("crashIdAndAttachmentsList", []):
    for att in item.get("attachments", []):
        print(att.get("downloadUrl"))   # 下载链接
```

---

### `fetch_crash_attachments` — 服务端附件

```python
result = client.fetch_crash_attachments(
    app_id="c5f3c55bbe",
    crash_id_list=["a683c7563e19495dbb00263efdd0662c"],
    attachment_filename_list=["extraMessage.txt"],  # 默认 extraMessage.txt
)
```

---

## 选择器与元数据

### `get_selector_data` — 获取版本/包名/处理人等

```python
result = client.get_selector_data(
    app_id="c5f3c55bbe",
    platform=Platform.PC,
    types="version,member,bundle,tag,channel",   # 逗号分隔，默认全部
)
# 返回 dict：
# {
#   "versionList": ["1.2.3", "1.2.4", ...],
#   "processorList": [{"userId": ..., "name": ...}, ...],
#   "bundleIdList": [...],
#   "tagList": [...],
#   "channelList": [...],
# }
```

---

### `get_version_date_list` — 版本首次出现日期

```python
result = client.get_version_date_list(
    app_id="c5f3c55bbe",
    platform=Platform.PC,
)
# 返回 {"columns": [...], "values": [["1.2.3", "20260101"], ...]}
```

---

## 错误处理

```python
from crashsight.exceptions import (
    CrashSightAPIError,      # 接口返回业务错误（code != 200）
    CrashSightAuthError,     # 鉴权失败（HTTP 401）
    CrashSightRateLimitError, # 频率超限（HTTP 429）
)

try:
    data = client.get_trend(app_id="xxx", platform=Platform.PC,
                            start_date="20260323", end_date="20260329")
except CrashSightAuthError:
    print("鉴权失败，检查 user_id 和 api_key")
except CrashSightRateLimitError:
    print("超过频率限制（25次/分钟），稍后重试")
except CrashSightAPIError as e:
    print(f"接口错误: {e.message}, code={e.status_code}, traceId={e.trace_id}")
```

---

## 完整使用示例

```python
from crashsight import CrashSightClient, Platform, CrashType, IssueStatus
import time

client = CrashSightClient(
    user_id="27528",
    api_key="your_api_key",
    region="cn",
)

APP_ID = "c5f3c55bbe"

# 1. 查看近一周趋势
trend = client.get_trend(APP_ID, Platform.PC, "20260323", "20260329")
for day in trend:
    print(f"{day['date']}: 崩溃 {day.get('crashNum', 0)} 次，影响 {day.get('crashUser', 0)} 设备")

# 2. 找出 TOP 问题
time.sleep(3)
top = client.get_top_issues(APP_ID, Platform.PC, "20260323", "20260329", limit=5)
for issue in top.get("topIssueList", []):
    print(f"{issue['issueId']}: {issue['exceptionName']} - {issue['imeiCount']} 设备")

# 3. 深入分析第一个问题
if top.get("topIssueList"):
    issue_id = top["topIssueList"][0]["issueId"]
    time.sleep(3)

    # 获取最近崩溃
    last = client.get_last_crash(APP_ID, Platform.PC, issue_id)
    crash_id = last["crashId"]
    crash_hash = ":".join(crash_id[i:i+2] for i in range(0, len(crash_id), 2))
    time.sleep(3)

    # 读取堆栈
    doc = client.get_crash_doc(APP_ID, Platform.PC, crash_hash)
    crash_map = doc.get("crashMap", {})
    print("堆栈:", crash_map.get("keyStack", "")[:200])
```
