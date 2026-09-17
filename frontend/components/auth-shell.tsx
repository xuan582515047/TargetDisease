"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";
import { ArrowUpRight, FlaskConical, Crosshair, Network, ShieldCheck, ArrowLeft } from "lucide-react";

const chapters = [
  {icon:Crosshair,title:"靶点识别",label:"AI IDENTIFICATION",heading:<>疾病研究，<br/><span>从靶点分析开始</span></>,description:"用自然语言描述研究问题，大模型从证据池识别种子靶点。",node:"研究问题",next:"种子靶点",note:"理解问题 · 识别候选"},
  {icon:Network,title:"连接生物网络",label:"NETWORK EXPLORATION",heading:<>沿生物网络，<br/><span>发现关联候选</span></>,description:"沿蛋白功能关联网络传播，探索种子之外的潜在候选。",node:"种子靶点",next:"网络候选",note:"传播扩展 · 发现关联"},
  {icon:ShieldCheck,title:"证据核查",label:"EVIDENCE VALIDATION",heading:<>查看候选靶点，<br/><span>追溯证据来源</span></>,description:"核查证据引用与归属，在交互网络中理解并对比候选。",node:"候选靶点",next:"证据核查",note:"依据核查 · 报告沉淀"},
];
export default function AuthShell({children}:{children:React.ReactNode}) {
  const pathname=usePathname();
  const [chapter,setChapter]=useState(0);
  const item=chapters[chapter];
  const Icon=item.icon;
  return <div className="studio-auth">
    <section className="auth-experience">
      <Link href="/" className="experience-brand"><FlaskConical size={29}/><span>靶研助手<small>TARGET EXPLORER</small></span></Link>
      <div className="experience-body"><h2>{item.heading}</h2><p>{item.description}</p>
        <div className="experience-map" aria-label="优选流程示意，非分析结果"><div className="map-heading"><span>分析流程</span><span>流程示意</span></div><div className="map-stage"><div className="map-source"><Icon size={25}/><b>{item.node}</b></div><div className="map-trace"><i/><i/><i/></div><div className="map-target"><span/><b>{item.next}</b><small>{item.note}</small></div><div className="map-satellites" aria-hidden="true"><span/><span/><span/><span/><span/></div></div><div className="map-foot"><ShieldCheck size={14}/><span>模型推断与可核查证据，清晰呈现</span><ArrowUpRight size={16}/></div></div>
      </div>
      <nav className="experience-tabs" aria-label="了解平台能力">{chapters.map(({icon:TabIcon,title},i)=><button key={title} aria-pressed={chapter===i} onClick={()=>setChapter(i)}><span>0{i+1}</span><TabIcon size={18}/><b>{title}</b></button>)}</nav>
      <footer className="experience-footer"><span>靶研助手</span><span>可解释靶点优选平台</span></footer>
    </section>
    <section className="auth-account"><Link href="/" className="account-back"><ArrowLeft size={15}/>返回首页</Link><div className="account-inner"><nav className="account-tabs" aria-label="账户操作"><Link href="/login" aria-current={pathname==="/login"?"page":undefined}>登录账户</Link><Link href="/register" aria-current={pathname==="/register"?"page":undefined}>创建账户</Link></nav>{children}<div className="account-assurance"><ShieldCheck size={16}/><span>你的研究项目、模型配置与分析结果，<br/>在专属账户中持续保存。</span></div></div><footer className="account-footer">靶研助手 · 疾病靶点研究平台</footer></section>
  </div>;
}
