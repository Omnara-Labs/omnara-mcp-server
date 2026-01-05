import httpx
import os
import re
import json
from typing import List, Dict, Any, Optional, Tuple

try:
    from . import mcp
except ImportError:
    from mcp.server.fastmcp import FastMCP
    mcp = FastMCP("Amap Tools")

AMAP_API_KEY = os.getenv("AMAP_API_KEY")
AMAP_API_HOST = "https://restapi.amap.com/v3"
AMAP_API_HOST_V4 = "https://restapi.amap.com/v4"

# ==================== 1. 基础组件 ====================

async def _resolve_location(client: httpx.AsyncClient, input_str: str, city: Optional[str] = None) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """坐标/地址解析"""
    if not input_str: return None, None, None
    if re.match(r'^-?\d+(\.\d+)?,-?\d+(\.\d+)?$', input_str.strip()):
        return input_str.strip(), None, input_str
    
    try:
        geo_params = {"key": AMAP_API_KEY, "address": input_str, "output": "JSON"}
        if city: geo_params["city"] = city
        resp = await client.get(f"{AMAP_API_HOST}/geocode/geo", params=geo_params)
        if resp.status_code == 200 and resp.json().get("status") == "1":
            g = resp.json().get("geocodes")[0]
            return g.get("location"), g.get("adcode"), g.get("formatted_address")
    except: pass
    
    try:
        poi_params = {"key": AMAP_API_KEY, "keywords": input_str, "citylimit": "true" if city else "false", "offset": 1}
        if city: poi_params["city"] = city
        resp = await client.get(f"{AMAP_API_HOST}/place/text", params=poi_params)
        if resp.status_code == 200 and resp.json().get("status") == "1":
            p = resp.json().get("pois")[0]
            return p.get("location"), p.get("adcode"), p.get("name")
    except: pass
    return None, None, input_str

def _fmt_time(seconds):
    """秒 -> 可读时间"""
    m = int(seconds) // 60
    if m < 60: return f"{m}分钟"
    h, m = divmod(m, 60)
    return f"{h}小时{m}分钟"

def _fmt_dist(meters):
    """米 -> 可读距离"""
    m = float(meters)
    if m < 1000: return f"{int(m)}米"
    return f"{m/1000:.1f}公里"

# ==================== 2. 文本生成逻辑 (核心) ====================

def _format_nav_text(mode: str, path_data: Dict) -> str:
    """
    [通用导航] 生成 驾车/步行/骑行 的文本描述
    """
    lines = []
    
    # 1. 概况
    dur = _fmt_time(path_data.get("duration", 0))
    dist = _fmt_dist(path_data.get("distance", 0))
    
    # 标题图标
    icon = "🚗" if mode == "driving" else "🚶" if mode == "walking" else "🚲"
    title = f"{icon} 【{mode}导航】"
    
    # 概况行
    summary = f"总耗时: {dur} | 总距离: {dist}"
    if mode == "driving":
        lights = path_data.get("traffic_lights", "0")
        tolls = path_data.get("tolls", "0")
        summary += f" | 红绿灯: {lights}个 | 过路费: {tolls}元"
        if path_data.get("restriction") == "1":
            summary += " (⚠️含限行区域)"
            
    lines.append(title)
    lines.append(summary)
    lines.append("-" * 20)
    lines.append("📝 详细路线:")

    # 2. 步骤生成 (结合路名)
    steps = path_data.get("steps", [])
    for i, s in enumerate(steps):
        instr = s.get("instruction", "")
        road = s.get("road", "")
        dist_val = s.get("distance", "0")
        action = s.get("action", "")
        assistant = s.get("assistant_action", "")

        # 优化指令文本：把 road 拼接到 instruction 里
        # 避免 "向北行驶" 这种空洞的描述
        desc = instr
        if road and road not in instr:
            # 如果指令里没提路名，但 road 字段有值，强制插入
            # 简单粗暴拼接法，AI 能读懂即可
            if "向" in desc:
                desc = desc + f" (沿{road})"
            else:
                desc = f"{desc}，沿{road}行驶"
        
        # 补全距离 (如果原文没说)
        if "米" not in desc and "公里" not in desc and int(dist_val) > 0:
            desc += f" {dist_val}米"
            
        # 补全辅助动作 (进入主路/匝道等)
        if assistant:
            desc += f" ({assistant})"

        lines.append(f"{i+1}. {desc}")

    return "\n".join(lines)

