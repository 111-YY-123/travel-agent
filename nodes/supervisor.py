from datetime import datetime
from typing import Literal, Optional
from langgraph.runtime import Runtime
from langgraph.types import Command, Send, interrupt
from state import TravelState, TravelIntent
from llm import structured_supervisor
from prompts_loader import SUPERVISOR_PROMPT
from utils.logger_handler import get_logger

logger = get_logger("travel")

_PREF_TO_NODE = {"美食": "food_node", "自然": "nature_node", "人文": "culture_node", "商业": "business_node"}
_DEFAULT_PREFS = ["美食", "自然", "人文", "商业"]

def _validate_fields(days, travelers, budget):
    if days is None or days < 1: days = 3
    elif days > 30: days = 30
    if travelers is None or travelers < 1: travelers = 1
    elif travelers > 20: travelers = 20
    if budget is not None and budget < 0: logger.warning(f"负数预算 {budget}")
    return days, travelers, budget

def _sanitize_preferences(preferences):
    valid = set(_PREF_TO_NODE.keys())
    cleaned = [p for p in (preferences or _DEFAULT_PREFS) if p in valid]
    if not cleaned:
        logger.warning("preferences 非法，回退到全选")
        cleaned = list(_DEFAULT_PREFS)
    return cleaned

def _resolve_start_date(raw_date: Optional[str]) -> str:
    if not raw_date: return datetime.now().strftime("%Y-%m-%d")
    try:
        return datetime.strptime(raw_date, "%Y-%m-%d").strftime("%Y-%m-%d")
    except ValueError:
        logger.warning(f"日期格式非法 {raw_date}，用今天代替")
        return datetime.now().strftime("%Y-%m-%d")

async def supervisor_node(
    state: TravelState, runtime: Runtime
) -> Command[Literal["food_node", "nature_node", "culture_node", "business_node", "__end__"]]:
    runtime.stream_writer("解析需求")
    today_str = datetime.now().strftime("%Y-%m-%d")

    intent: TravelIntent = await structured_supervisor.ainvoke(
        SUPERVISOR_PROMPT.format(user_request=state["user_request"], today=today_str)
    )
    logger.debug(f"LLM 解析结果 | {intent.model_dump()}")

    origin = intent.origin or state.get("origin")
    destination = intent.destination or state.get("destination")
    days = intent.days or state.get("days") or 3
    travelers = intent.travelers or state.get("travelers") or 1
    budget = intent.budget if intent.budget is not None else state.get("budget")
    start_date = _resolve_start_date(intent.start_date or state.get("start_date"))
    transport_preference = intent.transport_preference or state.get("transport_preference")
    preferences = _sanitize_preferences(intent.preferences or state.get("preferences"))
    days, travelers, budget = _validate_fields(days, travelers, budget)

    user_request_final = state["user_request"]

    if not destination:
        logger.warning("未识别到目的地，中断")
        runtime.stream_writer("等待补充目的地...")
        user_reply = interrupt({"type": "missing_destination", "question": "请补充目的地（如：上海、三亚）"})
        if not user_reply or not user_reply.strip():
            return Command(goto="__end__")

        user_request_final = state.get("user_request", "") + f"。补充：{user_reply}"
        intent = await structured_supervisor.ainvoke(
            SUPERVISOR_PROMPT.format(user_request=user_request_final, today=today_str)
        )
        origin = intent.origin or origin
        destination = intent.destination or destination
        days = intent.days or days
        travelers = intent.travelers or travelers
        budget = intent.budget if intent.budget is not None else budget
        start_date = _resolve_start_date(intent.start_date or start_date)
        preferences = _sanitize_preferences(intent.preferences or preferences)
        transport_preference = intent.transport_preference or transport_preference
        days, travelers, budget = _validate_fields(days, travelers, budget)

    if not destination:
        return Command(goto="__end__")

    has_old = bool(state.get("final_itinerary"))
    is_new_trip = not has_old or (intent.destination is not None and intent.destination != state.get("destination"))

    updates = {
        "user_request": user_request_final, "retry_count": 0, "budget_approved": False,
        "origin": origin, "destination": destination, "days": days, "travelers": travelers,
        "budget": budget, "start_date": start_date, "preferences": preferences,
        "transport_preference": transport_preference, "candidate_plans": ["__RESET__"],
    }
    if is_new_trip: updates["previous_itinerary"] = ""

    updated_state = {**state, **updates, "candidate_plans": []}
    sends = [Send(_PREF_TO_NODE[p], updated_state) for p in preferences]

    runtime.stream_writer(f"派发 {len(sends)} 个规划师：{preferences}")
    return Command(update=updates, goto=sends)