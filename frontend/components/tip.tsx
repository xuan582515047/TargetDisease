import type { ReactNode } from "react";

/**
 * 自定义提示框：悬停或键盘聚焦时在右上方弹出说明气泡。
 * 显隐由 globals.css 的 .tip / .tip-bubble 纯 CSS 控制。
 */
export default function Tip({ content, children }: { content: string; children: ReactNode }) {
  return (
    <div className="tip" tabIndex={0}>
      {children}
      <span role="tooltip" className="tip-bubble">{content}</span>
    </div>
  );
}
