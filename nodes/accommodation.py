from langgraph.runtime import Runtime
from state import TravelState, AccommodationOutput
from llm import structured_accommodation
from prompts_loader import ACCOMMODATION_PROMPT, ACCOMMODATION_SEARCH_PROMPT
from utils.budget_hint import build_budget_hint
from utils.react_runner import run_react

async def accommodation_node(state: TravelState, runtime: Runtime):
    retry = state.get("retry_count", 0)
    runtime.stream_writer(f"住宿规划师正在规划..." if retry == 0 else f"住宿规划师正在降级重写（第 {retry} 次）...")
    
    budget_hint = build_budget_hint(state.get("budget"), state["days"], state["travelers"])

    if retry == 0:
        keyword_hint = '"酒店" 或 "民宿"'
        budget_note = "按用户预算正常推荐"
    elif retry == 1:
        keyword_hint = '"经济型酒店" 或 "民宿"'
        budget_note = "**必须降一级**"
    else:
        keyword_hint = '"青旅" 或 "民宿"'
        budget_note = "**必须给最便宜**"

    search_prompt = ACCOMMODATION_SEARCH_PROMPT.format(
        destination=state["destination"], user_request=state["user_request"],
        travelers=state["travelers"], days=state["days"], budget_hint=budget_hint,
        retry=retry, budget_note=budget_note, keyword_hint=keyword_hint,
    )
    hotel_info = await run_react(search_prompt, runtime, "住宿查询")

    prompt = ACCOMMODATION_PROMPT.format(
        user_request=state["user_request"], selected_plan=state["selected_plan"],
        destination=state["destination"], days=state["days"], travelers=state["travelers"],
        budget_hint=budget_hint, retry_count=retry, hotel_info=hotel_info,
    )
    result: AccommodationOutput = await structured_accommodation.ainvoke(prompt)
    return {"accommodation": result.content, "accommodation_cost": result.total_cost}