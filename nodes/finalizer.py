# nodes/finalizer.py
from langgraph.runtime import Runtime
from state import TravelState
from llm import model
from prompts_loader import FINALIZER_PROMPT
from utils.logger_handler import get_logger

logger = get_logger("travel")


async def finalizer_node(state: TravelState, runtime: Runtime):
    runtime.stream_writer("正在生成最终行程单...")

    total_cost = state.get("total_cost", 0.0)
    logger.info(f"finalizer 开始 | total_cost={total_cost:.0f}")

    budget_value = state.get("budget")
    if budget_value is None:
        budget_str = "未指定"
    elif budget_value <= 0:
        budget_str = f"{budget_value}（无效）"
    else:
        budget_str = str(budget_value)

    prompt = FINALIZER_PROMPT.format(
        user_request=state.get("user_request", ""),
        destination=state.get("destination", ""),
        days=state.get("days", 3),
        travelers=state.get("travelers", 1),
        selected_plan=state.get("selected_plan", ""),
        accommodation=state.get("accommodation", ""),
        transport=state.get("transport", ""),
        total_cost= total_cost,
        budget=budget_str,
        budget_note=state.get("budget_note", "无预算审查说明"),
        budget_approved=state.get("budget_approved", False),
    )
    result = await model.ainvoke(prompt)

    logger.info(f"finalizer 完成 | 输出长度={len(result.content)}")
    return {
        "final_itinerary": result.content,
        "previous_itinerary": state.get("final_itinerary", ""),
    }