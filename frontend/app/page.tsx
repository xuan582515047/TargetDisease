import Link from "next/link";
import { ArrowRight, ArrowUpRight, Crosshair, Network, ShieldCheck, FileText, GitCompareArrows, FlaskConical } from "lucide-react";
import DiscoveryPreview from "@/components/discovery-preview";

const features = [
  { icon: Crosshair, title: "识别种子靶点", tag: "01 / AI IDENTIFICATION", text: "结合疾病方向与机制关键词，由大模型从本地证据池识别种子靶点，保留识别理由与引用。", detail: "研究问题 → 种子候选" },
  { icon: Network, title: "扩展关联候选", tag: "02 / NETWORK PROPAGATION", text: "以种子为起点，在蛋白功能关联网络上运行个性化 PageRank，发现值得进一步研究的关联候选。", detail: "种子候选 → 网络扩展" },
  { icon: ShieldCheck, title: "核查证据来源", tag: "03 / EVIDENCE VALIDATION", text: "程序核查证据归属，区分有证据支持与仅网络关联的候选，让模型推断和可核查依据清晰呈现。", detail: "候选排序 → 证据核查" },
];
export default function Home() {
  return <div className="science-home">
    <a className="skip-link" href="#main-content">跳到主要内容</a>
    <header className="science-nav">
      <Link href="/" className="science-brand" aria-label="靶研助手首页"><span className="science-logo"><FlaskConical size={25} /></span><span>靶研助手<small>TARGET EXPLORER</small></span></Link>
      <nav aria-label="首页导航"><a href="#capabilities">核心能力</a><a href="#workflow">研究流程</a><Link href="/login">登录</Link><Link className="science-nav-cta" href="/target-discovery">进入工作台 <ArrowUpRight size={16} /></Link></nav>
    </header>
    <section className="science-hero" id="main-content" aria-labelledby="hero-title">
      <div className="science-hero-copy"><h1 id="hero-title">疾病靶点分析，<br /><span>有依据，可追溯</span></h1><p className="science-intro">融合大模型与生物关联网络的可解释靶点优选平台。<br />不止给出候选，更呈现每一次优选背后的依据。</p><div className="science-actions"><Link className="science-button" href="/target-discovery">新建分析 <ArrowRight size={18} /></Link><a href="#capabilities" className="science-secondary">了解功能 <ArrowUpRight size={17} /></a></div><div className="science-hero-notes"><span><ShieldCheck size={15} /> 证据可追溯</span><span><Network size={15} /> 关联可探索</span><span><FileText size={15} /> 报告可导出</span></div></div>
      <DiscoveryPreview />
    </section>
    <div className="science-methods"><span>数据与方法</span><div><small>证据来源</small>Open Targets</div><div><small>功能关联网络</small>STRING</div><div><small>种子识别</small>DeepSeek</div><div><small>网络传播</small>Personalized PageRank</div></div>
    <section id="capabilities" className="science-section" aria-labelledby="capabilities-title"><div className="science-section-heading"><div><h2 id="capabilities-title">支持靶点研究的三个环节</h2></div><p>将模型推断、网络关联与证据核查连接起来，<br />让研究者看见结果，也理解过程。</p></div><div className="science-features">{features.map(({ icon: Icon, title, tag, text, detail }) => <article key={tag}><div className="feature-icon"><Icon size={25} strokeWidth={1.5} /></div><h3>{title}</h3><p>{text}</p><div className="feature-detail">{detail}<ArrowUpRight size={18} /></div></article>)}</div><div className="science-toolstrip"><span><GitCompareArrows size={20} /><b>候选多维对比</b><small>识别、证据与融合排序</small></span><span><Network size={20} /><b>交互式关联网络</b><small>筛选、拖拽与局部探索</small></span><span><FileText size={20} /><b>结构化研究报告</b><small>保存分析，导出研究依据</small></span></div></section>
    <section id="workflow" className="science-workflow" aria-labelledby="workflow-title"><div><h2 id="workflow-title">从研究问题<br /><span>到分析报告</span></h2><Link href="/register" className="science-button">创建研究账户 <ArrowRight size={18} /></Link></div><ol>{[["定义研究问题", "选择疾病方向，输入问题与机制关键词。"], ["识别并扩展候选", "大模型识别种子，本地算法传播优选。"], ["探索证据与关联", "查看网络、对比候选，理解优选依据。"], ["沉淀研究报告", "导出分析结果，支持后续研究与讨论。"]].map(([title, text], i) => <li key={title}><span>0{i + 1}</span><div><h3>{title}</h3><p>{text}</p></div><ArrowUpRight size={20} /></li>)}</ol></section>
    <footer className="science-footer"><span className="science-brand"><FlaskConical size={23} />靶研助手</span><p>可解释靶点优选 · 为研究提供下一步线索</p><small>输出为候选优选依据，不构成因果关系或临床结论。</small></footer>
  </div>;
}
