# graph.py
import os
from dotenv import load_dotenv
load_dotenv()

from utils.logger_handler import get_logger
logger = get_logger("travel")

from langgraph.graph import StateGraph, START, END
from psycopg_pool import AsyncConnectionPool
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from state import TravelState
from nodes.supervisor import supervisor_node
from nodes.food import food_node
from nodes.nature import nature_node
from nodes.culture import culture_node
from nodes.business import business_node
from nodes.synthesizer import synthesizer_node
from nodes.accommodation import accommodation_node
from nodes.transport import transport_node
from nodes.budget import budget_reviewer_node
from nodes.finalizer import finalizer_node

DB_URL = os.getenv("DATABASE_URL")
if not DB_URL:
    raise RuntimeError("DATABASE_URL 未配置，请检查 .env 文件")

def route_after_planning(state) -> str:
    destination = state.get("destination")
    selected_plan = (state.get("selected_plan") or "").strip()
    if destination and selected_plan:
        return "accommodation_node"
    logger.warning(f"planning 子图未产出有效方案 | destination={destination}")
    return END

def build_planning_subgraph():
    """第一阶段：方案生成子图
    输入：user_request
    输出：selected_plan, food_cost, ticket_cost
    """
    planning = StateGraph(TravelState)
    planning.add_node("supervisor", supervisor_node)
    planning.add_node("food_node", food_node)
    planning.add_node("nature_node", nature_node)
    planning.add_node("culture_node", culture_node)
    planning.add_node("business_node", business_node)
    planning.add_node("synthesizer", synthesizer_node)

    planning.add_edge(START, "supervisor")
    planning.add_edge("food_node", "synthesizer")
    planning.add_edge("nature_node", "synthesizer")
    planning.add_edge("culture_node", "synthesizer")
    planning.add_edge("business_node", "synthesizer")
    planning.add_edge("synthesizer", END)

    return planning.compile()


def build_main_graph(checkpointer):
    """主图：planning 子图 + 细节规划 + 预算闭环"""
    planning_graph = build_planning_subgraph()

    main_graph = StateGraph(TravelState)
    main_graph.add_node("planning", planning_graph)
    main_graph.add_node("accommodation_node", accommodation_node)
    main_graph.add_node("transport_node", transport_node)
    main_graph.add_node("budget_reviewer", budget_reviewer_node)
    main_graph.add_node("finalizer", finalizer_node)

    main_graph.add_edge(START, "planning")
    main_graph.add_conditional_edges("planning", route_after_planning)
    main_graph.add_edge("accommodation_node", "transport_node")
    main_graph.add_edge("transport_node", "budget_reviewer")
    main_graph.add_edge("finalizer", END)

    return main_graph.compile(checkpointer=checkpointer)

async def init_checkpointer():
    """应用启动时调用一次，返回编译好的 graph"""
    pool = AsyncConnectionPool(
        conninfo=DB_URL,
        max_size=10,
        kwargs={"autocommit": True},
        open=False,
    )
    await pool.open()
    
    checkpointer = AsyncPostgresSaver(pool)
    await checkpointer.setup()
    
    graph = build_main_graph(checkpointer)
    return graph, pool
