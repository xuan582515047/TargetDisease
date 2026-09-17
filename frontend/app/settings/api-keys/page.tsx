"use client";

import { useEffect, useRef, useState } from "react";
import { KeyRound, ShieldCheck, RefreshCw, Pencil, Trash2, Save, ArrowRight, Check, Eye, EyeOff, Cpu, LockKeyhole, ExternalLink, CircleHelp, Zap } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import Link from "next/link";
import { api, type CredentialStatus } from "@/lib/api";

function formatDate(value?: string | null) {
  if (!value) return "—";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? "—" : date.toLocaleString("zh-CN", { hour12: false });
}

export default function ApiKeysPage() {
  const [status, setStatus] = useState<CredentialStatus | null>(null);
  const [key, setKey] = useState("");
  const [visible, setVisible] = useState(false);
  const [info, setInfo] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState<"save" | "validate" | "remove" | "refresh" | null>(null);
  const [initialLoading, setInitialLoading] = useState(true);
  const inputRef = useRef<HTMLInputElement>(null);
  const locked = initialLoading || busy !== null;

  useEffect(() => {
    let cancelled = false;
    api.credentials.status().then((data) => {
      if (!cancelled) setStatus(data);
    }).catch((err) => {
      if (!cancelled) setError(err instanceof Error ? err.message : "读取凭据失败，请重试");
    }).finally(() => {
      if (!cancelled) setInitialLoading(false);
    });
    return () => { cancelled = true; };
  }, []);

  async function refresh() {
    setBusy("refresh");
    setError("");
    setInfo("");
    try { setStatus(await api.credentials.status()); }
    catch (err) { setStatus(null); setError(err instanceof Error ? err.message : "读取失败"); }
    finally { setBusy(null); }
  }

  async function onSave(event: React.FormEvent) {
    event.preventDefault();
    if (locked) return;
    setError(""); setInfo("");
    if (!key.trim()) { setError("请输入 API Key"); return; }
    setBusy("save");
    try {
      setStatus(await api.credentials.save(key.trim()));
      setKey("");
      setInfo("已保存。下方已更新当前凭据，请验证后使用。");
    } catch (err) { setError(err instanceof Error ? err.message : "保存失败"); }
    finally { setBusy(null); }
  }

  async function onValidate() {
    if (locked) return;
    setBusy("validate"); setError(""); setInfo("");
    try { setStatus(await api.credentials.validate()); setInfo("验证通过，当前 Key 可用于分析。"); }
    catch (err) {
      setError(err instanceof Error ? err.message : "验证失败");
      // Validation may invalidate the stored key; re-read its authoritative state.
      try { setStatus(await api.credentials.status()); } catch { setStatus(null); }
    } finally { setBusy(null); }
  }

  async function onRemove() {
    if (locked || !window.confirm("确定删除当前保存的 DeepSeek API Key？删除后需重新配置才能分析。")) return;
    setBusy("remove"); setError(""); setInfo("");
    try { setStatus(await api.credentials.remove()); setInfo("已删除保存的凭据。"); }
    catch (err) { setError(err instanceof Error ? err.message : "删除失败"); }
    finally { setBusy(null); }
  }

  const connected = Boolean(status?.validated);
  const saved = Boolean(status?.configured);
  return (
    <div className="studio-page connection-page">
      <header className="studio-heading"><div><h1>模型配置</h1><p>管理 DeepSeek API Key，保存后验证连接。</p></div><span className="studio-tag"><LockKeyhole size={14}/>仅当前账户可管理</span></header>
      <div className="connection-layout">
        <div className="connection-main">
          <ol className="connection-steps" aria-label="模型配置进度">
            <li className={saved?"done":"current"}><span>{saved?<Check size={15}/>:"01"}</span><div><b>保存凭据</b><small>输入你的 API Key</small></div></li>
            <li className={connected?"done":saved?"current":""}><span>{connected?<Check size={15}/>:"02"}</span><div><b>验证连接</b><small>检查密钥是否可用</small></div></li>
            <li className={connected?"current":""}><span>03</span><div><b>开始分析</b><small>回到靶点识别</small></div></li>
          </ol>
          <section className="studio-panel key-editor" aria-labelledby="key-title"><div className="studio-panel-title"><div><h2 id="key-title">{saved?"更新模型凭据":"添加模型凭据"}</h2><p>{saved?"新的密钥将替换当前凭据，保存后需要重新验证。":"使用你自己的 DeepSeek API Key 连接模型服务。"}</p></div><KeyRound size={23}/></div>
            <form onSubmit={onSave}>
              <div className="key-label"><Label htmlFor="api-key">API Key</Label><span>DeepSeek</span></div>
              <div className="studio-key-input"><KeyRound size={17}/><Input ref={inputRef} id="api-key" type={visible?"text":"password"} value={key} onChange={event=>setKey(event.target.value)} placeholder="sk-…" autoComplete="off" spellCheck={false} disabled={locked} aria-describedby="key-help"/><button type="button" onClick={()=>setVisible(!visible)} aria-label={visible?"隐藏 API Key":"显示 API Key"} aria-pressed={visible}>{visible?<EyeOff size={18}/>:<Eye size={18}/>}</button></div>
              <p id="key-help" className="studio-helper"><LockKeyhole size={13}/>密钥不会显示在报告或分析结果中。</p>
              <div className="key-save-row"><a href="https://platform.deepseek.com/api_keys" target="_blank" rel="noreferrer">获取 API Key <ExternalLink size={13}/></a><Button className="studio-button" type="submit" disabled={locked||!status||!key.trim()}><Save size={16}/>{busy==="save"?"正在保存…":saved?"保存并替换":"保存凭据"}</Button></div>
            </form>
          </section>
          <div aria-live="polite">{info&&<p className="studio-feedback success" role="status"><Check size={17}/>{info}</p>}{error&&<p className="studio-feedback error" role="alert"><CircleHelp size={17}/>{error}</p>}</div>
          <section className="studio-panel connection-saved" aria-labelledby="saved-title" aria-busy={locked}><div className="studio-panel-title"><div><h2 id="saved-title">当前连接</h2></div><button className="studio-icon-button" aria-label="刷新连接状态" onClick={refresh} disabled={locked}><RefreshCw size={17} className={busy==="refresh"?"spin":""}/></button></div>
          {initialLoading?<p className="connection-placeholder" role="status">正在读取凭据…</p>:!status?<div className="connection-placeholder"><CircleHelp size={23}/><div><b>暂时无法读取连接</b><p>点击右上角刷新，重新获取凭据状态。</p></div></div>:!saved?<div className="connection-placeholder"><span className="connection-placeholder-icon"><KeyRound size={23}/></span><div><b>等待添加你的第一条凭据</b><p>保存后，在这里验证连接，即可开始研究。</p></div></div>:<><div className="saved-key-summary"><div className="saved-key-icon"><Cpu size={24}/></div><div><b>DeepSeek API</b><code>•••• •••• {status.last4}</code></div><span className={`studio-status ${connected?"completed":"queued"}`}>{connected?"已验证":"待验证"}</span></div><div className="saved-key-meta"><span>首次保存<b>{formatDate(status.created_at)}</b></span><span>最近更新<b>{formatDate(status.updated_at)}</b></span></div><div className="saved-key-actions"><button className="studio-button" onClick={onValidate} disabled={locked}><ShieldCheck size={16}/>{busy==="validate"?"正在验证连接…":connected?"重新验证":"验证连接"}</button><button className="studio-text-button" onClick={()=>inputRef.current?.focus()} disabled={locked}><Pencil size={15}/>更换</button><button className="studio-text-button danger" onClick={onRemove} disabled={locked}><Trash2 size={15}/>{busy==="remove"?"删除中…":"删除"}</button></div></>}
          </section>
          {connected&&<Link href="/target-discovery" className="connection-next"><span><Zap size={20}/><b>模型已就绪，开始你的下一次探索</b></span><ArrowRight size={20}/></Link>}
        </div>
        <aside className="connection-help"><h2>配置帮助</h2><ol><li><b>获取你的 Key</b><p>在 DeepSeek 开放平台创建 API Key，然后复制到这里。</p></li><li><b>保存并验证</b><p>点击保存，再验证连接。验证结果会显示在当前连接中。</p></li><li><b>进入研究流程</b><p>选择疾病并描述问题，开始识别种子靶点。</p></li></ol><details><summary>验证失败怎么办？</summary><p>检查 Key 是否完整、账户额度是否充足，以及网络能否访问 DeepSeek 服务。</p></details><details><summary>更换 Key 会影响历史报告吗？</summary><p>已有分析结果会保留。新任务使用当前保存的凭据。</p></details><div className="connection-boundary"><ShieldCheck size={19}/><p>模型负责识别线索，<br/>证据负责支撑判断。</p></div></aside>
      </div>
    </div>
  );
}
