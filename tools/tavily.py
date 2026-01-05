import httpx
import os
import json
try:
    from . import mcp
except ImportError:
    from mcp.server.fastmcp import FastMCP
    mcp = FastMCP("Tavily Search")

# 读取多个Key
env_keys = os.getenv("TAVILY_API_KEYS", "")
KEY_POOL = [k.strip() for k in env_keys.split(",") if k.strip()]
CURRENT_KEY_INDEX = 0

@mcp.tool()
async def web_search(query: str, search_depth: str = "basic", include_answer: bool = True) -> str:
    """
    Tavily 联网搜索 (双Key自动切换版)。
    如果第一个Key额度用完，会自动切换到第二个。
    """
    global CURRENT_KEY_INDEX
    if not KEY_POOL: return "❌ 未配置 TAVILY_API_KEYS"

    url = "https://api.tavily.com/search"
    base_payload = {
        "query": query, "search_depth": search_depth, 
        "include_answer": include_answer, "max_results": 5
    }

    async with httpx.AsyncClient() as client:
        # 循环尝试机制
        while CURRENT_KEY_INDEX < len(KEY_POOL):
            current_key = KEY_POOL[CURRENT_KEY_INDEX]
            payload = base_payload.copy()
            payload["api_key"] = current_key

            try:
                resp = await client.post(url, json=payload, timeout=30)
                
                # 成功直接返回
                if resp.status_code == 200:
                    return _format_result(resp.json())
                
                # 失败(429/401)则切换下一个Key
                elif resp.status_code in [401, 403, 429]:
                    print(f"⚠️ Key[{CURRENT_KEY_INDEX}]额度耗尽，切换下一个...")
                    CURRENT_KEY_INDEX += 1
                    continue
                else:
                    return f"❌ 搜索失败: {resp.status_code}"
            except Exception as e:
                return f"❌ 运行错误: {str(e)}"
        
        return "❌ 所有Key额度均已耗尽。"

def _format_result(data: dict) -> str:
    lines = []
    if data.get("answer"):
        lines.append(f"🤖 **智能总结**:\n{data.get('answer')}\n" + "-"*20)
    
    for idx, item in enumerate(data.get("results", []), 1):
        lines.append(f"{idx}. **[{item.get('title')}]({item.get('url')})**\n   > {item.get('content', '')[:200]}...")
    
    return "\n".join(lines) if lines else "⚠️ 无结果"
