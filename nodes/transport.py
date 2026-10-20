from langgraph.runtime import Runtime
from state import TravelState, TransportOutput
from llm import structured_transport
from prompts_loader import TRANSPORT_PROMPT
from utils.budget_hint import build_budget_hint
from utils.react_runner import run_react

async def transport_node(state: TravelState, runtime: Runtime):
    retry = state.get("retry_count", 0)
    runtime.stream_writer(f"交通规划师正在规划..." if retry == 0 else f"交通规划师正在降级重写（第 {retry} 次）...")

    budget_hint = build_budget_hint(state.get("budget"), state["days"], state["travelers"])
    origin = state.get("origin") or ""
    transport_pref = state.get("transport_preference") or "未指定"

    if origin:
        distance_prompt = f"""请查询从 {origin} 到 {state['destination']} 的驾车距离。
            调用 calculate_distance(
            origin="{origin}",
            destination="{state['destination']}",
            mode="driving"
            )

            【判定标准】
            只要工具成功返回了公里数和预计时间，请立即停止调用工具，直接输出工具返回的原文，不要额外总结。
            """
        distance_info = await run_react(distance_prompt, runtime, " 交通距离查询")
    else:
        distance_info = "（出发地未指定，跳过距离计算）"

    prompt = TRANSPORT_PROMPT.format(
        selected_plan=state["selected_plan"], accommodation=state["accommodation"],
        origin=origin or "未指定", destination=state["destination"],
        days=state["days"], travelers=state["travelers"], budget_hint=budget_hint,
        retry_count=retry, transport_preference=transport_pref, distance_info=distance_info,
    )
    result: TransportOutput = await structured_transport.ainvoke(prompt)
    return {"transport": result.content, "transport_cost": result.total_cost}