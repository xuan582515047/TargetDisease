"""固定模板 Markdown 报告与 CSV 候选表导出。"""
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
    writer.writerow(["来源", "靶点", "基因", "疾病关联分A", "网络分N", "融合分",
                     "核查状态", "推荐理由"])
    for c in candidates:
        a = "" if c.get("a_score") is None else c["a_score"]
        n = "" if c.get("n_score") is None else c["n_score"]
        f = "" if c.get("fusion_score") is None else c["fusion_score"]
        writer.writerow([
            _escape_csv_cell("模型种子" if c.get("source") == "seed" else "网络扩展"),
            _escape_csv_cell(c.get("target_id")),
            _escape_csv_cell(c.get("symbol")),
            _escape_csv_cell(a),
            _escape_csv_cell(n),
            _escape_csv_cell(f),
            _escape_csv_cell(c.get("status_label")),
            _escape_csv_cell(c.get("reason")),
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
    lines.append(f"- 疾病：{disease.get('name_zh', '')}（{disease.get('name', '')}，ID: {disease.get('id', '')}）")
    lines.append(f"- 证据快照版本：{data.get('evidence_snapshot_version', '')}")
    lines.append(f"- 网络快照版本：{data.get('network_snapshot_version', '未提供')}")
    lines.append(f"- 模型：{data.get('model_name', '')}，提示词版本：{data.get('prompt_version', '')}")
    lines.append(f"- 生成时间：{data.get('generated_at', '')}")
    lines.append("")

    lines.append("## 一、种子靶点")
    lines.append("")
    seeds = data.get("seeds") or []
    if seeds:
        lines.append("| 靶点 | 基因 | 疾病关联分A | 网络分N | 核查状态 | 推荐理由 |")
        lines.append("|---|---|---|---|---|---|")
        for s in seeds:
            a = "" if s.get("a_score") is None else s["a_score"]
            n = "" if s.get("n_score") is None else s["n_score"]
            lines.append(f"| {s.get('target_id', '')} | {s.get('symbol', '')} | {a} | {n} | "
                         f"{s.get('status_label', '')} | {s.get('reason', '')} |")
    else:
        lines.append("本次未识别到有效种子。")
    lines.append("")

    lines.append("## 二、扩展候选")
    lines.append("")
    extended = data.get("extended_candidates") or []
    if extended:
        lines.append("| 靶点 | 基因 | 疾病关联分A | 网络分N | 证据 | ")
        lines.append("|---|---|---|---|---|")
        for c in extended:
            a = "" if c.get("a_score") is None else c["a_score"]
            n = "" if c.get("n_score") is None else c["n_score"]
            ev = "有" if c.get("has_evidence") else "探索性"
            lines.append(f"| {c.get('target_id', '')} | {c.get('symbol', '')} | {a} | {n} | {ev} |")
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
    lines.append(f"- 融合权重：A={params.get('w_a', 0.7)}，N={params.get('w_n', 0.3)}")
    lines.append("")

    lines.append("> 本报告为候选优选依据，不构成新靶点发现、因果关系或临床结论。")
    lines.append("")
    return "\n".join(lines)
