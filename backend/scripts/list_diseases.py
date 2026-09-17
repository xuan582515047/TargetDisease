"""从 Open Targets 按名称检索疾病，辅助挑选要导入的疾病。

用法（在 backend/ 目录下，需能联网访问 Open Targets）：
    python -m scripts.list_diseases "parkinson"
    python -m scripts.list_diseases "diabetes" --size 15 --counts

输出命中疾病的稳定 ID、英文名、描述摘要；加 --counts 时额外显示关联靶点数量
（每个疾病一次额外请求，较慢）。最后给出可直接复制的导入命令（配合 --merge 追加，
不会覆盖已有疾病）。
"""
from __future__ import annotations

import argparse

from app.services.opentargets_client import (
    OpenTargetsError,
    disease_target_count,
    search_diseases,
)


def _import_hint(disease_id: str) -> str:
    return (
        "docker compose exec backend python -m scripts.import_target_evidence "
        f"--disease {disease_id} --name-zh 替换为中文名 --merge"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="检索 Open Targets 疾病，辅助挑选导入对象")
    parser.add_argument("query", help="疾病英文名关键词，如 parkinson")
    parser.add_argument("--size", type=int, default=10, help="返回命中数上限（默认 10）")
    parser.add_argument("--counts", action="store_true", help="逐个查询关联靶点数量（较慢）")
    args = parser.parse_args()

    try:
        hits = search_diseases(args.query, args.size)
    except OpenTargetsError as exc:
        print(f"检索失败：{exc}")
        return

    print(f"命中 {len(hits)} 个疾病（关键词：{args.query}）：\n")
    for i, h in enumerate(hits, 1):
        name = h.get("name") or "(无名称)"
        desc = (h.get("description") or "").replace("\n", " ")[:80]
        print(f"{i}. {name}  [{h.get('id')}]")
        if desc:
            print(f"   {desc}")
        if args.counts:
            info = disease_target_count(h.get("id") or "")
            if info and info.get("target_count") is not None:
                print(f"   关联靶点：{info['target_count']} 个")
        print(f"   导入命令：{_import_hint(h.get('id') or '')}")
        print()


if __name__ == "__main__":
    main()
