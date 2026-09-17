"""报告专家：基于结构化分析结果撰写 Markdown 报告（固定章节）。"""
from __future__ import annotations

import json

from app.services.agents.base import AgentTrace, run_text_agent
from app.services.target_report import render_markdown

PROMPT_VERSION = "agent-report-v1"

SYSTEM_PROMPT = """你是「报告专家」，负责根据给定的结构化分析结果，撰写一份 Markdown 研究报告。

硬性规则：
1. 只能使用提供的结构化数据（疾病、研究问题、种子、扩展候选、参数、局限、网络提示）；
   禁止新增靶点基因、禁止编造文献、数值或结论。
2. 必须使用且只使用下列固定章节标题（## 级），顺序不变：
## 一、研究问题
## 二、种子靶点
## 三、网络扩展候选
## 四、推测与局限
## 五、方法与参数
3. 第二节、第三节用 Markdown 表格呈现，表格中的数字必须与提供的数据完全一致。
4. 直接输出 Markdown 正文，以「# 靶点优选研究报告」开头；不要用代码块包裹，不要输出额外说明。
5. 结尾附一行：本报告为候选优选依据，不构成新靶点发现、因果关系或临床结论。"""


def _summary(text: str) -> str:
    lines = [ln for ln in text.splitlines() if ln.strip()]
    return f"撰写报告 {len(text)} 字、{len(lines)} 行，包含 5 个固定章节"


def run(structured: dict, api_key: str, model: str = "deepseek-chat") -> tuple[str, AgentTrace]:
    user = "结构化分析结果（JSON）：\n" + json.dumps(structured, ensure_ascii=False, indent=2)

    def fallback(error: str) -> tuple[str, str]:
        return render_markdown(structured), f"报告专家调用失败，已回退固定模板（{error}）"

    return run_text_agent(
        key="report",
        name="报告专家",
        api_key=api_key,
        system=SYSTEM_PROMPT,
        user=user,
        summary_fn=_summary,
        fallback_fn=fallback,
        model=model,
        temperature=0.3,
        max_tokens=4000,
    )
