from mcp.server.fastmcp import FastMCP
import httpx
import os
import asyncio
import traceback
from datetime import datetime, timedelta, timezone

from . import mcp

# 获取API配置
QWEATHER_API_KEY = os.getenv("QWEATHER_API_KEY")
QWEATHER_API_HOST = os.getenv("QWEATHER_API_HOST", "https://devapi.qweather.com")

# ========================== 获取实时天气(可查城市，可查格点) =============================
@mcp.tool()
async def get_weather_now(location: str) -> str:
    """
    获取指定经纬度的实时天气数据（温度、体感、风力、湿度、能见度等）。
    
    前置条件：
    调用此工具前，请先获取目标地点的经纬度坐标。
    
    Args:
        location: 必须是经纬度坐标格式 "经度,纬度" (例如 "116.41,39.92")
    
    Returns:
        包含当前天气详情的格式化文本
    """
    # 1. 强制验证坐标格式
    if "," not in location:
        return "❌ 参数错误：location 必须是 '经度,纬度' 格式（例如 116.41,39.92）。请先调用地图工具查询坐标。"

    async with httpx.AsyncClient() as client:
        try:
            # 2. 发起请求
            response = await client.get(
                f"{QWEATHER_API_HOST}/v7/weather/now",
                params={
                    "location": location,
                    "key": QWEATHER_API_KEY,
                    "lang": "zh-hans"
                },
                timeout=10.0
            )
            
            # 3. 检查 HTTP 状态
            if response.status_code != 200:
                return f"❌ 请求失败: HTTP {response.status_code}"
            
            data = response.json()
            
            # 4. 检查业务状态 code
            if data.get("code") != "200":
                return f"⚠️ API错误: {data.get('code')} (请检查坐标是否有效)"
            
            # 5. 解析数据
            now = data.get("now", {})
            
            # 格式化观测时间: 2020-06-30T21:40+08:00 -> 21:40
            obs_time = now.get("obsTime", "")
            if "T" in obs_time:
                try:
                    obs_time = obs_time.split("T")[1][:5]
                except:
                    pass
            
            # 6. 构建输出
            return (
                f"🌤️ **实时天气** @ {location}\n"
                f"🕒 观测时间: {obs_time}\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"🌡️ **温度**: {now.get('temp', 'N/A')}°C  (体感 {now.get('feelsLike', 'N/A')}°C)\n"
                f"☁️ **天气**: {now.get('text', 'N/A')}\n"
                f"💨 **风况**: {now.get('windDir', 'N/A')} {now.get('windScale', 'N/A')}级 (风速 {now.get('windSpeed', 'N/A')}km/h)\n"
                f"💧 **湿度**: {now.get('humidity', 'N/A')}%\n"
                f"☔ **降水**: {now.get('precip', '0')}mm\n"
                f"📊 **气压**: {now.get('pressure', 'N/A')}hPa\n"
                f"👀 **能见度**: {now.get('vis', 'N/A')}km"
            )

        except Exception as e:
            return f"❌ 查询异常: {str(e)}"

@mcp.tool()
async def get_grid_weather_now(location: str) -> str:
    """
    获取指定经纬度的【格点】实时天气数据(当请求为具体的某个地址时，优先使用该方法查询天气情况)。
    
    前置条件：
    调用此工具前，请先使用搜索工具获取目标地点的经纬度坐标。
    
    Args:
        location: 必须是经纬度坐标格式 "经度,纬度" (例如 "116.41,39.92")
    
    Returns:
        包含温度、风况、气压、露点等信息的格点天气详情
    """
    # 1. 验证坐标
    if "," not in location:
        return "❌ 参数错误：格点天气必须使用 '经度,纬度' 格式。请先调用地图工具查询坐标。"

    async with httpx.AsyncClient() as client:
        try:
            # 2. 发起请求
            response = await client.get(
                f"{QWEATHER_API_HOST}/v7/grid-weather/now",
                params={
                    "location": location,
                    "key": QWEATHER_API_KEY,
                    "lang": "zh-hans"
                },
                timeout=10.0
            )
            
            if response.status_code != 200:
                return f"❌ 请求失败: HTTP {response.status_code}"
            
            data = response.json()
            if data.get("code") != "200":
                return f"⚠️ API错误: {data.get('code')} (请确认该坐标支持格点数据)"
            
            # 3. 解析数据
            now = data.get("now", {})
            obs_time_raw = now.get("obsTime", "") 
            obs_time = obs_time_raw[5:16].replace("T", " ") if len(obs_time_raw) > 16 else obs_time_raw
            
            # 基础信息
            temp = now.get("temp", "N/A")
            text = now.get("text", "N/A")
            feels_like = now.get("feelsLike", "N/A") # 测试结果里有这个字段
            
            # 风力
            wind_dir = now.get("windDir", "")
            wind_scale = now.get("windScale", "")
            wind_speed = now.get("windSpeed", "")
            
            # 环境指标
            humidity = now.get("humidity", "-")
            precip = now.get("precip", "0.0") 
            pressure = now.get("pressure", "-")
            cloud = now.get("cloud", "-")
            dew = now.get("dew", "-") # 格点特有：露点
            
            # 4. 构建输出 (去掉了能见度，增加了露点)
            return (
                f"🧊 **格点实时天气** @ {location}\n"
                f"🕒 观测时间: {obs_time}\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"🌡️ **温度**: {temp}°C (体感 {feels_like}°C)\n"
                f"☁️ **天气**: {text} (云量 {cloud}%)\n"
                f"💨 **风况**: {wind_dir} {wind_scale}级 ({wind_speed}km/h)\n"
                f"💧 **湿度**: {humidity}% (露点 {dew}°C)\n"
                f"☔ **降水**: {precip}mm | 📊 气压: {pressure}hPa"
            )

        except Exception as e:
            return f"❌ 查询异常: {str(e)}"


# ======================== 获取未来若干小时的天气情况 (可查城市，可查格点)================
@mcp.tool()
async def get_weather_hourly(location: str, hours: int = 24) -> str:
    """
    获取指定经纬度的逐小时天气预报（未来24小时或72小时或168小时）。
    
    前置条件：
    调用此工具前，请先获取目标地点的经纬度坐标。
    
    Args:
        location: 必须是经纬度坐标格式 "经度,纬度" (例如 "116.41,39.92")
        hours: 预报小时数，可选 24, 72, 168。默认为 24。
    
    Returns:
        逐小时的天气详情列表
    """
    # 1. 验证坐标
    if "," not in location:
        return "❌ 参数错误：location 必须是 '经度,纬度' 格式。请先调用地图工具查询坐标。"
    
    # 2. 验证小时数
    if hours not in [24, 72, 168]:
        hours = 24
    
    endpoint = f"/v7/weather/{hours}h"

    async with httpx.AsyncClient() as client:
        try:
            # 3. 发起请求
            response = await client.get(
                f"{QWEATHER_API_HOST}{endpoint}",
                params={
                    "location": location,
                    "key": QWEATHER_API_KEY,
                    "lang": "zh-hans"
                },
                timeout=10.0
            )
            
            if response.status_code != 200:
                return f"❌ 请求失败: HTTP {response.status_code}"
            
            data = response.json()
            if data.get("code") != "200":
                return f"⚠️ API错误: {data.get('code')} (开发版可能仅支持24h)"
            
            # 4. 解析数据
            hourly_list = data.get("hourly", [])
            # 格式化发布时间: 2021-02-16T13:35+08:00 -> 02-16 13:35
            update_time_raw = data.get("updateTime", "")
            update_time = update_time_raw[5:16].replace("T", " ") if len(update_time_raw) > 16 else update_time_raw
            
            output = [
                f"⏱️ **未来{hours}小时预报** @ {location}",
                f"🕒 发布时间: {update_time}",
                f"━━━━━━━━━━━━━━━━━━"
            ]
            
            # 5. 格式化列表 (更全面的解析)
            for item in hourly_list:
                # 时间处理: 2021-02-16T15:00+08:00 -> 15:00
                fx_time = item.get("fxTime", "")
                time_str = fx_time.split("T")[1][:5] if "T" in fx_time else fx_time
                
                # 核心天气
                temp = item.get("temp", "N/A")
                text = item.get("text", "N/A")
                
                # 降水信息
                pop = item.get("pop", "0")       # 降水概率
                precip = item.get("precip", "0.0") # 降水量
                
                # 风力信息
                wind_dir = item.get("windDir", "")
                wind_scale = item.get("windScale", "")
                wind_speed = item.get("windSpeed", "") # km/h
                
                # 其他环境指标
                humidity = item.get("humidity", "-")   # 湿度
                pressure = item.get("pressure", "-")   # 气压
                cloud = item.get("cloud", "-")         # 云量
                
                # 智能格式化降水显示
                rain_info = f"☔ 概率{pop}%"
                if float(precip) > 0:
                    rain_info += f" ({precip}mm)"
                
                # 构建单行描述
                # 格式: 15:00 | 晴 2°C | ☔ 概率0% | 💨 西北风3-4级 | 💧 11% ☁️ 0%
                line = (
                    f"**{time_str}** | {text} {temp}°C | {rain_info} | "
                    f"💨 {wind_dir}{wind_scale}级 ({wind_speed}km/h) | "
                    f"💧 湿度{humidity}% ☁️ 云量{cloud}%"
                )
                output.append(line)
                
            return "\n".join(output)

        except Exception as e:
            return f"❌ 查询异常: {str(e)}"

