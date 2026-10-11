"""接口层契约：请求模型 + SSE 事件模型"""
from typing import Literal, Optional, Union, Annotated
from pydantic import BaseModel, Field


class TravelInput(BaseModel):
    """POST /travel 的请求体"""
    user_request: str = ""
    thread_id: str = "default"
    resume: Optional[str] = None

class TokenEvent(BaseModel):
    type: Literal["token"] = "token"
    content: str

class ProgressEvent(BaseModel):
    type: Literal["progress"] = "progress"
    content: str

class InterruptEvent(BaseModel):
    type: Literal["interrupt"] = "interrupt"
    content: dict

class FinalEvent(BaseModel):
    type: Literal["final"] = "final"
    content: str

class ErrorEvent(BaseModel):
    type: Literal["error"] = "error"
    content: str

class DoneEvent(BaseModel):
    type: Literal["done"] = "done"


SSEEvent = Annotated[
    Union[
        TokenEvent, ProgressEvent, InterruptEvent,
        FinalEvent, ErrorEvent, DoneEvent,
    ],
    Field(discriminator="type"),
]

__all__ = [
    "TravelInput",
    "TokenEvent", "ProgressEvent", "InterruptEvent",
    "FinalEvent", "ErrorEvent", "DoneEvent",
    "SSEEvent",
]