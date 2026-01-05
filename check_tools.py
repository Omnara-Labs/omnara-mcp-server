#!/usr/bin/env python3
import asyncio
import aiohttp
from mcp import ClientSession
from mcp.client.sse import sse_client

MCP_SSE_URL = "https://mcp.domain-name/sse"

async def main():
    print(f"正在连接 MCP 服务器: {MCP_SSE_URL} ...")
    
    try:
        # 连接 MCP
        async with aiohttp.ClientSession() as http_session:
            async with sse_client(MCP_SSE_URL, headers={"User-Agent": "ToolChecker"}) as streams:
                async with ClientSession(streams[0], streams[1]) as session:
                    await session.initialize()
                    
                    # 获取工具列表
                    result = await session.list_tools()
                    tools = result.tools
                    
                    print(f"\n✅ 成功连接！共发现 {len(tools)} 个工具：\n")
                    print("="*50)
                    
                    # 打印方便复制的格式
                    print("【建议复制以下内容到.env中】\n")
                    print("mcp:")
                    print("  allowed_tools:")
                    for tool in tools:
                        print(f"    - \"{tool.name}\"  # {tool.description[:50]}...")
                    
                    print("="*50)

    except Exception as e:
        print(f"❌ 连接失败: {e}")
        print("请检查：")
        print("1. MCP 服务端是否已运行？")
        print("2. 端口 6537 是否正确？")

if __name__ == "__main__":
    asyncio.run(main())
