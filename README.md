# 🌴 多智能体旅游规划系统

基于 LangGraph 的多智能体协作系统，通过 9 个 Agent 协同完成旅游行程规划。支持并行方案生成、预算 Reflection 闭环、Human-in-the-loop 中断恢复、SSE 双通道流式输出。

## ✨ 核心特性

- **Supervisor 编排**：1 个 Supervisor 统一解析需求，并行调度 4 个专业规划师（美食/自然/人文/商业）
- **Send 并行扇出**：4 个规划师同时执行，结果通过自定义 reducer 累加
- **Reflection 闭环**：预算审查节点真实算账，超支时通过 `Command` 动态打回住宿/交通节点，触发分级降级（最多 2 次重试）
- **Human-in-the-loop**：缺少目的地时 `interrupt` 暂停图，用户补充后 `Command(resume=...)` 恢复
- **PostgresSaver 持久化**：会话状态跨进程、跨请求持久化
- **SSE 双通道流式**：内容通道推 LLM token，控制通道推节点进度/中断/最终结果
- **接口契约**：Pydantic discriminated union 定义 SSE 事件，类型安全

## 🏗️ 架构

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

## 🛠️ 技术栈

| 层 | 技术 |
|---|---|
| 图编排 | LangGraph |
| LLM | 阿里云百炼（Qwen-Plus） |
| 结构化输出 | Pydantic v2 |
| Web 框架 | FastAPI |
| 流式协议 | SSE |
| 持久化 | PostgreSQL + AsyncPostgresSaver |
| 前端 | 原生 HTML/CSS/JS |

## 🚀 快速开始

### 1. 准备环境

- Python 3.11+
- PostgreSQL 14+
- 阿里云百炼 API Key（[获取地址](https://bailian.console.aliyun.com/)）

### 2. 安装依赖

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
├── nodes/                  # 图节点
│   ├── supervisor.py       # 需求解析 + 并行派发
│   ├── food.py             # 美食规划师
│   ├── nature.py           # 自然规划师（含工具调用）
│   ├── culture.py          # 人文规划师
│   ├── business.py         # 商业规划师
│   ├── synthesizer.py      # 方案综合
│   ├── accommodation.py    # 住宿规划
│   ├── transport.py        # 交通规划
│   ├── budget.py           # 预算审查（Reflection 闭环）
│   └── finalizer.py        # 最终汇总
├── prompts/                # 各节点的提示词
├── tools/                  # 工具（天气、景点）
├── utils/                  # 工具函数（日志、预算提示、路径）
├── static/                 # 前端页面
├── graph.py                # 图定义
├── state.py                # 状态定义（TypedDict + Pydantic 模型）
├── schemas.py              # 接口契约（请求 + SSE 事件）
├── llm.py                  # LLM 实例化
├── main_api.py             # FastAPI + SSE 入口
└── main.py                 # CLI 入口
```

## 🔑 核心设计

### 1. Send 并行扇出

Supervisor 用 `Send` API 同时派发给 4 个规划师：

```python
sends = [Send(_PREF_TO_NODE[p], updated_state) for p in preferences]
return Command(update=updates, goto=sends)
```

并行结果通过自定义 reducer 累加：

```python
def plans_reducer(left, right):
    if right == ["__RESET__"]:
        return []
    return left + right
```

### 2. Reflection 预算闭环

预算审查节点真实算账，超支时打回住宿节点降级重写：

```python
if total_cost > budget and retry < 2:
    return Command(
        goto="accommodation_node",
        update={"retry_count": retry + 1, "budget_approved": False},
    )
```

### 3. Human-in-the-loop

缺少目的地时触发中断，用户补充后恢复：

```python
user_reply = interrupt({"question": "请补充你想去的目的地"})
...
graph_input = Command(resume=user_reply)
```

### 4. SSE 双通道

一个 SSE 连接同时推两类事件：

- **内容通道**：LLM token（`messages` 模式）
- **控制通道**：进度、中断、最终结果（`custom` + `values` 模式）

### 5. Pydantic 接口契约

SSE 事件用 discriminated union 定义：

```python
SSEEvent = Annotated[
    Union[TokenEvent, ProgressEvent, InterruptEvent,
          FinalEvent, ErrorEvent, DoneEvent],
    Field(discriminator="type"),
]
```

## 📄 License

MIT
