"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { toast } from "sonner";
import { api, type Project } from "@/lib/api";

export default function ProjectsPage() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [name, setName] = useState("");
  const [disease, setDisease] = useState("");
  const [notes, setNotes] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [pendingDelete, setPendingDelete] = useState<Project | null>(null);
  const [deleteError, setDeleteError] = useState("");

  const load = useCallback(async () => {
    try {
      setProjects(await api.projects.list());
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "加载项目失败");
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  async function onCreate(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    if (!name.trim()) {
      setError("请输入项目名称");
      return;
    }
    setLoading(true);
    try {
      await api.projects.create({
        name: name.trim(),
        primary_disease: disease.trim() || null,
        notes: notes.trim() || null,
      });
      setName("");
      setDisease("");
      setNotes("");
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "创建失败");
    } finally {
      setLoading(false);
    }
  }

  function onDelete(project: Project) {
    setDeleteError("");
    setPendingDelete(project);
  }

  async function onConfirmDelete() {
    if (!pendingDelete) return;
    const { id } = pendingDelete;
    setPendingDelete(null);
    setDeleteError("");
    const previous = projects; // 保存旧列表，失败时回滚
    // 先立即从界面移除，给用户即时的“已删除”反馈
    setProjects((list) => list.filter((p) => p.id !== id));
    try {
      await api.projects.remove(id);
      toast.success("项目已删除");
    } catch (err) {
      setProjects(previous); // 回滚，恢复被移除的项目
      toast.error(err instanceof Error ? err.message : "删除失败，请重试");
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">项目</h1>
        <p className="text-muted-foreground">管理你的药物靶点发现项目。</p>
        {deleteError && <p className="mt-2 text-sm text-destructive">{deleteError}</p>}
      </div>

      <Card>
        <CardHeader>
          <CardTitle>新建项目</CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={onCreate} className="space-y-4">
            <div className="grid gap-4 sm:grid-cols-2">
              <div className="space-y-2">
                <Label htmlFor="name">项目名称</Label>
                <Input
                  id="name"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="例如：阿尔茨海默病研究"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="disease">主要疾病</Label>
                <Input
                  id="disease"
                  value={disease}
                  onChange={(e) => setDisease(e.target.value)}
                  placeholder="可选"
                />
              </div>
            </div>
            <div className="space-y-2">
              <Label htmlFor="notes">备注</Label>
              <textarea
                id="notes"
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                rows={2}
                className="w-full rounded-lg border border-input bg-transparent px-2.5 py-1.5 text-sm outline-none focus-visible:border-ring"
                placeholder="可选"
              />
            </div>
            {error && <p className="text-sm text-destructive">{error}</p>}
            <Button type="submit" disabled={loading}>
              创建
            </Button>
          </form>
        </CardContent>
      </Card>

      {projects.length === 0 ? (
        <Card>
          <CardHeader>
            <CardTitle>暂无项目</CardTitle>
            <CardDescription>在上方创建你的第一个项目。</CardDescription>
          </CardHeader>
        </Card>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2">
          {projects.map((p) => (
            <Card key={p.id}>
              <CardHeader>
                <CardTitle>{p.name}</CardTitle>
                <CardDescription>
                  {p.primary_disease || "未指定疾病"}
                  {" · "}
                  {new Date(p.created_at).toLocaleDateString("zh-CN")}
                </CardDescription>
              </CardHeader>
              {p.notes && (
                <CardContent>
                  <p className="text-sm text-muted-foreground">{p.notes}</p>
                </CardContent>
              )}
              <CardContent>
                <Link
                  href={`/target-discovery?project_id=${p.id}`}
                  className="mr-4 text-sm text-primary underline"
                >
                  发起靶点分析
                </Link>
                <Button variant="destructive" size="sm" onClick={() => onDelete(p)}>
                  删除
                </Button>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      <Dialog
        open={pendingDelete !== null}
        onOpenChange={(open) => {
          if (!open) setPendingDelete(null);
        }}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>是否要删除该项目？</DialogTitle>
            <DialogDescription>
              确定要删除「{pendingDelete?.name}」吗？其关联的分析运行也会一并删除。
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setPendingDelete(null)}>
              取消
            </Button>
            <Button variant="destructive" onClick={onConfirmDelete}>
              删除
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
