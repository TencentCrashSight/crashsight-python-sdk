"""CrashSight OpenAPI Python SDK 客户端。

用法::

    from crashsight import CrashSightClient, Platform, CrashType

    client = CrashSightClient(
        user_id="27528",
        api_key="your-api-key",
        region="cn",
    )

    # 获取趋势数据
    data = client.get_trend(
        app_id="c5f3c55bbe",
        platform=Platform.PC,
        start_date="20240301",
        end_date="20240327",
        crash_type=CrashType.CRASH,
    )
"""

from __future__ import annotations

import json
import uuid
from typing import Any, Optional, Union
from urllib.parse import urlencode

import requests

from .auth import build_auth_params
from .enums import CrashType, IssueStatus, Platform, Region, VmType
from .exceptions import (
    CrashSightAPIError,
    CrashSightAuthError,
    CrashSightRateLimitError,
)

_DEFAULT_TIMEOUT = 30


class CrashSightClient:
    """CrashSight OpenAPI 统一客户端。

    Args:
        user_id: 用户 ID（localUserId），在 CrashSight 个人设置中获取。
        api_key: OpenAPI 密钥（userOpenapiKey），在 CrashSight 个人设置中获取。
        region: 部署区域，``"cn"`` 或 ``"sg"``。默认 ``"cn"``。
        timeout: 请求超时秒数，默认 30。
        base_url: 自定义基础 URL，设置后 region 参数将被忽略。
    """

    def __init__(
        self,
        user_id: str,
        api_key: str,
        region: str = "cn",
        timeout: int = _DEFAULT_TIMEOUT,
        base_url: str | None = None,
    ):
        self.user_id = user_id
        self.api_key = api_key
        self.timeout = timeout
        if base_url:
            self.base_url = base_url.rstrip("/")
        else:
            self.base_url = Region(region).base_url
        self._session = requests.Session()
        self._session.headers.update({
            "Content-Type": "application/json",
            "Accept-Encoding": "*",
        })

    # ── 内部请求方法 ───────────────────────────────────────────

    def _build_url(self, path: str, extra_params: dict[str, str] | None = None) -> str:
        auth = build_auth_params(self.user_id, self.api_key)
        params = {**auth, **(extra_params or {})}
        return f"{self.base_url}{path}?{urlencode(params)}"

    def _post(self, path: str, body: dict[str, Any]) -> Any:
        url = self._build_url(path)
        resp = self._session.post(url, json=body, timeout=self.timeout)
        return self._handle_response(resp)

    def _get(self, path: str, query: dict[str, Any] | None = None) -> Any:
        str_query = {k: str(v) for k, v in (query or {}).items()}
        url = self._build_url(path, extra_params=str_query)
        resp = self._session.get(url, timeout=self.timeout)
        return self._handle_response(resp)

    def _handle_response(self, resp: requests.Response) -> Any:
        if resp.status_code == 429:
            raise CrashSightRateLimitError(
                "频率限制：单用户各接口合计 25 次/分钟",
                status_code=429,
                raw_response=resp.text,
            )
        if resp.status_code == 401:
            raise CrashSightAuthError(f"鉴权失败: {resp.text}")

        try:
            data = resp.json()
        except ValueError:
            resp.raise_for_status()
            return resp.text

        if "error" in data and "path" in data and "timestamp" in data:
            raise CrashSightAPIError(
                message=data.get("message") or data.get("error", "Server error"),
                status_code=data.get("status"),
                raw_response=data,
            )

        status = data.get("status")
        ret = data.get("ret")

        if isinstance(ret, dict):
            code = ret.get("code")
            if code and code != 200:
                raise CrashSightAPIError(
                    message=ret.get("message", "Unknown error"),
                    status_code=code,
                    error_code=ret.get("errorCode"),
                    trace_id=ret.get("traceId"),
                    raw_response=data,
                )
            if "data" in ret:
                return ret["data"]
            return ret

        if "code" in data and data.get("code") not in (None, 200, 0):
            raise CrashSightAPIError(
                message=data.get("errmsg") or data.get("message", "Unknown error"),
                status_code=data.get("code"),
                raw_response=data,
            )

        if "data" in data and data["data"] is not None:
            return data["data"]
        return data

    @staticmethod
    def _fsn() -> str:
        return str(uuid.uuid4())

    @staticmethod
    def _to_platform_int(platform: Union[Platform, int]) -> int:
        return int(platform)

    @staticmethod
    def _to_crash_type(crash_type: Union[CrashType, str]) -> str:
        return str(crash_type.value) if isinstance(crash_type, CrashType) else str(crash_type)

    # ═══════════════════════════════════════════════════════════
    #  趋势统计
    # ═══════════════════════════════════════════════════════════

    def get_trend(
        self,
        app_id: str,
        platform: Union[Platform, int],
        start_date: str,
        end_date: str,
        crash_type: Union[CrashType, str] = CrashType.CRASH,
        version: str = "-1",
        vm: Union[VmType, int] = VmType.ALL,
        version_list: list[str] | None = None,
        need_country: bool = False,
        country_list: list[str] | None = None,
        merge_versions: bool = True,
        scene_tags: list[str] | None = None,
    ) -> Any:
        """获取趋势数据（最近 N 天）。

        Args:
            app_id: 项目 ID。
            platform: 平台类型。
            start_date: 开始日期，格式 ``YYYYMMDD``。
            end_date: 结束日期，格式 ``YYYYMMDD``。
            crash_type: 异常类型，默认 ``crash``。
            version: 版本号，``"-1"`` 代表全版本，支持通配符。
            vm: 设备类型过滤。
            version_list: 多版本列表（与 version 互斥）。
            need_country: 是否需要国家维度统计。
            country_list: 国家列表，空列表表示全部国家。
            merge_versions: 多版本结果是否合并。
            scene_tags: 场景标签筛选。
        """
        body: dict[str, Any] = {
            "appId": app_id,
            "platformId": self._to_platform_int(platform),
            "startDate": start_date,
            "endDate": end_date,
            "type": self._to_crash_type(crash_type),
            "dataType": "trendData",
            "vm": int(vm),
            "versionList": version_list or [version],
            "needCountryDimension": need_country,
            "countryList": country_list if country_list is not None else [],
            "mergeMultipleVersionsWithInaccurateResult": merge_versions,
        }
        if scene_tags:
            body["userSceneTagList"] = scene_tags
        return self._post("/uniform/openapi/getTrendEx", body)

    def get_dimension_top_stats(
        self,
        app_id: str,
        platform: Union[Platform, int],
        version: str,
        min_date: str,
        max_date: str,
        crash_type: Union[CrashType, str] = CrashType.CRASH,
        field: str = "model",
        limit: int = 20,
        merge_versions: bool = True,
        merge_dates: bool = True,
        sort_by_exception: bool = True,
        need_country: bool = False,
        country_list: list[str] | None = None,
    ) -> Any:
        """获取崩溃/ANR/错误排行榜。

        Args:
            field: 聚合维度 ``"model"``(设备) / ``"osVersion"``(系统版本) / ``"version"``(应用版本)。
            limit: 返回条数。
        """
        return self._post("/uniform/openapi/fetchDimensionTopStats", {
            "appId": app_id,
            "platformId": self._to_platform_int(platform),
            "version": version,
            "minDate": min_date,
            "maxDate": max_date,
            "type": self._to_crash_type(crash_type),
            "field": field,
            "limit": limit,
            "mergeMultipleVersionsWithInaccurateResult": merge_versions,
            "mergeMultipleDatesWithInaccurateResult": merge_dates,
            "sortByException": sort_by_exception,
            "needCountryDimension": "true" if need_country else "false",
            "countryList": country_list or [],
        })

    def get_daily_summary(
        self,
        app_id: str,
        platform: Union[Platform, int],
        start_date: str,
        end_date: str,
        version: str = "-1",
        query_all_vm_types: bool = False,
    ) -> Any:
        """获取日级精简统计数据（含 crash/anr/error/oom/jank/hang 等全类型）。

        Args:
            start_date: 开始日期，格式 ``YYYYMMDD``。
            end_date: 结束日期，格式 ``YYYYMMDD``。
        """
        return self._post("/uniform/openapi/fetchDailySummary", {
            "appId": app_id,
            "platformId": self._to_platform_int(platform),
            "version": version,
            "subModuleId": "-1",
            "startHour": f"{start_date}00",
            "endHour": f"{end_date}23",
            "queryAllVmTypes": query_all_vm_types,
        })

    def get_realtime_trend_append(
        self,
        app_id: str,
        platform: Union[Platform, int],
        date: str,
        version: str = "-1",
        crash_type: Union[CrashType, str] = CrashType.CRASH,
        vm: Union[VmType, int] = VmType.ALL,
        merge_versions: bool = False,
        need_country: bool = False,
        country_list: list[str] | None = None,
    ) -> Any:
        """获取今日累计趋势。

        Args:
            date: 日期，格式 ``YYYYMMDD``。
        """
        return self._post("/uniform/openapi/getAppRealTimeTrendAppendEx", {
            "appId": app_id,
            "platformId": self._to_platform_int(platform),
            "startDate": f"{date}00",
            "endDate": f"{date}23",
            "type": self._to_crash_type(crash_type),
            "dataType": "realTimeTrendData",
            "vm": int(vm),
            "version": version,
            "mergeMultipleVersionsWithInaccurateResult": merge_versions,
            "needCountryDimension": need_country,
            "countryList": country_list or [],
        })

    def get_hourly_trend(
        self,
        app_id: str,
        platform: Union[Platform, int],
        start_hour: str,
        end_hour: str,
        version: str = "-1",
        crash_type: Union[CrashType, str] = CrashType.CRASH,
        vm: Union[VmType, int] = VmType.ALL,
        merge_versions: bool = False,
        need_country: bool = False,
        country_list: list[str] | None = None,
    ) -> Any:
        """获取小时粒度趋势。

        Args:
            start_hour: 开始时间，格式 ``YYYYMMDDHH``。
            end_hour: 结束时间，格式 ``YYYYMMDDHH``。
        """
        return self._post("/uniform/openapi/getRealTimeHourlyStatEx", {
            "appId": app_id,
            "platformId": self._to_platform_int(platform),
            "startDate": start_hour,
            "endDate": end_hour,
            "version": version,
            "type": self._to_crash_type(crash_type),
            "dataType": "realTimeCompareData",
            "vm": int(vm),
            "mergeMultipleVersionsWithInaccurateResult": merge_versions,
            "needCountryDimension": need_country,
            "countryList": country_list or [],
        })

    def get_hourly_top_issues(
        self,
        app_id: str,
        platform: Union[Platform, int],
        start_hour: str,
        version: str = "-1",
        crash_type: Union[CrashType, str] = CrashType.CRASH,
        vm: Union[VmType, int] = VmType.ALL,
        limit: int = 5,
        country_list: list[str] | None = None,
    ) -> Any:
        """获取小时级 TOP 问题列表。

        Args:
            start_hour: 起始小时，格式 ``YYYYMMDDHH``。
            vm: 设备类型过滤。
            country_list: 国家列表。
        """
        return self._post("/uniform/openapi/getTopIssueHourly", {
            "appId": app_id,
            "platformId": self._to_platform_int(platform),
            "startHour": start_hour,
            "version": version,
            "type": self._to_crash_type(crash_type),
            "vm": int(vm),
            "limit": limit,
            "countryList": country_list or [],
        })

    def get_minute_crash_data(
        self,
        app_id: str,
        start_time: str,
        end_time: str,
        product_version: str = "-1",
        limit: int = 10,
    ) -> Any:
        """获取分钟级崩溃数据（仅部分项目支持）。

        Args:
            start_time: 格式 ``YYYY-MM-DD HH:MM:SS``。
            end_time: 格式 ``YYYY-MM-DD HH:MM:SS``。
            product_version: 版本号，``"-1"`` 表示全版本。
            limit: 返回条数。
        """
        return self._post("/uniform/openapi/getMinuteCrashData", {
            "appId": app_id,
            "stime": start_time,
            "etime": end_time,
            "product_version": product_version,
            "limit": limit,
        })

    # ═══════════════════════════════════════════════════════════
    #  问题管理
    # ═══════════════════════════════════════════════════════════

    def get_issue_list(
        self,
        app_id: str,
        platform: Union[Platform, int],
        exception_type_list: str = "Crash,Native,ExtensionCrash",
        rows: int = 20,
        sort_field: str = "uploadTime",
        sort_order: str = "desc",
        status: str = "",
        version: str = "",
        tapd_bug_status: str = "",
        issue_upload_time_relative_millis: int | None = None,
    ) -> Any:
        """获取崩溃/ANR/错误分析列表。

        Args:
            exception_type_list: 异常类型，逗号分隔。
                崩溃: ``"Crash,Native,ExtensionCrash"``
                ANR: ``"ANR"``
                错误: ``"AllCatched,Unity3D,Lua,JS"``
            status: 按状态过滤，``"0"``=未处理, ``"1"``=已处理, ``"2"``=处理中, 多选逗号分隔如 ``"0,2"``。
            version: 版本号，多版本分号分隔，支持通配符 ``*``。
            tapd_bug_status: ``"UNREPORTED"``(未关联) / ``"REPORTED"``(已关联)。
            issue_upload_time_relative_millis: 过滤最近 N 毫秒内有上报的问题(如 3600000=最近1小时)。
        """
        pid = self._to_platform_int(platform)
        body: dict[str, Any] = {
            "appId": app_id,
            "platformId": pid,
            "pid": str(pid),
            "exceptionTypeList": exception_type_list,
            "rows": rows,
            "sortField": sort_field,
            "sortOrder": sort_order,
            "skipQueryHbase": True,
        }
        if status:
            body["status"] = status
        if version:
            body["version"] = version
        if tapd_bug_status:
            body["tapdBugStatus"] = tapd_bug_status
        if issue_upload_time_relative_millis is not None:
            body["issueUploadTimeRelativeMillis"] = issue_upload_time_relative_millis
        return self._post("/uniform/openapi/queryIssueList", body)

    def get_top_issues(
        self,
        app_id: str,
        platform: Union[Platform, int],
        min_date: str,
        max_date: str,
        version: str = "-1",
        crash_type: Union[CrashType, str] = CrashType.CRASH,
        limit: int = 20,
        top_issue_data_type: str = "unSystemExit",
        merge_versions: bool = False,
        merge_dates: bool = False,
        version_list: list[str] | None = None,
        country_list: list[str] | None = None,
    ) -> Any:
        """获取 TOP 问题列表。

        Args:
            min_date: 日期范围起点，格式 ``YYYYMMDD``。
            max_date: 日期范围终点，格式 ``YYYYMMDD``。
            top_issue_data_type: ``"SystemExit"``(系统退出) / ``"unSystemExit"``(非系统退出)。
        """
        return self._post("/uniform/openapi/getTopIssueEx", {
            "appId": app_id,
            "platformId": self._to_platform_int(platform),
            "version": version,
            "date": min_date,
            "minDate": min_date,
            "maxDate": max_date,
            "type": self._to_crash_type(crash_type),
            "limit": limit,
            "topIssueDataType": top_issue_data_type,
            "mergeMultipleVersionsWithInaccurateResult": merge_versions,
            "mergeMultipleDatesWithInaccurateResult": merge_dates,
            "versionList": version_list or [version],
            "countryList": country_list or [],
        })

    def get_issue_info(
        self,
        app_id: str,
        platform: Union[Platform, int],
        issue_id: str,
    ) -> Any:
        """获取 issue 详情。"""
        return self._post("/uniform/openapi/issueInfo", {
            "appId": app_id,
            "platformId": self._to_platform_int(platform),
            "issueId": issue_id,
        })

    def get_issue_notes(
        self,
        app_id: str,
        platform: Union[Platform, int],
        issue_id: str,
        crash_data_type: str = "undefined",
    ) -> Any:
        """获取 issue 备注列表。"""
        pid = self._to_platform_int(platform)
        path = f"/uniform/openapi/noteList/appId/{app_id}/platformId/{pid}/issueId/{issue_id}"
        return self._get(path, {"crashDataType": crash_data_type})

    def get_issue_trend(
        self,
        app_id: str,
        platform: Union[Platform, int],
        issue_ids: list[str] | str,
        min_date: str,
        max_date: str,
        granularity_unit: str = "DAY",
        version: str = "-1",
    ) -> Any:
        """获取问题趋势。

        Args:
            issue_ids: 问题 ID 列表（或单个 ID 字符串）。
            min_date: 格式 ``YYYY-MM-DD HH:MM:SS``。
            max_date: 格式 ``YYYY-MM-DD HH:MM:SS``。
            granularity_unit: 聚合粒度 ``"DAY"`` 或 ``"HOUR"``。
        """
        ids = [issue_ids] if isinstance(issue_ids, str) else issue_ids
        return self._post("/uniform/openapi/queryIssueTrend", {
            "appId": app_id,
            "platformId": self._to_platform_int(platform),
            "issueIds": ids,
            "granularityUnit": granularity_unit,
            "minDate": min_date,
            "maxDate": max_date,
            "version": version,
        })

    def update_issue_status(
        self,
        app_id: str,
        platform: Union[Platform, int],
        issue_ids: str,
        status: Union[IssueStatus, int],
        processors: str = "",
        note: str = "",
        operator_user_id: str = "",
    ) -> Any:
        """更新 issue 状态。

        Args:
            issue_ids: 问题 ID（多个用逗号分隔）。
            status: 目标状态。
            processors: 处理人 ID。
            note: 备注。
            operator_user_id: 操作人 userId。
        """
        return self._post("/uniform/openapi/updateIssueStatus", {
            "appId": app_id,
            "platformId": self._to_platform_int(platform),
            "issueIds": issue_ids,
            "status": int(status),
            "processors": processors,
            "note": note,
            "newUserId": operator_user_id or self.user_id,
        })

    def add_issue_note(
        self,
        app_id: str,
        platform: Union[Platform, int],
        issue_id: str,
        note: str,
        operator_user_id: str = "",
    ) -> Any:
        """添加问题备注。"""
        import datetime
        uid = operator_user_id or self.user_id
        return self._post("/uniform/openapi/addIssueNote", {
            "appId": app_id,
            "platformId": self._to_platform_int(platform),
            "issueStatus": 3,
            "issueIds": issue_id,
            "note": note,
            "createTime": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "userId": uid,
            "newUserId": uid,
        })

    def add_issue_tag(
        self,
        app_id: str,
        platform: Union[Platform, int],
        issue_id: str,
        tag_name: str,
    ) -> Any:
        """设置问题级标签。"""
        return self._post("/uniform/openapi/addTag", {
            "appId": app_id,
            "platformId": self._to_platform_int(platform),
            "issueId": issue_id,
            "tagName": tag_name,
        })

    def upsert_bugs(
        self,
        app_id: str,
        platform: Union[Platform, int],
        issue_id: str,
        **kwargs: Any,
    ) -> Any:
        """查询/创建缺陷单。"""
        body = {
            "appId": app_id,
            "platformId": self._to_platform_int(platform),
            "issueId": issue_id,
            **kwargs,
        }
        return self._post("/uniform/openapi/upsertBugs", body)

    def query_bugs(
        self,
        app_id: str,
        platform: Union[Platform, int],
        bug_infos: list[dict[str, str]],
    ) -> Any:
        """查询缺陷单详情。

        Args:
            bug_infos: 缺陷单列表，每项含 ``bugPlatform``（如 ``"TAPD"``）和 ``id``。
                例如 ``[{"bugPlatform": "TAPD", "id": "12345"}]``。
        """
        return self._post("/uniform/openapi/queryBugs", {
            "appId": app_id,
            "platformId": self._to_platform_int(platform),
            "bugInfos": bug_infos,
        })

    def bind_bugs(
        self,
        app_id: str,
        platform: Union[Platform, int],
        issue_id: str,
        bug_id: str,
        bug_url: str,
    ) -> Any:
        """绑定缺陷单。"""
        return self._post("/uniform/openapi/bindBugs", {
            "appId": app_id,
            "platformId": self._to_platform_int(platform),
            "issueId": issue_id,
            "bugId": bug_id,
            "bugUrl": bug_url,
        })

    # ═══════════════════════════════════════════════════════════
    #  异常分析
    # ═══════════════════════════════════════════════════════════

    def get_crash_list(
        self,
        app_id: str,
        platform: Union[Platform, int],
        issue_id: str,
        start: int = 0,
        rows: int = 50,
        exception_type_list: str = "Crash,Native,ExtensionCrash",
        version: str = "",
    ) -> Any:
        """根据 issue 获取 crashHash 列表（支持 PC）。"""
        return self._post("/uniform/openapi/crashList", {
            "appId": app_id,
            "crashDataType": "undefined",
            "start": start,
            "searchType": "detail",
            "exceptionTypeList": exception_type_list,
            "pid": self._to_platform_int(platform),
            "platformId": self._to_platform_int(platform),
            "issueId": issue_id,
            "rows": rows,
            "version": version,
        })

    def get_last_crash(
        self,
        app_id: str,
        platform: Union[Platform, int],
        issue_id: str,
    ) -> Any:
        """获取最近一次 crashHash（支持 PC）。"""
        return self._post("/uniform/openapi/lastCrashInfo", {
            "appId": app_id,
            "platformId": str(self._to_platform_int(platform)),
            "issues": issue_id,
            "crashDataType": "undefined",
        })

    def get_crash_detail(
        self,
        app_id: str,
        platform: Union[Platform, int],
        crash_hash: str,
    ) -> Any:
        """获取跟踪数据、日志、自定义 KV。"""
        return self._post("/uniform/openapi/appDetailCrash", {
            "appId": app_id,
            "platformId": str(self._to_platform_int(platform)),
            "crashHash": crash_hash,
        })

    def get_crash_doc(
        self,
        app_id: str,
        platform: Union[Platform, int],
        crash_hash: str,
        logtype: str = "",
        need_custom_kv: bool = False,
    ) -> Any:
        """获取异常详情（崩溃堆栈、错误、ANR，支持 PC）。

        Args:
            crash_hash: 崩溃 Hash 值（crashId 每 2 位加 ``:`` 的规则生成）。
            logtype: 仅 PC 有效。``"interface"`` / ``"file"`` / ``"all"``。
            need_custom_kv: 是否返回自定义 KV。
        """
        return self._post("/uniform/openapi/crashDoc", {
            "appId": app_id,
            "platformId": str(self._to_platform_int(platform)),
            "crashHash": crash_hash,
            "logtype": logtype,
            "needQueryCustomKv": need_custom_kv,
        })

    def get_anr_message(
        self,
        app_id: str,
        platform: Union[Platform, int],
        crash_hash: str,
    ) -> Any:
        """获取 ANR message 及 ANR Trace。

        返回的 attachList 中筛选 fileName 为 ``anrMessage.txt`` 或 ``trace.zip``。
        """
        return self._post("/uniform/openapi/appDetailCrash", {
            "appId": app_id,
            "platformId": str(self._to_platform_int(platform)),
            "crashHash": crash_hash,
        })

    def query_crash_list(
        self,
        app_id: str,
        platform: Union[Platform, int],
        crash_type: Union[CrashType, str] = CrashType.CRASH,
        start: int = 0,
        rows: int = 50,
        version: str = "",
        start_date: str = "",
        end_date: str = "",
        model: str = "",
        os_version: str = "",
        keyword: str = "",
        user_id: str = "",
        device_id: str = "",
        crash_id: str = "",
    ) -> Any:
        """根据筛选条件拉取上报详情。"""
        body: dict[str, Any] = {
            "appId": app_id,
            "platformId": self._to_platform_int(platform),
            "type": self._to_crash_type(crash_type),
            "start": start,
            "rows": rows,
            "version": version,
            "startDate": start_date,
            "endDate": end_date,
        }
        if model:
            body["model"] = model
        if os_version:
            body["osVersion"] = os_version
        if keyword:
            body["keyword"] = keyword
        if user_id:
            body["userId"] = user_id
        if device_id:
            body["deviceId"] = device_id
        if crash_id:
            body["crashId"] = crash_id
        return self._post("/uniform/openapi/queryCrashList", body)

    def advanced_search(
        self,
        app_id: str,
        platform: Union[Platform, int],
        start_hour: str,
        end_hour: str,
        crash_type: Union[CrashType, str] = CrashType.CRASH,
        version: str = "-1",
        vm: Union[VmType, int] = VmType.ALL,
    ) -> Any:
        """崩溃分析自定义检索。

        Args:
            start_hour: 格式 ``YYYYMMDDHH``。
            end_hour: 格式 ``YYYYMMDDHH``。
        """
        return self._post("/uniform/openapi/advancedSearchEx", {
            "appId": app_id,
            "platformId": self._to_platform_int(platform),
            "startHour": start_hour,
            "endHour": end_hour,
            "type": self._to_crash_type(crash_type),
            "version": version,
            "dataType": "realTimeTrendData",
            "vm": int(vm),
        })

    def get_stack_crash_stat(
        self,
        app_id: str,
        platform: Union[Platform, int],
        key_name: str,
        start_time: str,
        end_time: str,
        limit: int = 0,
    ) -> Any:
        """根据堆栈关键字获取崩溃统计。

        Args:
            key_name: 堆栈关键字，支持 ``*`` 通配符。
            start_time: 格式 ``YYYY-MM-DD HH:MM:SS``。
            end_time: 格式 ``YYYY-MM-DD HH:MM:SS``。
        """
        pid = self._to_platform_int(platform)
        return self._post(f"/uniform/openapi/getStackCrashStat/platformId/{pid}", {
            "requestid": self._fsn(),
            "stime": start_time,
            "etime": end_time,
            "source": 0,
            "params": {"keyName": key_name, "appId": app_id},
            "limit": limit,
            "type": "pretty",
        })

    # ═══════════════════════════════════════════════════════════
    #  用户与设备
    # ═══════════════════════════════════════════════════════════

    def query_user_access_list(
        self,
        app_id: str,
        platform: Union[Platform, int],
        upload_time_begin_millis: int,
        user_id_list: list[str] | None = None,
        device_id_list: list[str] | None = None,
        page_number: int = 1,
        page_size: int = 3000,
        skip_distinct_query: bool = True,
    ) -> Any:
        """查询用户近 3 日异常数据上报。

        ``user_id_list`` 和 ``device_id_list`` 二选一。
        """
        body: dict[str, Any] = {
            "appId": app_id,
            "platformId": self._to_platform_int(platform),
            "uploadTimeBeginMillis": upload_time_begin_millis,
            "skipDistinctQuery": skip_distinct_query,
            "pageNumber": page_number,
            "pageSize": page_size,
        }
        if user_id_list:
            body["userIdList"] = user_id_list
        if device_id_list:
            body["deviceIdList"] = device_id_list
        return self._post("/uniform/openapi/queryAccessList", body)

    def get_crash_user_info(
        self,
        app_id: str,
        platform: Union[Platform, int],
        user_ids: list[str],
        start_time: str,
        end_time: str,
        limit: int = 1000,
        request_id: str = "",
    ) -> Any:
        """根据 openId 获取用户崩溃详情。

        Args:
            start_time: 格式 ``YYYY-MM-DD HH:MM:SS``。
            end_time: 格式 ``YYYY-MM-DD HH:MM:SS``。
        """
        pid = self._to_platform_int(platform)
        return self._post(f"/uniform/openapi/getCrashUserInfo/platformId/{pid}", {
            "requestid": request_id or self._fsn(),
            "stime": start_time,
            "etime": end_time,
            "type": "pretty",
            "appId": app_id,
            "filters": {"user": user_ids},
            "limit": limit,
        })

    def get_crash_user_list(
        self,
        app_id: str,
        platform: Union[Platform, int],
        start_date: str,
        end_date: str,
        crash_type: Union[CrashType, str] = CrashType.CRASH,
        version: str = "-1",
    ) -> Any:
        """获取时间段内崩溃用户列表。"""
        pid = self._to_platform_int(platform)
        return self._post(f"/uniform/openapi/getCrashUserList/platformId/{pid}", {
            "appId": app_id,
            "platformId": pid,
            "startDate": start_date,
            "endDate": end_date,
            "type": self._to_crash_type(crash_type),
            "version": version,
        })

    def get_most_report_users(
        self,
        app_id: str,
        versions: list[str] | None = None,
        time_range_millis: int = 604800000,
        exception_category: str = "CRASH",
        limit: int = 10,
        need_distinct_count: bool = True,
    ) -> Any:
        """获取 Top 上报用户崩溃次数。

        Args:
            versions: 版本列表，支持通配符。``["-1"]`` 表示全版本。
            time_range_millis: 时间范围（毫秒），默认 7 天 (604800000)。
            exception_category: ``"CRASH"`` / ``"ANR"`` / ``"ERROR"``。
            limit: 返回 Top N 用户数。
            need_distinct_count: 是否去重。
        """
        return self._post("/uniform/openapi/getMostReportUser", {
            "appId": app_id,
            "customFields": [{
                "available": True,
                "name": "userId",
                "aggregateType": 0,
                "termsSizeLimit": limit,
                "needDistinctCount": need_distinct_count,
            }],
            "searchConditionGroup": {
                "conditions": [
                    {
                        "queryType": "TERMS_WILDCARD",
                        "terms": versions or ["-1"],
                        "field": "version",
                    },
                    {
                        "field": "crashUploadTime",
                        "queryType": "RANGE_RELATIVE_DATETIME",
                        "gte": time_range_millis,
                    },
                    {
                        "queryType": "TERMS",
                        "terms": [exception_category],
                        "field": "exceptionCategory",
                    },
                ],
            },
        })

    def get_network_devices(
        self,
        app_id: str,
        platform: Union[Platform, int],
        start_time: str,
        end_time: str,
        request_id: str = "",
    ) -> Any:
        """获取联网设备数据（仅移动端 Android/iOS）。

        Args:
            start_time: 格式 ``YYYY-MM-DD HH:MM:SS``。
            end_time: 格式 ``YYYY-MM-DD HH:MM:SS``。
            request_id: 可选 trace ID，便于排查。
        """
        pid = self._to_platform_int(platform)
        return self._post(f"/uniform/openapi/getNetworkDevices/platformId/{pid}", {
            "requestid": request_id or self._fsn(),
            "stime": start_time,
            "etime": end_time,
            "appId": app_id,
        })

    def get_crash_device_stat(
        self,
        app_id: str,
        platform: Union[Platform, int],
        device_ids: list[str] | str,
        start_time: str,
        end_time: str,
        limit: int = 0,
    ) -> Any:
        """根据 deviceId 获取崩溃列表。

        Args:
            app_id: 项目 ID。
            device_ids: 设备 ID（单个字符串或列表）。
            start_time: 格式 ``YYYY-MM-DD HH:MM:SS``。
            end_time: 格式 ``YYYY-MM-DD HH:MM:SS``。
        """
        pid = self._to_platform_int(platform)
        ids = [device_ids] if isinstance(device_ids, str) else device_ids
        return self._post(f"/uniform/openapi/getCrashDeviceStat/platformId/{pid}", {
            "requestid": self._fsn(),
            "stime": start_time,
            "etime": end_time,
            "appId": app_id,
            "filters": {"deviceId": ids},
            "limit": limit,
            "type": "pretty",
        })

    def get_crash_device_info(
        self,
        app_id: str,
        platform: Union[Platform, int],
        issue_ids: list[str] | str,
        start_time: str,
        end_time: str,
        limit: int = 1000,
        request_id: str = "",
    ) -> Any:
        """根据 issue 获取 crashHash 列表（含设备信息，移动端）。

        Args:
            issue_ids: issueId 或其列表。
            start_time: 格式 ``YYYY-MM-DD HH:MM:SS``。
            end_time: 格式 ``YYYY-MM-DD HH:MM:SS``。
        """
        pid = self._to_platform_int(platform)
        ids = [issue_ids] if isinstance(issue_ids, str) else issue_ids
        return self._post(f"/uniform/openapi/getCrashDeviceInfo/platformId/{pid}", {
            "requestid": request_id or self._fsn(),
            "stime": start_time,
            "etime": end_time,
            "type": "pretty",
            "appId": app_id,
            "filters": {"issueId": ids},
            "limit": limit,
        })

    def get_device_user_info(
        self,
        app_id: str,
        platform: Union[Platform, int],
        device_id: str,
        start_time: str,
        end_time: str,
        limit: int = 10,
        request_id: str = "",
    ) -> Any:
        """根据设备 ID 获取 OpenId。

        Args:
            start_time: 格式 ``YYYY-MM-DD HH:MM:SS``。
            end_time: 格式 ``YYYY-MM-DD HH:MM:SS``。
        """
        pid = self._to_platform_int(platform)
        return self._post(f"/uniform/openapi/getDeviceUserInfo/platformId/{pid}", {
            "requestid": request_id or self._fsn(),
            "stime": start_time,
            "etime": end_time,
            "source": 0,
            "filters": {},
            "deviceId": device_id,
            "limit": limit,
            "type": "pretty",
            "appId": app_id,
        })

    def get_stack_device_info(
        self,
        app_id: str,
        platform: Union[Platform, int],
        key_name: str,
        start_time: str,
        end_time: str,
        limit: int = 0,
    ) -> Any:
        """根据堆栈关键字获取机型列表。

        Args:
            key_name: 堆栈关键字，支持 ``*`` 通配符。
            start_time: 格式 ``YYYY-MM-DD HH:MM:SS``。
            end_time: 格式 ``YYYY-MM-DD HH:MM:SS``。
        """
        pid = self._to_platform_int(platform)
        return self._post(f"/uniform/openapi/getStackDeviceInfo/platformId/{pid}", {
            "requestid": self._fsn(),
            "stime": start_time,
            "etime": end_time,
            "source": 0,
            "params": {"keyName": key_name, "appId": app_id},
            "limit": limit,
            "type": "pretty",
        })

    def get_crash_device_info_by_exp_uid(
        self,
        app_id: str,
        platform: Union[Platform, int],
        exp_uids: list[str] | str,
        start_time: str,
        end_time: str,
        limit: int = 0,
    ) -> Any:
        """根据 expUid 获取机型列表（移动端）。

        Args:
            app_id: 项目 ID。
            exp_uids: expUid（单个字符串或列表）。
            start_time: 格式 ``YYYY-MM-DD HH:MM:SS``。
            end_time: 格式 ``YYYY-MM-DD HH:MM:SS``。
        """
        pid = self._to_platform_int(platform)
        uids = [exp_uids] if isinstance(exp_uids, str) else exp_uids
        return self._post(f"/uniform/openapi/getCrashDeviceInfoByExpUid/platformId/{pid}", {
            "requestid": self._fsn(),
            "stime": start_time,
            "etime": end_time,
            "appId": app_id,
            "filters": {"expUid": uids},
            "limit": limit,
            "type": "pretty",
        })

    # ═══════════════════════════════════════════════════════════
    #  附件管理
    # ═══════════════════════════════════════════════════════════

    def fetch_crash_attachments(
        self,
        app_id: str,
        crash_id_list: list[str],
        attachment_filename_list: list[str] | None = None,
    ) -> Any:
        """下载崩溃附件（SDK 直传附件 + 服务端附件统一接口）。

        支持的附件类型包括 SDK_LOG、CustomizedAttachFile.zip、
        CustomizedLogFile.log、extraMessage.txt 等。

        Args:
            app_id: 项目 ID。
            crash_id_list: crashId 列表。
            attachment_filename_list: 需要的附件文件名列表，默认 ``["SDK_LOG"]``。

        Returns:
            ``{"crashIdAndAttachmentsList": [{"crashId": str, "attachments": [...]}]}``
            当无附件时返回空列表。
        """
        try:
            return self._post("/uniform/openapi/fetchCrashAttachments", {
                "appId": app_id,
                "crashIdList": crash_id_list,
                "attachmentFilenameList": attachment_filename_list or ["SDK_LOG"],
            })
        except CrashSightAPIError as e:
            if "attachmentFilenameList is empty" in str(e):
                return []
            raise

    # ═══════════════════════════════════════════════════════════
    #  选择器与元数据
    # ═══════════════════════════════════════════════════════════

    def get_selector_data(
        self,
        app_id: str,
        platform: Union[Platform, int],
        types: str = "version,member,bundle,tag,channel",
    ) -> Any:
        """获取版本、包名、处理人等选择器数据。

        Args:
            types: 需要查询的数据类型，逗号分隔。默认全部。
        """
        return self._post("/uniform/openapi/getSelectorDatas", {
            "appId": app_id,
            "pid": str(self._to_platform_int(platform)),
            "types": types,
        })

    def get_version_date_list(
        self,
        app_id: str,
        platform: Union[Platform, int],
    ) -> Any:
        """获取版本号首次出现日期列表。"""
        return self._post("/uniform/openapi/getVersionDateList", {
            "appId": app_id,
            "platformId": self._to_platform_int(platform),
        })
