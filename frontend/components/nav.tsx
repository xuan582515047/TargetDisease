"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { api, type User } from "@/lib/api";

export default function Nav() {
  const [user, setUser] = useState<User | null>(null);

  useEffect(() => {
    api.me().then(setUser).catch(() => setUser(null));
  }, []);

  return (
    <nav className="border-b bg-background">
      <div className="max-w-5xl mx-auto flex items-center gap-4 p-4 text-sm">
        <Link href="/" className="font-semibold text-base">
          靶研助手
        </Link>
        {user ? (
          <>
            <Link href="/dashboard" className="hover:underline">
              工作台
            </Link>
            <Link href="/target-discovery" className="hover:underline">
              靶点识别
            </Link>
            <Link href="/projects" className="hover:underline">
              项目
            </Link>
            <Link href="/settings/api-keys" className="hover:underline">
              API Key
            </Link>
            <span className="ml-auto text-muted-foreground">{user.email}</span>
            <Button
              variant="ghost"
              size="sm"
              onClick={async () => {
                await api.logout().catch(() => {});
                window.location.href = "/login";
              }}
            >
              退出
            </Button>
          </>
        ) : (
          <span className="ml-auto flex items-center gap-4">
            <Link href="/login" className="hover:underline">
              登录
            </Link>
            <Link href="/register" className="hover:underline">
              注册
            </Link>
          </span>
        )}
      </div>
    </nav>
  );
}
