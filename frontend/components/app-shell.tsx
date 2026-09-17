"use client";

import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import Sidebar from "@/components/sidebar";
import { api } from "@/lib/api";

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
      <main className="workspace-main">{children}</main>
    </div>
  );
}
