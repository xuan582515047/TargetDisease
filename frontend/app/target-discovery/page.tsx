"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { ArrowRight, Crosshair, KeyRound, Search } from "lucide-react";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { toast } from "sonner";
import { api, type CredentialStatus, type DiseaseInfo, type Project } from "@/lib/api";

export default function TargetDiscoveryPage() {
  const router = useRouter();
  const [diseases, setDiseases] = useState<DiseaseInfo[]>([]);
  const [projects, setProjects] = useState<Project[]>([]);
  const [cred, setCred] = useState<CredentialStatus | null>(null);

  const [query, setQuery] = useState("");
  const [selectedDisease, setSelectedDisease] = useState<DiseaseInfo | null>(null);
  const [projectId, setProjectId] = useState("");
  const [question, setQuestion] = useState("");
  const [keywords, setKeywords] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    Promise.allSettled([api.targetAnalysis.catalog(), api.projects.list(), api.credentials.status()]).then(
      ([d, p, c]) => {
        if (d.status === "fulfilled") setDiseases(d.value.diseases);
        else toast.error("疾病目录加载失败");
        if (p.status === "fulfilled") setProjects(p.value);
        if (c.status === "fulfilled") setCred(c.value);
      }
    );
  }, []);

  // 从项目卡片带 ?project_id= 进入时预选该项目
  useEffect(() => {
    const pid = new URLSearchParams(window.location.search).get("project_id");
    if (pid) setProjectId(pid);
  }, []);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return diseases;
    return diseases.filter(
      (d) =>
        d.name_zh.toLowerCase().includes(q) ||
        d.name.toLowerCase().includes(q) ||
        d.id.toLowerCase().includes(q)
    );
  }, [diseases, query]);

  const validLength = question.trim().length >= 10 && question.trim().length <= 1000;

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!selectedDisease) {
      toast.error("请先选择一个疾病方向");
      return;
    }
    if (!validLength) {
      toast.error("研究问题需为 10～1000 个字符");
      return;
    }
    setLoading(true);
    try {
      let pid = projectId;
      if (!pid) {
        const p = await api.projects.create({
          name: selectedDisease.name_zh,
          primary_disease: selectedDisease.name_zh,
        });
        pid = p.id;
      }
      const keywordList = keywords
        .split(/[,，、\s]+/)
        .map((s) => s.trim())
        .filter(Boolean);
      const run = await api.targetAnalysis.create({
        project_id: pid,
        disease_id: selectedDisease.id,
        question: question.trim(),
        mechanism_keywords: keywordList,
      });
      router.push(`/target-discovery/${run.id}`);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "创建分析失败");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="research-dashboard">
      <div className="workspace-heading">
        <div>
          <p className="workspace-eyebrow">TARGET DISCOVERY / 靶点识别</p>
          <h1>研究问题输入</h1>
          <p>选择疾病方向，填写研究问题，识别种子靶点并扩展候选。</p>
        </div>
      </div>

      <Card className="analysis-panel">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Crosshair size={20} />新建靶点优选分析
          </CardTitle>
          <CardDescription>大模型识别种子 → 网络传播扩展 → 证据核查 → 报告</CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={onSubmit} className="space-y-5">
            <div className="space-y-2">
              <Label>疾病方向</Label>
              <div className="relative">
                <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
                <Input
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  placeholder="搜索疾病名称或标准 ID…"
                  className="pl-9"
                />
              </div>
              <div className="max-h-52 space-y-1 overflow-auto rounded-lg border border-border bg-secondary/40 p-2">
                {filtered.length === 0 && (
                  <p className="px-2 py-3 text-xs text-muted-foreground">未找到匹配的疾病</p>
                )}
                {filtered.map((d) => {
                  const active = selectedDisease?.id === d.id;
                  return (
                    <button
                      type="button"
                      key={d.id}
                      onClick={() => setSelectedDisease(d)}
                      className={`flex w-full items-center justify-between rounded-md px-3 py-2 text-left text-sm transition-colors ${
                        active ? "bg-primary/10 text-primary" : "hover:bg-background"
                      }`}
                    >
                      <span>{d.name_zh}</span>
                      <span className="font-mono text-xs text-muted-foreground">{d.id}</span>
                    </button>
                  );
                })}
              </div>
              {selectedDisease && (
                <p className="text-xs text-muted-foreground">
                  已选：{selectedDisease.name_zh}（{selectedDisease.name}，{selectedDisease.id}）
                </p>
              )}
            </div>

            <div className="space-y-2">
              <Label htmlFor="question">研究问题（10～1000 字）</Label>
              <textarea
                id="question"
                value={question}
                onChange={(e) => setQuestion(e.target.value)}
                rows={4}
                placeholder="例如：我想研究阿尔茨海默病中与 tau 蛋白磷酸化相关的潜在干预靶点，重点关注神经炎症与突触功能障碍机制…"
                className="w-full rounded-lg border border-border bg-secondary/30 p-3 text-sm outline-none focus-visible:border-ring"
              />
              <p className="text-right text-xs text-muted-foreground">{question.length} / 1000</p>
            </div>

            <div className="grid gap-4 sm:grid-cols-2">
              <div className="space-y-2">
                <Label htmlFor="keywords">机制关键词（可选，逗号分隔）</Label>
                <Input
                  id="keywords"
                  value={keywords}
                  onChange={(e) => setKeywords(e.target.value)}
                  placeholder="如：神经炎症、突触功能障碍"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="project">归属项目</Label>
                <select
                  id="project"
                  value={projectId}
                  onChange={(e) => setProjectId(e.target.value)}
                  className="h-8 w-full rounded-lg border border-input bg-transparent px-2.5 text-sm outline-none focus-visible:border-ring"
                >
                  <option value="">自动新建项目</option>
                  {projects.map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.name}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            {!cred?.configured && (
              <p className="text-sm text-amber-600">
                尚未配置 DeepSeek API Key，请先前往{" "}
                <Link href="/settings/api-keys" className="underline">
                  API Key 设置
                </Link>
                。
              </p>
            )}

            <div className="analysis-submit-row">
              <p>分析结果将保存在归属项目中，可通过关联网络查看与导出</p>
              <Button type="submit" disabled={loading || !selectedDisease || !validLength}>
                {loading ? "提交中…" : "开始识别"} <ArrowRight size={16} />
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
