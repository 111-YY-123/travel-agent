import os
from dotenv import load_dotenv
load_dotenv(override=True)

from tools import TOOLS
from langchain_openai import ChatOpenAI
from state import (
    TravelIntent, SynthesizerOutput,
    AccommodationOutput, TransportOutput
)

_API_KEY = os.getenv("ALIBABA_API_KEY")
_BASE_URL = os.getenv("ALIBABA_BASE_URL")

if not _API_KEY:
    raise RuntimeError(
        "环境变量 ALIBABA_API_KEY 未配置。请检查 .env 文件，"
        "参考 .env.example 模板。"
    )
if not _BASE_URL:
    raise RuntimeError(
        "环境变量 ALIBABA_BASE_URL 未配置。请检查 .env 文件，"
        "参考 .env.example 模板。"
    )

_LLM_CONFIG = {
    "model": "qwen3.8-flash",
    "api_key":  _API_KEY,
    "base_url": _BASE_URL,
    "temperature": 0.3,        # 规划类任务用低温，稳定输出
    "timeout": 60,             # 单次调用超时 60 秒
    "max_retries": 3,          # 网络抖动自动重试 3 次
}

model = ChatOpenAI(**_LLM_CONFIG, streaming=True)
model_with_tools = ChatOpenAI(**_LLM_CONFIG).bind_tools(TOOLS)
structured_model = ChatOpenAI(**_LLM_CONFIG)

structured_supervisor = structured_model.with_structured_output(TravelIntent, method="json_mode")
structured_synthesizer = structured_model.with_structured_output(SynthesizerOutput, method="json_mode")
structured_accommodation = structured_model.with_structured_output(AccommodationOutput, method="json_mode")
structured_transport = structured_model.with_structured_output(TransportOutput, method="json_mode")