@mcp.tool()
async def get_grid_weather_hourly(location: str, hours: int = 24) -> str:
    """ 
    获取指定经纬度【格点】的逐小时天气预报（未来24小时或72小时）。

    前置条件：
    调用此工具前，请先获取目标地点的经纬度坐标。   

    Args:
        location: 必须是经纬度坐标格式 "经度,纬度" (例如 "116.41,39.92")
        hours: 预报小时数，可选 24, 72。默认为 24。
    
    Returns:
        格点逐小时天气详情列表
    """
    # 1. 验证坐标
    if "," not in location:
        return "❌ 参数错误：格点天气必须使用 '经度,纬度' 格式。请先调用地图工具查询坐标。"
    
    # 2. 验证小时数
    if hours not in [24, 72]:
        hours = 24
        
    endpoint = f"/v7/grid-weather/{hours}h"

    async with httpx.AsyncClient() as client:
        try:
            # 3. 发起请求
            response = await client.get(
                f"{QWEATHER_API_HOST}{endpoint}",
                params={
                    "location": location,
                    "key": QWEATHER_API_KEY,
                    "lang": "zh-hans"
                },
                timeout=10.0
            )
            
            if response.status_code != 200:
                return f"❌ 请求失败: HTTP {response.status_code}"
            
            data = response.json()
            if data.get("code") != "200":
                return f"⚠️ API错误: {data.get('code')} (请确认坐标支持格点预报)"
            
            # 4. 解析数据
            hourly_list = data.get("hourly", [])
            update_time = data.get("updateTime", "")[:16].replace("T", " ")
            
            output = [
                f"🧊 **格点未来{hours}小时预报** @ {location}",
                f"🕒 发布时间: {update_time}",
                f"━━━━━━━━━━━━━━━━━━"
            ]
            
            for item in hourly_list:
                # 时间处理
                fx_time = item.get("fxTime", "")
                time_str = fx_time.split("T")[1][:5] if "T" in fx_time else fx_time
                
                # 气象数据
                temp = item.get("temp", "N/A")
                text = item.get("text", "N/A")
                
                # 降水
                precip = item.get("precip", "0.0")
                
                # 风力
                wind_dir = item.get("windDir", "")
                wind_scale = item.get("windScale", "")
                wind_speed = item.get("windSpeed", "")
                
                # 环境指标
                humidity = item.get("humidity", "-")
                pressure = item.get("pressure", "-")
                cloud = item.get("cloud", "-")
                dew = item.get("dew", "-") # 露点
                
                # 格式化输出
                line = (
                    f"**{time_str}** | {text} {temp}°C | ☔ {precip}mm | "
                    f"💨 {wind_dir}{wind_scale}级 ({wind_speed}km/h) | "
                    f"💧 湿{humidity}% 云{cloud}% (露点{dew}°C)"
                )
                output.append(line)
                
            return "\n".join(output)

        except Exception as e:
            return f"❌ 查询异常: {str(e)}"

# ========================= 获取未来若干天的天气情况(可查城市，可查格点) ==================
@mcp.tool()
async def get_weather_daily(location: str, days: int = 3) -> str:
    """
    获取指定经纬度的未来几天天气预报（支持 3天 或 7天 或 10天 或 15天 或 30天）。
    包含温度、天气状况、风力、降水、紫外线以及日出日落等信息。
    
    前置条件：
    调用此工具前，请先获取目标地点的经纬度坐标。
    
    Args:
        location: 必须是经纬度坐标格式 "经度,纬度" (例如 "116.41,39.92")
        days: 预报天数，可选 3 或 7 或 10 或 15 或 30。默认为 3。
    
    Returns:
        未来几天的天气详情列表
    """
    # 1. 强制验证坐标格式
    if "," not in location:
        return "❌ 参数错误：location 必须是 '经度,纬度' 格式。请先调用地图工具查询坐标。"
    
    # 2. 修正天数参数
    if days not in [3, 7]:
        days = 3
        
    endpoint = f"/v7/weather/{days}d"

    async with httpx.AsyncClient() as client:
        try:
            # 3. 发起请求
            response = await client.get(
                f"{QWEATHER_API_HOST}{endpoint}",
                params={
                    "location": location,
                    "key": QWEATHER_API_KEY,
                    "lang": "zh-hans"
                },
                timeout=10.0
            )
            
            if response.status_code != 200:
                return f"❌ 请求失败: HTTP {response.status_code}"
            
            data = response.json()
            if data.get("code") != "200":
                return f"⚠️ API错误: {data.get('code')} (可能不支持查询{days}天或坐标有误)"
            
            # 4. 解析数据
            daily_list = data.get("daily", [])
            # 格式化时间: 2026-01-01T15:51+08:00 -> 2026-01-01 15:51
            update_time = data.get("updateTime", "")[:16].replace("T", " ")
            
            output = [
                f"📅 **{days}天天气预报** @ {location}",
                f"🕒 发布时间: {update_time}",
                f"━━━━━━━━━━━━━━━━━━"
            ]
            
            for day in daily_list:
                # 日期处理: 2026-01-01 -> 01-01
                date = day.get("fxDate", "未知日期")
                short_date = date[5:] if len(date) > 5 else date
                
                # 核心天气
                temp_min = day.get("tempMin", "N/A")
                temp_max = day.get("tempMax", "N/A")
                text_day = day.get("textDay", "N/A")
                text_night = day.get("textNight", "N/A")
                
                # 风力风向
                wind_dir = day.get("windDirDay", "")
                wind_scale = day.get("windScaleDay", "")
                
                # 其他指标
                precip = day.get("precip", "0")   # 降水
                uv_index = day.get("uvIndex", "-") # 紫外线
                humidity = day.get("humidity", "-") # 湿度
                
                # 简要天文
                sunrise = day.get("sunrise", "--:--")
                sunset = day.get("sunset", "--:--")
                moon_phase = day.get("moonPhase", "")
                
                day_desc = (
                    f"🗓️ **{short_date}** | {text_day} 转 {text_night}\n"
                    f"   🌡️ 温度: {temp_min}°C ~ {temp_max}°C\n"
                    f"   💨 风况: {wind_dir} {wind_scale}级\n"
                    f"   ☔ 降水: {precip}mm | 💧 湿度: {humidity}%\n"
                    f"   ☀️ UV指数: {uv_index} | 🌅 日出落: {sunrise}/{sunset} ({moon_phase})"
                )
                output.append(day_desc)
                
            return "\n\n".join(output)

        except Exception as e:
            return f"❌ 查询异常: {str(e)}"


