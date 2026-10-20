from dotenv import load_dotenv
load_dotenv()

from utils.logger_handler import get_logger
logger = get_logger("api")


from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
from langgraph.types import Command

from graph import init_checkpointer
from schemas import (
    TravelInput,
    TokenEvent, ProgressEvent, InterruptEvent,
    FinalEvent, ErrorEvent, DoneEvent,
)

graph = None
pool = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global graph, pool
    graph, pool = await init_checkpointer()
    yield
    await pool.close()


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)




def _sse(evt) -> str:
    """序列化一条 SSE 事件为 SSE 报文格式。"""
    return f"data: {evt.model_dump_json()}\n\n"
 
async def event_generator(req: TravelInput):
    final_itinerary = None
    config = {"configurable": {"thread_id": req.thread_id}}

    try:
        if req.resume is not None:
            if not req.resume.strip():
                yield _sse(ErrorEvent(content="恢复中断时 resume 不能为空"))
                yield _sse(DoneEvent())
                return
            graph_input = Command(resume=req.resume)
        else:
            graph_input = {"user_request": req.user_request}

        async for namespace, mode, data in graph.astream(
            graph_input,
            config=config,
            stream_mode=["messages", "custom", "values"],
            subgraphs=True,
        ):

            if mode == "messages":
                chunk, metadata = data
                node_name = metadata.get("langgraph_node", "")
                if node_name == "finalizer" and chunk.content:
                    content = chunk.content
                    # 处理 list 类型（多模态 content 块）
                    if isinstance(content, list):
                        parts = []
                        for item in content:
                            if isinstance(item, str):
                                parts.append(item)
                            elif isinstance(item, dict) and "text" in item:
                                parts.append(item["text"])
                        content = "".join(parts)
                    if content:
                        yield _sse(TokenEvent(content=content))

            elif mode == "custom":
                yield _sse(ProgressEvent(content=str(data)))

            elif mode == "values":
                if "__interrupt__" in data:
                    interrupt_info = data["__interrupt__"][0].value
                    yield _sse(InterruptEvent(content=interrupt_info))

                if data.get("final_itinerary"):
                    final_itinerary = data["final_itinerary"]

        if final_itinerary:
            yield _sse(FinalEvent(content=final_itinerary))


        yield _sse(DoneEvent())


    except Exception as e:
        logger.exception("event_generator 异常") 
        yield _sse(ErrorEvent(content=str(e)))
        yield _sse(DoneEvent())


@app.post("/travel")
async def travel(req: TravelInput):
    return StreamingResponse(
        event_generator(req),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@app.get("/health")
async def health():
    return {"status": "ok"}


static_dir = Path(__file__).parent / "static"
if static_dir.exists():
    app.mount("/", StaticFiles(directory=str(static_dir), html=True), name="static")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)