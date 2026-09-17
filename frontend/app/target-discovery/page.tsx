"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { ArrowRight, Crosshair, KeyRound, Check, Network, FileText, Sparkles } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { toast } from "sonner";
import { api, type CredentialStatus, type Project } from "@/lib/api";

export default function TargetDiscoveryPage() {
  const router = useRouter();
  const [projects, setProjects] = useState<Project[]>([]);
  const [cred, setCred] = useState<CredentialStatus | null>(null);
  const [projectId, setProjectId] = useState("");
  const [question, setQuestion] = useState("");
  const [keywords, setKeywords] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    let cancelled = false;
    Promise.allSettled([api.projects.list(), api.credentials.status()]).then(([p, c]) => {
      if (cancelled) return;
      if (p.status === "fulfilled") setProjects(p.value);
      if (c.status === "fulfilled") setCred(c.value);
      const pid = new URLSearchParams(window.location.search).get("project_id");
      if (pid) setProjectId(pid);
    });
    return () => { cancelled = true; };
  }, []);

  const validLength = question.trim().length >= 10 && question.trim().length <= 1000;

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!validLength) {
      toast.error("研究问题需为 10～1000 个字符");
      return;
    }
    setLoading(true);
    try {
      let pid = projectId;
      if (!pid) {
        const p = await api.projects.create({ name: question.trim().slice(0, 30) });
        pid = p.id;
      }
      const keywordList = keywords
        .split(/[,，、\s]+/)
        .map((s) => s.trim())
        .filter(Boolean);
      const run = await api.targetAnalysis.create({
        project_id: pid,
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

  function fillExample(mechanism = "神经炎症") {
    setQuestion(
      `我想研究阿尔茨海默病中的${mechanism}机制，请结合现有知识推荐值得优先研究的候选靶点基因，并说明理由与可能的机制。`
    );
    setKeywords(mechanism === "证据支持" ? "" : mechanism);
  }

  const ready = validLength && !!cred?.configured;

  return (
    <div className="studio-page discovery-studio">
      <header className="studio-heading">
        <div>
          <h1>新建靶点分析</h1>
          <p>用自然语言描述研究问题，大模型将推荐候选靶点并生成关联网络。</p>
        </div>
        <span className="studio-tag"><Crosshair size={14} />自由文本靶点优选</span>
      </header>
      <div className="discovery-workspace">
        <section className="studio-panel discovery-builder">
          <form onSubmit={onSubmit}>
            <div className="builder-stage">
              <h2>描述研究问题</h2>
              <p>具体的问题，有助于大模型推荐更相关的候选靶点。</p>
              <Label htmlFor="question">研究问题（10～1000 字）</Label>
              <textarea
                id="question"
                maxLength={1000}
                rows={5}
                value={question}
                onChange={(e) => setQuestion(e.target.value)}
                placeholder="描述你关注的疾病、机制、潜在干预方向或想进一步验证的研究问题…"
                aria-describedby="question-count"
              />
              <div className="question-footer">
                <span>建议包含：疾病 + 机制 + 研究目的</span>
                <span id="question-count">{question.length} / 1000</span>
              </div>
              <div className="question-presets">
                <span><Sparkles size={14} />从灵感开始</span>
                {["神经炎症", "突触功能", "蛋白磷酸化"].map((m) => (
                  <button type="button" key={m} onClick={() => fillExample(m)}>{m}</button>
                ))}
              </div>
              <div className="builder-fields">
                <div>
                  <Label htmlFor="keywords">机制关键词 <small>可选</small></Label>
                  <Input id="keywords" value={keywords} onChange={(e) => setKeywords(e.target.value)} placeholder="用逗号分隔，如：神经炎症、突触功能" />
                </div>
                <div>
                  <Label htmlFor="project">归属项目</Label>
                  <select id="project" value={projectId} onChange={(e) => setProjectId(e.target.value)}>
                    <option value="">自动新建项目</option>
                    {projects.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
                  </select>
                </div>
              </div>
              {!cred?.configured ? (
                <div className="studio-feedback warning">
                  <KeyRound size={19} />
                  <span>还差一步：配置模型凭据后即可开始。<Link href="/settings/api-keys">前往模型配置 <ArrowRight size={14} /></Link></span>
                </div>
              ) : (
                <div className="studio-feedback success">
                  <Check size={18} />模型凭据已保存，可以提交研究任务。
                </div>
              )}
            </div>
            <footer className="builder-actions">
              <span className="studio-text-button" aria-hidden="true" />
              <Button type="submit" className="studio-button" disabled={loading || !ready}>
                {loading ? "正在创建研究…" : "开始识别"}<ArrowRight size={17} />
              </Button>
            </footer>
          </form>
        </section>
        <aside className="research-brief">
          <h2>本次分析</h2>
          <div className="brief-item"><span>研究问题</span><p>{question || "一个具体的问题，将成为候选优选的起点。"}</p></div>
          <div className="brief-outputs">
            <h3>分析结果包含</h3>
            <span><Crosshair size={17} /><div><b>候选靶点排序</b><small>模型种子 + 网络扩展</small></div></span>
            <span><Network size={17} /><div><b>交互关联网络</b><small>查看种子与扩展候选的连接</small></div></span>
            <span><FileText size={17} /><div><b>可追溯研究报告</b><small>对比结果，导出研究依据</small></div></span>
          </div>
          <p className="brief-note">推荐结果由大模型自由生成，仅作候选优选参考。<br />不构成新靶点发现或临床结论。</p>
        </aside>
      </div>
    </div>
  );
}