@mcp.tool()
async def get_grid_weather_daily(location: str, days: int = 3) -> str:
    """
    获取指定经纬度的【格点】未来几天天气预报。
    包含温度、天气状况、风力、降水、紫外线以及日出日落等信息。

    前置条件：
    调用此工具前，请先获取目标地点的经纬度坐标。
    
    Args:
        location: 必须是经纬度坐标格式 "经度,纬度" (例如 "116.41,39.92")
        days: 预报天数，可选 3 或 7。默认为 3。
    
    Returns:
        格点每日天气预报详情（不含日出日落等天文信息）
    """
    # 1. 验证坐标
    if "," not in location:
        return "❌ 参数错误：格点天气必须使用 '经度,纬度' 格式。请先调用地图工具查询坐标。"
    
    # 2. 验证天数
    if days not in [3, 7]:
        days = 3
        
    endpoint = f"/v7/grid-weather/{days}d"

    async with httpx.AsyncClient() as client:
        try:
            # 3. 发起请求
            response = await client.get(
                f"{QWEATHER_API_HOST}{endpoint}",
                params={
                    "location": location,
                    "key": QWEATHER_API_KEY,
                    "lang": "zh-hans"
                },
                timeout=10.0
            )
            
            if response.status_code != 200:
                return f"❌ 请求失败: HTTP {response.status_code}"
            
            data = response.json()
            if data.get("code") != "200":
                return f"⚠️ API错误: {data.get('code')} (请确认坐标支持格点预报)"
            
            # 4. 解析数据
            daily_list = data.get("daily", [])
            update_time = data.get("updateTime", "")[:16].replace("T", " ")
            
            output = [
                f"🧊 **格点{days}天预报** @ {location}",
                f"🕒 发布时间: {update_time}",
                f"━━━━━━━━━━━━━━━━━━"
            ]
            
            for day in daily_list:
                # 日期
                date = day.get("fxDate", "未知")
                short_date = date[5:] if len(date) > 5 else date
                
                # 气温 & 天气
                temp_min = day.get("tempMin", "-")
                temp_max = day.get("tempMax", "-")
                text_day = day.get("textDay", "-")
                text_night = day.get("textNight", "-")
                
                # 风力 (格点风速更具参考价值)
                wind_dir = day.get("windDirDay", "")
                wind_scale = day.get("windScaleDay", "")
                wind_speed = day.get("windSpeedDay", "") # km/h
                
                # 环境指标
                precip = day.get("precip", "0.0")
                humidity = day.get("humidity", "-")
                pressure = day.get("pressure", "-")
                
                # 格式化输出 (注意：格点预报没有日出日落和紫外线)
                line = (
                    f"🗓️ **{short_date}** | {text_day} 转 {text_night}\n"
                    f"   🌡️ 温度: {temp_min}°C ~ {temp_max}°C\n"
                    f"   💨 风况: {wind_dir} {wind_scale}级 ({wind_speed}km/h)\n"
                    f"   ☔ 降水: {precip}mm | 💧 湿度: {humidity}% | 📊 气压: {pressure}hPa"
                )
                output.append(line)
                
            return "\n\n".join(output)

        except Exception as e:
            return f"❌ 查询异常: {str(e)}"

# ========================== 获取1公里精度的未来2小时每5分钟降雨预报 ===================
@mcp.tool()
async def get_minutely_precipitation(location: str) -> str:
    """
    获取指定经纬度的【分钟级】降水预报（未来2 小时，每 5 分钟更新）。
    
    Args:
        location: 必须是经纬度坐标格式 "经度,纬度" (例如 "116.41,39.92")
    
    Returns:
        降水摘要及逐5分钟的详细数据
    """
    # 1. 验证坐标
    if "," not in location:
        return "❌ 参数错误：分钟级降水必须使用 '经度,纬度' 格式。请先调用地图工具查询坐标。"

    async with httpx.AsyncClient() as client:
        try:
            # 2. 发起请求
            # Endpoint: /v7/minutely/5m
            response = await client.get(
                f"{QWEATHER_API_HOST}/v7/minutely/5m",
                params={
                    "location": location,
                    "key": QWEATHER_API_KEY,
                    "lang": "zh-hans"
                },
                timeout=10.0
            )
            
            if response.status_code != 200:
                return f"❌ 请求失败: HTTP {response.status_code}"
            
            data = response.json()
            if data.get("code") != "200":
                return f"⚠️ API错误: {data.get('code')} (请确认坐标位于支持分钟级降水的区域)"
            
            # 3. 解析数据
            summary = data.get("summary", "暂无降水描述")
            update_time = data.get("updateTime", "")[:16].replace("T", " ")
            minutely_list = data.get("minutely", [])
            
            output = [
                f"☔ **分钟级降水预报** @ {location}",
                f"🕒 发布时间: {update_time}",
                f"📝 **摘要**: {summary}", # 这是最重要的信息
                f"━━━━━━━━━━━━━━━━━━"
            ]
            
            # 4. 格式化列表
            # 如果全是0，列表可能会很长且无用，做个简单的统计
            total_precip = sum(float(item.get('precip', 0)) for item in minutely_list)
            
            if total_precip == 0:
                output.append("✅ 未来2小时无降水。")
            else:
                for item in minutely_list:
                    # 时间处理: 2021-12-16T18:55+08:00 -> 18:55
                    fx_time = item.get("fxTime", "")
                    time_str = fx_time.split("T")[1][:5] if "T" in fx_time else fx_time
                    
                    precip = item.get("precip", "0.0")
                    p_type = item.get("type", "rain") # rain/snow
                    
                    # 只有当有降水时，或者每隔15分钟显示一行，避免刷屏
                    # 这里我们显示所有非0降水，以及每3个点(15分钟)显示一次以保持连续性
                    is_raining = float(precip) > 0
                    
                    if is_raining:
                        type_icon = "❄️" if p_type == "snow" else "🌧️"
                        line = f"**{time_str}** | {type_icon} {precip}mm ({'雪' if p_type=='snow' else '雨'})"
                        output.append(line)
                    # 如果雨停了，为了体现变化，也可以适当显示间隔
            
            # 为了让AI看清楚趋势，如果列表太长且有雨，我们完整打印；
            # 如果没雨，上面已经处理了。
            if total_precip > 0 and len(output) < 10: 
                # 如果刚才过滤太狠，这里补全一下，或者直接全量打印（推荐全量打印给AI分析趋势）
                output = [
                    f"☔ **分钟级降水预报** @ {location}",
                    f"🕒 发布时间: {update_time}",
                    f"📝 **摘要**: {summary}",
                    f"━━━━━━━━━━━━━━━━━━"
                ]
                for item in minutely_list:
                    fx_time = item.get("fxTime", "")
                    time_str = fx_time.split("T")[1][:5] if "T" in fx_time else fx_time
                    precip = item.get("precip", "0.0")
                    p_type = item.get("type", "rain")
                    
                    # 简单可视化：0.0显示-, >0显示数值
                    val_str = f"{precip}mm" if float(precip) > 0 else "-"
                    type_str = ""
                    if float(precip) > 0:
                        type_str = "❄️" if p_type == "snow" else "🌧️"
                    
                    output.append(f"{time_str} | {val_str} {type_str}")

            return "\n".join(output)

        except Exception as e:
            return f"❌ 查询异常: {str(e)}"

