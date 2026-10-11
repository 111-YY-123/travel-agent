# nodes/synthesizer.py
from langgraph.runtime import Runtime
from state import TravelState, SynthesizerOutput
from llm import structured_synthesizer
from prompts_loader import SYNTHESIZER_PROMPT
from utils.budget_hint import build_budget_hint
from utils.logger_handler import get_logger

logger = get_logger("travel")


async def synthesizer_node(state: TravelState, runtime: Runtime):
    """综合节点：合并所有规划师的方案，输出 selected_plan + 费用明细。"""
    plans_count = len(state["candidate_plans"])
    runtime.stream_writer(f"正在综合 {plans_count} 个方案...")
    logger.info(f"synthesizer 开始 | plans_count={plans_count}")

    plans_text = "\n\n".join(state["candidate_plans"])
    budget_hint = build_budget_hint(state.get("budget"), state["days"], state["travelers"])

    prompt = SYNTHESIZER_PROMPT.format(
        user_request=state["user_request"],
        destination=state["destination"],
        days=state["days"],
        travelers=state["travelers"],
        budget_hint=budget_hint,
        plans_text=plans_text,
        plans_count=plans_count,
        previous_itinerary=state.get("previous_itinerary") or "（首次生成，无上一版）"
    )

    result: SynthesizerOutput = await structured_synthesizer.ainvoke(prompt)

    logger.info(f"synthesizer 完成 | 输出长度={len(result.plan)}")
    return {
        "selected_plan": result.plan,
        "food_cost": result.food_cost,
        "ticket_cost": result.ticket_cost,
        "candidate_plans": ["__RESET__"],
    }