"use client";

import { useState } from "react";
import { AlertTriangle, Bot, CheckCircle2, ChevronDown, XCircle } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { AgentTrace } from "@/lib/api";

const STATUS_META: Record<string, { label: string; className: string; Icon: typeof CheckCircle2 }> = {
  completed: { label: "已完成", className: "bg-emerald-100 text-emerald-700", Icon: CheckCircle2 },
  fallback: { label: "降级兜底", className: "bg-amber-100 text-amber-700", Icon: AlertTriangle },
  failed: { label: "失败", className: "bg-red-100 text-red-700", Icon: XCircle },
};

function formatOutput(output: unknown): string {
  if (output == null) return "（无输出）";
  if (typeof output === "string") return output;
  try {
    return JSON.stringify(output, null, 2);
  } catch {
    return String(output);
  }
}

export default function AgentSteps({ agents }: { agents: AgentTrace[] }) {
  const [open, setOpen] = useState<Record<string, boolean>>({});
  if (!agents.length) return null;

  const completed = agents.filter((a) => a.status === "completed").length;
  const fallback = agents.filter((a) => a.status === "fallback").length;
  const totalMs = agents.reduce((sum, a) => sum + (a.duration_ms || 0), 0);

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2"><Bot size={18} />多智能体协作过程</CardTitle>
        <p className="text-xs text-muted-foreground">
          共 {agents.length} 个智能体 · 完成 {completed} · 降级 {fallback} · 累计耗时 {(totalMs / 1000).toFixed(1)}s
        </p>
      </CardHeader>
      <CardContent className="space-y-2">
        {agents.map((a, i) => {
          const meta = STATUS_META[a.status] ?? STATUS_META.completed;
          const isOpen = !!open[a.key];
          return (
            <div key={a.key} className="rounded-lg border border-border bg-card p-3">
              <div className="flex items-start gap-3">
                <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-primary/10 text-xs font-semibold text-primary">
                  {i + 1}
                </span>
                <div className="min-w-0 flex-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="text-sm font-semibold">{a.name}</span>
                    <span className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs ${meta.className}`}>
                      <meta.Icon size={12} />{meta.label}
                    </span>
                    <span className="text-xs text-muted-foreground">{((a.duration_ms || 0) / 1000).toFixed(1)}s</span>
                    {a.total_tokens != null && (
                      <span className="text-xs text-muted-foreground">{a.total_tokens} tokens</span>
                    )}
                  </div>
                  <p className="mt-1 text-xs text-muted-foreground">{a.summary}</p>
                  {a.error && <p className="mt-1 text-xs text-amber-600">{a.error}</p>}
                  <button
                    type="button"
                    onClick={() => setOpen((prev) => ({ ...prev, [a.key]: !isOpen }))}
                    className="mt-2 inline-flex items-center gap-1 text-xs text-primary hover:underline"
                  >
                    <ChevronDown size={13} className={isOpen ? "rotate-180 transition-transform" : "transition-transform"} />
                    {isOpen ? "收起输出" : "展开输出"}
                  </button>
                  {isOpen && (
                    <pre className="mt-2 max-h-72 overflow-auto whitespace-pre-wrap break-words rounded-md bg-secondary p-3 text-xs">
                      {formatOutput(a.output)}
                    </pre>
                  )}
                </div>
              </div>
            </div>
          );
        })}
      </CardContent>
    </Card>
  );
}
