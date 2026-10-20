from tools.weather import get_weather
from tools.attractions import search_attractions
from tools.distance import calculate_distance

# 工具注册
TOOLS = [get_weather, search_attractions, calculate_distance]
TOOLS_BY_NAME = {t.name: t for t in TOOLS}

__all__ = [
    "get_weather",
    "search_attractions",
    "calculate_distance",
    "TOOLS",
    "TOOLS_BY_NAME",
]