# 多智能体旅游规划系统

基于 LangGraph 开发的多智能体协作系统。通过 Supervisor 编排多个专业 Agent，结合真实外部 API（高德地图、Open-Meteo），实现从用户需求解析到详细行程单生成的全流程规划。

## 核心特性

- **多智能体并行编排**：Supervisor 统一解析需求后，利用 LangGraph 的 `Send` API 将任务并行派发给美食、自然、人文、商业 4 个规划师，大幅降低整体耗时。
- **真实数据驱动与 ReAct 循环**：Agent 具备工具调用能力，可自主决策调用高德地图 API（POI 搜索、距离测算）和 Open-Meteo（多日天气）。内置异常兜底，工具报错时模型可自我纠错。
- **预算 Reflection 闭环**：算账节点严格计算真实花费。超支时通过 `Command` 将任务打回住宿节点，触发降级重写（最高重试 2 次），解决纯 LLM 规划容易超支的痛点。
- **Human-in-the-loop**：缺少目的地时，自动触发 `interrupt` 挂起图。前端通过 SSE 收到信号弹窗，用户补充后通过 `Command(resume=...)` 跨进程无损恢复执行。
- **高并发限流与缓存**：针对高德 API 的 QPS 限制，实现了基于 `asyncio` 的令牌桶限流器；同时为搜索工具加入了短时内存缓存，降低外部接口压力。
- **SSE 双通道流式输出**：一个 SSE 连接同时推送两类事件，内容通道推 LLM token（打字机效果），控制通道推节点执行进度与中断信号。

## 架构

```mermaid
graph TD
    START([用户输入]) --> P[Planning 子图]
    
    subgraph P [Planning 子图]
        S[Supervisor] -->|Send 并行| F[美食规划师]
        S --> N[自然规划师]
        S --> C[人文规划师]
        S --> B[商业规划师]
        F --> SYN[Synthesizer 综合]
        N --> SYN
        C --> SYN
        B --> SYN
    end
    
    P --> A[住宿规划师]
    A --> T[交通规划师]
    T --> BR{预算审查}
    BR -->|超支, retry<2| A
    BR -->|通过 / 重试上限| FIN[Finalizer 汇总]
    FIN --> END([最终行程单])

 ```
## 技术栈

- **大模型与编排**：LangGraph, LangChain, 阿里云百炼 (Qwen-Plus)
- **外部工具**：高德地图 API (POI/距离), Open-Meteo (天气)
- **数据持久化**：PostgreSQL (AsyncPostgresSaver)
- **Web 框架与协议**：FastAPI, SSE (Server-Sent Events)
- **数据校验**：Pydantic v2

## 快速开始

**1. 准备环境**
- Python 3.11+，PostgreSQL 14+
- 阿里云百炼 API Key（[获取地址](https://bailian.console.aliyun.com/)）
- 高德地图 Web 服务 API Key（[获取地址](https://lbs.amap.com/)）

**2. 安装依赖**
```bash
pip install -r requirements.txt
```

### 3. 配置环境变量

```bash
cp .env.example .env
```

编辑 `.env`，填入：

```
ALIBABA_API_KEY=your_dashscope_api_key
ALIBABA_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
DATABASE_URL=postgresql://user:password@localhost:5432/dbname?sslmode=disable
AMAP_API_KEY=your_amap_key_here
```

### 4. 启动服务

```bash
python main_api.py
```

浏览器打开 http://localhost:8000

### 5. 命令行模式（可选）

```bash
python main.py
```

## 📁 目录结构

```
Travel_agent/
├── nodes/                  # 图节点定义
│   ├── supervisor.py       # 需求解析、HITL中断与并行派发
│   ├── synthesizer.py      # 方案综合与成本核算
│   ├── accommodation.py    # 住宿规划（依赖降级重写）
│   ├── transport.py        # 交通规划（真实距离测算）
│   ├── budget.py           # 预算审查（Reflection 闭环）
│   └── ...
├── tools/                  # 外部工具封装
│   ├── attractions.py      # 高德 POI 搜索
│   ├── weather.py          # Open-Meteo 天气查询
│   └── distance.py         # 高德距离测量
├── utils/                  # 通用工具模块
│   ├── react_runner.py     # 通用 ReAct 循环执行器
│   ├── rate_limiter.py     # 令牌桶限流器
│   ├── tool_cache.py       # 工具结果缓存装饰器
│   └── logger_handler.py   # 日志配置
├── prompts/                # 各节点的提示词模板
├── static/                 # 原生前端页面
├── graph.py                # 图结构组装与持久化配置
├── state.py                # 状态定义 (TypedDict)
├── schemas.py              # 接口契约与 SSE 事件模型
├── llm.py                  # LLM 实例化配置
├── main_api.py             # FastAPI 入口 (SSE 流式)
└── main.py                 # CLI 入口
```

## 核心设计

### 1. ReAct 工具调用与自纠错
Agent 节点使用统一的 `run_react` 循环执行器。模型可以自主决定何时调用高德或天气 API。我们在 `tool.ainvoke` 外层加了 `try-except` 兜底，当工具执行异常时，会将错误信息包装成 `ToolMessage` 返回给模型，让模型决定是重试还是跳过，防止由于外部接口超时导致整个图崩溃。

```python
# utils/react_runner.py 核心逻辑
try:
    result = await tool.ainvoke(tc["args"])
except Exception as e:
    logger.exception(f"工具 {tc['name']} 调用失败")
    result = f"工具调用失败：{e}"

messages.append(ToolMessage(content=str(result), tool_call_id=tc["id"]))
```

### 2. 并发限流与结果缓存

高德 API 有严格的 QPS 限制。在 utils/rate_limiter.py 中实现了基于 asyncio.Lock 的令牌桶限流，防止并行 Agent 同时调用被高德封禁；同时 utils/tool_cache.py 对相同的查询结果做了 10 分钟缓存，大幅降低外部 API 调用频次。

### 3. Reflection 预算打回闭环

预算审查节点真实算账。若超支，通过 LangGraph 的 Command 动态路由，将任务打回住宿节点进行降级重写（最多重试 2 次）。

```python
if total_cost > budget and retry < 2:
    return Command(
        goto="accommodation_node",
        update={"retry_count": retry + 1, "budget_approved": False},
    )
```

### 4. SSE 双通道与接口契约
一个 SSE 连接中同时推送两类事件：内容通道 (`messages`) 推送 LLM token，控制通道 (`custom` / `values`) 推送节点执行状态、中断信号和最终行程。

在接口层使用 Pydantic 的 discriminated union 做严格的数据校验：
```python
SSEEvent = Annotated[
    Union[TokenEvent, ProgressEvent, InterruptEvent,
          FinalEvent, ErrorEvent, DoneEvent],
    Field(discriminator="type"),
]
```

### 5. Human-in-the-loop 中断恢复

当用户需求缺少关键信息（如目的地）时，图会执行 interrupt 挂起并保存 Checkpoint。前端收到中断事件后提示用户补充，随后通过 Command(resume=...) 从断点恢复，由 PostgresSaver 保证状态的跨进程持久化。