def _format_transit_text(transits: List[Dict]) -> str:
    """
    [公交导航] 生成 Top3 方案的文本描述
    """
    if not transits: return "未找到公交方案"
    
    lines = ["🚌 【公交/地铁导航】(推荐Top3)"]
    
    for idx, t in enumerate(transits[:3]):
        # 方案头
        dur = _fmt_time(t.get("duration", 0))
        cost = float(t.get("cost", 0))
        walk = _fmt_dist(t.get("walking_distance", 0))
        
        lines.append("") # 空行分隔
        lines.append(f"=== 方案 {idx+1} ({dur}) ===")
        lines.append(f"💰 票价: {cost}元 | 🚶 步行: {walk}")
        
        # 提取换乘链 (例如: 14号线 -> 10号线)
        segments = t.get("segments", [])
        chain = []
        details = []
        
        for seg in segments:
            # 公交/地铁
            if seg.get("bus") and seg["bus"].get("buslines"):
                b = seg["bus"]["buslines"][0]
                line = b.get("name", "").split('(')[0]
                dep = b.get("departure_stop", {}).get("name", "起点")
                arr = b.get("arrival_stop", {}).get("name", "终点")
                stops = b.get("num_stops", "--")
                chain.append(line)
                details.append(f"  • 🚌 乘 {line}: {dep} 上车 -> {arr} 下车 (坐{stops}站)")
                
            # 火车
            elif seg.get("railway") and seg["railway"].get("name"):
                r = seg["railway"]
                name = r.get("name")
                dep = r.get("departure_stop", {}).get("name")
                arr = r.get("arrival_stop", {}).get("name")
                chain.append(name)
                details.append(f"  • 🚄 乘 {name}: {dep} -> {arr}")
                
            # 步行 (只显示长距离步行，忽略换乘那几十米)
            elif seg.get("walking") and int(seg["walking"].get("distance", 0)) > 50:
                d = _fmt_dist(seg["walking"]["distance"])
                details.append(f"  • 🚶 步行 {d}")

        lines.append(f"📍 路线: {' -> '.join(chain)}")
        
        # 仅第一方案显示详情，避免刷屏
        if idx == 0:
            lines.append("📝 详细步骤:")
            lines.extend(details)
            
    return "\n".join(lines)

# ==================== 3. 工具定义 ====================

@mcp.tool()
async def get_location_by_ip(ip: Optional[str] = None) -> str:
    if not AMAP_API_KEY: return "Error: No API Key"
    async with httpx.AsyncClient() as client:
        params = {"key": AMAP_API_KEY, "ip": ip} if ip else {"key": AMAP_API_KEY}
        resp = await client.get(f"{AMAP_API_HOST}/ip", params=params)
        d = resp.json()
        return f"IP定位结果: {d.get('province')}{d.get('city')}"

@mcp.tool()
async def geocode_address(address: str, city: Optional[str] = None) -> str:
    if not AMAP_API_KEY: return "Error: No API Key"
    async with httpx.AsyncClient() as client:
        loc, code, fmt = await _resolve_location(client, address, city)
        if not loc: return "未找到该地址"
        return f"地址: {fmt}\n坐标: {loc}\n区域代码: {code}"

@mcp.tool()
async def regeocode_location(location: str) -> str:
    if not AMAP_API_KEY: return "Error: No API Key"
    try: # 坐标纠错
        p = location.split(',')
        if len(p)==2 and float(p[0]) < float(p[1]) and float(p[1]) > 60: location = f"{p[1]},{p[0]}"
    except: pass
    async with httpx.AsyncClient() as client:
        params = {"key": AMAP_API_KEY, "location": location, "extensions": "base", "output": "JSON"}
        resp = await client.get(f"{AMAP_API_HOST}/geocode/regeo", params=params)
        return f"位置解析: {resp.json().get('regeocode',{}).get('formatted_address')}"

