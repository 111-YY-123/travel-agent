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

    logger.info(f"====== 各规划师输出量监控 ======")
    total_len = 0
    for plan in state["candidate_plans"]:
        # 截取前几个字作为名字，比如【美食路线】
        name = plan.split("\n")[0].replace("【", "").replace("】", "") if plan.startswith("【") else "未知"
        length = len(plan)
        total_len += length
        logger.info(f"[{name}] 输出量: {length} 字符")
        
        # ========== 新增：单独打印美食路线全部输出 ==========
        if "美食" in name:
            logger.info(f"\n========== 美食路线完整输出开始 ==========\n{plan}\n========== 美食路线完整输出结束 ==========\n")
            
    logger.info(f"总计输入上下文: {total_len} 字符")
    logger.info(f"===============================")

    budget_hint = build_budget_hint(state.get("budget"), state["days"], state["travelers"])
    logger.info(f"综合输入监控 | plans_text 长度 = {len(plans_text)} 字符")

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

    logger.info(f"综合输入监控 | 最终 prompt 总长度 = {len(prompt)} 字符")
    result: SynthesizerOutput = await structured_synthesizer.ainvoke(prompt)

    logger.info(f"synthesizer 完成 | 输出长度={len(result.plan)}")
    return {
        "selected_plan": result.plan,
        "food_cost": result.food_cost,
        "ticket_cost": result.ticket_cost,
        "candidate_plans": ["__RESET__"],
    }