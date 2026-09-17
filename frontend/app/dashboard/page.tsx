"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { ArrowRight, Network, FolderOpen, Activity, KeyRound, Crosshair } from "lucide-react";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { toast } from "sonner";
import { api, type CredentialStatus, type Project, type Run } from "@/lib/api";

const STATUS_LABEL: Record<string, string> = {
  queued: "排队中",
  running: "运行中",
  completed: "已完成",
  failed: "失败",
};

export default function DashboardPage() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [runs, setRuns] = useState<Run[]>([]);
  const [cred, setCred] = useState<CredentialStatus | null>(null);

  const load = useCallback(async () => {
    const [p, r, c] = await Promise.allSettled([
      api.projects.list(),
      api.runs.list(),
      api.credentials.status(),
    ]);
    if (p.status === "rejected" || r.status === "rejected") {
      toast.error("部分数据加载失败，请刷新重试");
    }
    setProjects(p.status === "fulfilled" ? p.value : []);
    setRuns(r.status === "fulfilled" ? r.value : []);
    setCred(c.status === "fulfilled" ? c.value : null);
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  return (
    <div className="research-dashboard">
      <div className="workspace-heading">
        <div>
          <p className="workspace-eyebrow">OVERVIEW / 研究概览</p>
          <h1>研究工作台</h1>
          <p>从研究问题出发，识别并优选可解释的候选靶点。</p>
        </div>
        <Link href="/target-discovery" className="workspace-outline-link">
          <Crosshair size={16} /> 新建靶点识别 <ArrowRight size={15} />
        </Link>
      </div>

      <div className="dashboard-stats">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <FolderOpen size={17} />研究项目
            </CardTitle>
            <CardDescription>你的项目数</CardDescription>
          </CardHeader>
          <CardContent className="text-2xl font-semibold text-primary">{projects.length}</CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Activity size={17} />靶点分析
            </CardTitle>
            <CardDescription>已运行的识别任务</CardDescription>
          </CardHeader>
          <CardContent className="text-2xl font-semibold text-primary">{runs.length}</CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <KeyRound size={17} />模型凭据
            </CardTitle>
            <CardDescription>DeepSeek 凭据状态</CardDescription>
          </CardHeader>
          <CardContent className="text-2xl font-semibold text-primary">
            {cred?.configured ? (cred.validated ? "已验证" : "已配置") : "未配置"}
          </CardContent>
        </Card>
      </div>

      <Card className="recent-runs-panel">
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle className="flex items-center gap-2"><Network size={18} />最近运行</CardTitle>
            <span className="text-xs text-muted-foreground">最近 {Math.min(runs.length, 10)} 条记录</span>
          </div>
        </CardHeader>
        <CardContent className="space-y-2">
          {runs.length === 0 && (
            <div className="runs-empty">
              <span className="empty-icon"><Crosshair size={25} /></span>
              <div>
                <h3>你的第一条靶点优选，从这里开始</h3>
                <p>输入研究问题并选择疾病，识别种子靶点并扩展候选。</p>
              </div>
              <Link href="/target-discovery">创建首次识别 <ArrowRight size={15} /></Link>
            </div>
          )}
          {runs.slice(0, 10).map((r) => {
            const disease = (r.results_json?.disease?.name_zh) || (r.intermediate_json?.disease_id as string) || "—";
            return (
              <div
                key={r.id}
                className="flex items-center justify-between border-b border-border py-2 text-sm last:border-0"
              >
                <div>
                  <span className="font-medium">{disease}</span>
                  <span className="ml-2 text-muted-foreground">
                    {new Date(r.created_at).toLocaleString("zh-CN")}
                  </span>
                </div>
                <div className="flex items-center gap-3">
                  <span className="text-muted-foreground">{STATUS_LABEL[r.status] ?? r.status}</span>
                  <Link className="text-primary underline" href={`/target-discovery/${r.id}`}>
                    查看结果
                  </Link>
                </div>
              </div>
            );
          })}
        </CardContent>
      </Card>

      <footer className="workspace-footer">
        <span>靶研助手 · 研究工作空间</span>
        <span>研究问题 → 种子靶点 → 网络扩展 → 证据核查 → 报告</span>
      </footer>
    </div>
  );
}
