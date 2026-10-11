from langchain_core.tools import tool

@tool
def search_attractions(city: str) -> str:
    """搜索城市的热门景点信息。
    
    Args:
        city: 城市名
    """
    attractions_map = {
        "武汉": "黄鹤楼（需预约，80元）、东湖（免费）、湖北省博物馆（需预约，免费）、户部巷（免费）",
        "上海": "外滩（免费）、迪士尼（475元）、豫园（40元）",
    }
    return f"{city}热门景点：{attractions_map.get(city, '暂无数据')}"
