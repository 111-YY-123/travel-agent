# nodes/food.py
from langgraph.runtime import Runtime
from state import TravelState
from llm import model
from prompts_loader import FOOD_PROMPT
from utils.budget_hint import build_budget_hint
from utils.logger_handler import get_logger

logger = get_logger("travel")


async def food_node(state: TravelState, runtime: Runtime):
    runtime.stream_writer("🍜 美食规划师正在规划...")
    logger.info("food_node 开始")

    budget_hint = build_budget_hint(state.get("budget"), state["days"], state["travelers"])
    prompt = FOOD_PROMPT.format(
        user_request=state["user_request"],
        destination=state["destination"],
        days=state["days"],
        travelers=state["travelers"],
        budget_hint=budget_hint,
    )
    result = await model.ainvoke(prompt)

    logger.info(f"food_node 完成 | 输出长度={len(result.content)}")
    return {"candidate_plans": [f"【美食路线】\n{result.content}"]}