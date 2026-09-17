"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { ArrowLeft, Network, Scale, FileText, Loader2, CheckCircle2, XCircle } from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";
import { api, type Run, type TargetCandidate } from "@/lib/api";

const STATUS_LABEL: Record<string, string> = {
  queued: "排队中",
  running: "运行中",
  completed: "已完成",
  failed: "失败",
};

const STATUS_BADGE: Record<string, string> = {
  passed: "bg-emerald-100 text-emerald-700",
  partial: "bg-amber-100 text-amber-700",
  missing: "bg-muted text-muted-foreground",
  id_mismatch: "bg-red-100 text-red-700",
};

export default function RunResultPage() {
  const params = useParams<{ runId: string }>();
  const router = useRouter();
  const runId = params.runId;
  const [run, setRun] = useState<Run | null>(null);
  const [view, setView] = useState<"model" | "evidence" | "fusion">("fusion");
  const [compare, setCompare] = useState<Set<string>>(new Set());

  const load = useCallback(async () => {
    try {
      const r = await api.targetAnalysis.get(runId);
      setRun(r);
      return r.status;
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "加载失败");
      return null;
    }
  }, [runId]);

  useEffect(() => {
    let cancelled = false;
    let timer: ReturnType<typeof setTimeout> | null = null;
    async function poll() {
      const status = await load();
      if (cancelled) return;
      if (status === "queued" || status === "running") {
        timer = setTimeout(poll, 2000);
      }
    }
    poll();
    return () => {
      cancelled = true;
      if (timer) clearTimeout(timer);
    };
  }, [load]);

  const candidates = useMemo(() => {
    if (!run?.results_json) return [];
    const r = run.results_json;
    if (view === "model") return r.rankings.model;
    if (view === "evidence") return r.rankings.evidence;
    return r.rankings.fusion;
  }, [run, view]);

  function toggleCompare(id: string) {
    setCompare((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else if (next.size < 4) next.add(id);
      else toast.error("最多选择 4 个靶点进行对比");
      return next;
    });
  }

  const terminal = run && (run.status === "completed" || run.status === "failed");

  return (
    <div className="research-dashboard">
      <div className="workspace-heading">
        <div>
          <p className="workspace-eyebrow">RUN RESULT / 分析结果</p>
          <h1>{run?.results_json?.disease?.name_zh ?? "靶点优选分析"}</h1>
          <p>分析编号 {runId.slice(0, 8)} · {run ? STATUS_LABEL[run.status] ?? run.status : "加载中…"}</p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={() => router.push("/target-discovery")}>
            <ArrowLeft size={15} /> 返回
          </Button>
          {terminal && run.status === "completed" && (
            <>
              <Link href={`/target-discovery/${runId}/network`}>
                <Button variant="outline" size="sm"><Network size={15} /> 关联网络</Button>
              </Link>
              <Link href={`/target-discovery/${runId}/report`}>
                <Button variant="outline" size="sm"><FileText size={15} /> 报告</Button>
              </Link>
            </>
          )}
        </div>
      </div>

      {!terminal && (
        <Card>
          <CardContent className="flex items-center gap-3 py-8 text-sm text-muted-foreground">
            <Loader2 size={18} className="animate-spin text-primary" />
            正在执行靶点识别，请稍候…（模型识别与网络传播可能需要几十秒）
          </CardContent>
        </Card>
      )}

      {terminal && run.status === "failed" && (
        <Card>
          <CardContent className="flex items-start gap-3 py-8">
            <XCircle size={20} className="text-destructive" />
            <div>
              <p className="font-medium text-destructive">分析失败</p>
              <p className="mt-1 text-sm text-muted-foreground">{run.error_message || "未知错误"}</p>
            </div>
          </CardContent>
        </Card>
      )}

      {terminal && run.status === "completed" && run.results_json && (
        <>
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2"><CheckCircle2 size={18} />识别摘要</CardTitle>
              <CardDescription>{run.results_json.question_summary || run.results_json.question}</CardDescription>
            </CardHeader>
            <CardContent className="flex flex-wrap gap-6 text-sm">
              <span>种子靶点 <b className="text-primary">{run.results_json.seeds.length}</b></span>
              <span>扩展候选 <b className="text-primary">{run.results_json.extended_candidates.length}</b></span>
              <span>证据快照 v{run.results_json.evidence_snapshot_version}</span>
              {run.results_json.network_error && (
                <span className="text-amber-600">网络：{run.results_json.network_error}</span>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle>候选靶点</CardTitle>
                <div className="flex rounded-lg border border-border bg-secondary p-0.5">
                  {([
                    ["model", "模型推荐"],
                    ["evidence", "疾病证据"],
                    ["fusion", "融合排序"],
                  ] as const).map(([key, label]) => (
                    <button
                      key={key}
                      type="button"
                      onClick={() => setView(key)}
                      className={`rounded-md px-3 py-1.5 text-xs font-medium transition-colors ${
                        view === key ? "bg-white text-foreground shadow-sm" : "text-muted-foreground"
                      }`}
                    >
                      {label}
                    </button>
                  ))}
                </div>
              </div>
            </CardHeader>
            <CardContent className="space-y-2">
              {candidates.length === 0 && (
                <p className="py-6 text-center text-sm text-muted-foreground">该视图暂无候选</p>
              )}
              {candidates.map((c) => (
                <CandidateRow key={c.target_id} c={c} checked={compare.has(c.target_id)} onToggle={toggleCompare} />
              ))}
            </CardContent>
          </Card>

          <div className="flex items-center justify-end gap-3">
            <span className="text-xs text-muted-foreground">已选 {compare.size} 个靶点</span>
            <Link href={`/target-discovery/${runId}/compare?ids=${[...compare].join(",")}`}>
              <Button variant="outline" size="sm" disabled={compare.size < 2}>
                <Scale size={15} /> 对比所选
              </Button>
            </Link>
          </div>
        </>
      )}
    </div>
  );
}

function CandidateRow({
  c,
  checked,
  onToggle,
}: {
  c: TargetCandidate;
  checked: boolean;
  onToggle: (id: string) => void;
}) {
  const badge = STATUS_BADGE[c.status ?? ""] ?? STATUS_BADGE.missing;
  return (
    <div className="flex items-center gap-3 rounded-lg border border-border bg-card p-3">
      <input
        type="checkbox"
        checked={checked}
        onChange={() => onToggle(c.target_id)}
        className="accent-primary"
        aria-label={`选择 ${c.symbol}`}
      />
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2">
          <span className="font-semibold">{c.symbol || c.target_id}</span>
          <span className="rounded-full bg-primary/10 px-2 py-0.5 text-xs text-primary">
            {c.source === "seed" ? "种子" : "扩展"}
          </span>
          {c.status_label && (
            <span className={`rounded-full px-2 py-0.5 text-xs ${badge}`}>{c.status_label}</span>
          )}
        </div>
        {c.reason && <p className="mt-1 text-xs text-muted-foreground">{c.reason}</p>}
        <p className="mt-1 font-mono text-xs text-muted-foreground">{c.target_id}</p>
      </div>
      <div className="flex shrink-0 gap-4 text-right text-sm">
        <div><p className="text-xs text-muted-foreground">疾病分A</p><p>{c.a_score != null ? c.a_score.toFixed(2) : "—"}</p></div>
        <div><p className="text-xs text-muted-foreground">网络分N</p><p>{c.n_score != null ? c.n_score.toFixed(2) : "—"}</p></div>
        <div><p className="text-xs text-muted-foreground">融合分</p><p className="font-semibold text-primary">{c.fusion_score != null ? c.fusion_score.toFixed(1) : "—"}</p></div>
      </div>
    </div>
  );
}
