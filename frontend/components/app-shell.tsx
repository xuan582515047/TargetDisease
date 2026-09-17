"use client";

import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import Sidebar from "@/components/sidebar";
import { api } from "@/lib/api";
import { ChevronRight, FlaskConical, BookOpen } from "lucide-react";
import Link from "next/link";

export default function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const publicPage =
    pathname === "/" || pathname === "/login" || pathname === "/register";
  const [checking, setChecking] = useState(!publicPage);

  useEffect(() => {
    if (publicPage) return;
    let cancelled = false;
    api
      .me()
      .then(() => {
        if (!cancelled) setChecking(false);
      })
      .catch(() => {
        if (!cancelled) router.replace("/login");
      });
    return () => {
      cancelled = true;
    };
  }, [pathname, publicPage, router]);

  if (publicPage) return <main className="min-h-screen w-full">{children}</main>;

  if (checking) {
    return (
      <div className="workspace-shell">
        <Sidebar />
        <main className="workspace-main flex items-center justify-center text-muted-foreground">
          正在验证登录状态…
        </main>
      </div>
    );
  }

  return (
    <div className="workspace-shell">
      <Sidebar />
      <main className="workspace-main">
        <header className="lab-topbar"><span><FlaskConical size={16} />研究空间<ChevronRight size={13} /><b>{pathname.startsWith("/target-discovery") ? "靶点探索" : pathname.startsWith("/settings") ? "模型配置" : pathname.startsWith("/projects") ? "研究项目" : "工作台"}</b></span><Link href="/#workflow"><BookOpen size={15} />探索指南</Link></header>
        {children}
      </main>
    </div>
  );
}
