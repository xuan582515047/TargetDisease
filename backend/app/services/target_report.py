"""固定模板 Markdown 报告与 CSV 候选表导出（自由文本版）。"""
from __future__ import annotations

import csv
import io


def _escape_csv_cell(value) -> str:
    """对以 = + - @ 开头的文本作文本转义，防止表格软件执行公式。"""
    text = "" if value is None else str(value)
    if text.startswith(("=", "+", "-", "@")):
        return "'" + text
    return text


def render_csv(candidates: list[dict]) -> str:
    """导出候选表 CSV。"""
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["来源", "基因", "相关度分", "网络分N", "推荐理由", "机制推测"])
    for c in candidates:
        n = "" if c.get("n_score") is None else c["n_score"]
        r = "" if c.get("relevance_score") is None else c["relevance_score"]
        writer.writerow([
            _escape_csv_cell("模型种子" if c.get("source") == "seed" else "网络扩展"),
            _escape_csv_cell(c.get("symbol")),
            _escape_csv_cell(r),
            _escape_csv_cell(n),
            _escape_csv_cell(c.get("reason")),
            _escape_csv_cell(c.get("mechanism")),
        ])
    return buf.getvalue()


def render_markdown(data: dict) -> str:
    """用固定模板生成 Markdown 报告，不调用大模型。"""
    lines = []
    disease = data.get("disease") or {}
    lines.append("# 靶点优选研究报告")
    lines.append("")
    lines.append(f"- 研究问题：{data.get('question', '')}")
    if data.get("question_summary"):
        lines.append(f"- 意图概括：{data['question_summary']}")
    lines.append(f"- 疾病：{disease.get('name', '')}（ID: {disease.get('id', '')}）")
    lines.append(f"- 模型：{data.get('model_name', '')}，提示词版本：{data.get('prompt_version', '')}")
    lines.append(f"- 生成时间：{data.get('generated_at', '')}")
    lines.append("")

    lines.append("## 一、种子靶点")
    lines.append("")
    seeds = data.get("seeds") or []
    if seeds:
        lines.append("| 基因 | 相关度分 | 网络分N | 推荐理由 | 机制推测 |")
        lines.append("|---|---|---|---|---|")
        for s in seeds:
            n = "" if s.get("n_score") is None else s["n_score"]
            r = "" if s.get("relevance_score") is None else s["relevance_score"]
            lines.append(f"| {s.get('symbol', '')} | {r} | {n} | {s.get('reason', '')} | {s.get('mechanism', '')} |")
    else:
        lines.append("本次未识别到有效种子。")
    lines.append("")

    lines.append("## 二、网络扩展候选")
    lines.append("")
    extended = data.get("extended_candidates") or []
    if extended:
        lines.append("| 基因 | 网络分N |")
        lines.append("|---|---|")
        for c in extended:
            n = "" if c.get("n_score") is None else c["n_score"]
            lines.append(f"| {c.get('symbol', '')} | {n} |")
    else:
        lines.append("无扩展候选。")
    lines.append("")

    lines.append("## 三、推测与局限")
    lines.append("")
    for h in data.get("hypotheses") or []:
        lines.append(f"- 推测：{h}")
    for l in data.get("limitations") or []:
        lines.append(f"- 局限：{l}")
    lines.append("")

    lines.append("## 四、方法与参数")
    lines.append("")
    params = data.get("params") or {}
    lines.append(f"- 传播参数：α={params.get('alpha', '')}，max_iter={params.get('max_iter', '')}，tol={params.get('tol', '')}")
    lines.append(f"- STRING 网络：阈值={params.get('string_threshold', '')}，跳数={params.get('string_hops', '')}，节点上限={params.get('max_nodes', '')}")
    if data.get("network_error"):
        lines.append(f"- 网络提示：{data['network_error']}")
    lines.append("")

    lines.append("> 本报告为候选优选依据，由大模型自由生成推荐，不构成新靶点发现、因果关系或临床结论。")
    lines.append("")
    return "\n".join(lines)
