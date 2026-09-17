"use client";

import { EDGE_COLOR, NODE_COLOR, NODE_SHAPE } from "@/lib/target-network";

const NODE_ITEMS = [
  { type: "disease", label: "当前疾病", desc: "仅展示，不参与传播" },
  { type: "seed", label: "模型种子", desc: "经核查的模型初始候选" },
  { type: "extended", label: "网络扩展候选", desc: "网络算法选出的非种子候选" },
  { type: "background", label: "背景蛋白", desc: "参与计算但非优选结果" },
];

const EDGE_ITEMS = [
  { type: "evidence", label: "疾病—靶点证据边", desc: "数据源存在该关联" },
  { type: "association", label: "蛋白功能关联边", desc: "网络快照中的关联" },
];

export default function NetworkLegend({ stats }: { stats?: { display_nodes?: number; display_edges?: number; total_nodes?: number; total_edges?: number; truncated?: boolean } }) {
  return (
    <div className="space-y-4">
      <div>
        <p className="mb-2 text-xs font-semibold text-muted-foreground">图例</p>
        <div className="space-y-2">
          {NODE_ITEMS.map((item) => (
            <div key={item.type} className="flex items-center gap-2">
              <span
                className="inline-block size-3.5 shrink-0"
                style={{
                  background: NODE_COLOR[item.type],
                  borderRadius: NODE_SHAPE[item.type] === "rectangle" ? "2px" : "9999px",
                }}
              />
              <div className="min-w-0">
                <p className="text-xs font-medium">{item.label}</p>
                <p className="text-[10px] text-muted-foreground">{item.desc}</p>
              </div>
            </div>
          ))}
        </div>
      </div>
      <div>
        <p className="mb-2 text-xs font-semibold text-muted-foreground">边</p>
        <div className="space-y-2">
          {EDGE_ITEMS.map((item) => (
            <div key={item.type} className="flex items-center gap-2">
              <span className="inline-block h-0.5 w-4 shrink-0" style={{ background: EDGE_COLOR[item.type] }} />
              <div className="min-w-0">
                <p className="text-xs font-medium">{item.label}</p>
                <p className="text-[10px] text-muted-foreground">{item.desc}</p>
              </div>
            </div>
          ))}
        </div>
      </div>
      {stats && (
        <div className="border-t border-border pt-3">
          <p className="mb-2 text-xs font-semibold text-muted-foreground">网络统计</p>
          <div className="grid grid-cols-2 gap-2 text-xs">
            <div><p className="text-muted-foreground">显示节点</p><p className="font-semibold">{stats.display_nodes ?? 0} / {stats.total_nodes ?? 0}</p></div>
            <div><p className="text-muted-foreground">显示边</p><p className="font-semibold">{stats.display_edges ?? 0} / {stats.total_edges ?? 0}</p></div>
          </div>
          {stats.truncated && <p className="mt-2 text-[10px] text-amber-600">已按关联分值确定性裁剪</p>}
        </div>
      )}
    </div>
  );
}
