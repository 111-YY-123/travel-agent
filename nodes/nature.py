from langchain_core.messages import HumanMessage, ToolMessage
from langgraph.runtime import Runtime
from state import TravelState
from llm import model_with_tools
from tools import TOOLS_BY_NAME
from prompts_loader import NATURE_PROMPT
from utils.budget_hint import build_budget_hint
from utils.logger_handler import get_logger

logger = get_logger("travel")

# 防止 LLM 无限调用工具
MAX_TOOL_ROUNDS = 5


async def nature_node(state: TravelState, runtime: Runtime):
    runtime.stream_writer("🏞️ 自然规划师正在规划...")
    logger.info("nature_node 开始")

    destination = state["destination"]
    budget_hint = build_budget_hint(
        state.get("budget"), state["days"], state["travelers"]
    )

    prompt = NATURE_PROMPT.format(
        user_request=state["user_request"],
        destination=state["destination"],
        days=state["days"],
        travelers=state["travelers"],
        budget_hint=budget_hint,
        start_date=state["start_date"],
    )

    # ========== ReAct 循环 ==========
    messages = [HumanMessage(content=prompt)]
    response = None

    for round_idx in range(MAX_TOOL_ROUNDS):
        response = await model_with_tools.ainvoke(messages)
        messages.append(response)

        # LLM 不再要求调工具 → 结束循环
        if not response.tool_calls:
            break

        tool_names = [tc["name"] for tc in response.tool_calls]
        logger.info(f"nature_node 第 {round_idx + 1} 轮 | 调用工具 {tool_names}")
        runtime.stream_writer(f"🔧 自然规划师调用工具：{tool_names}")

        # 逐个执行工具，把结果塞回 messages
        for tc in response.tool_calls:
            tool = TOOLS_BY_NAME.get(tc["name"])
            if tool is None:
                result = f"未知工具：{tc['name']}"
            else:
                result = await tool.ainvoke(tc["args"])
                logger.info(f"工具 {tc['name']} 返回 | {str(result)[:80]}")

            messages.append(
                ToolMessage(content=str(result), tool_call_id=tc["id"])
            )
    else:
        # for 循环跑满都没 break（说明 LLM 还在要求工具）
        logger.warning(f"nature_node 达到工具调用上限 {MAX_TOOL_ROUNDS} 轮，强制结束")
        runtime.stream_writer(f"⚠️ 自然规划师达到工具调用上限，停止")

    content = response.content if response else "（无输出）"
    logger.info(f"nature_node 完成 | 输出长度={len(content)}")
    return {"candidate_plans": [f"【自然路线】\n{content}"]}