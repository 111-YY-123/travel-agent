# nodes/transport.py
from langgraph.runtime import Runtime
from state import TravelState, TransportOutput
from llm import structured_transport
from prompts_loader import TRANSPORT_PROMPT
from utils.budget_hint import build_budget_hint
from utils.logger_handler import get_logger

logger = get_logger("travel")


async def transport_node(state: TravelState, runtime: Runtime):
    """交通规划师：根据住宿位置和行程规划大交通 + 本地交通；retry > 0 时降级。"""
    retry = state.get("retry_count", 0)
    if retry > 0:
        runtime.stream_writer(f"🚗 交通规划师正在降级重写（第 {retry} 次）...")
    else:
        runtime.stream_writer("🚗 交通规划师正在规划...")
    logger.info(f"transport_node 开始 | retry={retry}")

    budget_hint = build_budget_hint(state.get("budget"), state["days"], state["travelers"])
    prompt = TRANSPORT_PROMPT.format(
        selected_plan=state["selected_plan"],
        accommodation=state["accommodation"],
        origin=state.get("origin") or "未指定",
        destination=state["destination"],
        days=state["days"],
        travelers=state["travelers"],
        budget_hint=budget_hint,
        retry_count=retry,
        transport_preference=state.get("transport_preference") or "未指定",
    )
    result: TransportOutput = await structured_transport.ainvoke(prompt)

    logger.info(f"transport_node 完成 | total_cost={result.total_cost}")
    return {
        "transport": result.content,
        "transport_cost": result.total_cost,
    }