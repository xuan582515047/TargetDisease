"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { ArrowLeft, Download, FileText, Table2 } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import MarkdownReport from "@/components/markdown-report";
import { toast } from "sonner";
import { api, type Run } from "@/lib/api";

export default function ReportPage() {
  const params = useParams<{ runId: string }>();
  const runId = params.runId;
  const [run, setRun] = useState<Run | null>(null);

  useEffect(() => {
    api.targetAnalysis.get(runId).then(setRun).catch((err) => toast.error(err instanceof Error ? err.message : "加载失败"));
  }, [runId]);

  function download(filename: string, content: string, type: string) {
    const blob = new Blob([content], { type });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }

  const markdown = run?.results_json?.report_markdown ?? "";
  const csv = run?.results_json?.candidates_csv ?? "";

  return (
    <div className="research-dashboard">
      <div className="workspace-heading">
        <div>
          <p className="workspace-eyebrow">REPORT / 研究报告</p>
          <h1>分析报告</h1>
          <p>{run?.results_json?.disease?.name_zh ?? ""} · 预览与下载</p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={() => download(`report_${runId}.md`, markdown, "text/markdown;charset=utf-8")}>
            <Download size={15} /> Markdown
          </Button>
          <Button variant="outline" size="sm" onClick={() => download(`candidates_${runId}.csv`, csv, "text/csv;charset=utf-8")}>
            <Table2 size={15} /> 候选表 CSV
          </Button>
          <Link href={`/target-discovery/${runId}`}>
            <Button variant="ghost" size="sm"><ArrowLeft size={15} /> 返回</Button>
          </Link>
        </div>
      </div>

      <Card>
        <CardContent>
          {markdown ? (
            <MarkdownReport markdown={markdown} filename={`靶点优选报告_${runId}.md`} />
          ) : (
            <div className="flex flex-col items-center gap-3 py-16 text-muted-foreground">
              <FileText size={32} />
              <p className="text-sm">报告尚未生成</p>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
