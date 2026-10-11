def build_budget_hint(budget, days, travelers):
    """根据用户预算生成提示语，供规划师参考。
    
    特别处理：预算 <= 0 时，明确告知 LLM 这是不可满足约束，
    避免 LLM 编造"免费""物物交换""公益"等不现实方案。
    """
    if budget is None:
        return "预算：用户未指定，请按中等舒适标准推荐。"

    if budget < 0:
        return (
            f"预算：用户填写 {budget} 元，**这是一个无效输入（预算不能为负数）**。\n"
            f"请你按中等舒适标准正常推荐方案，**不要编造**"
            f"「免费获取」「物物交换」「公益厨房」等不现实内容。\n"
            f"预算审查节点会按「未指定预算」处理，并在最终行程单中提示用户确认。"
        )

    if budget == 0:
        return (
            f"预算：用户填写 {budget} 元。**这是一个不可满足的约束**——"
            f"任何真实的旅行（交通、住宿、餐饮）都需要成本。\n"
            f"请你按中等舒适标准正常推荐方案，**不要编造**"
            f"「免费获取」「物物交换」「公益厨房」「共享休憩」等不现实内容。\n"
            f"预算审查节点会如实告知用户超支金额，由用户决定是否调整预算。"
        )

    per_person = budget / travelers if travelers else budget
    per_person_daily = per_person / days if days else per_person

    if per_person_daily < 400:
        level = "紧张"
        control = (
            "请主动选择性价比高的点位——免费景点优先、本地小吃优先、"
            "经济型住宿优先，不要推荐高消费项目（米其林、高档购物、豪华酒店）。"
        )
    elif per_person_daily < 800:
        level = "中等"
        control = "按正常标准推荐，兼顾性价比和体验。"
    else:
        level = "宽松"
        control = "可以推荐一些优质体验项目（特色餐厅、深度导览），不用刻意省钱。"

    return (
        f"预算：用户总预算 {budget} 元，共 {travelers} 人 {days} 天，"
        f"人均日预算约 {per_person_daily:.0f} 元（预算{level}）。\n"
        f"【控制要求】{control}"
    )

