from typing import Annotated,TypedDict, Optional
from pydantic import BaseModel, Field

def plans_reducer(left: list, right: list) -> list:
    """如果 right 是特殊标记，清空；否则追加"""
    if right == ["__RESET__"]:
        return []
    return left + right

# ============ 图内部完整状态 ============
class TravelState(TypedDict):                           #可改为MessagesState
    # ---------- 输入层 ----------
    user_request: str                                   # 用户需求原文
    origin: Optional[str]                               # 出发地城市
    destination: str                                    # 目的地城市
    days: int                                           # 出行天数
    travelers: int                                      # 出行人数
    budget: float                                       # 用户总预算（不是人均）
    start_date: str                                     # 出行开始日期
    preferences: list[str]                              # 偏好：美食/自然/人文/商业
    transport_preference: Optional[str]                 # 交通偏好：自驾/高铁/飞机/大巴

    # ---------- 第一阶段：方案生成 ----------
    candidate_plans: Annotated[list, plans_reducer]     # 四方案累加（并行）
    selected_plan: str                                  # 综合后的唯一方案
    previous_itinerary: str                             # 上一版行程单

    # ---------- 第二阶段：细节规划 ----------
    accommodation: str                                  # 住宿方案
    transport: str                                      # 交通方案（依赖住宿）
    food_cost: float                                    # 全程餐饮总费用（所有人总计）
    ticket_cost: float                                  # 全程门票总费用（所有人总计）
    accommodation_cost: float                           # 住宿总费用（所有人 + 所有晚）
    transport_cost: float                               # 交通总费用（所有人，含往返大交通）

    # ---------- 预算审查层 ----------
    total_cost: float                                   # 总花费
    budget_approved: bool                               # 预算是否通过
    retry_count: int                                    # 业务重试次数
    budget_note: str                                    # 预算审查结论的说明文字

    # ---------- 输出层 ----------
    final_itinerary: str                                # 最终行程单



class TravelIntent(BaseModel):
    origin:Optional[str] = Field(None,description="出发地城市,没提为null")
    destination: Optional[str] = Field(None, description="目的地城市，没提则 null")
    days: Optional[int] = Field(None, description="出行天数，没提则 null")
    travelers: Optional[int] = Field(default=1, description="出行人数，没提则为 1")
    budget: Optional[float] = Field(None,description="用户总预算（元），不是人均")
    start_date: Optional[str] = Field(None,description="行程起始日期，格式 YYYY-MM-DD。用户说'下周五''10月20号'都要换算成具体日期。没提则为 null")
    preferences: list[str] = Field(
        default_factory = lambda: ["美食", "自然", "人文", "商业"],
        description="偏好列表，用户明确不要的项从中去掉"
    )
    transport_preference: Optional[str] = Field(
        default=None, 
        description="交通偏好：自驾/高铁/飞机/大巴，没提为 null"
    )

class SynthesizerOutput(BaseModel):
    plan: str = Field(description="综合后的完整行程单（Markdown 格式）")
    food_cost: float = Field(description="全程餐饮总费用（元，所有人总计）")
    ticket_cost: float = Field(description="全程门票总费用（元，所有人总计）")

class AccommodationOutput(BaseModel):
    content: str = Field(description="住宿推荐文本")
    total_cost: float = Field(description="住宿总费用（元，所有人 + 所有晚，总计）")

class TransportOutput(BaseModel):
    content: str = Field(description="交通方案文本")
    total_cost: float = Field(description="交通总费用（元，所有人总计，含往返大交通）")
