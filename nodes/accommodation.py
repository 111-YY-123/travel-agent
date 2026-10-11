# nodes/accommodation.py
from langgraph.runtime import Runtime
from state import TravelState, AccommodationOutput
from llm import structured_accommodation
from prompts_loader import ACCOMMODATION_PROMPT
from utils.budget_hint import build_budget_hint
from utils.logger_handler import get_logger

logger = get_logger("travel")


async def accommodation_node(state: TravelState, runtime: Runtime):
    """住宿规划师：根据行程推荐住宿区域和档次；retry > 0 时降级。"""
    retry = state.get("retry_count", 0)
    if retry > 0:
        runtime.stream_writer(f"🏨 住宿规划师正在降级重写（第 {retry} 次）...")
    else:
        runtime.stream_writer("🏨 住宿规划师正在规划...")
    logger.info(f"accommodation_node 开始 | retry={retry}")

    budget_hint = build_budget_hint(state.get("budget"), state["days"], state["travelers"])
    prompt = ACCOMMODATION_PROMPT.format(
        user_request=state["user_request"],
        selected_plan=state["selected_plan"],
        destination=state["destination"],
        days=state["days"],
        travelers=state["travelers"],
        budget_hint=budget_hint,
        retry_count=retry,
    )
    result: AccommodationOutput = await structured_accommodation.ainvoke(prompt)

    logger.info(f"accommodation_node 完成 | total_cost={result.total_cost}")
    return {
        "accommodation": result.content,
        "accommodation_cost": result.total_cost,
    }