@mcp.tool()
async def plan_route(origin: str, destination: str, mode: str = "driving", city: str = "", strategy: int = 0) -> str:
    """
    [路径规划] 获取详细的导航路线文本描述。
    Args:
        origin: 起点 (坐标 "116.x,40.x" 或 地名)
        destination: 终点 (坐标 "116.x,40.x" 或 地名)
        mode: driving(驾车), transit(公交), walking(步行), bicycling(骑行)
        city: 城市 (公交必填)
        strategy: 公交策略
    """
    if not AMAP_API_KEY: return "Error: No API Key"

    mode_config = {
        "driving":   {"ver": "v3", "url": "/direction/driving"},
        "walking":   {"ver": "v3", "url": "/direction/walking"},
        "transit":   {"ver": "v3", "url": "/direction/transit/integrated"},
        "bicycling": {"ver": "v4", "url": "/direction/bicycling"},
    }
    
    # 别名处理
    if mode in ["car"]: mode = "driving"
    if mode in ["walk"]: mode = "walking"
    if mode in ["bike", "ride", "cycling"]: mode = "bicycling"
    if mode in ["bus", "subway"]: mode = "transit"
    
    cfg = mode_config.get(mode)
    if not cfg: return f"不支持的模式: {mode}"

    try:
        async with httpx.AsyncClient() as client:
            ori_loc, _, ori_name = await _resolve_location(client, origin, city)
            des_loc, _, des_name = await _resolve_location(client, destination, city)
            
            if not ori_loc or not des_loc: return f"无法定位起点({origin})或终点({destination})"

            host = AMAP_API_HOST_V4 if cfg["ver"] == "v4" else AMAP_API_HOST
            params = {"key": AMAP_API_KEY, "origin": ori_loc, "destination": des_loc}
            
            if cfg["ver"] == "v3": params.update({"output": "JSON", "extensions": "all"})
            if mode == "driving": params["strategy"] = 10 
            elif mode == "transit":
                c = city or "北京"
                params.update({"city": c, "cityd": c, "strategy": strategy})

            resp = await client.get(f"{host}{cfg['url']}", params=params)
            raw = resp.json()

            # === 生成文本描述 ===
            result_text = f"【路径规划】\n起点: {ori_name}\n终点: {des_name}\n"

            # 1. 骑行 (V4)
            if cfg["ver"] == "v4":
                if raw.get("errcode") != 0: return f"API错误: {raw.get('errmsg')}"
                paths = raw.get("data", {}).get("paths", [])
                if paths:
                    result_text += _format_nav_text(mode, paths[0])
                else:
                    result_text += "未找到骑行路线"

            # 2. 公交 (V3)
            elif mode == "transit":
                if raw.get("status") != "1": return f"API错误: {raw.get('info')}"
                transits = raw.get("route", {}).get("transits", [])
                result_text += _format_transit_text(transits)

            # 3. 驾车/步行 (V3)
            else:
                if raw.get("status") != "1": return f"API错误: {raw.get('info')}"
                paths = raw.get("route", {}).get("paths", [])
                if paths:
                    result_text += _format_nav_text(mode, paths[0])
                else:
                    result_text += f"未找到{mode}路线"

            return result_text

    except Exception as e:
        return f"Request Error: {str(e)}"