# ========================== 获取实时天气预警 =========================
@mcp.tool()
async def get_weather_warning(location: str) -> str:
    """
    获取指定经纬度的【天气灾害预警】信息（如暴雨、台风、大风、高温预警等）。
    
    Args:
        location: 必须是经纬度坐标格式 "经度,纬度" (例如 "116.41,39.92")
    
    Returns:
        当前生效的预警列表，或者“无预警”提示。
    """
    # 1. 验证坐标
    if "," not in location:
        return "❌ 参数错误：预警查询必须使用 '经度,纬度' 格式。请先调用地图工具查询坐标。"

    async with httpx.AsyncClient() as client:
        try:
            # 2. 发起请求
            # Endpoint: /v7/warning/now (标准灾害预警接口)
            response = await client.get(
                f"{QWEATHER_API_HOST}/v7/warning/now",
                params={
                    "location": location,
                    "key": QWEATHER_API_KEY,
                    "lang": "zh-hans"
                },
                timeout=10.0
            )
            
            if response.status_code != 200:
                return f"❌ 请求失败: HTTP {response.status_code}"
            
            data = response.json()
            if data.get("code") != "200":
                # 200代表成功，其他代表错误
                return f"⚠️ API错误: {data.get('code')}"
            
            # 3. 解析数据
            warning_list = data.get("warning", [])
            update_time = data.get("updateTime", "")[:16].replace("T", " ")
            
            output = [
                f"⚠️ **灾害预警信息** @ {location}",
                f"🕒 更新时间: {update_time}",
                f"━━━━━━━━━━━━━━━━━━"
            ]
            
            if not warning_list:
                output.append("✅ **当前无生效的灾害预警**")
                output.append("该地区目前气象状况平稳，无官方发布的预警信号。")
                return "\n\n".join(output)
            
            # 4. 格式化预警列表
            for w in warning_list:
                # 提取字段
                title = w.get("title", "未知预警") # 如 "北京市发布暴雨蓝色预警"
                text = w.get("text", "无详细内容")   # 详细描述和防御指南
                type_name = w.get("typeName", "")   # 如 "暴雨"
                level = w.get("level", "")          # 如 "蓝色"
                sender = w.get("sender", "气象台")   # 发布单位
                pub_time = w.get("pubTime", "")[:16].replace("T", " ")
                
                # 颜色映射 (让显示更直观)
                color_icon = "⚪"
                if "红" in level: color_icon = "🔴"
                elif "橙" in level: color_icon = "🟠"
                elif "黄" in level: color_icon = "🟡"
                elif "蓝" in level: color_icon = "🔵"
                
                warning_block = (
                    f"{color_icon} **{title}**\n"
                    f"   🏢 发布: {sender} ({pub_time})\n"
                    f"   🚨 类型: {type_name} ({level}预警)\n"
                    f"   📝 详情: {text}\n"
                )
                output.append(warning_block)
                
            return "\n".join(output)

        except Exception as e:
            return f"❌ 查询异常: {str(e)}"

# ========================= 获取生活指数预报数据 ======================
@mcp.tool()
async def get_weather_indices(location: str, days: int = 1) -> str:
    """
    获取指定经纬度的【生活指数】预报（支持当天或未来3天）。
    
    【包含指数】：
    1. 运动指数 (Outdoor Sports)
    2. 洗车指数 (Car Wash)
    3. 穿衣指数 (Dressing)
    5. 紫外线指数 (UV)
    6. 旅游指数 (Travel)
    9. 感冒指数 (Flu)
    
    Args:
        location: 必须是经纬度坐标格式 "经度,纬度" (例如 "116.41,39.92")
        days: 预报天数，可选 1 或 3。默认为 1（即只查当天）。
    
    Returns:
        生活指数建议列表
    """
    # 1. 验证坐标
    if "," not in location:
        return "❌ 参数错误：生活指数必须使用 '经度,纬度' 格式。请先调用地图工具查询坐标。"
    
    # 2. 验证天数 (API仅支持 1d 和 3d)
    if days not in [1, 3]:
        days = 1
        
    endpoint = f"/v7/indices/{days}d"

    async with httpx.AsyncClient() as client:
        try:
            # 3. 发起请求
            # 查询类型：1=运动, 2=洗车, 3=穿衣, 5=紫外线, 6=旅游, 9=感冒
            selected_types = "1,2,3,5,6,9"
            
            response = await client.get(
                f"{QWEATHER_API_HOST}{endpoint}",
                params={
                    "location": location,
                    "key": QWEATHER_API_KEY,
                    "lang": "zh-hans",
                    "type": selected_types
                },
                timeout=10.0
            )
            
            if response.status_code != 200:
                return f"❌ 请求失败: HTTP {response.status_code}"
            
            data = response.json()
            if data.get("code") != "200":
                return f"⚠️ API错误: {data.get('code')} (请确认坐标有效)"
            
            # 4. 解析数据
            daily_list = data.get("daily", [])
            update_time = data.get("updateTime", "")[:16].replace("T", " ")
            
            if not daily_list:
                return "⚠️ 未获取到生活指数数据。"

            output = [
                f"🧣 **生活指数预报({days}天)** @ {location}",
                f"🕒 发布时间: {update_time}",
                f"━━━━━━━━━━━━━━━━━━"
            ]
            
            # 5. 图标映射
            icon_map = {
                "1": "🏃", # 运动
                "2": "🚗", # 洗车
                "3": "👕", # 穿衣
                "5": "☀️", # 紫外线
                "6": "🧳", # 旅游
                "9": "💊", # 感冒
            }
            
            # 6. 按日期分组显示 (因为如果是3d预报，会有多个日期的同一指数)
            # 为了展示更清晰，我们按日期整理数据
            from collections import defaultdict
            date_groups = defaultdict(list)
            for item in daily_list:
                date_groups[item.get("date")].append(item)
            
            for date, items in date_groups.items():
                short_date = date[5:] if len(date) > 5 else date
                output.append(f"\n📅 **{short_date}**")
                
                for item in items:
                    type_id = item.get("type", "")
                    name = item.get("name", "未知")
                    category = item.get("category", "")
                    text = item.get("text", "暂无建议")
                    
                    icon = icon_map.get(type_id, "📌")
                    
                    # 格式：
                    # 🏃 运动指数: 较不宜
                    #    建议室内运动...
                    output.append(f"{icon} **{name}**: {category}\n   💡 {text}")

            return "\n".join(output)

        except Exception as e:
            return f"❌ 查询异常: {str(e)}"

# ========================= 获取空气质量 ==============================
# 获取实时空气质量
@mcp.tool()
async def get_air_quality(location: str) -> str:
    """
    获取指定经纬度的实时空气质量数据，精度为1x1公里。
    包含 AQI 指数、首要污染物、PM2.5/PM10 浓度及健康建议。
    
    Args:
        location: 必须是经纬度坐标格式 "经度,纬度" (例如 "116.41,39.92")
    
    Returns:
        包含AQI、主要污染物浓度和健康建议的详细报告
    """
    # 1. 坐标清洗与验证 (解决 URL 报错问题)
    try:
        # 替换可能误输入的中文逗号，移除首尾空白
        clean_loc = location.replace("，", ",").strip()
        if "," not in clean_loc:
            return "❌ 参数错误：必须是 '经度,纬度' 格式"
        
        lon_str, lat_str = clean_loc.split(",")
        # 再次strip确保无回车换行，并尝试转float验证是否为数字
        lon = lon_str.strip()
        lat = lat_str.strip()
        float(lon), float(lat) # 验证数字合法性
    except ValueError:
        return f"❌ 坐标数值无效: {location}"

    async with httpx.AsyncClient() as client:
        try:
            # 2. 发起请求
            # URL 结构: /airquality/v1/current/{lat}/{lon}
            # 注意: API要求 lat 在前，lon 在后
            url = f"{QWEATHER_API_HOST}/airquality/v1/current/{lat}/{lon}"
            
            response = await client.get(
                url,
                params={"key": QWEATHER_API_KEY, "lang": "zh-hans"},
                timeout=10.0
            )
            
            if response.status_code != 200:
                return f"❌ 请求失败: HTTP {response.status_code}"
            
            data = response.json()
            if "code" in data and data["code"] != "200":
                 return f"⚠️ API错误: {data.get('code')}"

            # 3. 解析数据
            indexes = data.get("indexes", [])
            pollutants = data.get("pollutants", [])
            
            output = [
                f"😷 **全球空气质量报告** @ {lon},{lat}",
                f"━━━━━━━━━━━━━━━━━━"
            ]
            
            # --- 解析 AQI 指数 ---
            if indexes:
                for idx in indexes:
                    # 安全获取字段 (解决 NoneType 报错)
                    standard = idx.get("name", "AQI")
                    val = idx.get("aqiDisplay", "-")
                    cat = idx.get("category", "未知")
                    
                    # 颜色图标判断
                    try:
                        aqi_val = float(idx.get("aqi", 0))
                        if aqi_val <= 50: icon = "🟢"
                        elif aqi_val <= 100: icon = "🟡"
                        elif aqi_val <= 150: icon = "🟠"
                        elif aqi_val <= 200: icon = "🔴"
                        elif aqi_val <= 300: icon = "🟣"
                        else: icon = "🟤"
                    except:
                        icon = "⚪"

                    # 🛡️ 链式调用防御：(x.get() or {}) 确保即使返回 None 也能回退到空字典
                    primary_obj = idx.get("primaryPollutant") or {}
                    primary = primary_obj.get("name", "无")
                    
                    health_obj = idx.get("health") or {}
                    advice_obj = health_obj.get("advice") or {}
                    advice = advice_obj.get("generalPopulation", "无特别建议")
                    
                    block = (
                        f"{icon} **{standard}**: {val} ({cat})\n"
                        f"   🏭 首要污染物: {primary}\n"
                        f"   📢 建议: {advice}"
                    )
                    output.append(block)
            else:
                output.append("⚠️ 暂无 AQI 指数数据")

            # --- 解析污染物浓度 ---
            if pollutants:
                output.append("\n🧪 **详细污染物浓度**:")
                details = []
                for p in pollutants:
                    name = p.get("name", "")
                    conc = p.get("concentration") or {} # 防御 None
                    value = conc.get("value", "-")
                    unit = conc.get("unit", "")
                    details.append(f"{name}: {value}{unit}")
                
                output.append(" | ".join(details))

            return "\n".join(output)

        except Exception as e:
            return f"❌ 查询异常: {type(e).__name__} - {str(e)}"

