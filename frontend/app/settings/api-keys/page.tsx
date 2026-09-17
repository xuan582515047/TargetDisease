"use client";

import { useEffect, useRef, useState } from "react";
import { KeyRound, ShieldCheck, RefreshCw, Pencil, Trash2, Save } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { api, type CredentialStatus } from "@/lib/api";

function formatDate(value?: string | null) {
  if (!value) return "—";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? "—" : date.toLocaleString("zh-CN", { hour12: false });
}

export default function ApiKeysPage() {
  const [status, setStatus] = useState<CredentialStatus | null>(null);
  const [key, setKey] = useState("");
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

  return (
    <div className="credential-page">
      <header className="workspace-heading"><div><p className="workspace-eyebrow">MODEL SETTINGS / 模型配置</p><h1>API Key 管理</h1><p>管理你的 DeepSeek 凭据，为研究分析连接模型服务。</p></div><span className="credential-private"><ShieldCheck size={16} /> 加密存储 · 仅本人可管理</span></header>
      <section className="credential-editor" aria-labelledby="credential-editor-title">
        <div className="credential-section-heading"><div><h2 id="credential-editor-title"><KeyRound size={18} />{status?.configured ? "更换 API Key" : "配置 API Key"}</h2><p>每个账号保存一条 DeepSeek Key；再次保存将覆盖当前 Key。</p></div></div>
        <form onSubmit={onSave}>
          <Label htmlFor="api-key">DeepSeek API Key</Label>
          <div className="credential-input-row"><Input ref={inputRef} id="api-key" type="password" value={key} onChange={(event) => setKey(event.target.value)} placeholder="输入你的 sk-…" autoComplete="off" spellCheck={false} disabled={locked} /><Button type="submit" disabled={locked || !status}><Save size={15} />{busy === "save" ? "保存中…" : status?.configured ? "保存并覆盖" : "保存 Key"}</Button></div>
          <p className="credential-input-note">保存后仅显示末 4 位，用于确认当前使用的凭据。</p>
        </form>
      </section>
      <div aria-live="polite">{info && <p className="credential-message success" role="status">{info}</p>}{error && <p className="credential-message error" role="alert">{error}</p>}</div>
      <section className="credential-storage" aria-labelledby="saved-credentials-title" aria-busy={locked}>
        <div className="credential-section-heading"><div><h2 id="saved-credentials-title">已保存的 API Key <span className="credential-count">{status ? (status.configured ? "1 / 1" : "0 / 1") : "— / 1"}</span></h2><p>这里展示当前账号实际保存的凭据，刷新页面后仍可查看。</p></div><Button type="button" variant="outline" onClick={refresh} disabled={locked}><RefreshCw size={14} />刷新</Button></div>
        {initialLoading ? <div className="credential-empty">正在读取已保存的凭据…</div> : !status ? <div className="credential-empty"><KeyRound size={28} /><h3>暂时无法读取凭据</h3><p>请检查登录状态或连接，然后点击刷新重试。</p></div> : !status.configured ? <div className="credential-empty"><KeyRound size={28} /><h3>还没有保存 API Key</h3><p>在上方输入并保存后，凭据信息会显示在这里。</p></div> : <div className="credential-table-scroll"><table className="credential-table"><caption className="sr-only">当前账号保存的 DeepSeek API Key</caption><thead><tr><th scope="col">服务商</th><th scope="col">Key</th><th scope="col">验证状态</th><th scope="col">首次保存时间</th><th scope="col">最近更新时间</th><th scope="col">操作</th></tr></thead><tbody><tr><td><span className="credential-provider"><span><KeyRound size={17} /></span><span>DeepSeek<small>当前分析凭据</small></span></span></td><td><code>••••••••{status.last4}</code></td><td><span className={`credential-badge ${status.validated ? "validated" : "pending"}`}>{status.validated ? "已验证" : "未验证"}</span></td><td>{formatDate(status.created_at)}</td><td>{formatDate(status.updated_at)}</td><td><div className="credential-actions"><button type="button" disabled={locked} onClick={onValidate}><ShieldCheck size={14} />{busy === "validate" ? "验证中…" : "验证"}</button><button type="button" disabled={locked} onClick={() => { setInfo("在上方输入新的 Key，保存后将覆盖当前凭据。"); inputRef.current?.focus(); }}><Pencil size={14} />更换</button><button type="button" className="credential-delete" disabled={locked} onClick={onRemove}><Trash2 size={14} />{busy === "remove" ? "删除中…" : "删除"}</button></div></td></tr></tbody></table></div>}
      </section>
    </div>
  );
}
