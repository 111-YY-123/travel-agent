import os

import httpx
from langchain_core.tools import tool

from utils.rate_limiter import amap_limiter

AMAP_KEY = os.getenv("AMAP_API_KEY")
GEO_URL = "https://restapi.amap.com/v3/geocode/geo"
DIST_URL = "https://restapi.amap.com/v3/distance"

_MODE_MAP = {
    "driving": ("1", "驾车"),
    "walking": ("3", "步行"),
    "straight": ("0", "直线"),
}


@tool
async def calculate_distance(origin: str, destination: str, mode: str = "driving") -> str:
    """计算两座城市之间的距离和预计时间。
    Args:
        origin: 出发城市，如"宿迁"
        destination: 目的城市，如"日照"
        mode: 交通方式，可选 driving（驾车，默认）、walking（步行）、straight（直线）
    """
    if not AMAP_KEY:
        return "未配置 AMAP_API_KEY，无法计算距离。"

    distance_type, mode_cn = _MODE_MAP.get(mode, _MODE_MAP["driving"])

    try:
        await amap_limiter.acquire()
        async with httpx.AsyncClient(timeout=10) as client:
            o_resp = await client.get(GEO_URL, params={"key": AMAP_KEY, "address": origin})
            d_resp = await client.get(GEO_URL, params={"key": AMAP_KEY, "address": destination})
            o_resp.raise_for_status()
            d_resp.raise_for_status()
            o_data = o_resp.json()
            d_data = d_resp.json()

        o_geocodes = o_data.get("geocodes") or []
        d_geocodes = d_data.get("geocodes") or []
        if not o_geocodes:
            return f"未找到城市「{origin}」"
        if not d_geocodes:
            return f"未找到城市「{destination}」"

        o_loc = o_geocodes[0]["location"]
        d_loc = d_geocodes[0]["location"]

        await amap_limiter.acquire()
        async with httpx.AsyncClient(timeout=10) as client:
            dist_resp = await client.get(
                DIST_URL,
                params={
                    "key": AMAP_KEY,
                    "origins": o_loc,
                    "destination": d_loc,
                    "type": distance_type,
                },
            )
            dist_resp.raise_for_status()
            dist_data = dist_resp.json()

    except httpx.HTTPError as e:
        return f"计算距离失败（网络错误）：{e}"
    except Exception as e:
        return f"计算距离失败：{e}"

    if dist_data.get("status") != "1":
        return f"计算距离失败：{dist_data.get('info', '未知错误')}"

    results = dist_data.get("results") or []
    if not results:
        return "未获取到距离数据。"

    r = results[0]
    distance_km = int(r.get("distance", 0)) / 1000
    duration_h = int(r.get("duration", 0)) / 3600

    if distance_km <= 0:
        return f"未获取到 {origin} → {destination} 的有效距离数据。"

    if mode == "straight":
        return f"{origin} → {destination} 直线距离约 {distance_km:.0f} 公里"
    return f"{origin} → {destination} {mode_cn}约 {distance_km:.0f} 公里，预计 {duration_h:.1f} 小时"