# 获取未来若干小时的空气质量
@mcp.tool()
async def get_air_quality_hourly(location: str) -> str:
    """
    获取指定经纬度的【空气质量逐小时预报】（未来24小时）。
    包含 AQI 趋势、首要污染物及 PM2.5 等关键指标变化。
    
    Args:
        location: 必须是经纬度坐标格式 "经度,纬度" (例如 "116.41,39.92")
    
    Returns:
        逐小时的空气质量变化列表
    """
    # 1. 坐标清洗与验证
    try:
        clean_loc = location.replace("，", ",").strip()
        if "," not in clean_loc:
            return "❌ 参数错误：必须是 '经度,纬度' 格式"
        
        lon_str, lat_str = clean_loc.split(",")
        lon = lon_str.strip()
        lat = lat_str.strip()
        # 验证数字合法性
        float(lon), float(lat)
    except ValueError:
        return f"❌ 坐标数值无效: {location}"

    async with httpx.AsyncClient() as client:
        try:
            # 2. 发起请求
            # URL 结构: /airquality/v1/hourly/{lat}/{lon}
            # 注意: 这里的顺序是 纬度/经度
            url = f"{QWEATHER_API_HOST}/airquality/v1/hourly/{lat}/{lon}"
            
            response = await client.get(
                url,
                params={"key": QWEATHER_API_KEY, "lang": "zh-hans"},
                timeout=10.0
            )
            
            if response.status_code != 200:
                return f"❌ 请求失败: HTTP {response.status_code}"
            
            data = response.json()
            # 空气质量V1接口通常没有外层code，直接判断 hours 字段是否存在
            if "hours" not in data:
                 return f"⚠️ API返回数据异常 (可能该区域不支持预报)"

            # 3. 解析数据
            hours_data = data.get("hours", [])
            
            output = [
                f"😷 **空气质量逐小时预报** @ {lon},{lat}",
                f"━━━━━━━━━━━━━━━━━━"
            ]
            
            for item in hours_data:
                # 时间处理: 2023-05-17T03:00Z -> 简单显示时间
                # 注意：API返回的是UTC时间(Z结尾)或带时区的ISO时间
                # 为了简化，我们直接截取 T 后面的部分
                fx_time = item.get("forecastTime", "")
                time_str = fx_time
                if "T" in fx_time:
                    # 尝试截取 HH:mm
                    # 示例: 2023-05-17T03:00Z -> 03:00 (注意这是UTC，实际使用中最好让LLM知道这是趋势)
                    # 更好的做法是保留日期: 17日03:00
                    parts = fx_time.split("T")
                    date_part = parts[0][-2:] # 日
                    time_part = parts[1][:5]  # 时分
                    time_str = f"{date_part}日{time_part}"

                # 获取 AQI 信息 (通常取第一个标准，如 QAQI)
                indexes = item.get("indexes", [])
                aqi_val = "-"
                category = ""
                icon = "⚪"
                
                if indexes:
                    idx = indexes[0] # 取第一个标准
                    aqi_val = idx.get("aqiDisplay", "-")
                    category = idx.get("category", "")
                    
                    # 颜色图标
                    try:
                        val = float(idx.get("aqi", 0))
                        if val <= 50: icon = "🟢"
                        elif val <= 100: icon = "🟡"
                        elif val <= 150: icon = "🟠"
                        elif val <= 200: icon = "🔴"
                        elif val > 200: icon = "🟣"
                    except:
                        pass

                # 获取主要污染物 (PM2.5)
                pollutants = item.get("pollutants", [])
                pm25 = "-"
                o3 = "-"
                
                for p in pollutants:
                    code = p.get("code", "")
                    val = p.get("concentration", {}).get("value", "-")
                    if code == "pm2p5":
                        pm25 = val
                    elif code == "o3":
                        o3 = val

                # 格式化单行
                # 17日14:00 | 🟢 AQI 45 (优) | PM2.5: 12 | O3: 60
                line = (
                    f"**{time_str}** | {icon} {aqi_val} ({category}) | "
                    f"PM2.5: {pm25} | O3: {o3}"
                )
                output.append(line)

            return "\n".join(output)

        except Exception as e:
            return f"❌ 查询异常: {type(e).__name__} - {str(e)}"

# 获取未来3天的空气质量
@mcp.tool()
async def get_air_quality_daily(location: str) -> str:
    """
    获取指定经纬度的【空气质量逐天预报】（未来3天的预报）。
    
    Args:
        location: 必须是经纬度坐标格式 "经度,纬度" (例如 "116.41,39.92")
    
    Returns:
        未来几天的空气质量每日摘要
    """
    # 1. 坐标清洗与验证
    try:
        clean_loc = location.replace("，", ",").strip()
        if "," not in clean_loc:
            return "❌ 参数错误：必须是 '经度,纬度' 格式"
        
        lon_str, lat_str = clean_loc.split(",")
        lon = lon_str.strip()
        lat = lat_str.strip()
        float(lon), float(lat)
    except ValueError:
        return f"❌ 坐标数值无效: {location}"

    async with httpx.AsyncClient() as client:
        try:
            # 2. 发起请求
            # URL: /airquality/v1/daily/{lat}/{lon}
            url = f"{QWEATHER_API_HOST}/airquality/v1/daily/{lat}/{lon}"
            
            response = await client.get(
                url,
                params={"key": QWEATHER_API_KEY, "lang": "zh-hans"},
                timeout=10.0
            )
            
            if response.status_code != 200:
                return f"❌ 请求失败: HTTP {response.status_code}"
            
            data = response.json()
            if "days" not in data:
                 return f"⚠️ API返回数据异常 (可能该区域不支持逐日预报)"

            # 3. 解析数据
            days_data = data.get("days", [])
            
            output = [
                f"😷 **空气质量逐天预报** @ {lon},{lat}",
                f"━━━━━━━━━━━━━━━━━━"
            ]
            
            for day in days_data:
                # 日期处理
                start_time = day.get("forecastStartTime", "")
                date_str = start_time[:10] if len(start_time) >= 10 else "未知日期"

                # 获取 AQI 信息
                indexes = day.get("indexes", [])
                aqi_val = "-"
                category = "未知"
                primary = "无"
                icon = "⚪"
                
                if indexes:
                    idx = indexes[0] 
                    aqi_val = idx.get("aqiDisplay", "-")
                    category = idx.get("category", "")
                    
                    # 🛡️ 修复点：使用 (get() or {}) 防止 NoneType 报错
                    primary_obj = idx.get("primaryPollutant") or {}
                    primary = primary_obj.get("name", "无")
                    
                    # 颜色图标
                    try:
                        val = float(idx.get("aqi", 0))
                        if val <= 50: icon = "🟢"
                        elif val <= 100: icon = "🟡"
                        elif val <= 150: icon = "🟠"
                        elif val <= 200: icon = "🔴"
                        elif val > 200: icon = "🟣"
                    except:
                        pass

                # 获取污染物 (PM2.5)
                pollutants = day.get("pollutants", [])
                pm25 = "-"
                
                for p in pollutants:
                    code = p.get("code", "")
                    # 🛡️ 修复点：使用 (get() or {}) 防止 NoneType 报错
                    conc_obj = p.get("concentration") or {}
                    val = conc_obj.get("value", "-")
                    
                    if code == "pm2p5":
                        pm25 = val

                # 格式化
                block = (
                    f"📅 **{date_str}**\n"
                    f"   {icon} AQI: {aqi_val} ({category}) | 🏭 首要: {primary}\n"
                    f"   🧪 PM2.5浓度: {pm25}"
                )
                output.append(block)

            return "\n".join(output)

        except Exception as e:
            return f"❌ 查询异常: {type(e).__name__} - {str(e)}"


