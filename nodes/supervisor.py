# nodes/supervisor.py
from typing import Literal
from langgraph.runtime import Runtime
from langgraph.types import Command, Send, interrupt
from state import TravelState, TravelIntent
from llm import structured_supervisor
from prompts_loader import SUPERVISOR_PROMPT
from utils.logger_handler import get_logger

logger = get_logger("travel")

_PREF_TO_NODE = {
    "美食": "food_node",
    "自然": "nature_node",
    "人文": "culture_node",
    "商业": "business_node",
}

_DEFAULT_PREFS = ["美食", "自然", "人文", "商业"]


def _validate_fields(days, travelers, budget):
    """校验数值字段，防止 LLM 返回异常值"""
    if days is None or days < 1:
        days = 3
    elif days > 30:
        days = 30
    if travelers is None or travelers < 1:
        travelers = 1
    elif travelers > 20:
        travelers = 20
    if budget is not None and budget < 0:
        logger.warning(f"用户填写负数预算 {budget}，保留原值交由下游处理")
    return days, travelers, budget

def _sanitize_preferences(preferences):
    """清洗 preferences：过滤非法值，空则回退到默认全选。

    返回的 list 保证：
    - 非空
    - 每一项都在 _PREF_TO_NODE 里
    """
    valid = set(_PREF_TO_NODE.keys())
    cleaned = [p for p in (preferences or _DEFAULT_PREFS) if p in valid]
    if not cleaned:
        logger.warning("preferences 未匹配任何标准值，回退到全选")
        cleaned = list(_DEFAULT_PREFS)
    return cleaned

async def supervisor_node(
    state: TravelState, runtime: Runtime
) -> Command[Literal["food_node", "nature_node", "culture_node", "business_node", "__end__"]]:
    """Supervisor 节点：解析需求 + 路由决策 + 并行派发。

    职责：
    1. 用 LLM 解析用户自然语言为结构化字段（TravelIntent）
    2. 根据 preferences 动态决定派发给哪些规划师
    3. 用 Send 并行扇出

    不负责汇总（synthesizer）、不负责决策（budget_reviewer）、不负责执行（规划师）。
    """
    runtime.stream_writer("解析需求")
    logger.info(f"supervisor 开始 | user_request={state['user_request'][:50]}")

    intent: TravelIntent = await structured_supervisor.ainvoke(
        SUPERVISOR_PROMPT.format(user_request=state["user_request"])
    )

    logger.debug(f"LLM 解析结果 | {intent.model_dump()}")

    # 增量合并
    origin = intent.origin or state.get("origin")
    destination = intent.destination or state.get("destination")
    days = intent.days or state.get("days") or 3
    travelers = intent.travelers or state.get("travelers") or 1
    budget = intent.budget if intent.budget is not None else state.get("budget")  
    transport_preference = intent.transport_preference or state.get("transport_preference")
    preferences = _sanitize_preferences(
        intent.preferences or state.get("preferences")
    )
    days, travelers, budget = _validate_fields(days, travelers, budget)

    user_request_final = state["user_request"]

    if not destination:
        logger.warning("未识别到目的地，触发中断询问")
        runtime.stream_writer("⚠️ 等待用户补充目的地...")

        user_reply = interrupt({
            "type": "missing_destination",
            "question": "请补充你想去的目的地（如：上海、三亚）",
        })

        logger.info(f"用户回复 | {user_reply}")

        if not user_reply or not user_reply.strip():
            logger.error("用户补充为空，终止流程")
            runtime.stream_writer("❌ 未获得有效补充，请重新发起对话")
            return Command(goto="__end__")

        user_request_final = state.get("user_request", "") + f"。补充：{user_reply}"
        intent = await structured_supervisor.ainvoke(
            SUPERVISOR_PROMPT.format(user_request=user_request_final)
        )

        logger.debug(f"重解析结果 | {intent.model_dump()}") 

        origin = intent.origin or origin
        destination = intent.destination or destination
        days = intent.days or days
        travelers = intent.travelers or travelers
        budget = intent.budget if intent.budget is not None else budget
        preferences = _sanitize_preferences(intent.preferences or preferences)
        transport_preference = intent.transport_preference or transport_preference  

        days, travelers, budget = _validate_fields(days, travelers, budget)      
    
    if not destination:
        logger.error("中断补充后仍未识别到目的地")
        runtime.stream_writer("❌ 未能识别目的地，请重新发起对话")
        return Command(goto="__end__")

    logger.info(
        f"解析结果 | origin={origin}, destination={destination}, "
        f"days={days}, travelers={travelers}, "
        f"budget={budget}, preferences={preferences}"
    )

    has_old = bool(state.get("final_itinerary"))
    is_new_trip = (
        not has_old
        or (intent.destination is not None and intent.destination != state.get("destination"))
    )

    updates = {
        "user_request": user_request_final,
        "retry_count": 0,
        "budget_approved": False,
        "origin": origin,
        "destination": destination,
        "days": days,
        "travelers": travelers,
        "budget": budget,
        "preferences": preferences,
        "transport_preference": transport_preference,
        "candidate_plans": ["__RESET__"],# 通过 Command(update) 传给 plans_reducer 触发清空
    }
    
    if is_new_trip:
        updates["previous_itinerary"] = ""
        logger.info("全新需求，清空 previous_itinerary")

    updated_state = {**state, **updates, "candidate_plans": []}# updated_state 是传给各规划师的初始 state，

    sends = [
        Send(_PREF_TO_NODE[p], updated_state)
        for p in preferences
    ]

    if not sends:
        logger.error("sends 为空，preferences 清洗逻辑有 bug")
        return Command(goto="__end__")

    runtime.stream_writer(f"派发 {len(sends)} 个规划师：{preferences}")
    logger.info(f"派发 {len(sends)} 个规划师 | preferences={preferences}")

    return Command(update=updates, goto=sends)