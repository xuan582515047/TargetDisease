import type { NetworkView } from "@/lib/api";

// 节点与边的视觉编码（参照实施方案 2.10）
export const NODE_COLOR: Record<string, string> = {
  disease: "#22C55E", // 当前疾病：亮绿色
  seed: "#15803D", // 模型种子：深绿色
  extended: "#F59E0B", // 网络扩展候选：金黄色
  background: "#CBD5E1", // 背景蛋白：灰色
};

export const NODE_SHAPE: Record<string, string> = {
  disease: "ellipse",
  seed: "ellipse",
  extended: "rectangle",
  background: "ellipse",
};

export const NODE_SIZE: Record<string, number> = {
  disease: 40,
  seed: 24,
  extended: 22,
  background: 14,
};

export const EDGE_COLOR: Record<string, string> = {
  evidence: "#86EFAC", // 疾病—靶点证据边：浅绿
  association: "#FDE68A", // 蛋白功能关联边：浅金
};

export type NetworkElements = {
  nodes: { data: Record<string, unknown> }[];
  edges: { data: Record<string, unknown> }[];
};

export function buildElements(view: NetworkView): NetworkElements {
  const nodes = view.nodes.map((n) => ({
    data: {
      id: n.id,
      label: n.label,
      type: n.type,
      geneId: n.gene_id ?? "",
      nScore: n.n_score,
      relevanceScore: n.relevance_score,
    },
  }));
  const edges = view.edges.map((e) => ({
    data: {
      id: e.id,
      source: e.source,
      target: e.target,
      type: e.type,
      score: e.score,
      version: e.version ?? "",
    },
  }));
  return { nodes, edges };
}
