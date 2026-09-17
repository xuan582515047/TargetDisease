"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { ArrowLeft } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { toast } from "sonner";
import { api, type Run, type TargetCandidate } from "@/lib/api";

export default function ComparePage() {
  const params = useParams<{ runId: string }>();
  const runId = params.runId;
  const [run, setRun] = useState<Run | null>(null);
  const [ids, setIds] = useState<string[]>([]);

  useEffect(() => {
    const raw = new URLSearchParams(window.location.search).get("ids");
    setIds((raw ?? "").split(",").filter(Boolean).slice(0, 4));
  }, []);

  const load = useCallback(async () => {
    try {
      setRun(await api.targetAnalysis.get(runId));
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "加载失败");
    }
  }, [runId]);

  useEffect(() => {
    load();
  }, [load]);

  const candidates = useMemo(() => {
    if (!run?.results_json) return [];
    const all = run.results_json.candidates;
    return ids.map((id) => all.find((c) => c.target_id === id)).filter(Boolean) as TargetCandidate[];
  }, [run, ids]);

  return (
    <div className="research-dashboard">
      <div className="workspace-heading">
        <div>
          <p className="workspace-eyebrow">COMPARE / 候选对比</p>
          <h1>候选靶点对比</h1>
          <p>按相同字段并列展示 {candidates.length} 个候选靶点。</p>
        </div>
        <Link href={`/target-discovery/${runId}`} className="workspace-outline-link">
          <ArrowLeft size={16} /> 返回结果
        </Link>
      </div>

      {candidates.length < 2 && (
        <Card>
          <CardContent className="py-10 text-center text-sm text-muted-foreground">
            请至少选择 2 个靶点进行对比
          </CardContent>
        </Card>
      )}

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        {candidates.map((c) => {
          return (
            <Card key={c.target_id}>
              <CardHeader>
                <CardTitle className="text-base">{c.symbol || c.target_id}</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3 text-sm">
                <div className="flex items-center gap-2">
                  <span className="rounded-full bg-primary/10 px-2 py-0.5 text-xs text-primary">
                    {c.source === "seed" ? "模型种子" : "网络扩展"}
                  </span>
                </div>
                {c.reason && <p className="text-xs text-muted-foreground">{c.reason}</p>}
                {c.mechanism && <p className="text-xs text-muted-foreground">机制：{c.mechanism}</p>}
                <div className="grid grid-cols-2 gap-2 border-t border-border pt-3 text-center">
                  <div><p className="text-[10px] text-muted-foreground">相关度分</p><p className="font-semibold">{c.relevance_score != null ? c.relevance_score.toFixed(2) : "—"}</p></div>
                  <div><p className="text-[10px] text-muted-foreground">网络分N</p><p className="font-semibold text-primary">{c.n_score != null ? c.n_score.toFixed(2) : "—"}</p></div>
                </div>
                {c.in_network != null && (
                  <div className="border-t border-border pt-2 text-xs text-muted-foreground">
                    <p>网络映射：{c.in_network ? "已映射" : "未映射"}</p>
                  </div>
                )}
              </CardContent>
            </Card>
          );
        })}
      </div>
    </div>
  );
}
