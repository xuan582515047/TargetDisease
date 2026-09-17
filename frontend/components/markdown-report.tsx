"use client";

import { useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { toast } from "sonner";
import { Copy, Download, Eye, FileCode2 } from "lucide-react";
import { Button } from "@/components/ui/button";

type Props = {
  markdown: string;
  filename?: string;
};

export default function MarkdownReport({ markdown, filename = "靶点分析报告.md" }: Props) {
  const [view, setView] = useState<"preview" | "source">("preview");

  async function onCopy() {
    try {
      await navigator.clipboard.writeText(markdown);
      toast.success("Markdown 已复制到剪贴板");
    } catch {
      toast.error("复制失败，请重试");
    }
  }

  function onDownload() {
    const blob = new Blob([markdown], { type: "text/markdown;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    toast.success("已下载 .md 文件");
  }

  return (
    <div>
      <div className="mb-4 flex flex-wrap items-center gap-2">
        <div className="flex rounded-lg border border-border bg-secondary p-0.5">
          <button
            type="button"
            onClick={() => setView("preview")}
            className={`flex items-center gap-1.5 rounded-md px-3 py-1.5 text-xs font-medium transition-colors ${
              view === "preview" ? "bg-white text-foreground shadow-sm" : "text-muted-foreground"
            }`}
          >
            <Eye size={14} /> 预览
          </button>
          <button
            type="button"
            onClick={() => setView("source")}
            className={`flex items-center gap-1.5 rounded-md px-3 py-1.5 text-xs font-medium transition-colors ${
              view === "source" ? "bg-white text-foreground shadow-sm" : "text-muted-foreground"
            }`}
          >
            <FileCode2 size={14} /> 源码
          </button>
        </div>
        <div className="ml-auto flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={onCopy}>
            <Copy size={14} /> 复制 Markdown
          </Button>
          <Button variant="outline" size="sm" onClick={onDownload}>
            <Download size={14} /> 下载 .md
          </Button>
        </div>
      </div>

      {view === "preview" ? (
        <div className="markdown-body">
          <ReactMarkdown remarkPlugins={[remarkGfm]}>{markdown}</ReactMarkdown>
        </div>
      ) : (
        <pre className="whitespace-pre-wrap text-sm leading-relaxed text-muted-foreground">
          {markdown}
        </pre>
      )}
    </div>
  );
}
