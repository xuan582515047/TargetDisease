import Link from "next/link";
import { ArrowRight, ArrowUpRight, Crosshair, Network, ShieldCheck, FileText, GitCompareArrows, FlaskConical } from "lucide-react";
import DiscoveryPreview from "@/components/discovery-preview";

const features = [
  { icon: Crosshair, title: "识别种子靶点", tag: "01 / AI IDENTIFICATION", text: "用自然语言描述研究问题，大模型直接推荐值得优先研究的候选靶点基因，并给出推荐理由、相关度分与机制推测。", detail: "研究问题 → 种子候选" },
  { icon: Network, title: "扩展关联候选", tag: "02 / NETWORK PROPAGATION", text: "以种子为起点动态拉取 STRING 蛋白功能关联网络，运行个性化 PageRank，发现种子之外值得关注的关联候选。", detail: "种子候选 → 网络扩展" },
  { icon: FileText, title: "探索与沉淀", tag: "03 / EXPLORE & REPORT", text: "在交互式关联网络里筛选定位、对比候选，并把分析过程与结果沉淀为可导出的研究报告。", detail: "候选排序 → 网络与报告" },
];
export default function Home() {
  return <div className="science-home">
    <a className="skip-link" href="#main-content">跳到主要内容</a>
    <header className="science-nav">
      <Link href="/" className="science-brand" aria-label="靶研助手首页"><span className="science-logo"><FlaskConical size={25} /></span><span>靶研助手<small>TARGET EXPLORER</small></span></Link>
      <nav aria-label="首页导航"><a href="#capabilities">核心能力</a><a href="#workflow">研究流程</a><Link href="/login">登录</Link><Link className="science-nav-cta" href="/target-discovery">进入工作台 <ArrowUpRight size={16} /></Link></nav>
    </header>
    <section className="science-hero" id="main-content" aria-labelledby="hero-title">
      <div className="science-hero-copy"><h1 id="hero-title">疾病靶点分析，<br /><span>有依据，可追溯</span></h1><p className="science-intro">融合大模型与生物关联网络的可解释靶点优选平台。<br />不止给出候选，更呈现每一次优选背后的依据。</p><div className="science-actions"><Link className="science-button" href="/target-discovery">新建分析 <ArrowRight size={18} /></Link><a href="#capabilities" className="science-secondary">了解功能 <ArrowUpRight size={17} /></a></div><div className="science-hero-notes"><span><ShieldCheck size={15} /> 候选可解释</span><span><Network size={15} /> 关联可探索</span><span><FileText size={15} /> 报告可导出</span></div></div>
      <DiscoveryPreview />
    </section>
    <div className="science-methods"><span>方法与数据</span><div><small>候选推荐</small>DeepSeek 大模型</div><div><small>功能关联网络</small>STRING</div><div><small>网络传播</small>Personalized PageRank</div><div><small>结果交付</small>网络可视化 · 报告</div></div>
    <section id="capabilities" className="science-section" aria-labelledby="capabilities-title"><div className="science-section-heading"><div><h2 id="capabilities-title">支持靶点研究的三个环节</h2></div><p>把大模型推荐、网络传播与交互探索连接起来，<br />让研究者看见结果，也理解过程。</p></div><div className="science-features">{features.map(({ icon: Icon, title, tag, text, detail }) => <article key={tag}><div className="feature-icon"><Icon size={25} strokeWidth={1.5} /></div><h3>{title}</h3><p>{text}</p><div className="feature-detail">{detail}<ArrowUpRight size={18} /></div></article>)}</div><div className="science-toolstrip"><span><GitCompareArrows size={20} /><b>候选多维对比</b><small>相关度分与网络分</small></span><span><Network size={20} /><b>交互式关联网络</b><small>筛选、拖拽与局部探索</small></span><span><FileText size={20} /><b>结构化研究报告</b><small>保存分析，导出研究依据</small></span></div></section>
    <section id="workflow" className="science-workflow" aria-labelledby="workflow-title"><div><h2 id="workflow-title">从研究问题<br /><span>到分析报告</span></h2><Link href="/register" className="science-button">创建研究账户 <ArrowRight size={18} /></Link></div><ol>{[["描述研究问题", "直接输入自然语言研究问题，可选机制关键词。"], ["推荐并扩展候选", "大模型推荐种子，动态网络传播扩展候选。"], ["探索关联与对比", "查看网络、对比候选，理解优选依据。"], ["沉淀研究报告", "导出分析结果，支持后续研究与讨论。"]].map(([title, text], i) => <li key={title}><span>0{i + 1}</span><div><h3>{title}</h3><p>{text}</p></div><ArrowUpRight size={20} /></li>)}</ol></section>
    <footer className="science-footer"><span className="science-brand"><FlaskConical size={23} />靶研助手</span><p>可解释靶点优选 · 为研究提供下一步线索</p><small>输出为候选优选依据，不构成因果关系或临床结论。</small></footer>
  </div>;
}
