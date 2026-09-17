"use client";

import Link from "next/link";
import { LayoutDashboard, KeyRound, Crosshair, LogOut, ArrowUpRight, FolderOpen, Network } from "lucide-react";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import { api, type User } from "@/lib/api";

const NAV = [
  { href: "/dashboard", label: "工作台", icon: LayoutDashboard },
  { href: "/target-discovery", label: "靶点识别", icon: Crosshair },
  { href: "/projects", label: "研究项目", icon: FolderOpen },
  { href: "/settings/api-keys", label: "模型配置", icon: KeyRound },
];

export default function Sidebar() {
  const [user, setUser] = useState<User | null>(null);
  const pathname = usePathname();

  useEffect(() => {
    api.me().then(setUser).catch(() => setUser(null));
  }, []);

  return (
    <aside className="workspace-sidebar">
      <div className="flex items-center gap-3 border-b border-border px-5 py-5">
        <span className="grid size-10 place-items-center rounded-xl bg-secondary">
          <Network size={21} />
        </span>
        <div className="min-w-0">
          <div className="truncate text-base font-semibold leading-tight">靶研助手</div>
          <div className="mt-1 text-[9px] tracking-widest text-muted-foreground">TARGET EXPLORER</div>
        </div>
      </div>

      {user ? (
        <>
          <nav className="flex-1 space-y-1 px-3 py-4">
            <p className="sidebar-section-label">研究空间</p>
            {NAV.map((item) => {
              const Icon = item.icon;
              const active =
                pathname === item.href ||
                (item.href !== "/dashboard" && pathname.startsWith(item.href));
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  aria-current={active ? "page" : undefined}
                  className={`flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition-colors ${
                    active
                      ? "bg-accent font-medium text-accent-foreground shadow-sm"
                      : "text-muted-foreground hover:bg-accent hover:text-foreground"
                  }`}
                >
                  <Icon size={18} strokeWidth={1.6} />
                  {item.label}
                </Link>
              );
            })}
            <Link href="/" className="sidebar-home">
              返回首页 <ArrowUpRight size={15} />
            </Link>
          </nav>
          <div className="border-t border-border px-5 py-4">
            <div className="truncate text-sm text-foreground" title={user.email}>
              {user.email}
            </div>
            <button
              onClick={async () => {
                await api.logout().catch(() => {});
                window.location.href = "/login";
              }}
              className="mt-3 flex w-full items-center justify-center gap-2 rounded-lg bg-secondary px-3 py-2 text-xs font-medium transition-colors hover:bg-accent"
            >
              <LogOut size={14} /> 退出登录
            </button>
          </div>
        </>
      ) : (
        <div className="flex flex-1 flex-col items-center justify-center gap-3 px-5">
          <p className="text-sm text-muted-foreground">登录后开始靶点识别</p>
          <Link
            href="/login"
            className="w-full rounded-lg bg-secondary px-3 py-2 text-center text-sm font-medium hover:bg-accent"
          >
            登录 / 注册
          </Link>
        </div>
      )}
    </aside>
  );
}
