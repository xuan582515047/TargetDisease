"use client";

import { X, Scale } from "lucide-react";
import type { NetworkEdge, NetworkNode } from "@/lib/api";

type Props = {
  node: NetworkNode | null;
  edge: NetworkEdge | null;
  onClose: () => void;
  onAddCompare?: (targetId: string) => void;
};

export default function NetworkDetails({ node, edge, onClose, onAddCompare }: Props) {
  if (!node && !edge) return null;

  return (
    <aside className="fixed right-0 top-0 z-20 flex h-full w-[320px] flex-col border-l border-border bg-background shadow-xl">
      <div className="flex items-center justify-between border-b border-border px-4 py-3">
        <h2 className="text-sm font-semibold">{node ? "节点详情" : "边详情"}</h2>
        <button type="button" onClick={onClose} aria-label="关闭" className="rounded-md p-1 hover:bg-secondary">
          <X size={16} />
        </button>
      </div>

      <div className="flex-1 space-y-4 overflow-auto p-4 text-sm">
        {node && (
          <>
            <div>
              <p className="text-xs text-muted-foreground">来源类别</p>
              <p className="mt-1 font-semibold">{typeLabel(node.type)}</p>
            </div>
            <div>
              <p className="text-xs text-muted-foreground">基因</p>
              <p className="mt-1 font-semibold">{node.label}</p>
            </div>
            {node.relevance_score != null && (
              <div><p className="text-xs text-muted-foreground">相关度分</p><p className="mt-1">{node.relevance_score.toFixed(3)}</p></div>
            )}
            {node.n_score != null && (
              <div><p className="text-xs text-muted-foreground">网络分 N</p><p className="mt-1">{node.n_score.toFixed(3)}</p></div>
            )}
            {node.type !== "disease" && onAddCompare && (
              <button
                type="button"
                onClick={() => onAddCompare(node.label || node.id)}
                className="flex w-full items-center justify-center gap-2 rounded-lg border border-primary/30 px-3 py-2 text-xs text-primary transition-colors hover:bg-primary/5"
              >
                <Scale size={14} /> 加入对比
              </button>
            )}
          </>
        )}
        {edge && (
          <>
            <div><p className="text-xs text-muted-foreground">关系类型</p><p className="mt-1 font-semibold">蛋白功能关联</p></div>
            <div><p className="text-xs text-muted-foreground">来源分值</p><p className="mt-1">{edge.score.toFixed(3)}</p></div>
            {edge.source_id && <div><p className="text-xs text-muted-foreground">来源记录</p><p className="mt-1 font-mono text-xs">{edge.source_id}</p></div>}
            {edge.version && <div><p className="text-xs text-muted-foreground">版本</p><p className="mt-1">{edge.version}</p></div>}
          </>
        )}
      </div>
    </aside>
  );
}

function typeLabel(type: string): string {
  switch (type) {
    case "disease": return "当前疾病";
    case "seed": return "模型种子";
    case "extended": return "网络扩展候选";
    case "background": return "背景蛋白";
    default: return type;
  }
}
