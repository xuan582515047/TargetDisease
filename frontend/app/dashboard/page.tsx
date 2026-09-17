"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { ArrowRight, ArrowUpRight, Check, Crosshair, FolderOpen, KeyRound, Clock3, Search, Activity, Plus, Layers3 } from "lucide-react";
import { api, type CredentialStatus, type Project, type Run } from "@/lib/api";
import CountUp from "@/components/count-up";

const labels: Record<string,string> = {queued:"排队中",running:"运行中",completed:"已完成",failed:"失败"};
export default function DashboardPage() {
  const [projects,setProjects]=useState<Project[]>([]);
  const [runs,setRuns]=useState<Run[]>([]);
  const [cred,setCred]=useState<CredentialStatus|null>(null);
  const [loading,setLoading]=useState(true);
  const [error,setError]=useState("");
  const [filter,setFilter]=useState("all");
  const [query,setQuery]=useState("");
  useEffect(()=>{let active=true;Promise.allSettled([api.projects.list(),api.runs.list(),api.credentials.status()]).then(([p,r,c])=>{if(!active)return;setProjects(p.status==="fulfilled"?p.value:[]);setRuns(r.status==="fulfilled"?r.value:[]);setCred(c.status==="fulfilled"?c.value:null);if(p.status==="rejected"||r.status==="rejected"||c.status==="rejected")setError("部分数据未能加载，请刷新页面重试。");setLoading(false)});return()=>{active=false}},[]);
  const completed=runs.filter(r=>r.status==="completed").length;
  const activeRuns=runs.filter(r=>["queued","running"].includes(r.status)).length;
  const filtered=runs.filter(r=>(filter==="all"||r.status===filter||(filter==="active"&&["queued","running"].includes(r.status)))&&`${r.results_json?.disease?.name||(r.intermediate_json?.question as string)||""} ${projects.find(p=>p.id===r.project_id)?.name||""}`.toLowerCase().includes(query.toLowerCase()));
  return <div className="studio-page">
    <header className="studio-heading"><div><h1>工作台</h1><p>查看分析进度，管理研究项目和候选靶点。</p></div><Link href="/target-discovery" className="studio-button"><Plus size={17}/>新建分析</Link></header>
    {error&&<p className="studio-alert" role="alert">{error}</p>}
    <div className="studio-metrics" aria-busy={loading}>{[[FolderOpen,"研究项目",projects.length],[Activity,"分析任务",runs.length],[Check,"已完成",completed],[Clock3,"进行中",activeRuns]].map(([Icon,label,value])=>{const Symbol=Icon as typeof FolderOpen;return <div key={String(label)}><Symbol size={19}/><span>{String(label)}</span><strong>{loading?"—":<CountUp value={Number(value)}/>}</strong></div>})}</div>
    <div className="studio-bento">
      <section className="studio-ready studio-panel"><div className="studio-panel-title"><h2>模型连接</h2></div><p>分析前请确认模型连接可用。</p><div className={`ready-item ${cred?.validated?"done":""}`}><span>{cred?.validated?<Check size={15}/>:<KeyRound size={15}/>}</span><div><b>{loading?"读取模型状态…":cred?.validated?"模型连接已验证":cred?.configured?"凭据已保存，待验证":"连接 DeepSeek 模型"}</b><small>{cred?.validated?"可以开始靶点分析":"用于根据研究问题推荐种子靶点"}</small></div></div><Link href={cred?.validated?"/target-discovery":"/settings/api-keys"}>{cred?.validated?"开始研究":"完成模型配置"}<ArrowRight size={17}/></Link></section>
      <section className="studio-runs studio-panel"><div className="studio-panel-title"><div><h2>研究任务</h2><p>查看最近的分析任务及结果。</p></div><span className="studio-count">{loading?"—":runs.length} 条记录</span></div><div className="studio-task-tools"><div className="studio-segments" role="group" aria-label="按任务状态筛选">{[["all","全部"],["active","进行中"],["completed","已完成"],["failed","失败"]].map(([value,label])=><button key={value} aria-pressed={filter===value} onClick={()=>setFilter(value)}>{label}</button>)}</div><label className="studio-search"><Search size={15}/><input aria-label="搜索研究任务" value={query} onChange={e=>setQuery(e.target.value)} placeholder="搜索疾病或项目"/></label></div>
      {loading?<div className="studio-empty" role="status">正在读取研究任务…</div>:filtered.length===0?<div className="studio-empty"><div className="empty-orbits"><Crosshair size={26}/></div><h3>{runs.length?"没有匹配的任务":"暂无分析任务"}</h3><p>{runs.length?"尝试切换状态或修改搜索关键词。":"新建分析后，可在这里查看进度和结果。"}</p>{runs.length?<button className="studio-text-button" onClick={()=>{setFilter("all");setQuery("")}}>清除筛选 <ArrowRight size={15}/></button>:<Link href="/target-discovery" className="studio-text-button">新建分析 <ArrowRight size={15}/></Link>}</div>:<div className="studio-run-list">{filtered.slice(0,10).map(r=><Link href={`/target-discovery/${r.id}`} key={r.id} className="studio-run-row"><span className="run-symbol"><Crosshair size={18}/></span><div><b>{r.results_json?.disease?.name||(r.intermediate_json?.question as string)?.slice(0,24)||"靶点优选分析"}</b><small>{new Date(r.created_at).toLocaleString("zh-CN")}</small></div><span className={`studio-status ${r.status}`}>{labels[r.status]||r.status}</span><ArrowUpRight size={16}/></Link>)}</div>}</section>
      <section className="studio-projects studio-panel"><div className="studio-panel-title"><h2>最近项目</h2><Link href="/projects" aria-label="查看所有项目"><ArrowUpRight size={19}/></Link></div>{loading?<p>正在读取项目…</p>:projects.length?<div className="studio-project-list">{projects.slice(0,3).map(p=><Link href={`/target-discovery?project_id=${p.id}`} key={p.id}><FolderOpen size={19}/><div><b>{p.name}</b><small>{p.primary_disease||"研究项目"}</small></div><ArrowRight size={15}/></Link>)}</div>:<div className="studio-project-empty"><Layers3 size={32}/><h3>暂无研究项目</h3><p>创建项目，按疾病或研究方向整理分析任务。</p><Link href="/projects">管理研究项目 <ArrowRight size={15}/></Link></div>}<div className="studio-project-foot"><KeyRound size={15}/><span>模型配置</span><Link href="/settings/api-keys">{loading?"读取中":cred?.validated?"已验证":cred?.configured?"待验证":"未连接"}<ArrowRight size={13}/></Link></div></section>
    </div>
  </div>;
}
