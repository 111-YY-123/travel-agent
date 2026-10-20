import os

import httpx
from langchain_core.tools import tool

from utils.rate_limiter import amap_limiter
from utils.tool_cache import cached

AMAP_KEY = os.getenv("AMAP_API_KEY")
AMAP_URL = "https://restapi.amap.com/v3/place/text"


@tool
@cached(ttl=600)
async def search_attractions(city: str, keywords: str = "景点", limit: int = 4) -> str:
    """搜索城市的地点信息。可用于查找景点、美食、博物馆、酒店、商圈等。
    Args:
        city: 城市名，如"武汉"、"上海"
        keywords: 搜索关键词。常用值：
            - "景点" / "风景名胜"：旅游景点
            - "美食" / "小吃"：餐厅、小吃街
            - "博物馆" / "古迹"：人文点位
            - "购物中心" / "商业街"：商圈
            - "酒店" / "民宿"：住宿
        limit: 返回条数。短途游(3天内)传4，中途游(7天内)传8，长途游传12。
    """
    if not AMAP_KEY:
        return "未配置 AMAP_API_KEY，无法查询景点。请在 .env 中配置。"

    await amap_limiter.acquire()

    safe_limit = min(max(int(limit), 1), 20)

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                AMAP_URL,
                params={
                    "key": AMAP_KEY,
                    "keywords": keywords,
                    "city": city,
                    "citylimit": "true",
                    "offset": safe_limit,
                    "page": 1,
                    "extensions": "all",
                },
            )
            resp.raise_for_status()
            data = resp.json()

    except httpx.HTTPError as e:
        return f"查询地点失败（网络错误）：{e}"
    except Exception as e:
        return f"查询地点失败：{e}"

    if data.get("status") != "1":
        return f"查询失败：{data.get('info', '未知错误')}"

    pois = data.get("pois") or []
    if not pois:
        return f"未找到「{city}」的「{keywords}」相关地点。"

    lines = [f"{city} 「{keywords}」 TOP{len(pois)}："]
    for poi in pois:
        # 安全获取 name，防列表或 None
        name_raw = poi.get("name", "")
        name = "".join(name_raw) if isinstance(name_raw, list) else str(name_raw).strip()

        # 安全获取 address，防列表或 None
        address_raw = poi.get("address", "")
        if isinstance(address_raw, list):
            address = "".join(address_raw).strip()
        else:
            address = str(address_raw).strip()

        biz_ext = poi.get("biz_ext") or {}
        if not isinstance(biz_ext, dict):
            biz_ext = {}
        rating = biz_ext.get("rating", "")
        cost = biz_ext.get("cost", "")

        parts = [name]
        if address: parts.append(address)
        if rating: parts.append(f"评分 {rating}")
        if cost: parts.append(f"人均 {cost} 元")
        
        lines.append("  · " + " | ".join(parts))

    return "\n".join(lines)