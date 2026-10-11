from langchain_core.tools import tool

@tool
def get_weather(city: str, date: str) -> str:
    """查询指定城市指定日期的天气。
    
    Args:
        city: 城市名，如"武汉"
        date: 日期，如"2026-10-07"
    """
    # Mock 数据
    weather_map = {
        "武汉": "多云转晴，18-25℃，适合户外活动",
        "上海": "小雨，15-20℃，建议带伞",
    }
    return f"{city} {date} 天气：{weather_map.get(city, '晴，20-26℃')}"
