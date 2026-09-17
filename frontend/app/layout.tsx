import type { Metadata } from "next";
import "./globals.css";
import "./science.css";
import "./research-space.css";
import "./studio.css";
import { Toaster } from "sonner";
import AppShell from "@/components/app-shell";

export const metadata: Metadata = {
  title: "靶研助手",
  description: "融合大模型与生物关联网络的可解释靶点优选平台。",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html
      lang="zh-CN"
      className="h-full antialiased"
    >
      <body className="min-h-full">
        <AppShell>{children}</AppShell>
        <Toaster position="top-right" richColors closeButton />
      </body>
    </html>
  );
}
