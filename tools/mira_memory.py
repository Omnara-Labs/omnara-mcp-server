import os
import json
import re
from pathlib import Path
from datetime import datetime, timedelta
from openai import OpenAI
from . import mcp

# ========== 1. 基础配置 ==========
try:
    MEM_BASE_DIR = Path(os.getenv("MIRA_MEM_DIR", "/mem0"))
    ENTITY_DIR = MEM_BASE_DIR / "entities"
    RELATIONS_PATH = MEM_BASE_DIR / "relations.json"
    INDEX_PATH = MEM_BASE_DIR / "entity_index.json"

    client = OpenAI(
        base_url=os.getenv("DEEPSEEK_BASE_URL", "https://openrouter.ai/api/v1"),
        api_key=os.getenv("DEEPSEEK_API_KEY")
    )
    
    MODEL_NAME = os.getenv("MIRA_MODEL", "deepseek-reasoner")
    MAX_TOKENS = int(os.getenv("MIRA_MAX_TOKENS", "8192"))
except Exception as e:
    print(f"❌ 配置加载错误: {e}")

def call_mira_brain(system_prompt, user_input):
    """大模型调用封装"""
    try:
        completion = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_input}
            ],
            max_tokens=MAX_TOKENS,
            timeout=180
        )
        return completion.choices[0].message.content
    except Exception as e:
        return f"⚠️ 意识连接中断: {str(e)}"

@mcp.tool()
def ask_mira_memory(question: str) -> str:
    """
    一个由DeepSeek V3.2驱动的记忆检索工具。它能访问用户的私人记忆，专门分析用户私人记忆中的实体关系图谱和实体时间流。每当用户提到过去的事件、特定的人或个人历史时（只要和用户有关系），请使用此工具。它能返回经过综合分析的、具有上下文意识的答案，以理清你回答时所需的背景信息。
    """
    try:
        # 0. 基础检查
        if not INDEX_PATH.exists() or not RELATIONS_PATH.exists():
            return "❌ 记忆系统未就绪：找不到索引或关系文件。"

        # 1. 获取当前时间锚点
        now = datetime.now()
        current_time_str = now.strftime("%Y-%m-%d %A %H:%M:%S")
        today_date = now.strftime("%Y-%m-%d")
        today_weekday = now.strftime("%A")

        # 2. 加载索引
        with open(RELATIONS_PATH, 'r', encoding='utf-8') as f:
            relations = json.load(f)
        with open(INDEX_PATH, 'r', encoding='utf-8') as f:
            index_data = json.load(f).get("entities", {})

        # 3. 路由决策
        print(f"🧠 [Mira] 收到提问: {question}")
        entity_keys = list(index_data.keys())
        
        decision_prompt = (
            f"现在时间是: {current_time_str}。\n"
            f"你是记忆调度员。请从已知实体列表中，选出回答问题 '{question}' 必须查看的实体。\n"
            f"实体列表: {entity_keys}\n"
            f"要求：只返回实体名称，用逗号分隔。如果没有相关的，返回 NONE。"
        )
        
        selected_raw = call_mira_brain(decision_prompt, "请提供实体名单")
        if not selected_raw: selected_raw = ""
        selected_names = [n.strip() for n in selected_raw.split(",") if n.strip() in index_data]
        
        # 4. 读取详情并排序
        flesh_content = ""
        for name in selected_names:
            path = ENTITY_DIR / f"{index_data[name]['file_id']}.json"
            if path.exists():
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    
                    temp_events = []
                    raw_events = data.get('events', [])
                    if isinstance(raw_events, list):
                        for ev in raw_events:
                            if isinstance(ev, dict):
                                t_str = ev.get('timestamp', '1970-01-01 00:00:00')
                                content = ev.get('content', '')
                                temp_events.append({"t": t_str, "c": content})
                    
                    temp_events.sort(key=lambda x: x["t"])

                    formatted_lines = []
                    for ev in temp_events:
                        formatted_lines.append(f"[{ev['t']}] {ev['c']}")
                    
                    flesh_content += f"\n=== [{name}] 的时间流 (已按时间正序排列) ===\n" + "\n".join(formatted_lines) + "\n"

        # 5. 综合生成 (Prompt 已包含 today_weekday)
        print(f"💬 [Mira] 正在生成回答...")
        
        synthesis_prompt = f"""
你现在是用户的专属助理 Mira。请根据记忆库回答问题。

【当前系统时间 (Now)】
{current_time_str}
(注意：今天是 {today_weekday})

【⚠️ 核心指令：时间线推演】
你必须严格按照以下逻辑计算，禁止臆造日历：

1. **基准计算**：
   - 记忆行开头的 `[时间戳]` 是计算原点。
   - "明天" = 时间戳 + 1天。
   - "后天" = 时间戳 + 2天。
   - "周六" = 寻找该时间戳之后的第一个周六。

2. **星期几的强制对齐**：
   - 如果记忆中提到具体星期（如"周六"），且推算出的日期正好是【今天】，**必须**判定为“就是今天”。
   - **严禁**出现"明天是周六"这种错误（因为系统时间明确显示今天是 {today_weekday}）。

3. **最终时态输出**：
   - 计算结果 < 今天 -> 说 **"昨天"** 或 **"之前"**。
   - 计算结果 == 今天 -> 说 **"就是今天"**。
   - 计算结果 > 今天 -> 说 **"明天"** 或 **"未来"**。

【示例修正】
假设今天是 12月20日 (周六)。
- 错误思维：看到"周六去探望"，以为是下一个周六，回答"下周去"。
- 正确思维：记忆(18日)说"周六去" -> 18+2=20日 -> 20日是周六 -> 20日==今天 -> 回答：**"计划就是今天(周六)晚上去探望"**。

【相关实体记忆】
{flesh_content}

【关系图谱片段】
{json.dumps(relations, ensure_ascii=False)}

目标：提供一份逻辑严谨、内容准确、深入本质且带有温度的分析总结。
"""
        return call_mira_brain(synthesis_prompt, question)

    except Exception as e:
        import traceback
        traceback.print_exc()
        return f"❌ 记忆模块发生内部错误: {str(e)}"
