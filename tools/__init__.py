from tools.weather import get_weather
from tools.attractions import search_attractions

# 工具注册
TOOLS = [get_weather, search_attractions]
TOOLS_BY_NAME = {t.name: t for t in TOOLS}


__all__ = [
    "get_weather",
    "search_attractions",
    "TOOLS",
    "TOOLS_BY_NAME",
]