# ========================= 获取热带气旋（台风）数据 ===================
# 获取台风列表
@mcp.tool()
async def get_storm_list(year: str = None, basin: str = "NP") -> str:
    """
    获取指定年份和流域的【台风列表】。
    用于查询台风的 ID (stormid)，以便进一步查询其路径预报。
    
    Args:
        year: 年份 (如 "2023")。如果不填，默认查询当年。
        basin: 流域代码，默认为 "NP" (西北太平洋)。
    
    Returns:
        包含台风ID、名称、是否活跃等信息的列表
    """
    try:
        # 1. 默认年份处理 (移入 try 块以防万一)
        if not year:
            year = str(datetime.now().year)

        async with httpx.AsyncClient() as client:
            # 2. 发起请求
            response = await client.get(
                f"{QWEATHER_API_HOST}/v7/tropical/storm-list",
                params={
                    "year": year,
                    "basin": basin,
                    "key": QWEATHER_API_KEY
                },
                timeout=10.0
            )
            
            if response.status_code != 200:
                return f"❌ 请求失败: HTTP {response.status_code}"
            
            data = response.json()
            
            # 3. 处理业务状态码
            # 204 表示该年份/流域没有台风数据，这是正常情况
            if str(data.get("code")) == "204":
                return f"ℹ️ {year}年 {basin}流域 暂无台风记录。"
            
            if str(data.get("code")) != "200":
                return f"⚠️ API错误: {data.get('code', '未知错误')}"
            
            # 4. 解析数据 (增加防御)
            # 即使 key 存在，值也可能是 None，必须由 [] 接管
            storm_list = data.get("storm") or []
            
            # 安全获取时间
            update_time_raw = str(data.get("updateTime", ""))
            update_time = update_time_raw[:10] if len(update_time_raw) >= 10 else update_time_raw
            
            output = [
                f"🌀 **{year}年台风列表** ({basin}流域)",
                f"🕒 数据更新: {update_time}",
                f"━━━━━━━━━━━━━━━━━━"
            ]
            
            if not storm_list:
                output.append("ℹ️ 返回了成功状态码，但列表为空。")
                return "\n".join(output)

            # 分类：活跃 vs 已停编
            active_storms = []
            inactive_storms = []
            
            for s in storm_list:
                # 再次防御：防止列表里混入 None
                if not isinstance(s, dict):
                    continue
                    
                is_active = str(s.get("isActive")) == "1"
                storm_id = s.get("id", "未知ID")
                name = s.get("name", "未命名")
                
                info = f"🆔 `{storm_id}` : **{name}**"
                
                if is_active:
                    active_storms.append(info)
                else:
                    inactive_storms.append(info)
            
            # 5. 格式化输出
            if active_storms:
                output.append("🔥 **正在活跃**:")
                for s in active_storms:
                    output.append(f"   {s} ⚡")
                output.append("") 
            
            if inactive_storms:
                output.append("⚪ **历史/已停编**:")
                # 切片操作 [:10] 对列表永远是安全的，即使列表为空
                for s in inactive_storms[:10]:
                    output.append(f"   {s}")
                
                if len(inactive_storms) > 10:
                    output.append(f"   ... (还有 {len(inactive_storms)-10} 个)")

            return "\n".join(output)

    except Exception:
        # 捕获所有异常并打印详细堆栈，方便排查那个神秘的 index error
        err_msg = traceback.format_exc()
        # 也可以只返回简短错误
        # return f"❌ 查询异常: {str(e)}"
        return f"❌ 内部运行错误:\n{err_msg}"


# 台风实况
@mcp.tool()
async def get_storm_track(stormid: str) -> str:
    """
    获取指定台风的【实况路径】（历史轨迹及当前最新位置）。
    
    【适用场景】：
    1. 查看台风“现在到哪了”（看列表最后一条）。
    2. 复盘台风过去的移动路线。
    3. 获取台风当前的具体强度、气压、7级/10级风圈半径等详细数据。
    
    Args:
        stormid: 台风ID (例如 "NP_202305")。
    
    Returns:
        台风从生成至今的路径点列表（按时间倒序排列，最新的在最前）
    """
    if not stormid:
        return "❌ 参数错误：必须提供 stormid (台风ID)"

    async with httpx.AsyncClient() as client:
        try:
            # 2. 发起请求
            response = await client.get(
                f"{QWEATHER_API_HOST}/v7/tropical/storm-track",
                params={
                    "stormid": stormid,
                    "key": QWEATHER_API_KEY
                },
                timeout=10.0
            )
            
            if response.status_code != 200:
                return f"❌ 请求失败: HTTP {response.status_code}"
            
            data = response.json()
            if data.get("code") != "200":
                return f"⚠️ API错误: {data.get('code')} (可能ID错误或无数据)"
            
            # 3. 解析数据
            tracks = data.get("track", [])
            is_active = data.get("isActive", "0") # 1=活跃, 0=停编
            status_str = "🔥活跃" if is_active == "1" else "⚪已停编"
            update_time = data.get("updateTime", "")[:16].replace("T", " ")
            
            output = [
                f"🌀 **台风实况路径** (ID: {stormid})",
                f"📊 状态: {status_str} | 更新: {update_time}",
                f"━━━━━━━━━━━━━━━━━━"
            ]
            
            # 等级映射
            type_map = {
                "TD": "热带低压", "TS": "热带风暴", "STS": "强热带风暴",
                "TY": "台风", "STY": "强台风", "SuperTY": "超强台风"
            }
            
            # 4. 格式化输出 (建议倒序，把最新的放在最上面，方便用户第一时间看到)
            # API返回通常是时间正序（旧->新），我们反转一下
            for item in reversed(tracks):
                time_str = item.get("time", "")[5:16].replace("T", " ")
                
                # 位置与强度
                lat = item.get("lat", "-")
                lon = item.get("lon", "-")
                storm_type = item.get("type", "")
                type_name = type_map.get(storm_type, storm_type)
                pressure = item.get("pressure", "-")
                wind_speed = item.get("windSpeed", "-")
                
                # 移动
                move_dir = item.get("moveDir", "")
                move_speed = item.get("moveSpeed", "")
                move_info = f"移向{move_dir} {move_speed}km/h" if move_dir else ""
                
                # 风圈 (如果有)
                radius_info = ""
                r30 = item.get("windRadius30", {}).get("neRadius") # 7级风圈东北半径作为参考
                if r30:
                    radius_info = f" | 🌪️ 7级圈~{r30}km"
                
                # 格式:
                # 05-27 14:00 | 台风(TY) | 38m/s
                # 📍 16.2N, 123.2E | 🧭 移向NE 20km/h
                line = (
                    f"⏰ **{time_str}** | {type_name} ({wind_speed}m/s, {pressure}hPa)\n"
                    f"   📍 {lat}N, {lon}E | 🧭 {move_info}{radius_info}"
                )
                output.append(line)
                
                # 如果列表太长（比如几十条），只显示最近的 10 条，避免 Context 爆炸
                if len(output) >= 15:
                    output.append(f"\n... (省略 {len(tracks) - 12} 条历史路径)")
                    break
            
            return "\n\n".join(output)

        except Exception as e:
            return f"❌ 查询异常: {str(e)}"

