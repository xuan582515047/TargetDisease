import Link from "next/link";
import { ArrowLeft, Network } from "lucide-react";
import MolecularScene from "@/components/molecular-scene";

export default function AuthShell({ children }: { children: React.ReactNode }) {
  return <div className="auth-shell"><header className="auth-nav"><Link href="/" className="brand"><span className="brand-mark"><Network size={21} /></span><span>靶研助手<span className="brand-en">TARGET EXPLORER</span></span></Link><Link href="/" className="auth-back"><ArrowLeft size={16} /> 返回首页</Link></header><div className="auth-content"><section className="auth-story"><span className="section-kicker">YOUR NEXT DISCOVERY STARTS HERE</span><h2>每一个靶点，<br />始于一次<span>优选。</span></h2><p>连接疾病、候选靶点与生物关联网络，<br />让研究的下一步，更加清晰。</p><MolecularScene /><span className="auth-story-foot">QUESTION → TARGET → NETWORK</span></section><section className="auth-form-panel" aria-label="账户访问">{children}<p className="auth-footnote">专注研究，让优选自然发生。</p></section></div><footer className="auth-footer">靶研助手 · 可解释靶点优选平台</footer></div>;
}
