import json
import ntplib
import pytz
from datetime import datetime, timezone as dt_timezone
from typing import Optional
from mcp.server.fastmcp import FastMCP

# 从当前模块或包导入 mcp 实例 (保持你原有的导入方式)
from . import mcp

# --- 1. 获取时间的工具 (保持 NTP 核心逻辑) ---

@mcp.tool()
def get_current_time(timezone_str: str = "Asia/Shanghai") -> str:
    """
    获取权威的实时日期和时间。
    
    优先连接中国国家授时中心(NTSC)获取原子钟基准时间。
    
    Args:
        timezone_str: 时区名称，必须是标准的 TZ 数据库名称，例如 "Asia/Shanghai"、"UTC"。
                      如果不确定，可以查阅 memo://timezones/all 资源。
    """
    source = "国家授时中心(NTP)"
    try:
        # 请求 NTP 时间
        client = ntplib.NTPClient()
        # ntp.ntsc.ac.cn 是国内最权威的源
        response = client.request('ntp.ntsc.ac.cn', timeout=2)
        # 将 NTP 时间戳转为 UTC datetime 对象
        base_now = datetime.fromtimestamp(response.tx_time, dt_timezone.utc)
    except Exception as e:
        # 降级方案：如果网络不通，使用系统本地时间
        base_now = datetime.now(dt_timezone.utc)
        source = f"系统本地时间 (NTP连接失败: {e})"

    try:
        # 时区转换
        target_tz = pytz.timezone(timezone_str)
        now = base_now.astimezone(target_tz)
        
        # 格式化输出
        fmt_full = now.strftime("%Y-%m-%d %H:%M:%S")
        offset = now.strftime("%z")
        weekday = now.strftime("%A")
        
        weekdays_cn = {
            "Monday": "星期一", "Tuesday": "星期二", "Wednesday": "星期三",
            "Thursday": "星期四", "Friday": "星期五", "Saturday": "星期六", "Sunday": "星期日"
        }

        # 返回 JSON 格式，方便 AI 提取和显示
        result = {
            "当前时间": fmt_full,
            "星期": weekdays_cn.get(weekday, weekday),
            "时区": f"{timezone_str} (UTC{offset})",
            "来源": source
        }
        return json.dumps(result, ensure_ascii=False, indent=2)
        
    except pytz.exceptions.UnknownTimeZoneError:
        return f"错误：无法识别时区 '{timezone_str}'。请调用资源查看有效列表。"

# --- 2. 完整时区列表资源 (让 AI 可以随时查阅) ---

@mcp.resource("memo://timezones/all")
def get_all_timezones() -> str:
    """
    提供全球完整的 TZ 数据库时区列表。
    当用户询问非北京时间或不确定时区拼写时，AI 可以读取此资源。
    """
    # 获取 pytz 支持的所有时区列表
    all_tz = pytz.all_timezones
    
    header = "全球标准时区列表 (TZ Database Names):\n"
    header += "-" * 30 + "\n"
    
    # 将几百个时区按字母顺序排列并分行
    return header + "\n".join(all_tz)

@mcp.resource("memo://timezones/common")
def get_common_timezones() -> str:
    """提供常用时区快速索引"""
    common = [
        "Asia/Shanghai - 中国标准时间 (CST)",
        "Asia/Hong_Kong - 香港时间",
        "Asia/Taipei - 台湾时间",
        "Asia/Tokyo - 日本标准时间 (JST)",
        "Europe/London - 伦敦/格林威治时间 (GMT/BST)",
        "Europe/Paris - 巴黎/中欧时间 (CET)",
        "America/New_York - 美东时间 (EST/EDT)",
        "America/Chicago - 美中时间 (CST/CDT)",
        "America/Los_Angeles - 美西时间 (PST/PDT)",
        "UTC - 协调世界时"
    ]
    return "常用时区快速参考:\n" + "\n".join(common)