# 台风预报
@mcp.tool()
async def get_storm_forecast(stormid: str) -> str:
    """
    获取指定台风的【未来预报】路径及强度信息。
    
    【适用场景】：
    1. 台风来袭时，查询其未来的移动路径和登陆点。
    2. 判断台风未来是增强还是减弱。
    
    Args:
        stormid: 台风ID (例如 "NP_202305")。需要先知道具体的台风编号。
    
    Returns:
        台风未来时间点的路径、风力、气压等预测数据
    """
    if not stormid:
        return "❌ 参数错误：必须提供 stormid (台风ID)"

    async with httpx.AsyncClient() as client:
        try:
            # 2. 发起请求
            # Endpoint: /v7/tropical/storm-forecast
            response = await client.get(
                f"{QWEATHER_API_HOST}/v7/tropical/storm-forecast",
                params={
                    "stormid": stormid,
                    "key": QWEATHER_API_KEY
                },
                timeout=10.0
            )
            
            if response.status_code != 200:
                return f"❌ 请求失败: HTTP {response.status_code}"
            
            data = response.json()
            if data.get("code") != "200":
                # 常见错误：204 (无数据/台风已停止编号)
                return f"⚠️ API错误: {data.get('code')} (可能该台风ID无效或已停止编号)"
            
            # 3. 解析数据
            forecast_list = data.get("forecast", [])
            update_time = data.get("updateTime", "")[:16].replace("T", " ")
            
            output = [
                f"🌀 **台风预报详情** (ID: {stormid})",
                f"🕒 更新时间: {update_time}",
                f"━━━━━━━━━━━━━━━━━━"
            ]
            
            # 台风等级映射表
            type_map = {
                "TD": "热带低压",
                "TS": "热带风暴",
                "STS": "强热带风暴",
                "TY": "台风",
                "STY": "强台风",
                "SuperTY": "超强台风"
            }
            
            for item in forecast_list:
                # 时间处理
                fx_time = item.get("fxTime", "")
                time_str = fx_time[5:16].replace("T", " ") if len(fx_time) > 16 else fx_time
                
                # 位置与强度
                lat = item.get("lat", "-")
                lon = item.get("lon", "-")
                storm_type = item.get("type", "")
                type_name = type_map.get(storm_type, storm_type)
                
                pressure = item.get("pressure", "-")
                wind_speed = item.get("windSpeed", "-")
                
                # 移动信息 (部分数据可能为空)
                move_dir = item.get("moveDir", "")
                move_speed = item.get("moveSpeed", "")
                move_info = f"移向{move_dir} ({move_speed}km/h)" if move_dir and move_speed else "移向未知"
                
                # 格式化输出
                # 07-27 20:00 | TS(热带风暴) | 💨 18m/s | 📍 31.7N, 118.4E
                line = (
                    f"📅 **{time_str}** | {type_name}\n"
                    f"   💨 风速: {wind_speed}m/s | 📊 气压: {pressure}hPa\n"
                    f"   📍 坐标: {lat}N, {lon}E | 🧭 {move_info}"
                )
                output.append(line)
            
            return "\n\n".join(output)

        except Exception as e:
            return f"❌ 查询异常: {str(e)}"


# ========================== 潮汐数据 =================================
@mcp.tool()
async def get_ocean_tide(location: str, date: str = None) -> str:
    """
    获取指定地点的【潮汐预报】。
    包含满潮/干潮时间表及潮位高度。
    
    Args:
        location: 必须是经纬度坐标 "经度,纬度" (例如 "120.38,36.06" 青岛) 或 港口ID (如 "P2951")。
                  注意：内陆城市（如北京）查询会报错，必须是沿海坐标。
        date: 查询日期，格式 YYYYMMDD (例如 "20230601")。如果不填，默认为今日。
    
    Returns:
        潮汐时间表（满潮/干潮时刻及水位）
    """
    # 1. 处理日期 (默认为今日)
    if not date:
        # 使用 UTC+8 时间
        utc_now = datetime.now(timezone.utc)
        beijing_now = utc_now + timedelta(hours=8)
        date = beijing_now.strftime("%Y%m%d")

    async with httpx.AsyncClient() as client:
        try:
            # 2. 发起请求
            # Endpoint: /v7/ocean/tide
            response = await client.get(
                f"{QWEATHER_API_HOST}/v7/ocean/tide",
                params={
                    "location": location,
                    "date": date,
                    "key": QWEATHER_API_KEY
                },
                timeout=10.0
            )
            
            if response.status_code != 200:
                return f"❌ 请求失败: HTTP {response.status_code}"
            
            data = response.json()
            if data.get("code") != "200":
                # 常见错误：请求了内陆地区
                return f"⚠️ API错误: {data.get('code')} (请确认坐标是否位于沿海区域)"
            
            # 3. 解析数据
            update_time = data.get("updateTime", "")[:16].replace("T", " ")
            tide_table = data.get("tideTable", [])
            
            output = [
                f"🌊 **潮汐预报** @ {location}",
                f"📅 日期: {date}",
                f"━━━━━━━━━━━━━━━━━━"
            ]
            
            if not tide_table:
                output.append("⚠️ 该地点今日无明显的满/干潮记录，或处于不规则半日潮区域，请参考逐小时数据。")
            else:
                # 4. 格式化潮汐表
                output.append("📊 **潮汐时刻表 (满/干潮)**:")
                for item in tide_table:
                    # 时间处理: 2021-02-06T03:48+08:00 -> 03:48
                    fx_time = item.get("fxTime", "")
                    time_str = fx_time.split("T")[1][:5] if "T" in fx_time else fx_time
                    
                    height = item.get("height", "-")
                    t_type = item.get("type", "")
                    
                    # 转换类型展示
                    if t_type == "H":
                        type_str = "🌊 满潮 (High)"
                        desc = "水位最高"
                    elif t_type == "L":
                        type_str = "📉 干潮 (Low) "
                        desc = "水位最低，适合赶海"
                    else:
                        type_str = t_type
                        desc = ""
                    
                    output.append(f"   ⏰ **{time_str}** | {type_str} | 高度 {height}m")
            
            # 5. 简述逐小时趋势 (可选，只显示极值附近的趋势太复杂，这里只提示更新时间)
            output.append(f"\n🕒 数据更新: {update_time}")
            output.append("💡 提示: 赶海建议在【干潮】前1-2小时到达海边。")

            return "\n".join(output)

        except Exception as e:
            return f"❌ 查询异常: {str(e)}"

