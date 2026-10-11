from dotenv import load_dotenv
load_dotenv()

import asyncio
from graph import init_checkpointer
from langgraph.types import Command


async def main():
    graph, pool = await init_checkpointer()

    try:
        user_input = input("请输入您的旅行计划：")
        config = {"configurable": {"thread_id": "cli-test"}}
        graph_input = {"user_request": user_input}

        while True:
            interrupted = False
            interrupt_info = None

            async for event in graph.astream(
                graph_input,
                config=config,
                stream_mode=["messages", "custom", "values"],
            ):
                mode, data = event
                if mode == "messages":
                    chunk, metadata = data
                    node_name = metadata.get("langgraph_node", "")
                    if node_name in ("synthesizer", "finalizer") and chunk.content:
                        content = chunk.content
                        if isinstance(content, list):
                            content = "".join(str(item) for item in content)
                        print(content, end="", flush=True)
                elif mode == "custom":
                    print(f"\n[进度] {data}")
                elif mode == "values":
                    if "__interrupt__" in data:
                        interrupted = True
                        interrupt_info = data["__interrupt__"][0].value

            if not interrupted:
                break

            print(f"\n\n⚠️ {interrupt_info.get('question', '请补充信息')}")
            user_reply = input("你的补充：")
            if not user_reply.strip():
                print("输入为空，退出")
                break
            graph_input = Command(resume=user_reply)

        print("\n" + "=" * 40)
    finally:
        await pool.close()


if __name__ == "__main__":
    asyncio.run(main())