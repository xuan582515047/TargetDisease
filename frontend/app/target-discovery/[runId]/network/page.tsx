"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { ArrowLeft, Search } from "lucide-react";
import { toast } from "sonner";
import cytoscape from "cytoscape";
import NetworkCanvas from "@/components/target-network/network-canvas";
import NetworkLegend from "@/components/target-network/network-legend";
import NetworkDetails from "@/components/target-network/network-details";
import { api, type NetworkEdge, type NetworkNode, type NetworkView, type Run } from "@/lib/api";
import { buildElements } from "@/lib/target-network";

export default function NetworkPage() {
  const params = useParams<{ runId: string }>();
  const runId = params.runId;
  const [run, setRun] = useState<Run | null>(null);
  const [view, setView] = useState<NetworkView | null>(null);
  const [threshold, setThreshold] = useState(0.7);
  const [layers, setLayers] = useState(2);
  const [showBackground, setShowBackground] = useState(false);
  const [selectedNode, setSelectedNode] = useState<NetworkNode | null>(null);
  const [selectedEdge, setSelectedEdge] = useState<NetworkEdge | null>(null);
  const [query, setQuery] = useState("");
  const cyRef = useRef<cytoscape.Core | null>(null);

  const loadNetwork = useCallback(
    async (t: number, l: number, bg: boolean) => {
      try {
        const r = await api.targetAnalysis.get(runId);
        setRun(r);
        const v = await api.targetAnalysis.network(runId, {
          threshold: t,
          layers: l,
          include_background: bg,
        });
        setView(v);
      } catch (err) {
        toast.error(err instanceof Error ? err.message : "网络加载失败");
      }
    },
    [runId]
  );

  useEffect(() => {
    loadNetwork(threshold, layers, showBackground);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [runId]);

  useEffect(() => {
    const timer = setTimeout(() => loadNetwork(threshold, layers, showBackground), 300);
    return () => clearTimeout(timer);
  }, [threshold, layers, showBackground, loadNetwork]);

  const elements = useMemo(() => (view ? buildElements(view) : { nodes: [], edges: [] }), [view]);

  function onSelect(id: string, kind: "node" | "edge") {
    if (kind === "node") {
      setSelectedNode(view?.nodes.find((n) => n.id === id) ?? null);
      setSelectedEdge(null);
    } else {
      setSelectedEdge(view?.edges.find((e) => e.id === id) ?? null);
      setSelectedNode(null);
    }
  }

  function onSearch(e: React.FormEvent) {
    e.preventDefault();
    const node = view?.nodes.find((n) => n.label.toLowerCase() === query.trim().toLowerCase());
    if (node && cyRef.current) {
      cyRef.current.getElementById(node.id).select();
      cyRef.current.center(cyRef.current.getElementById(node.id));
    } else {
      toast.error("未找到该基因节点");
    }
  }

  function addCompare(targetId: string) {
    const current = new URLSearchParams(window.location.search).get("ids")?.split(",").filter(Boolean) ?? [];
    const next = [...new Set([...current, targetId])].slice(0, 4);
    window.location.href = `/target-discovery/${runId}/compare?ids=${next.join(",")}`;
  }

  return (
    <div className="flex h-[calc(100svh-0px)] min-h-0 flex-col">
      <div className="flex items-center gap-3 border-b border-border bg-background px-5 py-3">
        <Link href={`/target-discovery/${runId}`} className="text-muted-foreground hover:text-foreground">
          <ArrowLeft size={17} />
        </Link>
        <div>
          <p className="text-sm font-semibold">生物关联网络</p>
          <p className="text-xs text-muted-foreground">
            {run?.results_json?.disease?.name_zh ?? "当前疾病"} · 分析 {runId.slice(0, 8)}
          </p>
        </div>
        <form onSubmit={onSearch} className="ml-auto flex items-center gap-2">
          <div className="relative">
            <Search size={14} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-muted-foreground" />
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="按 gene symbol 搜索"
              className="h-8 w-52 rounded-lg border border-input bg-transparent pl-8 pr-2 text-sm outline-none focus-visible:border-ring"
            />
          </div>
        </form>
      </div>

      <div className="flex min-h-0 flex-1">
        <aside className="w-[260px] shrink-0 overflow-auto border-r border-border bg-background p-4">
          <div className="space-y-5">
            <div>
              <label className="mb-2 block text-xs font-semibold text-muted-foreground">
                关联边显示阈值（STRING 分值）
              </label>
              <input
                type="range"
                min={0.4}
                max={1}
                step={0.05}
                value={threshold}
                onChange={(e) => setThreshold(Number(e.target.value))}
                className="w-full accent-primary"
              />
              <div className="flex justify-between text-[10px] text-muted-foreground">
                <span>0.4</span>
                <span className="font-semibold text-primary">{threshold.toFixed(2)}</span>
                <span>1</span>
              </div>
            </div>

            <div>
              <p className="mb-2 text-xs font-semibold text-muted-foreground">邻域层数</p>
              <div className="flex gap-2">
                {[1, 2].map((l) => (
                  <button
                    key={l}
                    type="button"
                    onClick={() => setLayers(l)}
                    className={`flex-1 rounded-lg border px-3 py-1.5 text-xs font-medium transition-colors ${
                      layers === l ? "border-primary bg-primary/10 text-primary" : "border-border text-muted-foreground"
                    }`}
                  >
                    {l} 跳
                  </button>
                ))}
              </div>
            </div>

            <div>
              <p className="mb-2 text-xs font-semibold text-muted-foreground">节点显示</p>
              <label className="flex items-center gap-2 text-xs">
                <input type="checkbox" checked={showBackground} onChange={(e) => setShowBackground(e.target.checked)} className="accent-primary" />
                显示背景蛋白
              </label>
            </div>

            <NetworkLegend
              stats={{
                display_nodes: view?.display_nodes,
                display_edges: view?.display_edges,
                total_nodes: view?.total_nodes,
                total_edges: view?.total_edges,
                truncated: view?.truncated,
              }}
            />
          </div>
        </aside>

        <main className="relative min-w-0 flex-1 bg-[#F4F8FF]">
          <NetworkCanvas elements={elements} onSelect={onSelect} onReady={(cy) => (cyRef.current = cy)} />
        </main>
      </div>

      {(selectedNode || selectedEdge) && (
        <NetworkDetails
          node={selectedNode}
          edge={selectedEdge}
          onClose={() => {
            setSelectedNode(null);
            setSelectedEdge(null);
          }}
          onAddCompare={addCompare}
        />
      )}
    </div>
  );
}
