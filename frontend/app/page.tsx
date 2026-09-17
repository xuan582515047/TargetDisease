import Link from "next/link";
import { ArrowDown, ArrowRight, ArrowUpRight, Crosshair, Network, ScanLine, Sparkles, ListChecks } from "lucide-react";
import MolecularScene from "@/components/molecular-scene";

const capabilities = [
  { icon: Crosshair, label: "大模型靶点识别", caption: "结合研究问题，从候选池识别种子靶点", number: "01" },
  { icon: Network, label: "生物网络扩展", caption: "个性化 PageRank 在关联网络中优选候选", number: "02" },
  { icon: ListChecks, label: "证据核查", caption: "程序校验引用归属，标记可核查依据", number: "03" },
  { icon: Sparkles, label: "交互网络可视化", caption: "可拖拽、可筛选、可导出的关联网络", number: "04" },
];

export default function Home() {
  return (
    <div className="landing">
      <header className="landing-nav">
        <Link href="/" className="brand" aria-label="靶研助手首页"><span className="brand-mark"><Network size={21} /></span><span>靶研助手<span className="brand-en">TARGET EXPLORER</span></span></Link>
        <nav aria-label="首页导航"><a href="#capabilities">平台能力</a><a href="#workflow">探索流程</a><Link href="/login" className="nav-login">登录平台 <ArrowUpRight size={15} /></Link></nav>
      </header>
      <section className="landing-hero" aria-labelledby="hero-title">
        <div className="hero-grid" aria-hidden="true" /><MolecularScene />
        <div className="hero-copy">
          <div className="hero-eyebrow"><span /> EXPLORE THE POSSIBILITY OF TARGETS</div>
          <h1 id="hero-title">从研究问题，<br />发现<span>可解释靶点。</span></h1>
          <p className="hero-description">连接疾病、候选靶点与生物关联网络，<br className="mobile-break" />让每一次优选都有据可循。</p>
          <div className="hero-actions"><Link href="/login" className="primary-cta">开始使用 <ArrowRight size={19} /></Link><a href="#workflow" className="secondary-cta">了解探索流程 <ArrowUpRight size={17} /></a></div>
          <div className="hero-note"><span /> 以研究为起点 · 让优选更可解释</div>
        </div>
        <div className="hero-bottom"><span>QUESTION → TARGET → NETWORK</span><a href="#capabilities" aria-label="向下了解平台能力"><span>向下探索</span><ArrowDown size={16} /></a><span>TARGET EXPLORER / 01</span></div>
      </section>
      <section className="capabilities-section" id="capabilities" aria-labelledby="capabilities-title">
        <div className="section-heading"><div><span className="section-kicker">BUILT FOR DISCOVERY</span><h2 id="capabilities-title">让候选靶点，逐步清晰。</h2></div><p>从一个研究问题出发，<br />将分散的线索连接为可继续探索的方向。</p></div>
        <div className="capability-grid">{capabilities.map(({ icon: Icon, label, caption, number }) => <article className="capability-card" key={number}><div className="capability-top"><Icon size={25} strokeWidth={1.5} /><span>{number}</span></div><h3>{label}</h3><p>{caption}</p></article>)}</div>
      </section>
      <section className="workflow-section" id="workflow" aria-labelledby="workflow-title">
        <div className="workflow-intro"><span className="section-kicker">A CLEAR PATH FORWARD</span><h2 id="workflow-title">一个问题。<br /><span>一条优选路径。</span></h2><p>将想法带入工作台，<br />开启属于你的靶点优选。</p><Link href="/login" className="text-cta">进入平台 <ArrowRight size={18} /></Link></div>
        <ol className="workflow-steps"><li><span className="step-number">01</span><div><h3>定义研究问题</h3><p>选择支持的疾病方向，填写关注的研究问题与机制关键词。</p></div><Crosshair size={22} /></li><li><span className="step-number">02</span><div><h3>识别与扩展候选</h3><p>大模型识别种子靶点，本地网络传播算法扩展并优选候选。</p></div><Network size={22} /></li><li><span className="step-number">03</span><div><h3>核查与导出报告</h3><p>程序核查证据，在交互网络中查看、对比并导出报告。</p></div><ListChecks size={22} /></li></ol>
      </section>
      <footer className="landing-footer"><Link href="/" className="footer-brand"><Network size={18} /> 靶研助手</Link><span>为每一种可能，找到探索的起点。</span><span>可解释靶点优选平台</span></footer>
    </div>
  );
}
