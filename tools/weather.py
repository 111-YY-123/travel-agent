from datetime import datetime, timedelta
import httpx
from langchain_core.tools import tool

GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
WEATHER_URL = "https://api.open-meteo.com/v1/forecast"
MAX_FORECAST_DAYS = 16

WMO_MAP = {
    0: "晴", 1: "少云", 2: "多云", 3: "阴", 45: "雾", 48: "霜雾",
    51: "小毛毛雨", 53: "中毛毛雨", 55: "大毛毛雨", 61: "小雨", 63: "中雨", 65: "大雨",
    71: "小雪", 73: "中雪", 75: "大雪", 80: "小阵雨", 81: "中阵雨", 82: "大阵雨",
    95: "雷阵雨", 96: "雷阵雨伴冰雹", 99: "强雷阵雨伴冰雹",
}

@tool
async def get_weather(city: str, start_date: str, days: int = 3) -> str:
    """查询指定城市从起始日期开始的连续多天天气预报。"""
    try:
        requested_days = max(1, int(days))
        actual_days = min(requested_days, MAX_FORECAST_DAYS)
        truncated = requested_days > MAX_FORECAST_DAYS
        
        start_dt = datetime.strptime(start_date, "%Y-%m-%d")
        today_dt = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        if start_dt < today_dt:
            start_dt = today_dt
            start_date = start_dt.strftime("%Y-%m-%d")
            
        end_dt = start_dt + timedelta(days=actual_days - 1)
        end_date = end_dt.strftime("%Y-%m-%d")

        async with httpx.AsyncClient(timeout=10) as client:
            geo_res = await client.get(GEOCODING_URL, params={"name": city, "count": 5, "language": "zh"})
            geo_res.raise_for_status()
            geo_data = geo_res.json()

            results = geo_data.get("results") or []
            if not results:
                return f"未找到城市「{city}」，请确认城市名。"

            loc = max(results, key=lambda r: r.get("population", 0))
            lat, lon = loc["latitude"], loc["longitude"]
            timezone = loc.get("timezone", "Asia/Shanghai")

            weather_resp = await client.get(
                WEATHER_URL,
                params={
                    "latitude": lat, "longitude": lon,
                    "daily": "temperature_2m_max,temperature_2m_min,weathercode",
                    "timezone": timezone, "start_date": start_date, "end_date": end_date,
                },
            )

            if weather_resp.status_code != 200:
                return f"天气 API 返回错误状态码 {weather_resp.status_code}，可能日期参数不合法。"
                
            weather_data = weather_resp.json()

        daily = weather_data.get("daily") or {}
        times = daily.get("time") or []
        if not times:
            return f"{city} {start_date} 起 {actual_days} 天无天气数据。"

        lines = [f"{city} 天气预报（{start_date} 至 {end_date}）："]
        for i, d in enumerate(times):
            t_max = daily["temperature_2m_max"][i]
            t_min = daily["temperature_2m_min"][i]
            code = daily["weathercode"][i]
            desc = WMO_MAP.get(code, f"代码{code}")
            
            tip = ""
            if code in (61, 63, 65, 80, 81, 82, 95, 96, 99): tip = "，建议室内活动"
            elif code in (0, 1, 2): tip = "，适合户外活动"
            elif code in (71, 73, 75): tip = "，雨雪天气，注意防滑保暖"
            elif code in (45, 48): tip = "，能见度低，注意出行安全"

            lines.append(f"  {d}：{desc}，{t_min}~{t_max}℃{tip}")

        if truncated:
            lines.append(
                f"\n【重要提示】您请求了 {requested_days} 天的天气，但天气预报 API 最多只支持 {MAX_FORECAST_DAYS} 天。"
                f"以上仅包含前 {actual_days} 天的数据。"
                f"剩余的 {requested_days - actual_days} 天，请按当地历史气候经验为游客做推荐，"
                f"并提醒游客在临近出行时重新查询实时天气。"
            )

        return "\n".join(lines)
    except ValueError:
        return "日期格式错误，请提供 YYYY-MM-DD 格式的日期。"
    except Exception as e:
        return f"查询天气失败：{e}"