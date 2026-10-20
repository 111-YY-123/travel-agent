"""ReAct 工具调用循环执行器。"""
from langchain_core.messages import HumanMessage, ToolMessage

from llm import model_with_tools, model
from tools import TOOLS_BY_NAME
from utils.logger_handler import get_logger

logger = get_logger("travel")

DEFAULT_MAX_ROUNDS = 3


async def run_react(
    prompt: str,
    runtime,
    node_label: str,
    max_rounds: int = DEFAULT_MAX_ROUNDS,
) -> str:
    messages = [HumanMessage(content=prompt)]
    response = None

    for round_idx in range(max_rounds):
        response = await model_with_tools.ainvoke(messages)
        messages.append(response)

        if not response.tool_calls:
            break

        tool_names = [tc["name"] for tc in response.tool_calls]
        logger.info(f"{node_label} 第 {round_idx + 1} 轮 | 调用工具 {tool_names}")
        runtime.stream_writer(f"{node_label} 调用工具：{', '.join(tool_names)}")

        for tc in response.tool_calls:
            tool = TOOLS_BY_NAME.get(tc["name"])
            if tool is None:
                result = f"未知工具：{tc['name']}"
                logger.warning(f"{node_label} 模型调用了未注册的工具 {tc['name']}")
            else:
                try:
                    result = await tool.ainvoke(tc["args"])
                    logger.info(f"工具 {tc['name']} 返回 | {str(result)[:80]}")
                except Exception as e:
                    logger.exception(f"工具 {tc['name']} 调用失败 | args={tc['args']}")
                    result = f"工具 {tc['name']} 调用失败：{type(e).__name__}: {e}"

            messages.append(ToolMessage(content=str(result), tool_call_id=tc["id"]))
            
    else:
        logger.warning(f"{node_label} 达到工具调用上限 {max_rounds} 轮")
        runtime.stream_writer(f"{node_label} 达到工具调用上限")

        try:
            response = await model.ainvoke(
                messages + [HumanMessage(content="请基于以上信息直接输出最终结果，不要再调用工具。")]
            )
        except Exception:
            logger.exception(f"{node_label} 强制收尾失败")

    # 兼容 list 格式的返回内容
    content = response.content if response else ""
    if isinstance(content, list):
        content = "".join(str(x) for x in content)
        
    return content or "（未获取到有效结果）"