@mcp.tool()
async def poi_search(
    keywords: str = "", 
    city: str = "", 
    center: str = "", 
    radius: int = 3000, 
    polygon: str = "", 
    poi_id: str = "", 
    limit: int = 10
) -> str:
    """
    全能POI搜索工具，自动根据参数切换 4 种高德搜索模式：
    
    1. ID搜索: 提供 poi_id
    2. 多边形搜索: 提供 polygon (格式: "经度,纬度|经度,纬度|...", 至少3个点)
    3. 周边搜索: 提供 center (格式: "经度,纬度")
    4. 关键字搜索: 仅提供 keywords (默认)
    
    Args:
        keywords: 搜索关键字 (模式2,3,4必填)
        city: 城市 (仅关键字搜索生效)
        center: 中心点坐标 (触发周边搜索)
        radius: 搜索半径 (配合center使用)
        polygon: 多边形坐标对 (触发多边形搜索)
        poi_id: 高德POI全局唯一ID (触发ID搜索)
    """
    if not AMAP_API_KEY: return "❌ 错误: 未配置 AMAP_API_KEY。"

    async with httpx.AsyncClient() as client:
        search_mode = "未知"
        params = {
            "key": AMAP_API_KEY,
            "output": "json",
            "extensions": "all"
        }

        # === 模式 1: ID 搜索 (优先级最高) ===
        if poi_id:
            url = f"{AMAP_API_HOST}/place/detail"
            params["id"] = poi_id
            search_mode = f"ID查询({poi_id})"
            
        # === 模式 2: 多边形搜索 (Polygon) ===
        elif polygon:
            if not keywords: return "❌ 错误: 多边形搜索需要 keywords。"
            url = f"{AMAP_API_HOST}/place/polygon"
            params.update({
                "polygon": polygon,
                "keywords": keywords,
                "offset": limit,
                "page": 1
            })
            search_mode = "多边形区域搜索"

        # === 模式 3: 周边搜索 (Around) ===
        elif center:
            if not keywords: return "❌ 错误: 周边搜索需要 keywords。"
            url = f"{AMAP_API_HOST}/place/around"
            params.update({
                "location": center,
                "keywords": keywords,
                "radius": radius,
                "sortrule": "distance",
                "offset": limit,
                "page": 1
            })
            search_mode = f"周边{radius}米"

        # === 模式 4: 关键字搜索 (Text) ===
        elif keywords:
            url = f"{AMAP_API_HOST}/place/text"
            params.update({
                "keywords": keywords,
                "offset": limit,
                "page": 1
            })
            if city:
                params["city"] = city
                params["citylimit"] = "true"
            search_mode = f"城市({city or '全国'})"
        
        else:
            return "❌ 错误: 请至少提供 keywords, center, polygon 或 poi_id 其中之一。"

        # === 执行请求 ===
        try:
            resp = await client.get(url, params=params, timeout=10)
            if resp.status_code != 200: return f"❌ HTTP请求失败: {resp.status_code}"
            
            data = resp.json()
            if data.get("status") != "1": return f"❌ 高德API错误: {data.get('info')}"

            pois = data.get("pois", [])
            
            # 兼容 ID 搜索返回格式 (ID搜索有时直接返回list，有时在pois字段)
            if not pois and search_mode.startswith("ID"):
                 # 有些旧版接口直接返回 list，或者 data 本身就是 dict
                 pass 

            if not pois: return f"⚠️ 在[{search_mode}]未找到相关结果。"

            # === 格式化输出 ===
            result_lines = [f"🔍 [{search_mode}] 找到 {len(pois)} 个结果:"]
            
            for idx, poi in enumerate(pois, 1):
                name = poi.get("name", "未知")
                addr = poi.get("address", "无地址")
                if isinstance(addr, list): addr = "".join(addr)
                
                # 距离 (仅周边搜索有)
                dist_info = ""
                distance = poi.get("distance", "")
                if distance:
                    d_val = float(distance)
                    dist_str = f"{int(d_val)}米" if d_val < 1000 else f"{d_val/1000:.1f}公里"
                    dist_info = f" (📏 距中心 {dist_str})"

                p_type = poi.get("type", "").split(';')[0]
                tel = poi.get("tel", "")
                if isinstance(tel, list): tel = " ".join(tel)
                p_id = poi.get("id", "") # 显示ID，方便后续反查
                
                entry = f"{idx}. **{name}**{dist_info}\n   📍 {addr}\n   🏷️ {p_type} | 🆔 {p_id}"
                if tel: entry += f" | 📞 {tel}"
                
                # 评分与价格
                biz = poi.get("biz_ext", {})
                if isinstance(biz, dict):
                    rating = biz.get("rating")
                    cost = biz.get("cost")
                    if rating and isinstance(rating, str) and rating.replace('.','').isdigit(): 
                        entry += f"\n   ⭐ 评分: {rating}分"
                    if cost and cost != []: 
                        entry += f" | 💰 人均: ¥{cost}"

                result_lines.append(entry)

            return "\n\n".join(result_lines)

        except Exception as e:
            return f"❌ 运行异常: {str(e)}"