# ========================= 太阳辐射预报 ==============================
@mcp.tool()
async def get_solar_radiation(location: str) -> str:
    """
    获取指定经纬度的【太阳辐射】未来预报。
    包含 GHI(总辐射)、DNI(直射)、DHI(散射) 及太阳高度角/方位角。
    
    Args:
        location: 必须是经纬度坐标格式 "经度,纬度" (例如 "116.41,39.92")
    
    Returns:
        逐小时的太阳辐射及角度数据表
    """
    # 1. 坐标清洗与验证
    try:
        clean_loc = location.replace("，", ",").strip()
        if "," not in clean_loc:
            return "❌ 参数错误：必须是 '经度,纬度' 格式"
        
        lon_str, lat_str = clean_loc.split(",")
        lon = lon_str.strip()
        lat = lat_str.strip()
        float(lon), float(lat)
    except ValueError:
        return f"❌ 坐标数值无效: {location}"

    async with httpx.AsyncClient() as client:
        try:
            # 2. 发起请求
            # Endpoint: /solarradiation/v1/forecast/{lat}/{lon}
            # 注意顺序：先纬度 lat，后经度 lon
            url = f"{QWEATHER_API_HOST}/solarradiation/v1/forecast/{lat}/{lon}"
            
            response = await client.get(
                url,
                params={"key": QWEATHER_API_KEY, "lang": "zh-hans"},
                timeout=10.0
            )
            
            if response.status_code != 200:
                return f"❌ 请求失败: HTTP {response.status_code}"
            
            data = response.json()
            # Solar Radiation V1 接口通常没有外层 code，若有 forecasts 则视为成功
            if "forecasts" not in data:
                 return f"⚠️ API返回数据异常 (可能无权限或坐标不支持)"

            # 3. 解析数据
            forecasts = data.get("forecasts", [])
            
            output = [
                f"☀️ **太阳辐射预报** @ {lon},{lat}",
                f"📝 说明: GHI=总辐射, DNI=直射, DHI=散射 (单位 W/m²)",
                f"━━━━━━━━━━━━━━━━━━"
            ]
            
            count = 0
            for item in forecasts:
                # 时间处理: 2023-10-15T11:30Z (UTC)
                # 原始数据通常是15分钟间隔，为了节省Token，我们只显示整点数据
                fx_time = item.get("forecastTime", "")
                
                # 简单的整点过滤逻辑 (如果不含 :00 则跳过，保留第一条除外)
                if count > 0 and ":00" not in fx_time and ":00Z" not in fx_time:
                    continue
                
                # 格式化时间显示
                time_str = fx_time
                if "T" in fx_time:
                    # 截取 日+时分 (例如 15日12:00)
                    parts = fx_time.split("T")
                    date_part = parts[0][-2:]
                    time_part = parts[1][:5]
                    time_str = f"{date_part}日{time_part}"

                # 太阳角度
                angle = item.get("solarAngle", {})
                azimuth = angle.get("azimuth", "-")   # 方位角
                elevation = angle.get("elevation", "-") # 高度角
                
                # 辐射数据
                ghi = item.get("ghi", {}).get("value", 0) # 总水平辐射
                dni = item.get("dni", {}).get("value", 0) # 法向直射
                dhi = item.get("dhi", {}).get("value", 0) # 水平散射
                
                # 天气简况 (API里有带weather字段)
                weather = item.get("weather", {})
                temp = weather.get("temperature", {}).get("value", "-")
                
                # 只有当有光照时才显示详细，或者显示夜间
                # 以高度角判断，<0 表示太阳下山
                try:
                    is_day = float(elevation) > 0
                except:
                    is_day = True # 解析失败默认显示

                if is_day:
                    line = (
                        f"⏰ **{time_str}** | 🌡️ {temp}°C\n"
                        f"   🌞 角度: 高度 {elevation}° / 方位 {azimuth}°\n"
                        f"   ⚡ 辐射: GHI {ghi} | DNI {dni} | DHI {dhi}"
                    )
                    output.append(line)
                    count += 1
                elif count == 0 or ":00" in fx_time: 
                    # 夜间数据简化显示 (仅整点)
                    # output.append(f"⏰ {time_str} | 🌙 夜间 (无辐射)")
                    pass # 也可以选择完全不显示夜间以节省空间

            if count == 0:
                output.append("ℹ️ 当前时段为夜间或无有效光照数据。")

            return "\n".join(output)

        except Exception as e:
            return f"❌ 查询异常: {str(e)}"


# ========================== 天文工具 ==================================
@mcp.tool()
async def get_astronomy_today(location: str, date: str = None) -> str:
    """
    获取指定经纬度的详细天文数据。
    
    前置条件：
    调用此工具前，请先获取目标地点的经纬度坐标。
    
    Args:
        location: 必须是经纬度坐标格式 "经度,纬度" (例如 "116.41,39.92")
        date: 可选，格式 YYYYMMDD。不填则默认使用当前北京时间日期。

    Returns:
        日出日落、月升月落、月相、实时太阳高度角/方位角
    """
    # 1. 验证坐标格式
    if "," not in location:
        return "❌ 参数错误：location 必须是 '经度,纬度' 格式（例如 116.41,39.92）。请先调用地图工具查询坐标。"

    # 2. 准备时间 (强制北京时间 UTC+8)
    # 因为我们要查询的是“此时此刻”的状态，或者“当天”的数据
    utc_now = datetime.now(timezone.utc)
    beijing_now = utc_now + timedelta(hours=8)
    
    query_date = date if date else beijing_now.strftime("%Y%m%d")
    current_time_str = beijing_now.strftime("%H%M") # 北京时间 HHmm

    # 辅助函数
    def format_iso_time(iso_str):
        if not iso_str: return "--:--"
        if "T" in iso_str:
            try: return iso_str.split("T")[1][:5]
            except: pass
        return iso_str
    
    def format_hhmm(hhmm):
        if hhmm and len(hhmm) == 4:
            return f"{hhmm[:2]}:{hhmm[2:]}"
        return hhmm

    async with httpx.AsyncClient() as client:
        base_params = {
            "key": QWEATHER_API_KEY, 
            "lang": "zh-hans",
            "location": location  # 所有接口现在都直接用坐标
        }

        try:
            # 3. 构建并发请求
            # 日出日落
            task_sun = client.get(
                f"{QWEATHER_API_HOST}/v7/astronomy/sun", 
                params={**base_params, "date": query_date}, 
                timeout=10.0
            )
            
            # 月升月落
            task_moon = client.get(
                f"{QWEATHER_API_HOST}/v7/astronomy/moon", 
                params={**base_params, "date": query_date}, 
                timeout=10.0
            )
            
            # 太阳高度角 (坐标模式下 tz 和 alt 是必填的)
            # 逻辑：告诉API "location" 在 "tz=0800" 时区的 "time" 时刻的高度角
            solar_params = {
                **base_params,
                "date": query_date,
                "time": current_time_str, 
                "tz": "0800", # 固定使用北京时区解析传入的 time
                "alt": "0"    # 默认海拔0米
            }
            task_solar = client.get(
                f"{QWEATHER_API_HOST}/v7/astronomy/solar-elevation-angle", 
                params=solar_params, 
                timeout=10.0
            )

            # 4. 执行请求
            results = await asyncio.gather(task_sun, task_moon, task_solar, return_exceptions=True)
            sun_res, moon_res, solar_res = results

            # 5. 构建输出
            output = [f"📅 **天文数据概览** ({query_date})", f"📍 坐标: {location}"]

            # --- 🌞 太阳行程 ---
            if isinstance(sun_res, httpx.Response) and sun_res.status_code == 200:
                data = sun_res.json()
                if data.get("code") == "200":
                    output.append(
                        f"🌞 **太阳行程**\n"
                        f"   - 日出: {format_iso_time(data.get('sunrise'))}\n"
                        f"   - 日落: {format_iso_time(data.get('sunset'))}"
                    )
                else:
                    output.append(f"🌞 太阳: 无数据 ({data.get('code')})")
            else:
                output.append(f"🌞 太阳: 请求失败")

            # --- 🌙 月亮行程 ---
            if isinstance(moon_res, httpx.Response) and moon_res.status_code == 200:
                data = moon_res.json()
                if data.get("code") == "200":
                    phases = data.get('moonPhase', [])
                    phase_str = "未知"
                    if phases:
                        # 取当天中间时刻的月相
                        idx = 12 if len(phases) > 12 else 0
                        p = phases[idx]
                        phase_str = f"{p.get('name')} (照明度 {p.get('illumination')}%)"
                    
                    output.append(
                        f"🌙 **月亮行程**\n"
                        f"   - 月升: {format_iso_time(data.get('moonrise'))}\n"
                        f"   - 月落: {format_iso_time(data.get('moonset'))}\n"
                        f"   - 月相: {phase_str}"
                    )
                else:
                    output.append(f"🌙 月亮: 无数据 ({data.get('code')})")
            else:
                output.append(f"🌙 月亮: 请求失败")

            # --- 📐 实时太阳方位 ---
            if isinstance(solar_res, httpx.Response) and solar_res.status_code == 200:
                data = solar_res.json()
                if data.get("code") == "200":
                    output.append(
                        f"📐 **实时太阳方位** (北京时间 {format_hhmm(current_time_str)})\n"
                        f"   - 高度角: {data.get('solarElevationAngle', 'N/A')}°\n"
                        f"   - 方位角: {data.get('solarAzimuthAngle', 'N/A')}°\n"
                        f"   - 真太阳时: {format_hhmm(data.get('solarHour'))}"
                    )
                else:
                    output.append(f"📐 太阳方位: 接口报错 ({data.get('code')})")
            else:
                # 打印出具体状态码方便调试
                err = solar_res.status_code if isinstance(solar_res, httpx.Response) else type(solar_res)
                output.append(f"📐 太阳方位: 请求失败 ({err})")

            return "\n\n".join(output)

        except Exception as e:
            return f"❌ 运行异常: {str(e)}"
