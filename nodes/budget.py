# nodes/budget.py
from typing import Literal
from langgraph.runtime import Runtime
from langgraph.types import Command
from state import TravelState
from utils.logger_handler import get_logger

logger = get_logger("travel")

 
async def budget_reviewer_node(
    state: TravelState, runtime: Runtime
) -> Command[Literal["finalizer", "accommodation_node"]]:
    """预算审查节点：真实算账 + 动态打回。

    决策规则：
    - total <= budget：通过，去 finalizer
    - total > budget 且 retry < 2：打回 accommodation，retry_count +1
    - total > budget 且 retry >= 2：强制输出，标记 budget_approved=False
    """
    total_cost = (
        (state.get("food_cost") or 0)
        + (state.get("ticket_cost") or 0)
        + (state.get("accommodation_cost") or 0)
        + (state.get("transport_cost") or 0)
    )

    budget = state.get("budget")
    retry = state.get("retry_count", 0)

    logger.info(f"预算审查 | total={total_cost:.0f}, budget={budget}, retry={retry}")

    if budget is not None and budget < 0:
        note = (
            f"您填写的预算 {budget} 元为负数（无效输入），"
            f"已按「未指定预算」处理，方案按中等舒适标准生成。请确认是否输入有误。"
        )
        logger.warning(f"预算为负数 {budget}，按未指定处理")
        runtime.stream_writer(f"⚠️ 预算 {budget} 元为负数，已按未指定处理")
        return Command(
            goto="finalizer",
            update={
                "total_cost": total_cost,
                "budget_approved": False,
                "budget_note": note,
            },
        )    

    if budget is not None and budget == 0:
        note = f"预算 {budget} 元为不可满足约束（数学上不可能满足），未尝试降级。"
        logger.warning(f"预算 = 0，跳过重试，直接输出")
        runtime.stream_writer(f"⚠️ 预算 {budget} 元不可满足，直接输出并如实告知")
        return Command(
            goto="finalizer",
            update={
                "total_cost": total_cost,
                "budget_approved": False,
                "budget_note": note,
            },
        )

    
    if budget is None:
        budget = float("inf")

    if total_cost <= budget:
        if retry == 0:
            note = "首次方案预算通过，未触发降级。"
        elif retry == 1:
            note = f"经过 1 次降级重写后，总花费降至 {total_cost:.0f} 元，预算通过。"
        else:  # retry >= 2
            note = f"经过 {retry} 次降级重写后，总花费降至 {total_cost:.0f} 元，预算通过。"
        
        logger.info(f"预算通过 | 结余={budget - total_cost:.0f}")
        runtime.stream_writer(f"✅ 预算审查：总计 {total_cost:.0f} 元，预算通过")
        return Command(
            goto="finalizer",
            update={
                "total_cost": total_cost,
                "budget_approved": True,
                "budget_note": note,
            },
        )

    elif retry >= 2:
        note = (
            f"已尝试 {retry} 次降级重写（住宿/交通均已降至较低档），"
            f"总花费仍超支 {total_cost - budget:.0f} 元，强制输出。"
        )
        logger.warning(f"重试上限，强制输出 | 超支={total_cost - budget:.0f}")
        runtime.stream_writer(f"⚠️ 预算审查：重试 {retry} 次仍超支，强制输出（超 {total_cost - budget:.0f} 元）")
        return Command(
            goto="finalizer",
            update={
                "total_cost": total_cost,
                "budget_approved": False,
                "budget_note": note,
            },
        )

    else:
        logger.warning(f"预算超支打回 | 超支={total_cost - budget:.0f}, 重试={retry + 1}")
        runtime.stream_writer(f"👉 预算超支 {total_cost - budget:.0f} 元，打回重写...")
        return Command(
            goto="accommodation_node",
            update={
                "total_cost": total_cost,
                "budget_approved": False,
                "retry_count": retry + 1,
            },
        )