from dotenv import load_dotenv
load_dotenv()

from tools import mcp
import importlib
import pkgutil
from pathlib import Path

def load_tools():
    tools_dir = Path(__file__).parent / "tools"
    loaded_count = 0  # 手动计数器
    
    for module_info in pkgutil.iter_modules([str(tools_dir)]):
        module_name = module_info.name
        if module_name.startswith('_'):
            continue
        
        importlib.import_module(f"tools.{module_name}")
        print(f"✓ 已加载: {module_name}")
        loaded_count += 1  # 每加载一个模块就计数
    
    return loaded_count  # 返回总数

if __name__ == "__main__":
    tool_count = load_tools()  # 直接获取计数结果
    print(f"🚀 服务器启动，共 {tool_count} 个工具")
    mcp.run(transport="sse", host="0.0.0.0", port=6537)
