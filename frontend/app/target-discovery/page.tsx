"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { ArrowRight, ArrowLeft, Crosshair, KeyRound, Search, Check, Network, FileText, Sparkles, ChevronRight } from "lucide-react";
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
  const [step, setStep] = useState(1);

  useEffect(() => {
    let cancelled = false;
    Promise.allSettled([api.targetAnalysis.catalog(), api.projects.list(), api.credentials.status()]).then(
      ([d, p, c]) => {
        if (cancelled) return;
        if (d.status === "fulfilled") setDiseases(d.value.diseases);
        else toast.error("疾病目录加载失败");
        if (p.status === "fulfilled") setProjects(p.value);
        if (c.status === "fulfilled") setCred(c.value);
        const pid = new URLSearchParams(window.location.search).get("project_id");
        if (pid) setProjectId(pid);
      }
    );
    return () => { cancelled = true; };
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
    if (step === 1) { setStep(2); return; }
    if (!validLength) {
      toast.error("研究问题需为 10～1000 个字符");
      return;
    }
    if (step < 3) { setStep(step + 1); return; }
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

  function fillExample(mechanism = "证据支持") {
    const disease = selectedDisease || diseases[0];
    if (!disease) return;
    setSelectedDisease(disease);
    setQuestion(`我想研究${disease.name_zh}中与${mechanism}相关的潜在干预靶点，结合现有证据与生物功能关联网络优选值得进一步研究的候选。`);
    setKeywords(mechanism === "证据支持" ? "" : mechanism);
    setStep(2);
  }
  const ready = !!selectedDisease && validLength && !!cred?.configured;
  return (
    <div className="studio-page discovery-studio">
      <header className="studio-heading"><div><h1>新建靶点分析</h1><p>选择疾病并填写研究问题，生成候选靶点与证据报告。</p></div><span className="studio-tag"><Crosshair size={14}/>新建靶点优选</span></header>
      <div className="discovery-workspace">
        <section className="studio-panel discovery-builder">
          <nav className="builder-steps" aria-label="研究设置步骤">{["选择疾病","描述问题","确认研究"].map((label,index)=><button type="button" key={label} onClick={()=>setStep(index+1)} disabled={loading || (index===1&&!selectedDisease)||(index===2&&(!selectedDisease||!validLength))} aria-current={step===index+1?"step":undefined}><span>{step>index+1?<Check size={15}/>:String(index+1).padStart(2,"0")}</span><b>{label}</b>{index<2&&<ChevronRight size={15}/>}</button>)}</nav>
          <form onSubmit={onSubmit}>
            {step===1&&<div className="builder-stage"><h2>选择疾病</h2><p>从已收录的疾病证据快照中选择一个方向。</p><label className="studio-search disease-search"><Search size={18}/><Input id="disease-search" aria-label="搜索疾病" value={query} onChange={e=>setQuery(e.target.value)} placeholder="搜索疾病名称或标准 ID"/></label><div className="disease-options">{filtered.length===0&&<p className="studio-helper">未找到匹配的疾病，请修改搜索内容。</p>}{filtered.map(d=><button type="button" key={d.id} aria-pressed={selectedDisease?.id===d.id} onClick={()=>setSelectedDisease(d)}><span className="disease-symbol"><Crosshair size={25} strokeWidth={1.4}/></span><span><b>{d.name_zh}</b><small>{d.name}</small><code>{d.id}</code></span><span className="disease-radio">{selectedDisease?.id===d.id&&<Check size={14}/>}</span></button>)}</div><div className="builder-tip"><FileText size={18}/><p>数据来源<small>疾病目录来自项目已加载的 Open Targets 本地快照。</small></p></div></div>}
            {step===2&&<div className="builder-stage"><h2>填写研究问题</h2><p>具体的问题，有助于大模型识别更相关的种子靶点。</p><div className="builder-selected"><Crosshair size={16}/>{selectedDisease?.name_zh}<button type="button" onClick={()=>setStep(1)}>更换疾病</button></div><Label htmlFor="question">研究问题（10～1000 字）</Label><textarea id="question" maxLength={1000} rows={5} value={question} onChange={e=>setQuestion(e.target.value)} placeholder="描述你关注的疾病机制、潜在干预方向或想进一步验证的研究问题…" aria-describedby="question-count"/><div className="question-footer"><span>建议包含：疾病 + 机制 + 研究目的</span><span id="question-count">{question.length} / 1000</span></div><div className="question-presets"><span><Sparkles size={14}/>从灵感开始</span>{["神经炎症","突触功能","蛋白磷酸化"].map(m=><button type="button" key={m} onClick={()=>fillExample(m)}>{m}</button>)}<button type="button" onClick={()=>fillExample()}>填入示例问题</button></div><div className="builder-fields"><div><Label htmlFor="keywords">机制关键词 <small>可选</small></Label><Input id="keywords" value={keywords} onChange={e=>setKeywords(e.target.value)} placeholder="用逗号分隔，如：神经炎症、突触功能"/></div><div><Label htmlFor="project">归属项目</Label><select id="project" value={projectId} onChange={e=>setProjectId(e.target.value)}><option value="">自动新建项目</option>{projects.map(p=><option key={p.id} value={p.id}>{p.name}</option>)}</select></div></div></div>}
            {step===3&&<div className="builder-stage"><h2>确认分析信息</h2><p>确认研究输入后，即可启动靶点优选。</p><dl className="research-review"><div><dt>疾病方向</dt><dd>{selectedDisease?.name_zh}<code>{selectedDisease?.id}</code></dd></div><div><dt>研究问题</dt><dd>{question}</dd></div><div><dt>机制关键词</dt><dd>{keywords||"未指定，由研究问题识别"}</dd></div><div><dt>归属项目</dt><dd>{projects.find(p=>p.id===projectId)?.name||"自动新建项目"}</dd></div></dl>{!cred?.configured?<div className="studio-feedback warning"><KeyRound size={19}/><span>还差一步：配置模型凭据后即可开始。<Link href="/settings/api-keys">前往模型配置 <ArrowRight size={14}/></Link></span></div>:<div className="studio-feedback success"><Check size={18}/>模型凭据已保存，可以提交研究任务。</div>}</div>}
            <footer className="builder-actions"><button type="button" className="studio-text-button" onClick={()=>setStep(step-1)} disabled={step===1||loading}><ArrowLeft size={16}/>上一步</button><span>{step} / 3</span><Button type="submit" className="studio-button" disabled={loading||(step===1&&!selectedDisease)||(step===2&&!validLength)||(step===3&&!ready)}>{loading?"正在创建研究…":step===3?"开始识别":step===2?"确认研究":"下一步：描述问题"}<ArrowRight size={17}/></Button></footer>
          </form>
        </section>
        <aside className="research-brief"><h2>本次分析</h2><div className="brief-disease"><Crosshair size={25}/><span>{selectedDisease?.name_zh||"等待选择疾病"}<small>{selectedDisease?.id||"先确定一个研究方向"}</small></span></div><div className="brief-item"><span>研究问题</span><p>{question||"一个具体的问题，将成为候选优选的起点。"}</p></div><div className="brief-outputs"><h3>分析结果包含</h3><span><Crosshair size={17}/><div><b>候选靶点排序</b><small>结合模型、证据与网络依据</small></div></span><span><Network size={17}/><div><b>交互关联网络</b><small>查看种子与扩展候选的连接</small></div></span><span><FileText size={17}/><div><b>可追溯研究报告</b><small>对比结果，导出研究依据</small></div></span></div><p className="brief-note">功能关联不等于因果关系。<br/>结果用于候选优选与后续研究。</p></aside>
      </div>
    </div>
  );
}
