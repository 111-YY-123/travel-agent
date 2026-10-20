from langgraph.runtime import Runtime
from state import TravelState
from prompts_loader import NATURE_PROMPT
from utils.budget_hint import build_budget_hint
from utils.react_runner import run_react

async def nature_node(state: TravelState, runtime: Runtime):
    runtime.stream_writer("自然规划师正在规划...")
    budget_hint = build_budget_hint(state.get("budget"), state["days"], state["travelers"])
    prompt = NATURE_PROMPT.format(
        user_request=state["user_request"], destination=state["destination"],
        days=state["days"], travelers=state["travelers"], budget_hint=budget_hint,
        start_date=state["start_date"],
    )
    content = await run_react(prompt, runtime, "自然规划师")
    return {"candidate_plans": [f"【自然路线】\n{content}"]}