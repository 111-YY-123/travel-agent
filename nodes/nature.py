# nodes/nature.py
from langgraph.runtime import Runtime
from state import TravelState
from llm import model, model_with_tools
from tools import TOOLS_BY_NAME
from prompts_loader import NATURE_PROMPT
from utils.budget_hint import build_budget_hint
from utils.logger_handler import get_logger

logger = get_logger("travel")


async def nature_node(state: TravelState, runtime: Runtime):
    runtime.stream_writer("🏞️ 自然规划师正在规划...")
    logger.info("nature_node 开始")

    destination = state["destination"]
    budget_hint = build_budget_hint(state.get("budget"), state["days"], state["travelers"])
    
    prompt_base = NATURE_PROMPT.format(
        user_request=state["user_request"],
        destination=state["destination"],
        days=state["days"],
        travelers=state["travelers"],
        budget_hint=budget_hint,
    )

    logger.info(f"nature_node 触发天气查询 | destination={destination}")
    response = await model_with_tools.ainvoke(prompt_base)

    if response.tool_calls:
        tool_names = [tc["name"] for tc in response.tool_calls]
        logger.info(f"nature_node 触发工具调用 | {tool_names}")
        runtime.stream_writer(f"🔧 自然规划师正在调用工具：{tool_names}")

        tool_results = []
        for tc in response.tool_calls:
            tool = TOOLS_BY_NAME[tc["name"]]
            result = await tool.ainvoke(tc["args"])
            logger.info(f"工具 {tc['name']} 返回 | {result[:80]}")
            tool_results.append(f"工具 {tc['name']} 返回：{result}")
            
        enriched_prompt = prompt_base + "\n\n【工具返回的实时信息】\n" + "\n".join(tool_results)
        response = await model.ainvoke(enriched_prompt)

    logger.info(f"nature_node 完成 | 输出长度={len(response.content)}")
    return {"candidate_plans": [f"【自然路线】\n{response.content}"]}