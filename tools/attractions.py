import os
from dotenv import load_dotenv
load_dotenv()
import httpx
from langchain_core.tools import tool

AMAP_KEY = os.getenv("AMAP_API_KEY")
AMAP_URL = "https://restapi.amap.com/v3/place/text"

PAGE_SIZE = 10

@tool
async def search_attractions(city: str, keywords: str = "景点") -> str:
    """搜索城市的热门景点信息。

    Args:
        city: 城市名，如"武汉"、"上海"
        keywords: 搜索关键词，默认"景点"，也可用"博物馆""公园""历史"等
    """
    if not AMAP_KEY:
        return "未配置 AMAP_API_KEY，无法查询景点。请在 .env 中配置。"
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                AMAP_URL,
                params={
                    "key": AMAP_KEY,
                    "keywords": keywords,
                    "city": city,
                    "citylimit": "true",       # 只返回指定城市的结果
                    "offset": PAGE_SIZE,       # 返回条数
                    "page": 1,
                    "extensions": "all",       # 返回详细信息（含评分）
                },
            )
            resp.raise_for_status()
            data = resp.json()

    except httpx.HTTPError as e:
        return f"查询景点失败（网络错误）：{e}"
    except Exception as e:
        return f"查询景点失败：{e}"

    if data.get("status") != "1":
        return f"查询失败：{data.get('info', '未知错误')}"

    pois = data.get("pois") or []
    if not pois:
        return f"未找到「{city}」的「{keywords}」相关景点。"

    lines = [f"{city} 「{keywords}」 TOP{len(pois)}："]
    for poi in pois:
        name = poi.get("name", "").strip()
        address = poi.get("address", "").strip()

        # 评分（只在 extensions=all 时返回）
        biz_ext = poi.get("biz_ext") or {}
        rating = biz_ext.get("rating", "")
        cost = biz_ext.get("cost", "")

        # 拼接一行
        parts = [name]
        if address:
            parts.append(address)
        if rating:
            parts.append(f"评分 {rating}")
        if cost:
            parts.append(f"人均 {cost} 元")

        lines.append("  · " + " | ".join(parts))

    return "\n".join(lines)

if __name__ == "__main__":
    import asyncio

    async def _test():
        result = await search_attractions.ainvoke({"city": "武汉", "keywords": "博物馆"})
        print(result)

    asyncio.run(_test())